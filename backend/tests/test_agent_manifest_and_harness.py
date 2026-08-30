from __future__ import annotations

import copy
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

import app as app_module
from agent_harness.handlers import HandlerRegistry
from agent_harness.registry import SkillContractError
from agent_harness.runtime import XiaoZhiAgentHarness
from agent_manifest import DEFAULT_AGENT_MANIFEST, load_agent_manifest
from common import create_avatar_config, get_setting, setting_overrides
from multi_agent_runtime import review_specialist_output


class AgentManifestAndHarnessTests(unittest.TestCase):
    def _write_manifest(self, payload: dict) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "manifest.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def test_default_manifest_registers_only_implemented_roles_and_all_18_skills(self) -> None:
        self.assertEqual(len(DEFAULT_AGENT_MANIFEST.skills), 18)
        self.assertEqual(len(DEFAULT_AGENT_MANIFEST.agents), 22)
        agent_ids = {item["id"] for item in DEFAULT_AGENT_MANIFEST.agents}
        self.assertIn("qwen-multimodal-evidence-agent", agent_ids)
        self.assertIn("document-text-extraction-agent", agent_ids)
        self.assertIn("spark-text-reasoning-agent", agent_ids)
        self.assertFalse(any(agent_id.startswith("runtime-support-") for agent_id in agent_ids))
        role_counts = {
            role: sum(1 for agent in DEFAULT_AGENT_MANIFEST.agents if agent["role"] == role)
            for role in {"supervisor", "specialist", "runtime"}
        }
        self.assertEqual(role_counts, {"supervisor": 1, "specialist": 18, "runtime": 3})
        agents = {item["id"]: item for item in DEFAULT_AGENT_MANIFEST.agents}
        self.assertTrue(agents["learning-animation-agent"]["hidden"])
        self.assertTrue(agents["mcu-agent"]["hidden"])
        self.assertIn("中医药", agents["learning-animation-agent"]["hiddenReason"])
        self.assertIn("已下线", agents["mcu-agent"]["hiddenReason"])
        skill_agent_ids = {item["agentId"] for item in DEFAULT_AGENT_MANIFEST.skills}
        unbound_specialists = {
            item["id"]
            for item in DEFAULT_AGENT_MANIFEST.agents
            if item["role"] == "specialist" and item["id"] not in skill_agent_ids
        }
        self.assertEqual(unbound_specialists, {"generated-video-agent"})
        self.assertEqual(len({item["id"] for item in DEFAULT_AGENT_MANIFEST.skills}), 18)
        self.assertEqual(len({item["mcpTool"] for item in DEFAULT_AGENT_MANIFEST.skills}), 18)
        self.assertIn("resource.document.generate", {item["id"] for item in DEFAULT_AGENT_MANIFEST.skills})
        self.assertIn("resource.animation.generate", {item["id"] for item in DEFAULT_AGENT_MANIFEST.skills})
        self.assertIn("knowledge.base.manage", {item["id"] for item in DEFAULT_AGENT_MANIFEST.skills})
        self.assertIn("learning.feedback.submit", {item["id"] for item in DEFAULT_AGENT_MANIFEST.skills})
        self.assertIn("learner.profile.manage", {item["id"] for item in DEFAULT_AGENT_MANIFEST.skills})
        skills = {item["id"]: item for item in DEFAULT_AGENT_MANIFEST.skills}
        self.assertEqual(skills["learning.tutor.answer"]["route"], "/smart-tutor")
        self.assertEqual(skills["learning.effect.evaluate"]["route"], "/effect-assessment")
        for skill in skills.values():
            self.assertEqual(skill["inputSchema"]["type"], "object")
            self.assertEqual(skill["outputSchema"]["type"], "object")
            self.assertTrue(skill["inputSchema"]["required"])
            self.assertTrue(skill["outputSchema"]["required"])

    def test_all_manifest_skills_have_natural_language_and_frontend_routes(self) -> None:
        routing_cases = {
            "learning_background": "继续采集我的学习背景",
            "profile_update": "生成第一份学习画像",
            "profile_management": "列出画像历史",
            "learning_path": "根据当前画像规划学习路径",
            "learning_path_stage": "细化第一周阶段任务",
            "personalized_resources": "生成一套个性化资源包",
            "question_bank": "生成 GPIO 专项题库",
            "ppt": "制作 GPIO 基础 PPT",
            "document": "生成 GPIO 课程讲义",
            "mindmap": "生成 GPIO 思维导图",
            "video": "查找 GPIO 讲解视频",
            "animation": "生成 GPIO H5 动画",
            "mcu": "查看 GPIO 单片机实验",
            "interview": "开始 STM32 模拟面试",
            "smart_tutor": "辅导我理解 GPIO 中断",
            "effect_assessment": "评估我的学习效果",
            "learning_feedback": "这个资源我已经学完了",
            "knowledge_base": "查看我的知识库",
        }
        self.assertEqual(
            set(routing_cases),
            {str(skill["taskType"]) for skill in DEFAULT_AGENT_MANIFEST.skills},
        )
        misleading_model_result = {
            "intent": "chat",
            "resourceType": "none",
            "topic": "",
            "reply": "普通聊天回复",
            "source": "hermes_agent",
        }
        with patch.object(app_module, "run_xiaozhi_hermes_agent", return_value=misleading_model_result):
            for expected_type, message in routing_cases.items():
                with self.subTest(task_type=expected_type):
                    routed = app_module.xiaozhi_detect_intent(message, {})
                    expected_route = "document" if expected_type == "mcu" else expected_type
                    self.assertEqual(routed["resourceType"], expected_route)
                    if expected_type == "mcu":
                        self.assertEqual(routed["resourceType"], "document")
                        self.assertIn("中医医案辨析讲义", routed["reply"])
                    else:
                        self.assertEqual(routed["routingSource"], "deterministic")

        repo_root = Path(__file__).resolve().parents[2]
        router_source = (repo_root / "frontend" / "src" / "router" / "index.js").read_text(encoding="utf-8")
        launcher_source = (repo_root / "frontend" / "src" / "components" / "FloatingLogoLauncher.vue").read_text(encoding="utf-8")
        fallback_block = launcher_source.split("function fallbackTaskRoute", 1)[1].split("function openTaskFullPage", 1)[0]
        for skill in DEFAULT_AGENT_MANIFEST.skills:
            route_path = str(skill["route"]).split("?", 1)[0]
            self.assertTrue(
                f"path: '{route_path}'" in router_source
                or f"path: '{route_path}/:" in router_source,
                f"frontend route is not registered: {route_path}",
            )
            self.assertIn(f"type === '{skill['taskType']}'", fallback_block)

    def test_diagnostic_mcu_question_routes_to_tutor_without_launching_simulator(self) -> None:
        misleading_model_result = {
            "intent": "generate_resource",
            "resourceType": "mcu",
            "resourceTypes": ["mcu"],
            "topic": "单片机实验",
            "reply": "启动模拟器",
            "source": "hermes_agent",
        }
        with patch.object(app_module, "run_xiaozhi_hermes_agent", return_value=misleading_model_result):
            routed = app_module.xiaozhi_detect_intent("为什么我的单片机实验失败了", {})
        self.assertEqual(routed["resourceType"], "smart_tutor")
        self.assertNotIn("mcu", routed["resourceTypes"])
        self.assertEqual(routed["routingSource"], "deterministic")

    def test_task_backed_routes_never_keep_autostart(self) -> None:
        route = app_module.xiaozhi_route_with_task(
            "/personalized-resources/question-bank?module=generate&autostart=1&chapter=GPIO",
            "xz_route_guard",
        )
        query = parse_qs(urlparse(route).query)
        self.assertNotIn("autostart", query)
        self.assertEqual(query["xzTask"], ["xz_route_guard"])

        existing = app_module.xiaozhi_route_with_task(
            "/personalized-resources/mind-map?autostart=1&xzTask=old_task",
            "new_task",
        )
        existing_query = parse_qs(urlparse(existing).query)
        self.assertNotIn("autostart", existing_query)
        self.assertEqual(existing_query["xzTask"], ["new_task"])

        repo_root = Path(__file__).resolve().parents[2]
        question_view = (repo_root / "frontend" / "src" / "views" / "QuestionGeneratorView.vue").read_text(encoding="utf-8")
        self.assertIn("if (String(route.query.xzTask || '').trim()) return", question_view)

    def test_manifest_rejects_duplicate_and_illegal_permission(self) -> None:
        payload = json.loads(DEFAULT_AGENT_MANIFEST.path.read_text(encoding="utf-8"))
        duplicate = copy.deepcopy(payload)
        duplicate["skills"][1]["id"] = duplicate["skills"][0]["id"]
        with self.assertRaisesRegex(ValueError, "duplicate skill id"):
            load_agent_manifest(self._write_manifest(duplicate))

        illegal = copy.deepcopy(payload)
        illegal["skills"][0]["permissions"].append("system:root")
        with self.assertRaisesRegex(ValueError, "illegal permissions"):
            load_agent_manifest(self._write_manifest(illegal))

        missing_schema = copy.deepcopy(payload)
        missing_schema["skills"][0].pop("outputSchema")
        with self.assertRaisesRegex(ValueError, "outputSchema"):
            load_agent_manifest(self._write_manifest(missing_schema))

    def test_handler_registry_rejects_missing_manifest_handler(self) -> None:
        registry = HandlerRegistry()
        registry.register("learning_background.collect", lambda handler, args, progress: handler(args, progress))
        with self.assertRaisesRegex(ValueError, "missing handlers"):
            registry.validate_manifest(DEFAULT_AGENT_MANIFEST)

    def test_harness_trace_contains_profile_skill_mcp_and_reviews(self) -> None:
        harness = XiaoZhiAgentHarness()

        def specialist(arguments, progress):
            progress(
                {
                    "agentId": "learning-background-dialogue-agent",
                    "stage": "collect",
                    "status": "complete",
                    "message": "已完成背景采集",
                    "progress": 100,
                }
            )
            return {
                "message": "请继续说明每周可投入时间。",
                "dialogue": {
                    "reply": "请继续说明每周可投入时间。",
                    "collectedFields": {"学习目标": "完成 STM32 基础"},
                    "missingFields": ["可投入时间"],
                    "status": "collecting",
                    "source": "llm",
                },
            }

        result = harness.run(
            "learning_background",
            "[HARNESS-E2E-20260710] 背景采集",
            {"message": "我正在学习 STM32"},
            {
                "profileReportId": 42,
                "profile": {"id": 42, "profileName": "测试画像", "version": 3},
            },
            specialist,
            user_id=1,
            max_retries=0,
            runtime_settings={
                "LLM_PROTOCOL": "openai",
                "OPENAI_BASE_URL": "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2",
                "ANTHROPIC_MODEL": "astron-code-latest",
                "VISION_LLM_MODEL": "qwen3-vl-plus",
            },
        )
        trace = result["orchestration"]
        harness_trace = result["harness"]
        self.assertEqual(trace["rootAgent"], "xiaozhi-companion-agent")
        self.assertEqual(harness_trace["profileReportId"], 42)
        self.assertEqual(harness_trace["skill"]["id"], "learner.background.collect")
        self.assertEqual(harness_trace["skill"]["handlerKey"], "learning_background.collect")
        self.assertEqual(harness_trace["modelRuntime"]["model"], "astron-code-latest")
        self.assertEqual(
            harness_trace["modelRuntime"]["routing"]["image"]["modelId"],
            "qwen3-vl-plus",
        )
        self.assertEqual(harness_trace["mcp"]["toolCalls"][0]["status"], "complete")
        self.assertEqual(harness_trace["mcp"]["toolCalls"][0]["contract"]["input"], "passed")
        self.assertEqual(harness_trace["mcp"]["toolCalls"][0]["contract"]["output"], "passed")
        self.assertTrue(trace["handoffs"])
        self.assertIn("score", trace["review"])
        self.assertIn("sensitiveContentDetected", trace["review"])

    def test_contextvar_setting_overrides_are_thread_isolated(self) -> None:
        barrier = threading.Barrier(2)
        results: dict[str, str] = {}

        def read_model(name: str) -> None:
            with setting_overrides({"ANTHROPIC_MODEL": name}):
                barrier.wait(timeout=5)
                results[name] = get_setting("ANTHROPIC_MODEL")

        threads = [
            threading.Thread(target=read_model, args=("model-user-a",)),
            threading.Thread(target=read_model, args=("model-user-b",)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        self.assertEqual(results["model-user-a"], "model-user-a")
        self.assertEqual(results["model-user-b"], "model-user-b")

    def test_avatar_config_exposes_signed_url_without_long_lived_credentials(self) -> None:
        with setting_overrides(
            {
                "AVATAR_APP_ID": "test-app",
                "AVATAR_API_KEY": "test-api-key",
                "AVATAR_API_SECRET": "test-api-secret",
                "AVATAR_SCENE_ID": "test-scene",
                "AVATAR_ID": "test-avatar",
                "AVATAR_SIGN_HOST": "avatar.example.com",
                "AVATAR_SIGN_PATH": "/v1/interact",
            }
        ):
            config = create_avatar_config()
        self.assertTrue(config["signedUrl"].startswith("wss://avatar.example.com/v1/interact?"))
        self.assertNotIn("apiKey", config)
        self.assertNotIn("apiSecret", config)

    def test_avatar_runtime_endpoints_require_authentication(self) -> None:
        client = app_module.app.test_client()
        protected_requests = (
            ("get", "/api/avatar/config"),
            ("get", "/api/avatar/diagnostics"),
            ("post", "/api/avatar/legacy/start"),
            ("post", "/api/avatar/legacy/stop"),
            ("post", "/api/avatar/legacy/ping"),
            ("post", "/api/avatar/legacy/text"),
        )

        for method, path in protected_requests:
            with self.subTest(path=path):
                response = getattr(client, method)(path, json={} if method == "post" else None)
                self.assertEqual(response.status_code, 401)

    def test_harness_trace_uses_platform_model_when_user_has_no_override(self) -> None:
        harness = XiaoZhiAgentHarness()

        def specialist(arguments, progress):
            return {
                "message": "ok",
                "dialogue": {"reply": "ok", "missingFields": [], "source": "llm"},
            }

        with setting_overrides(
            {
                "LLM_PROTOCOL": "auto",
                "OPENAI_BASE_URL": "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2",
                "ANTHROPIC_BASE_URL": "https://maas-coding-api.cn-huabei-1.xf-yun.com/anthropic",
                "ANTHROPIC_MODEL": "astron-code-latest",
            }
        ):
            result = harness.run(
                "learning_background",
                "platform default trace",
                {},
                {"profileReportId": 7, "profile": {"id": 7}},
                specialist,
                user_id=1,
                max_retries=0,
            )

        runtime = result["harness"]["modelRuntime"]
        self.assertEqual(runtime["protocol"], "auto")
        self.assertEqual(runtime["model"], "astron-code-latest")
        self.assertEqual(runtime["contextWindow"], 262144)
        self.assertEqual(runtime["routing"]["image"]["handoffTo"]["modelId"], "astron-code-latest")
        self.assertEqual(runtime["baseUrl"], "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2")
        self.assertFalse(runtime["customized"])

    def test_harness_rejects_invalid_output_contract(self) -> None:
        harness = XiaoZhiAgentHarness()

        with self.assertRaisesRegex(SkillContractError, "dialogue"):
            harness.run(
                "learning_background",
                "contract validation",
                {},
                {},
                lambda arguments, progress: {"message": "missing dialogue"},
                user_id=1,
                max_retries=0,
            )

    def test_learning_path_manifest_accepts_one_progressive_phase(self) -> None:
        harness = XiaoZhiAgentHarness()
        skill = harness.registry.resolve("learning_path")

        harness.mcp_gateway.validate_output(
            skill,
            {
                "message": "第一周学习路径已生成",
                "learningPath": {
                    "phases": [{"id": "week-1", "title": "GPIO 基础"}],
                    "config": {"meta": {"generationState": "partial"}},
                },
            },
        )

    def test_failed_quality_review_is_not_marked_complete(self) -> None:
        harness = XiaoZhiAgentHarness()
        result = harness.run(
            "learning_background",
            "quality failure",
            {},
            {},
            lambda arguments, progress: {"message": "采集结果为空", "dialogue": {}},
            user_id=1,
            max_retries=0,
        )

        self.assertFalse(result["orchestration"]["review"]["passed"])
        self.assertEqual(result["orchestration"]["status"], "failed")

    def test_resource_quality_review_rejects_empty_video_results(self) -> None:
        review = review_specialist_output(
            "video",
            {
                "selectedResource": {
                    "type": "video",
                    "content": "未检索到视频",
                    "metadata": {"results": []},
                    "qualityEvaluation": {"score": 18, "passed": False},
                },
                "qualityEvaluation": {"score": 18, "passed": False},
            },
            {"citations": [{"id": "KB1"}]},
            68,
        )

        self.assertFalse(review["passed"])
        self.assertTrue(review["retryRecommended"])
        self.assertIn("质量评价未通过", "；".join(review["issues"]))

    def test_quality_review_rejects_degraded_learning_path(self) -> None:
        review = review_specialist_output(
            "learning_path",
            {
                "learningPath": {
                    "source": "fallback-rule",
                    "degraded": True,
                    "error": "invalid model JSON",
                    "phases": [{"id": "week-1"}, {"id": "week-2"}, {"id": "week-3"}],
                }
            },
            {"citations": [{"id": "KB1"}]},
            70,
        )

        self.assertFalse(review["passed"])
        self.assertFalse(review["structuralOk"])
        self.assertTrue(any("规则降级结果不能冒充成功" in issue for issue in review["issues"]))
        self.assertTrue(review["retryRecommended"])

    def test_quality_review_accepts_one_phase_for_partial_learning_path(self) -> None:
        review = review_specialist_output(
            "learning_path",
            {
                "learningPath": {
                    "source": "llm",
                    "degraded": False,
                    "phases": [{"id": "week-1", "title": "GPIO 基础"}],
                    "config": {"meta": {"generationState": "partial"}},
                }
            },
            {"citations": [{"id": "KB1"}]},
            70,
        )

        self.assertTrue(review["passed"])
        self.assertTrue(review["structuralOk"])
        self.assertTrue(any("渐进式学习路径" in item for item in review["strengths"]))

    def test_quality_review_rejects_one_phase_for_complete_learning_path(self) -> None:
        review = review_specialist_output(
            "learning_path",
            {
                "learningPath": {
                    "source": "llm",
                    "degraded": False,
                    "phases": [{"id": "week-1", "title": "GPIO 基础"}],
                    "config": {"meta": {"generationState": "complete"}},
                }
            },
            {"citations": [{"id": "KB1"}]},
            70,
        )

        self.assertFalse(review["passed"])
        self.assertFalse(review["structuralOk"])
        self.assertTrue(any("至少需要 3 个阶段" in item for item in review["issues"]))

    def test_learning_path_runtime_summary_reads_nested_generator_quality(self) -> None:
        question_summary = app_module._learning_path_task_runtime_summary(
            {
                "taskId": "xz_question",
                "status": "complete",
                "result": {
                    "questionGenerator": {
                        "qualityEvaluation": {"score": 91, "passed": True, "citationCount": 3}
                    }
                },
            }
        )
        ppt_summary = app_module._learning_path_task_runtime_summary(
            {
                "taskId": "xz_ppt",
                "status": "complete",
                "result": {"ppt": {"qualityEvaluation": {"score": 94, "passed": True}}},
            }
        )

        self.assertEqual(question_summary["qualityScore"], 91)
        self.assertTrue(question_summary["qualityPassed"])
        self.assertEqual(question_summary["citationCount"], 3)
        self.assertEqual(ppt_summary["qualityScore"], 94)
        self.assertTrue(ppt_summary["qualityPassed"])

        historical_summary = app_module._learning_path_task_runtime_summary(
            {
                "taskId": "xz_historical_ppt",
                "status": "complete",
                "result": {
                    "ppt": {"pages": [{"title": "第一页"}]},
                    "orchestration": {
                        "review": {"score": 95, "passed": True, "citationCount": 7}
                    },
                },
            }
        )
        self.assertEqual(historical_summary["qualityScore"], 95)
        self.assertTrue(historical_summary["qualityPassed"])
        self.assertEqual(historical_summary["citationCount"], 7)

    def test_smart_tutor_platform_uses_exact_question_and_previous_turn(self) -> None:
        captured = {}
        context = {
            "profile": {"id": 39},
            "recentTasks": [
                {
                    "taskId": "xz_previous_tutor",
                    "taskType": "smart_tutor",
                    "title": "GPIO 中断辅导",
                    "prompt": "GPIO 中断为什么没有触发？",
                    "result": {
                        "answer": "先确认中断配置链路。",
                        "tutor": {
                            "question": "GPIO 中断为什么没有触发？",
                            "answer": "先确认中断配置链路。",
                            "socraticQuestions": [{"question": "NVIC 是否已使能？"}],
                            "followUp": "请说出你的排查顺序。",
                        },
                    },
                }
            ],
        }

        def capture_tutor(payload: dict) -> dict:
            captured.update(payload)
            return {"answer": "先检查 NVIC、EXTI 映射和中断标志位。"}

        with patch.object(app_module, "xiaozhi_smart_tutor_result", side_effect=capture_tutor):
            result = app_module.xiaozhi_run_platform_agent(
                "smart_tutor",
                "一段很长的编排说明",
                context,
                101,
                params={
                    "question": "如果中断没有触发，我应该先检查哪三项？",
                    "conversationContext": "上一轮主题：GPIO 中断\n我的回答或追问：如果中断没有触发，我应该先检查哪三项？",
                    "previousTaskId": "xz_previous_tutor",
                },
            )

        self.assertEqual(captured["question"], "如果中断没有触发，我应该先检查哪三项？")
        self.assertEqual(captured["previousTaskId"], "xz_previous_tutor")
        self.assertEqual(captured["previousTurn"]["answer"], "先确认中断配置链路。")
        self.assertIn("我的回答或追问", captured["conversationContext"])
        self.assertEqual(result["previousTaskId"], "xz_previous_tutor")


if __name__ == "__main__":
    unittest.main()
