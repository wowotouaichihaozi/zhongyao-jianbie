import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as app_module
from agent_manifest import DEFAULT_AGENT_MANIFEST
from database_schema import init_auth_schema


class McpProtocolApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.original_db_path = app_module.AUTH_DB_PATH
        app_module.AUTH_DB_PATH = Path(cls.tempdir.name) / "mcp-api-test.sqlite3"
        app_module.app.config.update(TESTING=True)
        with app_module.auth_db() as conn:
            init_auth_schema(conn)
            now = "2026-07-12T03:45:00+08:00"
            conn.execute(
                """
                INSERT INTO users
                    (id, username, display_name, password_hash, role, avatar_url, created_at, updated_at)
                VALUES (701, 'mcp-api-user', 'MCP API User', ?, 'user', '/userlogo.png', ?, ?)
                """,
                (app_module.password_hash("mcp-api-password"), now, now),
            )
            profile = app_module.create_profile_version(
                conn,
                701,
                {
                    "timestamp": now,
                    "aiAnalysis": {
                        "summary": "MCP 契约测试画像",
                        "weaknesses": ["GPIO 中断"],
                    },
                },
                profile_name="MCP 契约测试画像",
                start_new_profile=True,
                timestamp=now,
            )
            cls.profile_id = int(profile["id"])
            with app_module.app.test_request_context(
                "/api/auth/login",
                headers={"User-Agent": "mcp-api-test"},
            ):
                cls.token = app_module.create_session(conn, 701)
        cls.client = app_module.app.test_client()
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    @classmethod
    def tearDownClass(cls) -> None:
        app_module.AUTH_DB_PATH = cls.original_db_path
        cls.tempdir.cleanup()

    def rpc(self, method: str, params=None, request_id=1):
        return self.client.post(
            "/api/xiaozhi/mcp",
            headers=self.headers,
            json={
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params or {},
            },
        )

    def test_mcp_requires_authentication_and_valid_jsonrpc(self) -> None:
        unauthorized = self.client.post(
            "/api/xiaozhi/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}},
        )
        self.assertEqual(unauthorized.status_code, 401)

        invalid = self.client.post(
            "/api/xiaozhi/mcp",
            headers=self.headers,
            json={"id": 2, "method": "ping", "params": {}},
        )
        self.assertEqual(invalid.status_code, 200)
        self.assertEqual(invalid.get_json()["error"]["code"], -32600)

    def test_initialize_ping_and_initialized_notification(self) -> None:
        initialized = self.rpc(
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0"},
            },
        )
        result = initialized.get_json()["result"]
        self.assertEqual(initialized.status_code, 200)
        self.assertEqual(result["serverInfo"]["name"], "xiaozhi-agent-harness")
        self.assertIn("tools", result["capabilities"])
        self.assertIn("resources", result["capabilities"])
        self.assertIn("prompts", result["capabilities"])

        notification = self.rpc("notifications/initialized", request_id=None)
        self.assertEqual(notification.status_code, 202)
        self.assertEqual(self.rpc("ping").get_json()["result"], {})

    def test_all_tools_resources_and_prompts_are_discoverable(self) -> None:
        tools = self.rpc("tools/list").get_json()["result"]["tools"]
        resources = self.rpc("resources/list").get_json()["result"]["resources"]
        prompts = self.rpc("prompts/list").get_json()["result"]["prompts"]
        expected_tool_count = len(DEFAULT_AGENT_MANIFEST.skills)

        self.assertEqual(len(tools), expected_tool_count)
        self.assertEqual(len({item["name"] for item in tools}), expected_tool_count)
        self.assertEqual(len(resources), 5)
        self.assertEqual(len(prompts), 2)
        for tool in tools:
            self.assertEqual(tool["inputSchema"]["type"], "object")
            self.assertEqual(tool["outputSchema"]["type"], "object")
            self.assertTrue(tool["inputSchema"]["required"])
            self.assertTrue(tool["outputSchema"]["required"])

        for resource in resources:
            response = self.rpc("resources/read", {"uri": resource["uri"]})
            self.assertEqual(response.status_code, 200)
            contents = response.get_json()["result"]["contents"]
            self.assertEqual(contents[0]["uri"], resource["uri"])
            self.assertEqual(contents[0]["mimeType"], "application/json")

        for prompt in prompts:
            response = self.rpc(
                "prompts/get",
                {"name": prompt["name"], "arguments": {"topic": "STM32 GPIO"}},
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.get_json()["result"]["messages"])

    def test_every_manifest_tool_can_create_a_supervised_task(self) -> None:
        tools = self.rpc("tools/list").get_json()["result"]["tools"]
        expected_tool_count = len(DEFAULT_AGENT_MANIFEST.skills)
        with patch.object(app_module.threading, "Thread") as thread_class:
            for index, tool in enumerate(tools, start=1):
                response = self.rpc(
                    "tools/call",
                    {
                        "name": tool["name"],
                        "arguments": {"topic": f"MCP protocol test {index}"},
                    },
                    request_id=100 + index,
                )
                self.assertEqual(response.status_code, 200)
                payload = response.get_json()
                self.assertNotIn("error", payload)
                structured = payload["result"]["structuredContent"]
                self.assertEqual(structured["skill"]["id"], tool["name"])
                self.assertTrue(structured["task"]["taskId"])
                self.assertFalse(payload["result"]["isError"])

        self.assertEqual(thread_class.call_count, expected_tool_count)
        self.assertEqual(thread_class.return_value.start.call_count, expected_tool_count)

    def test_invalid_tool_arguments_do_not_create_a_task(self) -> None:
        with app_module.auth_db() as conn:
            before = int(
                conn.execute(
                    "SELECT COUNT(*) AS total FROM xiaozhi_tasks WHERE user_id = ?",
                    (701,),
                ).fetchone()["total"]
            )
        with patch.object(app_module.threading, "Thread") as thread_class:
            response = self.rpc(
                "tools/call",
                {"name": "learning.tutor.answer", "arguments": {}},
            )
        payload = response.get_json()
        self.assertEqual(payload["error"]["code"], -32602)
        self.assertIn("topic", payload["error"]["data"]["contractError"])
        thread_class.assert_not_called()
        with app_module.auth_db() as conn:
            after = int(
                conn.execute(
                    "SELECT COUNT(*) AS total FROM xiaozhi_tasks WHERE user_id = ?",
                    (701,),
                ).fetchone()["total"]
            )
        self.assertEqual(after, before)

    def test_learning_feedback_tool_preserves_the_source_resource_task(self) -> None:
        with patch.object(app_module.threading, "Thread") as thread_class:
            response = self.rpc(
                "tools/call",
                {
                    "name": "learning.feedback.submit",
                    "arguments": {
                        "topic": "GPIO 学习反馈",
                        "taskId": "source-resource-task-701",
                        "outcome": "completed",
                    },
                },
            )
        payload = response.get_json()
        self.assertNotIn("error", payload)
        queued_task_id = payload["result"]["structuredContent"]["task"]["taskId"]
        thread_args = thread_class.call_args.kwargs["args"]
        self.assertEqual(thread_args[0], queued_task_id)
        self.assertEqual(thread_args[2], "learning_feedback")
        self.assertEqual(thread_args[4]["sourceTaskId"], "source-resource-task-701")
        self.assertNotEqual(thread_args[4]["sourceTaskId"], queued_task_id)
        with app_module.auth_db() as conn:
            conn.execute("DELETE FROM xiaozhi_tasks WHERE task_id = ?", (queued_task_id,))

    def test_profile_driven_tool_requires_an_active_profile(self) -> None:
        with app_module.auth_db() as conn:
            app_module.reset_profile_state(conn, 701)
        try:
            with patch.object(app_module.threading, "Thread") as thread_class:
                response = self.rpc(
                    "tools/call",
                    {
                        "name": "resource.ppt.generate",
                        "arguments": {"topic": "GPIO 课件"},
                    },
                )
            payload = response.get_json()
            self.assertEqual(payload["error"]["code"], -32010)
            self.assertEqual(payload["error"]["data"]["errorCode"], "ACTIVE_PROFILE_REQUIRED")
            thread_class.assert_not_called()
        finally:
            with app_module.auth_db() as conn:
                app_module.activate_profile(conn, 701, self.profile_id)

    def test_profile_refresh_tool_can_queue_first_profile_without_active_profile(self) -> None:
        with app_module.auth_db() as conn:
            app_module.reset_profile_state(conn, 701)
        task_id = ""
        try:
            with patch.object(app_module.threading, "Thread") as thread_class:
                response = self.rpc(
                    "tools/call",
                    {
                        "name": "learner.profile.refresh",
                        "arguments": {"topic": "生成第一份学习画像"},
                    },
                )
            payload = response.get_json()
            self.assertNotIn("error", payload)
            structured = payload["result"]["structuredContent"]
            self.assertEqual(structured["skill"]["id"], "learner.profile.refresh")
            self.assertEqual(structured["task"]["type"], "profile_update")
            task_id = structured["task"]["taskId"]
            thread_class.return_value.start.assert_called_once()
        finally:
            with app_module.auth_db() as conn:
                if task_id:
                    conn.execute("DELETE FROM xiaozhi_tasks WHERE task_id = ?", (task_id,))
                app_module.activate_profile(conn, 701, self.profile_id)

    def test_failed_quality_review_persists_failed_task_with_trace(self) -> None:
        task_id = app_module.xiaozhi_create_task(
            701,
            "learning_background",
            "quality failure",
            "quality failure",
            "/learning-profile?collect=chat",
        )
        failed_result = {
            "message": "专业智能体已返回，但审核未通过",
            "orchestration": {
                "status": "failed",
                "review": {"passed": False, "issues": ["缺少有效追问"]},
                "events": [],
                "agentRuns": [],
            },
        }
        with patch.object(app_module, "xiaozhi_run_orchestrated", return_value=failed_result):
            app_module._xiaozhi_run_resource_task(
                task_id,
                701,
                "learning_background",
                "quality failure",
                {},
            )

        with app_module.auth_db() as conn:
            row = conn.execute(
                "SELECT * FROM xiaozhi_tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        task = app_module.xiaozhi_task_from_row(row)
        self.assertEqual(task["status"], "failed")
        self.assertIn("缺少有效追问", task["error"])
        self.assertEqual(task["result"]["currentStage"], "quality_review_failed")
        self.assertEqual(task["result"]["orchestration"]["status"], "failed")

    def test_all_legacy_specialist_outputs_are_normalized_to_skill_contracts(self) -> None:
        cases = {
            "learning_background": {"reply": "请继续说明学习目标", "missingFields": []},
            "profile_update": {"summary": "画像总结", "dimensionScores": [{"name": "基础", "score": 60}]},
            "profile_management": {"profileManagement": {"action": "list", "profiles": []}},
            "learning_path": {"phases": [{"id": "1"}, {"id": "2"}, {"id": "3"}]},
            "learning_path_stage": {"tasks": [{"id": "1"}]},
            "personalized_resources": {"resources": [{}, {}, {}, {}, {}]},
            "question_bank": {"question_bank": {"questions": []}},
            "ppt": {"pages": [{"id": "1"}]},
            "document": {"document": {}, "qualityEvaluation": {}},
            "mindmap": {"resources": [{"type": "mindmap"}]},
            "video": {"resources": [{"type": "video"}]},
            "animation": {"animation": {}, "qualityEvaluation": {}},
            "mcu": {"resources": [{"type": "simulator"}]},
            "interview": {"sessionId": "session-1", "question": "请解释 GPIO"},
            "smart_tutor": {"answer": "先判断中断标志位。"},
            "effect_assessment": {"summary": "学习效果稳定提升"},
            "learning_feedback": {"feedback": {"id": 1, "outcome": "completed", "profileReportId": 1}},
            "knowledge_base": {"collections": []},
        }
        for task_type, raw in cases.items():
            with self.subTest(task_type=task_type):
                normalized = app_module.xiaozhi_normalize_skill_output(task_type, "STM32", raw)
                skill = app_module.DEFAULT_AGENT_HARNESS.registry.resolve(task_type)
                app_module.DEFAULT_AGENT_HARNESS.mcp_gateway.validate_output(skill, normalized)
                for key, value in raw.items():
                    self.assertEqual(normalized[key], value)

    def test_orchestrated_review_failure_raises_with_original_trace(self) -> None:
        failed_result = {
            "message": "review failed",
            "orchestration": {
                "status": "failed",
                "runId": "run-review-failed",
                "review": {"passed": False, "issues": ["结构不完整"]},
            },
        }
        with (
            patch.object(app_module.DEFAULT_AGENT_HARNESS, "run", return_value=failed_result),
            patch.object(app_module, "xiaozhi_persist_orchestration") as persist,
        ):
            with self.assertRaises(app_module.SkillReviewError) as raised:
                app_module.xiaozhi_run_orchestrated(
                    "learning_background",
                    "review failure",
                    {},
                    701,
                    lambda arguments, progress: {},
                    context={"profileReportId": self.profile_id, "profile": {"id": self.profile_id}},
                )

        self.assertEqual(raised.exception.result["orchestration"]["runId"], "run-review-failed")
        self.assertIn("结构不完整", str(raised.exception))
        persist.assert_called_once()

    def test_unknown_method_tool_resource_and_prompt_return_jsonrpc_errors(self) -> None:
        cases = [
            ("unknown/method", {}, -32601),
            ("tools/call", {"name": "unknown.tool", "arguments": {}}, -32602),
            ("resources/read", {"uri": "unknown://resource"}, -32002),
            ("prompts/get", {"name": "unknown-prompt", "arguments": {}}, -32602),
        ]
        for method, params, expected_code in cases:
            response = self.rpc(method, params)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json()["error"]["code"], expected_code)


if __name__ == "__main__":
    unittest.main()
