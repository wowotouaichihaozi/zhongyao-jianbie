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
        self.request = main.GenerateRequest(sessionId="test-session", topic="STM32", pageCount=5)

    async def test_five_slides_are_generated_as_three_plus_two_and_merged_in_order(self) -> None:
        ranges: list[tuple[int, int]] = []
        completion_budgets: list[int] = []

        def fake_call(_url: str, _headers: dict, payload: dict, _timeout: int) -> dict:
            prompt = payload["messages"][0]["content"]
            match = re.search(r"Generate slides (\d+)-(\d+) of", prompt)
            self.assertIsNotNone(match)
            ranges.append(tuple(int(value) for value in match.groups()))
            completion_budgets.append(payload["max_tokens"])
            return _response_for_prompt(payload)

        with (
            patch.object(main, "ANTHROPIC_AUTH_TOKEN", "test-token"),
            patch.object(main, "call_llm_sync", side_effect=fake_call),
            patch.dict(
                os.environ,
                {
                    "OHMYPPT_LLM_BATCH_SIZE": "3",
                    "OHMYPPT_LLM_MAX_PARALLEL": "2",
                    "OHMYPPT_LLM_RETRIES": "1",
                    "OHMYPPT_LLM_MAX_TOKENS": "32768",
                },
            ),
        ):
            pages = await main.call_llm(self.request, self.runtime)

        self.assertEqual(sorted(ranges), [(1, 3), (4, 5)])
        self.assertEqual(completion_budgets, [32768, 32768])
        self.assertEqual([page["title"] for page in pages], [f"Page {index}" for index in range(1, 6)])

    def test_completion_budget_defaults_to_verified_deepseek_limit_and_clamps_overrides(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(main._completion_token_budget(), 32768)
        with patch.dict(os.environ, {"OHMYPPT_LLM_MAX_TOKENS": "131072"}):
            self.assertEqual(main._completion_token_budget(), 131072)
        with patch.dict(os.environ, {"OHMYPPT_LLM_MAX_TOKENS": "262144"}):
            self.assertEqual(main._completion_token_budget(), 131072)
        with patch.dict(os.environ, {"OHMYPPT_LLM_MAX_TOKENS": "invalid"}):
            self.assertEqual(main._completion_token_budget(), 32768)

    async def test_failed_batch_reports_its_page_range(self) -> None:
        def fake_call(_url: str, _headers: dict, payload: dict, _timeout: int) -> dict:
            prompt = payload["messages"][0]["content"]
            if "Generate slides 4-5" in prompt:
                raise TimeoutError("read operation timed out")
            return _response_for_prompt(payload)

        with (
            patch.object(main, "ANTHROPIC_AUTH_TOKEN", "test-token"),
            patch.object(main, "call_llm_sync", side_effect=fake_call),
            patch.dict(
                os.environ,
                {
                    "OHMYPPT_LLM_BATCH_SIZE": "3",
                    "OHMYPPT_LLM_MAX_PARALLEL": "2",
                    "OHMYPPT_LLM_RETRIES": "1",
                },
            ),
        ):
            with self.assertRaises(HTTPException) as context:
                await main.call_llm(self.request, self.runtime)

        self.assertEqual(context.exception.status_code, 502)
        self.assertIn("pages 4-5", str(context.exception.detail))
        self.assertIn("timed out", str(context.exception.detail))


if __name__ == "__main__":
    unittest.main()
