"""Learning-interview HTTP routes."""

from __future__ import annotations

import base64
import binascii
import os
import re
from dataclasses import dataclass
from typing import Any, Callable

from flask import Blueprint, current_app, g, jsonify, request

try:
    from common import setting_overrides
    from interview_runtime import (
        end_interview_session,
        get_interview_video_context,
        handle_interview_message,
        public_interview_profiles,
        save_interview_frame_analysis,
        start_interview_session,
    )
    from mimo_interview_client import (
        MimoInterviewConfigError,
        MimoInterviewError,
        analyze_interview_frame,
        generate_interview_followup,
        generate_interview_question,
    )
except ImportError:  # pragma: no cover - package import fallback
    from .common import setting_overrides
    from .interview_runtime import (
        end_interview_session,
        get_interview_video_context,
        handle_interview_message,
        public_interview_profiles,
        save_interview_frame_analysis,
        start_interview_session,
    )
    from .mimo_interview_client import (
        MimoInterviewConfigError,
        MimoInterviewError,
        analyze_interview_frame,
        generate_interview_followup,
        generate_interview_question,
    )


@dataclass(frozen=True)
class InterviewRouteDependencies:
    run_orchestrated: Callable[..., dict]
    runtime_setting_overrides: Callable[[int], dict[str, str]]
    llm_runtime: Callable[[int], dict]
    public_llm_error: Callable[[Exception], str]
    skill_review_error: type[Exception]
    generate_question: Callable[[dict], dict] = generate_interview_question
    generate_followup: Callable[[dict, str], dict] = generate_interview_followup
    analyze_frame: Callable[..., dict] = analyze_interview_frame


_FRAME_ERROR_MESSAGES = {
    "EMPTY_IMAGE": "未收到关键帧图片",
    "INVALID_IMAGE_BASE64": "关键帧图片格式不正确",
    "IMAGE_TOO_LARGE": "关键帧图片过大，请降低截图分辨率",
    "MIMO_CONFIG_MISSING": "AI 多模态配置缺失，请检查嵌小智模型设置或平台模型凭据",
    "MIMO_TIMEOUT": "AI 关键帧分析超时，请稍后重试",
    "MIMO_PARSE_ERROR": "AI 返回内容解析失败",
    "MIMO_AUTH_FAILED": "AI 鉴权失败，请检查后端 Token",
    "MIMO_ERROR": "AI 关键帧分析暂时不可用，请稍后重试",
}


def _response(result: dict):
    code = result.get("code")
    return (jsonify(result), code) if isinstance(code, int) and code >= 400 else jsonify(result)


def _frame_error_message(error_code: str) -> str:
    return _FRAME_ERROR_MESSAGES.get(error_code, _FRAME_ERROR_MESSAGES["MIMO_ERROR"])


def _frame_error_status(error_code: str) -> int:
    if error_code in {"EMPTY_IMAGE", "INVALID_IMAGE_BASE64"}:
        return 400
    if error_code == "IMAGE_TOO_LARGE":
        return 413
    if error_code == "MIMO_TIMEOUT":
        return 504
    return 502


def _frame_error(error_code: str, message: str, status: int):
    current_app.logger.warning("[AnalyzeFrame] failed errorCode=%s message=%s", error_code, message)
    public_error_code = re.sub(r"^MIMO_", "MODEL_", error_code or "MODEL_ERROR")
    return jsonify({"success": False, "errorCode": public_error_code, "error": message}), status


def _session_context(payload: dict, stored: dict | None = None) -> dict:
    stored = stored or {}
    return {
        **stored,
        "sessionId": str(payload.get("sessionId") or stored.get("sessionId") or "").strip(),
        "category": str(payload.get("category") or stored.get("category") or "").strip(),
        "categoryKey": str(payload.get("categoryKey") or payload.get("category_key") or stored.get("categoryKey") or "").strip(),
        "position": str(payload.get("position") or stored.get("position") or "").strip(),
        "positionKey": str(payload.get("positionKey") or payload.get("position_key") or stored.get("positionKey") or "").strip(),
        "direction": str(payload.get("direction") or stored.get("direction") or "").strip(),
        "directionKey": str(payload.get("directionKey") or payload.get("direction_key") or stored.get("directionKey") or "").strip(),
        "topic": str(payload.get("topic") or stored.get("topic") or "").strip(),
        "difficulty": str(payload.get("difficulty") or stored.get("difficulty") or "").strip(),
        "difficultyLabel": str(payload.get("difficultyLabel") or payload.get("difficulty_label") or stored.get("difficultyLabel") or "").strip(),
        "history": payload.get("history") if isinstance(payload.get("history"), list) else [],
    }


def create_interview_blueprint(dependencies: InterviewRouteDependencies) -> Blueprint:
    blueprint = Blueprint("interview", __name__)

    def current_user_id() -> int:
        return int(g.current_user["id"])

    @blueprint.post("/api/interview/session/start")
    def session_start():
        payload = request.get_json(silent=True) or {}
        user_id = current_user_id()
        result = dependencies.run_orchestrated(
            "interview",
            str(payload.get("topic") or payload.get("direction") or "开始数字人 AI 面试"),
            payload,
            user_id,
            lambda managed_payload, _progress: start_interview_session(user_id, managed_payload),
            max_retries=0,
        )
        return _response(result)

    @blueprint.post("/api/interview/session/message")
    def session_message():
        payload = request.get_json(silent=True) or {}
        user_id = current_user_id()
        result = dependencies.run_orchestrated(
            "interview",
            str(payload.get("topic") or payload.get("answer") or "AI 面试追问与评分"),
            payload,
            user_id,
            lambda managed_payload, _progress: handle_interview_message(user_id, managed_payload),
            max_retries=0,
        )
        return _response(result)

    @blueprint.post("/api/interview/session/end")
    def session_end():
        payload = request.get_json(silent=True) or {}
        user_id = current_user_id()
        result = dependencies.run_orchestrated(
            "interview",
            str(payload.get("topic") or "结束 AI 面试并评估学习效果"),
            payload,
            user_id,
            lambda managed_payload, _progress: end_interview_session(user_id, managed_payload),
            max_retries=0,
        )
        return _response(result)

    @blueprint.get("/api/interview/options")
    def options():
        return jsonify({"profiles": public_interview_profiles()})

    @blueprint.post("/api/interview/model-test")
    @blueprint.post("/api/interview/mimo-test")
    def model_test():
        payload = request.get_json(silent=True) or {}
        context = _session_context(
            {
                "category": payload.get("category") or "单片机与 MCU 开发",
                "categoryKey": payload.get("categoryKey") or payload.get("category_key") or "mcu_development",
                "position": payload.get("position") or "STM32 开发工程师",
                "positionKey": payload.get("positionKey") or payload.get("position_key") or "stm32_developer",
                "direction": payload.get("direction") or payload.get("topic") or "GPIO / 中断 / UART",
                "directionKey": payload.get("directionKey") or payload.get("direction_key") or "gpio_interrupt_uart",
                "topic": payload.get("topic") or "GPIO / 中断 / UART",
                "difficulty": payload.get("difficulty") or "medium",
                "difficultyLabel": payload.get("difficultyLabel") or payload.get("difficulty_label") or "",
                "history": payload.get("history") if isinstance(payload.get("history"), list) else [],
            }
        )
        context["round"] = payload.get("round") or 1
        answer = str(payload.get("answer") or "").strip()
        user_id = current_user_id()
        try:
            with setting_overrides(dependencies.runtime_setting_overrides(user_id)):
                result = (
                    dependencies.generate_followup(context, answer)
                    if answer
                    else dependencies.generate_question(context)
                )
            return jsonify(
                {
                    "success": True,
                    "reply": result.get("content", ""),
                    "result": result,
                    "modelRuntime": dependencies.llm_runtime(user_id),
                    "deprecatedRoute": request.path if request.path.endswith("/mimo-test") else "",
                }
            )
        except MimoInterviewConfigError as exc:
            return jsonify({"success": False, "error": dependencies.public_llm_error(exc), "errorCode": "MODEL_CONFIG_MISSING"})
        except MimoInterviewError as exc:
            return jsonify({"success": False, "error": dependencies.public_llm_error(exc), "errorCode": "MODEL_ERROR"}), 502
        except Exception as exc:
            return jsonify({"success": False, "error": f"AI interview call failed: {dependencies.public_llm_error(exc)}", "errorCode": "MODEL_ERROR"}), 500

    @blueprint.post("/api/interview/analyze-frame")
    def analyze_frame():
        payload = request.get_json(silent=True) or {}
        image_base64 = str(payload.get("imageBase64") or "").strip()
        if not image_base64:
            return _frame_error("EMPTY_IMAGE", "未收到关键帧图片", 400)

        encoded_image = image_base64
        data_url_match = re.match(
            r"^data:(image/(?:jpeg|jpg|png));base64,(.*)$",
            image_base64,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if image_base64.lower().startswith("data:") and not data_url_match:
            return _frame_error("INVALID_IMAGE_BASE64", "关键帧图片格式不正确", 400)
        if data_url_match:
            encoded_image = data_url_match.group(2)
        compact_image = re.sub(r"\s+", "", encoded_image)
        max_base64_chars = int(os.getenv("MIMO_INTERVIEW_FRAME_MAX_BASE64_CHARS", "900000") or "900000")
        if len(compact_image) > max_base64_chars:
            return _frame_error("IMAGE_TOO_LARGE", "关键帧图片过大，请降低截图分辨率", 413)
        try:
            decoded_image = base64.b64decode(compact_image, validate=True)
        except (binascii.Error, ValueError):
            return _frame_error("INVALID_IMAGE_BASE64", "关键帧图片格式不正确", 400)
        max_bytes = int(os.getenv("MIMO_INTERVIEW_FRAME_MAX_BYTES", str(2 * 1024 * 1024)) or str(2 * 1024 * 1024))
        if len(decoded_image) > max_bytes:
            return _frame_error("IMAGE_TOO_LARGE", "关键帧图片过大，请降低截图分辨率", 413)

        user_id = current_user_id()
        is_manual_test = str(payload.get("reason") or "").strip() == "manual-test"
        stored_context: dict[str, Any] = {}
        if not is_manual_test:
            ok, early_response, stored_context = get_interview_video_context(user_id, payload)
            if not ok:
                if not early_response.get("success"):
                    current_app.logger.warning(
                        "[AnalyzeFrame] failed errorCode=%s message=%s",
                        early_response.get("errorCode", "MIMO_ERROR"),
                        early_response.get("error", ""),
                    )
                return jsonify(early_response)
        context = _session_context(payload, stored_context)
        media_type = str(payload.get("mediaType") or payload.get("media_type") or "").strip()
        try:
            orchestration_payload = {
                key: value for key, value in payload.items() if key not in {"imageBase64", "image_base64"}
            }
            orchestration_payload["frameBytes"] = len(decoded_image)
            result = dependencies.run_orchestrated(
                "interview",
                str(context.get("topic") or "AI 面试关键帧分析"),
                orchestration_payload,
                user_id,
                lambda _managed_payload, _progress: dependencies.analyze_frame(
                    image_base64,
                    media_type=media_type,
                    session_context=context,
                ),
                max_retries=0,
            )
            try:
                round_no = int(payload.get("round") or context.get("round") or 0)
            except (TypeError, ValueError):
                round_no = 0
            if not is_manual_test:
                result = save_interview_frame_analysis(
                    user_id,
                    context.get("sessionId", ""),
                    result,
                    round_no=round_no,
                )
            return jsonify(result)
        except MimoInterviewConfigError as exc:
            error_code = getattr(exc, "error_code", "MIMO_CONFIG_MISSING")
            return _frame_error(error_code, _frame_error_message(error_code), _frame_error_status(error_code))
        except MimoInterviewError as exc:
            error_code = getattr(exc, "error_code", "MIMO_ERROR")
            return _frame_error(error_code, _frame_error_message(error_code), _frame_error_status(error_code))
        except dependencies.skill_review_error:
            raise
        except Exception as exc:
            current_app.logger.warning("[AnalyzeFrame] unexpected error: %s", exc)
            return _frame_error("MIMO_ERROR", f"关键帧分析异常: {str(exc)}", 500)

    return blueprint
