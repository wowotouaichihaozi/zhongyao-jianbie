import base64
import hashlib
import hmac
import json
import os
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import quote

try:
    from api_config import setting_default
except ImportError:  # pragma: no cover - package-style import fallback
    from .api_config import setting_default


_SETTING_OVERRIDES: ContextVar[dict[str, str]] = ContextVar("setting_overrides", default={})


def get_setting(name: str, default: Optional[str] = None) -> str:
    overrides = _SETTING_OVERRIDES.get()
    if name in overrides:
        return str(overrides[name] or "").strip()
    if default is None:
        default = setting_default(name, "")
    value = os.getenv(name, "").strip()
    return value or default


@contextmanager
def setting_overrides(values: Optional[Dict[str, str]] = None):
    current = dict(_SETTING_OVERRIDES.get())
    current.update({str(key): str(value or "") for key, value in (values or {}).items()})
    token = _SETTING_OVERRIDES.set(current)
    try:
        yield current
    finally:
        _SETTING_OVERRIDES.reset(token)


def require_setting(name: str, default: Optional[str] = None) -> str:
    value = get_setting(name, default)
    if not value:
        raise RuntimeError(f"Missing required setting: {name}")
    return value


def build_anthropic_messages_url(base_url: str) -> str:
    cleaned = str(base_url or "").strip().rstrip("/")
    if not cleaned:
        return ""
    lowered = cleaned.lower()
    if lowered.endswith("/v1/messages") or lowered.endswith("/messages"):
        return cleaned
    if lowered.endswith("/v1"):
        return f"{cleaned}/messages"
    return f"{cleaned}/v1/messages"


def create_llm_headers(token: str, *, anthropic: bool = True, stream: bool = False) -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if anthropic:
        headers["anthropic-version"] = "2023-06-01"
    if stream:
        headers["Accept"] = "text/event-stream"
    if token:
        headers["api-key"] = token
        headers["x-api-key"] = token
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_workflow_token() -> str:
    workflow_token = get_setting("COZE_WORKFLOW_TOKEN", "")
    if workflow_token:
        return workflow_token

    chat_token = get_setting("COZE_API_TOKEN", "")
    if chat_token:
        return chat_token

    return require_setting("COZE_WORKFLOW_TOKEN", setting_default("COZE_WORKFLOW_TOKEN"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_rfc1123() -> str:
    return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")


def sse_event(event: str, data: Any) -> bytes:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n".encode("utf-8")


def create_avatar_signed_url(api_key: str, api_secret: str) -> str:
    host = get_setting("AVATAR_SIGN_HOST")
    path = get_setting("AVATAR_SIGN_PATH")
    date = now_rfc1123()
    request_line = f"GET {path} HTTP/1.1"
    signature_origin = f"host: {host}\ndate: {date}\n{request_line}"
    signature_sha = hmac.new(
        api_secret.encode("utf-8"),
        signature_origin.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    signature = base64.b64encode(signature_sha).decode("utf-8")
    authorization_origin = (
        f'api_key="{api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature}"'
    )
    authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")
    return (
        f"wss://{host}{path}"
        f"?authorization={quote(authorization, safe='')}"
        f"&date={quote(date, safe='')}"
        f"&host={quote(host, safe='')}"
    )


def _int_setting(name: str, default: int) -> int:
    try:
        return int(get_setting(name, str(default)))
    except (TypeError, ValueError):
        return default


def create_avatar_config() -> Dict[str, Any]:
    app_id = get_setting("AVATAR_APP_ID")
    api_key = get_setting("AVATAR_API_KEY")
    api_secret = get_setting("AVATAR_API_SECRET")
    scene_id = get_setting("AVATAR_SCENE_ID")
    scene_version = get_setting("AVATAR_SCENE_VERSION")
    signed_url = ""

    if api_key and api_secret:
        try:
            signed_url = create_avatar_signed_url(api_key, api_secret)
        except Exception:
            signed_url = ""

    return {
        "serverUrl": get_setting("AVATAR_SERVER_URL"),
        "appId": app_id,
        "sceneId": scene_id,
        "sceneVersion": scene_version,
        "signedUrl": signed_url,
        "preferSignedUrl": True,
        "diagnostics": {
            "hasApiKey": bool(api_key),
            "hasApiSecret": bool(api_secret),
            "hasSignedUrl": bool(signed_url),
        },
        "avatarId": get_setting("AVATAR_ID"),
        "vcn": get_setting("AVATAR_VCN"),
        "stream": {
            "protocol": get_setting("AVATAR_STREAM_PROTOCOL", "xrtc"),
            "fps": _int_setting("AVATAR_STREAM_FPS", 25),
            "bitrate": _int_setting("AVATAR_STREAM_BITRATE", 1000000),
            "alpha": _int_setting("AVATAR_STREAM_ALPHA", 1),
        },
        "tts": {
            "speed": _int_setting("AVATAR_TTS_SPEED", 50),
            "pitch": _int_setting("AVATAR_TTS_PITCH", 50),
            "volume": _int_setting("AVATAR_TTS_VOLUME", 100),
        },
        "avatar": {
            "width": _int_setting("AVATAR_WIDTH", 720),
            "height": _int_setting("AVATAR_HEIGHT", 1280),
            "audio_format": _int_setting("AVATAR_AUDIO_FORMAT", 1),
        },
    }
