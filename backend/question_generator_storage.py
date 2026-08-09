import json
import sqlite3
from pathlib import Path
from typing import Any

try:
    from database_schema import init_question_generator_schema
except ImportError:  # pragma: no cover - package-style import fallback
    from .database_schema import init_question_generator_schema


DB_PATH = Path(__file__).resolve().parent / "data" / "question_generator.sqlite3"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def init_question_generator_db() -> None:
    with get_connection() as connection:
        init_question_generator_schema(connection)


def _row_to_sheet(row: sqlite3.Row) -> dict[str, Any]:
    payload = json.loads(row["payload_json"])
    return {
        "id": row["id"],
        "user_id": row["user_id"] if "user_id" in row.keys() else 0,
        "title": row["title"],
        "course_name": row["course_name"],
        "target_topic": row["target_topic"],
        "summary": row["summary"],
        "question_count": row["question_count"],
        "question_bank": payload,
        "created_at": row["created_at"],
    }


def _row_to_exam(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "user_id": row["user_id"] if "user_id" in row.keys() else 0,
        "sheet_id": row["sheet_id"],
        "title": row["title"],
        "score": row["score"],
        "total_score": row["total_score"],
        "correct_count": row["correct_count"],
        "question_count": row["question_count"],
        "answers": json.loads(row["answers_json"]),
        "detail": json.loads(row["detail_json"]),
        "created_at": row["created_at"],
    }


def save_question_sheet(question_bank: dict[str, Any], user_id: int | None = None) -> dict[str, Any]:
    init_question_generator_db()
    questions = question_bank.get("questions") or []
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO question_sheets
                (user_id, title, course_name, target_topic, summary, question_count, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(user_id or 0),
                question_bank.get("title") or "未命名题单",
                question_bank.get("course_name") or "",
                question_bank.get("target_topic") or "",
                question_bank.get("summary") or "",
                len(questions),
                json.dumps(question_bank, ensure_ascii=False),
            ),
        )
        sheet_id = cursor.lastrowid
        row = connection.execute("SELECT * FROM question_sheets WHERE id = ?", (sheet_id,)).fetchone()
    return _row_to_sheet(row)


def list_question_sheets(user_id: int | None = None) -> list[dict[str, Any]]:
    init_question_generator_db()
    with get_connection() as connection:
        if user_id is None:
            rows = connection.execute("SELECT * FROM question_sheets ORDER BY id DESC").fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM question_sheets WHERE user_id = ? ORDER BY id DESC",
                (int(user_id),),
            ).fetchall()
    return [_row_to_sheet(row) for row in rows]


def save_exam_result(payload: dict[str, Any], user_id: int | None = None) -> dict[str, Any]:
    init_question_generator_db()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO exam_results
                (user_id, sheet_id, title, score, total_score, correct_count, question_count, answers_json, detail_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(user_id or 0),
                payload.get("sheet_id"),
                payload.get("title") or "未命名考试",
                float(payload.get("score") or 0),
                float(payload.get("total_score") or 100),
                int(payload.get("correct_count") or 0),
                int(payload.get("question_count") or 0),
                json.dumps(payload.get("answers") or {}, ensure_ascii=False),
                json.dumps(payload.get("detail") or {}, ensure_ascii=False),
            ),
        )
        result_id = cursor.lastrowid
        row = connection.execute("SELECT * FROM exam_results WHERE id = ?", (result_id,)).fetchone()
    return _row_to_exam(row)


def list_exam_results(user_id: int | None = None) -> list[dict[str, Any]]:
    init_question_generator_db()
    with get_connection() as connection:
        if user_id is None:
            rows = connection.execute("SELECT * FROM exam_results ORDER BY id DESC").fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM exam_results WHERE user_id = ? ORDER BY id DESC",
                (int(user_id),),
            ).fetchall()
    return [_row_to_exam(row) for row in rows]


def list_history(user_id: int | None = None) -> dict[str, Any]:
    return {
        "question_sheets": list_question_sheets(user_id),
        "exam_results": list_exam_results(user_id),
    }


def save_user_question_config(user_id: int, config: dict[str, Any]) -> dict[str, Any]:
    init_question_generator_db()
    config_json = json.dumps(config, ensure_ascii=False)
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO user_question_configs (user_id, config_json, updated_at)
            VALUES (?, ?, datetime('now', 'localtime'))
            ON CONFLICT(user_id) DO UPDATE SET
                config_json = excluded.config_json,
                updated_at = excluded.updated_at
            """,
            (user_id, config_json),
        )
        row = connection.execute(
            "SELECT * FROM user_question_configs WHERE user_id = ?", (user_id,)
        ).fetchone()
    return {
        "user_id": row["user_id"],
        "config": json.loads(row["config_json"]),
        "updated_at": row["updated_at"],
    }


def get_user_question_config(user_id: int) -> dict[str, Any] | None:
    init_question_generator_db()
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM user_question_configs WHERE user_id = ?", (user_id,)
        ).fetchone()
    if not row:
        return None
    return {
        "user_id": row["user_id"],
        "config": json.loads(row["config_json"]),
        "updated_at": row["updated_at"],
    }
