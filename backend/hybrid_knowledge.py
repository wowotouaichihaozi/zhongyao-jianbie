"""Hybrid QA, document, and graph retrieval with traceable evidence routing."""

from __future__ import annotations

import json
import gzip
import hashlib
import math
import os
import re
import shutil
import sqlite3
import threading
import zlib
from itertools import combinations
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parent / "data"
QA_PATH = DATA_DIR / "tcm_qa_pairs.json"
GRAPH_PATH = DATA_DIR / "tcm_graph_index.json"
CORPUS_PATH = Path(
    os.environ.get("TCM_HYBRID_CORPUS_PATH")
    or (DATA_DIR / "tcm_hybrid_corpus.db.gz")
).resolve()
CORPUS_MANIFEST_PATH = DATA_DIR / "tcm_hybrid_corpus_manifest.json"
CORPUS_CACHE_DIR = DATA_DIR / "extract_cache"
ROUTER_VERSION = "hybrid-routing-v1"


def _clean_text(value: object) -> str:
    text = str(value or "").replace("\x00", " ").lower()
    return re.sub(r"\s+", " ", text).strip()


def _compact_text(value: object) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", _clean_text(value))


def _tokens(value: object) -> list[str]:
    text = _clean_text(value)
    tokens = re.findall(r"[a-z][a-z0-9_+\-]{1,}|[0-9]+(?:\.[0-9]+)?", text)
    for sequence in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        tokens.extend(sequence[index : index + 2] for index in range(len(sequence) - 1))
        if len(sequence) <= 12:
            tokens.append(sequence)
    return list(dict.fromkeys(tokens))


def _similarity(query: object, candidate: object) -> float:
    query_tokens = set(_tokens(query))
    candidate_tokens = set(_tokens(candidate))
    if not query_tokens or not candidate_tokens:
        return 0.0
    overlap = query_tokens & candidate_tokens
    coverage = len(overlap) / len(query_tokens)
    jaccard = len(overlap) / len(query_tokens | candidate_tokens)
    compact_query = _compact_text(query)
    compact_candidate = _compact_text(candidate)
    phrase_bonus = 0.0
    if len(compact_query) >= 4 and (
        compact_query in compact_candidate or compact_candidate in compact_query
    ):
        phrase_bonus = 0.24
    return min(1.0, coverage * 0.68 + jaccard * 0.22 + phrase_bonus)


def _pairwise_agreement(hits: list[dict[str, Any]]) -> float:
    representatives: dict[str, dict[str, Any]] = {}
    for hit in hits:
        representatives.setdefault(str(hit.get("route") or "document"), hit)
    if len(representatives) < 2:
        return 0.0
    scores: list[float] = []
    for left, right in combinations(representatives.values(), 2):
        left_tokens = set(_tokens(f"{left.get('title', '')} {left.get('excerpt', '')}"))
        right_tokens = set(_tokens(f"{right.get('title', '')} {right.get('excerpt', '')}"))
        if left_tokens and right_tokens:
            scores.append(len(left_tokens & right_tokens) / len(left_tokens | right_tokens))
    return round(sum(scores) / len(scores), 4) if scores else 0.0


def _fts_query(value: object) -> str:
    candidates = [token for token in _tokens(value) if 2 <= len(token) <= 32]
    candidates.sort(key=lambda token: (len(token), token), reverse=True)
    selected = list(dict.fromkeys(candidates))[:16]
    return " OR ".join(f'"{token.replace(chr(34), chr(34) * 2)}"' for token in selected)


def _focus_phrases(value: object) -> list[str]:
    compact = _compact_text(value)
    if not compact:
        return []
    separators = (
        "有什么关系", "有何关系", "主要功效", "核心知识", "注意事项",
        "适用于什么证", "指什么", "是什么", "有哪些", "为什么",
        "如何", "怎么", "中的", "的", "与", "和", "及",
    )
    segmented = compact
    for separator in separators:
        segmented = segmented.replace(separator, "|")
    generic_pieces = {
        "组成", "处方组成", "功效", "功用", "主要作用", "作用", "功能",
        "性味", "归经", "性味归经", "主治", "适应证", "用法", "用量",
        "用法用量", "炮制方法", "注意事项", "关系", "区别", "含义",
    }
    prompt_prefixes = ("请问", "请介绍", "介绍一下", "请简述", "简述", "分析", "比较")
    phrases: list[str] = []
    for raw_piece in segmented.split("|"):
        piece = raw_piece
        for prefix in prompt_prefixes:
            if piece.startswith(prefix):
                piece = piece[len(prefix):]
                break
        if not 2 <= len(piece) <= 16 or piece in generic_pieces:
            continue
        phrases.append(piece)
    return list(dict.fromkeys(phrases))


def _focused_fts_query(value: object) -> str:
    phrases = _focus_phrases(value)
    if not phrases:
        return ""
    focus = phrases[0][:12]
    focus_tokens = [token for token in _tokens(focus) if len(token) == 2]
    focus_tokens = list(dict.fromkeys(focus_tokens))[:8]
    return " AND ".join(f'"{token}"' for token in focus_tokens)


def _focus_relevance(query: object, candidate: object) -> float:
    candidate_text = _compact_text(candidate)
    phrases = _focus_phrases(query)
    if not candidate_text or not phrases:
        return 0.0
    primary = phrases[0]
    exact = 1.0 if primary in candidate_text else 0.0
    return max(exact, _similarity(primary, candidate_text))


def _attribute_relevance(query: object, candidate: object) -> float:
    query_text = _compact_text(query)
    candidate_text = _compact_text(candidate)
    attributes = (
        "组成", "处方", "功效", "功用", "功能", "性味", "归经", "主治",
        "用法", "用量", "炮制", "注意事项", "病机", "证候", "关系", "区别",
    )
    requested = [attribute for attribute in attributes if attribute in query_text]
    if not requested:
        return 0.0
    return sum(attribute in candidate_text for attribute in requested) / len(requested)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _decompress_text(value: object) -> str:
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, bytes):
        try:
            return zlib.decompress(value).decode("utf-8")
        except (zlib.error, UnicodeDecodeError):
            return value.decode("utf-8", errors="replace")
    return str(value or "")


def _prepare_corpus_database(path: Path) -> Path | None:
    if not path.is_file():
        return None
    if path.suffix.lower() != ".gz":
        return path
    compressed_hash = _sha256(path)
    expected_uncompressed_hash = ""
    expected_uncompressed_bytes = 0
    try:
        manifest = json.loads(CORPUS_MANIFEST_PATH.read_text(encoding="utf-8"))
        database = manifest.get("database") or {}
        if str(database.get("sha256") or "").upper() == compressed_hash:
            expected_uncompressed_hash = str(database.get("uncompressedSha256") or "").upper()
            expected_uncompressed_bytes = int(database.get("uncompressedBytes") or 0)
    except (OSError, ValueError, TypeError):
        pass
    CORPUS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    target = CORPUS_CACHE_DIR / f"tcm_hybrid_corpus-{compressed_hash[:16]}.db"
    if target.is_file() and (
        not expected_uncompressed_bytes or target.stat().st_size == expected_uncompressed_bytes
    ):
        return target
    temporary = target.with_name(f"{target.name}.tmp-{os.getpid()}")
    with gzip.open(path, "rb") as source, temporary.open("wb") as destination:
        shutil.copyfileobj(source, destination, length=1024 * 1024)
    if expected_uncompressed_bytes and temporary.stat().st_size != expected_uncompressed_bytes:
        raise RuntimeError("Hybrid corpus decompressed size does not match its manifest")
    if expected_uncompressed_hash and _sha256(temporary) != expected_uncompressed_hash:
        raise RuntimeError("Hybrid corpus decompressed checksum does not match its manifest")
    os.replace(temporary, target)
    return target


class HybridKnowledgeRouter:
    def __init__(
        self,
        qa_path: Path = QA_PATH,
        graph_path: Path = GRAPH_PATH,
        corpus_path: Path | None = CORPUS_PATH,
    ):
        self.qa_path = qa_path
        self.graph_path = graph_path
        self.corpus_path = corpus_path
        self._lock = threading.RLock()
        self._loaded = False
        self._qa_pairs: list[dict[str, Any]] = []
        self._graph_nodes: list[dict[str, Any]] = []
        self._corpus_database: Path | None = None
        self._corpus_stats = {"qaPairs": 0, "documentChunks": 0}

    def _load(self) -> None:
        with self._lock:
            if self._loaded:
                return
            try:
                qa_payload = json.loads(self.qa_path.read_text(encoding="utf-8"))
                self._qa_pairs = [
                    item for item in qa_payload.get("qaPairs", [])
                    if isinstance(item, dict) and item.get("question") and item.get("answer")
                ]
            except (OSError, ValueError, TypeError):
                self._qa_pairs = []
            try:
                graph_payload = json.loads(self.graph_path.read_text(encoding="utf-8"))
                self._graph_nodes = [
                    item for item in graph_payload.get("nodes", [])
                    if isinstance(item, dict) and item.get("title")
                ]
            except (OSError, ValueError, TypeError):
                self._graph_nodes = []
            try:
                self._corpus_database = (
                    _prepare_corpus_database(self.corpus_path)
                    if self.corpus_path is not None
                    else None
                )
                if self._corpus_database:
                    with sqlite3.connect(f"file:{self._corpus_database.as_posix()}?mode=ro", uri=True) as conn:
                        rows = conn.execute("SELECT key, value FROM metadata").fetchall()
                    metadata = {str(key): str(value) for key, value in rows}
                    self._corpus_stats = {
                        "qaPairs": int(metadata.get("qaPairs") or 0),
                        "documentChunks": int(metadata.get("documentChunks") or 0),
                    }
            except (OSError, ValueError, sqlite3.Error, RuntimeError):
                self._corpus_database = None
                self._corpus_stats = {"qaPairs": 0, "documentChunks": 0}
            self._loaded = True

    def _corpus_qa_hits(self, query: str, limit: int = 24) -> list[dict[str, Any]]:
        if not self._corpus_database:
            return []
        match_queries = list(dict.fromkeys(filter(None, (_focused_fts_query(query), _fts_query(query)))))
        if not match_queries:
            return []
        try:
            with sqlite3.connect(f"file:{self._corpus_database.as_posix()}?mode=ro", uri=True) as conn:
                conn.row_factory = sqlite3.Row
                rows_by_id: dict[str, sqlite3.Row] = {}
                for match_query in match_queries:
                    rows = conn.execute(
                        """
                        SELECT q.id, q.dataset, q.source, q.revision, q.license,
                               q.question, q.answer, q.tags, q.safety
                        FROM qa_fts
                        JOIN qa_pairs q ON q.rowid = qa_fts.rowid
                        WHERE qa_fts MATCH ? AND q.dataset <> ?
                        ORDER BY bm25(qa_fts)
                        LIMIT ?
                        """,
                        (
                            match_query,
                            "岐黄智境中医药知识图谱",
                            max(20, min(int(limit) * 12, 180)),
                        ),
                    ).fetchall()
                    for row in rows:
                        rows_by_id.setdefault(str(row["id"]), row)
        except sqlite3.Error:
            return []
        scored: list[tuple[float, sqlite3.Row]] = []
        for row in rows_by_id.values():
            answer = _decompress_text(row["answer"])
            candidate = f"{row['question']} {row['tags']} {answer[:800]}"
            score = (
                _similarity(query, row["question"]) * 0.58
                + _similarity(query, row["tags"]) * 0.08
                + _similarity(query, answer[:800]) * 0.05
                + _focus_relevance(query, candidate) * 0.21
                + _attribute_relevance(query, candidate) * 0.08
            )
            if score >= 0.12:
                scored.append((score, row))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "scope": "built-in",
                "sourceType": "curated-qa-corpus",
                "route": "qa",
                "qaId": row["id"],
                "dataset": row["dataset"],
                "source": row["source"],
                "sourceRevision": row["revision"],
                "sourceLicense": row["license"],
                "title": row["question"],
                "question": row["question"],
                "answer": _decompress_text(row["answer"]),
                "excerpt": _decompress_text(row["answer"]),
                "tags": str(row["tags"] or "").split(),
                "safety": row["safety"],
                "score": round(score, 4),
            }
            for score, row in scored[:limit]
        ]

    def _qa_hits(self, query: str, limit: int = 4) -> list[dict[str, Any]]:
        scored: list[tuple[float, dict[str, Any]]] = []
        for item in self._qa_pairs:
            question_score = _similarity(query, item.get("question"))
            tag_score = _similarity(query, " ".join(item.get("tags") or []))
            answer_score = _similarity(query, item.get("answer"))
            score = question_score * 0.76 + tag_score * 0.17 + answer_score * 0.07
            if score >= 0.14:
                scored.append((score, item))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        local_hits = [
            {
                "scope": "built-in",
                "sourceType": "curated-qa",
                "route": "qa",
                "qaId": item.get("id"),
                "source": "QA_中医知识问答.txt",
                "title": item.get("question"),
                "question": item.get("question"),
                "answer": item.get("answer"),
                "excerpt": item.get("answer"),
                "tags": item.get("tags") or [],
                "score": round(score, 4),
            }
            for score, item in scored[:limit]
        ]
        combined = [*local_hits, *self._corpus_qa_hits(query, limit=max(limit * 3, 12))]
        combined.sort(key=lambda item: float(item.get("score") or 0), reverse=True)
        selected: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in combined:
            fingerprint = _compact_text(item.get("question"))
            if not fingerprint or fingerprint in seen:
                continue
            seen.add(fingerprint)
            selected.append(item)
            if len(selected) >= limit:
                break
        return [{**item, "citationId": f"QA{index}"} for index, item in enumerate(selected, start=1)]

    def _graph_hits(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        scored: list[tuple[float, dict[str, Any]]] = []
        for item in self._graph_nodes:
            searchable = " ".join(
                [
                    str(item.get("title") or ""),
                    " ".join(item.get("path") or []),
                    str(item.get("domain") or ""),
                    str(item.get("summary") or ""),
                    str(item.get("explanation") or ""),
                    " ".join(item.get("tags") or []),
                ]
            )
            if _focus_phrases(query) and _focus_relevance(query, searchable) < 0.34:
                continue
            title_score = _similarity(query, item.get("title"))
            path_score = _similarity(query, " ".join(item.get("path") or []))
            body_score = _similarity(
                query,
                " ".join(
                    [
                        str(item.get("domain") or ""),
                        str(item.get("summary") or ""),
                        str(item.get("explanation") or ""),
                        " ".join(item.get("tags") or []),
                    ]
                ),
            )
            score = title_score * 0.52 + path_score * 0.21 + body_score * 0.27
            if score >= 0.1:
                scored.append((score, item))
        scored.sort(key=lambda pair: (pair[0], int(pair[1].get("level") or 0)), reverse=True)
        selected: list[tuple[float, dict[str, Any]]] = []
        seen_titles: set[str] = set()
        for score, item in scored:
            title = _compact_text(item.get("title"))
            if title in seen_titles:
                continue
            seen_titles.add(title)
            selected.append((score, item))
            if len(selected) >= limit:
                break
        return [
            {
                "citationId": f"KG{index}",
                "scope": "built-in",
                "sourceType": "knowledge-graph",
                "route": "graph",
                "nodeId": item.get("id"),
                "source": "中医药知识图谱 v1.2",
                "title": item.get("title"),
                "domain": item.get("domain"),
                "level": item.get("level"),
                "path": item.get("path") or [],
                "excerpt": item.get("explanation") or item.get("summary") or "",
                "score": round(score, 4),
            }
            for index, (score, item) in enumerate(selected, start=1)
        ]

    @staticmethod
    def _question_profile(query: str, qa_hits: list[dict[str, Any]]) -> dict[str, Any]:
        compact = _compact_text(query)
        faq_markers = ("什么", "哪些", "怎么", "如何", "指", "为何", "为什么", "区别")
        relation_markers = ("关系", "联系", "区别", "比较", "配伍", "相生", "相克", "归经", "证候", "病机", "为什么")
        faq = any(marker in compact for marker in faq_markers) or bool(qa_hits and qa_hits[0]["score"] >= 0.58)
        relational = any(marker in compact for marker in relation_markers)
        return {
            "type": "faq" if faq else "relational" if relational else "open",
            "faq": faq,
            "relational": relational,
        }

    def _corpus_document_hits(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        if not self._corpus_database:
            return []
        match_queries = list(dict.fromkeys(filter(None, (_focused_fts_query(query), _fts_query(query)))))
        if not match_queries:
            return []
        try:
            with sqlite3.connect(f"file:{self._corpus_database.as_posix()}?mode=ro", uri=True) as conn:
                conn.row_factory = sqlite3.Row
                rows_by_id: dict[str, sqlite3.Row] = {}
                focus_phrases = _focus_phrases(query)
                if focus_phrases:
                    exact_rows = conn.execute(
                        """
                        SELECT d.id, d.dataset, d.source, d.revision, d.license,
                               d.title, d.content, d.tags, d.chunk_index, d.safety
                        FROM document_chunks d
                        WHERE d.title = ? AND d.dataset <> ?
                        ORDER BY d.chunk_index
                        LIMIT ?
                        """,
                        (focus_phrases[0], "岐黄智境中医药知识图谱", max(8, int(limit))),
                    ).fetchall()
                    for row in exact_rows:
                        rows_by_id.setdefault(str(row["id"]), row)
                for match_query in match_queries:
                    rows = conn.execute(
                        """
                        SELECT d.id, d.dataset, d.source, d.revision, d.license,
                               d.title, d.content, d.tags, d.chunk_index, d.safety
                        FROM document_fts
                        JOIN document_chunks d ON d.rowid = document_fts.rowid
                        WHERE document_fts MATCH ? AND d.dataset <> ?
                        ORDER BY bm25(document_fts)
                        LIMIT ?
                        """,
                        (
                            match_query,
                            "岐黄智境中医药知识图谱",
                            max(30, min(int(limit) * 12, 180)),
                        ),
                    ).fetchall()
                    for row in rows:
                        rows_by_id.setdefault(str(row["id"]), row)
        except sqlite3.Error:
            return []
        scored: list[tuple[float, sqlite3.Row, str]] = []
        for row in rows_by_id.values():
            content = _decompress_text(row["content"])
            candidate = f"{row['title']} {row['tags']} {content[:1600]}"
            focus_phrases = _focus_phrases(query)
            exact_title = bool(
                focus_phrases
                and _compact_text(row["title"]) == _compact_text(focus_phrases[0])
            )
            score = (
                _similarity(query, row["title"]) * 0.22
                + _similarity(query, row["tags"]) * 0.10
                + _similarity(query, content[:1600]) * 0.30
                + _focus_relevance(query, candidate) * 0.25
                + _attribute_relevance(query, candidate) * 0.13
                + (0.35 if exact_title else 0.0)
            )
            if score >= 0.08:
                scored.append((score, row, content))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "citationId": f"DKB{index}",
                "scope": "built-in",
                "sourceType": "document-corpus",
                "route": "document",
                "chunkId": row["id"],
                "dataset": row["dataset"],
                "source": row["source"],
                "sourceRevision": row["revision"],
                "sourceLicense": row["license"],
                "title": row["title"],
                "section": int(row["chunk_index"] or 1),
                "excerpt": content[:1600],
                "tags": str(row["tags"] or "").split(),
                "safety": row["safety"],
                "score": round(score, 4),
            }
            for index, (score, row, content) in enumerate(scored[:limit], start=1)
        ]

    def _document_hits(self, document_result: dict[str, Any], query: str) -> list[dict[str, Any]]:
        hits = []
        for item in document_result.get("hits") or []:
            if Path(str(item.get("source") or "")).name == "QA_中医知识问答.txt":
                # The curated QA index is derived from this file. Counting the
                # same material again as a document would fake corroboration.
                continue
            hit = dict(item)
            hit["route"] = "document"
            hit.setdefault("sourceType", "course-corpus")
            hit.setdefault("scope", "built-in")
            hits.append(hit)
        hits.extend(self._corpus_document_hits(query))
        return hits

    @staticmethod
    def _rank_route(
        hits: list[dict[str, Any]],
        query: str,
        weight: float,
    ) -> list[dict[str, Any]]:
        ranked = []
        for rank, item in enumerate(hits, start=1):
            relevance = float(item.get("score") or 0.0)
            if item.get("route") == "document":
                relevance = max(
                    relevance,
                    _similarity(query, f"{item.get('title', '')} {item.get('excerpt', '')}"),
                )
            fusion_score = weight * (0.68 / rank + 0.32 * min(1.0, relevance))
            ranked.append({**item, "routeRank": rank, "fusionScore": round(fusion_score, 6)})
        return ranked

    @staticmethod
    def _select_diverse(candidates: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        by_route: dict[str, list[dict[str, Any]]] = {}
        for item in candidates:
            by_route.setdefault(str(item.get("route") or "document"), []).append(item)
        route_heads = [items[0] for items in by_route.values() if items]
        route_heads.sort(key=lambda item: float(item.get("fusionScore") or 0), reverse=True)
        for item in route_heads[:limit]:
            key = (str(item.get("sourceType")), str(item.get("citationId")))
            if key not in seen:
                selected.append(item)
                seen.add(key)
        for item in candidates:
            if len(selected) >= limit:
                break
            key = (str(item.get("sourceType")), str(item.get("citationId")))
            if key in seen:
                continue
            selected.append(item)
            seen.add(key)
        return selected[:limit]

    @staticmethod
    def _hit_block(hit: dict[str, Any]) -> str:
        citation_id = str(hit.get("citationId") or "KB")
        if hit.get("route") == "qa":
            return f"[{citation_id}][QA 精确问答] {hit.get('question')}\n{hit.get('answer')}"
        if hit.get("route") == "graph":
            path = " > ".join(hit.get("path") or [str(hit.get("title") or "")])
            return f"[{citation_id}][知识图谱] {path}\n{str(hit.get('excerpt') or '')[:1600]}"
        locator = f"第 {hit['page']} 页" if hit.get("page") else f"第 {hit.get('section') or 1} 节"
        private_label = "[我的知识库] " if hit.get("scope") == "private" else "[文档切块] "
        collection = f"；知识库：{hit.get('collectionName')}" if hit.get("collectionName") else ""
        return (
            f"[{citation_id}]{private_label}{hit.get('title') or hit.get('source') or '课程资料'}"
            f"（{hit.get('source') or '未知来源'}，{locator}{collection}）\n"
            f"{str(hit.get('excerpt') or '')[:1600]}"
        )

    def retrieve(
        self,
        query: str,
        document_result: dict[str, Any],
        *,
        top_k: int = 6,
        max_context_chars: int = 9000,
    ) -> dict[str, Any]:
        self._load()
        limit = max(1, min(int(top_k), 12))
        qa_hits = self._qa_hits(query)
        graph_hits = self._graph_hits(query)
        document_hits = self._document_hits(document_result, query)
        profile = self._question_profile(query, qa_hits)
        weights = {
            "qa": 1.28 if profile["faq"] else 0.94,
            "document": 1.08,
            "graph": 1.24 if profile["relational"] else 0.98,
        }
        candidates = [
            *self._rank_route(qa_hits, query, weights["qa"]),
            *self._rank_route(document_hits, query, weights["document"]),
            *self._rank_route(graph_hits, query, weights["graph"]),
        ]
        candidates.sort(key=lambda item: float(item.get("fusionScore") or 0), reverse=True)
        selected = self._select_diverse(candidates, limit)

        context_parts: list[str] = []
        accepted: list[dict[str, Any]] = []
        context_length = 0
        for hit in selected:
            block = self._hit_block(hit)
            if context_parts and context_length + len(block) > max_context_chars:
                continue
            context_parts.append(block)
            accepted.append(hit)
            context_length += len(block)

        route_counts = {
            "qa": len([item for item in accepted if item.get("route") == "qa"]),
            "document": len([item for item in accepted if item.get("route") == "document"]),
            "graph": len([item for item in accepted if item.get("route") == "graph"]),
        }
        evidence_routes = [route for route, count in route_counts.items() if count]
        agreement_score = _pairwise_agreement(accepted)
        corroborated = len(evidence_routes) >= 2 and agreement_score >= 0.015
        decision = "allow_grounded_generation" if corroborated else "mark_for_verification"
        verification = {
            "status": (
                "corroborated"
                if corroborated
                else "low_agreement"
                if len(evidence_routes) >= 2
                else "single_source"
                if accepted
                else "insufficient"
            ),
            "evidenceRoutes": evidence_routes,
            "agreementScore": agreement_score,
            "decision": decision,
            "verificationRequired": not corroborated,
            "rule": "至少两类独立知识源命中且语义一致度达标后允许按证据生成；重复来源、低一致度、单源或无命中内容必须标记为需进一步核验。",
        }
        citations = []
        for hit in accepted:
            citation = {
                "id": hit.get("citationId"),
                "scope": hit.get("scope"),
                "sourceType": hit.get("sourceType"),
                "route": hit.get("route"),
                "title": hit.get("title"),
                "source": hit.get("source"),
            }
            for key in (
                "page", "section", "collectionId", "collectionName", "documentId",
                "qaId", "nodeId", "chunkId", "path", "domain", "dataset",
                "sourceRevision", "sourceLicense", "safety", "score", "fusionScore",
            ):
                if hit.get(key) is not None:
                    citation[key] = hit.get(key)
            citations.append(citation)

        document_stats = document_result.get("stats") or {}
        return {
            "query": query,
            "grounded": bool(accepted),
            "context": "\n\n".join(context_parts),
            "hits": accepted,
            "chunks": accepted,
            "citations": citations,
            "activePrivateCollection": document_result.get("activePrivateCollection"),
            "routing": {
                "strategy": ROUTER_VERSION,
                "queryType": profile["type"],
                "routes": [
                    {"id": "qa", "label": "QA 精确问答", "weight": weights["qa"], "matched": len(qa_hits)},
                    {"id": "document", "label": "文档切块", "weight": weights["document"], "matched": len(document_hits)},
                    {"id": "graph", "label": "知识图谱", "weight": weights["graph"], "matched": len(graph_hits)},
                ],
                "crossValidation": verification,
            },
            "stats": {
                **document_stats,
                "retrievalStrategy": ROUTER_VERSION,
                "qaPairs": self._corpus_stats["qaPairs"] or len(self._qa_pairs),
                "documentCorpusChunks": self._corpus_stats["documentChunks"],
                "graphNodes": len(self._graph_nodes),
                "qaMatched": route_counts["qa"],
                "documentMatched": route_counts["document"],
                "graphMatched": route_counts["graph"],
                "matchedChunks": len(accepted),
            },
        }


_hybrid_router = HybridKnowledgeRouter()


def route_hybrid_knowledge(
    query: str,
    document_result: dict[str, Any],
    *,
    top_k: int = 6,
    max_context_chars: int = 9000,
) -> dict[str, Any]:
    return _hybrid_router.retrieve(
        query,
        document_result,
        top_k=top_k,
        max_context_chars=max_context_chars,
    )
