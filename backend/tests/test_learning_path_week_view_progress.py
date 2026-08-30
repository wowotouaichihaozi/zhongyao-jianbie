from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as app_module
from database_schema import init_auth_schema


class LearningPathWeekViewProgressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.original_db_path = app_module.AUTH_DB_PATH
        app_module.AUTH_DB_PATH = Path(cls.tempdir.name) / "week-view-progress.sqlite3"
        now = "2026-08-30T18:00:00+08:00"
        with app_module.auth_db() as conn:
            init_auth_schema(conn)
            conn.execute(
                """
                INSERT INTO users
                    (id, username, display_name, password_hash, role, avatar_url, created_at, updated_at)
                VALUES (981, 'week-view-user', '周进度用户', ?, 'user', '/userlogo.png', ?, ?)
                """,
                (app_module.password_hash("password-1"), now, now),
            )
            cls.profile = app_module.create_profile_version(
                conn,
                981,
                {"timestamp": now, "aiAnalysis": {"summary": "中药鉴别画像"}},
                profile_name="中药鉴别画像",
                start_new_profile=True,
                timestamp=now,
            )
            app_module.activate_profile(conn, 981, int(cls.profile["id"]))
            cls.stage_id = "week-1-herb"
            cls.config = app_module.default_learning_path_config()
            cls.config["meta"].update({
                "profileReportId": int(cls.profile["id"]),
                "totalWeeks": 6,
                "generationState": "partial",
            })
            cls.config["weeks"] = [{
                "id": cls.stage_id,
                "order": 1,
                "weekLabel": "第一周",
                "title": "药材性状基础",
                "status": "current",
                "enabled": True,
            }]
            cls.config["stages"] = {
                cls.stage_id: {
                    "id": cls.stage_id,
                    "nodes": [
                        {"id": "01", "cacheKey": "week-1-herb-01", "enabled": True},
                        {"id": "02", "cacheKey": "week-1-herb-02", "enabled": True},
                    ],
                }
            }
            app_module.write_learning_path_config(conn, cls.config, 981)

    @classmethod
    def tearDownClass(cls) -> None:
        app_module.AUTH_DB_PATH = cls.original_db_path
        cls.tempdir.cleanup()

    def _view_entry(self, node_id: str) -> dict:
        return {
            "status": "running",
            "stageId": self.stage_id,
            "nodeId": node_id,
            "profileReportId": int(self.profile["id"]),
            "viewedAt": 1788084000000,
            "viewSource": "learning-path-task-open",
        }

    def test_each_unique_task_view_increments_progress_once(self) -> None:
        with app_module.auth_db() as conn:
            app_module.upsert_learning_path_node_cache(
                conn, 981, "week-1-herb-01", self._view_entry("01")
            )
            first = app_module._learning_path_week_view_progress(
                conn, 981, self.config, self.stage_id
            )
            app_module.upsert_learning_path_node_cache(
                conn, 981, "week-1-herb-01", self._view_entry("01")
            )
            duplicate = app_module._learning_path_week_view_progress(
                conn, 981, self.config, self.stage_id
            )

        self.assertEqual(first["viewedCount"], 1)
        self.assertEqual(duplicate["viewedCount"], 1)
        self.assertFalse(duplicate["allViewed"])
        self.assertEqual(duplicate["missingNodeIds"], ["02"])

    def test_final_unique_view_queues_next_week_only_once(self) -> None:
        with app_module.auth_db() as conn:
            app_module.upsert_learning_path_node_cache(
                conn, 981, "week-1-herb-02", self._view_entry("02")
            )
            progress = app_module._learning_path_week_view_progress(
                conn, 981, self.config, self.stage_id
            )

        self.assertTrue(progress["allViewed"])
        self.assertEqual(progress["viewedCount"], 2)
        with patch.object(app_module.LEARNING_PATH_GENERATION_EXECUTOR, "submit") as submit:
            first_task = app_module._schedule_profile_learning_path_generation(
                981,
                int(self.profile["id"]),
                trigger="week_tasks_viewed",
                source_week_id=self.stage_id,
            )
            duplicate_task = app_module._schedule_profile_learning_path_generation(
                981,
                int(self.profile["id"]),
                trigger="week_tasks_viewed",
                source_week_id=self.stage_id,
            )

        self.assertIsNotNone(first_task)
        self.assertEqual(duplicate_task["taskId"], first_task["taskId"])
        submit.assert_called_once()
        with app_module.auth_db() as conn:
            queued = conn.execute(
                """
                SELECT COUNT(*) AS total FROM xiaozhi_tasks
                WHERE user_id = 981 AND task_type = 'learning_path'
                  AND status IN ('queued', 'running')
                """
            ).fetchone()["total"]
        self.assertEqual(queued, 1)

    def test_week_summary_reports_exact_view_progress(self) -> None:
        with app_module.auth_db() as conn:
            annotated = app_module._annotate_learning_path_week_view_progress(
                conn, 981, app_module._json_copy(self.config)
            )

        week = annotated["weeks"][0]
        self.assertEqual(week["viewProgress"]["viewedCount"], 2)
        self.assertEqual(week["viewProgress"]["taskCount"], 2)
        self.assertTrue(week["viewProgress"]["allViewed"])
        self.assertEqual(week["progressPercent"], 100)


if __name__ == "__main__":
    unittest.main()
