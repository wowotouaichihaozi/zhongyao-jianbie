from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import app as app_module
from database_schema import init_auth_schema


class LearningPathProfileSwitchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.original_db_path = app_module.AUTH_DB_PATH
        app_module.AUTH_DB_PATH = Path(cls.tempdir.name) / "path-profile-switch.sqlite3"
        app_module.app.config.update(TESTING=True)
        now = "2026-07-14T16:00:00+08:00"
        with app_module.auth_db() as conn:
            init_auth_schema(conn)
            conn.execute(
                """
                INSERT INTO users
                    (id, username, display_name, password_hash, role, avatar_url, created_at, updated_at)
                VALUES (901, 'path-switch-user', '路径切换用户', ?, 'user', '/userlogo.png', ?, ?)
                """,
                (app_module.password_hash("password-1"), now, now),
            )
            cls.profile_one = app_module.create_profile_version(
                conn,
                901,
                {"timestamp": now, "aiAnalysis": {"summary": "画像一"}},
                profile_name="画像一",
                start_new_profile=True,
                timestamp=now,
            )
            cls.profile_two = app_module.create_profile_version(
                conn,
                901,
                {"timestamp": "2026-07-14T16:05:00+08:00", "aiAnalysis": {"summary": "画像二"}},
                profile_name="画像二",
                start_new_profile=True,
                timestamp="2026-07-14T16:05:00+08:00",
            )

    @classmethod
    def tearDownClass(cls) -> None:
        app_module.AUTH_DB_PATH = cls.original_db_path
        cls.tempdir.cleanup()

    def test_each_profile_restores_its_own_learning_path(self) -> None:
        first_stage_id = "week-profile-one"
        first_config = app_module.default_learning_path_config()
        first_config["meta"].update(
            {
                "profileReportId": int(self.profile_one["id"]),
                "profileUpdatedAt": self.profile_one["updatedAt"],
                "generationState": "complete",
                "needsRegeneration": False,
            }
        )
        first_config["weeks"] = [
            {
                "id": first_stage_id,
                "order": 1,
                "weekLabel": "第一周",
                "title": "画像一对应路径",
                "status": "current",
                "enabled": True,
            }
        ]
        first_config["stages"] = {
            first_stage_id: {
                "id": first_stage_id,
                "weekLabel": "第一周",
                "title": "画像一任务",
                "resourceProfileReportId": int(self.profile_one["id"]),
                "nodes": [
                    {
                        "id": "01",
                        "label": "01",
                        "title": "GPIO 基础",
                        "description": "完成 GPIO 基础练习",
                        "state": "current",
                        "resourceType": "video",
                    }
                ],
            }
        }

        with app_module.auth_db() as conn:
            app_module.activate_profile(conn, 901, int(self.profile_one["id"]))
            app_module.write_learning_path_config(conn, first_config, 901)

            app_module.activate_profile(conn, 901, int(self.profile_two["id"]))
            app_module.mark_learning_path_profile_switch(
                conn,
                901,
                int(self.profile_two["id"]),
            )
            empty_second_path = app_module.read_learning_path_config(conn, 901)
            self.assertEqual(empty_second_path["weeks"], [])

            second_stage_id = "week-profile-two"
            second_config = app_module.default_learning_path_config()
            second_config["meta"].update({
                "profileReportId": int(self.profile_two["id"]),
                "generationState": "complete",
                "needsRegeneration": False,
            })
            second_config["weeks"] = [{
                "id": second_stage_id,
                "order": 1,
                "weekLabel": "第一周",
                "title": "画像二对应路径",
                "status": "current",
                "enabled": True,
            }]
            second_config["stages"] = {
                second_stage_id: {
                    "id": second_stage_id,
                    "weekLabel": "第一周",
                    "title": "画像二任务",
                    "resourceProfileReportId": int(self.profile_two["id"]),
                    "nodes": [],
                }
            }
            app_module.write_learning_path_config(conn, second_config, 901)

            app_module.activate_profile(conn, 901, int(self.profile_one["id"]))
            app_module.mark_learning_path_profile_switch(conn, 901, int(self.profile_one["id"]))
            restored_first = app_module.read_learning_path_config(conn, 901)

            app_module.activate_profile(conn, 901, int(self.profile_two["id"]))
            app_module.mark_learning_path_profile_switch(conn, 901, int(self.profile_two["id"]))
            restored_second = app_module.read_learning_path_config(conn, 901)
            stored_count = conn.execute(
                "SELECT COUNT(*) AS total FROM learning_path_profile_configs WHERE user_id = 901"
            ).fetchone()["total"]
            profiles, _state = app_module.list_profiles_for_user(conn, 901)
            app_module._attach_profile_learning_path_statuses(conn, 901, profiles)
            path_statuses = {
                int(profile["id"]): profile["learningPath"]
                for profile in profiles
            }

        self.assertEqual(restored_first["meta"]["profileReportId"], int(self.profile_one["id"]))
        self.assertEqual(restored_first["weeks"][0]["id"], first_stage_id)
        self.assertEqual(restored_first["stages"][first_stage_id]["title"], "画像一任务")
        self.assertEqual(restored_second["meta"]["profileReportId"], int(self.profile_two["id"]))
        self.assertEqual(restored_second["weeks"][0]["id"], second_stage_id)
        self.assertEqual(restored_second["stages"][second_stage_id]["title"], "画像二任务")
        self.assertEqual(stored_count, 2)
        self.assertTrue(path_statuses[int(self.profile_one["id"])]["hasPath"])
        self.assertTrue(path_statuses[int(self.profile_two["id"])]["hasPath"])
        self.assertEqual(path_statuses[int(self.profile_one["id"])]["weekCount"], 1)

    def test_legacy_user_path_is_migrated_without_losing_data(self) -> None:
        now = "2026-07-14T17:00:00+08:00"
        with app_module.auth_db() as conn:
            conn.execute(
                """
                INSERT INTO users
                    (id, username, display_name, password_hash, role, avatar_url, created_at, updated_at)
                VALUES (902, 'legacy-path-user', '旧路径用户', ?, 'user', '/userlogo.png', ?, ?)
                """,
                (app_module.password_hash("password-2"), now, now),
            )
            profile = app_module.create_profile_version(
                conn,
                902,
                {"timestamp": now, "aiAnalysis": {"summary": "旧画像"}},
                profile_name="旧画像",
                start_new_profile=True,
                timestamp=now,
            )
            config = app_module.default_learning_path_config()
            config["meta"]["profileReportId"] = int(profile["id"])
            config["weeks"] = [{
                "id": "legacy-week",
                "order": 1,
                "weekLabel": "第一周",
                "title": "旧路径仍保留",
                "status": "current",
                "enabled": True,
            }]
            config["stages"] = {"legacy-week": {"id": "legacy-week", "nodes": []}}
            conn.execute(
                """
                INSERT INTO user_learning_path_configs (user_id, config_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (902, json.dumps(config, ensure_ascii=False), now, now),
            )

            migrated = app_module.migrate_user_learning_path_configs(conn)
            restored = app_module.read_learning_path_config(conn, 902)
            stored = conn.execute(
                """
                SELECT config_json FROM learning_path_profile_configs
                WHERE user_id = ? AND profile_report_id = ?
                """,
                (902, int(profile["id"])),
            ).fetchone()

        self.assertGreaterEqual(migrated, 1)
        self.assertIsNotNone(stored)
        self.assertEqual(restored["weeks"][0]["title"], "旧路径仍保留")


if __name__ == "__main__":
    unittest.main()
