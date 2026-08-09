from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from PIL import Image

import learning_agents
from common import setting_overrides
from model_routing import resolve_model_routing


class _JsonResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload, ensure_ascii=False).encode("utf-8")


class ModelRoutingTests(unittest.TestCase):
    def test_default_routing_uses_spark_for_text_and_kimi_for_images(self) -> None:
        with setting_overrides(
            {
                "ANTHROPIC_MODEL": "xsparkx2agent",
                "VISION_LLM_MODEL": "xopkimik26",
                "LLM_CONTEXT_WINDOW": "262144",
                "VISION_LLM_CONTEXT_WINDOW": "262144",
            }
        ):
            runtime = resolve_model_routing()

        self.assertEqual(runtime["model"], "xsparkx2agent")
        self.assertEqual(runtime["modelName"], "Spark X2 Agent")
        self.assertEqual(runtime["contextWindow"], 262144)
        self.assertEqual(runtime["routing"]["image"]["modelId"], "xopkimik26")
        self.assertEqual(
            runtime["routing"]["image"]["handoffTo"]["modelId"],
            "xsparkx2agent",
        )
        self.assertEqual(
            runtime["routing"]["document"]["handoffTo"]["modelId"],
            "xsparkx2agent",
        )

    def test_vision_request_uses_openai_content_parts_and_kimi_model(self) -> None:
        import io

        image_buffer = io.BytesIO()
        Image.new("RGB", (24, 16), color=(255, 255, 255)).save(image_buffer, format="PNG")
        captured = {}

        def fake_urlopen(request, timeout=0):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return _JsonResponse(
                {
                    "choices": [
                        {"message": {"content": "可见文字：STM32；包含 GPIO 接线图。"}}
                    ]
                }
            )

        with setting_overrides(
            {
                "OPENAI_BASE_URL": "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2",
                "ANTHROPIC_AUTH_TOKEN": "test-token",
                "VISION_LLM_MODEL": "xopkimik26",
            }
        ), patch.object(learning_agents.urllib.request, "urlopen", side_effect=fake_urlopen):
            result = learning_agents.request_llm_image_understanding(
                image_buffer.getvalue(),
                filename="stm32.png",
                timeout=30,
            )

        self.assertIn("GPIO", result)
        self.assertTrue(captured["url"].endswith("/v2/chat/completions"))
        self.assertEqual(captured["body"]["model"], "xopkimik26")
        user_content = captured["body"]["messages"][1]["content"]
        self.assertEqual(user_content[0]["type"], "text")
        self.assertEqual(user_content[1]["type"], "image_url")
        self.assertTrue(user_content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,"))


if __name__ == "__main__":
    unittest.main()
