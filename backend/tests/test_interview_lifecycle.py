from __future__ import annotations

import base64

from backend import app as app_module
from backend import interview_runtime
from backend import mimo_interview_client


def test_interview_runtime_completes_question_frame_answer_and_summary(monkeypatch):
    interview_runtime._SESSIONS.clear()
    monkeypatch.setattr(
        interview_runtime,
        "generate_interview_question",
        lambda _context: {"content": "请说明望、闻、问、切四诊分别关注哪些信息。"},
    )
    monkeypatch.setattr(
        interview_runtime,
        "generate_interview_followup",
        lambda _context, _answer, frame_analysis=None: {
            "content": "请继续说明从四诊信息推导八纲证候的步骤。",
            "answerType": "strong_answer",
            "answerScore": 82,
            "coveredSkills": ["four_diagnostics", "syndrome_differentiation"],
            "shouldEnd": False,
        },
    )
    monkeypatch.setattr(
        interview_runtime,
        "generate_interview_summary",
        lambda _context: {
            "content": "回答包含四诊信息、八纲辨证与病机推导依据。",
            "score": 80,
            "advantages": ["辨证步骤清晰"],
            "weaknesses": ["可补充鉴别证候"],
            "suggestions": ["补充经典或教材依据"],
        },
    )

    started = interview_runtime.start_interview_session(
        901,
        {
            "positionKey": "stm32_developer",
            "direction": "四诊与八纲辨证",
            "videoAnalysisEnabled": True,
            "minRounds": 2,
            "maxRounds": 3,
        },
    )
    session_id = started["sessionId"]
    frame = interview_runtime.save_interview_frame_analysis(
        901,
        session_id,
        {
            "success": True,
            "analysis": "画面清晰，表达状态稳定。",
            "suggestions": ["保持看向镜头"],
            "presentationScore": 75,
            "confidenceSignal": "positive",
            "scoreDelta": 2,
        },
        round_no=1,
    )
    answered = interview_runtime.handle_interview_message(
        901,
        {
            "sessionId": session_id,
            "answer": "我会先按望闻问切整理四诊信息，再从表里、寒热、虚实判断八纲证候，并结合舌脉推导病机和治法。",
            "frameAnalysis": frame,
        },
    )
    ended = interview_runtime.end_interview_session(901, {"sessionId": session_id})

    assert started["usedAI"] is True
    assert started["source"] == "model"
    assert answered["usedAI"] is True
    assert answered["source"] == "model"
    assert answered["answerScore"] > 0
    assert ended["status"] == "ended"
    assert ended["textScore"] == 10
    assert ended["videoScoreDelta"] == 2
    assert ended["score"] == 10
    assert ended["totalAnswerCount"] == 1
    assert len(ended["frameAnalyses"]) == 1
    assert ended["videoScoreDelta"] == 2
    interview_runtime._SESSIONS.clear()


def test_interview_followup_deduplicates_repeated_model_question(monkeypatch):
    interview_runtime._SESSIONS.clear()
    opening_question = "请介绍一则你学习过的中医医案，并说明四诊信息和辨证结果。"
    repeated_followup = "请具体说说这则医案的舌脉信息和病机判断。"
    monkeypatch.setattr(
        interview_runtime,
        "generate_interview_question",
        lambda _context: {"content": opening_question},
    )
    monkeypatch.setattr(
        interview_runtime,
        "generate_interview_followup",
        lambda _context, _answer, frame_analysis=None: {
            "content": repeated_followup,
            "answerType": "vague_answer",
            "answerScore": 30,
            "coveredSkills": ["case_analysis"],
            "shouldEnd": False,
        },
    )

    started = interview_runtime.start_interview_session(
        902,
        {
            "positionKey": "stm32_developer",
            "direction": "综合医案辨析",
            "minRounds": 3,
            "maxRounds": 8,
        },
    )
    session_id = started["sessionId"]
    first = interview_runtime.handle_interview_message(
        902,
        {"sessionId": session_id, "answer": "我学习过一则脾胃病医案，先整理了患者的主诉和四诊信息。"},
    )
    second = interview_runtime.handle_interview_message(
        902,
        {"sessionId": session_id, "answer": "我主要根据舌脉和寒热虚实分析候选证候。"},
    )

    assert first["content"] == repeated_followup
    assert first["questionDeduplicated"] is False
    assert second["content"] != repeated_followup
    assert second["questionDeduplicated"] is True
    session = interview_runtime._SESSIONS[session_id]
    assert session["questions"] == [opening_question, repeated_followup, second["content"]]
    assert interview_runtime._session_history(session) == [
        {"role": "interviewer", "content": opening_question},
        {"role": "candidate", "content": "我学习过一则脾胃病医案，先整理了患者的主诉和四诊信息。"},
        {"role": "interviewer", "content": repeated_followup},
        {"role": "candidate", "content": "我主要根据舌脉和寒热虚实分析候选证候。"},
    ]
    interview_runtime._SESSIONS.clear()


def test_analyze_frame_rejects_provider_oversized_base64_before_model_call():
    client = app_module.app.test_client()
    encoded = base64.b64encode(b"x" * 700_000).decode("ascii")
    response = client.post(
        "/api/interview/analyze-frame",
        headers={"Authorization": "Bearer codex-preview-token", "Host": "localhost"},
        json={"imageBase64": f"data:image/jpeg;base64,{encoded}", "reason": "manual-test"},
    )

    assert response.status_code == 413
    assert response.get_json()["errorCode"] == "IMAGE_TOO_LARGE"


def test_analyze_frame_routes_image_to_qwen_then_evidence_to_spark(monkeypatch):
    raw = b"small-interview-frame"
    encoded = base64.b64encode(raw).decode("ascii")
    captured = {}

    def fake_vision(image_bytes, **kwargs):
        captured["vision_raw"] = image_bytes
        captured["vision_kwargs"] = kwargs
        return "画面清晰，光线均匀，人物位于画面中央；无法确认持续稳定性。"

    def fake_text_model(messages, **kwargs):
        captured["text_messages"] = messages
        captured["text_kwargs"] = kwargs
        return (
            '{"analysis":"画面清晰，主体位置稳定。","suggestions":["保持当前光线"],'
            '"confidence":"medium","presentationScore":78,'
            '"confidenceSignal":"neutral_positive","scoreDelta":1}'
        )

    monkeypatch.setattr(mimo_interview_client, "request_llm_image_understanding", fake_vision)
    monkeypatch.setattr(mimo_interview_client, "call_mimo_chat", fake_text_model)

    result = mimo_interview_client.analyze_interview_frame(
        f"data:image/jpeg;base64,{encoded}",
        session_context={"round": 1},
    )

    assert captured["vision_raw"] == raw
    assert captured["vision_kwargs"]["filename"] == "interview-frame.jpg"
    text_content = captured["text_messages"][0]["content"]
    assert "视觉模型证据" in text_content
    assert "画面清晰，光线均匀" in text_content
    assert "base64" not in text_content
    assert result["presentationScore"] == 78
    assert result["scoreDelta"] == 1


def test_interview_text_requires_configured_server_endpoint(monkeypatch):
    monkeypatch.setattr(mimo_interview_client, "_get_llm_protocol", lambda: "openai")
    monkeypatch.setattr(mimo_interview_client, "_is_openai_configured", lambda: False)
    monkeypatch.setattr(mimo_interview_client, "_is_anthropic_configured", lambda: False)

    def unexpected_request(*_args, **_kwargs):
        raise AssertionError("legacy MiMo endpoint must not be called")

    monkeypatch.setattr(mimo_interview_client.requests, "post", unexpected_request)

    try:
        mimo_interview_client.call_mimo_chat([{"role": "user", "content": "测试"}])
    except mimo_interview_client.MimoInterviewConfigError as exc:
        assert "openai" in str(exc)
    else:
        raise AssertionError("missing model configuration must fail explicitly")


def test_interview_openai_protocol_uses_deepseek_official_endpoint(monkeypatch):
    captured = {}
    settings = {
        "LLM_PROTOCOL": "openai",
        "OPENAI_BASE_URL": "https://api.deepseek.com",
        "ANTHROPIC_BASE_URL": "https://api.deepseek.com",
        "ANTHROPIC_AUTH_TOKEN": "server-secret",
        "ANTHROPIC_MODEL": "deepseek-v4-flash-vision-exp",
    }

    class FakeResponse:
        ok = True
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"choices": [{"message": {"content": "中医学习问题"}}]}

    def fake_get_setting(name, default=""):
        return settings.get(name, default)

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(mimo_interview_client, "get_setting", fake_get_setting)
    monkeypatch.setattr(mimo_interview_client.requests, "post", fake_post)

    result = mimo_interview_client.call_mimo_chat(
        [{"role": "user", "content": "请问一个中医基础问题"}],
        temperature=0.2,
        max_tokens=320,
    )

    assert result == "中医学习问题"
    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer server-secret"
    assert "anthropic-version" not in captured["headers"]
    assert captured["json"]["model"] == "deepseek-v4-flash-vision-exp"
    assert captured["json"]["max_tokens"] == 128000


def test_interview_logging_tolerates_closed_stdout(monkeypatch):
    def unavailable_stdout(*_args, **_kwargs):
        raise OSError(22, "Invalid argument")

    monkeypatch.setattr("builtins.print", unavailable_stdout)
    interview_runtime._log_runtime_event("stdout_probe", sessionId="session-test")
    mimo_interview_client._log_mimo_event("stdout_probe", model="astron-code-latest")
