from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
from typing import Any, Callable

import requests

try:
    from api_config import setting_default
    from common import get_setting
except ImportError:  # pragma: no cover
    from .api_config import setting_default
    from .common import get_setting


StageCallback = Callable[[dict[str, Any]], None]


class OhMyPptError(RuntimeError):
    """Raised when the isolated OhMyPPT service cannot produce a valid deck."""


LOOPBACK_PROXIES = {"http": "", "https": ""}


def _emit(on_stage: StageCallback | None, stage: str, message: str, progress: int, **extra: Any) -> None:
    if not callable(on_stage):
        return
    try:
        on_stage({"stage": stage, "message": message, "progress": progress, **extra})
    except Exception:
        pass


def _api_base() -> str:
    return get_setting(
        "OHMYPPT_API_URL",
        setting_default("OHMYPPT_API_URL", "http://127.0.0.1:8765/api"),
    ).strip().rstrip("/")


def _request_timeout() -> int:
    raw = get_setting("OHMYPPT_REQUEST_TIMEOUT", setting_default("OHMYPPT_REQUEST_TIMEOUT", "600"))
    try:
        return max(30, min(900, int(raw or 600)))
    except (TypeError, ValueError):
        return 600


def _runtime_settings() -> dict[str, str]:
    protocol = str(get_setting("LLM_PROTOCOL", "auto") or "auto").strip().lower()
    if protocol not in {"auto", "openai", "anthropic"}:
        protocol = "auto"
    if protocol == "auto":
        protocol = "openai" if get_setting("OPENAI_BASE_URL", setting_default("OPENAI_BASE_URL", "")) else "anthropic"
    if protocol == "openai":
        base_url = get_setting("OPENAI_BASE_URL", setting_default("OPENAI_BASE_URL", ""))
    else:
        base_url = get_setting("ANTHROPIC_BASE_URL", setting_default("ANTHROPIC_BASE_URL", ""))
    return {
        "protocol": protocol,
        "baseUrl": str(base_url or "").strip().rstrip("/"),
        "model": str(
            get_setting(
                "ANTHROPIC_MODEL",
                setting_default("ANTHROPIC_MODEL", "astron-code-latest"),
            )
            or "astron-code-latest"
        ).strip(),
    }


def _internal_secret() -> str:
    return str(
        get_setting("OHMYPPT_INTERNAL_TOKEN", "")
        or get_setting("ANTHROPIC_AUTH_TOKEN", setting_default("ANTHROPIC_AUTH_TOKEN", ""))
        or ""
    ).strip()


def _signed_headers(session_id: str, runtime: dict[str, str]) -> dict[str, str]:
    secret = _internal_secret()
    if not secret:
        raise OhMyPptError("OhMyPPT 内部鉴权未配置，请检查服务端模型密钥")
    timestamp = str(int(time.time()))
    protocol = runtime.get("protocol") or "auto"
    base_url = runtime.get("baseUrl") or ""
    model = runtime.get("model") or "astron-code-latest"
    canonical = "\n".join([timestamp, session_id, protocol, base_url, model])
    signature = hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-OhMyPPT-Timestamp": timestamp,
        "X-OhMyPPT-Session": session_id,
        "X-OhMyPPT-Protocol": protocol,
        "X-OhMyPPT-Base-URL": base_url,
        "X-OhMyPPT-Model": model,
        "X-OhMyPPT-Signature": signature,
    }


def _safe_error_detail(response: requests.Response) -> str:
    try:
        payload = response.json()
    except (ValueError, json.JSONDecodeError):
        payload = None
    if isinstance(payload, dict):
        detail = payload.get("detail") or payload.get("message") or payload.get("error")
        if isinstance(detail, list):
            detail = "; ".join(str(item.get("msg") or item) for item in detail if item)
        if detail:
            return str(detail)[:1200]
    return str(response.text or f"HTTP {response.status_code}")[:1200]


def ohmyppt_health(*, timeout: int = 4) -> dict[str, Any]:
    base_url = _api_base()
    try:
        response = requests.get(
            f"{base_url}/health",
            timeout=max(1, min(timeout, 10)),
            proxies=LOOPBACK_PROXIES,
        )
        if response.status_code < 200 or response.status_code >= 300:
            return {
                "ok": False,
                "engine": "ohmyppt-fastapi",
                "status": "unavailable",
                "error": _safe_error_detail(response),
            }
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        return {
            "ok": False,
            "engine": "ohmyppt-fastapi",
            "status": "unavailable",
            "error": str(exc)[:800],
        }
    return {
        "ok": bool(payload.get("ok")),
        "engine": "ohmyppt-fastapi",
        "status": "ready" if payload.get("ok") else "unavailable",
        "version": str(payload.get("version") or ""),
        "model": str(payload.get("model") or ""),
        "protocol": str(payload.get("protocol") or ""),
        "hasToken": bool(payload.get("hasToken")),
        "maxCompletionTokens": int(payload.get("maxCompletionTokens") or 0),
    }


def _validate_pages(payload: dict[str, Any], *, session_id: str, expected_count: int) -> list[dict[str, Any]]:
    response_session_id = str(payload.get("sessionId") or "").strip()
    if response_session_id != session_id:
        raise OhMyPptError("OhMyPPT 返回的会话编号与任务不一致")
    pages = payload.get("pages")
    if not isinstance(pages, list) or len(pages) != expected_count:
        actual = len(pages) if isinstance(pages, list) else 0
        raise OhMyPptError(f"OhMyPPT 返回页数不完整：期望 {expected_count} 页，实际 {actual} 页")

    normalized: list[dict[str, Any]] = []
    unsafe_pattern = re.compile(
        r"(?is)<(?:iframe|object|embed|base)\b|"
        r"(?:src|href)\s*=\s*['\"]\s*(?:https?:|//|javascript:)|"
        r"url\(\s*['\"]?\s*(?:https?:|//|javascript:)"
    )
    for index, page in enumerate(pages, start=1):
        if not isinstance(page, dict):
            raise OhMyPptError(f"OhMyPPT 第 {index} 页不是有效对象")
        title = str(page.get("title") or "").strip()
        html = str(page.get("html") or "").strip()
        if not title or len(html) < 200:
            raise OhMyPptError(f"OhMyPPT 第 {index} 页缺少标题或有效 HTML")
        if unsafe_pattern.search(html):
            raise OhMyPptError(f"OhMyPPT 第 {index} 页包含未经允许的外部资源")
        normalized.append(
            {
                "pageNumber": index,
                "title": title[:240],
                "contentOutline": str(page.get("contentOutline") or "").strip()[:1200],
                "html": html,
                "generationMode": str(page.get("generationMode") or "model").strip() or "model",
                "generationWarning": str(page.get("generationWarning") or "").strip()[:1200] or None,
            }
        )
    return normalized


def generate_with_ohmyppt(
    payload: dict[str, Any],
    *,
    on_stage: StageCallback | None = None,
) -> dict[str, Any]:
    session_id = str(payload.get("sessionId") or "").strip()
    topic = str(payload.get("topic") or "嵌入式学习课件").strip() or "嵌入式学习课件"
    if not session_id or len(session_id) > 160:
        raise OhMyPptError("PPT 会话编号无效")
    try:
        page_count = max(1, min(20, int(payload.get("pageCount") or 6)))
    except (TypeError, ValueError):
        page_count = 6

    _emit(on_stage, "ohmyppt_health", "正在连接 OhMyPPT 生成引擎", 18, engine="ohmyppt-fastapi")
    health = ohmyppt_health()
    if not health.get("ok"):
        detail = str(health.get("error") or "服务未就绪")
        raise OhMyPptError(f"OhMyPPT 服务不可用：{detail}")

    runtime = _runtime_settings()
    request_payload = {
        "sessionId": session_id,
        "topic": topic,
        "pageCount": page_count,
        "userMessage": str(payload.get("userMessage") or "").strip(),
        "styleName": str(payload.get("styleName") or "嵌智学航工程教学风").strip(),
        "styleDescription": str(
            payload.get("styleDescription")
            or "白底与极浅薄荷绿背景，深灰文字，绿色强调，模块化教育科技风。"
        ).strip(),
        "styleSkill": str(payload.get("styleSkill") or "").strip(),
        "knowledgeContext": str(payload.get("knowledgeContext") or "").strip(),
    }
    _emit(
        on_stage,
        "ohmyppt_request",
        f"OhMyPPT 正在生成 {page_count} 页 H5 幻灯片",
        36,
        engine="ohmyppt-fastapi",
        pageCount=page_count,
        model=runtime["model"],
        protocol=runtime["protocol"],
    )
    try:
        response = requests.post(
            f"{_api_base()}/generate",
            headers=_signed_headers(session_id, runtime),
            json=request_payload,
            timeout=_request_timeout(),
            proxies=LOOPBACK_PROXIES,
        )
    except requests.Timeout as exc:
        raise OhMyPptError("OhMyPPT 生成超时，请稍后重试") from exc
    except requests.RequestException as exc:
        raise OhMyPptError(f"OhMyPPT 请求失败：{str(exc)[:800]}") from exc

    if response.status_code < 200 or response.status_code >= 300:
        raise OhMyPptError(f"OhMyPPT 生成失败：{_safe_error_detail(response)}")
    try:
        response_payload = response.json()
    except ValueError as exc:
        raise OhMyPptError("OhMyPPT 返回了无法解析的响应") from exc
    if not isinstance(response_payload, dict):
        raise OhMyPptError("OhMyPPT 返回结构无效")

    _emit(on_stage, "ohmyppt_validate", "页面已返回，正在执行结构与安全校验", 88, pageCount=page_count)
    pages = _validate_pages(response_payload, session_id=session_id, expected_count=page_count)
    fallback_count = sum(1 for page in pages if page.get("generationMode") == "fallback")
    completion_message = f"OhMyPPT 已完成 {len(pages)} 页课件"
    if fallback_count:
        completion_message += f"，其中 {fallback_count} 页为可编辑保底页"
    _emit(
        on_stage,
        "ohmyppt_complete",
        completion_message,
        96,
        pageCount=len(pages),
        generationMode=str(response_payload.get("generationMode") or "model"),
        fallbackCount=fallback_count,
    )
    raw_warnings = response_payload.get("generationWarnings")
    generation_warnings = raw_warnings if isinstance(raw_warnings, list) else []
    return {
        "sessionId": session_id,
        "title": str(response_payload.get("title") or topic).strip() or topic,
        "pages": pages,
        "generationMode": str(response_payload.get("generationMode") or "model").strip() or "model",
        "generationWarnings": [
            str(item).strip()[:1200]
            for item in generation_warnings
            if str(item).strip()
        ],
        "engine": {
            "id": "ohmyppt-fastapi",
            "version": str(health.get("version") or ""),
            "protocol": runtime["protocol"],
            "model": runtime["model"],
        },
    }
