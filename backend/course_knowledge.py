"""Local course knowledge base with traceable lexical retrieval.

The primary course corpus lives in ``rag文档``. Text lessons are indexed eagerly;
PDFs are catalogued and extracted on demand when their filenames match a query.
This keeps startup fast while still making the complete document set available.
"""

from __future__ import annotations

import json
import copy
import hashlib
import math
import os
import re
import sqlite3
import threading
import time
from collections import Counter, OrderedDict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    from private_knowledge import retrieve_private_knowledge
except ImportError:  # pragma: no cover - package-style import fallback
    from .private_knowledge import retrieve_private_knowledge

try:
    from hybrid_knowledge import route_hybrid_knowledge
except ImportError:  # pragma: no cover - package-style import fallback
    from .hybrid_knowledge import route_hybrid_knowledge

try:
    from knowledge_retrieval_agent import plan_knowledge_retrieval
except ImportError:  # pragma: no cover - package-style import fallback
    from .knowledge_retrieval_agent import plan_knowledge_retrieval


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = Path(os.environ.get("COURSE_KNOWLEDGE_CORPUS_DIR") or (PROJECT_ROOT / "rag文档")).resolve()
CACHE_PATH = Path(
    os.environ.get("COURSE_KNOWLEDGE_INDEX_PATH")
    or (Path(__file__).resolve().parent / "data" / "course_knowledge_index.json")
).resolve()
CACHE_VERSION = 2
MAX_PDF_PAGES_PER_DOCUMENT = 80


@dataclass
class KnowledgeChunk:
    chunk_id: str
    source: str
    title: str
    content: str
    page: int | None = None
    section: int | None = None


def _clean_text(value: str) -> str:
    value = str(value or "").replace("\x00", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def _tokens(value: str) -> list[str]:
    text = _clean_text(value).lower()
    tokens = re.findall(r"[a-z][a-z0-9_+\-]{1,}|[0-9]+(?:\.[0-9]+)?", text)
    for sequence in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        tokens.extend(sequence[index : index + 2] for index in range(len(sequence) - 1))
        if len(sequence) <= 12:
            tokens.append(sequence)
    return tokens


def _split_text(text: str, target_size: int = 900, overlap: int = 120) -> list[str]:
    clean = _clean_text(text)
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
        while start < len(paragraph):
            end = min(len(paragraph), start + target_size)
            chunks.append(paragraph[start:end])
            if end >= len(paragraph):
                break
            start = max(start + 1, end - overlap)
        buffer = ""
    if buffer:
        chunks.append(buffer)
    return chunks


def _document_signature(path: Path) -> str:
    stat = path.stat()
    return f"{path.name}:{stat.st_size}:{stat.st_mtime_ns}"


class CourseKnowledgeBase:
    def __init__(self, corpus_dir: Path = CORPUS_DIR, cache_path: Path = CACHE_PATH):
        self.corpus_dir = corpus_dir
        self.cache_path = cache_path
        self._lock = threading.RLock()
        self._loaded = False
        self._chunks: list[KnowledgeChunk] = []
        self._pdf_signatures: dict[str, str] = {}
        self._term_frequencies: list[Counter[str]] = []
        self._document_frequencies: Counter[str] = Counter()
        self._average_length = 1.0

    def _catalog(self) -> list[Path]:
        if not self.corpus_dir.exists():
            return []
        return sorted(
            path
            for path in self.corpus_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in {".txt", ".pdf"}
        )

    def _load(self) -> None:
        with self._lock:
            if self._loaded:
                return
            files = self._catalog()
            signatures = {path.name: _document_signature(path) for path in files}
            cached: dict[str, Any] = {}
            try:
                cached = json.loads(self.cache_path.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                cached = {}

            cached_chunks = [
                item
                for item in (cached.get("chunks") or [])
                if isinstance(item, dict) and item.get("content")
            ]
            cache_matches_corpus = cached.get("signatures") == signatures
            portable_cache_only = not files and bool(cached_chunks)
            if cached.get("version") == CACHE_VERSION and (cache_matches_corpus or portable_cache_only):
                self._chunks = [
                    KnowledgeChunk(**item)
                    for item in cached_chunks
                ]
                self._pdf_signatures = dict(cached.get("pdfSignatures") or {})
            elif not files:
                # Portable source packages may intentionally ship the generated
                # index without the large raw corpus. Never replace that index
                # with an empty payload merely because the corpus is absent.
                self._chunks = []
                self._pdf_signatures = {}
            else:
                self._chunks = []
                self._pdf_signatures = {}
                for path in files:
                    if path.suffix.lower() == ".txt":
                        self._chunks.extend(self._extract_text_document(path))
                self._save(signatures)

            self._rebuild_statistics()
            self._loaded = True

    def _save(self, signatures: dict[str, str] | None = None) -> None:
        if signatures is None:
            signatures = {path.name: _document_signature(path) for path in self._catalog()}
        payload = {
            "version": CACHE_VERSION,
            "signatures": signatures,
            "pdfSignatures": self._pdf_signatures,
            "chunks": [asdict(chunk) for chunk in self._chunks],
        }
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.cache_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, self.cache_path)

    def _extract_text_document(self, path: Path) -> list[KnowledgeChunk]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        title = path.stem
        return [
            KnowledgeChunk(
                chunk_id=f"{path.name}#section-{index}",
                source=path.name,
                title=title,
                content=chunk,
                section=index,
            )
            for index, chunk in enumerate(_split_text(text), start=1)
        ]

    def _extract_pdf_document(self, path: Path) -> list[KnowledgeChunk]:
        chunks: list[KnowledgeChunk] = []
        try:
            import fitz

            with fitz.open(path) as document:
                for page_index, page in enumerate(document):
                    if page_index >= MAX_PDF_PAGES_PER_DOCUMENT:
                        break
                    page_text = _clean_text(page.get_text("text"))
                    for section_index, text in enumerate(_split_text(page_text), start=1):
                        chunks.append(
                            KnowledgeChunk(
                                chunk_id=f"{path.name}#page-{page_index + 1}-section-{section_index}",
                                source=path.name,
                                title=path.stem,
                                content=text,
                                page=page_index + 1,
                                section=section_index,
                            )
                        )
        except Exception:
            try:
                from pypdf import PdfReader

                reader = PdfReader(str(path))
                for page_index, page in enumerate(reader.pages[:MAX_PDF_PAGES_PER_DOCUMENT]):
                    for section_index, text in enumerate(_split_text(page.extract_text() or ""), start=1):
                        chunks.append(
                            KnowledgeChunk(
                                chunk_id=f"{path.name}#page-{page_index + 1}-section-{section_index}",
                                source=path.name,
                                title=path.stem,
                                content=text,
                                page=page_index + 1,
                                section=section_index,
                            )
                        )
            except Exception:
                return []
        return chunks

    def _ensure_matching_pdfs(self, query: str) -> None:
        query_tokens = set(_tokens(query))
        if not query_tokens:
            return
        candidates: list[tuple[int, Path]] = []
        for path in self._catalog():
            if path.suffix.lower() != ".pdf":
                continue
            signature = _document_signature(path)
            if self._pdf_signatures.get(path.name) == signature:
                continue
            filename_tokens = set(_tokens(path.stem))
            overlap = len(query_tokens & filename_tokens)
            if overlap:
                candidates.append((overlap, path))
        candidates.sort(key=lambda item: (item[0], -len(item[1].name)), reverse=True)
        if not candidates:
            return

        changed = False
        for _, path in candidates[:2]:
            extracted = self._extract_pdf_document(path)
            self._pdf_signatures[path.name] = _document_signature(path)
            if extracted:
                self._chunks.extend(extracted)
                changed = True
        if changed:
            self._rebuild_statistics()
        self._save()

    def _rebuild_statistics(self) -> None:
        self._term_frequencies = []
        self._document_frequencies = Counter()
        lengths: list[int] = []
        for chunk in self._chunks:
            frequencies = Counter(_tokens(f"{chunk.title} {chunk.content}"))
            self._term_frequencies.append(frequencies)
            lengths.append(sum(frequencies.values()))
            self._document_frequencies.update(frequencies.keys())
        self._average_length = sum(lengths) / len(lengths) if lengths else 1.0

    def retrieve(self, query: str, top_k: int = 6, max_context_chars: int = 9000) -> dict[str, Any]:
        self._load()
        with self._lock:
            self._ensure_matching_pdfs(query)
            query_terms = list(dict.fromkeys(_tokens(query)))
            total_documents = max(len(self._chunks), 1)
            scored: list[tuple[float, KnowledgeChunk]] = []
            k1 = 1.5
            b = 0.75
            for index, chunk in enumerate(self._chunks):
                frequencies = self._term_frequencies[index]
                length = max(sum(frequencies.values()), 1)
                score = 0.0
                for term in query_terms:
                    frequency = frequencies.get(term, 0)
                    if not frequency:
                        continue
                    document_frequency = self._document_frequencies.get(term, 0)
                    inverse_frequency = math.log(1 + (total_documents - document_frequency + 0.5) / (document_frequency + 0.5))
                    score += inverse_frequency * (
                        frequency * (k1 + 1)
                        / (frequency + k1 * (1 - b + b * length / self._average_length))
                    )
                if score > 0:
                    scored.append((score, chunk))
            scored.sort(key=lambda item: item[0], reverse=True)

            hits: list[dict[str, Any]] = []
            used_sources: Counter[str] = Counter()
            context_parts: list[str] = []
            context_length = 0
            for score, chunk in scored:
                if len(hits) >= max(1, min(int(top_k), 12)):
                    break
                if used_sources[chunk.source] >= 2:
                    continue
                citation_id = f"KB{len(hits) + 1}"
                locator = f"第 {chunk.page} 页" if chunk.page else f"第 {chunk.section or 1} 节"
                excerpt = chunk.content[:1600]
                block = f"[{citation_id}] {chunk.title}（{chunk.source}，{locator}）\n{excerpt}"
                if context_parts and context_length + len(block) > max_context_chars:
                    break
                used_sources[chunk.source] += 1
                context_parts.append(block)
                context_length += len(block)
                hits.append(
                    {
                        "citationId": citation_id,
                        "source": chunk.source,
                        "title": chunk.title,
                        "page": chunk.page,
                        "section": chunk.section,
                        "score": round(score, 4),
                        "excerpt": excerpt,
                    }
                )

            return {
                "query": query,
                "grounded": bool(hits),
                "context": "\n\n".join(context_parts),
                "hits": hits,
                "citations": [
                    {
                        "id": item["citationId"],
                        "title": item["title"],
                        "source": item["source"],
                        "page": item["page"],
                        "section": item["section"],
                    }
                    for item in hits
                ],
                "stats": {
                    "corpusFiles": len(self._catalog()),
                    "indexedChunks": len(self._chunks),
                    "matchedChunks": len(hits),
                },
            }


_knowledge_base = CourseKnowledgeBase()

RETRIEVAL_CACHE_VERSION = "hybrid-retrieval-cache-v1"
RETRIEVAL_CACHE_TTL_SECONDS = max(30, int(os.environ.get("KNOWLEDGE_RETRIEVAL_CACHE_TTL", "600")))
RETRIEVAL_CACHE_MAX_ENTRIES = max(16, int(os.environ.get("KNOWLEDGE_RETRIEVAL_CACHE_SIZE", "256")))
_retrieval_cache_lock = threading.RLock()
_retrieval_cache: OrderedDict[str, tuple[float, dict[str, Any]]] = OrderedDict()


def clear_retrieval_cache() -> None:
    with _retrieval_cache_lock:
        _retrieval_cache.clear()


def _file_revision(paths: list[Path]) -> str:
    parts = [RETRIEVAL_CACHE_VERSION, str(CACHE_VERSION)]
    for path in paths:
        try:
            stat = path.stat()
            parts.append(f"{path.name}:{stat.st_size}:{stat.st_mtime_ns}")
        except OSError:
            parts.append(f"{path.name}:missing")
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:20]


def _public_knowledge_revision() -> str:
    data_dir = Path(__file__).resolve().parent / "data"
    return _file_revision(
        [
            CACHE_PATH,
            data_dir / "tcm_qa_pairs.json",
            data_dir / "tcm_graph_index.json",
            data_dir / "tcm_hybrid_corpus.db.gz",
            data_dir / "tcm_hybrid_corpus_manifest.json",
        ]
    )


def _private_knowledge_revision(
    user_id: int | None,
    db_path: str | Path | None,
    collection_id: int | None,
    include_private: bool,
) -> str:
    if not include_private or user_id is None:
        return "private-disabled"
    # User id is always part of the revision, including when no collection is
    # active, so cached private evidence can never cross account boundaries.
    prefix = f"user:{int(user_id)}"
    if db_path is None:
        return f"{prefix}:runtime-resolved"
    resolved_path = Path(db_path)
    if not resolved_path.exists():
        return f"{prefix}:db-missing"
    try:
        conn = sqlite3.connect(resolved_path)
        conn.row_factory = sqlite3.Row
        try:
            resolved_collection_id = int(collection_id or 0)
            if not resolved_collection_id:
                state = conn.execute(
                    "SELECT active_collection_id FROM user_private_knowledge_state WHERE user_id = ?",
                    (int(user_id),),
                ).fetchone()
                resolved_collection_id = int(state["active_collection_id"] or 0) if state else 0
            if not resolved_collection_id:
                return f"{prefix}:none"
            row = conn.execute(
                """
                SELECT k.updated_at,
                       COUNT(DISTINCT d.id) AS document_count,
                       COUNT(c.id) AS chunk_count,
                       COALESCE(MAX(d.updated_at), '') AS document_revision,
                       COALESCE(MAX(c.id), 0) AS max_chunk_id
                FROM private_knowledge_collections AS k
                LEFT JOIN private_knowledge_documents AS d
                  ON d.collection_id = k.id AND d.user_id = k.user_id
                LEFT JOIN private_knowledge_chunks AS c
                  ON c.collection_id = k.id AND c.user_id = k.user_id AND c.document_id = d.id
                WHERE k.id = ? AND k.user_id = ? AND k.archived = 0
                GROUP BY k.id
                """,
                (resolved_collection_id, int(user_id)),
            ).fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        return f"{prefix}:db-unavailable"
    if not row:
        return f"{prefix}:collection:{resolved_collection_id}:missing"
    return (
        f"{prefix}:collection:{resolved_collection_id}:{row['updated_at']}:"
        f"{row['document_revision']}:{row['document_count']}:{row['chunk_count']}:{row['max_chunk_id']}"
    )


def _retrieval_signature(plan: dict[str, Any]) -> str:
    entities = sorted(str(item).strip().lower() for item in (plan.get("entities") or []))
    aspects = sorted(str(item).strip().lower() for item in (plan.get("aspects") or []))
    # For well-formed domain requests, entities + aspects + intent are the
    # semantic signature. Task wording such as "please", "generate PPT" or a
    # punctuation change should not force an identical retrieval to run again.
    fallback_keywords = [] if entities or aspects else sorted(
        str(item).strip().lower() for item in (plan.get("keywords") or [])
    )
    normalized = {
        "version": plan.get("version") or "",
        "intent": plan.get("intent") or "concept",
        "entities": entities,
        "aspects": aspects,
        "keywords": fallback_keywords,
    }
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _retrieval_cache_key(
    plan: dict[str, Any],
    *,
    top_k: int,
    max_context_chars: int,
    public_revision: str,
    private_revision: str,
) -> str:
    raw = "|".join(
        [
            _retrieval_signature(plan),
            str(int(top_k)),
            str(int(max_context_chars)),
            public_revision,
            private_revision,
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _cached_retrieval(key: str) -> tuple[dict[str, Any] | None, float]:
    now = time.monotonic()
    with _retrieval_cache_lock:
        entry = _retrieval_cache.get(key)
        if entry is None:
            return None, 0.0
        created_at, result = entry
        age = max(0.0, now - created_at)
        if age > RETRIEVAL_CACHE_TTL_SECONDS:
            _retrieval_cache.pop(key, None)
            return None, age
        _retrieval_cache.move_to_end(key)
        return copy.deepcopy(result), age


def _store_cached_retrieval(key: str, result: dict[str, Any]) -> None:
    with _retrieval_cache_lock:
        _retrieval_cache[key] = (time.monotonic(), copy.deepcopy(result))
        _retrieval_cache.move_to_end(key)
        while len(_retrieval_cache) > RETRIEVAL_CACHE_MAX_ENTRIES:
            _retrieval_cache.popitem(last=False)


def _knowledge_hit_block(hit: dict[str, Any]) -> str:
    citation_id = str(hit.get("citationId") or "KB")
    locator = f"第 {hit['page']} 页" if hit.get("page") else f"第 {hit.get('section') or 1} 节"
    private_label = "[我的知识库] " if hit.get("scope") == "private" else ""
    collection = f"；知识库：{hit.get('collectionName')}" if hit.get("collectionName") else ""
    return (
        f"[{citation_id}]{private_label}{hit.get('title') or hit.get('source') or '课程资料'}"
        f"（{hit.get('source') or '未知来源'}，{locator}{collection}）\n"
        f"{str(hit.get('excerpt') or '')[:1600]}"
    )


def _merge_knowledge_results(
    built_in: dict[str, Any],
    private: dict[str, Any],
    *,
    top_k: int,
    max_context_chars: int,
) -> dict[str, Any]:
    built_in_hits = [{**item, "scope": "built-in", "sourceType": "course-corpus"} for item in built_in.get("hits") or []]
    private_hits = [dict(item) for item in private.get("hits") or []]
    limit = max(1, min(int(top_k), 12))
    private_quota = min(len(private_hits), max(1, (limit + 1) // 2)) if private_hits else 0
    selected = private_hits[:private_quota] + built_in_hits[: max(0, limit - private_quota)]
    if len(selected) < limit:
        selected.extend(private_hits[private_quota : private_quota + (limit - len(selected))])
    if len(selected) < limit:
        selected.extend(built_in_hits[len([item for item in selected if item.get("scope") == "built-in"]) : limit])
    selected = selected[:limit]

    context_parts: list[str] = []
    context_length = 0
    for hit in selected:
        block = _knowledge_hit_block(hit)
        if context_parts and context_length + len(block) > max_context_chars:
            break
        context_parts.append(block)
        context_length += len(block)
    selected = selected[: len(context_parts)]
    citations = []
    for hit in selected:
        citation = {
            "id": hit.get("citationId"),
            "scope": hit.get("scope"),
            "sourceType": hit.get("sourceType"),
            "title": hit.get("title"),
            "source": hit.get("source"),
            "page": hit.get("page"),
            "section": hit.get("section"),
        }
        for key in ("collectionId", "collectionName", "documentId"):
            if hit.get(key) is not None:
                citation[key] = hit.get(key)
        citations.append(citation)
    return {
        "query": built_in.get("query") or private.get("query") or "",
        "grounded": bool(selected),
        "context": "\n\n".join(context_parts),
        "hits": selected,
        "citations": citations,
        "activePrivateCollection": private.get("activeCollection"),
        "stats": {
            **(built_in.get("stats") or {}),
            "matchedChunks": len(selected),
            "builtInMatchedChunks": len([item for item in selected if item.get("scope") == "built-in"]),
            "privateMatchedChunks": len([item for item in selected if item.get("scope") == "private"]),
            "privateCollections": int((private.get("stats") or {}).get("collections") or 0),
            "privateDocuments": int((private.get("stats") or {}).get("documents") or 0),
            "privateIndexedChunks": int((private.get("stats") or {}).get("indexedChunks") or 0),
        },
    }


def _retrieve_course_knowledge_once(
    query: str,
    top_k: int = 6,
    max_context_chars: int = 9000,
    *,
    user_id: int | None = None,
    db_path: str | Path | None = None,
    private_collection_id: int | None = None,
    include_private: bool = True,
) -> dict[str, Any]:
    built_in = _knowledge_base.retrieve(query, top_k=top_k, max_context_chars=max_context_chars)
    private = (
        retrieve_private_knowledge(
            query,
            user_id=user_id,
            db_path=db_path,
            collection_id=private_collection_id,
            top_k=top_k,
            max_context_chars=max_context_chars,
        )
        if include_private
        else {"query": query, "hits": [], "stats": {}}
    )
    document_result = _merge_knowledge_results(
        built_in,
        private,
        top_k=top_k,
        max_context_chars=max_context_chars,
    )
    return route_hybrid_knowledge(
        query,
        document_result,
        top_k=top_k,
        max_context_chars=max_context_chars,
    )


def _retrieval_hit_key(hit: dict[str, Any]) -> tuple[str, ...]:
    route = str(hit.get("route") or "document")
    if route == "qa":
        return (route, str(hit.get("qaId") or hit.get("dataset") or ""), str(hit.get("title") or ""))
    if route == "graph":
        return (route, str(hit.get("nodeId") or ""), str(hit.get("path") or hit.get("title") or ""))
    return (
        route,
        str(hit.get("scope") or "built-in"),
        str(hit.get("documentId") or hit.get("chunkId") or hit.get("source") or ""),
        str(hit.get("page") or hit.get("section") or ""),
        str(hit.get("title") or ""),
    )


def _retrieval_hit_score(hit: dict[str, Any]) -> float:
    try:
        base = float(hit.get("fusionScore") or hit.get("score") or 0)
    except (TypeError, ValueError):
        base = 0.0
    query_count = len(hit.get("matchedSubQueries") or [])
    return base + max(0, query_count - 1) * 0.04


def _agent_relevance_score(hit: dict[str, Any], plan: dict[str, Any]) -> float:
    text = re.sub(
        r"\s+",
        "",
        f"{hit.get('title') or ''}{hit.get('path') or ''}{hit.get('excerpt') or ''}",
    ).lower()
    entities = [
        re.sub(r"\s+", "", str(item or "")).lower()
        for item in (plan.get("entities") or [])
        if len(re.sub(r"\s+", "", str(item or ""))) >= 2
    ]
    aspects = [
        re.sub(r"\s+", "", str(item or "")).lower()
        for item in (plan.get("aspects") or [])
        if len(re.sub(r"\s+", "", str(item or ""))) >= 2
    ]
    entity_matches = sum(1 for item in entities if item in text)
    aspect_matches = sum(1 for item in aspects if item in text)
    score = min(0.16, aspect_matches * 0.04)
    if entities:
        score += 0.8 * (entity_matches / len(entities))
        if entity_matches == 0:
            score -= 0.7
    return score


def _entity_match_count(hit: dict[str, Any], plan: dict[str, Any]) -> int:
    text = re.sub(
        r"\s+",
        "",
        f"{hit.get('title') or ''}{hit.get('path') or ''}{hit.get('excerpt') or ''}",
    ).lower()
    return sum(
        1
        for raw in (plan.get("entities") or [])
        if len(re.sub(r"\s+", "", str(raw or ""))) >= 2
        and re.sub(r"\s+", "", str(raw or "")).lower() in text
    )


def _qa_matches_target_entity(hit: dict[str, Any], plan: dict[str, Any]) -> bool:
    if str(hit.get("route") or "") != "qa":
        return True
    entities = [
        re.sub(r"\s+", "", str(item or ""))
        for item in (plan.get("entities") or [])
        if len(re.sub(r"\s+", "", str(item or ""))) >= 2
    ]
    if not entities:
        return True
    title = re.sub(r"\s+", "", str(hit.get("title") or ""))
    for entity in entities:
        if re.search(rf"(?:^|[生炙制]){re.escape(entity)}(?:的|是|有何|有哪些|如何|主治|功效|性味|归经|来源|性状)", title):
            return True
    return False


def _assign_citation_ids(hits: list[dict[str, Any]]) -> None:
    counters: Counter[str] = Counter()
    for hit in hits:
        route = str(hit.get("route") or "document")
        if route == "qa":
            prefix = "QA"
        elif route == "graph":
            prefix = "KG"
        elif hit.get("scope") == "private":
            prefix = "PKB"
        else:
            prefix = "KB"
        counters[prefix] += 1
        hit["citationId"] = f"{prefix}{counters[prefix]}"


def _agent_hit_block(hit: dict[str, Any]) -> str:
    citation_id = str(hit.get("citationId") or "KB")
    route = str(hit.get("route") or "document")
    excerpt = str(hit.get("excerpt") or "")[:1600]
    if route == "qa":
        return f"[{citation_id}][QA] {hit.get('title') or '课程问答'}\n{excerpt}"
    if route == "graph":
        path = hit.get("path") or hit.get("title") or "中医知识节点"
        return f"[{citation_id}][知识图谱] {path}\n{excerpt}"
    locator = f"第 {hit['page']} 页" if hit.get("page") else f"第 {hit.get('section') or 1} 节"
    private_label = "[我的知识库] " if hit.get("scope") == "private" else ""
    return (
        f"[{citation_id}]{private_label}{hit.get('title') or hit.get('source') or '课程资料'}"
        f"（{hit.get('source') or '未知来源'}，{locator}）\n{excerpt}"
    )


def _merge_agent_retrievals(
    query: str,
    plan: dict[str, Any],
    runs: list[tuple[dict[str, Any], dict[str, Any]]],
    *,
    top_k: int,
    max_context_chars: int,
) -> dict[str, Any]:
    merged: dict[tuple[str, ...], dict[str, Any]] = {}
    run_summaries: list[dict[str, Any]] = []
    for subquery, result in runs:
        subquery_id = str(subquery.get("id") or "SQ")
        subquery_text = str(subquery.get("query") or "")
        route_counts: Counter[str] = Counter()
        for raw_hit in result.get("hits") or []:
            if not isinstance(raw_hit, dict):
                continue
            hit = dict(raw_hit)
            route_counts[str(hit.get("route") or "document")] += 1
            key = _retrieval_hit_key(hit)
            existing = merged.get(key)
            if existing is None:
                hit["matchedSubQueries"] = [subquery_id]
                hit["matchedQueries"] = [subquery_text]
                merged[key] = hit
                continue
            existing["matchedSubQueries"] = _dedupe_strings(
                [*(existing.get("matchedSubQueries") or []), subquery_id]
            )
            existing["matchedQueries"] = _dedupe_strings(
                [*(existing.get("matchedQueries") or []), subquery_text]
            )
            if _retrieval_hit_score(hit) > _retrieval_hit_score(existing):
                for key_name, value in hit.items():
                    if key_name not in {"matchedSubQueries", "matchedQueries", "citationId"}:
                        existing[key_name] = value
        run_summaries.append(
            {
                "id": subquery_id,
                "query": subquery_text,
                "matched": len(result.get("hits") or []),
                "routes": dict(route_counts),
            }
        )

    eligible = [item for item in merged.values() if _qa_matches_target_entity(item, plan)]
    if plan.get("entities"):
        entity_routes = {
            str(item.get("route") or "document")
            for item in eligible
            if _entity_match_count(item, plan) > 0
        }
        eligible = [
            item
            for item in eligible
            if str(item.get("route") or "document") not in entity_routes
            or _entity_match_count(item, plan) > 0
        ]
    ranked = sorted(
        eligible,
        key=lambda item: _retrieval_hit_score(item) + _agent_relevance_score(item, plan),
        reverse=True,
    )
    limit = max(1, min(int(top_k), 12))
    selected: list[dict[str, Any]] = []
    if limit >= 3:
        for route in ("qa", "document", "graph"):
            candidate = next((item for item in ranked if str(item.get("route") or "document") == route), None)
            if candidate is not None and candidate not in selected:
                selected.append(candidate)
    for raw_entity in plan.get("entities") or []:
        entity = re.sub(r"\s+", "", str(raw_entity or "")).lower()
        if len(entity) < 2:
            continue
        document_candidates = [
            item
            for item in ranked
            if str(item.get("route") or "document") == "document"
            and entity
            in re.sub(
                r"\s+",
                "",
                f"{item.get('title') or ''}{item.get('excerpt') or ''}",
            ).lower()
        ]
        candidate = next(
            (
                item
                for item in document_candidates
                if re.sub(r"\s+", "", str(item.get("title") or "")).lower() == entity
            ),
            document_candidates[0] if document_candidates else None,
        )
        if candidate is not None and candidate not in selected:
            selected.append(candidate)
    for candidate in ranked:
        if candidate not in selected:
            selected.append(candidate)
        if len(selected) >= limit:
            break
    selected = selected[:limit]
    _assign_citation_ids(selected)

    accepted: list[dict[str, Any]] = []
    context_parts: list[str] = []
    context_length = 0
    for hit in selected:
        block = _agent_hit_block(hit)
        if context_parts and context_length + len(block) > max_context_chars:
            continue
        accepted.append(hit)
        context_parts.append(block)
        context_length += len(block)

    route_counts = Counter(str(item.get("route") or "document") for item in accepted)
    evidence_routes = [route for route in ("qa", "document", "graph") if route_counts[route]]
    agreement_scores = [
        float((((result.get("routing") or {}).get("crossValidation") or {}).get("agreementScore") or 0))
        for _, result in runs
    ]
    agreement_score = max(agreement_scores, default=0.0)
    corroborated = len(evidence_routes) >= 2 and agreement_score >= 0.015
    verification = {
        "status": "corroborated" if corroborated else ("low_agreement" if len(evidence_routes) >= 2 else "single_source" if accepted else "insufficient"),
        "evidenceRoutes": evidence_routes,
        "agreementScore": round(agreement_score, 4),
        "decision": "allow_grounded_generation" if corroborated else "mark_for_verification",
        "verificationRequired": not corroborated,
        "rule": "至少两类独立知识源命中且语义一致度达标后允许按证据生成；重复来源、低一致度、单源或无命中内容必须标记为需进一步核验。",
    }

    citations: list[dict[str, Any]] = []
    citation_keys = (
        "scope", "sourceType", "route", "title", "source", "page", "section",
        "collectionId", "collectionName", "documentId", "qaId", "nodeId", "chunkId",
        "path", "domain", "dataset", "sourceRevision", "sourceLicense", "safety",
        "score", "fusionScore", "excerpt", "matchedSubQueries", "matchedQueries",
    )
    for hit in accepted:
        citation = {"id": hit.get("citationId")}
        for key in citation_keys:
            if hit.get(key) is not None:
                citation[key] = hit.get(key)
        citations.append(citation)

    stats_list = [result.get("stats") or {} for _, result in runs]
    stats = {
        key: max((int(item.get(key) or 0) for item in stats_list), default=0)
        for key in (
            "corpusFiles", "indexedChunks", "builtInMatchedChunks", "privateMatchedChunks",
            "privateCollections", "privateDocuments", "privateIndexedChunks", "qaPairs",
            "documentCorpusChunks", "graphNodes",
        )
    }
    stats.update(
        {
            "retrievalStrategy": "agentic-multi-query-hybrid-v1",
            "subQueryCount": len(runs),
            "qaMatched": route_counts["qa"],
            "documentMatched": route_counts["document"],
            "graphMatched": route_counts["graph"],
            "matchedChunks": len(accepted),
        }
    )
    active_collection = next(
        (result.get("activePrivateCollection") for _, result in runs if result.get("activePrivateCollection") is not None),
        None,
    )
    return {
        "query": query,
        "grounded": bool(accepted),
        "context": "\n\n".join(context_parts),
        "hits": accepted,
        "chunks": accepted,
        "citations": citations,
        "retrievalAgent": plan,
        "activePrivateCollection": active_collection,
        "routing": {
            "strategy": "hybrid-routing-v1",
            "mode": "agentic-multi-query",
            "queryType": plan.get("intent") or "concept",
            "routes": [
                {"id": "qa", "label": "QA 精确问答", "matched": route_counts["qa"]},
                {"id": "document", "label": "文档切块", "matched": route_counts["document"]},
                {"id": "graph", "label": "知识图谱", "matched": route_counts["graph"]},
            ],
            "subQueryRuns": run_summaries,
            "crossValidation": verification,
        },
        "stats": stats,
    }


def _dedupe_strings(values: list[object]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = str(raw or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def retrieve_course_knowledge(
    query: str,
    top_k: int = 6,
    max_context_chars: int = 9000,
    *,
    user_id: int | None = None,
    db_path: str | Path | None = None,
    private_collection_id: int | None = None,
    include_private: bool = True,
) -> dict[str, Any]:
    plan = plan_knowledge_retrieval(query, max_subqueries=4)
    public_revision = _public_knowledge_revision()
    private_revision = _private_knowledge_revision(
        user_id,
        db_path,
        private_collection_id,
        include_private,
    )
    cache_key = _retrieval_cache_key(
        plan,
        top_k=top_k,
        max_context_chars=max_context_chars,
        public_revision=public_revision,
        private_revision=private_revision,
    )
    cached, cache_age = _cached_retrieval(cache_key)
    if cached is not None:
        cached["query"] = query
        if isinstance(cached.get("retrievalAgent"), dict):
            cached["retrievalAgent"]["originalQuery"] = query
        cached["cache"] = {
            "hit": True,
            "key": cache_key[:16],
            "ageSeconds": round(cache_age, 3),
            "ttlSeconds": RETRIEVAL_CACHE_TTL_SECONDS,
            "publicRevision": public_revision,
            "privateRevision": private_revision,
        }
        return cached
    subqueries = plan.get("subQueries") or [{"id": "SQ1", "query": query}]
    runs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    per_query_top_k = 12
    for subquery in subqueries:
        subquery_text = str(subquery.get("query") or "").strip()
        if not subquery_text:
            continue
        result = _retrieve_course_knowledge_once(
            subquery_text,
            top_k=per_query_top_k,
            max_context_chars=max_context_chars,
            user_id=user_id,
            db_path=db_path,
            private_collection_id=private_collection_id,
            include_private=include_private,
        )
        runs.append((subquery, result))
    result = _merge_agent_retrievals(
        query,
        plan,
        runs,
        top_k=top_k,
        max_context_chars=max_context_chars,
    )
    _store_cached_retrieval(cache_key, result)
    result["cache"] = {
        "hit": False,
        "key": cache_key[:16],
        "ageSeconds": 0.0,
        "ttlSeconds": RETRIEVAL_CACHE_TTL_SECONDS,
        "publicRevision": public_revision,
        "privateRevision": private_revision,
    }
    return result


def grounded_prompt_block(
    query: str,
    top_k: int = 6,
    max_context_chars: int = 9000,
    *,
    user_id: int | None = None,
    db_path: str | Path | None = None,
    private_collection_id: int | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    result = retrieve_course_knowledge(
        query,
        top_k=top_k,
        max_context_chars=max_context_chars,
        user_id=user_id,
        db_path=db_path,
        private_collection_id=private_collection_id,
    )
    if not result["grounded"]:
        return (
            "课程知识库未检索到直接相关内容。不要编造教材事实；不确定的内容必须明确标注为待核验。",
            [],
        )
    verification = ((result.get("routing") or {}).get("crossValidation") or {})
    verification_note = (
        f"混合路由审核：{verification.get('status') or 'unknown'}；"
        f"决策：{verification.get('decision') or 'mark_for_verification'}；"
        f"证据路由：{', '.join(verification.get('evidenceRoutes') or []) or '无'}。"
    )
    retrieval_agent = result.get("retrievalAgent") or {}
    keywords = "、".join(retrieval_agent.get("keywords") or []) or "未提取"
    subqueries = "；".join(
        str(item.get("query") or "")
        for item in (retrieval_agent.get("subQueries") or [])
        if isinstance(item, dict) and str(item.get("query") or "").strip()
    ) or query
    retrieval_note = f"知识检索智能体关键词：{keywords}。执行子查询：{subqueries}。"
    prompt = (
        "以下内容先由知识检索智能体拆分关键词和子查询，再由混合知识路由器从结构化 QA、"
        "课程文档切块、当前用户私有文档和中医知识图谱中检索，"
        "并完成多源证据交叉验证。涉及定义、辨证依据、方药、步骤、参数和结论时必须优先依据这些证据；"
        "无法由证据支持或仅有单一来源支持的事实要明确标注为“需进一步核验”。"
        "输出中使用 [QA1] 标注 QA 对、[KB1] 标注文档、[PKB1] 标注用户私有资料、[KG1] 标注图谱节点。\n"
        f"{retrieval_note}\n{verification_note}\n\n"
        f"{result['context']}"
    )
    return prompt, result["citations"]
