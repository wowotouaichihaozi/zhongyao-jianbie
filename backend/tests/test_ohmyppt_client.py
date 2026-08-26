from __future__ import annotations

import pytest

from backend import ohmyppt_client


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self._payload


def configured_settings(values: dict[str, str]):
    def get_setting(name: str, default: str = "") -> str:
        return values.get(name, default)

    return get_setting


def valid_slide_html(title: str) -> str:
    return (
        "<!doctype html><html><head><meta charset='utf-8'></head><body>"
        "<div class='slide ppt-page-root' data-ppt-guard-root='1'>"
        f"<h1>{title}</h1><p>{'GPIO 学习内容' * 30}</p>"
        "</div><script>(()=>{})()</script></body></html>"
    )


def test_generate_uses_signed_internal_headers_and_validates_pages(monkeypatch):
    settings = {
        "OHMYPPT_API_URL": "http://127.0.0.1:8765/api",
        "OHMYPPT_INTERNAL_TOKEN": "internal-secret",
        "ANTHROPIC_AUTH_TOKEN": "model-secret",
        "LLM_PROTOCOL": "openai",
        "OPENAI_BASE_URL": "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2",
        "ANTHROPIC_MODEL": "spark-x2-agent",
        "OHMYPPT_REQUEST_TIMEOUT": "90",
    }
    monkeypatch.setattr(ohmyppt_client, "get_setting", configured_settings(settings))
    monkeypatch.setattr(
        ohmyppt_client.requests,
        "get",
        lambda *_args, **_kwargs: FakeResponse(
            {
                "ok": True,
                "version": "0.3.0",
                "model": "astron-code-latest",
                "protocol": "auto",
                "hasToken": True,
            }
        ),
    )
    captured = {}

    def fake_post(url, *, headers, json, timeout, proxies):
        captured.update({"url": url, "headers": headers, "json": json, "timeout": timeout, "proxies": proxies})
        return FakeResponse(
            {
                "sessionId": "ppt-test",
                "title": "GPIO",
                "generationMode": "fallback",
                "generationWarnings": ["第 1 页模型响应异常，已生成保底页"],
                "pages": [
                    {
                        "pageNumber": 1,
                        "title": "GPIO 基础",
                        "contentOutline": "工作模式",
                        "html": valid_slide_html("GPIO 基础"),
                        "generationMode": "fallback",
                        "generationWarning": "第 1 页模型响应异常，已生成保底页",
                    }
                ],
            }
        )

    monkeypatch.setattr(ohmyppt_client.requests, "post", fake_post)
    stages = []
    result = ohmyppt_client.generate_with_ohmyppt(
        {"sessionId": "ppt-test", "topic": "GPIO", "pageCount": 1},
        on_stage=stages.append,
    )

    assert result["engine"]["id"] == "ohmyppt-fastapi"
    assert result["engine"]["model"] == "spark-x2-agent"
    assert len(result["pages"]) == 1
    assert result["generationMode"] == "fallback"
    assert result["generationWarnings"] == ["第 1 页模型响应异常，已生成保底页"]
    assert result["pages"][0]["generationMode"] == "fallback"
    assert result["pages"][0]["generationWarning"] == "第 1 页模型响应异常，已生成保底页"
    assert captured["url"] == "http://127.0.0.1:8765/api/generate"
    assert captured["headers"]["X-OhMyPPT-Protocol"] == "openai"
    assert captured["headers"]["X-OhMyPPT-Model"] == "spark-x2-agent"
    assert captured["proxies"] == {"http": "", "https": ""}
    assert len(captured["headers"]["X-OhMyPPT-Signature"]) == 64
    assert "internal-secret" not in str(captured)
    assert "model-secret" not in str(captured)
    assert "modelConfig" not in captured["json"]
    assert [item["stage"] for item in stages] == [
        "ohmyppt_health",
        "ohmyppt_request",
        "ohmyppt_validate",
        "ohmyppt_complete",
    ]
    assert stages[-1]["fallbackCount"] == 1
    assert "1 页为可编辑保底页" in stages[-1]["message"]


def test_validate_pages_rejects_external_resources():
    with pytest.raises(ohmyppt_client.OhMyPptError, match="外部资源"):
        ohmyppt_client._validate_pages(
            {
                "sessionId": "ppt-test",
                "pages": [
                    {
                        "title": "不安全页面",
                        "html": valid_slide_html("不安全页面") + '<img src="https://untrusted.example/image.png">',
                    }
                ],
            },
            session_id="ppt-test",
            expected_count=1,
        )


def test_validate_pages_rejects_partial_deck():
    with pytest.raises(ohmyppt_client.OhMyPptError, match="页数不完整"):
        ohmyppt_client._validate_pages(
            {"sessionId": "ppt-test", "pages": []},
            session_id="ppt-test",
            expected_count=3,
        )
