import unittest

from agent_manifest import DEFAULT_AGENT_MANIFEST
from harness_real_e2e import ADDITIONAL_TUTOR_CASES, CASES, validate_specific


class HarnessRealE2ETests(unittest.TestCase):
    def test_real_e2e_cases_cover_every_manifest_skill(self):
        case_tools = {tool for tool, _arguments in CASES}
        manifest_tools = {str(item.get("mcpTool") or "") for item in DEFAULT_AGENT_MANIFEST.skills}

        self.assertEqual(case_tools, manifest_tools)
        self.assertEqual(len(CASES), len(DEFAULT_AGENT_MANIFEST.skills))

    def test_real_e2e_produces_five_distinct_tutoring_cases(self):
        tutor_cases = [case for case in [*CASES, *ADDITIONAL_TUTOR_CASES] if case[0] == "learning.tutor.answer"]

        self.assertEqual(len(tutor_cases), 5)
        self.assertEqual(len({case[1]["topic"] for case in tutor_cases}), 5)

    def test_profile_management_validation_requires_active_profile(self):
        valid = {
            "profileManagement": {
                "action": "list",
                "profiles": [{"id": 39, "isActive": True}],
                "activeReportId": 39,
            }
        }
        invalid = {
            "profileManagement": {
                "action": "list",
                "profiles": [],
                "activeReportId": None,
            }
        }

        self.assertEqual(validate_specific("profile_management", valid), [])
        self.assertIn("画像管理未返回当前激活画像", validate_specific("profile_management", invalid))

    def test_learning_feedback_validation_requires_path_evidence_writeback(self):
        valid = {
            "feedback": {
                "id": 8,
                "outcome": "needs_review",
                "profileReportId": 39,
                "pathCache": {
                    "learningFeedback": {"outcome": "needs_review"},
                },
            }
        }
        invalid = {
            "feedback": {
                "id": 8,
                "outcome": "needs_review",
                "profileReportId": 39,
                "pathCache": {},
            }
        }

        self.assertEqual(validate_specific("learning_feedback", valid), [])
        self.assertIn(
            "学习反馈未回写学习路径证据",
            validate_specific("learning_feedback", invalid),
        )

    def test_learning_path_validation_rejects_silent_rule_fallback(self):
        result = {
            "learningPath": {
                "source": "fallback-rule",
                "degraded": True,
                "error": "invalid model JSON",
                "phases": [{"id": "week-1"}, {"id": "week-2"}, {"id": "week-3"}],
            }
        }

        self.assertIn(
            "学习路径使用了规则降级结果，未完成真实模型结构化生成",
            validate_specific("learning_path", result),
        )

    def test_learning_path_validation_rejects_profile_context_pollution(self):
        result = {
            "learningPath": {
                "source": "llm",
                "degraded": False,
                "phases": [{"id": "week-1"}, {"id": "week-2"}, {"id": "week-3"}],
                "profileContext": {
                    "goals": ["完成课程设计", "week-1-gpio", "第一周"],
                    "resourcePreferences": [
                        "PPT课件",
                        "{'title': '历史视频', 'type': 'video', 'updatedAt': '2026-07-12T19:33:16+00:00'}",
                    ],
                    "timeBudget": "2026-07-12T19:49:44.926517+00:00",
                    "learningStyle": "项目实践驱动",
                    "topicKeywords": ["GPIO输入输出", "驱动开发基础"],
                },
            }
        }

        errors = validate_specific("learning_path", result)

        self.assertIn("学习路径可投入时间缺失或被时间戳污染", errors)
        self.assertIn("学习路径目标混入周次或路由标识", errors)
        self.assertIn("学习路径资源偏好混入历史资源记录", errors)
        self.assertIn("学习路径把非驱动语义误判为驱动开发主题", errors)

    def test_learning_path_validation_accepts_clean_profile_context(self):
        result = {
            "learningPath": {
                "source": "llm",
                "degraded": False,
                "phases": [{"id": "week-1"}, {"id": "week-2"}, {"id": "week-3"}],
                "profileContext": {
                    "goals": ["完成课程设计"],
                    "resourcePreferences": ["PPT课件"],
                    "timeBudget": "每周能投入6小时",
                    "learningStyle": "分步骤讲解、项目实践驱动",
                    "topicKeywords": ["STM32基础与外设配置", "GPIO输入输出"],
                },
            }
        }

        self.assertEqual(validate_specific("learning_path", result), [])

    def test_stage_detail_validation_requires_llm_and_complete_structure(self):
        fallback = {
            "stageDetail": {
                "source": "profile-rule-agent",
                "degraded": True,
                "goals": ["目标"],
                "weeks": [{"week": "第一周"}],
                "resources": [{"type": "ppt"}],
                "checkpoints": ["检查点"],
                "summary": "x" * 240,
            }
        }

        self.assertIn(
            "阶段细化使用了规则降级结果，未完成真实模型结构化生成",
            validate_specific("learning_path_stage", fallback),
        )


if __name__ == "__main__":
    unittest.main()
