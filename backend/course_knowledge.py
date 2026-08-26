"""Local course knowledge base with traceable lexical retrieval.

The primary course corpus lives in ``rag文档``. Text lessons are indexed eagerly;
PDFs are catalogued and extracted on demand when their filenames match a query.
This keeps startup fast while still making the complete document set available.
"""

from __future__ import annotations

import json
import math
import os
import re
import threading
from collections import Counter
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
    prompt = (
        "以下内容由混合知识路由器从结构化 QA、课程文档切块、当前用户私有文档和中医知识图谱中检索，"
        "并完成多源证据交叉验证。涉及定义、辨证依据、方药、步骤、参数和结论时必须优先依据这些证据；"
        "无法由证据支持或仅有单一来源支持的事实要明确标注为“需进一步核验”。"
        "输出中使用 [QA1] 标注 QA 对、[KB1] 标注文档、[PKB1] 标注用户私有资料、[KG1] 标注图谱节点。\n"
        f"{verification_note}\n\n"
        f"{result['context']}"
    )
    return prompt, result["citations"]
