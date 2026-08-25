from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from backend import app as app_module
from backend.database_schema import init_auth_schema


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def llm_client():
    tempdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    original_db_path = app_module.AUTH_DB_PATH
    app_module.AUTH_DB_PATH = Path(tempdir.name) / "llm-gateway.sqlite3"
    app_module.app.config.update(TESTING=True)
    with app_module.auth_db() as conn:
        init_auth_schema(conn)
        now = "2026-07-12T10:00:00+08:00"
        conn.execute(
            """
            INSERT INTO users
                (id, username, display_name, password_hash, role, avatar_url, created_at, updated_at)
            VALUES (301, 'llm-user', 'LLM 用户', ?, 'user', '/userlogo.png', ?, ?)
            """,
            (app_module.password_hash("password-1"), now, now),
        )
        conn.execute(
            """
            INSERT INTO user_agent_runtime_settings
                (user_id, enabled, protocol, base_url, model, created_at, updated_at)
            VALUES (301, 1, 'openai', ?, 'spark-x2-agent', ?, ?)
            """,
            ("https://maas-coding-api.cn-huabei-1.xf-yun.com/v2", now, now),
        )
        with app_module.app.test_request_context(
            "/api/auth/login",
            headers={"User-Agent": "llm-gateway-test"},
        ):
            token = app_module.create_session(conn, 301)

    try:
        yield app_module.app.test_client(), {"Authorization": f"Bearer {token}"}
    finally:
        app_module.AUTH_DB_PATH = original_db_path
        tempdir.cleanup()


def test_llm_gateway_requires_authentication(llm_client):
    client, _headers = llm_client
    assert client.get("/api/llm/runtime").status_code == 401
    assert client.post("/api/llm/messages", json={"messages": []}).status_code == 401
    assert client.post("/api-mimo/anthropic/v1/messages", json={"messages": []}).status_code == 401


def test_public_model_capabilities_exposes_routes_without_connection_details(llm_client):
    client, _headers = llm_client
    response = client.get("/api/model-capabilities")

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["routing"]["image"]["modelId"] == "qwen3-vl-plus"
    assert payload["routing"]["audio"]["modelId"] == "qwen3-omni-flash"
    serialized = json.dumps(payload).lower()
    assert "baseurl" not in serialized
    assert "key" not in serialized
    assert "token" not in serialized


def test_llm_runtime_exposes_current_user_model_without_credentials(llm_client):
    client, headers = llm_client
    response = client.get("/api/llm/runtime", headers=headers)

    assert response.status_code == 200
    runtime = response.get_json()["data"]
    assert runtime["protocol"] == "openai"
    assert runtime["model"] == "spark-x2-agent"
    assert runtime["customized"] is True
    assert runtime["source"] == "user"
    assert runtime["contextWindow"] == 262_144
    assert runtime["routing"]["image"]["modelId"] == "qwen3-vl-plus"
    assert runtime["routing"]["image"]["handoffTo"]["modelId"] == "spark-x2-agent"
    assert "key" not in str(runtime).lower()
    assert "token" not in str(runtime).lower()


def test_llm_gateway_ignores_browser_model_and_returns_validated_json(llm_client):
    client, headers = llm_client
    with patch.object(app_module, "call_llm_json", return_value={"markdown": "# GPIO\n## 输出模式"}) as model_call:
        response = client.post(
            "/api/llm/messages",
            headers={**headers, "api-key": "browser-key-must-be-ignored"},
            json={
                "model": "mimo-v2.5",
                "messages": [{"role": "user", "content": "生成 GPIO 思维导图"}],
                "response_format": {"type": "json_object"},
                "max_completion_tokens": 1200,
            },
        )

    assert response.status_code == 200
    result = response.get_json()
    assert result["model"] == "spark-x2-agent"
    assert result["modelRuntime"]["model"] == "spark-x2-agent"
    assert result["choices"][0]["message"]["content"] == '{"markdown": "# GPIO\\n## 输出模式"}'
    assert "mimo-v2.5" not in str(result)
    model_call.assert_called_once()


def test_legacy_mindmap_route_uses_same_authenticated_gateway(llm_client):
    client, headers = llm_client
    with patch.object(app_module, "request_llm_text", return_value="# GPIO\n## 输入模式"):
        response = client.post(
            "/api-mimo/anthropic/v1/messages",
            headers=headers,
            json={
                "model": "mimo-v2.5",
                "messages": [{"role": "user", "content": "扩展 GPIO"}],
                "max_tokens": 500,
            },
        )

    assert response.status_code == 200
    result = response.get_json()
    assert result["model"] == "spark-x2-agent"
    assert result["content"][0]["text"].startswith("# GPIO")
    assert result["modelRuntime"]["source"] == "user"


def test_llm_gateway_rejects_invalid_message_roles(llm_client):
    client, headers = llm_client
    response = client.post(
        "/api/llm/messages",
        headers=headers,
        json={"messages": [{"role": "root", "content": "invalid"}]},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_REQUEST"


def test_llm_gateway_repairs_json_missing_required_fields(llm_client):
    client, headers = llm_client
    with patch.object(
        app_module,
        "call_llm_json",
        side_effect=[
            {"title": "GPIO"},
            {"title": "GPIO", "markdown": "# GPIO\n## 输出模式"},
        ],
    ) as model_call:
        response = client.post(
            "/api/llm/messages",
            headers=headers,
            json={
                "messages": [{"role": "user", "content": "生成 GPIO 思维导图"}],
                "response_format": {
                    "type": "json_object",
                    "required": ["markdown"],
                },
            },
        )

    assert response.status_code == 200
    content = response.get_json()["choices"][0]["message"]["content"]
    assert '"markdown"' in content
    assert model_call.call_count == 2


def test_llm_gateway_repairs_shallow_mindmap_json(llm_client):
    client, headers = llm_client
    valid_markdown = (
        "# STM32 GPIO\n"
        "## 工作模式\n### 输入浮空与上下拉\n### 推挽与开漏输出\n"
        "## 寄存器配置\n### CRL 与 CRH\n### ODR 与 BSRR\n"
        "## 调试验证\n### 时钟使能\n### 引脚电平与串口日志\n"
        "## 常见错误\n### 端口时钟未开启\n### 引脚复用配置冲突"
    )
    with patch.object(
        app_module,
        "call_llm_json",
        side_effect=[
            {"markdown": "# GPIO\n## 模式"},
            {"markdown": valid_markdown},
        ],
    ) as model_call:
        response = client.post(
            "/api/llm/messages",
            headers=headers,
            json={
                "messages": [{"role": "user", "content": "生成 GPIO 思维导图"}],
                "response_format": {
                    "type": "json_object",
                    "schema": "mindmap_markdown",
                    "required": ["markdown"],
                },
            },
        )

    assert response.status_code == 200
    content = response.get_json()["choices"][0]["message"]["content"]
    assert content.count("## ") >= 3
    assert model_call.call_count == 2


def test_llm_gateway_repairs_invalid_mindmap_edit_commands(llm_client):
    client, headers = llm_client
    with patch.object(
        app_module,
        "call_llm_json",
        side_effect=[
            {
                "message": "已修改节点",
                "commands": [{"action": "update", "data": {"content": "推挽输出"}}],
            },
            {
                "message": "当前导图无需修改。",
                "commands": [],
                "frontendCommand": None,
            },
        ],
    ) as model_call:
        response = client.post(
            "/api/llm/messages",
            headers=headers,
            json={
                "messages": [{"role": "user", "content": "把 GPIO 节点改成推挽输出"}],
                "response_format": {
                    "type": "json_object",
                    "schema": "mindmap_edit_commands",
                    "required": ["message", "commands"],
                },
            },
        )

    assert response.status_code == 200
    content = response.get_json()["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    assert parsed["commands"] == []
    assert parsed["message"] == "当前导图无需修改。"
    assert model_call.call_count == 2


def test_mindmap_chat_frontend_uses_server_gateway_without_browser_key_gate():
    scripts_dir = PROJECT_ROOT / "img" / "mind-map-wizard" / "scripts"
    chat_edits = (scripts_dir / "chat-edits.js").read_text(encoding="utf-8")
    chat_ui = (scripts_dir / "chat-ui.js").read_text(encoding="utf-8")
    generator = (scripts_dir / "new.js").read_text(encoding="utf-8")

    assert "API_KEY_REQUIRED" not in chat_edits
    assert "API_KEY_REQUIRED" not in chat_ui
    assert "getStoredApiKey" not in generator
    assert "openrouter-api-key-encrypted" not in generator
    assert 'schema: "mindmap_edit_commands"' in chat_edits
    assert "window.callLlmChatCompletion" in chat_edits


def test_interview_model_test_uses_current_user_runtime(llm_client):
    client, headers = llm_client

    def fake_question(_context):
        return {
            "content": "请说明 GPIO 推挽输出。",
            "runtimeModel": app_module.get_setting("ANTHROPIC_MODEL"),
        }

    with patch.object(app_module, "generate_interview_question", side_effect=fake_question):
        response = client.post(
            "/api/interview/model-test",
            headers=headers,
            json={"topic": "GPIO"},
        )

    assert response.status_code == 200
    result = response.get_json()
    assert result["success"] is True
    assert result["result"]["runtimeModel"] == "spark-x2-agent"
    assert result["modelRuntime"]["model"] == "spark-x2-agent"
    assert result["deprecatedRoute"] == ""
