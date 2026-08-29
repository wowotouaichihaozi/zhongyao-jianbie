import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from hermes_xiaozhi_agent import HERMES_XIAOZHI_SYSTEM_PROMPT, HermesAgentConfig, HermesXiaoZhiAgent


class HermesPromptCacheTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
