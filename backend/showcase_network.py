"""Read-only showcase projections for Harness traces and knowledge sources."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote


DOMAIN_RULES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("mcu", "MCU 与单片机", ("单片机", "mcu", "8051", "stm32", "arduino", "rp2040", "pico")),
    ("rtos", "实时操作系统", ("rtos", "freertos", "zephyr", "nuttx", "任务调度", "实时操作")),
    ("linux", "嵌入式 Linux", ("linux", "kernel", "驱动", "device tree", "设备树")),
    ("riscv", "RISC-V 与处理器", ("risc-v", "riscv", "处理器", "cortex", "cmsis", "arm")),
    ("network", "通信与网络", ("lwip", "tcp", "udp", "can", "usb", "tinyusb", "串口", "通信", "网络")),
    ("gui", "图形与人机交互", ("lvgl", "显示", "触摸", "gui", "lcd", "oled")),
    ("hardware", "硬件与接口", ("pcb", "传感器", "电源", "gpio", "adc", "dac", "pwm", "接口")),
    ("engineering", "工程与验证", ("测试", "调试", "ci", "静态分析", "故障", "debug", "toolchain")),
    ("language", "嵌入式编程", ("c语言", "embedded c", "c++", "编程", "算法", "数据结构")),
)

TOPIC_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("FreeRTOS", ("freertos",)),
    ("RISC-V", ("risc-v", "riscv")),
    ("STM32", ("stm32",)),
    ("8051", ("8051",)),
    ("Arduino", ("arduino",)),
    ("Zephyr", ("zephyr",)),
    ("NuttX", ("nuttx",)),
    ("LVGL", ("lvgl",)),
    ("TinyUSB", ("tinyusb",)),
    ("lwIP", ("lwip",)),
    ("嵌入式 Linux", ("linux",)),
    ("ARM Cortex-M", ("cortex-m", "cortex m", "cmsis")),
    ("GPIO", ("gpio",)),
    ("中断", ("中断", "interrupt")),
    ("定时器", ("定时器", "timer")),
    ("通信总线", ("can", "i2c", "spi", "uart", "串口")),
    ("测试与调试", ("测试", "调试", "debug", "static analysis")),
)

_catalog_cache: dict[str, Any] = {"key": None, "documents": []}
CATALOG_VERSION = 1


def _json(value: object, fallback: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    try:
        parsed = json.loads(str(value or ""))
    except (TypeError, ValueError):
        return fallback
    return parsed if isinstance(parsed, type(fallback)) else fallback


def _slug(value: str) -> str:
    clean = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return clean or hashlib.sha1(str(value).encode("utf-8")).hexdigest()[:12]


def _domain_for(text: str) -> tuple[str, str]:
    lowered = str(text or "").lower()
    scores = [
        (sum(lowered.count(keyword) for keyword in keywords), key, label)
        for key, label, keywords in DOMAIN_RULES
    ]
    score, key, label = max(scores, key=lambda item: item[0])
    return (key, label) if score else ("foundation", "嵌入式基础")


def _catalog_path(index_path: Path) -> Path:
    return index_path.with_name(f"{index_path.stem}_catalog.json")


def _summarize_course_chunks(chunks: object) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for chunk in chunks if isinstance(chunks, list) else []:
        if not isinstance(chunk, dict):
            continue
        source = str(chunk.get("source") or "").strip()
        if not source:
            continue
        item = grouped.setdefault(
            source,
            {
                "source": source,
                "title": str(chunk.get("title") or Path(source).stem),
                "chunks": 0,
                "sample": "",
                "detail": "",
                "topics": set(),
            },
        )
        item["chunks"] += 1
        content = str(chunk.get("content") or "")
        if not item["sample"]:
            item["sample"] = content[:320]
            item["detail"] = content[:1200]
        searchable = f"{item['title']} {content}".lower()
        for topic, keywords in TOPIC_RULES:
            if any(keyword in searchable for keyword in keywords):
                item["topics"].add(topic)
    documents: list[dict[str, Any]] = []
    for item in grouped.values():
        domain_key, domain_label = _domain_for(f"{item['title']} {item['sample']} {' '.join(item['topics'])}")
        item["domainKey"] = domain_key
        item["domain"] = domain_label
        item["topics"] = sorted(item["topics"])
        documents.append(item)
    documents.sort(key=lambda item: (-int(item["chunks"]), item["source"]))
    return documents


def write_course_catalog(index_path: Path, output_path: Path | None = None) -> dict[str, Any]:
    index_path = Path(index_path)
    output_path = Path(output_path) if output_path else _catalog_path(index_path)
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    documents = _summarize_course_chunks(payload.get("chunks") or [])
    catalog = {
        "version": CATALOG_VERSION,
        "sourceIndexBytes": index_path.stat().st_size,
        "indexedChunks": sum(int(item["chunks"]) for item in documents),
        "documents": documents,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(f"{output_path.suffix}.tmp")
    temporary.write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.replace(temporary, output_path)
    return catalog


def _course_documents(index_path: Path) -> list[dict[str, Any]]:
    try:
        stat = index_path.stat()
        catalog_path = _catalog_path(index_path)
        catalog_stat = catalog_path.stat() if catalog_path.is_file() else None
        cache_key = f"{index_path}:{stat.st_size}:{stat.st_mtime_ns}:{getattr(catalog_stat, 'st_size', 0)}:{getattr(catalog_stat, 'st_mtime_ns', 0)}"
    except OSError:
        return []
    if _catalog_cache["key"] == cache_key:
        return list(_catalog_cache["documents"])
    if catalog_stat:
        try:
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            documents = catalog.get("documents") or []
            if (
                catalog.get("version") == CATALOG_VERSION
                and int(catalog.get("sourceIndexBytes") or 0) == stat.st_size
                and isinstance(documents, list)
            ):
                _catalog_cache.update({"key": cache_key, "documents": documents})
                return list(documents)
        except (OSError, ValueError, TypeError):
            pass
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return []
    documents = _summarize_course_chunks(payload.get("chunks") or [])
    _catalog_cache.update({"key": cache_key, "documents": documents})
    return list(documents)


def knowledge_overview(
    conn: sqlite3.Connection,
    user_id: int,
    index_path: Path,
    collection_id: int | None = None,
    view: str = "overview",
    node_limit: int = 180,
) -> dict[str, Any]:
    documents = _course_documents(index_path)
    is_atlas = view == "atlas"
    node_limit = max(180, min(int(node_limit or 180), 20000)) if is_atlas else 180
    domain_counts = Counter(item["domainKey"] for item in documents)
    domain_labels = {item["domainKey"]: item["domain"] for item in documents}
    topic_counts: Counter[tuple[str, str]] = Counter()
    for item in documents:
        for topic in item["topics"]:
            topic_counts[(item["domainKey"], topic)] += 1

    nodes: list[dict[str, Any]] = [{"id": "knowledge-root", "name": "嵌入式知识网络", "type": "root", "symbolSize": 62, "verified": True}]
    edges: list[dict[str, Any]] = []
    for domain_key, count in domain_counts.most_common(12):
        node_id = f"course-domain:{domain_key}"
        nodes.append({"id": node_id, "name": domain_labels[domain_key], "type": "domain", "count": count, "symbolSize": min(46, 22 + math.sqrt(count) * 1.5), "verified": True})
        edges.append({"source": "knowledge-root", "target": node_id, "relation": "contains"})
    topic_node_ids: set[str] = set()
    topic_nodes_by_name: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for (domain_key, topic), count in topic_counts.most_common(180 if is_atlas else 36):
        if domain_key not in domain_counts:
            continue
        node_id = f"course-topic:{domain_key}:{_slug(topic)}"
        topic_node_ids.add(node_id)
        nodes.append({"id": node_id, "name": topic, "type": "topic", "domain": domain_labels.get(domain_key, domain_key), "domainKey": domain_key, "count": count, "symbolSize": min(31, 14 + math.sqrt(count) * 1.6), "verified": True})
        edges.append({"source": f"course-domain:{domain_key}", "target": node_id, "relation": "mentions"})
        topic_nodes_by_name[topic.casefold()].append((domain_key, node_id))

    # Cross-domain bridges are derived only from normalized topics that occur in
    # more than one real domain. A sorted chain keeps the relationship auditable
    # without turning one shared topic into a dense all-to-all mesh.
    for shared_topic, members in sorted(topic_nodes_by_name.items()):
        unique_members = sorted(set(members))
        for left, right in zip(unique_members, unique_members[1:]):
            edges.append({
                "source": left[1],
                "target": right[1],
                "relation": "shared_topic",
                "sharedTopic": shared_topic,
            })

    if is_atlas:
        # The atlas returns one node per source document, not one node per chunk.
        # This keeps a 10k+ node graph practical while preserving source traceability.
        document_budget = max(0, node_limit - len(nodes) - 100)
        for item in documents[:document_budget]:
            document_node = f"course-document:{quote(item['source'], safe='')}"
            nodes.append({
                "id": document_node,
                "name": item["title"],
                "type": "document",
                "source": item["source"],
                "domain": item["domain"],
                "domainKey": item["domainKey"],
                "chunkCount": item["chunks"],
                "excerpt": item["sample"],
                "topics": item["topics"],
                "symbolSize": 4 + min(5, math.sqrt(item["chunks"])),
                "verified": True,
                "sourceType": "built-in-course",
            })
            edges.append({
                "source": f"course-domain:{item['domainKey']}",
                "target": document_node,
                "relation": "contains",
            })
            for topic in item["topics"][:3]:
                topic_node = f"course-topic:{item['domainKey']}:{_slug(topic)}"
                if topic_node in topic_node_ids:
                    edges.append({"source": topic_node, "target": document_node, "relation": "mentions"})

    collection_where = "AND c.id = ?" if collection_id else ""
    values: list[Any] = [int(user_id)]
    if collection_id:
        values.append(int(collection_id))
    private_rows = conn.execute(
        f"""
        SELECT c.id AS collection_id, c.name AS collection_name, c.updated_at,
               d.id AS document_id, d.title, d.filename, d.chunk_count
        FROM private_knowledge_collections c
        LEFT JOIN private_knowledge_documents d ON d.collection_id = c.id AND d.user_id = c.user_id AND d.status = 'ready'
        WHERE c.user_id = ? AND c.archived = 0 {collection_where}
        ORDER BY c.updated_at DESC, d.id DESC LIMIT 80
        """,
        values,
    ).fetchall()
    seen_collections: set[int] = set()
    for row in private_rows:
        collection_key = int(row["collection_id"])
        collection_node = f"private-collection:{collection_key}"
        if collection_key not in seen_collections:
            seen_collections.add(collection_key)
            nodes.append({"id": collection_node, "name": row["collection_name"], "type": "collection", "symbolSize": 34, "verified": True, "collectionId": collection_key})
            edges.append({"source": "knowledge-root", "target": collection_node, "relation": "contains"})
        if row["document_id"]:
            document_node = f"private-document:{int(row['document_id'])}"
            nodes.append({"id": document_node, "name": row["title"] or row["filename"], "type": "document", "symbolSize": 18, "verified": True, "source": row["filename"], "collectionId": collection_key})
            edges.append({"source": collection_node, "target": document_node, "relation": "contains"})

    edge_limit = min(60000, node_limit * 4) if is_atlas else 300
    result_nodes = nodes[:node_limit]
    result_node_ids = {node["id"] for node in result_nodes}
    result_edges = [
        edge for edge in edges
        if edge["source"] in result_node_ids and edge["target"] in result_node_ids
    ][:edge_limit]
    return {
        "nodes": result_nodes,
        "edges": result_edges,
        "stats": {
            "courseDocuments": len(documents),
            "courseDomains": len(domain_counts),
            "privateCollections": len(seen_collections),
            "visibleNodes": len(result_nodes),
            "visibleEdges": len(result_edges),
            "indexedChunks": sum(int(item["chunks"]) for item in documents),
        },
        "limits": {"nodes": node_limit, "edges": edge_limit},
        "view": "atlas" if is_atlas else "overview",
        "generatedFrom": "course-index-and-user-data",
    }


def expand_knowledge_node(conn: sqlite3.Connection, user_id: int, index_path: Path, node_id: str, limit: int = 30) -> dict[str, Any]:
    limit = max(1, min(int(limit or 30), 50))
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    detail: dict[str, Any] | None = None
    if node_id.startswith("course-domain:"):
        domain_key = node_id.split(":", 1)[1]
        for item in [doc for doc in _course_documents(index_path) if doc["domainKey"] == domain_key][:limit]:
            child_id = f"course-document:{quote(item['source'], safe='')}"
            nodes.append({"id": child_id, "name": item["title"], "type": "document", "source": item["source"], "excerpt": item["sample"], "chunkCount": item["chunks"], "verified": True, "sourceType": "built-in-course"})
            edges.append({"source": node_id, "target": child_id, "relation": "contains"})
    elif node_id.startswith("course-document:"):
        source = unquote(node_id.split(":", 1)[1])
        document = next((item for item in _course_documents(index_path) if item["source"] == source), None)
        if document:
            detail = {"excerpt": document["detail"], "source": document["source"]}
            for topic in document["topics"][:limit]:
                child_id = f"document-topic:{_slug(source)}:{_slug(topic)}"
                nodes.append({"id": child_id, "name": topic, "type": "topic", "source": source, "verified": True})
                edges.append({"source": node_id, "target": child_id, "relation": "mentions"})
    elif node_id.startswith("private-collection:"):
        collection_id = int(node_id.split(":", 1)[1])
        rows = conn.execute(
            "SELECT id, title, filename, chunk_count FROM private_knowledge_documents WHERE user_id = ? AND collection_id = ? AND status = 'ready' ORDER BY id DESC LIMIT ?",
            (int(user_id), collection_id, limit),
        ).fetchall()
        for row in rows:
            child_id = f"private-document:{int(row['id'])}"
            nodes.append({"id": child_id, "name": row["title"] or row["filename"], "type": "document", "source": row["filename"], "chunkCount": row["chunk_count"], "collectionId": collection_id, "verified": True})
            edges.append({"source": node_id, "target": child_id, "relation": "contains"})
    elif node_id.startswith("private-document:"):
        document_id = int(node_id.split(":", 1)[1])
        rows = conn.execute(
            """SELECT c.id, c.chunk_index, c.page, c.content, d.filename FROM private_knowledge_chunks c
               JOIN private_knowledge_documents d ON d.id = c.document_id
               WHERE c.user_id = ? AND c.document_id = ? ORDER BY c.chunk_index LIMIT ?""",
            (int(user_id), document_id, limit),
        ).fetchall()
        for row in rows:
            child_id = f"private-chunk:{int(row['id'])}"
            nodes.append({"id": child_id, "name": f"片段 {row['chunk_index']}", "type": "citation", "source": row["filename"], "page": row["page"], "section": row["chunk_index"], "excerpt": str(row["content"] or "")[:500], "verified": True})
            edges.append({"source": node_id, "target": child_id, "relation": "contains"})
    return {"anchor": node_id, "nodes": nodes, "edges": edges, "detail": detail, "limit": limit}


def knowledge_timeline(conn: sqlite3.Connection, user_id: int, limit: int = 40) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit or 40), 100))
    events: list[dict[str, Any]] = []
    for row in conn.execute(
        "SELECT run_id, task_type, topic, root_agent, skill_id, status, created_at FROM agent_orchestration_runs WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (int(user_id), limit),
    ).fetchall():
        events.append({"id": f"run:{row['run_id']}", "type": "agent_run", "stage": "智能体调用", "title": row["topic"] or row["task_type"], "detail": row["skill_id"] or row["root_agent"], "status": row["status"], "runId": row["run_id"], "createdAt": row["created_at"]})
    for row in conn.execute(
        "SELECT id, run_id, title, status, review_note, created_at, reviewed_at FROM knowledge_feedback_candidates WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (int(user_id), limit),
    ).fetchall():
        events.append({"id": f"feedback:{row['id']}", "type": "feedback", "stage": "知识反哺", "title": row["title"], "detail": row["review_note"] or "等待来源与内容审核", "status": row["status"], "runId": row["run_id"], "createdAt": row["reviewed_at"] or row["created_at"]})
    events.sort(key=lambda item: str(item.get("createdAt") or ""), reverse=True)
    return events[:limit]


def knowledge_growth_summary(conn: sqlite3.Connection, user_id: int) -> dict[str, int]:
    user_id = int(user_id)
    run_row = conn.execute(
        """
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN status IN ('complete', 'completed') THEN 1 ELSE 0 END) AS completed
        FROM agent_orchestration_runs WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()
    feedback_row = conn.execute(
        """
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending,
               SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) AS approved,
               SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) AS rejected,
               SUM(CASE WHEN approved_document_id IS NOT NULL THEN 1 ELSE 0 END) AS ingested
        FROM knowledge_feedback_candidates WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()
    collection_row = conn.execute(
        """
        SELECT COUNT(DISTINCT c.id) AS collections,
               COUNT(d.id) AS documents
        FROM private_knowledge_collections c
        LEFT JOIN private_knowledge_documents d
          ON d.collection_id = c.id AND d.user_id = c.user_id AND d.status = 'ready'
        WHERE c.user_id = ? AND c.archived = 0
        """,
        (user_id,),
    ).fetchone()
    return {
        "agentRuns": int(run_row["total"] or 0),
        "completedRuns": int(run_row["completed"] or 0),
        "candidates": int(feedback_row["total"] or 0),
        "pending": int(feedback_row["pending"] or 0),
        "approved": int(feedback_row["approved"] or 0),
        "rejected": int(feedback_row["rejected"] or 0),
        "ingestedDocuments": int(feedback_row["ingested"] or 0),
        "collections": int(collection_row["collections"] or 0),
        "privateDocuments": int(collection_row["documents"] or 0),
    }


def public_feedback_candidate(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": int(row["id"]), "userId": int(row["user_id"]), "collectionId": int(row["collection_id"]),
        "runId": row["run_id"], "title": row["title"], "content": row["content"],
        "evidence": _json(row["evidence_json"], []), "confidence": float(row["confidence"] or 0),
        "status": row["status"], "reviewNote": row["review_note"],
        "reviewedBy": int(row["reviewed_by"] or 0) or None, "reviewedAt": row["reviewed_at"],
        "approvedDocumentId": int(row["approved_document_id"] or 0) or None,
        "createdAt": row["created_at"], "updatedAt": row["updated_at"],
    }
