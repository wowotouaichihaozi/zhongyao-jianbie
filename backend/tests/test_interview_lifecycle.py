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
        lambda _context: {"content": "请说明 GPIO 推挽与开漏输出的区别。"},
    )
    monkeypatch.setattr(
        interview_runtime,
        "generate_interview_followup",
        lambda _context, _answer, frame_analysis=None: {
            "content": "请继续说明 EXTI 中断调试步骤。",
            "answerType": "strong_answer",
            "answerScore": 82,
            "coveredSkills": ["GPIO", "EXTI"],
            "shouldEnd": False,
        },
    )
    monkeypatch.setattr(
        interview_runtime,
        "generate_interview_summary",
        lambda _context: {
            "content": "回答包含寄存器配置与中断排查依据。",
            "score": 80,
            "advantages": ["排查步骤清晰"],
            "weaknesses": ["可补充波形验证"],
            "suggestions": ["补充示波器验证过程"],
        },
    )

    started = interview_runtime.start_interview_session(
        901,
        {
            "positionKey": "stm32_developer",
            "direction": "GPIO / 中断 / UART",
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
            "answer": "推挽能主动驱动高低电平，开漏高电平依赖上拉；EXTI 调试会检查映射、边沿、NVIC 和挂起标志。",
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
    assert ended["score"] == ended["textScore"] + 2
    assert ended["totalAnswerCount"] == 1
    assert len(ended["frameAnalyses"]) == 1
    assert ended["videoScoreDelta"] == 2
    interview_runtime._SESSIONS.clear()


def test_interview_followup_deduplicates_repeated_model_question(monkeypatch):
    interview_runtime._SESSIONS.clear()
    opening_question = "请介绍一个你做过的 STM32 项目，并说明你的职责和结果。"
    repeated_followup = "请具体说一个你做过的 STM32 传感器采集实验。"
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
            "coveredSkills": ["project_experience"],
            "shouldEnd": False,
        },
    )

    started = interview_runtime.start_interview_session(
        902,
        {
            "positionKey": "stm32_developer",
            "direction": "GPIO / 中断 / UART",
            "minRounds": 3,
            "maxRounds": 8,
        },
    )
    session_id = started["sessionId"]
    first = interview_runtime.handle_interview_message(
        902,
        {"sessionId": session_id, "answer": "我用 STM32 开发过一个环境监测终端。"},
    )
    second = interview_runtime.handle_interview_message(
        902,
        {"sessionId": session_id, "answer": "我主要负责传感器数据采集。"},
    )

    assert first["content"] == repeated_followup
    assert first["questionDeduplicated"] is False
    assert second["content"] != repeated_followup
    assert second["questionDeduplicated"] is True
    session = interview_runtime._SESSIONS[session_id]
    assert session["questions"] == [opening_question, repeated_followup, second["content"]]
    assert interview_runtime._session_history(session) == [
        {"role": "interviewer", "content": opening_question},
        {"role": "candidate", "content": "我用 STM32 开发过一个环境监测终端。"},
        {"role": "interviewer", "content": repeated_followup},
        {"role": "candidate", "content": "我主要负责传感器数据采集。"},
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

    def fake_spark(messages, **kwargs):
        captured["spark_messages"] = messages
        captured["spark_kwargs"] = kwargs
        return (
            '{"analysis":"画面清晰，主体位置稳定。","suggestions":["保持当前光线"],'
            '"confidence":"medium","presentationScore":78,'
            '"confidenceSignal":"neutral_positive","scoreDelta":1}'
        )

    monkeypatch.setattr(mimo_interview_client, "request_llm_image_understanding", fake_vision)
    monkeypatch.setattr(mimo_interview_client, "call_mimo_anthropic_text", fake_spark)

    result = mimo_interview_client.analyze_interview_frame(
        f"data:image/jpeg;base64,{encoded}",
        session_context={"round": 1},
    )

    assert captured["vision_raw"] == raw
    assert captured["vision_kwargs"]["filename"] == "interview-frame.jpg"
    spark_content = captured["spark_messages"][0]["content"]
    assert "Qwen3-VL-Plus 视觉证据" in spark_content
    assert "画面清晰，光线均匀" in spark_content
    assert "base64" not in spark_content
    assert result["presentationScore"] == 78
    assert result["scoreDelta"] == 1


def test_interview_text_does_not_fall_back_to_legacy_mimo_endpoint(monkeypatch):
    monkeypatch.setattr(mimo_interview_client, "_is_anthropic_configured", lambda: False)

    def unexpected_request(*_args, **_kwargs):
        raise AssertionError("legacy MiMo endpoint must not be called")

    monkeypatch.setattr(mimo_interview_client.requests, "post", unexpected_request)

    try:
        mimo_interview_client.call_mimo_chat([{"role": "user", "content": "测试"}])
    except mimo_interview_client.MimoInterviewConfigError as exc:
        assert "Spark X2 Flash" in str(exc)
    else:
        raise AssertionError("missing Spark configuration must fail explicitly")


def test_interview_logging_tolerates_closed_stdout(monkeypatch):
    def unavailable_stdout(*_args, **_kwargs):
        raise OSError(22, "Invalid argument")

    monkeypatch.setattr("builtins.print", unavailable_stdout)
    interview_runtime._log_runtime_event("stdout_probe", sessionId="session-test")
    mimo_interview_client._log_mimo_event("stdout_probe", model="astron-code-latest")
