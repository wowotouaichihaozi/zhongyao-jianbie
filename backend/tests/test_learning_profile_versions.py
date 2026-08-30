from __future__ import annotations

import sqlite3
import unittest

from database_schema import init_auth_schema
from learning_profile_versions import (
    activate_profile,
    active_profile_for_user,
    create_profile_version,
    delete_profile,
    list_profiles_for_user,
    rename_profile,
    reset_profile_state,
    save_or_update_active_profile,
)


class LearningProfileVersionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        init_auth_schema(self.conn)
        self.conn.executemany(
            """
            INSERT INTO users
                (id, username, display_name, password_hash, role, avatar_url, created_at, updated_at)
            VALUES (?, ?, ?, 'hash', 'user', '/userlogo.png', ?, ?)
            """,
            [
                (1, "profile-user-1", "用户一", "2026-07-10T10:00:00+08:00", "2026-07-10T10:00:00+08:00"),
                (2, "profile-user-2", "用户二", "2026-07-10T10:00:00+08:00", "2026-07-10T10:00:00+08:00"),
            ],
        )

    def tearDown(self) -> None:
        self.conn.close()

    def test_immutable_refresh_activate_and_reset(self) -> None:
        root = create_profile_version(
            self.conn,
            1,
            {"timestamp": "2026-07-10T10:01:00+08:00", "aiAnalysis": {"summary": "root"}},
            profile_name="STM32 入门画像",
            timestamp="2026-07-10T10:01:00+08:00",
        )
        child = create_profile_version(
            self.conn,
            1,
            {"timestamp": "2026-07-10T10:02:00+08:00", "aiAnalysis": {"summary": "child"}},
            parent_report_id=root["id"],
            timestamp="2026-07-10T10:02:00+08:00",
        )

        self.assertEqual(root["version"], 1)
        self.assertEqual(child["version"], 2)
        self.assertEqual(child["parentReportId"], root["id"])
        self.assertEqual(active_profile_for_user(self.conn, 1)["id"], child["id"])

        activated = activate_profile(self.conn, 1, root["id"], timestamp="2026-07-10T10:03:00+08:00")
        self.assertTrue(activated["isActive"])
        self.assertEqual(active_profile_for_user(self.conn, 1)["id"], root["id"])

        renamed = rename_profile(
            self.conn,
            1,
            root["id"],
            "基础阶段画像",
            timestamp="2026-07-10T10:04:00+08:00",
        )
        self.assertEqual(renamed["profileName"], "基础阶段画像")
        self.assertEqual(renamed["aiAnalysis"]["summary"], "root")

        state = reset_profile_state(self.conn, 1, timestamp="2026-07-10T10:05:00+08:00")
        self.assertIsNone(state["activeReportId"])
        self.assertEqual(active_profile_for_user(self.conn, 1), {})
        profiles, _ = list_profiles_for_user(self.conn, 1)
        self.assertEqual(len(profiles), 2)

        new_root = create_profile_version(
            self.conn,
            1,
            {"timestamp": "2026-07-10T10:06:00+08:00", "aiAnalysis": {"summary": "new root"}},
            timestamp="2026-07-10T10:06:00+08:00",
        )
        self.assertEqual(new_root["version"], 1)
        self.assertIsNone(new_root["parentReportId"])
        self.assertEqual(active_profile_for_user(self.conn, 1)["id"], new_root["id"])

    def test_cross_user_activation_is_rejected(self) -> None:
        profile = create_profile_version(
            self.conn,
            1,
            {"timestamp": "2026-07-10T10:01:00+08:00", "aiAnalysis": {"summary": "private"}},
        )
        with self.assertRaises(LookupError):
            activate_profile(self.conn, 2, profile["id"])

    def test_delete_profile_cascades_scoped_data_and_reselects_active_profile(self) -> None:
        root = create_profile_version(
            self.conn,
            1,
            {"timestamp": "2026-07-10T10:01:00+08:00", "aiAnalysis": {"summary": "root"}},
            profile_name="基础画像",
            timestamp="2026-07-10T10:01:00+08:00",
        )
        current = create_profile_version(
            self.conn,
            1,
            {"timestamp": "2026-07-10T10:02:00+08:00", "aiAnalysis": {"summary": "current"}},
            parent_report_id=root["id"],
            profile_name="当前画像",
            timestamp="2026-07-10T10:02:00+08:00",
        )
        self.conn.execute(
            """
            INSERT INTO learning_path_profile_configs
                (user_id, profile_report_id, config_json, created_at, updated_at)
            VALUES (?, ?, '{}', ?, ?)
            """,
            (1, current["id"], "2026-07-10T10:02:00+08:00", "2026-07-10T10:02:00+08:00"),
        )

        deleted = delete_profile(
            self.conn,
            1,
            current["id"],
            timestamp="2026-07-10T10:03:00+08:00",
        )

        self.assertTrue(deleted["deletedActiveProfile"])
        self.assertEqual(deleted["activeReportId"], root["id"])
        self.assertEqual(active_profile_for_user(self.conn, 1)["id"], root["id"])
        self.assertIsNone(self.conn.execute(
            "SELECT id FROM learning_profile_reports WHERE id = ?",
            (current["id"],),
        ).fetchone())
        self.assertIsNone(self.conn.execute(
            "SELECT profile_report_id FROM learning_path_profile_configs WHERE profile_report_id = ?",
            (current["id"],),
        ).fetchone())

        with self.assertRaises(LookupError):
            delete_profile(self.conn, 2, root["id"])

    def test_save_updates_active_profile_in_place_and_merges_dimensions(self) -> None:
        root = create_profile_version(
            self.conn,
            1,
            {
                "timestamp": "2026-07-10T10:01:00+08:00",
                "chatStudentProfile": {"学习目标": "掌握 GPIO", "资源偏好": "视频"},
                "aiAnalysis": {"summary": "更新前"},
                "retainedEvidence": {"examCount": 2},
            },
            profile_name="当前画像",
            timestamp="2026-07-10T10:01:00+08:00",
        )

        updated, save_mode = save_or_update_active_profile(
            self.conn,
            1,
            {
                "timestamp": "2026-07-10T10:02:00+08:00",
                "chatStudentProfile": {"学习目标": "掌握中断"},
                "aiAnalysis": {"summary": "更新后"},
            },
            profile_name="不应覆盖名称",
            timestamp="2026-07-10T10:02:00+08:00",
        )

        count = self.conn.execute(
            "SELECT COUNT(*) AS total FROM learning_profile_reports WHERE user_id = 1"
        ).fetchone()["total"]
        self.assertEqual(save_mode, "updated")
        self.assertEqual(count, 1)
        self.assertEqual(updated["id"], root["id"])
        self.assertEqual(updated["version"], root["version"])
        self.assertEqual(updated["profileName"], "当前画像")
        self.assertEqual(updated["chatStudentProfile"]["学习目标"], "掌握中断")
        self.assertEqual(updated["chatStudentProfile"]["资源偏好"], "视频")
        self.assertEqual(updated["retainedEvidence"], {"examCount": 2})
        self.assertEqual(updated["aiAnalysis"]["summary"], "更新后")


if __name__ == "__main__":
    unittest.main()
