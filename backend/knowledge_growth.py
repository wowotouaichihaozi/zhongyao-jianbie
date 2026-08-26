"""User-isolated long-term memories extracted from completed dialogue turns."""

from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
from typing import Any


TOPIC_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("中医基础理论", ("阴阳", "五行", "藏象", "气血津液", "经络")),
    ("中医诊断学", ("四诊", "望诊", "闻诊", "问诊", "切诊", "舌诊", "脉诊")),
    ("八纲辨证", ("八纲", "表里", "寒热", "虚实", "阴阳辨证")),
    ("脏腑辨证", ("脏腑辨证", "心系", "肝胆", "脾胃", "肺系", "肾系")),
    ("中药学", ("中药", "性味", "归经", "功效", "炮制")),
    ("方剂学", ("方剂", "君臣佐使", "配伍", "方义", "加减")),
    ("中医经典", ("黄帝内经", "伤寒论", "金匮要略", "经典条文")),
    ("针灸推拿", ("针灸", "经络", "腧穴", "配穴", "推拿")),
    ("中医养生", ("养生", "体质", "四时", "情志", "食疗")),
    ("医案辨析", ("医案", "证候", "病机", "治法", "辨证论治")),
    ("学习复盘", ("复盘", "错题", "薄弱点", "学习计划", "总结")),
)

SIGNAL_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("学习目标", ("我想学", "我希望", "目标是", "准备学习", "想掌握")),
    ("薄弱点", ("不懂", "不会", "薄弱", "总是出错", "看不明白", "容易混淆")),
    ("内容偏好", ("喜欢", "偏好", "希望用", "更适合", "最好用")),
    ("学习节奏", ("每天", "每周", "小时", "分钟", "时间不多", "进度")),
    ("已有基础", ("学过", "做过", "会用", "了解", "有基础")),
)


def _loads(value: object, fallback: Any) -> Any:
    if isinstance(value, type(fallback)):
        return value
    try:
        parsed = json.loads(str(value or ""))
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback
    return parsed if isinstance(parsed, type(fallback)) else fallback


def _compact(value: object, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def extract_conversation_core(
    user_message: str,
    assistant_message: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = metadata if isinstance(metadata, dict) else {}
    combined = f"{user_message} {assistant_message}".lower()
    topics = [label for label, keywords in TOPIC_KEYWORDS if any(keyword in combined for keyword in keywords)]
    supplied_topic = _compact(metadata.get("topic"), 60)
    if supplied_topic and supplied_topic.lower() not in {item.lower() for item in topics}:
        topics.insert(0, supplied_topic)
    topics = list(dict.fromkeys(topics))[:8]

    signals = []
    user_text = _compact(user_message, 1200)
    sentences = [part.strip() for part in re.split(r"[。！？!?；;\n]+", user_text) if part.strip()]
    for label, keywords in SIGNAL_RULES:
        evidence = next((sentence for sentence in sentences if any(word in sentence.lower() for word in keywords)), "")
        if evidence:
            signals.append({"type": label, "value": evidence[:100], "source": "user-message"})

    dimensions = metadata.get("dimensions") if isinstance(metadata.get("dimensions"), dict) else {}
    for key, value in list(dimensions.items())[:6]:
        value_text = _compact(value, 100)
        if value_text:
            signals.append({"type": str(key)[:40], "value": value_text, "source": "profile-agent"})

    supplied_summary = _compact(metadata.get("summary"), 220)
    if supplied_summary:
        summary = supplied_summary
    elif supplied_topic:
        summary = f"用户围绕“{supplied_topic}”展开对话：{_compact(user_message, 150)}"
    else:
        summary = _compact(user_message, 200)
    if not summary:
        summary = "本轮对话已保存，等待智能体回复后补全核心信息。"

    return {"summary": summary, "topics": topics, "signals": signals[:10]}


def record_conversation_memory(
    conn: sqlite3.Connection,
    user_id: int,
    *,
    source_type: str,
    source_key: str,
    user_message: str,
    assistant_message: str = "",
    session_id: str = "",
    route: str = "",
    metadata: dict[str, Any] | None = None,
    timestamp: str,
) -> dict[str, Any]:
    metadata = metadata if isinstance(metadata, dict) else {}
    core = extract_conversation_core(user_message, assistant_message, metadata)
    status = "complete" if str(assistant_message or "").strip() else "captured"
    conn.execute(
        """
        INSERT INTO knowledge_growth_memories
            (user_id, source_type, source_key, session_id, route, user_message,
             assistant_message, core_summary, topics_json, signals_json, metadata_json,
             status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, source_type, source_key) DO UPDATE SET
            session_id = excluded.session_id,
            route = excluded.route,
            user_message = excluded.user_message,
            assistant_message = excluded.assistant_message,
            core_summary = excluded.core_summary,
            topics_json = excluded.topics_json,
            signals_json = excluded.signals_json,
            metadata_json = excluded.metadata_json,
            status = excluded.status,
            updated_at = excluded.updated_at
        """,
        (
            int(user_id), str(source_type)[:40], str(source_key)[:160], str(session_id)[:160],
            str(route)[:300], str(user_message)[:12000], str(assistant_message)[:12000],
            core["summary"], json.dumps(core["topics"], ensure_ascii=False),
            json.dumps(core["signals"], ensure_ascii=False), json.dumps(metadata, ensure_ascii=False),
            status, timestamp, timestamp,
        ),
    )
    row = conn.execute(
        "SELECT * FROM knowledge_growth_memories WHERE user_id = ? AND source_type = ? AND source_key = ?",
        (int(user_id), str(source_type)[:40], str(source_key)[:160]),
    ).fetchone()
    return public_memory(row)


def public_memory(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "sourceType": str(row["source_type"]),
        "sourceKey": str(row["source_key"]),
        "sessionId": str(row["session_id"] or ""),
        "route": str(row["route"] or ""),
        "userMessage": str(row["user_message"] or ""),
        "assistantMessage": str(row["assistant_message"] or ""),
        "summary": str(row["core_summary"] or ""),
        "topics": _loads(row["topics_json"], []),
        "signals": _loads(row["signals_json"], []),
        "status": str(row["status"] or "captured"),
        "extractor": str(row["extractor"] or ""),
        "createdAt": str(row["created_at"] or ""),
        "updatedAt": str(row["updated_at"] or ""),
    }


def conversation_growth_overview(conn: sqlite3.Connection, user_id: int, limit: int = 60) -> dict[str, Any]:
    limit = max(1, min(int(limit or 60), 100))
    rows = conn.execute(
        "SELECT * FROM knowledge_growth_memories WHERE user_id = ? ORDER BY updated_at DESC, id DESC LIMIT ?",
        (int(user_id), limit),
    ).fetchall()
    memories = [public_memory(row) for row in rows]
    topic_counts = Counter(topic for item in memories for topic in item["topics"])
    signal_count = sum(len(item["signals"]) for item in memories)
    completed = sum(1 for item in memories if item["status"] == "complete")
    return {
        "memories": memories,
        "stats": {
            "conversationTurns": len(memories),
            "completedExtractions": completed,
            "topicCount": len(topic_counts),
            "signalCount": signal_count,
            "contextReady": completed,
        },
        "topics": [{"name": name, "count": count} for name, count in topic_counts.most_common(16)],
    }


def recent_memory_context(conn: sqlite3.Connection, user_id: int, limit: int = 12) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, core_summary, topics_json, signals_json, updated_at
        FROM knowledge_growth_memories
        WHERE user_id = ? AND status = 'complete'
        ORDER BY updated_at DESC, id DESC LIMIT ?
        """,
        (int(user_id), max(1, min(int(limit or 12), 30))),
    ).fetchall()
    return [{
        "id": int(row["id"]),
        "summary": str(row["core_summary"] or ""),
        "topics": _loads(row["topics_json"], []),
        "signals": _loads(row["signals_json"], []),
        "updatedAt": str(row["updated_at"] or ""),
    } for row in rows]
