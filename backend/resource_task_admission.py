from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from contextlib import contextmanager
from typing import Any, Callable, Iterator


class ResourceTaskAdmission:
    """Serialize resource task creation and reuse equivalent active work."""

    def __init__(self) -> None:
        self._creation_lock = threading.Lock()

    @staticmethod
    def fingerprint(task_type: str, topic: str, prompt: str, params: dict) -> str:
        stable_params = {
            str(key): value
            for key, value in (params or {}).items()
            if str(key) not in {"sessionId", "ohmyPptSessionId", "force", "retry"}
        }
        encoded = json.dumps(
            {
                "taskType": str(task_type),
                "topic": str(topic).strip(),
                "prompt": str(prompt).strip(),
                "params": stable_params,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @contextmanager
    def creation_scope(self) -> Iterator[None]:
        with self._creation_lock:
            yield

    @staticmethod
    def find_active_row(
        connection_factory: Callable[[], sqlite3.Connection],
        *,
        user_id: int,
        task_type: str,
        fingerprint: str,
        title: str,
        prompt: str,
        profile_report_id: int = 0,
    ) -> sqlite3.Row | None:
        with connection_factory() as conn:
            resolved_profile_id = int(profile_report_id or 0)
            if resolved_profile_id <= 0:
                state = conn.execute(
                    "SELECT active_report_id FROM user_learning_profile_state WHERE user_id = ?",
                    (int(user_id),),
                ).fetchone()
                resolved_profile_id = int(state["active_report_id"] or 0) if state else 0
            rows = conn.execute(
                """
                SELECT task_id, task_type, title, prompt, status, route, result_json,
                       error, created_at, updated_at
                FROM xiaozhi_tasks
                WHERE user_id = ? AND task_type = ?
                  AND profile_report_id = ?
                  AND status IN ('waiting', 'queued', 'running')
                  AND title = ? AND prompt = ?
                ORDER BY id DESC
                LIMIT 30
                """,
                (int(user_id), str(task_type), resolved_profile_id, str(title), str(prompt)),
            ).fetchall()
        for row in rows:
            try:
                result: Any = json.loads(row["result_json"] or "{}")
            except (TypeError, ValueError, json.JSONDecodeError):
                result = {}
            saved_fingerprint = str(result.get("requestFingerprint") or "") if isinstance(result, dict) else ""
            if not saved_fingerprint or saved_fingerprint == fingerprint:
                return row
        return None


RESOURCE_TASK_ADMISSION = ResourceTaskAdmission()
