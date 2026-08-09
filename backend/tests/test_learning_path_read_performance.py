from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import app as app_module
from database_schema import init_auth_schema


class LearningPathReadPerformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.original_db_path = app_module.AUTH_DB_PATH
        app_module.AUTH_DB_PATH = Path(cls.tempdir.name) / "learning-path-read.sqlite3"
        app_module.app.config.update(TESTING=True)
        now = "2026-07-17T10:00:00+08:00"
        with app_module.auth_db() as conn:
            init_auth_schema(conn)
            conn.execute(
                """
                INSERT INTO users
                    (id, username, display_name, password_hash, role, avatar_url, created_at, updated_at)
                VALUES (971, 'path-read-user', '路径读取用户', ?, 'user', '/userlogo.png', ?, ?)
                """,
                (app_module.password_hash("password-1"), now, now),
            )
            cls.profile = app_module.create_profile_version(
                conn,
                971,
                {"timestamp": now, "aiAnalysis": {"summary": "路径读取画像"}},
                profile_name="路径读取画像",
                start_new_profile=True,
                timestamp=now,
            )
            config = app_module.default_learning_path_config()
            config["meta"].update(
                {
                    "profileReportId": int(cls.profile["id"]),
                    "generationState": "complete",
                    "needsRegeneration": False,
                }
            )
            config["weeks"] = [
                {
                    "id": "week-read-fast",
                    "order": 1,
                    "weekLabel": "第一周",
                    "title": "读取性能验证",
                    "status": "current",
                    "enabled": True,
                }
            ]
            config["stages"] = {
                "week-read-fast": {
                    "id": "week-read-fast",
                    "weekLabel": "第一周",
                    "title": "读取性能验证任务",
                    "nodes": [
                        {
                            "id": "01",
                            "label": "01",
                            "title": "GPIO 读取验证",
                            "description": "验证路径读取不产生数据库写入。",
                            "state": "current",
                            "resourceType": "mindmap",
                        }
                    ],
                }
            }
            app_module.write_learning_path_config(conn, config, 971)
            with app_module.app.test_request_context("/api/auth/login"):
                cls.token = app_module.create_session(conn, 971)

        cls.client = app_module.app.test_client()
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    @classmethod
    def tearDownClass(cls) -> None:
        app_module.AUTH_DB_PATH = cls.original_db_path
        cls.tempdir.cleanup()

    def test_read_learning_path_config_does_not_write_to_sqlite(self) -> None:
        with app_module.auth_db() as conn:
            changes_before = conn.total_changes
            config = app_module.read_learning_path_config(
                conn,
                971,
                profile_report_id=int(self.profile["id"]),
            )
            changes_after = conn.total_changes

        self.assertEqual(config["weeks"][0]["id"], "week-read-fast")
        self.assertEqual(changes_after, changes_before)

    def test_stage_endpoint_can_return_compact_payload(self) -> None:
        compact = self.client.get(
            "/api/learning-path/stages/week-read-fast?includeConfig=0",
            headers=self.headers,
        )
        self.assertEqual(compact.status_code, 200)
        compact_data = compact.get_json()["data"]
        self.assertNotIn("config", compact_data)
        self.assertEqual(compact_data["stage"]["id"], "week-read-fast")
        self.assertEqual(compact_data["meta"]["activeProfileSummary"]["id"], int(self.profile["id"]))
        self.assertEqual(compact_data["meta"]["activeProfileSummary"]["profileName"], "路径读取画像")

        compatible = self.client.get(
            "/api/learning-path/stages/week-read-fast",
            headers=self.headers,
        )
        self.assertEqual(compatible.status_code, 200)
        self.assertIn("config", compatible.get_json()["data"])


if __name__ == "__main__":
    unittest.main()
