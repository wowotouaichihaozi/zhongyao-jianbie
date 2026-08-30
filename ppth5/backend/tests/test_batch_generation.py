from __future__ import annotations

import os
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import main  # noqa: E402


def _response_for_prompt(payload: dict) -> dict:
    prompt = payload["messages"][0]["content"]
    match = re.search(r"Generate slides (\d+)-(\d+) of", prompt)
    if not match:
        raise AssertionError("Batch range was not included in the model prompt")
    start_page, end_page = (int(value) for value in match.groups())
    blocks = []
    for page_number in range(start_page, end_page + 1):
        blocks.append(
            "\n".join(
                [
                    f"SLIDE_TITLE: Page {page_number}",
                    f"SLIDE_OUTLINE: Outline {page_number}",
                    "SLIDE_HTML: "
                    f"<section><h1>Page {page_number}</h1><p>Valid batch generated content.</p></section>",
                ]
            )
        )
    return {"choices": [{"message": {"content": "\n---\n".join(blocks)}}]}


class BatchGenerationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.runtime = {
            "baseUrl": "https://example.test/v2",
            "model": "test-model",
            "protocol": "openai",
        }
        self.request = main.GenerateRequest(sessionId="test-session", topic="中药鉴别", pageCount=6)

    async def test_six_slides_use_one_non_thinking_request_with_full_budget(self) -> None:
        ranges: list[tuple[int, int]] = []
        completion_budgets: list[int] = []
        thinking_modes: list[dict] = []

        def fake_call(_url: str, _headers: dict, payload: dict, _timeout: int) -> dict:
            prompt = payload["messages"][0]["content"]
            match = re.search(r"Generate slides (\d+)-(\d+) of", prompt)
            self.assertIsNotNone(match)
            ranges.append(tuple(int(value) for value in match.groups()))
            completion_budgets.append(payload["max_tokens"])
            thinking_modes.append(payload.get("thinking"))
            return _response_for_prompt(payload)

        with (
            patch.object(main, "ANTHROPIC_AUTH_TOKEN", "test-token"),
            patch.object(main, "call_llm_sync", side_effect=fake_call),
            patch.dict(
                os.environ,
                {
                    "OHMYPPT_LLM_MAX_TOKENS": "32768",
                },
            ),
        ):
            pages = await main.call_llm(self.request, self.runtime)

        self.assertEqual(ranges, [(1, 6)])
        self.assertEqual(completion_budgets, [128000])
        self.assertEqual(thinking_modes, [{"type": "disabled"}])
        self.assertEqual([page["title"] for page in pages], [f"Page {index}" for index in range(1, 7)])

    def test_completion_budget_defaults_to_verified_deepseek_limit_and_clamps_overrides(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(main._completion_token_budget(), 128000)
        with patch.dict(os.environ, {"OHMYPPT_LLM_MAX_TOKENS": "131072"}):
            self.assertEqual(main._completion_token_budget(), 131072)
        with patch.dict(os.environ, {"OHMYPPT_LLM_MAX_TOKENS": "262144"}):
            self.assertEqual(main._completion_token_budget(), 131072)
        with patch.dict(os.environ, {"OHMYPPT_LLM_MAX_TOKENS": "invalid"}):
            self.assertEqual(main._completion_token_budget(), 128000)

    async def test_missing_slides_are_filled_without_additional_model_requests(self) -> None:
        ranges: list[tuple[int, int]] = []

        def fake_call(_url: str, _headers: dict, payload: dict, _timeout: int) -> dict:
            prompt = payload["messages"][0]["content"]
            match = re.search(r"Generate slides (\d+)-(\d+) of", prompt)
            self.assertIsNotNone(match)
            ranges.append(tuple(int(value) for value in match.groups()))
            response = _response_for_prompt(payload)
            content = response["choices"][0]["message"]["content"]
            response["choices"][0]["message"]["content"] = "\n---\n".join(content.split("\n---\n")[:4])
            return response

        with (
            patch.object(main, "ANTHROPIC_AUTH_TOKEN", "test-token"),
            patch.object(main, "call_llm_sync", side_effect=fake_call),
        ):
            pages = await main.call_llm(self.request, self.runtime)

        self.assertEqual(ranges, [(1, 6)])
        self.assertEqual(len(pages), 6)
        self.assertEqual([page.get("generationMode", "model") for page in pages[:4]], ["model"] * 4)
        self.assertEqual([page.get("generationMode") for page in pages[4:]], ["fallback", "fallback"])

    async def test_persistent_empty_responses_create_marked_fallback_pages(self) -> None:
        request_count = 0

        def fake_call(_url: str, _headers: dict, _payload: dict, _timeout: int) -> dict:
            nonlocal request_count
            request_count += 1
            return {"choices": [{"message": {"content": ""}}]}

        with (
            patch.object(main, "ANTHROPIC_AUTH_TOKEN", "test-token"),
            patch.object(main, "call_llm_sync", side_effect=fake_call),
        ):
            pages = await main.call_llm(self.request, self.runtime)

        self.assertEqual(request_count, 1)
        self.assertEqual(len(pages), 6)
        self.assertTrue(all(page.get("generationMode") == "fallback" for page in pages))
        self.assertTrue(all("保底页" in str(page.get("generationWarning")) for page in pages))
        self.assertTrue(all("自动恢复页" in page["h"] for page in pages))


if __name__ == "__main__":
    unittest.main()
