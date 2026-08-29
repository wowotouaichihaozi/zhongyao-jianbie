"""Profile-scoped shared conversation for the XiaoZhi agent harness.

Every agent run associated with the same learning profile writes into one
ordered message stream. Older messages are compacted into a durable summary
before the prompt budget is exhausted; recent messages and artifact references
remain available verbatim.
"""

from __future__ import annotations

import json
import hashlib
import math
import os
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


SUPERVISOR_AGENT_ID = "xiaozhi-companion-agent"
SUPERVISOR_AGENT_NAME = "岐小智总控智能体"
DEFAULT_CONTEXT_TOKEN_LIMIT = 128_000_000
DEFAULT_COMPACTION_RATIO = 0.9
DEFAULT_RECENT_MESSAGE_LIMIT = 4096
DEFAULT_SUMMARY_CHAR_LIMIT = 12000


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _json_text(value: Any, max_chars: int = 8000) -> str:
    try:
        text = json.dumps(value if value is not None else {}, ensure_ascii=False, default=str)
    except Exception:
        text = json.dumps({"value": str(value)}, ensure_ascii=False)
    if len(text) <= max_chars:
        return text
    return json.dumps(
        {"truncated": True, "originalChars": len(text), "preview": text[:max_chars]},
        ensure_ascii=False,
    )


def _json_value(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback


def estimate_tokens(*values: Any) -> int:
    """Conservative token estimate that works for mixed Chinese/JSON content."""

    characters = 0
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            characters += len(value)
        else:
            characters += len(_json_text(value, 16000))
    return max(1, int(math.ceil(characters / 2.2)))


def _positive_int_setting(name: str, default: int, minimum: int) -> int:
    try:
        value = int(str(os.getenv(name, default)).strip())
    except (TypeError, ValueError):
        value = default
    return max(minimum, value)


def _compaction_ratio() -> float:
    try:
        value = float(str(os.getenv("PROFILE_AGENT_CONTEXT_COMPACTION_RATIO", DEFAULT_COMPACTION_RATIO)))
    except (TypeError, ValueError):
        value = DEFAULT_COMPACTION_RATIO
    return max(0.5, min(0.9, value))


def _resource_references(payload: Any) -> list[dict[str, str]]:
    references: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    keys = {
        "taskId": "task",
        "resourceId": "resource",
        "cacheKey": "cache",
        "route": "route",
        "sessionId": "session",
        "runId": "run",
        "citationId": "citation",
    }

    def walk(value: Any, depth: int = 0) -> None:
        if depth > 4 or len(references) >= 24:
            return
        if isinstance(value, dict):
            for key, item in value.items():
                if key in keys and isinstance(item, (str, int)) and str(item).strip():
                    identity = (keys[key], str(item).strip())
                    if identity not in seen:
                        seen.add(identity)
                        references.append({"type": identity[0], "id": identity[1]})
                elif isinstance(item, (dict, list, tuple)):
                    walk(item, depth + 1)
        elif isinstance(value, (list, tuple)):
            for item in value[:30]:
                walk(item, depth + 1)

    walk(payload)
    return references


class ProfileAgentContextStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 30000")
        return conn

    def _conversation_row(
        self,
        conn: sqlite3.Connection,
        user_id: int,
        profile_report_id: int,
        *,
        create: bool,
    ) -> sqlite3.Row | None:
        row = conn.execute(
            """
            SELECT * FROM profile_agent_conversations
            WHERE user_id = ? AND profile_report_id = ?
            """,
            (int(user_id), int(profile_report_id)),
        ).fetchone()
        if row is not None or not create:
            return row
        profile = conn.execute(
            "SELECT id FROM learning_profile_reports WHERE id = ? AND user_id = ?",
            (int(profile_report_id), int(user_id)),
        ).fetchone()
        if profile is None:
            return None
        timestamp = _now_iso()
        conn.execute(
            """
            INSERT OR IGNORE INTO profile_agent_conversations
                (user_id, profile_report_id, supervisor_agent, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (int(user_id), int(profile_report_id), SUPERVISOR_AGENT_ID, timestamp, timestamp),
        )
        return conn.execute(
            """
            SELECT * FROM profile_agent_conversations
            WHERE user_id = ? AND profile_report_id = ?
            """,
            (int(user_id), int(profile_report_id)),
        ).fetchone()

    def append(
        self,
        user_id: int,
        profile_report_id: int,
        *,
        agent_id: str,
        agent_name: str = "",
        message_type: str = "status",
        status: str = "",
        content: str,
        payload: Any = None,
        run_id: str = "",
        task_id: str = "",
        dedupe_key: str = "",
        created_at: str = "",
    ) -> dict[str, Any] | None:
        if int(user_id or 0) <= 0 or int(profile_report_id or 0) <= 0 or not str(content or "").strip():
            return None
        payload_text = _json_text(payload or {}, 8000)
        references = _resource_references(payload)
        reference_text = _json_text(references, 4000)
        normalized_content = str(content).strip()[:2000]
        token_estimate = estimate_tokens(normalized_content, payload_text, reference_text)
        normalized_agent = str(agent_id or SUPERVISOR_AGENT_ID).strip() or SUPERVISOR_AGENT_ID
        normalized_dedupe = str(dedupe_key or "").strip()
        if not normalized_dedupe:
            content_digest = hashlib.sha256(
                f"{normalized_content}\n{payload_text}".encode("utf-8")
            ).hexdigest()[:16]
            normalized_dedupe = (
                f"manual:{run_id}:{task_id}:{normalized_agent}:{message_type}:"
                f"{content_digest}"
            )

        with closing(self._connect()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            conversation = self._conversation_row(
                conn,
                int(user_id),
                int(profile_report_id),
                create=True,
            )
            if conversation is None:
                return None
            existing = conn.execute(
                """
                SELECT * FROM profile_agent_messages
                WHERE conversation_id = ? AND dedupe_key = ?
                """,
                (int(conversation["id"]), normalized_dedupe),
            ).fetchone()
            if existing is not None:
                return self._public_message(existing)
            sequence = int(conversation["message_count"] or 0) + 1
            timestamp = str(created_at or _now_iso())
            cursor = conn.execute(
                """
                INSERT INTO profile_agent_messages
                    (conversation_id, sequence, dedupe_key, run_id, task_id, agent_id,
                     agent_name, message_type, status, content, payload_json,
                     resource_refs_json, estimated_tokens, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(conversation["id"]),
                    sequence,
                    normalized_dedupe,
                    str(run_id or ""),
                    str(task_id or ""),
                    normalized_agent,
                    str(agent_name or normalized_agent)[:120],
                    str(message_type or "status")[:40],
                    str(status or "")[:40],
                    normalized_content,
                    payload_text,
                    reference_text,
                    token_estimate,
                    timestamp,
                ),
            )
            conn.execute(
                """
                UPDATE profile_agent_conversations
                SET message_count = ?, estimated_tokens = estimated_tokens + ?, updated_at = ?
                WHERE id = ?
                """,
                (sequence, token_estimate, timestamp, int(conversation["id"])),
            )
            row = conn.execute(
                "SELECT * FROM profile_agent_messages WHERE id = ?",
                (int(cursor.lastrowid),),
            ).fetchone()
        self.compact_if_needed(user_id, profile_report_id)
        return self._public_message(row) if row is not None else None

    def append_event(
        self,
        user_id: int,
        profile_report_id: int,
        event: dict[str, Any],
        *,
        task_id: str = "",
    ) -> dict[str, Any] | None:
        if not isinstance(event, dict):
            return None
        run_id = str(event.get("runId") or "")
        sequence = int(event.get("sequence") or 0)
        resolved_task_id = str(event.get("taskId") or task_id or "")
        return self.append(
            user_id,
            profile_report_id,
            agent_id=str(event.get("agentId") or SUPERVISOR_AGENT_ID),
            agent_name=str(event.get("agentName") or ""),
            message_type="agent_event",
            status=str(event.get("status") or ""),
            content=str(event.get("message") or event.get("stage") or "智能体状态已更新"),
            payload={
                "stage": event.get("stage"),
                "progress": event.get("progress"),
                "taskId": resolved_task_id,
                "details": event.get("payload") or {},
            },
            run_id=run_id,
            task_id=resolved_task_id,
            dedupe_key=f"{run_id}:event:{sequence}",
            created_at=str(event.get("time") or ""),
        )

    def append_handoff(
        self,
        user_id: int,
        profile_report_id: int,
        handoff: dict[str, Any],
        *,
        task_id: str = "",
    ) -> dict[str, Any] | None:
        if not isinstance(handoff, dict):
            return None
        run_id = str(handoff.get("runId") or "")
        sequence = int(handoff.get("sequence") or 0)
        from_name = str(handoff.get("fromAgentName") or handoff.get("fromAgent") or "智能体")
        to_name = str(handoff.get("toAgentName") or handoff.get("toAgent") or "智能体")
        summary = str(handoff.get("summary") or "完成任务交接")
        return self.append(
            user_id,
            profile_report_id,
            agent_id=str(handoff.get("fromAgent") or SUPERVISOR_AGENT_ID),
            agent_name=from_name,
            message_type="handoff",
            status="complete",
            content=f"{from_name}向{to_name}交接：{summary}",
            payload={
                "taskId": str(task_id or ""),
                "toAgent": handoff.get("toAgent"),
                "toAgentName": to_name,
                "artifactType": handoff.get("artifactType"),
                "artifact": handoff.get("payload") or {},
            },
            run_id=run_id,
            task_id=str(task_id or ""),
            dedupe_key=f"{run_id}:handoff:{sequence}",
            created_at=str(handoff.get("time") or ""),
        )

    def record_trace(
        self,
        user_id: int,
        profile_report_id: int,
        result: dict[str, Any],
        *,
        task_id: str = "",
    ) -> None:
        trace = result.get("orchestration") if isinstance(result, dict) else {}
        if not isinstance(trace, dict):
            return
        for event in trace.get("events") or []:
            if isinstance(event, dict):
                self.append_event(user_id, profile_report_id, event, task_id=task_id)
        for handoff in trace.get("handoffs") or []:
            if isinstance(handoff, dict):
                self.append_handoff(user_id, profile_report_id, handoff, task_id=task_id)
        run_id = str(trace.get("runId") or "")
        review = trace.get("review") if isinstance(trace.get("review"), dict) else {}
        if review:
            score = review.get("score")
            passed = bool(review.get("passed"))
            self.append(
                user_id,
                profile_report_id,
                agent_id="quality-review-agent",
                agent_name="资源审核智能体",
                message_type="review",
                status="complete" if passed else "needs_attention",
                content=(
                    f"审核完成，质量分 {score}，已通过。"
                    if passed
                    else f"审核未通过，质量分 {score}，需要继续处理。"
                ),
                payload={**review, "taskId": task_id},
                run_id=run_id,
                task_id=task_id,
                dedupe_key=f"{run_id}:review:final",
            )

    def backfill_from_orchestration(
        self,
        user_id: int,
        profile_report_id: int,
        *,
        limit: int = 12,
    ) -> int:
        if int(user_id or 0) <= 0 or int(profile_report_id or 0) <= 0:
            return 0
        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT run_id, task_id
                FROM agent_orchestration_runs
                WHERE user_id = ? AND profile_report_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (int(user_id), int(profile_report_id), max(1, min(50, int(limit or 12)))),
            ).fetchall()
            run_ids = [str(row["run_id"] or "") for row in rows if str(row["run_id"] or "")]
            task_ids = {str(row["run_id"] or ""): str(row["task_id"] or "") for row in rows}
            if not run_ids:
                return 0
            placeholders = ",".join("?" for _ in run_ids)
            event_rows = conn.execute(
                f"""
                SELECT run_id, sequence, agent_id, stage, status, message, progress,
                       payload_json, created_at
                FROM agent_orchestration_events
                WHERE run_id IN ({placeholders})
                ORDER BY id ASC
                """,
                run_ids,
            ).fetchall()
            handoff_rows = conn.execute(
                f"""
                SELECT run_id, sequence, from_agent, to_agent, artifact_type, summary,
                       payload_json, created_at
                FROM agent_orchestration_handoffs
                WHERE run_id IN ({placeholders})
                ORDER BY id ASC
                """,
                run_ids,
            ).fetchall()
            review_rows = conn.execute(
                f"""
                SELECT run_id, task_id, review_json, updated_at
                FROM agent_orchestration_runs
                WHERE run_id IN ({placeholders}) AND review_json NOT IN ('', '{{}}')
                ORDER BY id ASC
                """,
                run_ids,
            ).fetchall()

        inserted = 0
        for row in event_rows:
            message = str(row["message"] or row["stage"] or "智能体状态已更新").strip()
            if not message:
                continue
            result = self.append(
                user_id,
                profile_report_id,
                agent_id=str(row["agent_id"] or SUPERVISOR_AGENT_ID),
                agent_name="",
                message_type="agent_event",
                status=str(row["status"] or ""),
                content=message,
                payload={
                    "stage": row["stage"],
                    "progress": row["progress"],
                    "details": _json_value(row["payload_json"], {}),
                },
                run_id=str(row["run_id"] or ""),
                task_id=task_ids.get(str(row["run_id"] or ""), ""),
                dedupe_key=f"{row['run_id']}:event:{int(row['sequence'] or 0)}",
                created_at=str(row["created_at"] or ""),
            )
            inserted += 1 if result else 0
        for row in handoff_rows:
            from_agent = str(row["from_agent"] or SUPERVISOR_AGENT_ID)
            to_agent = str(row["to_agent"] or "智能体")
            summary = str(row["summary"] or "完成任务交接")
            result = self.append(
                user_id,
                profile_report_id,
                agent_id=from_agent,
                agent_name="",
                message_type="handoff",
                status="complete",
                content=f"{from_agent}向{to_agent}交接：{summary}",
                payload={
                    "toAgent": to_agent,
                    "artifactType": row["artifact_type"],
                    "artifact": _json_value(row["payload_json"], {}),
                },
                run_id=str(row["run_id"] or ""),
                task_id=task_ids.get(str(row["run_id"] or ""), ""),
                dedupe_key=f"{row['run_id']}:handoff:{int(row['sequence'] or 0)}",
                created_at=str(row["created_at"] or ""),
            )
            inserted += 1 if result else 0
        for row in review_rows:
            review = _json_value(row["review_json"], {})
            if not isinstance(review, dict) or not review:
                continue
            score = review.get("score")
            passed = bool(review.get("passed"))
            result = self.append(
                user_id,
                profile_report_id,
                agent_id="quality-review-agent",
                agent_name="资源审核智能体",
                message_type="review",
                status="complete" if passed else "needs_attention",
                content=(
                    f"审核完成，质量分 {score}，已通过。"
                    if passed
                    else f"审核未通过，质量分 {score}，需要继续处理。"
                ),
                payload=review,
                run_id=str(row["run_id"] or ""),
                task_id=str(row["task_id"] or ""),
                dedupe_key=f"{row['run_id']}:review:final",
                created_at=str(row["updated_at"] or ""),
            )
            inserted += 1 if result else 0
        return inserted

    def compact_if_needed(self, user_id: int, profile_report_id: int) -> bool:
        token_limit = _positive_int_setting(
            "PROFILE_AGENT_CONTEXT_MAX_TOKENS",
            DEFAULT_CONTEXT_TOKEN_LIMIT,
            2000,
        )
        threshold = int(token_limit * _compaction_ratio())
        recent_limit = _positive_int_setting(
            "PROFILE_AGENT_CONTEXT_RECENT_MESSAGES",
            DEFAULT_RECENT_MESSAGE_LIMIT,
            8,
        )
        with closing(self._connect()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            conversation = self._conversation_row(
                conn,
                int(user_id),
                int(profile_report_id),
                create=False,
            )
            if conversation is None:
                return False
            rows = conn.execute(
                """
                SELECT * FROM profile_agent_messages
                WHERE conversation_id = ? AND compacted = 0
                ORDER BY sequence ASC
                """,
                (int(conversation["id"]),),
            ).fetchall()
            active_tokens = sum(int(row["estimated_tokens"] or 0) for row in rows)
            if active_tokens < threshold or len(rows) <= recent_limit:
                return False

            candidates = rows[:-recent_limit]
            target_active_tokens = max(int(token_limit * 0.45), 1000)
            selected: list[sqlite3.Row] = []
            remaining_tokens = active_tokens
            for row in candidates:
                selected.append(row)
                remaining_tokens -= int(row["estimated_tokens"] or 0)
                if remaining_tokens <= target_active_tokens:
                    break
            if not selected:
                return False

            existing_summary = str(conversation["summary_text"] or "").strip()
            summary = self._merge_summary(existing_summary, selected)
            version = int(conversation["summary_version"] or 0) + 1
            through_sequence = int(selected[-1]["sequence"])
            selected_tokens = sum(int(row["estimated_tokens"] or 0) for row in selected)
            selected_ids = [int(row["id"]) for row in selected]
            placeholders = ",".join("?" for _ in selected_ids)
            timestamp = _now_iso()
            conn.execute(
                f"UPDATE profile_agent_messages SET compacted = 1 WHERE id IN ({placeholders})",
                selected_ids,
            )
            conn.execute(
                """
                INSERT INTO profile_agent_context_snapshots
                    (conversation_id, version, summary_text, source_message_count,
                     source_estimated_tokens, through_sequence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(conversation["id"]),
                    version,
                    summary,
                    len(selected),
                    selected_tokens,
                    through_sequence,
                    timestamp,
                ),
            )
            conn.execute(
                """
                UPDATE profile_agent_conversations
                SET summary_text = ?, summary_version = ?, compacted_through_sequence = ?,
                    estimated_tokens = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    summary,
                    version,
                    through_sequence,
                    remaining_tokens + estimate_tokens(summary),
                    timestamp,
                    int(conversation["id"]),
                ),
            )
        return True

    def restore_compacted_messages_if_budget_allows(self, user_id: int, profile_report_id: int) -> bool:
        token_limit = _positive_int_setting(
            "PROFILE_AGENT_CONTEXT_MAX_TOKENS",
            DEFAULT_CONTEXT_TOKEN_LIMIT,
            2000,
        )
        threshold = int(token_limit * _compaction_ratio())
        with closing(self._connect()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            conversation = self._conversation_row(
                conn,
                int(user_id),
                int(profile_report_id),
                create=False,
            )
            if conversation is None or not int(conversation["summary_version"] or 0):
                return False
            totals = conn.execute(
                """
                SELECT COUNT(*) AS message_count,
                       COALESCE(SUM(estimated_tokens), 0) AS total_tokens
                FROM profile_agent_messages
                WHERE conversation_id = ?
                """,
                (int(conversation["id"]),),
            ).fetchone()
            total_tokens = int(totals["total_tokens"] or 0)
            if total_tokens >= threshold:
                return False
            timestamp = _now_iso()
            conn.execute(
                "UPDATE profile_agent_messages SET compacted = 0 WHERE conversation_id = ?",
                (int(conversation["id"]),),
            )
            conn.execute(
                """
                UPDATE profile_agent_conversations
                SET summary_text = '', summary_version = 0,
                    compacted_through_sequence = 0, estimated_tokens = ?, updated_at = ?
                WHERE id = ?
                """,
                (total_tokens, timestamp, int(conversation["id"])),
            )
        return True

    def context(
        self,
        user_id: int,
        profile_report_id: int,
        *,
        recent_limit: int | None = None,
    ) -> dict[str, Any]:
        if int(user_id or 0) <= 0 or int(profile_report_id or 0) <= 0:
            return self.empty_context(profile_report_id)
        self.restore_compacted_messages_if_budget_allows(user_id, profile_report_id)
        self.compact_if_needed(user_id, profile_report_id)
        limit = max(
            8,
            min(
                200_000,
                int(
                    recent_limit
                    or _positive_int_setting(
                        "PROFILE_AGENT_CONTEXT_RECENT_MESSAGES",
                        DEFAULT_RECENT_MESSAGE_LIMIT,
                        8,
                    )
                ),
            ),
        )
        with closing(self._connect()) as conn, conn:
            conversation = self._conversation_row(
                conn,
                int(user_id),
                int(profile_report_id),
                create=True,
            )
            if conversation is None:
                return self.empty_context(profile_report_id)
            rows = conn.execute(
                """
                SELECT * FROM profile_agent_messages
                WHERE conversation_id = ? AND compacted = 0
                ORDER BY sequence DESC
                LIMIT ?
                """,
                (int(conversation["id"]), limit),
            ).fetchall()
        messages = [self._public_message(row) for row in reversed(rows)]
        summary = str(conversation["summary_text"] or "")
        active_tokens = sum(int(item.get("estimatedTokens") or 0) for item in messages)
        return {
            "conversationId": int(conversation["id"]),
            "profileReportId": int(profile_report_id),
            "supervisor": {
                "id": str(conversation["supervisor_agent"] or SUPERVISOR_AGENT_ID),
                "name": SUPERVISOR_AGENT_NAME,
            },
            "summary": summary,
            "summaryVersion": int(conversation["summary_version"] or 0),
            "compactedThroughSequence": int(conversation["compacted_through_sequence"] or 0),
            "messageCount": int(conversation["message_count"] or 0),
            "recentMessages": messages,
            "contextBudget": {
                "maxTokens": _positive_int_setting(
                    "PROFILE_AGENT_CONTEXT_MAX_TOKENS",
                    DEFAULT_CONTEXT_TOKEN_LIMIT,
                    2000,
                ),
                "estimatedTokens": estimate_tokens(summary) + active_tokens,
                "compactionRatio": _compaction_ratio(),
                "automaticCompaction": True,
            },
            "updatedAt": str(conversation["updated_at"] or ""),
        }

    @staticmethod
    def empty_context(profile_report_id: int = 0) -> dict[str, Any]:
        return {
            "conversationId": 0,
            "profileReportId": int(profile_report_id or 0),
            "supervisor": {"id": SUPERVISOR_AGENT_ID, "name": SUPERVISOR_AGENT_NAME},
            "summary": "",
            "summaryVersion": 0,
            "compactedThroughSequence": 0,
            "messageCount": 0,
            "recentMessages": [],
            "contextBudget": {
                "maxTokens": _positive_int_setting(
                    "PROFILE_AGENT_CONTEXT_MAX_TOKENS",
                    DEFAULT_CONTEXT_TOKEN_LIMIT,
                    2000,
                ),
                "estimatedTokens": 0,
                "compactionRatio": _compaction_ratio(),
                "automaticCompaction": True,
            },
            "updatedAt": "",
        }

    @staticmethod
    def _public_message(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "sequence": int(row["sequence"]),
            "runId": str(row["run_id"] or ""),
            "taskId": str(row["task_id"] or ""),
            "agentId": str(row["agent_id"] or ""),
            "agentName": str(row["agent_name"] or row["agent_id"] or ""),
            "type": str(row["message_type"] or "status"),
            "status": str(row["status"] or ""),
            "content": str(row["content"] or ""),
            "payload": _json_value(row["payload_json"], {}),
            "resourceReferences": _json_value(row["resource_refs_json"], []),
            "estimatedTokens": int(row["estimated_tokens"] or 0),
            "createdAt": str(row["created_at"] or ""),
        }

    @staticmethod
    def _merge_summary(existing_summary: str, rows: Iterable[sqlite3.Row]) -> str:
        lines: list[str] = []
        if existing_summary:
            lines.append(existing_summary)
        for row in rows:
            agent = str(row["agent_name"] or row["agent_id"] or "智能体")
            status = str(row["status"] or "").strip()
            content = " ".join(str(row["content"] or "").split())[:320]
            references = _json_value(row["resource_refs_json"], [])
            reference_text = ""
            if references:
                reference_text = "；引用 " + "、".join(
                    f"{item.get('type')}:{item.get('id')}"
                    for item in references[:8]
                    if isinstance(item, dict)
                )
            lines.append(
                f"- #{int(row['sequence'])} {agent}"
                f"{f'[{status}]' if status else ''}：{content}{reference_text}"
            )
        heading = "画像级智能体群聊压缩摘要（岐小智总控）\n"
        merged = heading + "\n".join(lines)
        if len(merged) <= DEFAULT_SUMMARY_CHAR_LIMIT:
            return merged
        tail = merged[-(DEFAULT_SUMMARY_CHAR_LIMIT - 120) :]
        return heading + "（更早摘要已继续压缩，仅保留关键结果与最近交接）\n" + tail
