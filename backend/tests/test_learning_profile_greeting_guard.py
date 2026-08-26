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
            "reply": "你的中医学习画像已经基本补齐，我会根据这些信息为你推荐更合适的学习路径和资源。",
            "evidence": [
                {"dimension": dimension, "value": "已补齐", "confidence": 0.99}
                for dimension in workflow_agent.PROFILE_DIMENSIONS
            ],
            "next_dimension": "",
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
        self.assertNotIn("已经基本补齐", result["reply"])


if __name__ == "__main__":
    unittest.main()
