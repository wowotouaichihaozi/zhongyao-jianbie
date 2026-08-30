from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import learning_profile_workflow_agent as workflow_agent


class LearningProfileGreetingGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.original_db_path = workflow_agent.DB_PATH
        workflow_agent.DB_PATH = Path(self.tempdir.name) / "profile-workflow.sqlite3"
        workflow_agent.init_db()

    def tearDown(self) -> None:
        workflow_agent.DB_PATH = self.original_db_path
        self.tempdir.cleanup()

    def test_greeting_only_does_not_fill_profile_even_if_llm_hallucinates(self) -> None:
        hallucinated = {
            "reply": "你好，我们从你的中医学习方向开始。你目前主要在学习哪门中医课程？",
            "evidence": [
                {"dimension": dimension, "value": "已补齐", "confidence": 0.99}
                for dimension in workflow_agent.PROFILE_DIMENSIONS
            ],
            "next_dimension": "专业/课程背景",
            "user_intent": "补充画像信息",
        }

        with patch.object(workflow_agent, "_request_llm_text", return_value=json.dumps(hallucinated, ensure_ascii=False)):
            result = workflow_agent.run_learning_profile_workflow(
                [
                    {"role": "assistant", "content": "你好，我是你的数字人 AI 讲师，会陪你梳理中医学习画像。"},
                    {"role": "user", "content": "你好"},
                ],
                user_id="greeting-user",
                verbose=False,
            )

        self.assertEqual(result["status"], "collecting")
        self.assertEqual(result["nextDimension"], workflow_agent.PROFILE_DIMENSIONS[0])
        self.assertEqual(result["missingProfileDimensions"], workflow_agent.PROFILE_DIMENSIONS)
        self.assertEqual(result["completeness"], 0)
        self.assertEqual(result["workflow"]["candidateEvidence"], [])
        self.assertIn("中医", result["reply"])

    def test_model_failure_is_reported_instead_of_returning_a_fixed_question(self) -> None:
        with patch.object(
            workflow_agent,
            "_request_llm_text",
            side_effect=RuntimeError("provider unavailable"),
        ) as request_model:
            with self.assertRaises(workflow_agent.LearningProfileModelUnavailable):
                workflow_agent.run_learning_profile_workflow(
                    [{"role": "user", "content": "我在学习中药学"}],
                    user_id="unavailable-user",
                    verbose=False,
                )

        self.assertEqual(request_model.call_count, 2)

    def test_repeated_model_reply_is_retried_then_reported(self) -> None:
        repeated = {
            "reply": "你目前主要在学习哪门中医课程？",
            "evidence": [],
            "next_dimension": "专业/课程背景",
            "user_intent": "补充画像信息",
        }
        messages = [
            {"role": "assistant", "content": repeated["reply"]},
            {"role": "user", "content": "中药学"},
        ]
        with patch.object(
            workflow_agent,
            "_request_llm_text",
            return_value=json.dumps(repeated, ensure_ascii=False),
        ) as request_model:
            with self.assertRaises(workflow_agent.LearningProfileModelUnavailable):
                workflow_agent.run_learning_profile_workflow(
                    messages,
                    user_id="duplicate-user",
                    verbose=False,
                )

        self.assertEqual(request_model.call_count, 2)

    def test_last_dimension_can_complete_without_another_question(self) -> None:
        existing_profile = {
            dimension: f"已采集的{dimension}"
            for dimension in workflow_agent.PROFILE_DIMENSIONS
            if dimension != "难度接受程度"
        }
        completed = {
            "reply": "已记录你偏好适中难度，十个维度的信息已经收集完整。",
            "evidence": [
                {
                    "dimension": "难度接受程度",
                    "value": "适中，先巩固基础再逐步进阶",
                    "confidence": 0.96,
                }
            ],
            "next_dimension": "",
            "user_intent": "补充画像信息",
        }

        with patch.object(
            workflow_agent,
            "_request_llm_text",
            return_value=json.dumps(completed, ensure_ascii=False),
        ) as request_model:
            result = workflow_agent.run_learning_profile_workflow(
                [
                    {"role": "assistant", "content": "你更喜欢基础、适中还是挑战性较高的任务？"},
                    {"role": "user", "content": "适中"},
                ],
                user_id="last-dimension-user",
                profile=existing_profile,
                verbose=False,
            )

        self.assertEqual(request_model.call_count, 1)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["completeness"], 100)
        self.assertEqual(result["missingProfileDimensions"], [])
        self.assertEqual(result["nextDimension"], "")
        self.assertEqual(
            result["studentProfile"]["难度接受程度"],
            "适中，先巩固基础再逐步进阶",
        )

    def test_goal_topic_does_not_fabricate_foundation_or_progress(self) -> None:
        for answer in ["辨析中药", "学习方剂", "想掌握辨证"]:
            with self.subTest(answer=answer):
                extracted = workflow_agent.extract_by_rules([
                    {"role": "user", "content": answer},
                ])

                self.assertNotIn("当前知识基础", extracted["profile_patch"])
                self.assertNotIn("学习进度", extracted["profile_patch"])

    def test_goal_answer_continues_with_current_knowledge_foundation(self) -> None:
        for index, answer in enumerate(["辨析中药", "学习方剂", "想掌握辨证"]):
            model_result = {
                "reply": f"已记录你的目标是{answer}。你目前具备怎样的中医知识基础？",
                "evidence": [
                    {
                        "dimension": "学习目标",
                        "value": answer,
                        "confidence": 0.96,
                    }
                ],
                "next_dimension": "当前知识基础",
                "user_intent": "补充画像信息",
            }
            with self.subTest(answer=answer):
                with patch.object(
                    workflow_agent,
                    "_request_llm_text",
                    return_value=json.dumps(model_result, ensure_ascii=False),
                ):
                    result = workflow_agent.run_learning_profile_workflow(
                        [
                            {"role": "assistant", "content": "你学习中药鉴别的主要目标是什么？"},
                            {"role": "user", "content": answer},
                        ],
                        user_id=f"goal-routing-user-{index}",
                        profile={"专业/课程背景": "中医专业"},
                        verbose=False,
                    )

                self.assertEqual(result["nextDimension"], "当前知识基础")
                self.assertIn("当前知识基础", result["missingProfileDimensions"])
                self.assertFalse(workflow_agent.is_filled(result["studentProfile"].get("学习进度")))

    def test_rule_filled_model_next_dimension_is_recomputed(self) -> None:
        model_result = {
            "reply": "已记录你的学习经历。你目前有哪些薄弱知识点？",
            "evidence": [],
            "next_dimension": "当前知识基础",
            "user_intent": "补充画像信息",
        }
        with patch.object(
            workflow_agent,
            "_request_llm_text",
            return_value=json.dumps(model_result, ensure_ascii=False),
        ):
            result = workflow_agent.run_learning_profile_workflow(
                [
                    {"role": "assistant", "content": "请介绍你的当前基础和学习进度。"},
                    {"role": "user", "content": "我学过中医基础，目前正在学方剂。"},
                ],
                user_id="rule-model-next-dimension-user",
                profile={
                    "专业/课程背景": "中医专业",
                    "学习目标": ["提升辨证能力"],
                },
                verbose=False,
            )

        self.assertEqual(result["nextDimension"], "薄弱知识点")
        self.assertEqual(result["studentProfile"]["当前知识基础"], "我学过中医基础，目前正在学方剂。")
        self.assertEqual(result["studentProfile"]["学习进度"], "我学过中医基础，目前正在学方剂。")

    def test_short_numeric_time_answer_uses_daily_question_cadence(self) -> None:
        extracted = workflow_agent.extract_by_rules([
            {"role": "assistant", "content": "你平时每天能投入多少时间学习中药呢？"},
            {"role": "user", "content": "7"},
        ])

        self.assertEqual(extracted["profile_patch"]["可投入时间"], "每天约 7 小时")

    def test_short_numeric_time_answer_uses_weekly_question_cadence(self) -> None:
        extracted = workflow_agent.extract_by_rules([
            {"role": "assistant", "content": "你每周能投入多少时间复习中药呢？"},
            {"role": "user", "content": "7"},
        ])

        self.assertEqual(extracted["profile_patch"]["可投入时间"], "每周约 7 小时")

    def test_short_numeric_time_turn_has_enough_model_output_budget(self) -> None:
        model_result = {
            "reply": "已记录你每天约有 7 小时可用于学习。你最容易出现哪类辨析错误？",
            "evidence": [],
            "next_dimension": "易错点类型",
            "user_intent": "补充画像信息",
        }
        profile = {
            "专业/课程背景": "中药学",
            "学习目标": ["临床用药"],
            "当前知识基础": "刚入门",
            "学习进度": "刚开始学",
            "薄弱知识点": ["药材辨析"],
        }
        messages = [
            {"role": "assistant", "content": "你平时每天能投入多少时间学习中药呢？"},
            {"role": "user", "content": "7"},
        ]

        with patch.object(
            workflow_agent,
            "_request_llm_text",
            return_value=json.dumps(model_result, ensure_ascii=False),
        ) as request_model:
            result = workflow_agent.run_learning_profile_workflow(
                messages,
                user_id="daily-time-user",
                profile=profile,
                verbose=False,
            )

        self.assertEqual(request_model.call_args.kwargs["max_tokens"], workflow_agent.PROFILE_AGENT_MAX_TOKENS)
        self.assertEqual(request_model.call_args.kwargs["timeout"], 90)
        self.assertIs(request_model.call_args.kwargs["thinking"], False)
        self.assertEqual(result["studentProfile"]["可投入时间"], "每天约 7 小时")
        self.assertEqual(result["nextDimension"], "易错点类型")
        self.assertNotIn("大模型不可用", result["reply"])


if __name__ == "__main__":
    unittest.main()
