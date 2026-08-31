from __future__ import annotations

import sqlite3
import threading
import time
import os
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable


class QueueCapacityError(RuntimeError):
    """Raised when a background executor has no remaining admission slots."""

    def __init__(self, executor_name: str) -> None:
        super().__init__(f"background queue is full: {executor_name}")
        self.executor_name = executor_name


class BoundedExecutor:
    """Thread pool with a bounded pending queue and observable counters."""

    def __init__(self, *, name: str, max_workers: int, max_pending: int) -> None:
        self.name = str(name)
        self.max_workers = max(1, int(max_workers))
        self.max_pending = max(0, int(max_pending))
        self.capacity = self.max_workers + self.max_pending
        self._executor = ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix=self.name,
        )
        self._slots = threading.BoundedSemaphore(self.capacity)
        self._lock = threading.Lock()
        self._submitted = 0
        self._running = 0
        self._completed = 0
        self._failed = 0
        self._rejected = 0

    def submit(self, fn: Callable[..., Any], /, *args: Any, **kwargs: Any) -> Future:
        if not self._slots.acquire(blocking=False):
            with self._lock:
                self._rejected += 1
            raise QueueCapacityError(self.name)

        with self._lock:
            self._submitted += 1

        def run() -> Any:
            with self._lock:
                self._running += 1
            try:
                return fn(*args, **kwargs)
            except BaseException:
                with self._lock:
                    self._failed += 1
                raise
            finally:
                with self._lock:
                    self._running -= 1
                    self._completed += 1
                self._slots.release()

        try:
            return self._executor.submit(run)
        except BaseException:
            self._slots.release()
            with self._lock:
                self._failed += 1
                self._completed += 1
            raise

    def snapshot(self) -> dict[str, int | str]:
        with self._lock:
            active = self._running
            admitted = self._submitted - self._completed
            return {
                "name": self.name,
                "workers": self.max_workers,
                "maxPending": self.max_pending,
                "capacity": self.capacity,
                "active": active,
                "pending": max(0, admitted - active),
                "available": max(0, self.capacity - admitted),
                "completed": self._completed,
                "failed": self._failed,
                "rejected": self._rejected,
            }

    def shutdown(self, wait: bool = True, *, cancel_futures: bool = False) -> None:
        self._executor.shutdown(wait=wait, cancel_futures=cancel_futures)


def configured_bounded_executor(
    *,
    name: str,
    worker_setting: str | None,
    default_workers: int,
    worker_limit: int,
    pending_setting: str | None,
    default_pending: int,
    pending_limit: int,
) -> BoundedExecutor:
    def integer_setting(setting: str | None, default: int, minimum: int, maximum: int) -> int:
        if not setting:
            return max(minimum, min(maximum, int(default)))
        try:
            return max(minimum, min(maximum, int(os.getenv(setting, str(default)))))
        except (TypeError, ValueError):
            return max(minimum, min(maximum, int(default)))

    return BoundedExecutor(
        name=name,
        max_workers=integer_setting(worker_setting, default_workers, 1, worker_limit),
        max_pending=integer_setting(pending_setting, default_pending, 0, pending_limit),
    )


def create_platform_executors() -> dict[str, BoundedExecutor]:
    specifications = {
        "resource": ("resource-agent", "RESOURCE_AGENT_MAX_WORKERS", 10, 12, "RESOURCE_AGENT_MAX_PENDING", 30, 100),
        "ppt": ("ppt-resource", "PPT_RESOURCE_MAX_WORKERS", 1, 2, "PPT_RESOURCE_MAX_PENDING", 6, 20),
        "video": ("video-resource", None, 2, 2, None, 10, 10),
        "learningPath": ("learning-path-generation", "LEARNING_PATH_GENERATION_MAX_WORKERS", 2, 3, None, 12, 12),
        "weekPreparation": ("learning-path-week-preparation", "LEARNING_PATH_WEEK_PREPARATION_MAX_WORKERS", 2, 4, None, 12, 12),
        "profilePortrait": ("profile-portrait", "PROFILE_PORTRAIT_MAX_WORKERS", 2, 3, None, 8, 8),
    }
    return {
        key: configured_bounded_executor(
            name=values[0],
            worker_setting=values[1],
            default_workers=values[2],
            worker_limit=values[3],
            pending_setting=values[4],
            default_pending=values[5],
            pending_limit=values[6],
        )
        for key, values in specifications.items()
    }


def database_health(db_path: str | Path) -> dict[str, Any]:
    """Run a cheap read-only database probe suitable for a public health route."""

    started = time.perf_counter()
    path = Path(db_path).resolve()
    try:
        uri = f"file:{path.as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=2.0) as conn:
            conn.execute("SELECT 1").fetchone()
            schema = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'"
            ).fetchone()
        return {
            "status": "healthy",
            "latencyMs": round((time.perf_counter() - started) * 1000, 2),
            "schemaTables": int((schema or [0])[0] or 0),
        }
    except (OSError, sqlite3.Error):
        return {
            "status": "unavailable",
            "latencyMs": round((time.perf_counter() - started) * 1000, 2),
        }


def runtime_health_snapshot(
    *,
    db_path: str | Path,
    connection_factory: Callable[[], sqlite3.Connection],
    executors: dict[str, BoundedExecutor],
    service: str,
    started_at: float,
    timestamp: str,
) -> tuple[dict[str, Any], int]:
    database = database_health(db_path)
    task_counts = {"waiting": 0, "queued": 0, "running": 0, "failed": 0}
    if database.get("status") == "healthy":
        try:
            with connection_factory() as conn:
                rows = conn.execute(
                    """
                    SELECT status, COUNT(*) AS total
                    FROM xiaozhi_tasks
                    WHERE status IN ('waiting', 'queued', 'running', 'failed')
                    GROUP BY status
                    """
                ).fetchall()
            task_counts.update({str(row["status"]): int(row["total"] or 0) for row in rows})
        except sqlite3.Error:
            database = {**database, "status": "unavailable"}

    executor_states = [executor.snapshot() for executor in executors.values()]
    overloaded = any(int(item.get("available") or 0) == 0 for item in executor_states)
    database_ok = database.get("status") == "healthy"
    status = "healthy" if database_ok and not overloaded else "degraded" if database_ok else "unavailable"
    payload = {
        "ok": database_ok,
        "status": status,
        "service": service,
        "database": database,
        "backgroundTasks": task_counts,
        "executors": executor_states,
        "uptimeSeconds": max(0, round(time.monotonic() - started_at)),
        "now": timestamp,
    }
    return payload, 200 if database_ok else 503
