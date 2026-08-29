"""Immutable learning-profile versions and per-user active selection."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any


def _timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _json_dict(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    try:
        parsed = json.loads(str(value or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {"summary": str(parsed)}


def profile_from_row(row: sqlite3.Row, *, active_report_id: int | None = None) -> dict[str, Any]:
    report = _json_dict(row["report_json"])
    report_id = int(row["id"])
    created_at = str(row["created_at"] or "")
    updated_at = str(row["updated_at"] or created_at)
    report.update(
        {
            "id": report_id,
            "profileName": str(row["profile_name"] or "学习画像"),
            "version": max(1, int(row["version"] or 1)),
            "parentReportId": int(row["parent_report_id"]) if row["parent_report_id"] is not None else None,
            "createdAt": created_at,
            "updatedAt": updated_at,
            "archived": bool(row["archived"]),
            "isActive": active_report_id == report_id,
        }
    )
    report.setdefault("timestamp", created_at)
    return report


def profile_state_for_user(conn: sqlite3.Connection, user_id: int) -> dict[str, Any]:
    state = conn.execute(
        """
        SELECT active_report_id, generation, reset_at, created_at, updated_at
        FROM user_learning_profile_state
        WHERE user_id = ?
        """,
        (int(user_id),),
    ).fetchone()
    if state:
        active_report_id = int(state["active_report_id"]) if state["active_report_id"] is not None else None
        return {
            "activeReportId": active_report_id,
            "generation": max(0, int(state["generation"] or 0)),
            "resetAt": str(state["reset_at"] or ""),
            "createdAt": str(state["created_at"] or ""),
            "updatedAt": str(state["updated_at"] or ""),
            "explicit": True,
        }

    latest = conn.execute(
        """
        SELECT id
        FROM learning_profile_reports
        WHERE user_id = ? AND archived = 0
        ORDER BY id DESC
        LIMIT 1
        """,
        (int(user_id),),
    ).fetchone()
    return {
        "activeReportId": int(latest["id"]) if latest else None,
        "generation": 0,
        "resetAt": "",
        "createdAt": "",
        "updatedAt": "",
        "explicit": False,
    }


def active_profile_for_user(conn: sqlite3.Connection, user_id: int) -> dict[str, Any]:
    state = profile_state_for_user(conn, user_id)
    report_id = state["activeReportId"]
    if report_id is None:
        return {}
    row = conn.execute(
        """
        SELECT id, user_id, report_json, profile_name, version, parent_report_id,
               created_at, updated_at, archived
        FROM learning_profile_reports
        WHERE id = ? AND user_id = ? AND archived = 0
        LIMIT 1
        """,
        (int(report_id), int(user_id)),
    ).fetchone()
    if not row:
        return {}
    report = profile_from_row(row, active_report_id=int(report_id))
    report["_profileReportId"] = int(report_id)
    report["_profileUpdatedAt"] = report["updatedAt"]
    return report


def list_profiles_for_user(conn: sqlite3.Connection, user_id: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    state = profile_state_for_user(conn, user_id)
    rows = conn.execute(
        """
        SELECT id, user_id, report_json, profile_name, version, parent_report_id,
               created_at, updated_at, archived
        FROM learning_profile_reports
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (int(user_id),),
    ).fetchall()
    return [
        profile_from_row(row, active_report_id=state["activeReportId"])
        for row in rows
    ], state


def get_profile_for_user(conn: sqlite3.Connection, user_id: int, report_id: int) -> dict[str, Any]:
    state = profile_state_for_user(conn, user_id)
    row = conn.execute(
        """
        SELECT id, user_id, report_json, profile_name, version, parent_report_id,
               created_at, updated_at, archived
        FROM learning_profile_reports
        WHERE id = ? AND user_id = ?
        LIMIT 1
        """,
        (int(report_id), int(user_id)),
    ).fetchone()
    return profile_from_row(row, active_report_id=state["activeReportId"]) if row else {}


def activate_profile(conn: sqlite3.Connection, user_id: int, report_id: int, *, timestamp: str | None = None) -> dict[str, Any]:
    report = get_profile_for_user(conn, user_id, report_id)
    if not report:
        raise LookupError("学习画像不存在")
    if report.get("archived"):
        raise ValueError("已归档画像不能设为当前画像")
    now = timestamp or _timestamp()
    conn.execute(
        """
        INSERT INTO user_learning_profile_state
            (user_id, active_report_id, generation, reset_at, created_at, updated_at)
        VALUES (?, ?, 0, '', ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            active_report_id = excluded.active_report_id,
            updated_at = excluded.updated_at
        """,
        (int(user_id), int(report_id), now, now),
    )
    report["isActive"] = True
    return report


def create_profile_version(
    conn: sqlite3.Connection,
    user_id: int,
    report: dict[str, Any],
    *,
    parent_report_id: int | None = None,
    profile_name: str = "",
    start_new_profile: bool = False,
    timestamp: str | None = None,
) -> dict[str, Any]:
    now = timestamp or str(report.get("timestamp") or "") or _timestamp()
    parent = {}
    if not start_new_profile:
        if parent_report_id is not None:
            parent = get_profile_for_user(conn, user_id, int(parent_report_id))
            if not parent:
                raise LookupError("父画像不存在")
        else:
            parent = active_profile_for_user(conn, user_id)

    version = int(parent.get("version") or 0) + 1 if parent else 1
    resolved_name = str(profile_name or parent.get("profileName") or "学习画像").strip()[:80] or "学习画像"
    payload = dict(report)
    for key in (
        "id",
        "profileName",
        "version",
        "parentReportId",
        "createdAt",
        "updatedAt",
        "archived",
        "isActive",
        "_profileReportId",
        "_profileUpdatedAt",
    ):
        payload.pop(key, None)
    payload["timestamp"] = str(payload.get("timestamp") or now)
    cursor = conn.execute(
        """
        INSERT INTO learning_profile_reports
            (user_id, report_json, profile_name, version, parent_report_id,
             created_at, updated_at, archived)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        """,
        (
            int(user_id),
            json.dumps(payload, ensure_ascii=False),
            resolved_name,
            version,
            int(parent["id"]) if parent else None,
            now,
            now,
        ),
    )
    report_id = int(cursor.lastrowid)
    return activate_profile(conn, user_id, report_id, timestamp=now)


def rename_profile(
    conn: sqlite3.Connection,
    user_id: int,
    report_id: int,
    profile_name: str,
    *,
    timestamp: str | None = None,
) -> dict[str, Any]:
    name = str(profile_name or "").strip()
    if not name:
        raise ValueError("画像名称不能为空")
    if len(name) > 80:
        raise ValueError("画像名称不能超过 80 个字符")
    existing = get_profile_for_user(conn, user_id, report_id)
    if not existing:
        raise LookupError("学习画像不存在")
    now = timestamp or _timestamp()
    conn.execute(
        """
        UPDATE learning_profile_reports
        SET profile_name = ?, updated_at = ?
        WHERE id = ? AND user_id = ?
        """,
        (name, now, int(report_id), int(user_id)),
    )
    return get_profile_for_user(conn, user_id, report_id)


def delete_profile(
    conn: sqlite3.Connection,
    user_id: int,
    report_id: int,
    *,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Delete one owned profile and keep the user's active selection valid."""

    existing = get_profile_for_user(conn, user_id, report_id)
    if not existing:
        raise LookupError("学习画像不存在")

    was_active = bool(existing.get("isActive"))
    conn.execute(
        "DELETE FROM learning_profile_reports WHERE id = ? AND user_id = ?",
        (int(report_id), int(user_id)),
    )

    if was_active:
        replacement_row = conn.execute(
            """
            SELECT id
            FROM learning_profile_reports
            WHERE user_id = ? AND archived = 0
            ORDER BY updated_at DESC, id DESC
            LIMIT 1
            """,
            (int(user_id),),
        ).fetchone()
        replacement_id = int(replacement_row["id"]) if replacement_row else None
        now = timestamp or _timestamp()
        conn.execute(
            """
            INSERT INTO user_learning_profile_state
                (user_id, active_report_id, generation, reset_at, created_at, updated_at)
            VALUES (?, ?, 0, '', ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                active_report_id = excluded.active_report_id,
                updated_at = excluded.updated_at
            """,
            (int(user_id), replacement_id, now, now),
        )

    state = profile_state_for_user(conn, user_id)
    active_profile = active_profile_for_user(conn, user_id)
    return {
        "deletedReportId": int(report_id),
        "deletedActiveProfile": was_active,
        "activeReportId": state["activeReportId"],
        "activeProfile": active_profile or None,
    }


def update_profile_report(
    conn: sqlite3.Connection,
    user_id: int,
    report_id: int,
    report: dict[str, Any],
    *,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Replace the content of one existing profile without creating a version."""
    existing = get_profile_for_user(conn, user_id, report_id)
    if not existing:
        raise LookupError("学习画像不存在")
    now = timestamp or _timestamp()
    payload = dict(report)
    for key in (
        "id", "profileName", "version", "parentReportId", "createdAt", "updatedAt",
        "archived", "isActive", "_profileReportId", "_profileUpdatedAt",
    ):
        payload.pop(key, None)
    payload["timestamp"] = str(payload.get("timestamp") or now)
    conn.execute(
        "UPDATE learning_profile_reports SET report_json = ?, updated_at = ? WHERE id = ? AND user_id = ?",
        (json.dumps(payload, ensure_ascii=False), now, int(report_id), int(user_id)),
    )
    return get_profile_for_user(conn, user_id, report_id)


_PROFILE_METADATA_FIELDS = {
    "id",
    "profileName",
    "version",
    "parentReportId",
    "createdAt",
    "updatedAt",
    "archived",
    "isActive",
    "_profileReportId",
    "_profileUpdatedAt",
}


def _profile_report_payload(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in dict(report or {}).items()
        if key not in _PROFILE_METADATA_FIELDS
    }


def save_or_update_active_profile(
    conn: sqlite3.Connection,
    user_id: int,
    report: dict[str, Any],
    *,
    profile_name: str = "",
    timestamp: str | None = None,
) -> tuple[dict[str, Any], str]:
    """Update the active profile in place, creating a record only for the first profile."""

    active = active_profile_for_user(conn, user_id)
    now = timestamp or str(report.get("timestamp") or "") or _timestamp()
    if not active:
        created = create_profile_version(
            conn,
            user_id,
            report,
            profile_name=profile_name,
            start_new_profile=True,
            timestamp=now,
        )
        return created, "created"

    merged = _profile_report_payload(active)
    updates = _profile_report_payload(report)
    active_dimensions = merged.get("chatStudentProfile")
    update_dimensions = updates.get("chatStudentProfile")
    if isinstance(active_dimensions, dict) and isinstance(update_dimensions, dict):
        updates["chatStudentProfile"] = {**active_dimensions, **update_dimensions}
    merged.update(updates)
    merged["timestamp"] = str(updates.get("timestamp") or now)
    updated = update_profile_report(
        conn,
        user_id,
        int(active["id"]),
        merged,
        timestamp=now,
    )
    return updated, "updated"


def reset_profile_state(conn: sqlite3.Connection, user_id: int, *, timestamp: str | None = None) -> dict[str, Any]:
    now = timestamp or _timestamp()
    conn.execute(
        """
        INSERT INTO user_learning_profile_state
            (user_id, active_report_id, generation, reset_at, created_at, updated_at)
        VALUES (?, NULL, 1, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            active_report_id = NULL,
            generation = user_learning_profile_state.generation + 1,
            reset_at = excluded.reset_at,
            updated_at = excluded.updated_at
        """,
        (int(user_id), now, now, now),
    )
    return profile_state_for_user(conn, user_id)
