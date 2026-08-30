import base64
import binascii
import json
import logging
import os
import re
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

try:
    from api_config import setting_default
except ImportError:  # pragma: no cover - package-style import fallback
    try:
        from .api_config import setting_default
    except ImportError:  # pragma: no cover
        def setting_default(name: str, fallback: str = "") -> str:
            return fallback

try:
    from common import get_setting
except ImportError:  # pragma: no cover
    try:
        from .common import get_setting
    except ImportError:  # pragma: no cover
        def get_setting(name: str, default: str = "") -> str:
            return (os.getenv(name) or default).strip()

try:
    from learning_agents import completion_token_budget, request_llm_image_understanding
except ImportError:  # pragma: no cover - package-style import fallback
    from .learning_agents import completion_token_budget, request_llm_image_understanding

try:
    from interview_profiles import DEFAULT_POSITION_KEY, DEFAULT_WEAK_SIGNALS, get_interview_profile, profile_to_prompt
except Exception:  # pragma: no cover - package-style import fallback
    try:
        from .interview_profiles import DEFAULT_POSITION_KEY, DEFAULT_WEAK_SIGNALS, get_interview_profile, profile_to_prompt
    except Exception:  # pragma: no cover
        DEFAULT_POSITION_KEY = "stm32_developer"
        DEFAULT_WEAK_SIGNALS = {
            "dont_know": ["不知道", "不会", "不懂"],
            "no_experience": ["没做过", "没有经验"],
            "vague_answer": ["大概", "差不多"],
            "irrelevant_answer": ["打游戏", "我不是这个方向"],
            "negative_answer": ["我啥也不会"],
            "refuse_answer": ["不想回答"],
            "end_request": ["什么时候结束"],
            "nonsense_answer": ["123", "abc", "嗯"],
        }

        def get_interview_profile(position_key: str | None = None, position_label: str | None = None) -> Dict[str, Any]:
            return {
                "positionKey": DEFAULT_POSITION_KEY,
                "label": position_label or "中医基础理论学习者",
                "coreSkills": ["theory_framework", "four_diagnostics", "syndrome_differentiation", "materia_medica", "formula_reasoning", "case_analysis", "safety_evidence"],
                "basicQuestions": ["没关系，我们从基础开始。你能简单说明阴阳学说的基本含义吗？"],
                "strongAnswerSignals": ["四诊", "辨证", "病机", "治法", "方剂", "医案"],
                "weakAnswerSignals": ["不知道", "不会"],
                "projectQuestionTemplate": "请介绍一则你学习过的中医医案，重点说明四诊信息、辨证依据、病机和治法思路。",
                "scoringHints": "重点看中医基础、辨证思路、知识依据和安全边界。",
            }

        def profile_to_prompt(profile: Dict[str, Any]) -> str:
            return f"学习方向：{profile.get('label', '')}"

try:
    from question_generator_runtime import (
        DEFAULT_API_URL,
        DEFAULT_MODEL,
        TOKEN_PLAN_API_URL,
        get_mimo_api_key,
        get_mimo_model,
        parse_json_text,
        resolve_mimo_api_url,
    )
except Exception:  # pragma: no cover - package-style import fallback
    try:
        from .question_generator_runtime import (
            DEFAULT_API_URL,
            DEFAULT_MODEL,
            TOKEN_PLAN_API_URL,
            get_mimo_api_key,
            get_mimo_model,
            parse_json_text,
            resolve_mimo_api_url,
        )
    except Exception:  # pragma: no cover - lightweight fallback when LangGraph deps are absent
        DEFAULT_MODEL = "astron-code-latest"
        DEFAULT_API_URL = "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2/chat/completions"
        TOKEN_PLAN_API_URL = DEFAULT_API_URL

        def _load_mimo_config() -> Dict[str, Any]:
            paths = [
                Path(__file__).resolve().with_name("mimo_config.json"),
                Path.cwd() / "mimo_config.json",
            ]
            paths.extend(parent / "mimo_config.json" for parent in Path(__file__).resolve().parents)
            for path in paths:
                if path.exists():
                    try:
                        return json.loads(path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        return {}
            return {}

        def _get_config_value(
            payload: Dict[str, Any],
            env_names: List[str],
            config_names: List[str],
            default: str = "",
        ) -> str:
            for key in config_names:
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            for name in env_names:
                value = os.getenv(name)
                if value:
                    return value.strip()
            config = _load_mimo_config()
            for key in config_names:
                value = config.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            return default

        def get_mimo_api_key(payload: Dict[str, Any]) -> str:
            return _get_config_value(payload, ["MIMO_API_KEY", "XIAOMI_API_KEY"], ["api_key"])

        def get_mimo_model(payload: Dict[str, Any]) -> str:
            return _get_config_value(payload, ["MIMO_MODEL", "XIAOMI_MODEL"], ["model"], DEFAULT_MODEL)

        def _get_mimo_api_url(payload: Dict[str, Any]) -> str:
            return _get_config_value(payload, ["MIMO_API_URL", "XIAOMI_API_URL"], ["api_url"], DEFAULT_API_URL)

        def _get_mimo_token_plan_api_url(payload: Dict[str, Any]) -> str:
            return _get_config_value(
                payload,
                ["MIMO_TOKEN_PLAN_API_URL", "XIAOMI_TOKEN_PLAN_API_URL"],
                ["token_plan_api_url"],
                TOKEN_PLAN_API_URL,
            )

        def resolve_mimo_api_url(api_key: str, payload: Dict[str, Any]) -> str:
            if payload.get("api_url"):
                return str(payload["api_url"])
            if api_key.startswith("tp-"):
                return _get_mimo_token_plan_api_url(payload)
            return _get_mimo_api_url(payload)

        def parse_json_text(text: str) -> Dict[str, Any]:
            cleaned = text.strip()
            if cleaned.startswith("```"):
                lines = cleaned.splitlines()
                if len(lines) >= 3:
                    cleaned = "\n".join(lines[1:-1]).strip()
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                start = cleaned.find("{")
                end = cleaned.rfind("}")
                if start >= 0 and end > start:
                    candidate = cleaned[start : end + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        repaired = re.sub(r",(\s*[}\]])", r"\1", candidate)
                        return json.loads(repaired)
                raise


load_dotenv(Path(__file__).resolve().parent / ".env")
logger = logging.getLogger(__name__)
DIFFICULTY_LABELS = {
    "intern": "启蒙",
    "campus": "入门",
    "basic": "基础",
    "medium": "进阶",
    "advanced": "综合",
    "junior": "基础",
    "senior": "进阶",
}


class MimoInterviewConfigError(RuntimeError):
    def __init__(self, message: str, error_code: str = "MIMO_CONFIG_MISSING"):
        super().__init__(message)
        self.error_code = error_code


class MimoInterviewError(RuntimeError):
    def __init__(self, message: str, error_code: str = "MIMO_ERROR"):
        super().__init__(message)
        self.error_code = error_code


def _clean_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _difficulty_label(value: Any, explicit_label: Any = None) -> str:
    label = _clean_text(explicit_label)
    if label:
        return label
    text = _clean_text(value, "medium")
    return DIFFICULTY_LABELS.get(text, text)


def _normalize_mimo_base_url(value: str) -> str:
    base_url = value.strip().rstrip("/")
    if not base_url:
        return ""
    if base_url.endswith("/chat/completions"):
        return base_url
    if base_url.lower() == "https://api.deepseek.com":
        return f"{base_url}/chat/completions"
    if base_url.endswith("/v1"):
        return f"{base_url}/chat/completions"
    return f"{base_url}/v1/chat/completions"


def _get_openai_base_url() -> str:
    return (
        get_setting("OPENAI_BASE_URL", setting_default("OPENAI_BASE_URL"))
        or get_setting("ANTHROPIC_BASE_URL", setting_default("ANTHROPIC_BASE_URL"))
    ).strip()


def _get_anthropic_base_url() -> str:
    return get_setting("ANTHROPIC_BASE_URL", setting_default("ANTHROPIC_BASE_URL")).strip()


def _get_anthropic_auth_token() -> str:
    return get_setting("ANTHROPIC_AUTH_TOKEN", setting_default("ANTHROPIC_AUTH_TOKEN")).strip()


def _get_anthropic_model() -> str:
    return (
        get_setting("ANTHROPIC_MODEL", "")
        or get_setting("MIMO_MODEL", "")
        or setting_default("ANTHROPIC_MODEL", DEFAULT_MODEL)
    ).strip()


def _is_anthropic_configured() -> bool:
    return bool(_get_anthropic_base_url() and _get_anthropic_auth_token())


def _is_openai_configured() -> bool:
    return bool(_get_openai_base_url() and _get_anthropic_auth_token())


def _get_llm_protocol() -> str:
    protocol = get_setting("LLM_PROTOCOL", "auto").strip().lower()
    return protocol if protocol in {"auto", "openai", "anthropic"} else "auto"


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)) or str(default))
    except (TypeError, ValueError):
        return default


def _anthropic_timeout() -> int:
    return _int_env("ANTHROPIC_INTERVIEW_TIMEOUT", _int_env("MIMO_INTERVIEW_TIMEOUT", 60))


def _mimo_timeout() -> int:
    return _int_env("MIMO_INTERVIEW_TIMEOUT", 60)


def _mimo_provider_name() -> str:
    protocol = _get_llm_protocol()
    if protocol == "openai" or (protocol == "auto" and _is_openai_configured()):
        return "openai"
    return "anthropic" if _is_anthropic_configured() else "unconfigured"


def _safe_console_print(message: str) -> None:
    try:
        print(message, flush=True)
    except (OSError, ValueError):
        logger.debug("interview model console output is unavailable", exc_info=True)


def _log_mimo_event(event: str, **kwargs: Any) -> None:
    safe_fields = {
        key: value
        for key, value in kwargs.items()
        if key not in {"api_key", "token", "auth_token", "apiSecret", "api_secret"}
    }
    logger.info("[MiMo Interview] %s %s", event, safe_fields)
    _safe_console_print(f"[MiMo Interview] {event} {safe_fields}")


def build_anthropic_messages_url(base_url: str) -> str:
    cleaned = base_url.strip().rstrip("/")
    if not cleaned:
        return ""
    lowered = cleaned.lower()
    if lowered.endswith("/v1/messages"):
        return cleaned
    if lowered.endswith("/v1"):
        return f"{cleaned}/messages"
    return f"{cleaned}/v1/messages"


def _normalize_anthropic_messages_url(base_url: str) -> str:
    return build_anthropic_messages_url(base_url)


def _anthropic_headers(use_x_api_key: bool = False) -> Dict[str, str]:
    token = _get_anthropic_auth_token()
    headers = {
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
        "api-key": token,
        "x-api-key": token,
        "Authorization": f"Bearer {token}",
    }
    return headers


def _openai_headers() -> Dict[str, str]:
    token = _get_anthropic_auth_token()
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }


def _build_config_payload() -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    configured_api_url = os.getenv("MIMO_API_URL") or os.getenv("XIAOMI_API_URL")
    configured_base_url = os.getenv("MIMO_BASE_URL")
    if not configured_api_url and configured_base_url:
        payload["api_url"] = _normalize_mimo_base_url(configured_base_url)
    return payload


def _safe_error_text(text: str) -> str:
    cleaned = str(text or "")
    for value in [
        os.getenv("MIMO_API_KEY", ""),
        os.getenv("XIAOMI_API_KEY", ""),
        os.getenv("ANTHROPIC_AUTH_TOKEN", ""),
        _get_anthropic_auth_token(),
    ]:
        if value:
            cleaned = cleaned.replace(value, "***")
    return cleaned[:1200]


def _extract_chat_content(data: Dict[str, Any]) -> str:
    choices = data.get("choices") or []
    if not choices:
        return ""
    choice = choices[0] or {}
    message = choice.get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    delta = choice.get("delta") or {}
    delta_content = delta.get("content")
    if isinstance(delta_content, str):
        return delta_content.strip()
    return ""


def _extract_anthropic_text(data: Dict[str, Any]) -> str:
    content = data.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: List[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block.strip())
            elif isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str):
                    parts.append(text.strip())
        return "\n".join(part for part in parts if part)
    message = data.get("message")
    if isinstance(message, dict):
        return _extract_anthropic_text(message)
    return ""


def _post_anthropic_messages(body: Dict[str, Any], use_x_api_key: bool = False) -> requests.Response:
    base_url = _get_anthropic_base_url()
    token = _get_anthropic_auth_token()
    if not base_url or not token:
        raise MimoInterviewConfigError(
            "ANTHROPIC_BASE_URL and ANTHROPIC_AUTH_TOKEN are not configured",
            "MIMO_CONFIG_MISSING",
        )

    try:
        return requests.post(
            build_anthropic_messages_url(base_url),
            headers=_anthropic_headers(use_x_api_key=use_x_api_key),
            json=body,
            timeout=_anthropic_timeout(),
        )
    except requests.Timeout as exc:
        raise MimoInterviewError("MiMo request timeout, please retry later", "MIMO_TIMEOUT") from exc
    except requests.RequestException as exc:
        raise MimoInterviewError(
            f"MiMo Anthropic request failed: {_safe_error_text(str(exc))}",
            "MIMO_ERROR",
        ) from exc


def _post_openai_chat_completions(body: Dict[str, Any]) -> requests.Response:
    base_url = _get_openai_base_url()
    token = _get_anthropic_auth_token()
    if not base_url or not token:
        raise MimoInterviewConfigError(
            "OPENAI_BASE_URL and ANTHROPIC_AUTH_TOKEN are not configured",
            "MIMO_CONFIG_MISSING",
        )

    try:
        return requests.post(
            _normalize_mimo_base_url(base_url),
            headers=_openai_headers(),
            json=body,
            timeout=_mimo_timeout(),
        )
    except requests.Timeout as exc:
        raise MimoInterviewError("Model request timeout, please retry later", "MIMO_TIMEOUT") from exc
    except requests.RequestException as exc:
        raise MimoInterviewError(
            f"OpenAI-compatible request failed: {_safe_error_text(str(exc))}",
            "MIMO_ERROR",
        ) from exc


def call_mimo_openai_text(
    messages: List[Dict[str, Any]],
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> str:
    started_at = time.perf_counter()
    max_tokens = completion_token_budget(max_tokens)
    body = {
        "model": _get_anthropic_model(),
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
    }
    _log_mimo_event(
        "request_start",
        provider="openai",
        model=body["model"],
        max_tokens=max_tokens,
        temperature=temperature,
    )

    try:
        response = _post_openai_chat_completions(body)
    except Exception as exc:
        _log_mimo_event(
            "request_failed",
            provider="openai",
            model=body["model"],
            duration_ms=round((time.perf_counter() - started_at) * 1000, 1),
            error=_safe_error_text(str(exc)),
        )
        raise

    if not response.ok:
        _log_mimo_event(
            "request_failed",
            provider="openai",
            model=body["model"],
            status_code=response.status_code,
            duration_ms=round((time.perf_counter() - started_at) * 1000, 1),
        )
        error_code = "MIMO_AUTH_FAILED" if response.status_code in {401, 403} else "MIMO_ERROR"
        raise MimoInterviewError(
            f"OpenAI-compatible API call failed: HTTP {response.status_code}; {_safe_error_text(response.text)}",
            error_code,
        )

    try:
        data = response.json()
    except (json.JSONDecodeError, ValueError) as exc:
        raise MimoInterviewError(
            f"OpenAI-compatible response is not valid JSON: {_safe_error_text(response.text)}",
            "MIMO_PARSE_ERROR",
        ) from exc

    content = _extract_chat_content(data)
    if not content:
        _log_mimo_event(
            "request_failed",
            provider="openai",
            model=body["model"],
            duration_ms=round((time.perf_counter() - started_at) * 1000, 1),
            error="empty assistant content",
        )
        raise MimoInterviewError(
            "OpenAI-compatible response did not contain assistant content",
            "MIMO_PARSE_ERROR",
        )
    _log_mimo_event(
        "request_success",
        provider="openai",
        model=body["model"],
        duration_ms=round((time.perf_counter() - started_at) * 1000, 1),
    )
    return content


def call_mimo_anthropic_text(
    messages: List[Dict[str, Any]],
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> str:
    started_at = time.perf_counter()
    max_tokens = completion_token_budget(max_tokens)
    body = {
        "model": _get_anthropic_model(),
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
    }
    _log_mimo_event(
        "request_start",
        provider="anthropic",
        model=body["model"],
        max_tokens=max_tokens,
        temperature=temperature,
    )

    try:
        response = _post_anthropic_messages(body, use_x_api_key=False)
        if response.status_code in {401, 403}:
            response = _post_anthropic_messages(body, use_x_api_key=True)
    except Exception as exc:
        _log_mimo_event(
            "request_failed",
            provider="anthropic",
            model=body["model"],
            duration_ms=round((time.perf_counter() - started_at) * 1000, 1),
            error=_safe_error_text(str(exc)),
        )
        raise

    if not response.ok:
        _log_mimo_event(
            "request_failed",
            provider="anthropic",
            model=body["model"],
            status_code=response.status_code,
            duration_ms=round((time.perf_counter() - started_at) * 1000, 1),
        )
        error_code = "MIMO_AUTH_FAILED" if response.status_code in {401, 403} else "MIMO_ERROR"
        raise MimoInterviewError(
            f"MiMo Anthropic API call failed: HTTP {response.status_code}; {_safe_error_text(response.text)}",
            error_code,
        )

    try:
        data = response.json()
    except (json.JSONDecodeError, ValueError) as exc:
        raise MimoInterviewError(
            f"MiMo Anthropic response is not valid JSON: {_safe_error_text(response.text)}",
            "MIMO_PARSE_ERROR",
        ) from exc

    content = _extract_anthropic_text(data)
    if not content:
        _log_mimo_event(
            "request_failed",
            provider="anthropic",
            model=body["model"],
            duration_ms=round((time.perf_counter() - started_at) * 1000, 1),
            error="empty assistant content",
        )
        raise MimoInterviewError("MiMo Anthropic response did not contain assistant content", "MIMO_PARSE_ERROR")
    _log_mimo_event(
        "request_success",
        provider="anthropic",
        model=body["model"],
        duration_ms=round((time.perf_counter() - started_at) * 1000, 1),
    )
    return content


def call_mimo_chat(
    messages: List[Dict[str, Any]],
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> str:
    completion_tokens = completion_token_budget(
        max_tokens or int(os.getenv("MIMO_INTERVIEW_MAX_TOKENS", "128000") or "128000")
    )
    protocol = _get_llm_protocol()
    if protocol in {"openai", "auto"} and _is_openai_configured():
        return call_mimo_openai_text(
            messages,
            temperature=temperature,
            max_tokens=completion_tokens,
        )
    if protocol in {"anthropic", "auto"} and _is_anthropic_configured():
        return call_mimo_anthropic_text(
            messages,
            temperature=temperature,
            max_tokens=completion_tokens,
        )
    raise MimoInterviewConfigError(
        f"Configured {protocol} model endpoint and server credential are required",
        "MIMO_CONFIG_MISSING",
    )


def _history_lines(session_context: Dict[str, Any]) -> str:
    history = session_context.get("history") or session_context.get("messages") or session_context.get("answers") or []
    lines: List[str] = []
    for item in history[-8:]:
        if isinstance(item, dict):
            role = _clean_text(item.get("role"), "user")
            content = _clean_text(item.get("content") or item.get("answer") or item.get("question"))
            if content:
                lines.append(f"{role}: {content}")
        elif isinstance(item, str) and item.strip():
            lines.append(item.strip())
    return "\n".join(lines) or "暂无历史记录。"


def _profile_from_context(session_context: Dict[str, Any]) -> Dict[str, Any]:
    profile = session_context.get("profile")
    if isinstance(profile, dict) and profile.get("coreSkills"):
        data = dict(profile)
        data.setdefault("positionKey", session_context.get("positionKey") or session_context.get("position_key") or DEFAULT_POSITION_KEY)
        return data
    return get_interview_profile(
        session_context.get("positionKey") or session_context.get("position_key"),
        session_context.get("position"),
    )


def _profile_basic_question(profile: Dict[str, Any], index: int, fallback: str) -> str:
    questions = profile.get("basicQuestions") or []
    if questions:
        return _clean_text(questions[min(max(index, 0), len(questions) - 1)], fallback)
    return fallback


def _profile_followup(profile: Dict[str, Any], answer_type: str, fallback: str) -> str:
    followups = profile.get("followupTemplates") or {}
    followup_key = {
        "strong_answer": "strong",
        "normal_answer": "normal",
        "weak_answer": "weak",
        "vague_answer": "vague",
    }.get(answer_type)
    if followup_key:
        return _clean_text(followups.get(followup_key), fallback)
    return fallback


def _context_summary(session_context: Dict[str, Any]) -> str:
    profile = _profile_from_context(session_context)
    category = _clean_text(session_context.get("category"))
    position = _clean_text(session_context.get("position"), profile.get("label", "中医基础理论学习者"))
    direction = _clean_text(session_context.get("direction") or session_context.get("topic"), "中医基础理论、四诊、辨证、方药与医案")
    difficulty = _clean_text(session_context.get("difficulty"), "medium")
    difficulty_display = _difficulty_label(difficulty, session_context.get("difficultyLabel") or session_context.get("difficulty_label"))
    round_no = session_context.get("round") or session_context.get("current_round") or 1
    profile_prompt = profile_to_prompt(profile)
    stats = session_context.get("sessionStats") or session_context.get("session_stats") or {}
    if isinstance(stats, dict):
        stats_text = (
            f"低分连续次数：{stats.get('consecutiveLowScoreCount', 0)}；"
            f"累计低分次数：{stats.get('totalLowScoreCount', 0)}；"
            f"不知道/不会次数：{stats.get('dontKnowCount', 0)}；"
            f"跑题次数：{stats.get('irrelevantCount', 0)}；"
            f"拒答次数：{stats.get('refuseCount', 0)}；"
            f"要求结束次数：{stats.get('endRequestCount', 0)}；"
            f"无意义/过短次数：{stats.get('nonsenseCount', 0)}；"
            f"已覆盖能力点：{'、'.join(stats.get('coveredSkills') or [])}"
        )
    else:
        stats_text = "暂无状态机统计。"
    frame_text = "暂无关键帧辅助分析。"
    frame_analysis = (
        session_context.get("frameAnalysis")
        or session_context.get("frame_analysis")
        or session_context.get("lastFrameAnalysis")
        or session_context.get("last_frame_analysis")
    )
    frame_analyses = session_context.get("frameAnalyses") or session_context.get("frame_analyses") or []
    if not isinstance(frame_analysis, dict) and isinstance(frame_analyses, list) and frame_analyses:
        latest = frame_analyses[-1]
        if isinstance(latest, dict):
            frame_analysis = latest
    if isinstance(frame_analysis, dict):
        analysis = _clean_text(frame_analysis.get("analysis") or frame_analysis.get("content"))
        suggestions = _normalize_list(frame_analysis.get("suggestions"), [])
        confidence = _clean_text(frame_analysis.get("confidence"), "medium")
        if analysis or suggestions:
            frame_text = f"{analysis or '无文字观察'}；建议：{'；'.join(suggestions) or '无'}；置信度：{confidence}"
    return (
        f"课程领域：{category or '未指定'}\n"
        f"学习方向：{position}\n"
        f"访谈主题：{direction}\n"
        f"难度：{difficulty_display}（{difficulty}）\n"
        f"当前轮次：{round_no}\n"
        f"{profile_prompt}\n"
        f"状态机统计：{stats_text}\n"
        f"关键帧辅助分析：{frame_text}\n"
        f"历史记录：\n{_history_lines(session_context)}"
    )


def _json_instruction(schema: str) -> str:
    return (
        "你是严谨的中医学习访谈讲师。只输出 JSON，不要输出 Markdown，不要解释 JSON 之外的内容。\n"
        f"JSON 结构：{schema}"
    )


def _parse_model_json(text: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
    try:
        data = parse_json_text(text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    fallback = dict(fallback)
    fallback["raw"] = text[:1200]
    return fallback


def _normalize_list(value: Any, fallback: List[str]) -> List[str]:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return items or fallback
    if isinstance(value, str) and value.strip():
        parts = [part.strip() for part in re.split(r"[;；\n]", value) if part.strip()]
        return parts or [value.strip()]
    return fallback


def _extract_score(value: Any, fallback: Optional[int] = None) -> Optional[int]:
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        text = _clean_text(value)
        match = (
            re.search(r"(\d{1,3})\s*/\s*100", text)
            or re.search(r"(?:综合)?评分[：:\s]*(\d{1,3})\s*分?", text)
            or re.search(r"得分[：:\s]*(\d{1,3})\s*分?", text)
        )
        if match:
            try:
                return max(0, min(100, int(match.group(1))))
            except (TypeError, ValueError):
                pass
    return fallback


def _strip_summary_score_lines(text: str) -> str:
    lines = str(text or "").splitlines()
    cleaned: List[str] = []
    score_line_pattern = re.compile(r"(?:综合)?评分|得分|\d{1,3}\s*/\s*100")
    for line in lines:
        if score_line_pattern.search(line):
            continue
        cleaned.append(line)
    result = "\n".join(cleaned).strip()
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result


def _looks_like_internal_json_text(text: str) -> bool:
    return bool(re.search(r"\b(answerType|answer_type|score|source|usedMimo|fallbackReason|message)\b\s*[:：]", text or ""))


def _extract_text_field_from_raw(text: str, fallback: str) -> str:
    raw = _clean_text(text)
    if not raw:
        return fallback
    for key in ["content", "message", "reply", "question", "summary"]:
        match = re.search(rf'"{key}"\s*:\s*"((?:\\.|[^"\\])*)"', raw, flags=re.DOTALL)
        if match:
            try:
                return json.loads(f'"{match.group(1)}"').strip()
            except Exception:
                return match.group(1).strip()
        line_match = re.search(rf"(?im)^\s*{key}\s*[:：]\s*(.+?)\s*$", raw)
        if line_match:
            return line_match.group(1).strip().strip('"').strip("'")
    if _looks_like_internal_json_text(raw):
        return fallback
    return raw


def _answer_types_from_context(session_context: Dict[str, Any]) -> List[str]:
    profile = _profile_from_context(session_context)
    history = session_context.get("history") or session_context.get("messages") or []
    answers = session_context.get("answers") or []
    values: List[str] = []
    for item in history:
        if isinstance(item, dict) and str(item.get("role", "")).lower() in {"candidate", "user"}:
            values.append(classify_answer_type(_clean_text(item.get("content") or item.get("answer")), profile=profile))
    for item in answers:
        if isinstance(item, dict):
            values.append(classify_answer_type(_clean_text(item.get("content") or item.get("answer")), profile=profile))
        elif isinstance(item, str):
            values.append(classify_answer_type(item, profile=profile))
    return values


def _score_cap_for_context(session_context: Dict[str, Any]) -> Optional[int]:
    stats = session_context.get("sessionStats") or session_context.get("session_stats") or {}
    if isinstance(stats, dict):
        if int(stats.get("effectiveAnswerCount") or 0) <= 0 and stats.get("scores"):
            return 10
        if (
            int(stats.get("dontKnowCount") or 0) >= 2
            or int(stats.get("endRequestCount") or 0) >= 2
            or int(stats.get("refuseCount") or 0) >= 2
            or int(stats.get("nonsenseCount") or 0) >= 2
        ):
            return 10
        if int(stats.get("consecutiveLowScoreCount") or 0) >= 3:
            return 15

    answer_types = _answer_types_from_context(session_context)
    if not answer_types:
        return None
    weak_types = {
        "weak_answer",
        "vague_answer",
        "too_short",
        "no_experience",
        "dont_know",
        "irrelevant_answer",
        "negative_answer",
        "refuse_answer",
        "end_request",
        "nonsense_answer",
    }
    if all(answer_type in weak_types for answer_type in answer_types):
        return 30
    if any(answer_type in {"no_experience", "dont_know", "irrelevant_answer", "negative_answer", "refuse_answer", "end_request", "nonsense_answer", "too_short"} for answer_type in answer_types):
        return 60
    return None


def _decode_image_base64(image_base64: str, media_type: Optional[str] = None) -> Tuple[str, str]:
    value = str(image_base64 or "").strip()
    if not value:
        raise MimoInterviewConfigError("imageBase64 is required", "EMPTY_IMAGE")

    requested_media_type = str(media_type or "").strip().lower().replace("image/jpg", "image/jpeg")
    match = re.match(r"^data:(image/(?:jpeg|jpg|png));base64,(.*)$", value, flags=re.IGNORECASE | re.DOTALL)
    if match:
        detected_media_type = match.group(1).lower().replace("image/jpg", "image/jpeg")
        value = match.group(2)
    else:
        detected_media_type = "image/png" if value.startswith("iVBOR") else (requested_media_type or "image/jpeg")

    encoded = re.sub(r"\s+", "", value)
    max_base64_chars = int(
        os.getenv("MIMO_INTERVIEW_FRAME_MAX_BASE64_CHARS", "900000") or "900000"
    )
    if len(encoded) > max_base64_chars:
        raise MimoInterviewConfigError(
            f"imageBase64 is too large; max {max_base64_chars} base64 characters",
            "IMAGE_TOO_LARGE",
        )
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise MimoInterviewConfigError("imageBase64 is not valid base64 data", "INVALID_IMAGE_BASE64") from exc

    max_bytes = int(os.getenv("MIMO_INTERVIEW_FRAME_MAX_BYTES", str(2 * 1024 * 1024)) or str(2 * 1024 * 1024))
    if len(decoded) > max_bytes:
        raise MimoInterviewConfigError(f"imageBase64 is too large; max {max_bytes} bytes", "IMAGE_TOO_LARGE")
    if detected_media_type not in {"image/jpeg", "image/png"}:
        raise MimoInterviewConfigError("Only image/jpeg and image/png are supported", "INVALID_IMAGE_BASE64")
    return detected_media_type, encoded


def _frame_suggestions_from_text(text: str) -> List[str]:
    fallback = ["回答时尽量看向镜头", "保持自然表情和稳定语速"]
    lines = [line.strip(" -•\t") for line in str(text or "").splitlines() if line.strip()]
    suggestion_lines = [line for line in lines if "建议" in line or line.startswith(("1.", "2.", "3.", "-"))]
    return suggestion_lines[:4] or fallback


def _normalize_frame_analysis(text: str) -> Dict[str, Any]:
    raw_text = _clean_text(text)
    if not raw_text:
        raise MimoInterviewError("MiMo frame analysis response was empty", "MIMO_PARSE_ERROR")
    try:
        data = parse_json_text(text)
    except Exception:
        data = {
            "analysis": raw_text,
            "suggestions": _frame_suggestions_from_text(raw_text),
            "confidence": "low",
        }
    if not isinstance(data, dict):
        raise MimoInterviewError("MiMo frame analysis response is not a JSON object", "MIMO_PARSE_ERROR")
    fallback = {
        "analysis": "",
        "suggestions": [],
        "confidence": "medium",
        "presentationScore": 60,
        "confidenceSignal": "neutral",
        "scoreDelta": 0,
    }
    analysis = _clean_text(data.get("analysis") or data.get("content") or data.get("summary"), fallback["analysis"])
    if not analysis:
        raise MimoInterviewError("MiMo frame analysis response did not contain analysis", "MIMO_PARSE_ERROR")
    suggestions = _normalize_list(data.get("suggestions"), fallback["suggestions"])
    confidence = _clean_text(data.get("confidence"), fallback["confidence"]).lower()
    if confidence not in {"low", "medium", "high"}:
        confidence = "medium"
    confidence_signal = _clean_text(data.get("confidenceSignal") or data.get("confidence_signal"), fallback["confidenceSignal"])
    try:
        presentation_score = max(0, min(100, int(round(float(data.get("presentationScore", fallback["presentationScore"]))))))
    except (TypeError, ValueError):
        presentation_score = fallback["presentationScore"]
    try:
        score_delta = int(round(float(data.get("scoreDelta", fallback["scoreDelta"]))))
    except (TypeError, ValueError):
        score_delta = fallback["scoreDelta"]
    score_delta = max(-3, min(3, score_delta))
    return {
        "success": True,
        "analysis": analysis,
        "suggestions": suggestions,
        "confidence": confidence,
        "presentationScore": presentation_score,
        "confidenceSignal": confidence_signal,
        "scoreDelta": score_delta,
    }


def analyze_interview_frame(
    image_base64: str,
    media_type: str = "",
    session_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    media_type, encoded = _decode_image_base64(image_base64, media_type=media_type)
    raw = base64.b64decode(encoded)
    size_kb = round(len(raw) / 1024, 1)
    logger.info("[AnalyzeFrame] received image media_type=%s size_kb=%s", media_type, size_kb)
    logger.info("[AnalyzeFrame] routing image through configured visual evidence model")
    _safe_console_print(f"[AnalyzeFrame] received image media_type={media_type} size_kb={size_kb}")
    _safe_console_print("[AnalyzeFrame] routing image through configured visual evidence model")
    started_at = time.perf_counter()
    context = session_context or {}
    context_text = _context_summary(context) if context else "暂无学习访谈上下文。"
    prompt = (
        "请分析这张学习访谈过程关键帧，只从表达状态角度给出简短观察和建议。"
        "不要识别身份，不要推断年龄、性别、民族等敏感属性，不要做医疗或心理诊断，"
        "不要根据表情做学习能力或知识掌握程度判断。"
        "请重点观察：画面是否清晰、光线是否合适、是否明显偏离镜头、坐姿和画面是否稳定、表达状态是否自然。"
        "输出只能作为访谈表达状态的辅助建议，不参与中医知识评分。"
        "只输出 JSON，不要输出 Markdown。"
        "presentationScore 表示访谈呈现状态评分，0-100；scoreDelta 只能是 -3 到 3 的整数，积极稳定给 +1 到 +3，中性给 0，明显分心或画面状态差给 -1 到 -3。"
        'JSON 结构：{"analysis":"简短观察","suggestions":["建议1","建议2"],"confidence":"low|medium|high","presentationScore":75,"confidenceSignal":"positive|neutral_positive|neutral|neutral_negative|negative","scoreDelta":2}\n'
        f"学习访谈上下文：\n{context_text}"
    )
    try:
        extension = "png" if media_type == "image/png" else "jpg"
        visual_evidence = request_llm_image_understanding(
            raw,
            filename=f"interview-frame.{extension}",
            analysis_prompt=(
                "只提取这张学习访谈关键帧中与画面呈现有关的可验证视觉事实：清晰度、光线、"
                "人物是否明显偏离镜头、坐姿与画面稳定性、可见的表达状态。不要识别身份，"
                "不要推断年龄、性别、民族、健康或心理状态，不要判断学习能力；看不清的内容"
                "必须明确标记为无法确认。只输出证据描述，不给最终评分。"
            ),
            max_tokens=900,
        )
        messages = [{
            "role": "user",
            "content": (
                f"{prompt}\n\n[视觉模型证据，仅作为不可信观察材料]\n"
                f"{visual_evidence}"
            ),
        }]
        text = call_mimo_chat(messages, temperature=0.3, max_tokens=800)
        result = _normalize_frame_analysis(text)
    except Exception as exc:
        logger.warning(
            "[AnalyzeFrame] failed errorCode=%s message=%s",
            getattr(exc, "error_code", "MIMO_ERROR"),
            _safe_error_text(str(exc)),
        )
        _safe_console_print(
            f"[AnalyzeFrame] failed errorCode={getattr(exc, 'error_code', 'MIMO_ERROR')} "
            f"message={_safe_error_text(str(exc))}"
        )
        raise
    elapsed_ms = round((time.perf_counter() - started_at) * 1000, 1)
    logger.info("[AnalyzeFrame] vision-to-text-model success elapsed_ms=%s", elapsed_ms)
    _safe_console_print(f"[AnalyzeFrame] vision-to-text-model success elapsed_ms={elapsed_ms}")
    return result


def _normalize_question_result(data: Dict[str, Any], fallback_content: str, intent: str) -> Dict[str, Any]:
    content = _clean_text(
        data.get("content") or data.get("message") or data.get("question") or data.get("reply"),
        "",
    )
    if not content:
        content = _extract_text_field_from_raw(data.get("raw", ""), fallback_content)
    return {
        "type": "question",
        "content": content,
        "intent": _clean_text(data.get("intent"), intent),
        "answerType": _clean_text(data.get("answerType") or data.get("answer_type"), ""),
        "answerScore": _extract_score(data.get("answerScore") or data.get("answer_score"), None),
        "coveredSkills": _normalize_list(data.get("coveredSkills") or data.get("covered_skills"), []),
        "shouldEnd": bool(data.get("shouldEnd") or data.get("should_end") or False),
        "endReason": _clean_text(data.get("endReason") or data.get("end_reason")),
        "score": None,
    }


def normalize_answer_text(text: str) -> str:
    value = unicodedata.normalize("NFKC", str(text or "")).strip().lower()
    value = re.sub(r"\s+", "", value)
    value = re.sub(r"([。！？!?.,，、；;])\1+", r"\1", value)
    return value


def _profile_signal_keywords(profile: Dict[str, Any]) -> List[str]:
    values: List[str] = []
    values.extend(str(item) for item in profile.get("strongAnswerSignals") or [])
    for items in (profile.get("skillSignals") or {}).values():
        values.extend(str(item) for item in items)
    values.extend(["项目", "实验", "课程设计", "调试", "排查", "验证", "职责", "结果"])
    normalized: List[str] = []
    for item in values:
        text = normalize_answer_text(item)
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def _weak_signal_map(profile: Dict[str, Any]) -> Dict[str, List[str]]:
    merged = {key: list(values) for key, values in DEFAULT_WEAK_SIGNALS.items()}
    profile_signals = profile.get("weakAnswerSignals")
    if isinstance(profile_signals, dict):
        for key, values in profile_signals.items():
            merged.setdefault(key, [])
            merged[key].extend(str(item) for item in values)
    extra = profile.get("extraWeakSignals")
    if isinstance(extra, dict):
        for key, values in extra.items():
            merged.setdefault(key, [])
            merged[key].extend(str(item) for item in values)
    normalized_map: Dict[str, List[str]] = {}
    for key, values in merged.items():
        normalized_map[key] = []
        for item in values:
            normalized = normalize_answer_text(item)
            if normalized and re.search(r"[a-z0-9\u4e00-\u9fff]", normalized):
                normalized_map[key].append(normalized)
    return normalized_map


def _count_hits(answer: str, signals: List[str]) -> int:
    return len({signal for signal in signals if signal and signal in answer})


def _has_weak(answer: str, weak_signals: Dict[str, List[str]], category: str) -> bool:
    return _count_hits(answer, weak_signals.get(category, [])) > 0


def _result_detail_hits(answer: str) -> int:
    signals = [
        "负责", "实现", "配置", "采集", "上传", "解析", "排查", "定位", "验证", "结果",
        "稳定", "优化", "解决", "异常", "重连", "日志", "波形", "上位机", "完成", "降低", "提升", "%",
    ]
    return _count_hits(answer, [normalize_answer_text(item) for item in signals])


def _has_answer_evidence_for_project_followup(user_answer: str) -> bool:
    answer = normalize_answer_text(user_answer)
    evidence_markers = [
        "课程", "练习", "医案", "分析", "复盘", "依据", "阴阳", "五行", "藏象", "气血", "津液",
        "经络", "四诊", "望诊", "闻诊", "问诊", "切诊", "舌诊", "脉诊", "八纲", "辨证", "证候",
        "病机", "治法", "中药", "方剂", "君臣佐使", "配伍", "禁忌", "经典", "安全",
    ]
    return _count_hits(answer, [normalize_answer_text(item) for item in evidence_markers]) > 0


def _is_relation_only_answer(user_answer: str) -> bool:
    answer = normalize_answer_text(user_answer)
    relation_markers = ["有关系", "相关", "有关", "沾边", "算是", "大概了解", "就是和"]
    if _count_hits(answer, [normalize_answer_text(item) for item in relation_markers]) <= 0:
        return False
    return not _has_answer_evidence_for_project_followup(user_answer)


def _basic_specific_followup(profile: Dict[str, Any], fallback: str) -> str:
    question = _profile_basic_question(profile, 0, fallback)
    return (
        "你提到和当前方向有关，但还没有具体细节。请具体说一个学过的概念、方药或医案，"
        f"并说明理解依据。也可以先回答这个基础问题：{question}"
    )


def classify_answer_type(user_answer: str, profile: Optional[Dict[str, Any]] = None) -> str:
    profile = profile or get_interview_profile(DEFAULT_POSITION_KEY)
    answer = normalize_answer_text(user_answer)
    if not answer:
        return "nonsense_answer"

    weak_signals = _weak_signal_map(profile)
    role_hits = _count_hits(answer, _profile_signal_keywords(profile))
    detail_hits = _result_detail_hits(answer)
    if _is_relation_only_answer(user_answer):
        return "vague_answer"

    if _has_weak(answer, weak_signals, "nonsense_answer") or re.fullmatch(r"[\d\W_]+", answer) or re.fullmatch(r"[a-z]{1,6}", answer):
        return "nonsense_answer"
    if len(re.sub(r"[^\w\u4e00-\u9fff]", "", answer)) < 2:
        return "too_short"

    if _has_weak(answer, weak_signals, "end_request"):
        return "end_request"
    if _has_weak(answer, weak_signals, "refuse_answer"):
        return "refuse_answer"

    has_dont_know = _has_weak(answer, weak_signals, "dont_know")
    has_no_experience = _has_weak(answer, weak_signals, "no_experience")
    has_negative = _has_weak(answer, weak_signals, "negative_answer")
    has_irrelevant = _has_weak(answer, weak_signals, "irrelevant_answer")
    has_vague = _has_weak(answer, weak_signals, "vague_answer")
    generic_mismatch = [
        "海报", "运营", "销售", "剪辑", "文案", "文科", "办公软件", "word", "ppt",
        "打游戏", "玩游戏", "只会玩", "不搞硬件", "不写代码", "不做开发",
    ]
    if role_hits <= 0 and _count_hits(answer, [normalize_answer_text(item) for item in generic_mismatch]) > 0:
        return "irrelevant_answer"

    if has_dont_know and role_hits <= 0:
        return "dont_know"
    if has_no_experience and role_hits <= 0:
        return "no_experience"
    if has_negative and role_hits <= 0:
        return "negative_answer"
    if has_irrelevant and role_hits <= 0:
        return "irrelevant_answer"

    clean_len = len(re.sub(r"[^\w\u4e00-\u9fff]", "", answer))
    if clean_len < 4 and role_hits <= 0:
        return "too_short"
    if clean_len < 8 and role_hits <= 0:
        return "weak_answer"

    if (has_dont_know or has_no_experience or has_vague or has_negative) and role_hits > 0:
        return "weak_answer" if role_hits <= 2 else "vague_answer"

    if has_vague and role_hits <= 0:
        return "vague_answer"
    if has_irrelevant:
        return "weak_answer" if role_hits > 0 else "irrelevant_answer"

    if role_hits >= 5 and detail_hits >= 3 and clean_len >= 45:
        return "strong_answer"
    if role_hits >= 4 and clean_len >= 18:
        return "normal_answer"
    if role_hits >= 3 and detail_hits >= 1 and clean_len >= 18:
        return "normal_answer"
    if role_hits >= 1:
        return "weak_answer"
    return "vague_answer" if clean_len >= 8 else "too_short"


def score_interview_answer(user_answer: str, profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    profile = profile or get_interview_profile(DEFAULT_POSITION_KEY)
    answer_type = classify_answer_type(user_answer, profile=profile)
    answer = normalize_answer_text(user_answer)
    role_hits = _count_hits(answer, _profile_signal_keywords(profile))
    detail_hits = _result_detail_hits(answer)
    score_ranges = {
        "nonsense_answer": (0, 5),
        "dont_know": (0, 10),
        "refuse_answer": (0, 10),
        "end_request": (0, 10),
        "irrelevant_answer": (0, 15),
        "negative_answer": (0, 15),
        "no_experience": (5, 20),
        "too_short": (0, 20),
        "vague_answer": (20, 40),
        "weak_answer": (20, 45),
        "normal_answer": (50, 75),
        "strong_answer": (80, 100),
    }
    low, high = score_ranges.get(answer_type, (20, 40))
    if answer_type == "weak_answer":
        score = 28 + min(role_hits * 4, 12) + min(detail_hits * 2, 5)
    elif answer_type == "vague_answer":
        score = 24 + min(role_hits * 3, 9) + min(detail_hits * 2, 5)
    elif answer_type == "normal_answer":
        score = 54 + min(role_hits * 4, 16) + min(detail_hits * 2, 8)
    elif answer_type == "strong_answer":
        score = 82 + min(role_hits * 2, 10) + min(detail_hits * 2, 8)
    elif answer_type in {"no_experience", "irrelevant_answer", "negative_answer"}:
        score = low + min(role_hits * 3, max(0, high - low))
    else:
        score = low + min(role_hits * 2, max(0, high - low))
    return {
        "answerType": answer_type,
        "answerScore": max(low, min(high, int(round(score)))),
    }


def _is_incompatible_followup(answer_type: str, content: str, user_answer: str = "") -> bool:
    has_evidence = _has_answer_evidence_for_project_followup(user_answer)
    if answer_type not in {"no_experience", "dont_know", "irrelevant_answer", "negative_answer", "refuse_answer", "end_request", "nonsense_answer", "too_short"} and has_evidence:
        return False
    text = _clean_text(content)
    project_only_markers = ["你刚才提到的项目", "项目里", "项目中的", "技术难点", "排查步骤", "量化结果", "你负责", "实际负责", "遇到的技术问题", "项目难点"]
    return any(marker in text for marker in project_only_markers)


def generate_interview_question(session_context: Dict[str, Any]) -> Dict[str, Any]:
    profile = _profile_from_context(session_context)
    fallback = {
        "type": "question",
        "content": _clean_text(
            profile.get("projectQuestionTemplate"),
            "请介绍一则你学习或分析过的中医医案，重点说明四诊信息、辨证依据、病机和治法思路。",
        ),
        "intent": "opening",
        "score": None,
    }
    messages = [
        {
            "role": "system",
            "content": _json_instruction('{"type":"question","content":"学习访谈问题","intent":"opening","score":null}'),
        },
        {
            "role": "user",
            "content": (
                "请根据以下学习方向和访谈上下文生成第一道或下一道中医学习问题。问题要口语化、具体、适合数字人朗读。\n"
                "必须围绕当前课程领域、学习方向和访谈主题，不要使用其他方向的问题。\n"
                f"{_context_summary(session_context)}"
            ),
        },
    ]
    text = call_mimo_chat(messages, temperature=0.65)
    data = _parse_model_json(text, fallback)
    return _normalize_question_result(data, fallback["content"], "opening")


def generate_interview_followup(
    session_context: Dict[str, Any],
    user_answer: str,
    frame_analysis: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    profile = _profile_from_context(session_context)
    frame_analysis = frame_analysis or session_context.get("frameAnalysis") or session_context.get("frame_analysis")
    local_eval = score_interview_answer(user_answer, profile=profile)
    local_answer_type = local_eval["answerType"]
    local_answer_score = local_eval["answerScore"]
    frame_hint = ""
    if isinstance(frame_analysis, dict):
        analysis = _clean_text(frame_analysis.get("analysis") or frame_analysis.get("content"))
        suggestions = _normalize_list(frame_analysis.get("suggestions"), [])
        if analysis or suggestions:
            frame_hint = (
                "\n最近一次学习访谈画面观察（仅作为表达状态参考，不参与知识评分，不做身份、敏感属性或医疗判断）："
                f"{analysis}"
                f"{'；建议：' + '；'.join(suggestions) if suggestions else ''}"
            )
    default_project_followup = _clean_text(
        profile.get("projectQuestionTemplate"),
        "请补充一则与当前学习方向相关的医案或课程练习，说明你的分析依据、关键思路和复盘结果。",
    )
    has_answer_evidence = _has_answer_evidence_for_project_followup(user_answer)
    relation_only_answer = _is_relation_only_answer(user_answer)
    basic_specific_followup = _basic_specific_followup(profile, default_project_followup)
    fallback_by_type = {
        "no_experience": _profile_basic_question(profile, 0, default_project_followup),
        "dont_know": _profile_basic_question(profile, 1, default_project_followup),
        "irrelevant_answer": _profile_basic_question(profile, 0, default_project_followup),
        "negative_answer": _profile_basic_question(profile, 0, default_project_followup),
        "refuse_answer": f"这个问题需要继续确认一下学习基础。{_profile_basic_question(profile, 0, default_project_followup)}",
        "end_request": f"可以理解，我们再用一个很基础的问题快速确认一下。{_profile_basic_question(profile, 0, default_project_followup)}",
        "nonsense_answer": _profile_basic_question(profile, 0, default_project_followup),
        "too_short": _profile_basic_question(profile, 0, default_project_followup),
        "vague_answer": basic_specific_followup if not has_answer_evidence else "你刚才的回答还比较概括。请你补充一个具体例子，说明你接触过的实验或技术点是什么。",
        "weak_answer": basic_specific_followup if not has_answer_evidence else "你刚才提到了一些相关内容，请再具体说一下这个实验或技术点的一个具体步骤。",
        "normal_answer": "你刚才提到的经历里，最关键的技术难点是什么？请进一步说明你当时的排查步骤。",
        "strong_answer": "你刚才的项目描述比较完整，请进一步说明其中一个关键问题的定位过程和最终量化结果。",
    }
    fallback_content = _profile_followup(
        profile,
        local_answer_type,
        fallback_by_type.get(local_answer_type, fallback_by_type["normal_answer"]),
    )
    if relation_only_answer or (local_answer_type in {"weak_answer", "vague_answer"} and not has_answer_evidence):
        fallback_content = basic_specific_followup
    allowed_skills = "、".join(profile.get("coreSkills") or [])
    messages = [
        {
            "role": "system",
            "content": _json_instruction(
                '{"type":"question","answerType":"strong_answer|normal_answer|vague_answer|weak_answer|no_experience|dont_know|irrelevant_answer|negative_answer|refuse_answer|end_request|nonsense_answer|too_short",'
                '"answerScore":5,"coveredSkills":["当前学习能力点key"],"shouldEnd":false,"endReason":"","content":"追问内容","score":null}'
            ),
        },
        {
            "role": "user",
            "content": (
                "请先判断学习者最新回答类型并给本轮回答评分，再生成一个自然追问。\n"
                "回答类型只能是：strong_answer、normal_answer、vague_answer、weak_answer、no_experience、dont_know、irrelevant_answer、negative_answer、refuse_answer、end_request、nonsense_answer、too_short。\n"
                "评分区间：nonsense_answer 0-5；dont_know/refuse_answer/end_request 0-10；irrelevant_answer/negative_answer 0-15；no_experience 5-20；too_short 0-20；vague_answer 20-40；weak_answer 20-45；normal_answer 50-75；strong_answer 80-100。\n"
                "规则：\n"
                "1. 如果学习者说“我不会”“我不知道”“我啥也不会”等，answerScore 必须小于等于 15，并降低难度，改问基础问题。\n"
                "2. 这种情况不要追问复杂医案细节，不要假装学习者已经提供了辨证依据。\n"
                "3. 如果回答空泛，追问具体概念、辨证依据或课程练习步骤。\n"
                "4. 只有学习者确实提到中医概念、方药、医案或分析过程时，才追问判断依据和复盘结果。\n"
                "5. 每次只问一个问题。\n"
                "6. message 阶段不要输出最终总结，score 必须是 null。shouldEnd 只作为建议，最终是否结束由后端决定。\n"
                "7. 如果连续多轮明显不会、不知道、跑题或要求结束，可以把 shouldEnd 设为 true 并给出 endReason。\n"
                f"8. coveredSkills 只能从当前学习方向核心能力点中选择：{allowed_skills}。\n"
                "9. 所有追问必须围绕当前中医学习方向；基础理论侧重概念关系，诊断学侧重四诊与辨证，中药方剂侧重功效配伍，医案方向侧重证候、病机与治法。\n"
                f"10. 如果需要降难度，优先从这些学习基础题中选择：{'；'.join(profile.get('basicQuestions') or [])}\n"
                "11. 自动结束规则摘要：连续 3 次低分、累计 4 次低分、多次不知道/拒答/要求结束/无意义回答、长期偏离主题、达到最大轮次、能力点覆盖完整或连续高分时，后端状态机会自动结束。\n"
                "12. 如果学习者只接触过课程练习，但能说出中医概念、方药或医案相关内容，不要判 0 分，应按 weak_answer 或 vague_answer 继续追问基础细节。\n"
                "13. 不要编造学习者没有说过的知识或经历；不要把“相关”“有关系”“大概了解”当成有效学习证据。\n"
                "14. 追问必须基于学习者实际说出的内容；如果没有提供概念、四诊、辨证、方药、医案或依据细节，就问更基础、更明确的问题。\n"
                "15. 如果学习者只说“和中医有关系”，应追问一个接触过的概念、方药或医案，并要求说明理解依据。\n"
                "16. 不得重复历史记录中已经问过的问题；同一细节最多补问一次，仍然回答较短时必须切换到尚未覆盖的学习能力点。\n"
                f"{_context_summary(session_context)}\n"
                f"{frame_hint}\n"
                f"学习者最新回答：{_clean_text(user_answer)}\n"
                f"后端初步分类参考：{local_answer_type}，后端初步评分参考：{local_answer_score}"
            ),
        },
    ]
    text = call_mimo_chat(messages, temperature=0.7)
    data = _parse_model_json(
        text,
        {
            "type": "question",
            "content": fallback_content,
            "intent": "followup",
            "answerType": local_answer_type,
            "answerScore": local_answer_score,
            "coveredSkills": [],
            "shouldEnd": False,
            "endReason": "",
            "score": None,
        },
    )
    result = _normalize_question_result(data, fallback_content, "followup")
    result["answerType"] = result.get("answerType") or local_answer_type
    model_score = _extract_score(result.get("answerScore"), None)
    if model_score is None:
        model_score = local_answer_score
    if local_answer_score <= 15:
        model_score = min(model_score, local_answer_score)
        if result["answerType"] in {"strong_answer", "normal_answer", "weak_answer", "vague_answer"}:
            result["answerType"] = local_answer_type
    result["answerScore"] = max(0, min(100, int(model_score)))
    result["coveredSkills"] = _normalize_list(result.get("coveredSkills"), [])
    if _is_incompatible_followup(local_answer_type, result["content"], user_answer=user_answer):
        result["content"] = fallback_content
        result["intent"] = "basic_probe"
        result["answerType"] = local_answer_type
        result["answerScore"] = local_answer_score
    return result


def generate_interview_summary(session_context: Dict[str, Any]) -> Dict[str, Any]:
    profile = _profile_from_context(session_context)
    scoring_hints = profile.get("scoringHints") or []
    scoring_hint_text = "；".join(scoring_hints) if isinstance(scoring_hints, list) else _clean_text(scoring_hints)
    fallback = {
        "type": "summary",
        "content": "本次学习访谈已完成。学习者的中医知识表达和辨证思路仍需继续提升。",
        "score": 50,
        "advantages": ["能够围绕课程练习或医案展开表达"],
        "weaknesses": ["中医概念依据和辨证过程还不够具体"],
        "suggestions": ["准备一则完整医案复盘", "补充四诊依据、病机与治法思路"],
    }
    messages = [
        {
            "role": "system",
            "content": _json_instruction(
                '{"type":"summary","content":"总结评价","score":80,'
                '"advantages":["优点1"],"weaknesses":["不足1"],"suggestions":["建议1"]}'
            ),
        },
        {
            "role": "user",
            "content": (
                "请根据完整学习访谈上下文生成总结评价。评分范围 0-100，建议具体可执行。\n"
                f"必须按当前学习方向评价，不要套用其他方向标准。当前方向核心能力点：{'、'.join(profile.get('coreSkills') or [])}。\n"
                f"评分关注：{scoring_hint_text}\n"
                "后端会基于每轮 answerScore 和状态机计算最终 score；你的 score 只能作为参考，不要通过正文重复写评分。\n"
                "如果学习者多次不知道、拒答、无意义回答或长期偏离主题，必须给出低分倾向和基础补救建议。\n"
                "必须忠实依据历史回答，不要假设学习者掌握未曾提到的知识或医案。\n"
                "如果学习者明确表示不会、没有学习经历或回答跑题，请直接指出基础薄弱，并给出入门改进建议。\n"
                "如果上下文包含关键帧辅助分析，只能把它写入表达状态建议，不能把它作为核心技术评分依据。\n"
                "content 字段里不要重复写评分，评分只能放在 score 字段。\n"
                f"{_context_summary(session_context)}"
            ),
        },
    ]
    text = call_mimo_chat(messages, temperature=0.45)
    data = _parse_model_json(text, fallback)
    raw_summary = _clean_text(data.get("raw") or data.get("content") or data.get("summary"), fallback["content"])
    score = _extract_score(data.get("score"), None)
    if score is None:
        score = _extract_score(raw_summary, None)
    if score is None:
        score = fallback["score"]
    score_cap = _score_cap_for_context(session_context)
    if score_cap is not None:
        score = min(score, score_cap)
    summary_text = _strip_summary_score_lines(raw_summary) or fallback["content"]

    return {
        "type": "summary",
        "content": summary_text,
        "score": score,
        "advantages": _normalize_list(data.get("advantages"), fallback["advantages"]),
        "weaknesses": _normalize_list(data.get("weaknesses"), fallback["weaknesses"]),
        "suggestions": _normalize_list(data.get("suggestions"), fallback["suggestions"]),
    }


__all__ = [
    "MimoInterviewConfigError",
    "MimoInterviewError",
    "analyze_interview_frame",
    "build_anthropic_messages_url",
    "call_mimo_anthropic_text",
    "call_mimo_chat",
    "classify_answer_type",
    "normalize_answer_text",
    "score_interview_answer",
    "generate_interview_question",
    "generate_interview_followup",
    "generate_interview_summary",
]
