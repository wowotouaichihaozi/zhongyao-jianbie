import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from hermes_xiaozhi_agent import HERMES_XIAOZHI_SYSTEM_PROMPT, HermesAgentConfig, HermesXiaoZhiAgent


class HermesPromptCacheTests(unittest.TestCase):
    def _agent(self):
        return HermesXiaoZhiAgent(HermesAgentConfig(
            agent_id="xiaozhi-companion-agent",
            agent_name="岐小智",
            api_url="https://api.deepseek.com/chat/completions",
            auth_token="test-token",
            model="deepseek-chat",
        ))

    def test_system_prompt_is_a_stable_module_constant(self):
        config = HermesAgentConfig(
            agent_id="xiaozhi-companion-agent",
            agent_name="岐小智",
            api_url="https://api.deepseek.com/chat/completions",
            auth_token="test-token",
            model="deepseek-chat",
        )
        first_agent = HermesXiaoZhiAgent(config)
        second_agent = HermesXiaoZhiAgent(config)

        self.assertIs(first_agent._system_prompt(), HERMES_XIAOZHI_SYSTEM_PROMPT)
        self.assertEqual(first_agent._system_prompt(), second_agent._system_prompt())
        self.assertNotIn("User message:", HERMES_XIAOZHI_SYSTEM_PROMPT)
        self.assertNotIn("Platform context summary:", HERMES_XIAOZHI_SYSTEM_PROMPT)
        self.assertIn("Response JSON shape:", HERMES_XIAOZHI_SYSTEM_PROMPT)

    def test_relevant_memories_survive_large_volatile_context_without_raw_truncation(self):
        prompt = self._agent()._user_prompt(
            "请继续安排麻黄与桂枝辨析",
            {
                "profileReportId": 9,
                "profileName": "中药辨析画像",
                "profile": {"goal": "辨析相似药材"},
                "longTermMemories": [{"id": 41, "summary": "麻黄与桂枝容易混淆"}],
                "agentConversation": {"huge": "x" * 2_000_000},
                "learningEvidence": {"huge": "y" * 2_000_000},
            },
        )

        self.assertIn('"id":41', prompt)
        self.assertIn("麻黄与桂枝容易混淆", prompt)
        self.assertNotIn("x" * 1000, prompt)
        self.assertLess(len(prompt), 20_000)
        self.assertLess(prompt.index("Stable learner/profile context"), prompt.index("User message:"))
        self.assertLess(prompt.index("Relevant long-term learner memories"), prompt.index("User message:"))


if __name__ == "__main__":
    unittest.main()
