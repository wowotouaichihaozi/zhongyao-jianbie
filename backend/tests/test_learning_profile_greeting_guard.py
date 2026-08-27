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


if __name__ == "__main__":
    unittest.main()
