from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import app as app_module
from database_schema import init_auth_schema
from system_monitor import SystemMonitor


class SystemMonitorTests(unittest.TestCase):
    def test_snapshot_is_written_as_rotating_json_log(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tempdir:
            root = Path(tempdir)
            (root / "frontend" / "dist").mkdir(parents=True)
            (root / "frontend" / "dist" / "index.html").write_text("ok", encoding="utf-8")
            monitor = SystemMonitor(root)

            snapshot = monitor.snapshot_and_record()
            history = monitor.recent(10)

            self.assertIn(snapshot["severity"], {"healthy", "warning", "critical"})
            self.assertIn("cpuPercent", snapshot["resources"])
            self.assertEqual(history[-1]["timestamp"], snapshot["timestamp"])
            self.assertTrue((root / "logs" / "system-monitor.jsonl").is_file())


class SuperAdminRuntimeApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.original_db_path = app_module.AUTH_DB_PATH
        cls.original_monitor = app_module.SYSTEM_MONITOR
        app_module.AUTH_DB_PATH = Path(cls.tempdir.name) / "runtime-api.sqlite3"
        monitor = SystemMonitor(Path(cls.tempdir.name))
        monitor.start = lambda: None
        app_module.SYSTEM_MONITOR = monitor
        app_module.app.config.update(TESTING=True)
        now = "2026-08-01T12:00:00+08:00"
        with app_module.auth_db() as conn:
            init_auth_schema(conn)
            for user_id, username in ((701, app_module.ADMIN_USERNAME), (702, "other-admin")):
                conn.execute(
                    """
                    INSERT INTO users
                        (id, username, display_name, password_hash, role, avatar_url, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 'admin', '/userlogo.png', ?, ?)
                    """,
                    (user_id, username, username, app_module.password_hash("Admin-password-1"), now, now),
                )
            with app_module.app.test_request_context("/api/admin/runtime"):
                cls.super_token = app_module.create_session(conn, 701)
                cls.other_token = app_module.create_session(conn, 702)
        cls.client = app_module.app.test_client()

    @classmethod
    def tearDownClass(cls) -> None:
        app_module.AUTH_DB_PATH = cls.original_db_path
        app_module.SYSTEM_MONITOR = cls.original_monitor
        cls.tempdir.cleanup()

    def test_runtime_requires_super_admin_identity(self) -> None:
        denied = self.client.get(
            "/api/admin/runtime",
            headers={"Authorization": f"Bearer {self.other_token}"},
        )
        self.assertEqual(denied.status_code, 403)

        allowed = self.client.get(
            "/api/admin/runtime?limit=10",
            headers={"Authorization": f"Bearer {self.super_token}"},
        )
        self.assertEqual(allowed.status_code, 200)
        payload = allowed.get_json()["data"]
        self.assertEqual(payload["logFile"], "logs/system-monitor.jsonl")
        self.assertIn("resources", payload["snapshot"])


if __name__ == "__main__":
    unittest.main()
