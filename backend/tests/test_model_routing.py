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
    def test_default_routing_uses_spark_for_text_and_qwen_for_images(self) -> None:
        with setting_overrides(
            {
                "ANTHROPIC_MODEL": "astron-code-latest",
                "VISION_LLM_MODEL": "qwen3-vl-plus",
                "LLM_CONTEXT_WINDOW": "262144",
                "VISION_LLM_CONTEXT_WINDOW": "131072",
            }
        ):
            runtime = resolve_model_routing()

        self.assertEqual(runtime["model"], "astron-code-latest")
        self.assertEqual(runtime["modelName"], "Spark X2 Flash")
        self.assertEqual(runtime["contextWindow"], 262144)
        self.assertEqual(runtime["routing"]["image"]["modelId"], "qwen3-vl-plus")
        self.assertEqual(runtime["routing"]["image"]["agentId"], "qwen-multimodal-evidence-agent")
        self.assertEqual(runtime["routing"]["image"]["provider"], "Alibaba Bailian")
        self.assertEqual(runtime["routing"]["audio"]["modelId"], "qwen3-omni-flash")
        self.assertEqual(runtime["routing"]["audio"]["handoffTo"]["modelId"], "astron-code-latest")
        self.assertEqual(
            runtime["routing"]["image"]["handoffTo"]["modelId"],
            "astron-code-latest",
        )
        self.assertEqual(
            runtime["routing"]["document"]["handoffTo"]["modelId"],
            "astron-code-latest",
        )

    def test_vision_request_uses_independent_bailian_config_and_openai_content_parts(self) -> None:
        import io

        image_buffer = io.BytesIO()
        Image.new("RGB", (24, 16), color=(255, 255, 255)).save(image_buffer, format="PNG")
        captured = {}

        def fake_urlopen(request, timeout=0):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["authorization"] = request.get_header("Authorization")
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
                "OPENAI_BASE_URL": "https://text.example/v2",
                "ANTHROPIC_AUTH_TOKEN": "spark-test-token",
                "VISION_LLM_BASE_URL": "https://bailian.example/compatible-mode/v1",
                "VISION_LLM_API_KEY": "bailian-test-token",
                "VISION_LLM_MODEL": "qwen3-vl-plus",
            }
        ), patch.object(learning_agents.urllib.request, "urlopen", side_effect=fake_urlopen):
            result = learning_agents.request_llm_image_understanding(
                image_buffer.getvalue(),
                filename="stm32.png",
                timeout=30,
            )

        self.assertIn("GPIO", result)
        self.assertEqual(captured["url"], "https://bailian.example/compatible-mode/v1/chat/completions")
        self.assertEqual(captured["authorization"], "Bearer bailian-test-token")
        self.assertEqual(captured["body"]["model"], "qwen3-vl-plus")
        user_content = captured["body"]["messages"][1]["content"]
        self.assertEqual(user_content[0]["type"], "text")
        self.assertEqual(user_content[1]["type"], "image_url")
        self.assertTrue(user_content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,"))

    def test_audio_request_uses_bailian_native_multimodal_route(self) -> None:
        captured = {}

        def fake_urlopen(request, timeout=0):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["authorization"] = request.get_header("Authorization")
            captured["timeout"] = timeout
            return _JsonResponse(
                {
                    "output": {
                        "choices": [
                            {
                                "message": {
                                    "content": [{"text": "转写：GPIO 实验；听不清处已标记。"}]
                                }
                            }
                        ]
                    }
                }
            )

        with setting_overrides(
            {
                "VISION_LLM_API_KEY": "shared-bailian-token",
                "AUDIO_LLM_BASE_URL": "https://bailian.example/api/v1",
                "AUDIO_LLM_API_KEY": "",
                "AUDIO_LLM_MODEL": "qwen3-omni-flash",
            }
        ), patch.object(learning_agents.urllib.request, "urlopen", side_effect=fake_urlopen):
            result = learning_agents.request_llm_audio_understanding(
                b"RIFF-test-audio",
                filename="gpio.wav",
                timeout=30,
            )

        self.assertIn("GPIO", result)
        self.assertEqual(
            captured["url"],
            "https://bailian.example/api/v1/services/aigc/multimodal-generation/generation",
        )
        self.assertEqual(captured["authorization"], "Bearer shared-bailian-token")
        self.assertEqual(captured["body"]["model"], "qwen3-omni-flash")
        content = captured["body"]["input"]["messages"][0]["content"]
        self.assertTrue(content[0]["audio"].startswith("data:audio/wav;base64,"))
        self.assertEqual(captured["body"]["parameters"]["modalities"], ["text"])


if __name__ == "__main__":
    unittest.main()
