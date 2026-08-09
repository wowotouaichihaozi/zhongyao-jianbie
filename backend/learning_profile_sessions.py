"""Persistence helpers for isolated learning-profile dialogue sessions."""

from __future__ import annotations

import json
import sqlite3
from typing import Any


def _loads(value: object, fallback: Any) -> Any:
    try:
        parsed = json.loads(str(value or ""))
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback
    return parsed if isinstance(parsed, type(fallback)) else fallback


def _session_from_row(conn: sqlite3.Connection, row: sqlite3.Row, include_messages: bool = False) -> dict[str, Any]:
    session_id = int(row["id"])
    item = {
        "id": session_id,
        "title": str(row["title"] or "新学习画像"),
        "status": str(row["status"] or "collecting"),
        "dimensions": _loads(row["dimensions_json"], {}),
        "reportId": int(row["report_id"]) if row["report_id"] is not None else None,
        "createdAt": str(row["created_at"] or ""),
        "updatedAt": str(row["updated_at"] or ""),
    }
    if include_messages:
        rows = conn.execute(
            "SELECT id, role, content, metadata_json, created_at FROM learning_profile_session_messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
        item["messages"] = [{
            "id": int(message["id"]), "role": str(message["role"]), "content": str(message["content"]),
            "metadata": _loads(message["metadata_json"], {}), "createdAt": str(message["created_at"] or ""),
        } for message in rows]
    return item


def list_sessions(conn: sqlite3.Connection, user_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM learning_profile_sessions WHERE user_id = ? ORDER BY updated_at DESC, id DESC", (int(user_id),)
    ).fetchall()
    return [_session_from_row(conn, row) for row in rows]


def create_session(conn: sqlite3.Connection, user_id: int, timestamp: str, title: str = "") -> dict[str, Any]:
    cursor = conn.execute(
        "INSERT INTO learning_profile_sessions (user_id, title, status, dimensions_json, created_at, updated_at) VALUES (?, ?, 'collecting', '{}', ?, ?)",
        (int(user_id), (title or "新学习画像").strip()[:80] or "新学习画像", timestamp, timestamp),
    )
    return get_session(conn, user_id, int(cursor.lastrowid), include_messages=True)


def get_session(conn: sqlite3.Connection, user_id: int, session_id: int, *, include_messages: bool = True) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM learning_profile_sessions WHERE id = ? AND user_id = ?", (int(session_id), int(user_id))).fetchone()
    return _session_from_row(conn, row, include_messages) if row else {}


def add_message(conn: sqlite3.Connection, user_id: int, session_id: int, role: str, content: str, timestamp: str, metadata: dict[str, Any] | None = None) -> int:
    if not get_session(conn, user_id, session_id, include_messages=False):
        raise LookupError("学习画像会话不存在")
    cursor = conn.execute(
        "INSERT INTO learning_profile_session_messages (session_id, role, content, metadata_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (int(session_id), role, content, json.dumps(metadata or {}, ensure_ascii=False), timestamp),
    )
    conn.execute("UPDATE learning_profile_sessions SET updated_at = ? WHERE id = ?", (timestamp, int(session_id)))
    return int(cursor.lastrowid)


def update_session(conn: sqlite3.Connection, user_id: int, session_id: int, *, dimensions: dict[str, Any], status: str, timestamp: str, report_id: int | None = None) -> dict[str, Any]:
    if not get_session(conn, user_id, session_id, include_messages=False):
        raise LookupError("学习画像会话不存在")
    conn.execute(
        "UPDATE learning_profile_sessions SET dimensions_json = ?, status = ?, report_id = COALESCE(?, report_id), updated_at = ? WHERE id = ? AND user_id = ?",
        (json.dumps(dimensions, ensure_ascii=False), status, report_id, timestamp, int(session_id), int(user_id)),
    )
    return get_session(conn, user_id, session_id, include_messages=True)
