from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from backend import learning_agents, ppt_h5, question_generator_runtime


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def configured_get_setting(values: dict[str, str]):
    def get_setting(name: str, default: str = "") -> str:
        return values.get(name, default)

    return get_setting


class FakeUrlResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload, ensure_ascii=False).encode("utf-8")


def test_json_model_calls_have_enough_budget_for_reasoning_models():
    settings = {
        "LLM_PROTOCOL": "openai",
        "OPENAI_BASE_URL": "https://trusted.example/v2",
        "ANTHROPIC_BASE_URL": "https://trusted.example/anthropic",
        "ANTHROPIC_AUTH_TOKEN": "server-secret",
        "ANTHROPIC_MODEL": "spark-x2-agent",
    }
    model_response = {
        "choices": [{"message": {"content": '{"ok":true}'}, "finish_reason": "stop"}]
    }
    with (
        patch.object(learning_agents, "get_setting", side_effect=configured_get_setting(settings)),
        patch.object(
            learning_agents.urllib.request,
            "urlopen",
            return_value=FakeUrlResponse(model_response),
        ) as request_call,
    ):
        result = learning_agents.request_llm_text(
            "只输出 JSON",
            '返回 {"ok":true}',
            max_tokens=120,
            json_mode=True,
        )

    request_body = json.loads(request_call.call_args.args[0].data.decode("utf-8"))
    assert result == '{"ok":true}'
    assert request_body["max_tokens"] == 128000


def test_question_generator_ignores_request_model_url_and_credentials():
    browser_payload = {
        "api_key": "browser-secret",
        "model": "mimo-v2.5",
        "api_url": "https://untrusted.example/chat/completions",
        "token_plan_api_url": "https://untrusted.example/token-plan",
    }
    settings = {
        "ANTHROPIC_AUTH_TOKEN": "server-secret",
        "ANTHROPIC_MODEL": "spark-x2-agent",
        "ANTHROPIC_BASE_URL": "https://trusted.example/anthropic",
        "OPENAI_BASE_URL": "https://trusted.example/v2",
    }
    with patch.object(
        question_generator_runtime,
        "get_setting",
        side_effect=configured_get_setting(settings),
    ):
        assert question_generator_runtime.get_mimo_api_key(browser_payload) == "server-secret"
        assert question_generator_runtime.get_mimo_model(browser_payload) == "spark-x2-agent"
        assert question_generator_runtime.resolve_mimo_api_url("server-secret", browser_payload) == (
            "https://trusted.example/v2/chat/completions"
        )


def test_ppt_generator_ignores_request_model_url_and_credentials():
    model_response = {
        "choices": [
            {
                "message": {
                    "content": (
                        "SLIDE_TITLE: GPIO 基础\n"
                        "SLIDE_OUTLINE: GPIO 工作模式\n"
                        "SLIDE_HTML: <section><h1>GPIO 基础</h1></section>"
                    )
                }
            }
        ]
    }
    request_data = {
        "topic": "GPIO",
        "userMessage": "",
        "pageCount": 1,
        "knowledgeContext": "[KB1] GPIO 课程资料",
        "modelConfig": {
            "protocol": "anthropic",
            "baseUrl": "https://untrusted.example/anthropic",
            "apiKey": "browser-secret",
            "model": "mimo-v2.5",
            "maxTokens": 32000,
        },
    }
    settings = {
        "LLM_PROTOCOL": "openai",
        "OPENAI_BASE_URL": "https://trusted.example/v2",
        "ANTHROPIC_AUTH_TOKEN": "server-secret",
        "ANTHROPIC_MODEL": "spark-x2-agent",
        "PPT_H5_LLM_RETRIES": "1",
        "PPT_H5_MAX_TOKENS": "4096",
    }
    with (
        patch.object(ppt_h5, "get_setting", side_effect=configured_get_setting(settings)),
        patch.object(ppt_h5, "call_llm_sync", return_value=model_response) as model_call,
    ):
        pages = ppt_h5.call_llm(request_data)

    assert len(pages) == 1
    request_url, headers, body, _timeout = model_call.call_args.args
    assert request_url == "https://trusted.example/v2/chat/completions"
    assert headers["Authorization"] == "Bearer server-secret"
    assert body["model"] == "spark-x2-agent"
    assert body["max_tokens"] != 32000
    assert "untrusted.example" not in str(model_call.call_args)
    assert "browser-secret" not in str(model_call.call_args)
    assert "mimo-v2.5" not in str(model_call.call_args)


def test_optional_ppth5_backend_does_not_accept_browser_model_credentials():
    source = (PROJECT_ROOT / "ppth5" / "backend" / "main.py").read_text(encoding="utf-8")

    assert "req.modelConfig" not in source
    assert "apiKey: str" not in source
    assert "baseUrl: str" not in source
