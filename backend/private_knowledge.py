"""User-isolated private knowledge-base storage and lexical retrieval."""

from __future__ import annotations

import hashlib
import io
import math
import re
import sqlite3
from collections import Counter
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator


DEFAULT_DB_PATH = Path(__file__).resolve().parent / "data" / "auth.sqlite3"
ALLOWED_EXTENSIONS = {".txt", ".md", ".markdown", ".pdf"}
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_TEXT_CHARS = 2_000_000
MAX_PDF_PAGES = 120
MAX_DOCUMENT_CHUNKS = 2_000


class PrivateKnowledgeError(ValueError):
    pass


class PrivateKnowledgeNotFoundError(PrivateKnowledgeError):
    pass


class PrivateKnowledgeConflictError(PrivateKnowledgeError):
    pass


@dataclass(frozen=True)
class PrivateKnowledgeRuntimeContext:
    user_id: int
    db_path: Path


_RUNTIME_CONTEXT: ContextVar[PrivateKnowledgeRuntimeContext | None] = ContextVar(
    "private_knowledge_runtime_context",
    default=None,
)


def bind_private_knowledge_context(
    user_id: int,
    db_path: str | Path | None = None,
) -> Token[PrivateKnowledgeRuntimeContext | None]:
    return _RUNTIME_CONTEXT.set(
        PrivateKnowledgeRuntimeContext(
            user_id=max(0, int(user_id or 0)),
            db_path=Path(db_path) if db_path is not None else DEFAULT_DB_PATH,
        )
    )


def reset_private_knowledge_context(token: Token[PrivateKnowledgeRuntimeContext | None]) -> None:
    _RUNTIME_CONTEXT.reset(token)


@contextmanager
def private_knowledge_scope(
    user_id: int,
    db_path: str | Path | None = None,
) -> Iterator[None]:
    token = bind_private_knowledge_context(user_id, db_path)
    try:
        yield
    finally:
        reset_private_knowledge_context(token)


def current_private_knowledge_context() -> PrivateKnowledgeRuntimeContext | None:
    return _RUNTIME_CONTEXT.get()


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _clean_text(value: object) -> str:
    text = str(value or "").replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _tokens(value: object) -> list[str]:
    text = _clean_text(value).lower()
    tokens = re.findall(r"[a-z][a-z0-9_+\-]{1,}|[0-9]+(?:\.[0-9]+)?", text)
    for sequence in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        tokens.extend(sequence[index : index + 2] for index in range(len(sequence) - 1))
        if len(sequence) <= 12:
            tokens.append(sequence)
    return tokens


def _split_text(text: str, target_size: int = 1000, overlap: int = 140) -> list[str]:
    clean = _clean_text(text)[:MAX_TEXT_CHARS]
    if not clean:
        return []
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", clean) if item.strip()]
    chunks: list[str] = []
    buffer = ""
    for paragraph in paragraphs:
        if len(buffer) + len(paragraph) + 2 <= target_size:
            buffer = f"{buffer}\n\n{paragraph}".strip()
            continue
        if buffer:
            chunks.append(buffer)
        if len(paragraph) <= target_size:
            buffer = paragraph
            continue
        start = 0
        while start < len(paragraph) and len(chunks) < MAX_DOCUMENT_CHUNKS:
            end = min(len(paragraph), start + target_size)
            chunks.append(paragraph[start:end])
            if end >= len(paragraph):
                break
            start = max(start + 1, end - overlap)
        buffer = ""
        if len(chunks) >= MAX_DOCUMENT_CHUNKS:
            break
    if buffer and len(chunks) < MAX_DOCUMENT_CHUNKS:
        chunks.append(buffer)
    return chunks


def _decode_text(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def _extract_pdf(content: bytes) -> list[tuple[int, str]]:
    pages: list[tuple[int, str]] = []
    try:
        import fitz

        with fitz.open(stream=content, filetype="pdf") as document:
            for page_index, page in enumerate(document):
                if page_index >= MAX_PDF_PAGES:
                    break
                text = _clean_text(page.get_text("text"))
                if text:
                    pages.append((page_index + 1, text))
    except Exception:
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(content))
            for page_index, page in enumerate(reader.pages[:MAX_PDF_PAGES]):
                text = _clean_text(page.extract_text() or "")
                if text:
                    pages.append((page_index + 1, text))
        except Exception as exc:
            raise PrivateKnowledgeError(f"PDF 解析失败：{exc}") from exc
    return pages


def extract_document_chunks(filename: str, content: bytes) -> list[dict[str, Any]]:
    safe_name = Path(str(filename or "")).name.strip()
    extension = Path(safe_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise PrivateKnowledgeError("仅支持 TXT、Markdown 和 PDF 文件")
    if not content:
        raise PrivateKnowledgeError("上传文件为空")
    if len(content) > MAX_UPLOAD_BYTES:
        raise PrivateKnowledgeError("单个文件不能超过 15 MB")

    chunks: list[dict[str, Any]] = []
    if extension == ".pdf":
        for page, page_text in _extract_pdf(content):
            for section in _split_text(page_text):
                chunks.append({"page": page, "content": section})
                if len(chunks) >= MAX_DOCUMENT_CHUNKS:
                    break
            if len(chunks) >= MAX_DOCUMENT_CHUNKS:
                break
    else:
        chunks = [{"page": None, "content": item} for item in _split_text(_decode_text(content))]

    if not chunks:
        raise PrivateKnowledgeError("文件中没有可检索的文本内容")
    return chunks


def _collection_row(conn: sqlite3.Connection, user_id: int, collection_id: int) -> sqlite3.Row:
    row = conn.execute(
        """
        SELECT id, user_id, name, description, archived, created_at, updated_at
        FROM private_knowledge_collections
        WHERE id = ? AND user_id = ?
        """,
        (int(collection_id), int(user_id)),
    ).fetchone()
    if not row:
        raise PrivateKnowledgeNotFoundError("知识库不存在")
    return row


def _document_public(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "collectionId": int(row["collection_id"]),
        "filename": str(row["filename"] or ""),
        "title": str(row["title"] or ""),
        "mimeType": str(row["mime_type"] or "application/octet-stream"),
        "byteSize": int(row["byte_size"] or 0),
        "status": str(row["status"] or "ready"),
        "error": str(row["error"] or ""),
        "chunkCount": int(row["chunk_count"] or 0),
        "createdAt": str(row["created_at"] or ""),
        "updatedAt": str(row["updated_at"] or ""),
    }


def list_knowledge_collections(
    conn: sqlite3.Connection,
    user_id: int,
    *,
    include_archived: bool = False,
) -> dict[str, Any]:
    state = conn.execute(
        "SELECT active_collection_id FROM user_private_knowledge_state WHERE user_id = ?",
        (int(user_id),),
    ).fetchone()
    active_collection_id = int(state["active_collection_id"] or 0) if state else 0
    where_archived = "" if include_archived else "AND archived = 0"
    collections = conn.execute(
        f"""
        SELECT id, user_id, name, description, archived, created_at, updated_at
        FROM private_knowledge_collections
        WHERE user_id = ? {where_archived}
        ORDER BY updated_at DESC, id DESC
        """,
        (int(user_id),),
    ).fetchall()
    documents = conn.execute(
        """
        SELECT id, collection_id, filename, title, mime_type, byte_size, status,
               error, chunk_count, created_at, updated_at
        FROM private_knowledge_documents
        WHERE user_id = ?
        ORDER BY created_at DESC, id DESC
        """,
        (int(user_id),),
    ).fetchall()
    documents_by_collection: dict[int, list[dict[str, Any]]] = {}
    for document in documents:
        documents_by_collection.setdefault(int(document["collection_id"]), []).append(_document_public(document))

    items: list[dict[str, Any]] = []
    total_chunks = 0
    for row in collections:
        collection_documents = documents_by_collection.get(int(row["id"]), [])
        chunk_count = sum(int(item["chunkCount"] or 0) for item in collection_documents)
        total_chunks += chunk_count
        items.append(
            {
                "id": int(row["id"]),
                "name": str(row["name"] or ""),
                "description": str(row["description"] or ""),
                "archived": bool(row["archived"]),
                "isActive": int(row["id"]) == active_collection_id,
                "documentCount": len(collection_documents),
                "chunkCount": chunk_count,
                "documents": collection_documents,
                "createdAt": str(row["created_at"] or ""),
                "updatedAt": str(row["updated_at"] or ""),
            }
        )
    if active_collection_id and not any(item["id"] == active_collection_id for item in items):
        active_collection_id = 0
    return {
        "collections": items,
        "activeCollectionId": active_collection_id or None,
        "stats": {
            "collectionCount": len(items),
            "documentCount": sum(item["documentCount"] for item in items),
            "chunkCount": total_chunks,
        },
    }


def create_knowledge_collection(
    conn: sqlite3.Connection,
    user_id: int,
    name: object,
    description: object = "",
    *,
    activate: bool = True,
    timestamp: str | None = None,
) -> dict[str, Any]:
    clean_name = _clean_text(name)[:80]
    if not clean_name:
        raise PrivateKnowledgeError("知识库名称不能为空")
    clean_description = _clean_text(description)[:500]
    now = timestamp or _now()
    try:
        cursor = conn.execute(
            """
            INSERT INTO private_knowledge_collections
                (user_id, name, description, archived, created_at, updated_at)
            VALUES (?, ?, ?, 0, ?, ?)
            """,
            (int(user_id), clean_name, clean_description, now, now),
        )
    except sqlite3.IntegrityError as exc:
        raise PrivateKnowledgeConflictError("已存在同名知识库") from exc
    collection_id = int(cursor.lastrowid)
    state = conn.execute(
        "SELECT active_collection_id FROM user_private_knowledge_state WHERE user_id = ?",
        (int(user_id),),
    ).fetchone()
    should_activate = activate or not state or not int(state["active_collection_id"] or 0)
    if should_activate:
        conn.execute(
            """
            INSERT INTO user_private_knowledge_state (user_id, active_collection_id, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                active_collection_id = excluded.active_collection_id,
                updated_at = excluded.updated_at
            """,
            (int(user_id), collection_id, now, now),
        )
    payload = list_knowledge_collections(conn, int(user_id))
    return next(item for item in payload["collections"] if item["id"] == collection_id)


def update_knowledge_collection(
    conn: sqlite3.Connection,
    user_id: int,
    collection_id: int,
    *,
    name: object | None = None,
    description: object | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    current = _collection_row(conn, user_id, collection_id)
    clean_name = _clean_text(name if name is not None else current["name"])[:80]
    if not clean_name:
        raise PrivateKnowledgeError("知识库名称不能为空")
    clean_description = _clean_text(
        description if description is not None else current["description"]
    )[:500]
    try:
        conn.execute(
            """
            UPDATE private_knowledge_collections
            SET name = ?, description = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (clean_name, clean_description, timestamp or _now(), int(collection_id), int(user_id)),
        )
    except sqlite3.IntegrityError as exc:
        raise PrivateKnowledgeConflictError("已存在同名知识库") from exc
    payload = list_knowledge_collections(conn, int(user_id), include_archived=True)
    return next(item for item in payload["collections"] if item["id"] == int(collection_id))


def activate_knowledge_collection(
    conn: sqlite3.Connection,
    user_id: int,
    collection_id: int,
    *,
    timestamp: str | None = None,
) -> dict[str, Any]:
    collection = _collection_row(conn, user_id, collection_id)
    if bool(collection["archived"]):
        raise PrivateKnowledgeError("已归档知识库不能设为当前知识库")
    now = timestamp or _now()
    conn.execute(
        """
        INSERT INTO user_private_knowledge_state (user_id, active_collection_id, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            active_collection_id = excluded.active_collection_id,
            updated_at = excluded.updated_at
        """,
        (int(user_id), int(collection_id), now, now),
    )
    payload = list_knowledge_collections(conn, int(user_id))
    return next(item for item in payload["collections"] if item["id"] == int(collection_id))


def find_knowledge_collection(
    conn: sqlite3.Connection,
    user_id: int,
    reference: object,
) -> dict[str, Any]:
    text = _clean_text(reference)
    payload = list_knowledge_collections(conn, int(user_id))
    collections = payload["collections"]
    if text.isdigit():
        match = next((item for item in collections if item["id"] == int(text)), None)
        if match:
            return match
    lowered = text.lower()
    exact = next((item for item in collections if item["name"].lower() == lowered), None)
    if exact:
        return exact
    partial = next(
        (item for item in collections if item["name"] and item["name"].lower() in lowered),
        None,
    )
    if partial:
        return partial
    raise PrivateKnowledgeNotFoundError("没有找到指定知识库")


def delete_knowledge_collection(
    conn: sqlite3.Connection,
    user_id: int,
    collection_id: int,
) -> dict[str, Any]:
    _collection_row(conn, user_id, collection_id)
    state = conn.execute(
        "SELECT active_collection_id FROM user_private_knowledge_state WHERE user_id = ?",
        (int(user_id),),
    ).fetchone()
    conn.execute(
        "DELETE FROM private_knowledge_collections WHERE id = ? AND user_id = ?",
        (int(collection_id), int(user_id)),
    )
    if state and int(state["active_collection_id"] or 0) == int(collection_id):
        replacement = conn.execute(
            """
            SELECT id FROM private_knowledge_collections
            WHERE user_id = ? AND archived = 0
            ORDER BY updated_at DESC, id DESC LIMIT 1
            """,
            (int(user_id),),
        ).fetchone()
        conn.execute(
            """
            UPDATE user_private_knowledge_state
            SET active_collection_id = ?, updated_at = ?
            WHERE user_id = ?
            """,
            (int(replacement["id"]) if replacement else None, _now(), int(user_id)),
        )
    return list_knowledge_collections(conn, int(user_id))


def add_knowledge_document(
    conn: sqlite3.Connection,
    user_id: int,
    collection_id: int,
    *,
    filename: str,
    content: bytes,
    mime_type: str = "application/octet-stream",
    timestamp: str | None = None,
) -> dict[str, Any]:
    collection = _collection_row(conn, user_id, collection_id)
    if bool(collection["archived"]):
        raise PrivateKnowledgeError("不能向已归档知识库上传文件")
    safe_name = Path(str(filename or "")).name.strip()[:180]
    if not safe_name:
        raise PrivateKnowledgeError("文件名不能为空")
    checksum = hashlib.sha256(content).hexdigest()
    duplicate = conn.execute(
        """
        SELECT id FROM private_knowledge_documents
        WHERE user_id = ? AND collection_id = ? AND sha256 = ?
        """,
        (int(user_id), int(collection_id), checksum),
    ).fetchone()
    if duplicate:
        raise PrivateKnowledgeConflictError("该文件已存在于当前知识库")

    chunks = extract_document_chunks(safe_name, content)
    now = timestamp or _now()
    cursor = conn.execute(
        """
        INSERT INTO private_knowledge_documents
            (user_id, collection_id, filename, title, mime_type, byte_size, sha256,
             status, error, chunk_count, content_blob, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'ready', '', ?, ?, ?, ?)
        """,
        (
            int(user_id),
            int(collection_id),
            safe_name,
            Path(safe_name).stem[:120],
            str(mime_type or "application/octet-stream")[:120],
            len(content),
            checksum,
            len(chunks),
            sqlite3.Binary(content),
            now,
            now,
        ),
    )
    document_id = int(cursor.lastrowid)
    conn.executemany(
        """
        INSERT INTO private_knowledge_chunks
            (user_id, collection_id, document_id, chunk_index, page, content, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                int(user_id),
                int(collection_id),
                document_id,
                index,
                item.get("page"),
                item["content"],
                now,
            )
            for index, item in enumerate(chunks, start=1)
        ],
    )
    conn.execute(
        "UPDATE private_knowledge_collections SET updated_at = ? WHERE id = ?",
        (now, int(collection_id)),
    )
    row = conn.execute(
        """
        SELECT id, collection_id, filename, title, mime_type, byte_size, status,
               error, chunk_count, created_at, updated_at
        FROM private_knowledge_documents WHERE id = ?
        """,
        (document_id,),
    ).fetchone()
    return _document_public(row)


def delete_knowledge_document(
    conn: sqlite3.Connection,
    user_id: int,
    document_id: int,
) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT id, collection_id FROM private_knowledge_documents
        WHERE id = ? AND user_id = ?
        """,
        (int(document_id), int(user_id)),
    ).fetchone()
    if not row:
        raise PrivateKnowledgeNotFoundError("知识库文档不存在")
    conn.execute(
        "DELETE FROM private_knowledge_documents WHERE id = ? AND user_id = ?",
        (int(document_id), int(user_id)),
    )
    conn.execute(
        "UPDATE private_knowledge_collections SET updated_at = ? WHERE id = ?",
        (_now(), int(row["collection_id"])),
    )
    return list_knowledge_collections(conn, int(user_id))


def _resolve_runtime(
    user_id: int | None,
    db_path: str | Path | None,
) -> tuple[int, Path] | None:
    if user_id is not None and int(user_id or 0) > 0:
        return int(user_id), Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    context = current_private_knowledge_context()
    if not context or context.user_id <= 0:
        return None
    return context.user_id, Path(db_path) if db_path is not None else context.db_path


def retrieve_private_knowledge(
    query: str,
    *,
    user_id: int | None = None,
    db_path: str | Path | None = None,
    collection_id: int | None = None,
    top_k: int = 4,
    max_context_chars: int = 6000,
) -> dict[str, Any]:
    runtime = _resolve_runtime(user_id, db_path)
    empty = {
        "query": str(query or ""),
        "grounded": False,
        "context": "",
        "hits": [],
        "citations": [],
        "activeCollection": None,
        "stats": {"collections": 0, "documents": 0, "indexedChunks": 0, "matchedChunks": 0},
    }
    if runtime is None:
        return empty
    resolved_user_id, resolved_db_path = runtime
    if not resolved_db_path.exists():
        return empty

    try:
        conn = sqlite3.connect(resolved_db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            if collection_id is None:
                state = conn.execute(
                    "SELECT active_collection_id FROM user_private_knowledge_state WHERE user_id = ?",
                    (resolved_user_id,),
                ).fetchone()
                collection_id = int(state["active_collection_id"] or 0) if state else 0
            collection = conn.execute(
                """
                SELECT id, name FROM private_knowledge_collections
                WHERE id = ? AND user_id = ? AND archived = 0
                """,
                (int(collection_id or 0), resolved_user_id),
            ).fetchone()
            if not collection:
                return empty
            rows = conn.execute(
                """
                SELECT c.id, c.chunk_index, c.page, c.content,
                       d.id AS document_id, d.filename, d.title,
                       k.id AS collection_id, k.name AS collection_name
                FROM private_knowledge_chunks c
                JOIN private_knowledge_documents d ON d.id = c.document_id
                JOIN private_knowledge_collections k ON k.id = c.collection_id
                WHERE c.user_id = ? AND c.collection_id = ? AND d.status = 'ready'
                ORDER BY c.id
                """,
                (resolved_user_id, int(collection["id"])),
            ).fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return empty

    query_terms = list(dict.fromkeys(_tokens(query)))
    if not query_terms or not rows:
        empty["activeCollection"] = {"id": int(collection["id"]), "name": str(collection["name"])}
        empty["stats"] = {
            "collections": 1,
            "documents": len({int(row["document_id"]) for row in rows}),
            "indexedChunks": len(rows),
            "matchedChunks": 0,
        }
        return empty

    frequencies: list[Counter[str]] = []
    document_frequencies: Counter[str] = Counter()
    lengths: list[int] = []
    for row in rows:
        terms = Counter(_tokens(f"{row['title']} {row['title']} {row['content']}"))
        frequencies.append(terms)
        lengths.append(max(1, sum(terms.values())))
        document_frequencies.update(terms.keys())
    average_length = sum(lengths) / len(lengths) if lengths else 1.0
    total_chunks = max(len(rows), 1)
    scored: list[tuple[float, sqlite3.Row]] = []
    for index, row in enumerate(rows):
        terms = frequencies[index]
        score = 0.0
        for term in query_terms:
            frequency = terms.get(term, 0)
            if not frequency:
                continue
            document_frequency = document_frequencies.get(term, 0)
            inverse_frequency = math.log(
                1 + (total_chunks - document_frequency + 0.5) / (document_frequency + 0.5)
            )
            score += inverse_frequency * (
                frequency * 2.5
                / (frequency + 1.5 * (0.25 + 0.75 * lengths[index] / average_length))
            )
        if score > 0:
            scored.append((score, row))
    scored.sort(key=lambda item: item[0], reverse=True)

    hits: list[dict[str, Any]] = []
    context_parts: list[str] = []
    context_length = 0
    used_documents: Counter[int] = Counter()
    limit = max(1, min(int(top_k), 12))
    for score, row in scored:
        document_id = int(row["document_id"])
        if len(hits) >= limit:
            break
        if used_documents[document_id] >= 2:
            continue
        citation_id = f"PKB{len(hits) + 1}"
        locator = f"第 {int(row['page'])} 页" if row["page"] else f"片段 {int(row['chunk_index'])}"
        excerpt = str(row["content"] or "")[:1600]
        block = (
            f"[{citation_id}][我的知识库] {row['title']}"
            f"（{row['filename']}，{locator}；知识库：{row['collection_name']}）\n{excerpt}"
        )
        if context_parts and context_length + len(block) > max_context_chars:
            break
        used_documents[document_id] += 1
        context_parts.append(block)
        context_length += len(block)
        hits.append(
            {
                "citationId": citation_id,
                "scope": "private",
                "sourceType": "user-private-knowledge",
                "collectionId": int(row["collection_id"]),
                "collectionName": str(row["collection_name"] or ""),
                "documentId": document_id,
                "source": str(row["filename"] or ""),
                "title": str(row["title"] or ""),
                "page": int(row["page"]) if row["page"] else None,
                "section": int(row["chunk_index"]),
                "score": round(score, 4),
                "excerpt": excerpt,
            }
        )

    return {
        "query": str(query or ""),
        "grounded": bool(hits),
        "context": "\n\n".join(context_parts),
        "hits": hits,
        "citations": [
            {
                "id": item["citationId"],
                "scope": item["scope"],
                "sourceType": item["sourceType"],
                "collectionId": item["collectionId"],
                "collectionName": item["collectionName"],
                "documentId": item["documentId"],
                "title": item["title"],
                "source": item["source"],
                "page": item["page"],
                "section": item["section"],
            }
            for item in hits
        ],
        "activeCollection": {"id": int(collection["id"]), "name": str(collection["name"] or "")},
        "stats": {
            "collections": 1,
            "documents": len({int(row["document_id"]) for row in rows}),
            "indexedChunks": len(rows),
            "matchedChunks": len(hits),
        },
    }
