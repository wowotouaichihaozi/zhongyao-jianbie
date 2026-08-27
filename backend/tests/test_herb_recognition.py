from __future__ import annotations

import io
import unittest
from unittest.mock import patch

from PIL import Image

try:
    import herb_recognition as herb_recognition_module
    from herb_recognition import _deepseek_chat_completions_url, _extract_standard_herb_name, _herb_ai_settings, decode_class_label, recognize_herb_image_with_deepseek, load_name_mapping
except ImportError:  # pragma: no cover - repository-root test invocation
    from backend import herb_recognition as herb_recognition_module
    from backend.herb_recognition import _deepseek_chat_completions_url, _extract_standard_herb_name, _herb_ai_settings, decode_class_label, recognize_herb_image_with_deepseek, load_name_mapping


class HerbRecognitionTests(unittest.TestCase):
    def test_mapping_contains_the_trained_white_peony_class(self) -> None:
        self.assertEqual(load_name_mapping()["White Peony Root"], "白芍")

    def test_legacy_serialized_class_name_is_decoded(self) -> None:
        self.assertEqual(decode_class_label("{0: 'Poria'}", 0), "Poria")

    def test_ai_calibration_accepts_only_one_mapped_name(self) -> None:
        self.assertEqual(_extract_standard_herb_name("白芍", {"白芍", "茯苓"}), "白芍")
        with self.assertRaisesRegex(ValueError, "未返回可确认"):
            _extract_standard_herb_name("白芍或茯苓", {"白芍", "茯苓"})

    def test_deepseek_base_url_does_not_add_v1(self) -> None:
        self.assertEqual(
            _deepseek_chat_completions_url("https://api.deepseek.com"),
            "https://api.deepseek.com/chat/completions",
        )

    def test_ai_calibration_requires_a_server_side_key(self) -> None:
        settings = {
            "HERB_AI_BASE_URL": "https://api.deepseek.com",
            "HERB_AI_MODEL": "deepseek-v4-flash-vision-exp",
        }
        with patch.object(herb_recognition_module, "get_setting", side_effect=lambda name, default="": settings.get(name, default)):
            with self.assertRaisesRegex(ValueError, "未配置 API Key"):
                _herb_ai_settings()

    def test_ai_calibration_posts_only_to_deepseek_without_yolo(self) -> None:
        raw = io.BytesIO()
        Image.new("RGB", (4, 4), "white").save(raw, format="JPEG")

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict:
                return {"choices": [{"message": {"content": "白芍"}}]}

        with (
            patch.object(herb_recognition_module, "get_setting", side_effect=lambda name, default="": {
                "HERB_AI_BASE_URL": "https://api.deepseek.com",
                "HERB_AI_API_KEY": "test-key",
                "HERB_AI_MODEL": "deepseek-v4-flash-vision-exp",
                "HERB_AI_TIMEOUT": "120",
                "HERB_AI_MAX_TOKENS": "512",
            }.get(name, default)),
            patch.object(herb_recognition_module.requests, "post", return_value=FakeResponse()) as post,
            patch.object(herb_recognition_module, "recognize_herb_image", side_effect=AssertionError("YOLO must not run")),
        ):
            self.assertEqual(recognize_herb_image_with_deepseek("sample.jpg", raw.getvalue()), "白芍")

        self.assertEqual(post.call_args.args[0], "https://api.deepseek.com/chat/completions")
        self.assertEqual(post.call_args.kwargs["json"]["model"], "deepseek-v4-flash-vision-exp")


if __name__ == "__main__":
    unittest.main()
