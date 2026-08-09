from __future__ import annotations

import sqlite3

from backend.database_schema import init_auth_schema, recover_interrupted_xiaozhi_tasks


def test_recover_interrupted_xiaozhi_tasks_marks_task_and_run_failed(tmp_path):
    conn = sqlite3.connect(tmp_path / "recovery.sqlite3")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_auth_schema(conn)
    timestamp = "2026-07-12T14:00:00+08:00"
    conn.execute(
        """
        INSERT INTO users
            (id, username, display_name, password_hash, role, avatar_url, created_at, updated_at)
        VALUES (1, 'recovery-user', 'Recovery User', 'hash', 'user', '/userlogo.png', ?, ?)
        """,
        (timestamp, timestamp),
    )
    conn.execute(
        """
        INSERT INTO xiaozhi_tasks
            (task_id, user_id, task_type, title, status, created_at, updated_at)
        VALUES ('task-running', 1, 'ppt', 'Running task', 'running', ?, ?),
               ('task-complete', 1, 'video', 'Complete task', 'complete', ?, ?)
        """,
        (timestamp, timestamp, timestamp, timestamp),
    )
    conn.execute(
        """
        INSERT INTO agent_orchestration_runs
            (run_id, task_id, user_id, task_type, status, created_at, updated_at)
        VALUES ('run-running', 'task-running', 1, 'ppt', 'running', ?, ?)
        """,
        (timestamp, timestamp),
    )
    conn.commit()

    assert recover_interrupted_xiaozhi_tasks(conn) == 1
    running = conn.execute(
        "SELECT status, error FROM xiaozhi_tasks WHERE task_id = 'task-running'"
    ).fetchone()
    complete = conn.execute(
        "SELECT status FROM xiaozhi_tasks WHERE task_id = 'task-complete'"
    ).fetchone()
    run = conn.execute(
        "SELECT status FROM agent_orchestration_runs WHERE run_id = 'run-running'"
    ).fetchone()

    assert running["status"] == "failed"
    assert "服务重启" in running["error"]
    assert complete["status"] == "complete"
    assert run["status"] == "failed"
    conn.close()
