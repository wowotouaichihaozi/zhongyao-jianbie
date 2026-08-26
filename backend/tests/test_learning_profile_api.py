from __future__ import annotations

import json
import sqlite3
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import app as app_module
import learning_agents as learning_agents_module
from database_schema import (
    backfill_learning_profile_portrait_files,
    init_auth_schema,
    recover_interrupted_learning_profile_portraits,
)
from learning_profile_versions import create_profile_version


class LearningProfileApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.original_db_path = app_module.AUTH_DB_PATH
        app_module.AUTH_DB_PATH = Path(cls.tempdir.name) / "api-test.sqlite3"
        app_module.app.config.update(TESTING=True)
        with app_module.auth_db() as conn:
            init_auth_schema(conn)
            now = "2026-07-10T10:00:00+08:00"
            conn.executemany(
                """
                INSERT INTO users
                    (id, username, display_name, password_hash, role, avatar_url, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'user', '/userlogo.png', ?, ?)
                """,
                [
                    (101, "api-user-1", "API 用户一", app_module.password_hash("password-1"), now, now),
                    (102, "api-user-2", "API 用户二", app_module.password_hash("password-2"), now, now),
                ],
            )
            cls.profile_one = create_profile_version(
                conn,
                101,
                {
                    "timestamp": "2026-07-10T10:01:00+08:00",
                    "chatStudentProfile": {"学习目标": "掌握 STM32"},
                    "aiAnalysis": {
                        "source": "llm",
                        "learningStyle": "实践型",
                        "summary": "基础画像",
                        "strengths": ["动手"],
                        "weaknesses": ["中断"],
                        "recommendations": ["完成中断实验"],
                    },
                },
                profile_name="基础画像",
            )
            cls.profile_two = create_profile_version(
                conn,
                101,
                {
                    "timestamp": "2026-07-10T10:02:00+08:00",
                    "chatStudentProfile": {"学习目标": "完成综合项目"},
                    "aiAnalysis": {
                        "source": "llm",
                        "learningStyle": "项目型",
                        "summary": "项目画像",
                        "strengths": ["项目"],
                        "weaknesses": ["调试"],
                        "recommendations": ["完成串口调试"],
                    },
                },
                parent_report_id=cls.profile_one["id"],
                profile_name="项目画像",
            )
            cls.other_profile = create_profile_version(
                conn,
                102,
                {
                    "timestamp": "2026-07-10T10:03:00+08:00",
                    "aiAnalysis": {"source": "llm", "summary": "other"},
                },
            )
            with app_module.app.test_request_context(
                "/api/auth/login",
                headers={"User-Agent": "harness-api-test"},
            ):
                cls.token = app_module.create_session(conn, 101)
                cls.other_token = app_module.create_session(conn, 102)

        cls.client = app_module.app.test_client()
        cls.headers = {"Authorization": f"Bearer {cls.token}"}
        cls.other_headers = {"Authorization": f"Bearer {cls.other_token}"}

    @classmethod
    def tearDownClass(cls) -> None:
        app_module.AUTH_DB_PATH = cls.original_db_path
        cls.tempdir.cleanup()

    def _cleanup_test_profile(self, report_id: int) -> None:
        with app_module.auth_db() as conn:
            conn.execute("DELETE FROM learning_profile_reports WHERE id = ?", (int(report_id),))
            app_module.activate_profile(conn, 101, self.profile_two["id"])

    def _snapshot_learning_path_storage(self, user_id: int = 101) -> dict:
        with app_module.auth_db() as conn:
            legacy = conn.execute(
                "SELECT user_id, config_json, created_at, updated_at FROM user_learning_path_configs WHERE user_id = ?",
                (int(user_id),),
            ).fetchone()
            scoped = conn.execute(
                """
                SELECT user_id, profile_report_id, config_json, created_at, updated_at
                FROM learning_path_profile_configs
                WHERE user_id = ?
                ORDER BY profile_report_id
                """,
                (int(user_id),),
            ).fetchall()
        return {
            "legacy": dict(legacy) if legacy else None,
            "scoped": [dict(row) for row in scoped],
        }

    def _restore_learning_path_storage(self, snapshot: dict, user_id: int = 101) -> None:
        with app_module.auth_db() as conn:
            conn.execute("DELETE FROM user_learning_path_configs WHERE user_id = ?", (int(user_id),))
            conn.execute("DELETE FROM learning_path_profile_configs WHERE user_id = ?", (int(user_id),))
            legacy = snapshot.get("legacy") if isinstance(snapshot, dict) else None
            if isinstance(legacy, dict):
                conn.execute(
                    """
                    INSERT INTO user_learning_path_configs (user_id, config_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        legacy["user_id"],
                        legacy["config_json"],
                        legacy["created_at"],
                        legacy["updated_at"],
                    ),
                )
            for row in snapshot.get("scoped") or []:
                conn.execute(
                    """
                    INSERT INTO learning_path_profile_configs
                        (user_id, profile_report_id, config_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        row["user_id"],
                        row["profile_report_id"],
                        row["config_json"],
                        row["created_at"],
                        row["updated_at"],
                    ),
                )

    def _integrity_test_path_config(self, marker: str, planner_source: str = "llm") -> dict:
        config = app_module.default_learning_path_config()
        config["meta"].update(
            {
                "needsRegeneration": False,
                "generationState": "complete",
                "profileReportId": self.profile_two["id"],
                "totalWeeks": 3,
            }
        )
        config["planner"].update({"source": planner_source})
        config["weeks"] = []
        config["stages"] = {}
        for index in range(1, 4):
            stage_id = f"week-{marker}-{index}"
            week_label = f"第{index}周"
            title = f"{marker}-第{index}周"
            config["weeks"].append(
                {
                    "id": stage_id,
                    "order": index,
                    "weekLabel": week_label,
                    "title": title,
                    "status": "current" if index == 1 else "locked",
                    "enabled": True,
                }
            )
            config["stages"][stage_id] = {
                "id": stage_id,
                "weekLabel": week_label,
                "title": title,
                "nodes": [
                    {
                        "id": "01",
                        "label": "01",
                        "title": f"{title}任务",
                        "description": "完成可验证学习任务。",
                        "resourceType": "video",
                    }
                ],
            }
        return config

    def test_waiting_generated_video_starts_same_persisted_task(self) -> None:
        with (
            patch.object(app_module.VIDEO_RESOURCE_EXECUTOR, "submit") as initial_submit,
            patch.object(app_module, "execute_generated_video_task") as execute_video,
        ):
            created = app_module.xiaozhi_create_resource_agent_task(
                101,
                "generated_video",
                "STM32 GPIO 中断",
                {
                    "prompt": "结合当前画像讲解 STM32 GPIO 中断配置",
                    "duration": 30,
                },
            )
        self.assertEqual(created["status"], "waiting")
        self.assertTrue(created["result"]["params"]["deferred"])
        self.assertEqual(created["result"]["currentStage"], "waiting_for_user")
        initial_submit.assert_not_called()
        execute_video.assert_not_called()

        with (
            patch.object(app_module.VIDEO_RESOURCE_EXECUTOR, "submit") as submit,
            patch.object(app_module, "execute_generated_video_task") as execute_video,
        ):
            response = self.client.post(
                f"/api/personalized-resources/generated-videos/{created['taskId']}/start",
                headers=self.headers,
                json={
                    "prompt": "重点讲清 EXTI 映射和中断优先级",
                    "params": {
                        "duration": 40,
                        "style": "科技信息图",
                        "voice": "alloy",
                        "resolution": "1080p",
                        "videoEngine": "seedance_2",
                    },
                },
            )

        self.assertEqual(response.status_code, 202)
        task = response.get_json()["data"]["task"]
        self.assertEqual(task["taskId"], created["taskId"])
        self.assertEqual(task["status"], "queued")
        self.assertEqual(task["prompt"], "重点讲清 EXTI 映射和中断优先级")
        self.assertEqual(task["result"]["params"]["videoEngine"], "seedance_2")
        self.assertEqual(task["result"]["params"]["resolution"], "1080p")
        self.assertNotIn("deferred", task["result"]["params"])
        submit.assert_called_once()
        submitted_args = submit.call_args.args
        self.assertIs(submitted_args[0], app_module.xiaozhi_run_resource_task)
        self.assertEqual(submitted_args[1:4], (created["taskId"], 101, "generated_video"))
        self.assertEqual(submitted_args[5]["videoEngine"], "seedance_2")
        self.assertEqual(submitted_args[5]["resolution"], "1080p")
        execute_video.assert_not_called()

        repeated = self.client.post(
            f"/api/personalized-resources/generated-videos/{created['taskId']}/start",
            headers=self.headers,
            json={"params": {}},
        )
        self.assertEqual(repeated.status_code, 409)

        forbidden = self.client.post(
            f"/api/personalized-resources/generated-videos/{created['taskId']}/start",
            headers=self.other_headers,
            json={"params": {}},
        )
        self.assertEqual(forbidden.status_code, 404)

    def test_generated_video_start_validates_engine_and_resolution(self) -> None:
        cases = (
            ("defaults", {}, "seedance_1_5_coze", "720p"),
            ("coze-480p", {"videoEngine": "seedance_1_5_coze", "resolution": "480p"}, "seedance_1_5_coze", "480p"),
            ("mini-720p", {"videoEngine": "seedance_2_mini", "resolution": "720p"}, "seedance_2_mini", "720p"),
            ("seedance-2-1080p", {"videoEngine": "seedance_2", "resolution": "1080p"}, "seedance_2", "1080p"),
            ("invalid-fallback", {"videoEngine": "unknown", "resolution": "2160p"}, "seedance_1_5_coze", "720p"),
        )
        task_ids = []
        try:
            for label, requested, expected_engine, expected_resolution in cases:
                with self.subTest(label=label):
                    with (
                        patch.object(app_module.VIDEO_RESOURCE_EXECUTOR, "submit") as submit,
                        patch.object(app_module, "execute_generated_video_task") as execute_video,
                    ):
                        created = app_module.xiaozhi_create_resource_agent_task(
                            101,
                            "generated_video",
                            f"视频参数校验 {label}",
                            {"prompt": f"生成参数校验视频 {label}"},
                        )
                        task_ids.append(created["taskId"])
                        submit.assert_not_called()

                        response = self.client.post(
                            f"/api/personalized-resources/generated-videos/{created['taskId']}/start",
                            headers=self.headers,
                            json={"params": requested},
                        )

                    self.assertEqual(response.status_code, 202)
                    params = response.get_json()["data"]["task"]["result"]["params"]
                    self.assertEqual(params["videoEngine"], expected_engine)
                    self.assertEqual(params["resolution"], expected_resolution)
                    submit.assert_called_once()
                    submitted_params = submit.call_args.args[5]
                    self.assertEqual(submitted_params["videoEngine"], expected_engine)
                    self.assertEqual(submitted_params["resolution"], expected_resolution)
                    execute_video.assert_not_called()
        finally:
            with app_module.auth_db() as conn:
                for task_id in task_ids:
                    conn.execute("DELETE FROM xiaozhi_tasks WHERE task_id = ?", (task_id,))
                    conn.execute(
                        "DELETE FROM xiaozhi_events WHERE user_id = ? AND payload_json LIKE ?",
                        (101, f'%{task_id}%'),
                    )

    def test_generated_video_agent_api_only_saves_prompt_until_user_confirmation(self) -> None:
        task_id = ""
        try:
            with (
                patch.object(app_module.VIDEO_RESOURCE_EXECUTOR, "submit") as submit,
                patch.object(app_module, "execute_generated_video_task") as execute_video,
            ):
                response = self.client.post(
                    "/api/personalized-resources/agent-task",
                    headers=self.headers,
                    json={
                        "resourceType": "generated_video",
                        "topic": "GPIO 输入输出模式",
                        "prompt": "结合当前画像讲清 GPIO 浮空、上拉、推挽与开漏模式",
                        "params": {"duration": 30},
                    },
                )

            self.assertEqual(response.status_code, 202)
            payload = response.get_json()
            task = payload["data"]["task"]
            task_id = str(task["taskId"])
            self.assertEqual(task["status"], "waiting")
            self.assertEqual(task["prompt"], "结合当前画像讲清 GPIO 浮空、上拉、推挽与开漏模式")
            self.assertEqual(task["result"]["currentStage"], "waiting_for_user")
            self.assertTrue(task["result"]["params"]["deferred"])
            self.assertIn("等待用户确认", payload["msg"])
            submit.assert_not_called()
            execute_video.assert_not_called()
        finally:
            if task_id:
                with app_module.auth_db() as conn:
                    conn.execute("DELETE FROM xiaozhi_tasks WHERE task_id = ?", (task_id,))
                    conn.execute(
                        "DELETE FROM xiaozhi_events WHERE user_id = ? AND payload_json LIKE ?",
                        (101, f'%{task_id}%'),
                    )

    def test_generated_video_history_is_persisted_and_user_scoped(self) -> None:
        task_ids = []
        try:
            with patch.object(app_module.VIDEO_RESOURCE_EXECUTOR, "submit") as submit:
                first = app_module.xiaozhi_create_resource_agent_task(
                    101,
                    "generated_video",
                    "STM32 GPIO 模式",
                    {"prompt": "讲解 GPIO 模式"},
                )
                second = app_module.xiaozhi_create_resource_agent_task(
                    101,
                    "generated_video",
                    "STM32 EXTI 中断",
                    {"prompt": "讲解 EXTI 中断"},
                )
                other = app_module.xiaozhi_create_resource_agent_task(
                    102,
                    "generated_video",
                    "其他用户的视频",
                    {"prompt": "不应返回给用户 101"},
                )
            submit.assert_not_called()
            task_ids = [first["taskId"], second["taskId"], other["taskId"]]
            for created in (first, second, other):
                task_id = str(created["taskId"])
                app_module.xiaozhi_update_task(
                    task_id,
                    status="complete",
                    result_json={
                        "progress": 100,
                        "currentStage": "complete",
                        "selectedResource": {
                            "type": "generated_video",
                            "title": created["title"],
                            "description": "已生成并保存",
                            "content": {
                                "videoUrl": f"/api/personalized-resources/generated-videos/{task_id}/file",
                                "posterUrl": f"/api/personalized-resources/generated-videos/{task_id}/poster",
                                "duration": 30,
                            },
                            "metadata": {"taskId": task_id},
                        },
                    },
                )

            unauthorized = self.client.get("/api/personalized-resources/generated-videos")
            self.assertEqual(unauthorized.status_code, 401)
            invalid = self.client.get(
                "/api/personalized-resources/generated-videos?status=unknown",
                headers=self.headers,
            )
            self.assertEqual(invalid.status_code, 400)
            response = self.client.get(
                "/api/personalized-resources/generated-videos?status=complete&limit=1&offset=0",
                headers=self.headers,
            )
            self.assertEqual(response.status_code, 200)
            data = response.get_json()["data"]
            self.assertGreaterEqual(data["total"], 2)
            self.assertEqual(len(data["tasks"]), 1)
            self.assertTrue(data["hasMore"])

            all_response = self.client.get(
                "/api/personalized-resources/generated-videos?status=complete&limit=100",
                headers=self.headers,
            )
            returned_ids = {task["taskId"] for task in all_response.get_json()["data"]["tasks"]}
            self.assertIn(first["taskId"], returned_ids)
            self.assertIn(second["taskId"], returned_ids)
            self.assertNotIn(other["taskId"], returned_ids)
        finally:
            if task_ids:
                with app_module.auth_db() as conn:
                    placeholders = ",".join("?" for _ in task_ids)
                    conn.execute(f"DELETE FROM xiaozhi_tasks WHERE task_id IN ({placeholders})", task_ids)
                    for task_id in task_ids:
                        conn.execute(
                            "DELETE FROM xiaozhi_events WHERE payload_json LIKE ?",
                            (f'%{task_id}%',),
                        )

    def test_admin_user_list_returns_preaggregated_user_counts(self) -> None:
        with app_module.auth_db() as conn:
            conn.execute("UPDATE users SET role = 'admin' WHERE id = 101")
            expected = {
                int(row["id"]): {
                    "reportCount": int(row["report_count"] or 0),
                    "taskCount": int(row["task_count"] or 0),
                    "eventCount": int(row["event_count"] or 0),
                }
                for row in conn.execute(
                    """
                    SELECT u.id,
                           (SELECT COUNT(*) FROM learning_profile_reports r WHERE r.user_id = u.id) AS report_count,
                           (SELECT COUNT(*) FROM xiaozhi_tasks t WHERE t.user_id = u.id) AS task_count,
                           (SELECT COUNT(*) FROM xiaozhi_events e WHERE e.user_id = u.id) AS event_count
                    FROM users u
                    WHERE LOWER(u.username) <> LOWER(?)
                    """,
                    (app_module.CODEX_PREVIEW_USERNAME,),
                ).fetchall()
            }
        try:
            response = self.client.get(
                "/api/admin/users?current=1&size=20",
                headers=self.headers,
            )
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertEqual(payload["code"], "0000")
            self.assertNotIn(
                app_module.CODEX_PREVIEW_USERNAME,
                {item["username"] for item in payload["data"]["records"]},
            )
            records = {int(item["id"]): item for item in payload["data"]["records"]}
            self.assertEqual(set(records), set(expected))
            for user_id, counts in expected.items():
                with self.subTest(user_id=user_id):
                    self.assertEqual(
                        {key: int(records[user_id][key]) for key in counts},
                        counts,
                    )
        finally:
            with app_module.auth_db() as conn:
                conn.execute("UPDATE users SET role = 'user' WHERE id = 101")

    def test_learning_path_resource_plan_version_uses_agent_source(self) -> None:
        self.assertEqual(
            app_module.LEARNING_PATH_RESOURCE_PLAN_VERSION,
            learning_agents_module.LEARNING_PATH_RESOURCE_PLAN_VERSION,
        )

    def test_runtime_settings_are_not_saved_when_connection_test_fails(self) -> None:
        with app_module.auth_db() as conn:
            conn.execute("DELETE FROM user_agent_runtime_settings WHERE user_id = ?", (101,))

        payload = {
            "enabled": True,
            "protocol": "openai",
            "baseUrl": "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2",
            "model": "missing-model",
        }
        with patch.object(app_module, "test_xiaozhi_runtime_connection", side_effect=RuntimeError("Model Not Found")):
            response = self.client.put(
                "/api/xiaozhi/runtime-settings",
                headers=self.headers,
                json=payload,
            )

        self.assertEqual(response.status_code, 502)
        self.assertIn("配置未保存", response.get_json()["msg"])
        with app_module.auth_db() as conn:
            row = conn.execute(
                "SELECT model FROM user_agent_runtime_settings WHERE user_id = ?",
                (101,),
            ).fetchone()
        self.assertIsNone(row)

    def test_auth_and_profile_crud(self) -> None:
        unauthorized = self.client.get("/api/learning-profile/profiles")
        self.assertEqual(unauthorized.status_code, 401)

        response = self.client.get("/api/learning-profile/profiles", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()["data"]
        self.assertEqual(len(data["profiles"]), 2)
        self.assertEqual(data["activeReportId"], self.profile_two["id"])

        forbidden = self.client.post(
            f"/api/learning-profile/profiles/{self.other_profile['id']}/activate",
            headers=self.headers,
        )
        self.assertEqual(forbidden.status_code, 404)

        with patch.object(
            app_module,
            "_schedule_profile_learning_path_generation",
            return_value={"taskId": "activate-path-task", "status": "queued"},
        ) as schedule_path:
            activated = self.client.post(
                f"/api/learning-profile/profiles/{self.profile_one['id']}/activate",
                headers=self.headers,
            )
        self.assertEqual(activated.status_code, 200)
        self.assertTrue(activated.get_json()["data"]["profile"]["isActive"])
        schedule_path.assert_called_once_with(101, self.profile_one["id"])

        renamed = self.client.patch(
            f"/api/learning-profile/profiles/{self.profile_one['id']}",
            headers=self.headers,
            json={"profileName": "重命名画像"},
        )
        self.assertEqual(renamed.status_code, 200)
        self.assertEqual(renamed.get_json()["data"]["profile"]["profileName"], "重命名画像")

    def test_refresh_updates_existing_profile_and_reset_keeps_history(self) -> None:
        fake_analysis = {
            "source": "llm",
            "learningStyle": "证据驱动型",
            "summary": "已结合最近考试更新",
            "strengths": ["基础概念"],
            "weaknesses": ["定时器"],
            "recommendations": ["完成定时器专项练习"],
        }
        with (
            patch.object(app_module, "xiaozhi_run_orchestrated", return_value=fake_analysis),
            patch.object(app_module, "_schedule_profile_portrait_generation"),
            patch.object(app_module, "_schedule_profile_learning_path_generation", return_value=None) as schedule_path,
        ):
            refreshed = self.client.post(
                f"/api/learning-profile/profiles/{self.profile_one['id']}/refresh",
                headers=self.headers,
                json={"instruction": "[HARNESS-E2E-20260710] 根据最近考试更新画像"},
            )
        self.assertEqual(refreshed.status_code, 200)
        updated_profile = refreshed.get_json()["data"]["profile"]
        self.assertEqual(updated_profile["id"], self.profile_one["id"])
        self.assertEqual(updated_profile["version"], self.profile_one["version"])
        self.assertEqual(updated_profile["aiAnalysis"]["summary"], fake_analysis["summary"])
        schedule_path.assert_called_once_with(101, self.profile_one["id"])

        reset = self.client.post("/api/learning-profile/reset", headers=self.headers)
        self.assertEqual(reset.status_code, 200)
        self.assertIsNone(reset.get_json()["data"]["activeReportId"])

        profiles = self.client.get("/api/learning-profile/profiles", headers=self.headers).get_json()["data"]
        self.assertEqual(len(profiles["profiles"]), 2)
        self.assertIsNone(profiles["activeReportId"])

    def test_analyze_updates_active_profile_without_replacing_saved_path(self) -> None:
        fake_analysis = {
            "source": "llm",
            "learningStyle": "实践型",
            "summary": "同一画像原位更新",
            "strengths": ["GPIO 实验"],
            "weaknesses": ["中断调试"],
            "recommendations": ["完成中断复盘"],
        }
        stage_id = "week-profile-in-place-update"
        with app_module.auth_db() as conn:
            original_active = app_module.active_profile_for_user(conn, 101)
            original_profile = app_module.get_profile_for_user(conn, 101, self.profile_one["id"])
            original_config = app_module.read_learning_path_config(conn, 101)
            app_module.activate_profile(conn, 101, self.profile_one["id"])
            config = app_module.default_learning_path_config()
            config["meta"].update(
                {
                    "profileReportId": self.profile_one["id"],
                    "taskModel": "dynamic-week-tasks-v2",
                    "taskResourceModel": app_module.LEARNING_PATH_RESOURCE_PLAN_VERSION,
                    "generationState": "complete",
                    "needsRegeneration": False,
                }
            )
            config["weeks"] = [
                {
                    "id": stage_id,
                    "order": 1,
                    "weekLabel": "第一周",
                    "title": "原画像路径",
                    "status": "current",
                    "enabled": True,
                }
            ]
            config["stages"] = {
                stage_id: {
                    "id": stage_id,
                    "title": "原路径任务",
                    "nodes": [{"id": "01", "title": "GPIO 原任务", "state": "current"}],
                }
            }
            expected_path = app_module.write_learning_path_config(conn, config, 101)
            count_before = int(
                conn.execute(
                    "SELECT COUNT(*) AS total FROM learning_profile_reports WHERE user_id = ?",
                    (101,),
                ).fetchone()["total"]
            )

        try:
            with (
                patch.object(app_module, "xiaozhi_run_orchestrated", return_value=fake_analysis),
                patch.object(app_module, "_schedule_profile_portrait_generation") as schedule_portrait,
                patch.object(app_module, "_schedule_profile_learning_path_generation", return_value=None) as schedule_path,
            ):
                response = self.client.post(
                    "/api/learning-profile/analyze",
                    headers=self.headers,
                    json={
                        "chatBackground": "根据最近任务更新当前画像",
                        "chatStudentProfile": {"学习目标": "掌握 GPIO 与中断"},
                        "completedProfileDimensions": [f"维度 {index}" for index in range(1, 11)],
                        "missingProfileDimensions": [],
                    },
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers.get("X-Profile-Save-Mode"), "updated")
            report = response.get_json()
            self.assertEqual(report["id"], self.profile_one["id"])
            self.assertEqual(report["version"], original_profile["version"])
            self.assertEqual(report["profileName"], original_profile["profileName"])
            schedule_portrait.assert_called_once_with(101, self.profile_one["id"], force=True)
            schedule_path.assert_called_once_with(101, self.profile_one["id"])

            with app_module.auth_db() as conn:
                count_after = int(
                    conn.execute(
                        "SELECT COUNT(*) AS total FROM learning_profile_reports WHERE user_id = ?",
                        (101,),
                    ).fetchone()["total"]
                )
                saved_path = app_module.read_learning_path_config(conn, 101)
            self.assertEqual(count_after, count_before)
            self.assertEqual(saved_path["weeks"], expected_path["weeks"])
            self.assertEqual(saved_path["stages"], expected_path["stages"])
            self.assertEqual(saved_path["meta"]["profileReportId"], self.profile_one["id"])
        finally:
            with app_module.auth_db() as conn:
                app_module.update_profile_report(
                    conn,
                    101,
                    self.profile_one["id"],
                    original_profile,
                    timestamp=original_profile["updatedAt"],
                )
                app_module.write_learning_path_config(conn, original_config, 101)
                if original_active:
                    app_module.activate_profile(conn, 101, original_active["id"])

    def test_completed_profile_session_updates_active_profile_in_place(self) -> None:
        workflow = {
            "source": "llm",
            "status": "complete",
            "reply": "十个画像维度已补齐。",
            "question": "十个画像维度已补齐。",
            "summary": "已完成十维画像采集",
            "completeness": 100,
            "missingProfileDimensions": [],
            "studentProfile": {f"维度 {index}": f"值 {index}" for index in range(1, 11)},
        }
        fake_analysis = {
            "source": "llm",
            "learningStyle": "证据驱动型",
            "summary": "会话完成后更新当前画像",
            "strengths": ["实践"],
            "weaknesses": ["调试"],
            "recommendations": ["完成专项练习"],
        }
        session_id = 0
        with app_module.auth_db() as conn:
            original_active = app_module.active_profile_for_user(conn, 101)
            original_profile = app_module.get_profile_for_user(conn, 101, self.profile_one["id"])
            app_module.activate_profile(conn, 101, self.profile_one["id"])
            count_before = int(
                conn.execute(
                    "SELECT COUNT(*) AS total FROM learning_profile_reports WHERE user_id = ?",
                    (101,),
                ).fetchone()["total"]
            )

        def fake_orchestrated(task_type, _topic, _payload, _user_id, _handler, **_kwargs):
            return workflow if task_type == "learning_background" else fake_analysis

        try:
            session = self.client.post(
                "/api/learning-profile/sessions",
                headers=self.headers,
                json={"title": "原位更新会话"},
            ).get_json()["data"]["session"]
            session_id = int(session["id"])
            with (
                patch.object(app_module, "xiaozhi_run_orchestrated", side_effect=fake_orchestrated),
                patch.object(app_module, "_schedule_profile_portrait_generation"),
                patch.object(
                    app_module,
                    "_schedule_profile_learning_path_generation",
                    return_value={"taskId": "path-task", "status": "queued"},
                ) as schedule_path,
            ):
                response = self.client.post(
                    f"/api/learning-profile/sessions/{session_id}/messages",
                    headers=self.headers,
                    json={"content": "这是第十个维度的信息"},
                )

            self.assertEqual(response.status_code, 200)
            data = response.get_json()["data"]
            self.assertEqual(data["profileSaveMode"], "updated")
            self.assertEqual(data["report"]["id"], self.profile_one["id"])
            self.assertEqual(data["report"]["version"], original_profile["version"])
            self.assertEqual(data["learningPathTask"]["taskId"], "path-task")
            schedule_path.assert_called_once_with(101, self.profile_one["id"])
            with app_module.auth_db() as conn:
                count_after = int(
                    conn.execute(
                        "SELECT COUNT(*) AS total FROM learning_profile_reports WHERE user_id = ?",
                        (101,),
                    ).fetchone()["total"]
                )
            self.assertEqual(count_after, count_before)
        finally:
            with app_module.auth_db() as conn:
                if session_id:
                    conn.execute("DELETE FROM learning_profile_sessions WHERE id = ?", (session_id,))
                app_module.update_profile_report(
                    conn,
                    101,
                    self.profile_one["id"],
                    original_profile,
                    timestamp=original_profile["updatedAt"],
                )
                if original_active:
                    app_module.activate_profile(conn, 101, original_active["id"])

    def test_completed_profile_schedules_only_one_background_learning_path_task(self) -> None:
        profile_id = 0
        task_id = ""
        with app_module.auth_db() as conn:
            original_active = app_module.active_profile_for_user(conn, 101)
            profile = create_profile_version(
                conn,
                101,
                {
                    "timestamp": "2026-07-16T23:40:00+08:00",
                    "chatStudentProfile": {"学习目标": "完成后台路径测试"},
                    "aiAnalysis": {"source": "llm", "summary": "后台路径测试画像"},
                },
                profile_name="后台路径测试画像",
                start_new_profile=True,
            )
            profile_id = int(profile["id"])

        try:
            with patch.object(app_module.LEARNING_PATH_GENERATION_EXECUTOR, "submit", return_value=None) as submit:
                first = app_module._schedule_profile_learning_path_generation(101, profile_id)
                second = app_module._schedule_profile_learning_path_generation(101, profile_id)

            self.assertIsNotNone(first)
            self.assertIsNotNone(second)
            task_id = str(first["taskId"])
            self.assertEqual(second["taskId"], task_id)
            self.assertEqual(first["status"], "queued")
            self.assertEqual(first["result"]["profileReportId"], profile_id)
            submit.assert_called_once()
            config_response = self.client.get("/api/learning-path/config", headers=self.headers)
            self.assertEqual(config_response.status_code, 200)
            background = config_response.get_json()["data"]["meta"]["backgroundGeneration"]
            self.assertEqual(background["taskId"], task_id)
            self.assertEqual(background["status"], "queued")
            self.assertEqual(background["profileReportId"], profile_id)
            self.assertEqual(background["completedWeeks"], 0)
            self.assertEqual(background["totalWeeks"], 6)
            with app_module.auth_db() as conn:
                task_count = int(conn.execute(
                    "SELECT COUNT(*) FROM xiaozhi_tasks WHERE user_id = ? AND task_type = 'learning_path' AND result_json LIKE ?",
                    (101, f'%\"profileReportId\": {profile_id}%'),
                ).fetchone()[0])
            self.assertEqual(task_count, 1)
        finally:
            with app_module.auth_db() as conn:
                if task_id:
                    conn.execute("DELETE FROM xiaozhi_tasks WHERE task_id = ?", (task_id,))
                    conn.execute(
                        "DELETE FROM xiaozhi_events WHERE user_id = ? AND payload_json LIKE ?",
                        (101, f'%{task_id}%'),
                    )
                if profile_id:
                    conn.execute("DELETE FROM learning_profile_reports WHERE id = ?", (profile_id,))
                if original_active:
                    app_module.activate_profile(conn, 101, original_active["id"])

    def test_completed_profile_generates_path_without_opening_learning_path_page(self) -> None:
        profile_id = 0
        task_id = ""
        background_started = threading.Event()
        release_background = threading.Event()
        fake_analysis = {
            "source": "llm",
            "learningStyle": "项目实践型",
            "summary": "画像保存后自动规划学习路径",
            "strengths": ["动手实践"],
            "weaknesses": ["中断调试"],
            "recommendations": ["完成可验证的中断实验"],
        }
        with app_module.auth_db() as conn:
            original_active = app_module.active_profile_for_user(conn, 101)
            original_config = app_module.read_learning_path_config(conn, 101)
            profile = create_profile_version(
                conn,
                101,
                {
                    "timestamp": "2026-07-17T01:00:00+08:00",
                    "chatStudentProfile": {"学习目标": "验证画像完成后自动生成路径"},
                    "aiAnalysis": fake_analysis,
                },
                profile_name="后台自动路径接口测试",
                start_new_profile=True,
            )
            profile_id = int(profile["id"])

        def fake_orchestrated(task_type, _topic, payload, _user_id, _handler, **_kwargs):
            if task_type == "profile_update":
                return fake_analysis
            if task_type != "learning_path":
                raise AssertionError(f"unexpected task type: {task_type}")
            background_started.set()
            if not release_background.wait(timeout=5):
                raise RuntimeError("test did not release background path generation")
            week_number = int(payload["weekStart"])
            existing = payload.get("existingConfig") if isinstance(payload.get("existingConfig"), dict) else {}
            weeks = list(existing.get("weeks") or [])
            stages = dict(existing.get("stages") or {})
            stage_id = f"week-background-api-{week_number}"
            weeks.append({
                "id": stage_id,
                "order": week_number,
                "weekLabel": f"第 {week_number} 周",
                "title": f"后台生成第 {week_number} 周",
                "enabled": True,
            })
            stages[stage_id] = {"id": stage_id, "title": f"第 {week_number} 周任务", "nodes": []}
            total_weeks = int(payload.get("totalWeeks") or 6)
            return {
                "config": {
                    "version": 2,
                    "meta": {
                        "profileReportId": profile_id,
                        "totalWeeks": total_weeks,
                        "generationState": "complete" if week_number == total_weeks else "partial",
                    },
                    "weeks": weeks,
                    "stages": stages,
                }
            }

        try:
            with (
                patch.object(app_module, "xiaozhi_run_orchestrated", side_effect=fake_orchestrated),
                patch.object(app_module, "_schedule_profile_portrait_generation"),
                patch.object(app_module, "_queue_learning_path_week_resource_preparation") as queue_resources,
            ):
                started_at = time.perf_counter()
                response = self.client.post(
                    "/api/learning-profile/analyze",
                    headers=self.headers,
                    json={
                        "chatBackground": "验证画像完成后后台自动规划",
                        "chatStudentProfile": {"学习目标": "掌握 STM32 中断"},
                        "completedProfileDimensions": [f"维度 {index}" for index in range(1, 11)],
                        "missingProfileDimensions": [],
                    },
                )
                response_elapsed = time.perf_counter() - started_at

                self.assertEqual(response.status_code, 200)
                self.assertLess(response_elapsed, 2.0)
                task_id = str(response.get_json()["learningPathTask"]["taskId"])
                self.assertTrue(background_started.wait(timeout=2))
                with app_module.auth_db() as conn:
                    running = conn.execute(
                        "SELECT status FROM xiaozhi_tasks WHERE task_id = ?",
                        (task_id,),
                    ).fetchone()
                self.assertIsNotNone(running)
                self.assertEqual(running["status"], "running")

                release_background.set()
                deadline = time.time() + 5
                status = ""
                while time.time() < deadline:
                    with app_module.auth_db() as conn:
                        row = conn.execute(
                            "SELECT status FROM xiaozhi_tasks WHERE task_id = ?",
                            (task_id,),
                        ).fetchone()
                    status = str(row["status"] or "") if row else ""
                    if status in {"complete", "failed"}:
                        break
                    time.sleep(0.05)

                self.assertEqual(status, "complete")
                with app_module.auth_db() as conn:
                    saved = app_module.read_learning_path_config(
                        conn,
                        101,
                        profile_report_id=profile_id,
                    )
                self.assertEqual(len(app_module._visible_learning_path_weeks(saved)), 6)
                queue_resources.assert_called_once()
        finally:
            release_background.set()
            with app_module.auth_db() as conn:
                if task_id:
                    conn.execute("DELETE FROM xiaozhi_tasks WHERE task_id = ?", (task_id,))
                    conn.execute(
                        "DELETE FROM xiaozhi_events WHERE user_id = ? AND payload_json LIKE ?",
                        (101, f'%{task_id}%'),
                    )
                if profile_id:
                    conn.execute(
                        "DELETE FROM learning_path_profile_configs WHERE user_id = ? AND profile_report_id = ?",
                        (101, profile_id),
                    )
                    conn.execute("DELETE FROM learning_profile_reports WHERE id = ?", (profile_id,))
                if original_active:
                    app_module.activate_profile(conn, 101, original_active["id"])
                app_module.write_learning_path_config(conn, original_config, 101)

    def test_background_learning_path_generates_all_weeks_before_resource_queue(self) -> None:
        with app_module.auth_db() as conn:
            original_active = app_module.active_profile_for_user(conn, 101)
            app_module.activate_profile(conn, 101, self.profile_two["id"])

        generated_payloads = []

        def fake_run(_user_id, payload, _context, **kwargs):
            generated_payloads.append({**payload, "taskId": kwargs.get("task_id")})
            week_number = int(payload["weekStart"])
            existing = payload.get("existingConfig") if isinstance(payload.get("existingConfig"), dict) else {}
            weeks = list(existing.get("weeks") or [])
            stages = dict(existing.get("stages") or {})
            stage_id = f"week-{week_number}"
            weeks.append({
                "id": stage_id,
                "order": week_number,
                "weekLabel": f"第 {week_number} 周",
                "title": f"第 {week_number} 周任务",
                "enabled": True,
            })
            stages[stage_id] = {"id": stage_id, "nodes": []}
            return {
                "config": {
                    "version": 2,
                    "meta": {
                        "profileReportId": self.profile_two["id"],
                        "totalWeeks": 4,
                        "generationState": "complete" if week_number == 4 else "partial",
                    },
                    "weeks": weeks,
                    "stages": stages,
                }
            }

        try:
            with (
                patch.object(app_module, "_read_profile_scoped_learning_path_config", return_value=app_module.default_learning_path_config()),
                patch.object(app_module, "_run_learning_path_generation", side_effect=fake_run),
                patch.object(app_module, "_queue_learning_path_week_resource_preparation") as queue_resources,
                patch.object(app_module, "xiaozhi_update_task") as update_task,
                patch.object(app_module, "xiaozhi_insert_event"),
            ):
                app_module._run_profile_learning_path_generation_task(
                    "path-background-test",
                    101,
                    self.profile_two["id"],
                    4,
                )

            self.assertEqual([item["weekStart"] for item in generated_payloads], [1, 2, 3, 4])
            self.assertTrue(all(item["prepareResources"] is False for item in generated_payloads))
            self.assertTrue(all(item["taskId"] == "path-background-test" for item in generated_payloads))
            queue_resources.assert_called_once()
            queued_config = queue_resources.call_args.args[1]
            self.assertEqual(len(queued_config["weeks"]), 4)
            final_updates = [
                call.kwargs
                for call in update_task.call_args_list
                if call.kwargs.get("status") == "complete"
            ]
            self.assertEqual(len(final_updates), 1)
            self.assertEqual(final_updates[0]["result_json"]["completedWeeks"], 4)
        finally:
            with app_module.auth_db() as conn:
                if original_active:
                    app_module.activate_profile(conn, 101, original_active["id"])

    def test_xiaozhi_refresh_updates_active_profile_in_place(self) -> None:
        fake_analysis = {
            "source": "llm",
            "learningStyle": "证据驱动型",
            "summary": "嵌小智已结合最近学习证据更新",
            "strengths": ["实验复盘"],
            "weaknesses": ["中断优先级"],
            "recommendations": ["完成中断专项练习"],
            "dimensionScores": [
                {"dimension": f"维度 {index}", "score": 70 + index}
                for index in range(1, 7)
            ],
        }
        with app_module.auth_db() as conn:
            active = app_module.activate_profile(conn, 101, self.profile_one["id"])
            count_before = int(
                conn.execute(
                    "SELECT COUNT(*) AS total FROM learning_profile_reports WHERE user_id = ?",
                    (101,),
                ).fetchone()["total"]
            )
        try:
            context = app_module.xiaozhi_latest_context(101)
            with (
                patch.object(app_module, "generate_profile_report", return_value=fake_analysis),
                patch.object(app_module, "_schedule_profile_portrait_generation"),
                patch.object(app_module, "_schedule_profile_learning_path_generation", return_value=None),
            ):
                result = app_module.xiaozhi_run_platform_agent(
                    "profile_update",
                    "根据最近学习证据更新画像",
                    context,
                    101,
                )

            with app_module.auth_db() as conn:
                count_after = int(
                    conn.execute(
                        "SELECT COUNT(*) AS total FROM learning_profile_reports WHERE user_id = ?",
                        (101,),
                    ).fetchone()["total"]
                )
                refreshed = app_module.active_profile_for_user(conn, 101)

            self.assertEqual(count_after, count_before)
            self.assertEqual(result["reportId"], active["id"])
            self.assertEqual(refreshed["id"], active["id"])
            self.assertEqual(refreshed["version"], active["version"])
            self.assertEqual(refreshed["aiAnalysis"]["summary"], fake_analysis["summary"])
            self.assertIn("resourceCalls", refreshed["learningEvidence"])
            self.assertIn("pathProgress", refreshed["learningEvidence"])
        finally:
            with app_module.auth_db() as conn:
                app_module.activate_profile(conn, 101, self.profile_two["id"])

    def test_xiaozhi_refresh_without_active_profile_creates_first_report(self) -> None:
        with app_module.auth_db() as conn:
            app_module.reset_profile_state(conn, 101, timestamp="2026-07-12T16:20:00+08:00")
            count_before = int(
                conn.execute(
                    "SELECT COUNT(*) AS total FROM learning_profile_reports WHERE user_id = ?",
                    (101,),
                ).fetchone()["total"]
            )
        created_report_id = 0
        try:
            context = app_module.xiaozhi_latest_context(101)
            fake_analysis = {
                "source": "llm",
                "learningStyle": "证据驱动型",
                "summary": "已根据现有问卷和学习证据生成第一份画像",
                "strengths": ["愿意实践"],
                "weaknesses": ["中断调试"],
                "recommendations": ["完成中断专项练习"],
                "dimensionScores": [
                    {"name": f"维度 {index}", "score": 3}
                    for index in range(1, 7)
                ],
            }
            with (
                patch.object(app_module, "generate_profile_report", return_value=fake_analysis),
                patch.object(app_module, "_schedule_profile_portrait_generation"),
                patch.object(app_module, "_schedule_profile_learning_path_generation", return_value=None),
            ):
                result = app_module.xiaozhi_run_platform_agent(
                    "profile_update",
                    "生成第一份学习画像",
                    context,
                    101,
                )
            with app_module.auth_db() as conn:
                count_after = int(
                    conn.execute(
                        "SELECT COUNT(*) AS total FROM learning_profile_reports WHERE user_id = ?",
                        (101,),
                    ).fetchone()["total"]
                )
                active = app_module.active_profile_for_user(conn, 101)
            created_report_id = int(result["reportId"])
            self.assertEqual(count_after, count_before + 1)
            self.assertEqual(active["id"], created_report_id)
            self.assertEqual(active["version"], 1)
            self.assertEqual(active["aiAnalysis"]["summary"], fake_analysis["summary"])
            self.assertIn("第一份画像", result["message"])
        finally:
            with app_module.auth_db() as conn:
                if created_report_id:
                    conn.execute("DELETE FROM learning_profile_reports WHERE id = ?", (created_report_id,))
                app_module.activate_profile(conn, 101, self.profile_two["id"])

    def test_xiaozhi_chat_can_queue_first_profile_without_active_profile(self) -> None:
        with app_module.auth_db() as conn:
            app_module.reset_profile_state(conn, 101, timestamp="2026-07-12T16:25:00+08:00")
        task_id = ""
        try:
            model_chat = {
                "intent": "chat",
                "resourceType": "none",
                "topic": "",
                "reply": "普通聊天回复",
                "source": "hermes_agent",
            }
            with (
                patch.object(app_module, "run_xiaozhi_hermes_agent", return_value=model_chat),
                patch.object(app_module.threading, "Thread") as thread_class,
            ):
                response = self.client.post(
                    "/api/xiaozhi/chat",
                    headers=self.headers,
                    json={"message": "生成第一份学习画像", "route": "/learning-profile"},
                )
            self.assertEqual(response.status_code, 200)
            data = response.get_json()["data"]
            self.assertEqual(data["intent"]["resourceType"], "profile_update")
            self.assertEqual(data["intent"]["routingSource"], "deterministic")
            self.assertEqual(len(data["cards"]), 1)
            self.assertEqual(data["cards"][0]["type"], "profile_update")
            task_id = data["cards"][0]["taskId"]
            thread_class.return_value.start.assert_called_once()
        finally:
            with app_module.auth_db() as conn:
                if task_id:
                    conn.execute("DELETE FROM xiaozhi_tasks WHERE task_id = ?", (task_id,))
                app_module.activate_profile(conn, 101, self.profile_two["id"])

    def test_xiaozhi_chat_preserves_exact_smart_tutor_follow_up(self) -> None:
        message = "\n".join(
            [
                "继续智能辅导，请基于上一轮内容判断我的理解并继续苏格拉底式追问。",
                "上一轮主题：GPIO 中断",
                "当前追问：请说出你的排查顺序。",
                "我的回答或追问：如果中断没有触发，我应该先检查哪三项？",
            ]
        )
        task_id = ""
        intent = {
            "intent": "generate_resource",
            "resourceType": "smart_tutor",
            "resourceTypes": ["smart_tutor"],
            "topic": message,
            "reply": "继续智能辅导。",
        }
        try:
            with (
                patch.object(app_module, "xiaozhi_detect_intent", return_value=intent),
                patch.object(app_module.threading, "Thread") as thread_class,
            ):
                response = self.client.post(
                    "/api/xiaozhi/chat",
                    headers=self.headers,
                    json={"message": message, "route": "/smart-tutor?xzTask=xz_previous_tutor"},
                )
            self.assertEqual(response.status_code, 200)
            data = response.get_json()["data"]
            task_id = data["cards"][0]["taskId"]
            thread_args = thread_class.call_args.kwargs["args"]
            self.assertEqual(thread_args[2], "smart_tutor")
            self.assertEqual(thread_args[3], "如果中断没有触发，我应该先检查哪三项？")
            self.assertEqual(thread_args[4]["question"], "如果中断没有触发，我应该先检查哪三项？")
            self.assertEqual(thread_args[4]["previousTaskId"], "xz_previous_tutor")
            self.assertEqual(thread_args[4]["conversationContext"], message)
            self.assertTrue(data["cards"][0]["title"].startswith("如果中断没有触发"))
        finally:
            if task_id:
                with app_module.auth_db() as conn:
                    conn.execute("DELETE FROM xiaozhi_tasks WHERE task_id = ?", (task_id,))

    def test_profile_management_runs_through_harness_skill(self) -> None:
        context = app_module.xiaozhi_latest_context(101)
        result = app_module.xiaozhi_run_orchestrated(
            "profile_management",
            "列出画像历史",
            {"topic": "列出画像历史", "action": "list"},
            101,
            lambda managed_payload, progress: app_module.xiaozhi_run_platform_agent(
                "profile_management",
                "列出画像历史",
                context,
                101,
                on_stage=progress,
                params=managed_payload,
            ),
            context=context,
            max_retries=0,
        )
        run_id = result["orchestration"]["runId"]
        try:
            self.assertEqual(result["profileManagement"]["action"], "list")
            self.assertGreaterEqual(len(result["profileManagement"]["profiles"]), 2)
            self.assertEqual(result["harness"]["skill"]["id"], "learner.profile.manage")
            self.assertEqual(result["harness"]["mcp"]["toolCalls"][0]["status"], "complete")
            self.assertEqual(result["orchestration"]["rootAgent"], "xiaozhi-companion-agent")
        finally:
            with app_module.auth_db() as conn:
                conn.execute("DELETE FROM agent_orchestration_runs WHERE run_id = ?", (run_id,))

    def test_profile_sessions_keep_chat_and_dimensions_isolated(self) -> None:
        first = self.client.post(
            "/api/learning-profile/sessions",
            headers=self.headers,
            json={"title": "会话一"},
        ).get_json()["data"]["session"]
        second = self.client.post(
            "/api/learning-profile/sessions",
            headers=self.headers,
            json={"title": "会话二"},
        ).get_json()["data"]["session"]
        workflow = {
            "source": "llm",
            "status": "collecting",
            "reply": "已记录，请继续补充学习目标。",
            "question": "已记录，请继续补充学习目标。",
            "summary": "专业/课程背景：STM32",
            "completeness": 10,
            "missingProfileDimensions": ["学习目标"],
            "studentProfile": {"专业/课程背景": "STM32"},
        }
        with patch.object(app_module, "run_learning_profile_workflow", return_value=workflow):
            response = self.client.post(
                f"/api/learning-profile/sessions/{first['id']}/messages",
                headers=self.headers,
                json={"content": "我在学 STM32"},
            )
        self.assertEqual(response.status_code, 200)
        workflow_result = response.get_json()["data"]["workflow"]
        self.assertEqual(workflow_result["orchestration"]["rootAgent"], "xiaozhi-companion-agent")
        self.assertEqual(workflow_result["harness"]["skill"]["id"], "learner.background.collect")
        first_detail = self.client.get(
            f"/api/learning-profile/sessions/{first['id']}", headers=self.headers
        ).get_json()["data"]["session"]
        second_detail = self.client.get(
            f"/api/learning-profile/sessions/{second['id']}", headers=self.headers
        ).get_json()["data"]["session"]
        self.assertEqual([item["content"] for item in first_detail["messages"]], ["我在学 STM32", workflow["reply"]])
        self.assertEqual(second_detail["messages"], [])
        self.assertEqual(first_detail["dimensions"], {"专业/课程背景": "STM32"})
        self.assertEqual(second_detail["dimensions"], {})

    def test_background_chat_stream_does_not_disguise_failures_as_llm_output(self) -> None:
        with patch.object(app_module, "generate_background_chat", side_effect=RuntimeError("model unavailable")):
            response = self.client.post(
                "/api/learning-profile/background-chat-stream",
                headers=self.headers,
                json={"messages": [{"role": "user", "content": "你好"}]},
            )
            body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("event: error", body)
        self.assertIn('"source": "error"', body)
        self.assertIn('"status": "failed"', body)
        self.assertNotIn("我是你的数字人 AI 讲师", body)

    def test_effect_assessment_uses_active_profile_and_learning_evidence(self) -> None:
        response = self.client.get("/api/effect-assessment", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()["data"]
        self.assertIn(payload["profile"]["id"], {self.profile_one["id"], self.profile_two["id"]})
        self.assertEqual(len(payload["assessment"]["labels"]), 6)
        self.assertEqual(len(payload["assessment"]["radarScores"]), 6)
        self.assertIn("pathProgress", payload["evidence"])

    def test_effect_assessment_filters_internal_task_labels_from_weak_points(self) -> None:
        assessment = app_module.effect_assessment_snapshot(
            {
                "id": self.profile_two["id"],
                "aiAnalysis": {"weaknesses": ["GPIO 配置"]},
            },
            {
                "weakPoints": [
                    "[FUNCTION-CHECK-20260712] STM32 · 视频查找智能体",
                    "STM32 - UART 中断 · 视频查找智能体",
                ],
            },
        )

        self.assertNotIn("[FUNCTION-CHECK-20260712] STM32 · 视频查找智能体", assessment["weakPoints"])
        self.assertIn("STM32 - UART 中断", assessment["weakPoints"])
        self.assertIn("GPIO 配置", assessment["weakPoints"])

    def test_learning_activity_pulse_records_server_bounded_active_time(self) -> None:
        session_id = "web_activity_api_test_101"
        try:
            with patch.object(app_module, "now_iso", return_value="2026-07-12T10:00:00+00:00"):
                started = self.client.post(
                    "/api/learning-activity/pulse",
                    headers=self.headers,
                    json={
                        "sessionId": session_id,
                        "action": "start",
                        "route": "/learning-path",
                        "routeName": "learning-path",
                    },
                )
            self.assertEqual(started.status_code, 200)

            with patch.object(app_module, "now_iso", return_value="2026-07-12T10:00:30+00:00"):
                heartbeat = self.client.post(
                    "/api/learning-activity/pulse",
                    headers=self.headers,
                    json={
                        "sessionId": session_id,
                        "action": "heartbeat",
                        "route": "/learning-path",
                        "routeName": "learning-path",
                    },
                )
            activity = heartbeat.get_json()["data"]["activity"]
            self.assertEqual(activity["activeSeconds"], 30)
            self.assertEqual(activity["addedSeconds"], 30)

            with patch.object(app_module, "now_iso", return_value="2026-07-12T10:02:30+00:00"):
                ended = self.client.post(
                    "/api/learning-activity/pulse",
                    headers=self.headers,
                    json={
                        "sessionId": session_id,
                        "action": "end",
                        "route": "/learning-path",
                        "routeName": "learning-path",
                    },
                )
            ended_activity = ended.get_json()["data"]["activity"]
            self.assertEqual(ended_activity["status"], "ended")
            self.assertEqual(ended_activity["activeSeconds"], 75)
        finally:
            with app_module.auth_db() as conn:
                conn.execute(
                    "DELETE FROM learning_activity_sessions WHERE user_id = 101 AND session_id = ?",
                    (session_id,),
                )

    def test_learning_activity_start_is_idempotent_under_concurrency(self) -> None:
        session_id = "web_activity_concurrent_101"
        payload = {
            "sessionId": session_id,
            "action": "start",
            "route": "/learning-path",
            "routeName": "learning-path",
        }

        def send_start(_index: int) -> int:
            client = app_module.app.test_client()
            return client.post(
                "/api/learning-activity/pulse",
                headers=self.headers,
                json=payload,
            ).status_code

        try:
            with ThreadPoolExecutor(max_workers=8) as pool:
                statuses = list(pool.map(send_start, range(8)))
            self.assertEqual(statuses, [200] * 8)
            with app_module.auth_db() as conn:
                count = conn.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM learning_activity_sessions
                    WHERE user_id = 101 AND session_id = ?
                    """,
                    (session_id,),
                ).fetchone()["total"]
            self.assertEqual(count, 1)
        finally:
            with app_module.auth_db() as conn:
                conn.execute(
                    "DELETE FROM learning_activity_sessions WHERE user_id = 101 AND session_id = ?",
                    (session_id,),
                )

    def test_effect_assessment_uses_actual_resource_visits_and_active_seconds(self) -> None:
        session_id = "web_effect_evidence_test_101"
        event_title = "effect-resource-visit-test"
        try:
            with app_module.auth_db() as conn:
                conn.execute(
                    """
                    INSERT INTO learning_activity_sessions
                        (session_id, user_id, route, route_name, started_at, last_seen_at,
                         active_seconds, status, ended_at, created_at, updated_at)
                    VALUES (?, 101, '/personalized-resources/video-search', 'video-search',
                            '2026-07-12T11:00:00+00:00', '2026-07-12T11:10:00+00:00',
                            600, 'ended', '2026-07-12T11:10:00+00:00',
                            '2026-07-12T11:00:00+00:00', '2026-07-12T11:10:00+00:00')
                    """,
                    (session_id,),
                )
                conn.execute(
                    """
                    INSERT INTO xiaozhi_events
                        (user_id, event_type, route, title, payload_json, created_at)
                    VALUES (101, 'page_view', '/personalized-resources/video-search?topic=GPIO', ?,
                            '{"name":"video-search"}', '2026-07-12T11:00:00+00:00')
                    """,
                    (event_title,),
                )

            response = self.client.get("/api/effect-assessment", headers=self.headers)
            self.assertEqual(response.status_code, 200)
            data = response.get_json()["data"]
            evidence = data["evidence"]
            assessment = data["assessment"]
            self.assertGreaterEqual(evidence["activeLearningSeconds"], 600)
            self.assertTrue(any(item["type"] == "video" for item in evidence["resourceVisits"]))
            self.assertGreaterEqual(assessment["activeLearningSeconds"], 600)
            self.assertIn("video", assessment["resourceTypes"])
            self.assertGreaterEqual(assessment["resourceCount"], 1)
            self.assertNotEqual(assessment["learningDurationText"], "暂无可核验时长")
        finally:
            with app_module.auth_db() as conn:
                conn.execute(
                    "DELETE FROM learning_activity_sessions WHERE user_id = 101 AND session_id = ?",
                    (session_id,),
                )
                conn.execute(
                    "DELETE FROM xiaozhi_events WHERE user_id = 101 AND title = ?",
                    (event_title,),
                )

    def test_learning_feedback_is_orchestrated_persisted_and_updates_path_evidence(self) -> None:
        task_id = "feedback-source-task-101"
        cache_key = "feedback-source-cache-101"
        run_id = ""
        try:
            with app_module.auth_db() as conn:
                conn.execute(
                    """
                    INSERT INTO xiaozhi_tasks
                        (task_id, user_id, task_type, title, prompt, status, route,
                         result_json, error, created_at, updated_at)
                    VALUES (?, 101, 'video', 'GPIO 中断学习视频', '', 'complete',
                            '/personalized-resources/video-search', ?, '', ?, ?)
                    """,
                    (
                        task_id,
                        json.dumps({"qualityEvaluation": {"score": 88, "passed": True}}, ensure_ascii=False),
                        "2026-07-12T12:00:00+08:00",
                        "2026-07-12T12:00:00+08:00",
                    ),
                )
                app_module.upsert_learning_path_node_cache(
                    conn,
                    101,
                    cache_key,
                    {
                        "status": "running",
                        "resourceType": "video",
                        "title": "GPIO 中断学习视频",
                        "route": "/personalized-resources/video-search",
                    },
                )

            response = self.client.post(
                "/api/xiaozhi/feedback",
                headers=self.headers,
                json={
                    "taskId": task_id,
                    "cacheKey": cache_key,
                    "topic": "GPIO 中断学习视频",
                    "resourceType": "video",
                    "outcome": "completed",
                    "difficulty": "appropriate",
                    "helpful": True,
                    "route": "/personalized-resources/video-search",
                },
            )
            self.assertEqual(response.status_code, 200, response.get_json())
            result = response.get_json()["data"]
            feedback = result["feedback"]
            run_id = result["orchestration"]["runId"]
            self.assertEqual(feedback["taskId"], task_id)
            self.assertEqual(feedback["outcome"], "completed")
            self.assertEqual(feedback["profileReportId"], self.profile_two["id"])
            self.assertEqual(result["harness"]["skill"]["id"], "learning.feedback.submit")
            self.assertEqual(result["harness"]["mcp"]["toolCalls"][0]["status"], "complete")

            by_cache_key = self.client.get(
                f"/api/learning-feedback?cacheKey={cache_key}",
                headers=self.headers,
            )
            self.assertEqual(by_cache_key.status_code, 200)
            self.assertEqual(by_cache_key.get_json()["data"]["feedbacks"][0]["taskId"], task_id)

            overview = self.client.get("/api/effect-assessment", headers=self.headers)
            self.assertEqual(overview.status_code, 200)
            evidence = overview.get_json()["data"]["evidence"]
            self.assertTrue(any(item["taskId"] == task_id for item in evidence["learningFeedbacks"]))
            self.assertGreaterEqual(overview.get_json()["data"]["assessment"]["evidenceUsed"]["learningFeedbacks"], 1)

            with app_module.auth_db() as conn:
                cache = conn.execute(
                    "SELECT * FROM learning_path_node_caches WHERE user_id = 101 AND cache_key = ?",
                    (cache_key,),
                ).fetchone()
                self.assertEqual(cache["status"], "complete")

            review_response = self.client.post(
                "/api/xiaozhi/feedback",
                headers=self.headers,
                json={
                    "taskId": task_id,
                    "topic": "GPIO 中断学习视频",
                    "resourceType": "video",
                    "outcome": "needs_review",
                    "difficulty": "hard",
                    "route": "/personalized-resources/video-search",
                },
            )
            self.assertEqual(review_response.status_code, 200, review_response.get_json())
            review_feedback = review_response.get_json()["data"]["feedback"]
            self.assertEqual(review_feedback["id"], feedback["id"])
            self.assertEqual(review_feedback["outcome"], "needs_review")
            self.assertEqual(review_feedback["cacheKey"], cache_key)
            self.assertEqual(review_feedback["pathCache"]["status"], "running")
            self.assertNotIn("completionSource", review_feedback["pathCache"])
            with app_module.auth_db() as conn:
                cache = conn.execute(
                    "SELECT * FROM learning_path_node_caches WHERE user_id = 101 AND cache_key = ?",
                    (cache_key,),
                ).fetchone()
                self.assertEqual(cache["status"], "running")
                feedback_count = conn.execute(
                    "SELECT COUNT(*) AS total FROM learning_feedback_records WHERE user_id = 101 AND task_id = ?",
                    (task_id,),
                ).fetchone()
                self.assertEqual(feedback_count["total"], 1)

            forbidden = self.client.post(
                "/api/xiaozhi/feedback",
                headers=self.other_headers,
                json={"taskId": task_id, "topic": "越权反馈", "outcome": "completed"},
            )
            self.assertEqual(forbidden.status_code, 404)
        finally:
            with app_module.auth_db() as conn:
                conn.execute("DELETE FROM learning_feedback_records WHERE task_id = ?", (task_id,))
                conn.execute("DELETE FROM learning_path_node_caches WHERE user_id = 101 AND cache_key = ?", (cache_key,))
                conn.execute("DELETE FROM xiaozhi_tasks WHERE task_id = ?", (task_id,))
                conn.execute("DELETE FROM xiaozhi_events WHERE user_id IN (101, 102) AND event_type = 'learning_feedback'")
                if run_id:
                    conn.execute("DELETE FROM agent_orchestration_runs WHERE run_id = ?", (run_id,))

    def test_learning_feedback_separates_resources_without_creating_path_caches(self) -> None:
        task_id = "feedback-multi-resource-task-101"
        cache_keys = (
            "resource-detail-feedback-multi-resource-task-101-video",
            "resource-detail-feedback-multi-resource-task-101-mindmap",
        )
        run_ids: list[str] = []
        try:
            with app_module.auth_db() as conn:
                conn.execute(
                    """
                    INSERT INTO xiaozhi_tasks
                        (task_id, user_id, task_type, title, prompt, status, route,
                         result_json, error, created_at, updated_at)
                    VALUES (?, 101, 'personalized_resources', 'GPIO 资源包', '', 'complete',
                            '/personalized-resources', '{}', '', ?, ?)
                    """,
                    (
                        task_id,
                        "2026-07-12T13:00:00+08:00",
                        "2026-07-12T13:00:00+08:00",
                    ),
                )
                legacy_feedback = app_module.record_learning_feedback(
                    conn,
                    101,
                    {
                        "taskId": task_id,
                        "topic": "GPIO 旧版资源反馈",
                        "resourceType": "personalized_resources",
                        "outcome": "completed",
                    },
                )

            submitted = []
            for cache_key, resource_type, outcome in (
                (cache_keys[0], "video", "completed"),
                (cache_keys[1], "mindmap", "needs_review"),
            ):
                response = self.client.post(
                    "/api/xiaozhi/feedback",
                    headers=self.headers,
                    json={
                        "taskId": task_id,
                        "cacheKey": cache_key,
                        "topic": f"GPIO {resource_type}",
                        "resourceType": resource_type,
                        "outcome": outcome,
                        "difficulty": "appropriate",
                    },
                )
                self.assertEqual(response.status_code, 200, response.get_json())
                result = response.get_json()["data"]
                run_ids.append(result["orchestration"]["runId"])
                submitted.append(result["feedback"])

            update_response = self.client.post(
                "/api/xiaozhi/feedback",
                headers=self.headers,
                json={
                    "taskId": task_id,
                    "cacheKey": cache_keys[0],
                    "topic": "GPIO video",
                    "resourceType": "video",
                    "outcome": "blocked",
                    "difficulty": "hard",
                    "note": "需要先复习中断优先级",
                },
            )
            self.assertEqual(update_response.status_code, 200, update_response.get_json())
            update_result = update_response.get_json()["data"]
            run_ids.append(update_result["orchestration"]["runId"])
            updated = update_result["feedback"]

            with app_module.auth_db() as conn:
                cache_only_updated = app_module.record_learning_feedback(
                    conn,
                    101,
                    {
                        "cacheKey": cache_keys[1],
                        "topic": "GPIO mindmap",
                        "resourceType": "mindmap",
                        "outcome": "needs_review",
                    },
                )

            self.assertNotEqual(submitted[0]["id"], submitted[1]["id"])
            self.assertEqual(submitted[0]["id"], legacy_feedback["id"])
            self.assertEqual(updated["id"], submitted[0]["id"])
            self.assertEqual(updated["cacheKey"], cache_keys[0])
            self.assertNotIn("pathCache", updated)
            self.assertEqual(cache_only_updated["id"], submitted[1]["id"])
            self.assertEqual(cache_only_updated["taskId"], task_id)

            filtered = self.client.get(
                f"/api/learning-feedback?taskId={task_id}&cacheKey={cache_keys[1]}",
                headers=self.headers,
            )
            self.assertEqual(filtered.status_code, 200)
            filtered_feedbacks = filtered.get_json()["data"]["feedbacks"]
            self.assertEqual(len(filtered_feedbacks), 1)
            self.assertEqual(filtered_feedbacks[0]["cacheKey"], cache_keys[1])
            self.assertEqual(filtered_feedbacks[0]["outcome"], "needs_review")

            by_task = self.client.get(
                f"/api/learning-feedback?taskId={task_id}",
                headers=self.headers,
            )
            self.assertEqual(by_task.status_code, 200)
            task_feedbacks = by_task.get_json()["data"]["feedbacks"]
            self.assertEqual(len(task_feedbacks), 2)
            self.assertEqual({item["cacheKey"] for item in task_feedbacks}, set(cache_keys))

            with app_module.auth_db() as conn:
                feedback_rows = conn.execute(
                    """
                    SELECT cache_key, outcome
                    FROM learning_feedback_records
                    WHERE user_id = 101 AND task_id = ?
                    """,
                    (task_id,),
                ).fetchall()
                fake_path_rows = conn.execute(
                    """
                    SELECT cache_key
                    FROM learning_path_node_caches
                    WHERE user_id = 101 AND cache_key IN (?, ?)
                    """,
                    cache_keys,
                ).fetchall()
            self.assertEqual(len(feedback_rows), 2)
            self.assertEqual(
                {row["cache_key"]: row["outcome"] for row in feedback_rows},
                {cache_keys[0]: "blocked", cache_keys[1]: "needs_review"},
            )
            self.assertEqual(fake_path_rows, [])
        finally:
            with app_module.auth_db() as conn:
                conn.execute("DELETE FROM learning_feedback_records WHERE task_id = ?", (task_id,))
                conn.execute("DELETE FROM xiaozhi_tasks WHERE task_id = ?", (task_id,))
                conn.execute(
                    "DELETE FROM xiaozhi_events WHERE user_id = 101 AND event_type = 'learning_feedback' AND payload_json LIKE ?",
                    (f'%"taskId": "{task_id}"%',),
                )
                for run_id in run_ids:
                    conn.execute("DELETE FROM agent_orchestration_runs WHERE run_id = ?", (run_id,))

    def test_learning_feedback_query_normalizes_non_ascii_resource_key(self) -> None:
        task_id = "feedback-non-ascii-key-task-101"
        raw_cache_keys = (
            f"resource-detail:task:{task_id}:GPIO 讲义",
            f"resource-detail:task:{task_id}:GPIO 导图",
        )
        normalized_cache_keys = tuple(
            app_module.normalize_learning_feedback_cache_key(value)
            for value in raw_cache_keys
        )
        self.assertNotEqual(normalized_cache_keys[0], normalized_cache_keys[1])
        self.assertEqual(
            app_module.normalize_learning_feedback_cache_key("resource-detail:plain-ascii"),
            "resource-detail:plain-ascii",
        )
        run_ids: list[str] = []
        try:
            with app_module.auth_db() as conn:
                conn.execute(
                    """
                    INSERT INTO xiaozhi_tasks
                        (task_id, user_id, task_type, title, prompt, status, route,
                         result_json, error, created_at, updated_at)
                    VALUES (?, 101, 'personalized_resources', 'GPIO 资源包', '', 'complete',
                            '/personalized-resources', '{}', '', ?, ?)
                    """,
                    (
                        task_id,
                        "2026-07-12T14:00:00+08:00",
                        "2026-07-12T14:00:00+08:00",
                    ),
                )

            for index, raw_cache_key in enumerate(raw_cache_keys):
                response = self.client.post(
                    "/api/xiaozhi/feedback",
                    headers=self.headers,
                    json={
                        "taskId": task_id,
                        "cacheKey": raw_cache_key,
                        "topic": "GPIO 讲义" if index == 0 else "GPIO 导图",
                        "resourceType": "document" if index == 0 else "mindmap",
                        "outcome": "completed" if index == 0 else "needs_review",
                    },
                )
                self.assertEqual(response.status_code, 200, response.get_json())
                result = response.get_json()["data"]
                run_ids.append(result["orchestration"]["runId"])
                self.assertEqual(result["feedback"]["cacheKey"], normalized_cache_keys[index])

                restored = self.client.get(
                    "/api/learning-feedback",
                    headers=self.headers,
                    query_string={"taskId": task_id, "cacheKey": raw_cache_key},
                )
                self.assertEqual(restored.status_code, 200, restored.get_json())
                feedbacks = restored.get_json()["data"]["feedbacks"]
                self.assertEqual(len(feedbacks), 1)
                self.assertEqual(feedbacks[0]["cacheKey"], normalized_cache_keys[index])

            by_task = self.client.get(
                "/api/learning-feedback",
                headers=self.headers,
                query_string={"taskId": task_id},
            )
            self.assertEqual(by_task.status_code, 200, by_task.get_json())
            self.assertEqual(len(by_task.get_json()["data"]["feedbacks"]), 2)
        finally:
            with app_module.auth_db() as conn:
                conn.execute("DELETE FROM learning_feedback_records WHERE task_id = ?", (task_id,))
                conn.execute("DELETE FROM xiaozhi_tasks WHERE task_id = ?", (task_id,))
                conn.execute(
                    "DELETE FROM xiaozhi_events WHERE user_id = 101 AND event_type = 'learning_feedback' AND payload_json LIKE ?",
                    (f'%"taskId": "{task_id}"%',),
                )
                for run_id in run_ids:
                    conn.execute("DELETE FROM agent_orchestration_runs WHERE run_id = ?", (run_id,))

    def test_stage_detail_resolves_the_requested_saved_week(self) -> None:
        config = {
            "weeks": [
                {"id": "week-one", "order": 1, "weekLabel": "第一周", "title": "GPIO", "status": "current"},
                {"id": "week-two", "order": 2, "weekLabel": "第二周", "title": "串口调试", "status": "locked"},
            ],
            "stages": {
                "week-one": {"id": "week-one", "nodes": [{"id": "01", "resourceType": "video"}]},
                "week-two": {
                    "id": "week-two",
                    "nodes": [
                        {"id": "01", "resourceType": "question-bank"},
                        {"id": "02", "resourceType": "mcu"},
                    ],
                },
            },
        }
        selected = app_module.xiaozhi_resolve_learning_path_stage(config, "请细化第二周的任务")
        self.assertEqual(selected["id"], "week-two")
        self.assertEqual(selected["weekLabel"], "第二周")
        self.assertEqual(selected["resourceTypes"], ["quiz", "simulator"])

    def test_learning_path_resource_cache_key_tracks_task_semantics(self) -> None:
        first = app_module._learning_path_resource_cache_key(
            "week-1-gpio",
            "01",
            39,
            "mindmap",
            "GPIO 时钟使能检查清单",
        )
        repeated = app_module._learning_path_resource_cache_key(
            "week-1-gpio",
            "01",
            39,
            "mindmap",
            "GPIO 时钟使能检查清单",
        )
        changed = app_module._learning_path_resource_cache_key(
            "week-1-gpio",
            "01",
            39,
            "mindmap",
            "GPIO 模式配置知识导图",
        )

        self.assertEqual(first, repeated)
        self.assertNotEqual(first, changed)
        self.assertIn("-mindmap-", first)
        self.assertTrue(first.endswith(app_module.LEARNING_PATH_RESOURCE_PLAN_VERSION))
        fingerprint = first.removesuffix(app_module.LEARNING_PATH_RESOURCE_PLAN_VERSION).rstrip("-").rsplit("-", 1)[-1]
        self.assertEqual(len(fingerprint), 12)
        self.assertTrue(all(character in "0123456789abcdef" for character in fingerprint))

    def test_legacy_completed_resource_with_failed_quality_is_requeued_once(self) -> None:
        stage_id = "week-quality-repair"
        task_id = "legacy-quality-rejected-task-101"
        cache_key = "legacy-quality-rejected-cache-101"
        with app_module.auth_db() as conn:
            original_config = app_module.read_learning_path_config(conn, 101)
        config = app_module.default_learning_path_config()
        config["meta"].update({"needsRegeneration": False, "generationState": "complete"})
        config["weeks"] = [{
            "id": stage_id,
            "order": 1,
            "weekLabel": "第一周",
            "title": "质量修复测试",
            "status": "current",
            "enabled": True,
        }]
        config["stages"] = {
            stage_id: {
                "id": stage_id,
                "weekLabel": "第一周",
                "title": "第一周具体学习任务",
                "nodes": [{
                    "id": "01",
                    "label": "01",
                    "title": "历史低质量视频",
                    "description": "自动重新生成",
                    "state": "current",
                    "resourceType": "video",
                    "cacheKey": cache_key,
                    "actionRoute": "/personalized-resources/video-search",
                    "resourceTask": {"taskId": task_id, "status": "complete"},
                    "order": 1,
                }],
                "resourcePreparation": {
                    "version": app_module.LEARNING_PATH_RESOURCE_PLAN_VERSION,
                    "status": "complete",
                    "profileReportId": self.profile_two["id"],
                    "plannedCount": 1,
                    "resolvedCount": 1,
                    "totalCount": 1,
                },
            }
        }
        try:
            with app_module.auth_db() as conn:
                app_module.write_learning_path_config(conn, config, 101)
                conn.execute(
                    """
                    INSERT INTO xiaozhi_tasks
                        (task_id, user_id, task_type, title, prompt, status, route,
                         result_json, error, created_at, updated_at)
                    VALUES (?, 101, 'video', '历史低质量视频', '', 'complete',
                            '/personalized-resources/video-search', ?, '', ?, ?)
                    """,
                    (
                        task_id,
                        json.dumps({
                            "selectedResource": {
                                "type": "video",
                                "metadata": {"results": []},
                                "qualityEvaluation": {"score": 18, "passed": False},
                            },
                            "orchestration": {"review": {"passed": True}},
                        }, ensure_ascii=False),
                        "2026-07-12T12:00:00+08:00",
                        "2026-07-12T12:00:00+08:00",
                    ),
                )
                app_module.upsert_learning_path_node_cache(
                    conn,
                    101,
                    cache_key,
                    {"status": "complete", "agentTaskId": task_id},
                )

            status = app_module.prepare_learning_path_stage_resources_for_user(
                101,
                stage_id,
                use_llm=False,
                advance=False,
            )
            repaired_node = status["stage"]["nodes"][0]
            self.assertEqual(status["preparation"]["status"], "running")
            self.assertEqual(repaired_node["resourceTask"]["status"], "waiting")
            self.assertNotIn("taskId", repaired_node["resourceTask"])
            with app_module.auth_db() as conn:
                stored = app_module.read_learning_path_config(conn, 101)
                cached = conn.execute(
                    "SELECT * FROM learning_path_node_caches WHERE user_id = 101 AND cache_key = ?",
                    (cache_key,),
                ).fetchone()
                old_task = conn.execute(
                    "SELECT task_id FROM xiaozhi_tasks WHERE task_id = ?",
                    (task_id,),
                ).fetchone()
            self.assertEqual(stored["stages"][stage_id]["resourcePreparation"]["status"], "running")
            self.assertEqual(cached["status"], "waiting")
            self.assertIsNotNone(old_task)
        finally:
            with app_module.auth_db() as conn:
                app_module.write_learning_path_config(conn, original_config, 101)
                conn.execute("DELETE FROM learning_path_node_caches WHERE user_id = 101 AND cache_key = ?", (cache_key,))
                conn.execute("DELETE FROM xiaozhi_tasks WHERE task_id = ?", (task_id,))
        with self.assertRaises(LookupError):
            app_module.xiaozhi_resolve_learning_path_stage(
                config,
                "细化任务",
                {"stageId": "missing-week"},
            )

    def test_xiaozhi_profile_context_keeps_profile_and_evidence_provenance(self) -> None:
        profile = app_module.xiaozhi_profile_with_evidence(
            {
                "profileReportId": 77,
                "profile": {"id": 77, "updatedAt": "2026-07-12T12:00:00+00:00"},
                "learningEvidence": {
                    "evidenceVersion": "evidence-77",
                    "updatedAt": "2026-07-12T12:05:00+00:00",
                    "resourceVisits": [{"type": "mindmap"}],
                },
            }
        )
        self.assertEqual(profile["_profileReportId"], 77)
        self.assertEqual(profile["learningEvidence"]["evidenceVersion"], "evidence-77")
        self.assertEqual(profile["learningEvidence"]["resourceVisits"][0]["type"], "mindmap")

    def test_effect_assessment_merge_keeps_deterministic_metrics_authoritative(self) -> None:
        snapshot = {
            "summary": "证据化总结",
            "achievementRate": 62.5,
            "masteryRate": 71.0,
            "radarScores": [2.0, 2.5, 3.0, 3.2, 3.6, 2.8],
            "knowledgeHeatmap": [{"knowledgePoint": "GPIO", "masteryRate": 60}],
            "pathAdjustmentPlan": {
                "planId": "effect-test",
                "reason": "优先巩固 GPIO",
                "tasks": [{"acceptanceCriteria": "完成专项练习"}],
            },
        }
        merged = app_module.merge_xiaozhi_effect_assessment(
            snapshot,
            {
                "source": "llm",
                "summary": "模型诊断总结",
                "scores": {"achievementRate": 99, "unsupported": 1},
            },
        )
        self.assertEqual(merged["achievementRate"], 62.5)
        self.assertEqual(merged["masteryRate"], 71.0)
        self.assertEqual(merged["scores"]["achievementRate"], 62.5)
        self.assertEqual(merged["scores"]["masteryRate"], 71.0)
        self.assertEqual(merged["summary"], "模型诊断总结")
        self.assertEqual(merged["recommendations"], ["完成专项练习"])
        self.assertEqual(merged["adjustments"], ["优先巩固 GPIO"])

    def test_corrupted_knowledge_points_are_excluded_from_learning_evidence(self) -> None:
        self.assertEqual(app_module.normalize_learning_weak_point("Linux???"), "")
        self.assertEqual(app_module.normalize_learning_weak_point("MCU����"), "")
        self.assertEqual(
            app_module.normalize_learning_weak_point("GPIO 中断配置"),
            "GPIO 中断配置",
        )

    def test_effect_assessment_adjustment_is_applied_through_harness_once(self) -> None:
        stage_id = "week-effect-adjustment"
        experiment_id = "effect-adjustment-weak-gpio"
        config = app_module.default_learning_path_config()
        config["meta"].update({"needsRegeneration": False, "generationState": "complete"})
        config["weeks"] = [
            {
                "id": stage_id,
                "order": 1,
                "weekLabel": "第一周",
                "title": "GPIO 专项学习",
                "description": "根据效果评估动态调整",
                "status": "current",
                "enabled": True,
            }
        ]
        config["stages"] = {
            stage_id: {
                "id": stage_id,
                "weekLabel": "第一周",
                "title": "第一周具体学习任务",
                "nodes": [
                    {
                        "id": "01",
                        "label": "01",
                        "title": "原始学习任务",
                        "description": "完成 GPIO 基础学习",
                        "state": "current",
                        "resourceType": "video",
                        "order": 1,
                    }
                ],
            }
        }
        with app_module.auth_db() as conn:
            app_module.activate_profile(conn, 101, self.profile_two["id"])
            app_module.write_learning_path_config(conn, config, 101)
            conn.execute(
                """
                INSERT INTO mcu_experiments
                    (user_id, experiment_id, experiment_name, passed, weak_points, run_data, created_at)
                VALUES (101, ?, 'GPIO 中断实验', 0, ?, '{}', '2026-07-11T21:00:00+08:00')
                """,
                (experiment_id, json.dumps(["GPIO 中断配置"], ensure_ascii=False)),
            )

        try:
            overview = self.client.get("/api/effect-assessment", headers=self.headers)
            self.assertEqual(overview.status_code, 200)
            assessment = overview.get_json()["data"]["assessment"]
            self.assertIn("achievementRate", assessment)
            self.assertIn("masteryRate", assessment)
            self.assertTrue(assessment["knowledgeHeatmap"])
            plan = assessment["pathAdjustmentPlan"]
            self.assertTrue(plan["canApply"])
            self.assertEqual(plan["targetWeekId"], stage_id)

            first = self.client.post(
                "/api/effect-assessment/apply-adjustment",
                headers=self.headers,
                json={"profileId": self.profile_two["id"], "planId": plan["planId"]},
            )
            self.assertEqual(first.status_code, 200)
            first_data = first.get_json()["data"]
            self.assertFalse(first_data["alreadyApplied"])
            self.assertTrue(first_data["runId"])
            self.assertEqual(first_data["orchestration"]["rootAgent"], "xiaozhi-companion-agent")
            self.assertEqual(first_data["harness"]["skill"]["id"], "learning.effect.evaluate")
            self.assertEqual(first_data["harness"]["skill"]["mcpTool"], "learning.effect.evaluate")
            self.assertTrue(first_data["orchestration"]["handoffs"])
            self.assertIn("score", first_data["orchestration"]["review"])
            self.assertIn("sensitiveContentDetected", first_data["orchestration"]["review"])

            with app_module.auth_db() as conn:
                stored = app_module.read_learning_path_config(conn, 101)
                stored_nodes = stored["stages"][stage_id]["nodes"]
                adjustment_nodes = [
                    item for item in stored_nodes
                    if item.get("resourceSelectionSource") == "effect-assessment"
                ]
                assessment_count = conn.execute(
                    "SELECT COUNT(*) AS total FROM learning_effect_assessments WHERE user_id = 101 AND profile_report_id = ?",
                    (self.profile_two["id"],),
                ).fetchone()["total"]
            self.assertTrue(adjustment_nodes)
            self.assertTrue(all(item.get("resourceParams", {}).get("assessmentPlanId") == plan["planId"] for item in adjustment_nodes))
            self.assertEqual(stored["stages"][stage_id]["resourcePreparation"]["status"], "running")
            self.assertEqual(assessment_count, 1)

            second = self.client.post(
                "/api/effect-assessment/apply-adjustment",
                headers=self.headers,
                json={"profileId": self.profile_two["id"], "planId": plan["planId"]},
            )
            self.assertEqual(second.status_code, 200)
            self.assertTrue(second.get_json()["data"]["alreadyApplied"])
            with app_module.auth_db() as conn:
                repeated_nodes = app_module.read_learning_path_config(conn, 101)["stages"][stage_id]["nodes"]
                repeated_count = conn.execute(
                    "SELECT COUNT(*) AS total FROM learning_effect_assessments WHERE user_id = 101 AND profile_report_id = ?",
                    (self.profile_two["id"],),
                ).fetchone()["total"]
            self.assertEqual(len(repeated_nodes), len(stored_nodes))
            self.assertEqual(repeated_count, 1)
        finally:
            with app_module.auth_db() as conn:
                conn.execute(
                    "DELETE FROM mcu_experiments WHERE user_id = 101 AND experiment_id = ?",
                    (experiment_id,),
                )

    def test_effect_assessment_review_failure_does_not_write_path(self) -> None:
        stage_id = "week-effect-review-rejected"
        plan_id = "effect-review-rejected"
        with app_module.auth_db() as conn:
            original_config = app_module.read_learning_path_config(conn, 101)
            original_assessment_count = conn.execute(
                "SELECT COUNT(*) AS total FROM learning_effect_assessments WHERE user_id = 101 AND profile_report_id = ?",
                (self.profile_two["id"],),
            ).fetchone()["total"]
            app_module.activate_profile(conn, 101, self.profile_two["id"])
            config = app_module.default_learning_path_config()
            config["weeks"] = [{"id": stage_id, "order": 1, "weekLabel": "Week 1", "enabled": True}]
            config["stages"] = {
                stage_id: {
                    "id": stage_id,
                    "weekLabel": "Week 1",
                    "title": "Review guard",
                    "nodes": [
                        {
                            "id": "01",
                            "label": "01",
                            "title": "Existing task",
                            "description": "Keep this task unchanged",
                            "state": "current",
                            "resourceType": "video",
                            "order": 1,
                        }
                    ],
                }
            }
            app_module.write_learning_path_config(conn, config, 101)

        assessment = {
            "summary": "Rejected adjustment",
            "achievementRate": 50,
            "masteryRate": 50,
            "radarScores": [2, 2, 2, 2, 2, 2],
            "pathAdjustmentPlan": {
                "planId": plan_id,
                "canApply": True,
                "targetWeekId": stage_id,
                "targetWeekLabel": "Week 1",
                "tasks": [
                    {
                        "nodeId": "effect-01",
                        "title": "Must not be written",
                        "resourceType": "question-bank",
                        "acceptanceCriteria": "Pass review first",
                    }
                ],
            },
        }
        failed_result = {
            "message": "review failed",
            "orchestration": {
                "status": "failed",
                "runId": "run-effect-review-rejected",
                "review": {"passed": False, "issues": ["review rejected"]},
            },
        }
        try:
            with (
                patch.object(app_module, "effect_assessment_snapshot", return_value=assessment),
                patch.object(app_module.DEFAULT_AGENT_HARNESS, "run", return_value=failed_result),
                patch.object(app_module, "xiaozhi_persist_orchestration"),
            ):
                response = self.client.post(
                    "/api/effect-assessment/apply-adjustment",
                    headers=self.headers,
                    json={"profileId": self.profile_two["id"], "planId": plan_id},
                )

            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.get_json()["errorCode"], "AGENT_REVIEW_FAILED")
            with app_module.auth_db() as conn:
                stored = app_module.read_learning_path_config(conn, 101)
                node_ids = [item.get("id") for item in stored["stages"][stage_id]["nodes"]]
                assessment_count = conn.execute(
                    "SELECT COUNT(*) AS total FROM learning_effect_assessments WHERE user_id = 101 AND profile_report_id = ?",
                    (self.profile_two["id"],),
                ).fetchone()["total"]
            self.assertEqual(node_ids, ["01"])
            self.assertEqual(assessment_count, original_assessment_count)
        finally:
            with app_module.auth_db() as conn:
                app_module.write_learning_path_config(conn, original_config, 101)
                app_module.activate_profile(conn, 101, self.profile_two["id"])

    def test_question_ai_score_review_failure_is_not_returned_as_local_success(self) -> None:
        failed = app_module.SkillReviewError(
            {
                "message": "review failed",
                "orchestration": {
                    "status": "failed",
                    "runId": "run-question-score-rejected",
                    "review": {"passed": False, "issues": ["review rejected"]},
                },
            }
        )
        with patch.object(app_module, "xiaozhi_run_orchestrated", side_effect=failed):
            response = self.client.post(
                "/api/question-generator/ai-score",
                headers=self.headers,
                json={
                    "title": "Review guard",
                    "detail": [
                        {
                            "type": "single_choice",
                            "answer": "A",
                            "user_answer": "A",
                            "full_score": 5,
                        }
                    ],
                },
            )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.get_json()["errorCode"], "AGENT_REVIEW_FAILED")

    def test_profile_portrait_is_persisted_and_access_is_isolated(self) -> None:
        with app_module.auth_db() as conn:
            portrait_profile = create_profile_version(
                conn,
                101,
                {
                    "timestamp": "2026-07-11T20:00:00+08:00",
                    "chatStudentProfile": {"学习目标": "完成 GPIO 综合实验"},
                    "aiAnalysis": {"source": "llm", "summary": "头像持久化测试画像"},
                },
                profile_name="头像持久化测试",
            )
            self.addCleanup(self._cleanup_test_profile, portrait_profile["id"])
            original_updated_at = conn.execute(
                "SELECT updated_at FROM learning_profile_reports WHERE id = ?",
                (portrait_profile["id"],),
            ).fetchone()["updated_at"]

        image_bytes = b"\x89PNG\r\n\x1a\n" + (b"portrait-test" * 200)
        generated = {
            "imageBytes": image_bytes,
            "mimeType": "image/png",
            "source": "image2-test",
        }
        with patch.object(app_module.PROFILE_PORTRAIT_EXECUTOR, "submit") as submitter:
            response = self.client.post(
                f"/api/learning-profile/profiles/{portrait_profile['id']}/portrait",
                headers=self.headers,
            )
        self.assertEqual(response.status_code, 202)
        self.assertTrue(response.get_json()["data"]["started"])
        self.assertEqual(submitter.call_count, 1)
        worker, *worker_args = submitter.call_args.args
        with patch.object(app_module, "generate_profile_portrait", return_value=generated) as generator:
            worker(*worker_args)
        self.assertEqual(generator.call_count, 1)

        status_response = self.client.get(
            f"/api/learning-profile/profiles/{portrait_profile['id']}/portrait/status",
            headers=self.headers,
        )
        self.assertEqual(status_response.status_code, 200)
        portrait = status_response.get_json()["data"]["portrait"]
        stable_url = f"/api/learning-profile/profiles/{portrait_profile['id']}/portrait"
        self.assertEqual(portrait["url"], stable_url)
        self.assertEqual(portrait["status"], "ready")

        with app_module.auth_db() as conn:
            stored = conn.execute(
                """
                SELECT image_blob, mime_type, source, status
                FROM learning_profile_portraits
                WHERE report_id = ? AND user_id = ?
                """,
                (portrait_profile["id"], 101),
            ).fetchone()
            report_row = conn.execute(
                "SELECT report_json, updated_at FROM learning_profile_reports WHERE id = ?",
                (portrait_profile["id"],),
            ).fetchone()
        self.assertEqual(bytes(stored["image_blob"]), image_bytes)
        self.assertEqual(stored["mime_type"], "image/png")
        self.assertEqual(stored["source"], "image2-test")
        self.assertEqual(stored["status"], "ready")
        self.assertEqual(json.loads(report_row["report_json"])["portrait"]["url"], stable_url)
        self.assertEqual(report_row["updated_at"], original_updated_at)

        unauthorized = self.client.get(stable_url)
        self.assertEqual(unauthorized.status_code, 401)
        forbidden = self.client.get(stable_url, headers=self.other_headers)
        self.assertEqual(forbidden.status_code, 404)
        image_response = self.client.get(stable_url, headers=self.headers)
        self.assertEqual(image_response.status_code, 200)
        self.assertEqual(image_response.data, image_bytes)
        self.assertEqual(image_response.mimetype, "image/png")

        legacy_url = f"/api/learning-profile/portraits/profile-{portrait_profile['id']}.png"
        self.assertEqual(self.client.get(legacy_url, headers=self.headers).status_code, 200)
        self.assertEqual(self.client.get(legacy_url, headers=self.other_headers).status_code, 404)

        with patch.object(app_module.PROFILE_PORTRAIT_EXECUTOR, "submit") as cached_submitter:
            cached = self.client.post(stable_url, headers=self.headers)
        self.assertEqual(cached.status_code, 200)
        self.assertFalse(cached.get_json()["data"]["started"])
        cached_submitter.assert_not_called()

    def test_profile_portrait_generation_is_idempotent_and_failure_is_persisted(self) -> None:
        with app_module.auth_db() as conn:
            portrait_profile = create_profile_version(
                conn,
                101,
                {
                    "timestamp": "2026-07-11T20:05:00+08:00",
                    "aiAnalysis": {"source": "llm", "summary": "portrait queue test"},
                },
                profile_name="portrait queue test",
            )
            self.addCleanup(self._cleanup_test_profile, portrait_profile["id"])

        endpoint = f"/api/learning-profile/profiles/{portrait_profile['id']}/portrait"
        with patch.object(app_module.PROFILE_PORTRAIT_EXECUTOR, "submit") as submitter:
            first = self.client.post(endpoint, headers=self.headers)
            second = self.client.post(endpoint, headers=self.headers)

        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 202)
        self.assertTrue(first.get_json()["data"]["started"])
        self.assertFalse(second.get_json()["data"]["started"])
        self.assertEqual(submitter.call_count, 1)

        worker, *worker_args = submitter.call_args.args
        with patch.object(app_module, "generate_profile_portrait", side_effect=RuntimeError("relay timeout")):
            worker(*worker_args)

        failed = self.client.get(f"{endpoint}/status", headers=self.headers)
        self.assertEqual(failed.status_code, 200)
        failed_portrait = failed.get_json()["data"]["portrait"]
        self.assertEqual(failed_portrait["status"], "failed")
        self.assertIn("relay timeout", failed_portrait["error"])
        self.assertEqual(failed_portrait["attemptCount"], 1)

        with patch.object(app_module.PROFILE_PORTRAIT_EXECUTOR, "submit") as retry_submitter:
            retry = self.client.post(endpoint, json={"force": True}, headers=self.headers)
        self.assertEqual(retry.status_code, 202)
        self.assertTrue(retry.get_json()["data"]["started"])
        self.assertEqual(retry.get_json()["data"]["portrait"]["attemptCount"], 2)
        self.assertEqual(retry_submitter.call_count, 1)

    def test_interrupted_portrait_is_released_and_list_uses_blob_status(self) -> None:
        with app_module.auth_db() as conn:
            portrait_profile = create_profile_version(
                conn,
                101,
                {
                    "timestamp": "2026-07-11T20:08:00+08:00",
                    "aiAnalysis": {"source": "llm", "summary": "interrupted portrait"},
                },
                profile_name="interrupted portrait",
            )
            self.addCleanup(self._cleanup_test_profile, portrait_profile["id"])
            conn.execute(
                """
                INSERT INTO learning_profile_portraits
                    (report_id, user_id, image_blob, mime_type, source, status, error,
                     generation_token, attempt_count, created_at, updated_at)
                VALUES (?, 101, NULL, 'image/png', '', 'generating', '', 'old-worker', 1,
                        '2026-07-11T20:08:00+08:00', '2026-07-11T20:08:00+08:00')
                """,
                (portrait_profile["id"],),
            )
            self.assertEqual(recover_interrupted_learning_profile_portraits(conn), 1)

        missing_response = self.client.get("/api/learning-profile/profiles", headers=self.headers)
        self.assertEqual(missing_response.status_code, 200)
        missing_profile = next(
            item
            for item in missing_response.get_json()["data"]["profiles"]
            if item["id"] == portrait_profile["id"]
        )
        self.assertEqual(missing_profile["portrait"]["status"], "missing")
        self.assertFalse(missing_profile["portrait"]["persisted"])

        image_bytes = b"\x89PNG\r\n\x1a\n" + (b"restart-recovery" * 200)
        with app_module.auth_db() as conn:
            conn.execute(
                """
                UPDATE learning_profile_portraits
                SET image_blob = ?, status = 'ready', source = 'image2-test',
                    generation_token = '', updated_at = '2026-07-11T20:09:00+08:00'
                WHERE report_id = ? AND user_id = 101
                """,
                (sqlite3.Binary(image_bytes), portrait_profile["id"]),
            )

        ready_response = self.client.get("/api/learning-profile/profiles", headers=self.headers)
        ready_profile = next(
            item
            for item in ready_response.get_json()["data"]["profiles"]
            if item["id"] == portrait_profile["id"]
        )
        self.assertEqual(ready_profile["portrait"]["status"], "ready")
        self.assertTrue(ready_profile["portrait"]["persisted"])
        self.assertEqual(
            ready_profile["portrait"]["url"],
            f"/api/learning-profile/profiles/{portrait_profile['id']}/portrait",
        )

    def test_legacy_portrait_file_is_backfilled_into_database(self) -> None:
        with app_module.auth_db() as conn:
            legacy_profile = create_profile_version(
                conn,
                101,
                {
                    "timestamp": "2026-07-11T20:10:00+08:00",
                    "aiAnalysis": {"source": "llm", "summary": "旧头像迁移测试画像"},
                },
                profile_name="旧头像迁移测试",
            )
            self.addCleanup(self._cleanup_test_profile, legacy_profile["id"])
            original_updated_at = conn.execute(
                "SELECT updated_at FROM learning_profile_reports WHERE id = ?",
                (legacy_profile["id"],),
            ).fetchone()["updated_at"]

        image_bytes = b"\x89PNG\r\n\x1a\n" + (b"legacy-portrait" * 200)
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as portrait_dir:
            Path(portrait_dir, f"profile-{legacy_profile['id']}.png").write_bytes(image_bytes)
            with app_module.auth_db() as conn:
                migrated = backfill_learning_profile_portrait_files(conn, portrait_dir)
                stored = conn.execute(
                    "SELECT image_blob, source, status FROM learning_profile_portraits WHERE report_id = ?",
                    (legacy_profile["id"],),
                ).fetchone()
                report_row = conn.execute(
                    "SELECT report_json, updated_at FROM learning_profile_reports WHERE id = ?",
                    (legacy_profile["id"],),
                ).fetchone()

        self.assertEqual(migrated, 1)
        self.assertEqual(bytes(stored["image_blob"]), image_bytes)
        self.assertEqual(stored["source"], "filesystem-migration")
        self.assertEqual(stored["status"], "ready")
        portrait = json.loads(report_row["report_json"])["portrait"]
        self.assertEqual(
            portrait["url"],
            f"/api/learning-profile/profiles/{legacy_profile['id']}/portrait",
        )
        self.assertEqual(report_row["updated_at"], original_updated_at)

    def test_complete_saved_path_is_reused_after_same_profile_data_changes(self) -> None:
        with app_module.auth_db() as conn:
            active_profile = app_module.active_profile_for_user(conn, 101)
        config = app_module.default_learning_path_config()
        config["meta"].update(
            {
                "needsRegeneration": False,
                "generationState": "complete",
                "taskModel": "dynamic-week-tasks-v2",
                "taskResourceModel": app_module.LEARNING_PATH_RESOURCE_PLAN_VERSION,
                "profileReportId": active_profile["id"],
                "profileUpdatedAt": "outdated-profile-version",
                "learningEvidenceVersion": "outdated-evidence-version",
            }
        )
        config["weeks"] = [
            {
                "id": "week-1-persisted",
                "order": 1,
                "weekLabel": "第一周",
                "title": "数据库中的已保存路径",
                "status": "current",
                "enabled": True,
            }
        ]
        with app_module.auth_db() as conn:
            saved = app_module.write_learning_path_config(conn, config, 101)
            saved_at = saved["meta"]["savedAt"]

        first = self.client.get("/api/learning-path/config", headers=self.headers).get_json()["data"]
        second = self.client.get("/api/learning-path/config", headers=self.headers).get_json()["data"]

        self.assertEqual(first["weeks"][0]["title"], "数据库中的已保存路径")
        self.assertTrue(first["meta"]["persisted"])
        self.assertFalse(first["meta"]["refreshRecommended"])
        self.assertFalse(first["meta"]["needsRegeneration"])
        self.assertEqual(first["meta"]["savedAt"], saved_at)
        self.assertEqual(second["meta"]["savedAt"], saved_at)

    def test_personalized_resources_use_the_active_profile_and_persist_package_task(self) -> None:
        with app_module.auth_db() as conn:
            previous_state = app_module.profile_state_for_user(conn, 101)
            app_module.activate_profile(conn, 101, self.profile_one["id"])
        captured = {}

        def fake_orchestrated(task_type, topic, payload, user_id, specialist, **kwargs):
            captured.update({"taskType": task_type, "payload": payload, "userId": user_id})
            return {"message": "ok", "workflow": {"resources": []}}

        try:
            with patch.object(app_module, "xiaozhi_run_orchestrated", side_effect=fake_orchestrated):
                generated = self.client.post(
                    "/api/personalized-resources/generate",
                    headers=self.headers,
                    json={"profile": {"id": 999999}, "topic": "GPIO 资源包"},
                )
            self.assertEqual(generated.status_code, 200)
            self.assertEqual(captured["taskType"], "personalized_resources")
            self.assertEqual(captured["userId"], 101)
            self.assertEqual(captured["payload"]["profile"]["id"], self.profile_one["id"])

            with patch.object(app_module.RESOURCE_AGENT_EXECUTOR, "submit", return_value=None) as submit:
                started = self.client.post(
                    "/api/personalized-resources/agent-task",
                    headers=self.headers,
                    json={"resourceType": "personalized_resources", "topic": "GPIO 资源包"},
                )
            self.assertEqual(started.status_code, 202)
            task = started.get_json()["data"]["task"]
            self.assertEqual(task["taskType"], "personalized_resources")
            submit.assert_called_once()

            with app_module.auth_db() as conn:
                app_module.reset_profile_state(conn, 101)
            blocked = self.client.post(
                "/api/personalized-resources/agent-task",
                headers=self.headers,
                json={"resourceType": "ppt", "topic": "无画像课件"},
            )
            self.assertEqual(blocked.status_code, 409)
            self.assertEqual(blocked.get_json()["errorCode"], "ACTIVE_PROFILE_REQUIRED")
        finally:
            with app_module.auth_db() as conn:
                active_report_id = previous_state.get("activeReportId")
                if active_report_id:
                    app_module.activate_profile(conn, 101, int(active_report_id))
                else:
                    app_module.reset_profile_state(conn, 101)

    def test_mindmap_task_history_is_persistent_filtered_and_user_scoped(self) -> None:
        created_ids = []
        try:
            completed_id = app_module.xiaozhi_create_task(
                101,
                "mindmap",
                "GPIO 模式导图",
                "生成 GPIO 模式导图",
                "/personalized-resources/mind-map?topic=GPIO",
            )
            running_id = app_module.xiaozhi_create_task(
                101,
                "mindmap",
                "中断系统导图",
                "生成中断系统导图",
                "/personalized-resources/mind-map?topic=中断系统",
            )
            ppt_id = app_module.xiaozhi_create_task(
                101,
                "ppt",
                "不应出现在导图历史中",
                "PPT",
                "/personalized-resources/ppt",
            )
            other_user_id = app_module.xiaozhi_create_task(
                102,
                "mindmap",
                "其他用户导图",
                "其他用户",
                "/personalized-resources/mind-map?topic=其他用户",
            )
            created_ids.extend([completed_id, running_id, ppt_id, other_user_id])
            app_module.xiaozhi_update_task(
                completed_id,
                status="complete",
                result_json={
                    "topic": "GPIO",
                    "progress": 100,
                    "selectedResource": {
                        "type": "mindmap",
                        "title": "GPIO 知识结构图",
                        "content": "# GPIO\n\n## 输入\n### 上拉",
                    },
                },
            )
            app_module.xiaozhi_update_task(
                running_id,
                status="running",
                result_json={"topic": "中断系统", "progress": 46},
            )

            unauthorized = self.client.get("/api/personalized-resources/mind-map/tasks")
            self.assertEqual(unauthorized.status_code, 401)

            response = self.client.get(
                "/api/personalized-resources/mind-map/tasks?limit=20",
                headers=self.headers,
            )
            self.assertEqual(response.status_code, 200)
            data = response.get_json()["data"]
            task_ids = [item["taskId"] for item in data["tasks"]]
            self.assertIn(completed_id, task_ids)
            self.assertIn(running_id, task_ids)
            self.assertNotIn(ppt_id, task_ids)
            self.assertNotIn(other_user_id, task_ids)
            self.assertEqual(data["activeCount"], 1)
            self.assertGreaterEqual(data["statusCounts"]["complete"], 1)
            completed = next(item for item in data["tasks"] if item["taskId"] == completed_id)
            self.assertEqual(completed["result"]["selectedResource"]["title"], "GPIO 知识结构图")
            self.assertIn(f"xzTask={completed_id}", completed["route"])

            running_response = self.client.get(
                "/api/personalized-resources/mind-map/tasks?status=running",
                headers=self.headers,
            )
            self.assertEqual([item["taskId"] for item in running_response.get_json()["data"]["tasks"]], [running_id])
            invalid = self.client.get(
                "/api/personalized-resources/mind-map/tasks?status=unknown",
                headers=self.headers,
            )
            self.assertEqual(invalid.status_code, 400)
        finally:
            with app_module.auth_db() as conn:
                conn.executemany("DELETE FROM xiaozhi_tasks WHERE task_id = ?", [(task_id,) for task_id in created_ids])

    def test_manual_question_generation_creates_persistent_xiaozhi_task(self) -> None:
        class DeferredThread:
            def __init__(self, *args, **kwargs):
                self.target = kwargs.get("target")

            def start(self):
                return None

        with app_module._question_generation_lock:
            app_module._question_generation_tasks.pop(101, None)

        try:
            with patch.object(app_module.threading, "Thread", DeferredThread):
                response = self.client.post(
                    "/api/question-generator/upload-generate-background",
                    headers=self.headers,
                    data={
                        "pasted_text": "GPIO 可配置为输入、推挽输出和开漏输出。",
                        "course_name": "STM32",
                        "chapter_name": "GPIO 工作模式",
                        "question_count": "6",
                        "preferred_question_types": "[]",
                    },
                )

            self.assertEqual(response.status_code, 202)
            payload = response.get_json()
            task_id = str(payload.get("taskId") or payload.get("payload", {}).get("taskId") or "")
            self.assertTrue(task_id.startswith("xz_"))

            with app_module.auth_db() as conn:
                row = conn.execute(
                    "SELECT task_type, status, route, result_json FROM xiaozhi_tasks WHERE user_id = ? AND task_id = ?",
                    (101, task_id),
                ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["task_type"], "question_bank")
            self.assertEqual(row["status"], "running")
            self.assertIn("xzTask=", row["route"])
            self.assertEqual(json.loads(row["result_json"])["currentStage"], "start")
        finally:
            with app_module._question_generation_lock:
                app_module._question_generation_tasks.pop(101, None)
            with app_module.auth_db() as conn:
                conn.execute(
                    "DELETE FROM xiaozhi_tasks WHERE user_id = ? AND task_type = 'question_bank' AND title LIKE ?",
                    (101, "%GPIO 工作模式%"),
                )

    def test_managed_question_generation_attaches_quality_before_harness_review(self) -> None:
        generated_bank = {
            "message": "结构化题库生成成功",
            "question_count": 3,
            "question_bank": {
                "questions": [
                    {
                        "id": f"Q{index}",
                        "type": "单选题",
                        "stem": f"GPIO 题目 {index}",
                        "answer": "A",
                        "analysis": "依据 GPIO 配置流程进行判断。[KB1]",
                    }
                    for index in range(1, 4)
                ],
                "knowledge_sources": [{"id": "KB1", "title": "GPIO 课程资料"}],
            },
            "knowledgeSources": [{"id": "KB1", "title": "GPIO 课程资料"}],
        }

        def harness_run(task_type, topic, payload, platform_context, specialist, **kwargs):
            output = specialist(payload, lambda event: None)
            self.assertTrue(output["qualityEvaluation"]["passed"])
            self.assertEqual(output["qualityEvaluation"]["questionCount"], 3)
            return {
                **output,
                "orchestration": {"status": "complete", "review": {"passed": True}},
                "harness": {},
            }

        with (
            patch.object(app_module, "generate_question_bank", return_value=generated_bank),
            patch.object(app_module.DEFAULT_AGENT_HARNESS, "run", side_effect=harness_run),
            patch.object(app_module, "xiaozhi_latest_context", return_value={"profileReportId": 1, "profile": {"id": 1}}),
            patch.object(app_module, "xiaozhi_persist_orchestration"),
        ):
            result = app_module.xiaozhi_generate_question_bank_managed(
                {
                    "course_name": "STM32",
                    "target_topic": "GPIO",
                    "question_count": 3,
                },
                101,
            )

        self.assertTrue(result["qualityEvaluation"]["passed"])
        self.assertEqual(result["harness"]["profileReportId"], 1)

    def test_legacy_path_is_preserved_but_profile_driven_actions_require_an_active_profile(self) -> None:
        stage_id = "week-legacy-generic"
        config = app_module.default_learning_path_config()
        config["meta"].update({"needsRegeneration": False, "generationState": "complete"})
        config["weeks"] = [
            {
                "id": stage_id,
                "order": 1,
                "weekLabel": "第一周",
                "title": "保留的历史通用路径",
                "status": "current",
                "enabled": True,
            }
        ]
        config["stages"] = {
            stage_id: {
                "id": stage_id,
                "weekLabel": "第一周",
                "title": "历史通用任务",
                "nodes": [
                    {
                        "id": "01",
                        "label": "01",
                        "title": "GPIO 基础复习",
                        "description": "保留旧任务但不继续生成新资源。",
                        "state": "current",
                        "resourceType": "video",
                    }
                ],
            }
        }

        with app_module.auth_db() as conn:
            previous_config = conn.execute(
                "SELECT config_json, created_at, updated_at FROM user_learning_path_configs WHERE user_id = ?",
                (101,),
            ).fetchone()
            previous_state = app_module.profile_state_for_user(conn, 101)
            app_module.write_learning_path_config(conn, config, 101)
            app_module.reset_profile_state(conn, 101, timestamp="2026-07-12T18:10:00+08:00")
            task_count_before = int(
                conn.execute("SELECT COUNT(*) AS total FROM xiaozhi_tasks WHERE user_id = ?", (101,)).fetchone()["total"]
            )

        try:
            response = self.client.get("/api/learning-path/config", headers=self.headers)
            self.assertEqual(response.status_code, 200)
            saved_path = response.get_json()["data"]
            self.assertEqual(saved_path["weeks"][0]["title"], "保留的历史通用路径")
            self.assertEqual(saved_path["meta"]["profileReportId"], 0)
            self.assertEqual(saved_path["meta"]["personalizationStatus"], "legacy-generic")
            self.assertTrue(saved_path["meta"]["profileRequired"])
            self.assertFalse(saved_path["meta"]["canGeneratePersonalized"])
            self.assertFalse(saved_path["meta"]["canPrepareResources"])
            self.assertFalse(saved_path["meta"]["needsRegeneration"])

            generated = self.client.post(
                "/api/learning-path/generate",
                headers=self.headers,
                json={"profile": {"id": 999}, "persist": True},
            )
            detailed = self.client.post(
                "/api/learning-path/stage-detail",
                headers=self.headers,
                json={"stage": {"id": stage_id, "title": "绕过画像"}},
            )
            prepared = self.client.post(
                f"/api/learning-path/stages/{stage_id}/prepare-resources",
                headers=self.headers,
                json={"useLLM": False, "advance": True},
            )

            for blocked in (generated, detailed, prepared):
                self.assertEqual(blocked.status_code, 409)
                self.assertEqual(blocked.get_json()["errorCode"], "ACTIVE_PROFILE_REQUIRED")

            with app_module.auth_db() as conn:
                stored = app_module.read_learning_path_config(conn, 101)
                task_count_after = int(
                    conn.execute("SELECT COUNT(*) AS total FROM xiaozhi_tasks WHERE user_id = ?", (101,)).fetchone()["total"]
                )
            self.assertEqual(stored["weeks"][0]["title"], "保留的历史通用路径")
            self.assertEqual(task_count_after, task_count_before)
            with self.assertRaises(app_module.LearningProfileRequiredError):
                app_module.xiaozhi_run_platform_agent(
                    "learning_path",
                    "绕过前端生成路径",
                    app_module.xiaozhi_latest_context(101),
                    101,
                )
        finally:
            with app_module.auth_db() as conn:
                active_report_id = previous_state.get("activeReportId")
                if active_report_id:
                    app_module.activate_profile(conn, 101, int(active_report_id))
                else:
                    app_module.reset_profile_state(conn, 101)
                if previous_config:
                    conn.execute(
                        """
                        INSERT INTO user_learning_path_configs (user_id, config_json, created_at, updated_at)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(user_id) DO UPDATE SET
                            config_json = excluded.config_json,
                            created_at = excluded.created_at,
                            updated_at = excluded.updated_at
                        """,
                        (
                            101,
                            previous_config["config_json"],
                            previous_config["created_at"],
                            previous_config["updated_at"],
                        ),
                    )
                else:
                    conn.execute("DELETE FROM user_learning_path_configs WHERE user_id = ?", (101,))

    def test_path_generation_does_not_invalidate_its_own_evidence_version(self) -> None:
        first_config = app_module.default_learning_path_config()
        first_config["meta"].update({"needsRegeneration": False, "generationState": "partial"})
        first_config["weeks"] = [
            {
                "id": "week-1-test",
                "order": 1,
                "weekLabel": "第一周",
                "title": "基础任务",
                "status": "current",
                "enabled": True,
            }
        ]
        with app_module.auth_db() as conn:
            app_module.write_learning_path_config(conn, first_config, 101)
            first_evidence = app_module.learning_evidence_for_user(conn, 101)

            second_config = json.loads(json.dumps(first_config, ensure_ascii=False))
            second_config["meta"]["generationState"] = "complete"
            second_config["weeks"].append(
                {
                    "id": "week-2-test",
                    "order": 2,
                    "weekLabel": "第二周",
                    "title": "进阶任务",
                    "status": "locked",
                    "enabled": True,
                }
            )
            app_module.write_learning_path_config(conn, second_config, 101)
            second_evidence = app_module.learning_evidence_for_user(conn, 101)

        self.assertEqual(first_evidence["evidenceVersion"], second_evidence["evidenceVersion"])
        self.assertEqual(len(first_evidence["pathProgress"]["weeks"]), 1)
        self.assertEqual(len(second_evidence["pathProgress"]["weeks"]), 2)

    def test_legacy_profile_task_route_is_migrated_to_personalized_resource(self) -> None:
        legacy_config = app_module.default_learning_path_config()
        legacy_config["meta"].update({"needsRegeneration": False, "generationState": "complete"})
        legacy_config["weeks"] = [
            {
                "id": "week-legacy-route",
                "order": 1,
                "weekLabel": "第一周",
                "title": "GPIO 核心机制",
                "status": "current",
                "enabled": True,
            }
        ]
        legacy_config["stages"] = {
            "week-legacy-route": {
                "id": "week-legacy-route",
                "weekLabel": "第一周",
                "title": "第一周学习任务",
                "nodes": [
                    {
                        "id": "01",
                        "label": "01",
                        "title": "目标拆解",
                        "description": "明确 GPIO 学习目标",
                        "state": "current",
                        "resourceType": "profile",
                        "resourceTypes": ["profile"],
                        "actionText": "查看画像",
                        "actionRoute": "/learning-profile",
                    }
                ],
            }
        }
        saved_at = "2026-07-10T12:00:00+08:00"
        with app_module.auth_db() as conn:
            previous_config = conn.execute(
                "SELECT config_json, created_at, updated_at FROM user_learning_path_configs WHERE user_id = ?",
                (101,),
            ).fetchone()
            previous_profile_configs = conn.execute(
                """
                SELECT profile_report_id, config_json, created_at, updated_at
                FROM learning_path_profile_configs WHERE user_id = ?
                """,
                (101,),
            ).fetchall()
            conn.execute("DELETE FROM learning_path_profile_configs WHERE user_id = ?", (101,))
            conn.execute(
                """
                INSERT INTO user_learning_path_configs (user_id, config_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET config_json = excluded.config_json, updated_at = excluded.updated_at
                """,
                (101, json.dumps(legacy_config, ensure_ascii=False), saved_at, saved_at),
            )

        try:
            response = self.client.get("/api/learning-path/config", headers=self.headers).get_json()["data"]
            node = response["stages"]["week-legacy-route"]["nodes"][0]
            self.assertEqual(node["resourceType"], "video")
            self.assertTrue(node["actionRoute"].startswith("/personalized-resources/video-search?"))
            self.assertNotIn("/learning-profile", node["actionRoute"])

            with app_module.auth_db() as conn:
                stored = json.loads(
                    conn.execute(
                        "SELECT config_json FROM user_learning_path_configs WHERE user_id = 101"
                    ).fetchone()["config_json"]
                )
            stored_node = stored["stages"]["week-legacy-route"]["nodes"][0]
            self.assertEqual(stored_node["resourceType"], "video")
            self.assertNotIn("/learning-profile", stored_node["actionRoute"])
        finally:
            with app_module.auth_db() as conn:
                conn.execute("DELETE FROM learning_path_profile_configs WHERE user_id = ?", (101,))
                for row in previous_profile_configs:
                    conn.execute(
                        """
                        INSERT INTO learning_path_profile_configs
                            (user_id, profile_report_id, config_json, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            101,
                            row["profile_report_id"],
                            row["config_json"],
                            row["created_at"],
                            row["updated_at"],
                        ),
                    )
                if previous_config:
                    conn.execute(
                        """
                        INSERT INTO user_learning_path_configs (user_id, config_json, created_at, updated_at)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(user_id) DO UPDATE SET
                            config_json = excluded.config_json,
                            created_at = excluded.created_at,
                            updated_at = excluded.updated_at
                        """,
                        (101, previous_config["config_json"], previous_config["created_at"], previous_config["updated_at"]),
                    )
                else:
                    conn.execute("DELETE FROM user_learning_path_configs WHERE user_id = ?", (101,))

    def _save_resource_retry_stage(self, stage_id: str) -> None:
        config = app_module.default_learning_path_config()
        config["meta"].update({"needsRegeneration": False, "generationState": "complete"})
        config["weeks"] = [
            {
                "id": stage_id,
                "order": 1,
                "weekLabel": "第一周",
                "title": "GPIO 失败重试任务",
                "status": "current",
                "enabled": True,
            }
        ]
        config["stages"] = {
            stage_id: {
                "id": stage_id,
                "weekLabel": "第一周",
                "title": "GPIO 失败重试任务",
                "focus": "GPIO 调试",
                "nodes": [
                    {
                        "id": "01",
                        "label": "01",
                        "title": "GPIO 调试复盘",
                        "description": "根据错误证据复盘 GPIO 配置。",
                        "state": "current",
                        "order": 1,
                    }
                ],
            }
        }
        with app_module.auth_db() as conn:
            app_module.write_learning_path_config(conn, config, 101)

    @staticmethod
    def _valid_resource_retry_plan() -> dict:
        return {
            "agent": "learning-path-resource-router-agent",
            "source": "llm",
            "tasks": [
                {
                    "id": "01",
                    "resourceType": "video",
                    "resourceParams": {"topic": "GPIO 调试复盘", "keyword": "STM32 GPIO 调试"},
                    "resourcePrompt": "检索 GPIO 调试复盘视频并保留学习证据。",
                }
            ],
            "orchestration": {"runId": "retry-plan-run"},
            "harness": {
                "skill": {
                    "id": "learning.path.stage-detail",
                    "mcpTool": "learning.path.stage-detail",
                }
            },
        }

    def test_stage_resource_planning_failure_retries_once_then_succeeds(self) -> None:
        with app_module.auth_db() as conn:
            app_module.activate_profile(conn, 101, self.profile_one["id"])
        stage_id = "week-resource-planning-retry"
        self._save_resource_retry_stage(stage_id)

        with (
            patch.object(
                app_module,
                "xiaozhi_run_orchestrated",
                side_effect=[RuntimeError("结构化计划无效"), self._valid_resource_retry_plan()],
            ) as orchestrate,
            patch.object(app_module.RESOURCE_AGENT_EXECUTOR, "submit", return_value=None),
        ):
            first = self.client.post(
                f"/api/learning-path/stages/{stage_id}/prepare-resources",
                headers=self.headers,
                json={"useLLM": True, "advance": True},
            ).get_json()["data"]
            second = self.client.post(
                f"/api/learning-path/stages/{stage_id}/prepare-resources",
                headers=self.headers,
                json={"useLLM": True, "advance": True},
            ).get_json()["data"]

        self.assertEqual(orchestrate.call_count, 2)
        self.assertEqual(first["preparation"]["status"], "running")
        self.assertEqual(first["stage"]["nodes"][0]["resourceTask"]["attemptCount"], 1)
        self.assertTrue(first["needsPreparationRetry"])
        self.assertEqual(second["preparation"]["status"], "complete")
        self.assertEqual(second["stage"]["nodes"][0]["resourceTask"]["attemptCount"], 2)
        self.assertTrue(second["stage"]["nodes"][0]["resourceTask"]["taskId"])

    def test_stage_resource_planning_stops_after_bounded_retry(self) -> None:
        with app_module.auth_db() as conn:
            app_module.activate_profile(conn, 101, self.profile_one["id"])
        stage_id = "week-resource-planning-terminal-failure"
        self._save_resource_retry_stage(stage_id)

        with patch.object(app_module, "xiaozhi_run_orchestrated", side_effect=RuntimeError("模型结构化输出无效")) as orchestrate:
            first = app_module.prepare_learning_path_stage_resources_for_user(101, stage_id, use_llm=True)
            second = app_module.prepare_learning_path_stage_resources_for_user(101, stage_id, use_llm=True)
            repeated = app_module.prepare_learning_path_stage_resources_for_user(101, stage_id, use_llm=True)

        self.assertEqual(orchestrate.call_count, 2)
        self.assertEqual(first["preparation"]["status"], "running")
        self.assertEqual(second["preparation"]["status"], "failed")
        self.assertEqual(repeated["preparation"]["status"], "failed")
        terminal_task = repeated["stage"]["nodes"][0]["resourceTask"]
        self.assertEqual(terminal_task["attemptCount"], 2)
        self.assertFalse(terminal_task["retryable"])
        self.assertFalse(repeated["needsPreparationRetry"])

    def test_failed_generated_resource_is_requeued_only_once(self) -> None:
        with app_module.auth_db() as conn:
            app_module.activate_profile(conn, 101, self.profile_one["id"])
        stage_id = "week-resource-generation-retry"
        self._save_resource_retry_stage(stage_id)

        with (
            patch.object(app_module, "xiaozhi_run_orchestrated", return_value=self._valid_resource_retry_plan()),
            patch.object(app_module.RESOURCE_AGENT_EXECUTOR, "submit", return_value=None),
        ):
            initial = app_module.prepare_learning_path_stage_resources_for_user(101, stage_id, use_llm=True)
            first_task_id = initial["stage"]["nodes"][0]["resourceTask"]["taskId"]
            with app_module.auth_db() as conn:
                conn.execute(
                    "UPDATE xiaozhi_tasks SET status = 'failed', error = ? WHERE task_id = ?",
                    ("视频资源质量评价未通过", first_task_id),
                )

            requeued = app_module.prepare_learning_path_stage_resources_for_user(
                101,
                stage_id,
                use_llm=True,
                advance=False,
            )
            retried = app_module.prepare_learning_path_stage_resources_for_user(101, stage_id, use_llm=True)

        retry_task = retried["stage"]["nodes"][0]["resourceTask"]
        self.assertEqual(requeued["preparation"]["status"], "running")
        self.assertEqual(requeued["stage"]["nodes"][0]["resourceTask"]["generationAttemptCount"], 2)
        self.assertNotEqual(retry_task["taskId"], first_task_id)
        self.assertEqual(retry_task["generationAttemptCount"], 2)
        self.assertEqual(retry_task["retryOfTaskId"], first_task_id)

        with app_module.auth_db() as conn:
            conn.execute(
                "UPDATE xiaozhi_tasks SET status = 'failed', error = ? WHERE task_id = ?",
                ("第二次视频资源质量评价仍未通过", retry_task["taskId"]),
            )
        terminal = app_module.prepare_learning_path_stage_resources_for_user(
            101,
            stage_id,
            use_llm=True,
            advance=False,
        )
        self.assertEqual(terminal["preparation"]["status"], "failed")
        self.assertFalse(terminal["needsPreparationRetry"])
        self.assertEqual(terminal["stage"]["nodes"][0]["resourceTask"]["taskId"], retry_task["taskId"])

    def test_learning_path_ppt_task_starts_background_generation_immediately(self) -> None:
        task_id = ""
        with patch.object(app_module.PPT_RESOURCE_EXECUTOR, "submit", return_value=None) as submit:
            task = app_module.xiaozhi_create_resource_agent_task(
                101,
                "ppt",
                "八纲辨证入门",
                {
                    "source": "learning-path",
                    "stageId": "week-tcm-ppt-background",
                    "nodeId": "03",
                    "cacheKey": "week-tcm-ppt-background-03",
                    "pageCount": 6,
                },
                title="第一周 · 八纲辨证入门课件",
                prompt="生成六页八纲辨证入门课件",
            )
            task_id = task["taskId"]

        def cleanup_task() -> None:
            with app_module.auth_db() as conn:
                conn.execute(
                    "DELETE FROM xiaozhi_events WHERE user_id = ? AND payload_json LIKE ?",
                    (101, f'%"taskId": "{task_id}"%'),
                )
                conn.execute("DELETE FROM xiaozhi_tasks WHERE task_id = ?", (task_id,))

        self.addCleanup(cleanup_task)

        self.assertEqual(task["status"], "queued")
        self.assertEqual(task["result"]["currentStage"], "queued")
        self.assertEqual(task["result"]["ppt"]["status"], "queued")
        self.assertTrue(task["result"]["ppt"]["sessionId"])
        submit.assert_called_once()
        callback, submitted_task_id, user_id, task_type, topic, params = submit.call_args.args
        self.assertIs(callback, app_module.xiaozhi_run_resource_task)
        self.assertEqual(submitted_task_id, task_id)
        self.assertEqual(user_id, 101)
        self.assertEqual(task_type, "ppt")
        self.assertEqual(topic, "八纲辨证入门")
        self.assertEqual(params["source"], "learning-path")

        with app_module.auth_db() as conn:
            stored = conn.execute(
                "SELECT status, result_json FROM xiaozhi_tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        self.assertEqual(stored["status"], "queued")
        self.assertEqual(json.loads(stored["result_json"])["params"]["source"], "learning-path")

    def test_ppt_progress_and_failure_preserve_persisted_session_state(self) -> None:
        task_id = ""
        with patch.object(app_module.PPT_RESOURCE_EXECUTOR, "submit", return_value=None):
            task = app_module.xiaozhi_create_resource_agent_task(
                101,
                "ppt",
                "四诊合参基础",
                {
                    "source": "learning-path",
                    "stageId": "week-ppt-state",
                    "nodeId": "04",
                    "cacheKey": "week-ppt-state-04",
                    "pageCount": 6,
                },
            )
            task_id = task["taskId"]

        def cleanup_task() -> None:
            with app_module.auth_db() as conn:
                conn.execute(
                    "DELETE FROM xiaozhi_events WHERE user_id = ? AND payload_json LIKE ?",
                    (101, f'%"taskId": "{task_id}"%'),
                )
                conn.execute("DELETE FROM xiaozhi_tasks WHERE task_id = ?", (task_id,))

        self.addCleanup(cleanup_task)
        captured = {}

        def fail_after_progress(*_args, **kwargs):
            kwargs["on_event"](
                {
                    "stage": "ohmyppt_request",
                    "message": "OhMyPPT 正在生成 6 页课件",
                    "progress": 53,
                    "pageCount": 6,
                }
            )
            with app_module.auth_db() as conn:
                row = conn.execute(
                    "SELECT status, result_json FROM xiaozhi_tasks WHERE task_id = ?",
                    (task_id,),
                ).fetchone()
            captured["status"] = row["status"]
            captured["result"] = json.loads(row["result_json"])
            raise RuntimeError("PPT provider temporarily unavailable")

        with (
            patch.object(app_module, "xiaozhi_latest_context", return_value={}),
            patch.object(app_module, "xiaozhi_run_orchestrated", side_effect=fail_after_progress),
        ):
            app_module._xiaozhi_run_resource_task(
                task_id,
                101,
                "ppt",
                "四诊合参基础",
                task["result"]["params"],
            )

        progress_result = captured["result"]
        self.assertEqual(captured["status"], "running")
        self.assertEqual(progress_result["currentStage"], "ohmyppt_request")
        self.assertEqual(progress_result["pageCount"], 6)
        self.assertEqual(progress_result["params"]["source"], "learning-path")
        self.assertEqual(progress_result["ppt"]["status"], "running")
        self.assertEqual(progress_result["ppt"]["sessionId"], task["result"]["ppt"]["sessionId"])
        self.assertIn(f"xzTask={task_id}", progress_result["route"])

        with app_module.auth_db() as conn:
            failed_row = conn.execute(
                "SELECT status, route, result_json, error FROM xiaozhi_tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        failed_result = json.loads(failed_row["result_json"])
        self.assertEqual(failed_row["status"], "failed")
        self.assertIn("temporarily unavailable", failed_row["error"])
        self.assertEqual(failed_result["params"]["cacheKey"], "week-ppt-state-04")
        self.assertEqual(failed_result["ppt"]["status"], "failed")
        self.assertEqual(failed_result["ppt"]["pageCount"], 6)
        self.assertEqual(failed_result["ppt"]["sessionId"], task["result"]["ppt"]["sessionId"])
        self.assertIn(f"xzTask={task_id}", failed_row["route"])

    def test_startup_recovery_requeues_saved_learning_path_resources(self) -> None:
        snapshot = self._snapshot_learning_path_storage()
        with app_module.auth_db() as conn:
            previous_state = app_module.profile_state_for_user(conn, 101)
        config = app_module.default_learning_path_config()
        config["meta"].update({"needsRegeneration": False, "generationState": "complete"})
        config["weeks"] = [
            {
                "id": "week-startup-ppt-recovery",
                "order": 1,
                "weekLabel": "第一周",
                "title": "辨证基础",
                "status": "current",
                "enabled": True,
            }
        ]
        config["stages"] = {
            "week-startup-ppt-recovery": {
                "id": "week-startup-ppt-recovery",
                "weekLabel": "第一周",
                "title": "辨证基础",
                "focus": "八纲辨证",
                "nodes": [],
            }
        }
        try:
            with app_module.auth_db() as conn:
                app_module.activate_profile(conn, 101, self.profile_one["id"])
                app_module.write_learning_path_config(conn, config, 101)

            queued = []

            def fake_queue(user_id, saved_config):
                queued.append((user_id, saved_config))
                return 1 if user_id == 101 else 0

            with (
                patch.object(app_module, "recover_interrupted_xiaozhi_tasks", return_value=2),
                patch.object(
                    app_module,
                    "_queue_learning_path_week_resource_preparation",
                    side_effect=fake_queue,
                ),
            ):
                result = app_module._recover_learning_path_resource_generation_after_restart()

            queued_for_user = [saved for user_id, saved in queued if user_id == 101]
            self.assertEqual(result["recoveredTasks"], 2)
            self.assertEqual(result["queuedUsers"], 1)
            self.assertEqual(result["queuedStages"], 1)
            self.assertEqual(queued_for_user[0]["weeks"][0]["id"], "week-startup-ppt-recovery")
        finally:
            self._restore_learning_path_storage(snapshot)
            with app_module.auth_db() as conn:
                active_report_id = previous_state.get("activeReportId")
                if active_report_id:
                    app_module.activate_profile(conn, 101, int(active_report_id))
                else:
                    app_module.reset_profile_state(conn, 101)

    def test_stage_resource_preparation_is_background_and_idempotent(self) -> None:
        with app_module.auth_db() as conn:
            app_module.activate_profile(conn, 101, self.profile_one["id"])
        profile_id = self.profile_one["id"]
        stage_id = "week-resource-idempotency"
        config = app_module.default_learning_path_config()
        config["meta"].update({"needsRegeneration": False, "generationState": "complete"})
        config["weeks"] = [
            {
                "id": stage_id,
                "order": 1,
                "weekLabel": "第一周",
                "title": "GPIO 画像驱动任务",
                "description": "按当前画像完成学习任务",
                "status": "current",
                "enabled": True,
            }
        ]
        config["stages"] = {
            stage_id: {
                "id": stage_id,
                "weekLabel": "第一周",
                "title": "第一周具体任务",
                "focus": "GPIO 中断",
                "resourcePlanVersion": "legacy-fixed-sequence",
                "resourceProfileReportId": 0,
                "nodes": [
                    {
                        "id": "01",
                        "label": "01",
                        "title": "中断概念辨析",
                        "description": "针对中断薄弱点完成专项测评",
                        "state": "current",
                        "resourceType": "question-bank",
                        "resourceParams": {
                            "topic": "GPIO 中断专项测评",
                            "course": "嵌入式系统",
                            "chapter": "GPIO 中断",
                            "count": 8,
                        },
                        "resourcePrompt": "生成 8 道 GPIO 中断专项题并给出解析",
                    },
                    {
                        "id": "02",
                        "label": "02",
                        "title": "按键实验验证",
                        "description": "在模拟器验证按键输入",
                        "state": "available",
                        "resourceType": "mcu",
                        "resourceParams": {
                            "topic": "按键输入实验",
                            "board": "arduino",
                            "projectId": "uno-button-ready",
                        },
                        "resourcePrompt": "打开按键输入预设实验并记录现象",
                    },
                ],
            }
        }
        with app_module.auth_db() as conn:
            app_module.write_learning_path_config(conn, config, 101)

        with patch.object(app_module.RESOURCE_AGENT_EXECUTOR, "submit", return_value=None) as submit:
            initialize_response = self.client.post(
                f"/api/learning-path/stages/{stage_id}/prepare-resources",
                headers=self.headers,
                json={"useLLM": False, "advance": False},
            )
            first_response = self.client.post(
                f"/api/learning-path/stages/{stage_id}/prepare-resources",
                headers=self.headers,
                json={"useLLM": False, "advance": True},
            )
            second_response = self.client.post(
                f"/api/learning-path/stages/{stage_id}/prepare-resources",
                headers=self.headers,
                json={"useLLM": False, "advance": True},
            )
            repeated_response = self.client.post(
                f"/api/learning-path/stages/{stage_id}/prepare-resources",
                headers=self.headers,
                json={"useLLM": False, "advance": True},
            )

        self.assertEqual(initialize_response.status_code, 202)
        self.assertEqual(first_response.status_code, 202)
        self.assertEqual(second_response.status_code, 202)
        self.assertEqual(repeated_response.status_code, 202)
        initialized = initialize_response.get_json()["data"]
        first = first_response.get_json()["data"]
        second = second_response.get_json()["data"]
        repeated = repeated_response.get_json()["data"]
        self.assertEqual(initialized["tasks"], [])
        self.assertEqual(initialized["preparation"]["status"], "running")
        self.assertEqual(initialized["preparation"]["currentNodeId"], "01")
        first_ids = [task["taskId"] for task in first["tasks"]]
        second_ids = [task["taskId"] for task in second["tasks"]]
        repeated_ids = [task["taskId"] for task in repeated["tasks"]]
        self.assertEqual(len(first_ids), 2)
        self.assertEqual(first_ids, second_ids)
        self.assertEqual(second_ids, repeated_ids)
        self.assertEqual(len(second_ids), 2)
        self.assertEqual(submit.call_count, 2)
        self.assertTrue(all("xzTask=" in task["route"] for task in second["tasks"]))
        self.assertTrue(all(node["actionRoute"] for node in second["stage"]["nodes"]))
        self.assertEqual(second["preparation"]["status"], "complete")
        planner_runs = second["stage"]["resourcePlannerRuns"]
        self.assertEqual(len(planner_runs), 2)
        self.assertTrue(all(item["runId"] for item in planner_runs))
        self.assertTrue(all(item["skillId"] == "learning.path.stage-detail" for item in planner_runs))
        self.assertTrue(all(item["mcpTool"] == "learning.path.stage-detail" for item in planner_runs))

        with app_module.auth_db() as conn:
            stored = app_module.read_learning_path_config(conn, 101)
            placeholders = ",".join("?" for _ in second_ids)
            task_count = conn.execute(
                f"SELECT COUNT(*) AS n FROM xiaozhi_tasks WHERE user_id = ? AND task_id IN ({placeholders})",
                [101, *second_ids],
            ).fetchone()["n"]
            orchestrations = [
                conn.execute(
                    "SELECT root_agent, skill_id, mcp_tool, profile_report_id, input_json FROM agent_orchestration_runs WHERE run_id = ?",
                    (planner_run["runId"],),
                ).fetchone()
                for planner_run in planner_runs
            ]
        self.assertEqual(task_count, 2)
        self.assertTrue(all(item["root_agent"] == app_module.XIAOZHI_MASTER_AGENT_ID for item in orchestrations))
        self.assertTrue(all(item["skill_id"] == "learning.path.stage-detail" for item in orchestrations))
        self.assertTrue(all(item["mcp_tool"] == "learning.path.stage-detail" for item in orchestrations))
        self.assertTrue(all(item["profile_report_id"] == profile_id for item in orchestrations))
        persisted_inputs = [json.loads(item["input_json"]) for item in orchestrations]
        self.assertTrue(all(len(item["input_json"]) < 20000 for item in orchestrations))
        self.assertTrue(all("profileContext" in item for item in persisted_inputs))
        self.assertTrue(all("profile" not in item for item in persisted_inputs))
        self.assertTrue(all(len((item.get("stage") or {}).get("nodes") or []) == 1 for item in persisted_inputs))
        stored_nodes = stored["stages"][stage_id]["nodes"]
        self.assertEqual([node["resourceTask"]["taskId"] for node in stored_nodes], second_ids)
        self.assertEqual(stored["stages"][stage_id]["resourceProfileReportId"], profile_id)

    def test_stage_resource_parallel_dispatch_creates_clickable_tasks_immediately(self) -> None:
        stage_id = "week-resource-direct-parallel-dispatch"
        created_task_ids: list[str] = []
        cache_keys: list[str] = []
        with app_module.auth_db() as conn:
            original_active = app_module.active_profile_for_user(conn, 101)
            original_config = app_module.read_learning_path_config(conn, 101)
            app_module.activate_profile(conn, 101, self.profile_one["id"])
            config = app_module.default_learning_path_config()
            config["meta"].update({"needsRegeneration": False, "generationState": "complete"})
            config["weeks"] = [
                {
                    "id": stage_id,
                    "order": 1,
                    "weekLabel": "第一周",
                    "title": "并行资源派发",
                    "status": "current",
                    "enabled": True,
                }
            ]
            config["stages"] = {
                stage_id: {
                    "id": stage_id,
                    "weekLabel": "第一周",
                    "title": "第一周并行资源派发",
                    "focus": "STM32 GPIO",
                    "nodes": [
                        {
                            "id": "01",
                            "label": "01",
                            "title": "GPIO 配置专项测评",
                            "description": "生成 GPIO 配置练习题并保留解析。",
                            "state": "current",
                            "order": 1,
                            "resourceType": "question-bank",
                            "resourceParams": {
                                "topic": "GPIO 配置专项测评",
                                "course": "嵌入式系统",
                                "chapter": "GPIO 配置",
                                "count": 8,
                            },
                            "resourcePrompt": "生成 8 道 GPIO 配置专项练习题。",
                        },
                        {
                            "id": "02",
                            "label": "02",
                            "title": "GPIO 原理 AI 视频讲解",
                            "description": "按学习画像准备 GPIO 原理视频提示词。",
                            "state": "available",
                            "order": 2,
                            "resourceType": "generated_video",
                            "resourceParams": {
                                "topic": "GPIO 工作原理",
                                "prompt": "面向嵌入式初学者讲解 GPIO 输入输出原理。",
                            },
                            "resourcePrompt": "面向嵌入式初学者讲解 GPIO 输入输出原理。",
                        },
                    ],
                }
            }
            app_module.write_learning_path_config(conn, config, 101)

        try:
            with (
                patch.object(app_module, "xiaozhi_run_orchestrated") as orchestrate,
                patch.object(app_module.RESOURCE_AGENT_EXECUTOR, "submit", return_value=None) as submit,
                patch.object(app_module.VIDEO_RESOURCE_EXECUTOR, "submit", return_value=None) as video_submit,
                patch.object(app_module, "execute_generated_video_task") as execute_video,
            ):
                first_response = self.client.post(
                    f"/api/learning-path/stages/{stage_id}/prepare-resources",
                    headers=self.headers,
                    json={"useLLM": False, "advance": False, "parallelDispatch": True},
                )
                repeated_response = self.client.post(
                    f"/api/learning-path/stages/{stage_id}/prepare-resources",
                    headers=self.headers,
                    json={"useLLM": False, "advance": False, "parallelDispatch": True},
                )

            self.assertEqual(first_response.status_code, 202)
            self.assertEqual(repeated_response.status_code, 202)
            first = first_response.get_json()["data"]
            repeated = repeated_response.get_json()["data"]
            self.assertEqual(first["dispatchMode"], "parallel")
            self.assertTrue(first["allEntrypointsReady"])
            self.assertEqual(first["preparation"]["status"], "complete")
            self.assertEqual(len(first["tasks"]), 2)
            self.assertTrue(all("xzTask=" in task["route"] for task in first["tasks"]))
            self.assertTrue(all(node["actionRoute"] for node in first["stage"]["nodes"]))

            tasks_by_node = {task["nodeId"]: task for task in first["tasks"]}
            self.assertEqual(tasks_by_node["01"]["status"], "queued")
            self.assertEqual(tasks_by_node["02"]["status"], "waiting")
            self.assertEqual(submit.call_count, 1)
            self.assertEqual(video_submit.call_count, 0)
            execute_video.assert_not_called()
            orchestrate.assert_not_called()

            created_task_ids = [task["taskId"] for task in first["tasks"]]
            repeated_task_ids = [task["taskId"] for task in repeated["tasks"]]
            self.assertEqual(repeated_task_ids, created_task_ids)
            self.assertEqual(repeated["submittedCount"], 0)

            with app_module.auth_db() as conn:
                stored = app_module.read_learning_path_config(conn, 101)
            stored_nodes = stored["stages"][stage_id]["nodes"]
            cache_keys = [str(node.get("cacheKey") or "") for node in stored_nodes]
            self.assertEqual(
                [node["resourceTask"]["taskId"] for node in stored_nodes],
                created_task_ids,
            )
        finally:
            with app_module.auth_db() as conn:
                for task_id in created_task_ids:
                    conn.execute("DELETE FROM xiaozhi_tasks WHERE user_id = ? AND task_id = ?", (101, task_id))
                    conn.execute(
                        "DELETE FROM xiaozhi_events WHERE user_id = ? AND payload_json LIKE ?",
                        (101, f'%"taskId": "{task_id}"%'),
                    )
                for cache_key in cache_keys:
                    if cache_key:
                        conn.execute(
                            "DELETE FROM learning_path_node_caches WHERE user_id = ? AND cache_key = ?",
                            (101, cache_key),
                        )
                app_module.write_learning_path_config(conn, original_config, 101)
                if original_active:
                    app_module.activate_profile(conn, 101, original_active["id"])

    def test_parallel_dispatch_adopts_legacy_tasks_and_only_fills_missing_entries(self) -> None:
        stage_id = "week-resource-adopt-existing"
        created_task_ids: list[str] = []
        cache_keys: list[str] = []
        with app_module.auth_db() as conn:
            original_active = app_module.active_profile_for_user(conn, 101)
            original_config = app_module.read_learning_path_config(conn, 101)
            app_module.activate_profile(conn, 101, self.profile_one["id"])

        existing_task_id = app_module.xiaozhi_create_task(
            101,
            "video",
            "GPIO 视频查找",
            "检索 GPIO 基础讲解视频",
            "/personalized-resources/video-search?keyword=GPIO",
        )
        with app_module.auth_db() as conn:
            existing_row = conn.execute(
                "SELECT * FROM xiaozhi_tasks WHERE user_id = ? AND task_id = ?",
                (101, existing_task_id),
            ).fetchone()
        existing_summary = app_module._learning_path_task_runtime_summary(
            app_module.xiaozhi_task_from_row(existing_row)
        )
        config = app_module.default_learning_path_config()
        config["meta"].update({"needsRegeneration": False, "generationState": "complete"})
        config["weeks"] = [
            {"id": stage_id, "order": 1, "weekLabel": "第一周", "title": "兼容旧任务", "enabled": True}
        ]
        config["stages"] = {
            stage_id: {
                "id": stage_id,
                "weekLabel": "第一周",
                "title": "兼容旧任务",
                "focus": "GPIO",
                "resourcePlanVersion": "legacy-resource-plan",
                "resourceProfileReportId": 0,
                "resourcePreparation": {"version": "legacy-resource-plan", "status": "complete"},
                "nodes": [
                    {
                        "id": "01",
                        "title": "GPIO 视频查找",
                        "description": "检索 GPIO 基础讲解视频。",
                        "state": "current",
                        "order": 1,
                        "resourceType": "video",
                        "resourceParams": {"topic": "GPIO", "keyword": "GPIO"},
                        "resourcePrompt": "检索 GPIO 基础讲解视频。",
                        "resourceTask": existing_summary,
                        "actionRoute": existing_summary["route"],
                    },
                    {
                        "id": "02",
                        "title": "GPIO AI 视频讲解",
                        "description": "准备 GPIO 原理讲解视频提示词。",
                        "state": "available",
                        "order": 2,
                        "resourceType": "generated_video",
                        "resourceParams": {"topic": "GPIO 原理", "prompt": "讲解 GPIO 原理。"},
                        "resourcePrompt": "讲解 GPIO 原理。",
                    },
                ],
            }
        }
        with app_module.auth_db() as conn:
            app_module.write_learning_path_config(conn, config, 101)

        try:
            with (
                patch.object(app_module, "xiaozhi_run_orchestrated") as orchestrate,
                patch.object(app_module.RESOURCE_AGENT_EXECUTOR, "submit", return_value=None) as submit,
                patch.object(app_module.VIDEO_RESOURCE_EXECUTOR, "submit", return_value=None) as video_submit,
            ):
                result = app_module.prepare_learning_path_stage_resources_for_user(
                    101,
                    stage_id,
                    use_llm=False,
                    advance=False,
                    parallel_dispatch=True,
                )

            created_task_ids = [task["taskId"] for task in result["tasks"]]
            self.assertIn(existing_task_id, created_task_ids)
            self.assertEqual(len(created_task_ids), 2)
            self.assertEqual(result["submittedCount"], 1)
            self.assertTrue(result["allEntrypointsReady"])
            self.assertEqual(submit.call_count, 0)
            self.assertEqual(video_submit.call_count, 0)
            orchestrate.assert_not_called()
            generated_task = next(task for task in result["tasks"] if task["nodeId"] == "02")
            self.assertEqual(generated_task["status"], "waiting")

            with app_module.auth_db() as conn:
                stored = app_module.read_learning_path_config(conn, 101)
            stored_nodes = stored["stages"][stage_id]["nodes"]
            cache_keys = [str(node.get("cacheKey") or "") for node in stored_nodes]
            self.assertEqual(stored_nodes[0]["resourceTask"]["taskId"], existing_task_id)
        finally:
            with app_module.auth_db() as conn:
                for task_id in created_task_ids or [existing_task_id]:
                    conn.execute("DELETE FROM xiaozhi_tasks WHERE user_id = ? AND task_id = ?", (101, task_id))
                    conn.execute(
                        "DELETE FROM xiaozhi_events WHERE user_id = ? AND payload_json LIKE ?",
                        (101, f'%"taskId": "{task_id}"%'),
                    )
                for cache_key in cache_keys:
                    if cache_key:
                        conn.execute(
                            "DELETE FROM learning_path_node_caches WHERE user_id = ? AND cache_key = ?",
                            (101, cache_key),
                        )
                app_module.write_learning_path_config(conn, original_config, 101)
                if original_active:
                    app_module.activate_profile(conn, 101, original_active["id"])

    def test_stale_parallel_week_writes_merge_only_the_target_stage(self) -> None:
        with app_module.auth_db() as conn:
            app_module.activate_profile(conn, 101, self.profile_one["id"])
            config = app_module.default_learning_path_config()
            config["weeks"] = [
                {"id": "week-merge-1", "order": 1, "weekLabel": "第一周", "title": "GPIO", "enabled": True},
                {"id": "week-merge-2", "order": 2, "weekLabel": "第二周", "title": "中断", "enabled": True},
            ]
            config["stages"] = {
                "week-merge-1": {
                    "id": "week-merge-1",
                    "title": "第一周",
                    "focus": "GPIO",
                    "nodes": app_module._ensure_learning_path_task_resource_coverage(
                        app_module.build_default_stage_nodes("第一周", "GPIO"),
                        "GPIO",
                        "week-merge-1",
                    ),
                },
                "week-merge-2": {
                    "id": "week-merge-2",
                    "title": "第二周",
                    "focus": "中断",
                    "nodes": app_module._ensure_learning_path_task_resource_coverage(
                        app_module.build_default_stage_nodes("第二周", "中断"),
                        "中断",
                        "week-merge-2",
                    ),
                },
            }
            app_module.write_learning_path_config(conn, config, 101)
            stale = app_module.read_learning_path_config(conn, 101)

        first_stage = app_module._json_copy(stale["stages"]["week-merge-1"])
        second_stage = app_module._json_copy(stale["stages"]["week-merge-2"])
        first_stage["resourcePreparation"] = {"status": "complete", "marker": "first"}
        second_stage["resourcePreparation"] = {"status": "complete", "marker": "second"}

        app_module._persist_learning_path_stage_update(101, "week-merge-1", first_stage)
        app_module._persist_learning_path_stage_update(101, "week-merge-2", second_stage)

        with app_module.auth_db() as conn:
            stored = app_module.read_learning_path_config(conn, 101)
        self.assertEqual(stored["stages"]["week-merge-1"]["resourcePreparation"]["marker"], "first")
        self.assertEqual(stored["stages"]["week-merge-2"]["resourcePreparation"]["marker"], "second")

    def test_stage_resource_planners_run_in_parallel_with_a_bounded_pool(self) -> None:
        stage_id = "week-resource-parallel-planning"
        resource_types = ["video", "mindmap", "question-bank", "ppt", "mcu", "generated_video"]
        active_calls = 0
        max_active_calls = 0
        call_lock = threading.Lock()
        created_task_ids: list[str] = []
        cache_keys: list[str] = []

        with app_module.auth_db() as conn:
            original_active = app_module.active_profile_for_user(conn, 101)
            original_config = app_module.read_learning_path_config(conn, 101)
            app_module.activate_profile(conn, 101, self.profile_one["id"])
            config = app_module.default_learning_path_config()
            config["meta"].update({"needsRegeneration": False, "generationState": "complete"})
            config["weeks"] = [
                {
                    "id": stage_id,
                    "order": 1,
                    "weekLabel": "第一周",
                    "title": "并发资源规划",
                    "status": "current",
                    "enabled": True,
                }
            ]
            config["stages"] = {
                stage_id: {
                    "id": stage_id,
                    "weekLabel": "第一周",
                    "title": "第一周并发任务",
                    "focus": "STM32 GPIO",
                    "nodes": [
                        {
                            "id": f"{index:02d}",
                            "label": f"{index:02d}",
                            "title": f"并发任务 {index}",
                            "description": f"完成第 {index} 项可验证学习任务",
                            "state": "current" if index == 1 else "available",
                            "order": index,
                        }
                        for index in range(1, 7)
                    ],
                }
            }
            app_module.write_learning_path_config(conn, config, 101)

        def fake_orchestrated(_task_type, _topic, payload, _user_id, _handler, **_kwargs):
            nonlocal active_calls, max_active_calls
            node_id = str(payload["nodeId"])
            with call_lock:
                active_calls += 1
                max_active_calls = max(max_active_calls, active_calls)
            try:
                time.sleep(0.08)
            finally:
                with call_lock:
                    active_calls -= 1
            resource_type = resource_types[int(node_id) - 1]
            return {
                "agent": "learning-path-resource-router-agent",
                "source": "llm",
                "tasks": [
                    {
                        "id": node_id,
                        "resourceType": resource_type,
                        "resourceParams": {"topic": f"STM32 GPIO 任务 {node_id}"},
                        "resourcePrompt": f"为任务 {node_id} 生成可验证资源",
                    }
                ],
                "orchestration": {"runId": f"parallel-plan-{node_id}"},
                "harness": {
                    "skill": {
                        "id": "learning.path.stage-detail",
                        "mcpTool": "learning.path.stage-detail",
                    }
                },
            }

        try:
            with (
                patch.object(app_module, "xiaozhi_run_orchestrated", side_effect=fake_orchestrated) as orchestrate,
                patch.object(app_module.RESOURCE_AGENT_EXECUTOR, "submit", return_value=None) as submit,
                patch.object(app_module.PPT_RESOURCE_EXECUTOR, "submit", return_value=None) as ppt_submit,
                patch.object(app_module.VIDEO_RESOURCE_EXECUTOR, "submit", return_value=None) as video_submit,
                patch.object(app_module, "LEARNING_PATH_RESOURCE_PLANNER_MAX_WORKERS", 3),
            ):
                result = app_module.prepare_learning_path_stage_resources_for_user(
                    101,
                    stage_id,
                    use_llm=True,
                    advance=True,
                )

            created_task_ids = [task["taskId"] for task in result["tasks"]]
            cache_keys = [str(node.get("cacheKey") or "") for node in result["stage"]["nodes"]]
            self.assertEqual(orchestrate.call_count, 6)
            self.assertEqual(submit.call_count, 4)
            self.assertEqual(ppt_submit.call_count, 1)
            self.assertEqual(video_submit.call_count, 0)
            self.assertEqual(len(created_task_ids), 6)
            self.assertEqual(result["preparation"]["status"], "complete")
            self.assertEqual(len(result["planners"]), 6)
            self.assertGreaterEqual(max_active_calls, 2)
            self.assertLessEqual(max_active_calls, 3)
            generated_task = next(task for task in result["tasks"] if task["nodeId"] == "06")
            self.assertEqual(generated_task["status"], "waiting")
        finally:
            with app_module.auth_db() as conn:
                for task_id in created_task_ids:
                    conn.execute("DELETE FROM xiaozhi_tasks WHERE user_id = ? AND task_id = ?", (101, task_id))
                    conn.execute(
                        "DELETE FROM xiaozhi_events WHERE user_id = ? AND payload_json LIKE ?",
                        (101, f'%"taskId": "{task_id}"%'),
                    )
                for cache_key in cache_keys:
                    if cache_key:
                        conn.execute(
                            "DELETE FROM learning_path_node_caches WHERE user_id = ? AND cache_key = ?",
                            (101, cache_key),
                        )
                app_module.write_learning_path_config(conn, original_config, 101)
                if original_active:
                    app_module.activate_profile(conn, 101, original_active["id"])

    def test_learning_path_generate_stream_emits_live_harness_events_and_result(self) -> None:
        with app_module.auth_db() as conn:
            active_profile = app_module.latest_learning_profile_for_user(conn, 101)
        profile_id = int(active_profile["id"])
        stage_id = "week-1-stream-test"
        config = {
            "version": 2,
            "meta": {
                "title": "个性化周学习计划",
                "generationState": "partial",
                "totalWeeks": 6,
                "profileReportId": profile_id,
            },
            "weeks": [
                {
                    "id": stage_id,
                    "order": 1,
                    "weekLabel": "第一周",
                    "title": "GPIO 基础",
                    "description": "完成 GPIO 概念与实验闭环",
                    "status": "current",
                    "enabled": True,
                }
            ],
            "stages": {
                stage_id: {
                    "id": stage_id,
                    "title": "第一周学习任务与资源",
                    "nodes": [{"id": "01", "title": "GPIO 概念建模", "state": "current"}],
                }
            },
        }

        def fake_orchestrated(_task_type, _topic, _payload, _user_id, _handler, **kwargs):
            kwargs["on_event"]({
                "runId": "mar_stream_test",
                "agentId": "learning-route-agent",
                "agentName": "学习路径规划智能体",
                "stage": "specialist_start",
                "status": "running",
                "message": "正在生成第一周路径",
                "progress": 38,
                "payload": {"attempt": 1},
            })
            return {
                "source": "llm",
                "phases": [{"id": stage_id}],
                "config": config,
                "orchestration": {
                    "runId": "mar_stream_test",
                    "status": "complete",
                    "review": {"passed": True, "score": 92},
                },
            }

        with patch.object(app_module, "xiaozhi_run_orchestrated", side_effect=fake_orchestrated):
            response = self.client.post(
                "/api/learning-path/generate-stream",
                headers=self.headers,
                json={
                    "persist": False,
                    "generationPhase": "first-week",
                    "weekStart": 1,
                    "weekCount": 1,
                    "totalWeeks": 6,
                },
            )

        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content_type.startswith("text/event-stream"))
        self.assertIn("event: start", body)
        self.assertIn("event: progress", body)
        self.assertIn("event: result", body)
        self.assertIn("event: done", body)
        self.assertIn("mar_stream_test", body)
        self.assertIn("学习路径规划智能体", body)
        self.assertIn('"generationState": "partial"', body)

    def test_learning_profile_analyze_stream_emits_detailed_live_events(self) -> None:
        fake_analysis = {
            "source": "llm",
            "learningStyle": "evidence-driven",
            "overallScore": 82,
            "radarScores": [3.4, 3.7, 3.9, 3.5, 3.8, 3.3],
            "dimensionScores": [
                {"name": f"dimension-{index}", "score": score}
                for index, score in enumerate([3.4, 3.7, 3.9, 3.5, 3.8, 3.3], start=1)
            ],
            "strengths": ["hands-on practice"],
            "weaknesses": ["debugging evidence"],
            "recommendations": ["complete one traceable debugging exercise"],
            "summary": "Profile generated from current evidence.",
        }

        def fake_orchestrated(_task_type, _topic, _payload, _user_id, _handler, **kwargs):
            kwargs["on_event"]({
                "runId": "mar_profile_stream_test",
                "sequence": 3,
                "agentId": "skill-registry-agent",
                "agentName": "Skill Registry",
                "stage": "skill_resolved",
                "status": "complete",
                "message": "profile skill resolved",
                "progress": 25,
                "payload": {"skillId": "learning.profile.update", "riskLevel": "low"},
            })
            kwargs["on_event"]({
                "runId": "mar_profile_stream_test",
                "sequence": 4,
                "agentId": "mcp-tool-gateway",
                "agentName": "MCP Tool Gateway",
                "stage": "mcp_tool_start",
                "status": "running",
                "message": "calling learning.profile.update",
                "progress": 40,
                "payload": {"callId": "mcp_profile_test", "skillId": "learning.profile.update"},
            })
            kwargs["on_event"]({
                "runId": "mar_profile_stream_test",
                "sequence": 8,
                "agentId": "quality-review-agent",
                "agentName": "Quality Review Agent",
                "stage": "quality_review",
                "status": "complete",
                "message": "quality review passed",
                "progress": 82,
                "payload": {"passed": True, "score": 94, "threshold": 70, "citationCount": 2},
            })
            return fake_analysis

        def fake_profile_save(_conn, _user_id, report, **_kwargs):
            return (
                {**report, "id": 909, "version": 1, "profileName": "stream-profile"},
                "updated",
            )

        with (
            patch.object(app_module, "xiaozhi_run_orchestrated", side_effect=fake_orchestrated),
            patch.object(app_module, "save_or_update_active_profile", side_effect=fake_profile_save),
            patch.object(app_module, "_schedule_profile_portrait_generation"),
            patch.object(app_module, "_schedule_profile_learning_path_generation", return_value=None),
            patch.object(app_module, "llm_runtime_for_user", return_value={
                "protocol": "openai",
                "model": "spark-x2-agent",
                "customized": True,
                "source": "user",
            }),
        ):
            response = self.client.post(
                "/api/learning-profile/analyze-stream",
                headers=self.headers,
                json={
                    "scaleScores": [3, 4, 4, 3, 4, 3],
                    "chatBackground": "STM32 GPIO",
                    "completedProfileDimensions": [f"dimension-{index}" for index in range(1, 11)],
                    "missingProfileDimensions": [],
                    "uploadFiles": [],
                },
            )
            body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content_type.startswith("text/event-stream"))
        self.assertEqual(response.headers.get("X-Accel-Buffering"), "no")
        self.assertIn("event: start", body)
        self.assertIn("event: progress", body)
        self.assertIn("event: result", body)
        self.assertIn("event: done", body)
        self.assertIn("mar_profile_stream_test", body)
        self.assertIn("mcp_profile_test", body)
        self.assertIn("spark-x2-agent", body)
        self.assertIn('"score": 94', body)
        self.assertIn('"reportId": 909', body)
        self.assertIn('"saveMode": "updated"', body)
        self.assertNotIn("apiKey", body)

    def test_xiaozhi_generated_learning_path_is_persisted_only_after_review(self) -> None:
        storage_before = self._snapshot_learning_path_storage()
        generated_config = app_module.default_learning_path_config()
        generated_config["meta"].update({"needsRegeneration": False, "generationState": "complete"})
        generated_config["weeks"] = [
            {
                "id": "week-1-xiaozhi",
                "order": 1,
                "weekLabel": "第一周",
                "title": "嵌小智生成并保存的路径",
                "status": "current",
                "enabled": True,
            }
        ]
        try:
            context = app_module.xiaozhi_latest_context(101)
            with patch.object(app_module, "generate_learning_path", return_value={"config": generated_config}):
                result = app_module.xiaozhi_run_platform_agent(
                    "learning_path",
                    "重新规划学习路径",
                    context,
                    101,
                )

            self.assertEqual(self._snapshot_learning_path_storage(), storage_before)
            self.assertEqual(result["learningPath"]["config"]["weeks"][0]["title"], "嵌小智生成并保存的路径")
            self.assertFalse(result["learningPath"]["config"]["meta"].get("persisted", False))

            result["orchestration"] = {
                "status": "complete",
                "profileReportId": self.profile_two["id"],
            }
            app_module._persist_xiaozhi_reviewed_learning_path_candidate("learning_path", 101, result)

            with app_module.auth_db() as conn:
                persisted = app_module.read_learning_path_config(conn, 101)
            self.assertEqual(persisted["weeks"][0]["title"], "嵌小智生成并保存的路径")
            self.assertTrue(result["learningPath"]["config"]["meta"]["persisted"])
        finally:
            self._restore_learning_path_storage(storage_before)

    def test_degraded_learning_path_cannot_prepare_resources(self) -> None:
        storage_before = self._snapshot_learning_path_storage()
        with app_module.auth_db() as conn:
            active_before = app_module.active_profile_for_user(conn, 101) or {}
            app_module.activate_profile(conn, 101, self.profile_two["id"])
        config = self._integrity_test_path_config("degraded", planner_source="fallback-rule")
        config["meta"].update({"generationStatus": "fallback", "degraded": True})
        stage_id = config["weeks"][0]["id"]
        try:
            with app_module.auth_db() as conn:
                app_module.write_learning_path_config(
                    conn,
                    config,
                    101,
                    profile_report_id=self.profile_two["id"],
                )

            response = self.client.get("/api/learning-path/config", headers=self.headers)
            self.assertEqual(response.status_code, 200)
            meta = response.get_json()["data"]["meta"]
            self.assertEqual(meta["personalizationStatus"], "degraded")
            self.assertFalse(meta["canPrepareResources"])
            self.assertTrue(meta["needsRegeneration"])

            prepared = self.client.post(
                f"/api/learning-path/stages/{stage_id}/prepare-resources",
                headers=self.headers,
                json={"parallelDispatch": True, "advance": False},
            )
            self.assertEqual(prepared.status_code, 409)
            self.assertIn("降级结果", prepared.get_json()["msg"])
        finally:
            self._restore_learning_path_storage(storage_before)
            previous_profile_id = int(active_before.get("id") or 0)
            if previous_profile_id > 0:
                with app_module.auth_db() as conn:
                    app_module.activate_profile(conn, 101, previous_profile_id)


if __name__ == "__main__":
    unittest.main()
