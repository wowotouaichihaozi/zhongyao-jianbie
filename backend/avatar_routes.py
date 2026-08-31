"""Digital-human HTTP routes and provider protocol helpers."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import re
import secrets
import time
from urllib.parse import quote

import requests
from flask import Blueprint, jsonify, request

try:
    from common import create_avatar_config, get_setting
except ImportError:  # pragma: no cover - package import fallback
    from .common import create_avatar_config, get_setting


avatar_bp = Blueprint("avatar", __name__)


def _redact(value: str, keep: int = 4) -> str:
    text = str(value or "")
    if not text:
        return ""
    if len(text) <= keep * 2:
        return "*" * len(text)
    return f"{text[:keep]}...{text[-keep:]}"


def _auth_hint(code, message: str) -> str:
    raw = f"{code or ''} {message or ''}".lower()
    if "20015" in raw or "avatarid is invalid" in raw or "avatar_id" in raw and "invalid" in raw:
        return "avatar_id_invalid"
    if "11203" in raw or "11200" in raw or "auth" in raw:
        return "avatar_auth_failed"
    return "unknown"


def _int_setting(name: str, default: int) -> int:
    try:
        return int(get_setting(name, str(default)))
    except (TypeError, ValueError):
        return default


def _primary_start_payload(avatar_id: str, protocol: str) -> dict:
    audio_format = _int_setting("AVATAR_AUDIO_FORMAT", 1)
    return {
        "header": {
            "app_id": get_setting("AVATAR_APP_ID"),
            "ctrl": "start",
            "request_id": f"diag_{secrets.token_hex(4)}",
            "scene_id": get_setting("AVATAR_SCENE_ID"),
            "scene_version": get_setting("AVATAR_SCENE_VERSION", ""),
        },
        "parameter": {
            "avatar_dispatch": {"enable_action_status": 1},
            "avatar": {
                "stream": {
                    "protocol": protocol,
                    "bitrate": max(1, int(_int_setting("AVATAR_STREAM_BITRATE", 1000000) / 1024)),
                    "fps": _int_setting("AVATAR_STREAM_FPS", 25),
                    "alpha": _int_setting("AVATAR_STREAM_ALPHA", 1),
                },
                "avatar_id": avatar_id,
                "width": _int_setting("AVATAR_WIDTH", 720),
                "height": _int_setting("AVATAR_HEIGHT", 1280),
                "audio_format": audio_format,
            },
            "tts": {
                "vcn": get_setting("AVATAR_VCN"),
                "speed": _int_setting("AVATAR_TTS_SPEED", 50),
                "pitch": _int_setting("AVATAR_TTS_PITCH", 50),
                "volume": _int_setting("AVATAR_TTS_VOLUME", 100),
                "audio": {"sample_rate": 24000 if audio_format == 2 else 16000},
            },
            "air": {"air": 0, "add_nonsemantic": 0},
        },
    }


def _primary_probe(avatar_id: str, protocol: str) -> dict:
    signed_url = (create_avatar_config() or {}).get("signedUrl") or ""
    if not signed_url:
        return {"success": False, "error": "signed url unavailable"}

    try:
        from websockets.sync.client import connect as ws_connect
    except Exception as exc:  # pragma: no cover - optional runtime package
        return {"success": False, "error": f"websocket client unavailable: {type(exc).__name__}"}

    result = {
        "success": False,
        "code": None,
        "message": "",
        "hasStreamUrl": False,
        "streamProtocol": "",
    }
    try:
        with ws_connect(signed_url, open_timeout=8, close_timeout=2) as websocket:
            websocket.send(json.dumps(_primary_start_payload(avatar_id, protocol), ensure_ascii=False))
            for _ in range(4):
                raw = websocket.recv(timeout=8)
                try:
                    body = json.loads(raw)
                except (TypeError, ValueError):
                    result["message"] = str(raw or "")[:240]
                    continue
                header = body.get("header") or {}
                payload = body.get("payload") or {}
                avatar_payload = payload.get("avatar") or {}
                stream_url = avatar_payload.get("stream_url") or header.get("stream_url") or ""
                result.update(
                    {
                        "code": header.get("code"),
                        "message": str(header.get("message") or "")[:240],
                        "hasStreamUrl": bool(stream_url),
                        "streamProtocol": str(stream_url).split(":", 1)[0] if stream_url else "",
                    }
                )
                if stream_url or header.get("code") == 0:
                    result["success"] = bool(stream_url or header.get("code") == 0)
                    break
                if header.get("code") not in (None, 0):
                    break
    except Exception as exc:
        result["error"] = type(exc).__name__
        if not result.get("message"):
            result["message"] = str(exc)[:240]
    return result


def _legacy_signed_url(path: str) -> str:
    host = get_setting("AVATAR_LEGACY_HOST", "vms.cn-huadong-1.xf-yun.com")
    api_key = get_setting("AVATAR_API_KEY")
    api_secret = get_setting("AVATAR_API_SECRET")
    date = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
    signature_origin = f"host: {host}\ndate: {date}\nPOST {path} HTTP/1.1"
    signature = base64.b64encode(
        hmac.new(
            api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
    ).decode("utf-8")
    authorization_origin = (
        f'api_key="{api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature}"'
    )
    authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")
    return (
        f"https://{host}{path}"
        f"?host={quote(host, safe='')}"
        f"&date={quote(date, safe='')}"
        f"&authorization={quote(authorization, safe='')}"
    )


def _legacy_post(path: str, payload: dict, timeout: float = 15.0) -> dict:
    if get_setting("AVATAR_LEGACY_ENABLED", "true").lower() in {"0", "false", "no", "off"}:
        return {"success": False, "error": "legacy avatar fallback disabled", "status": 400}
    if not get_setting("AVATAR_API_KEY") or not get_setting("AVATAR_API_SECRET") or not get_setting("AVATAR_APP_ID"):
        return {"success": False, "error": "legacy avatar credential missing", "status": 400}
    response = requests.post(
        _legacy_signed_url(path),
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=timeout,
    )
    try:
        body = response.json()
    except ValueError:
        body = {"raw": response.text}
    return {
        "success": response.ok and (body.get("header") or {}).get("code") == 0,
        "status": response.status_code,
        "body": body,
    }


def _decode_payload_text(value: str) -> str:
    if not value:
        return ""
    try:
        return base64.b64decode(value).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return value


def _iter_payload_dicts(body: dict):
    stack = [body.get("payload") or {}]
    seen = set()
    while stack:
        current = stack.pop()
        if not isinstance(current, dict):
            continue
        marker = id(current)
        if marker in seen:
            continue
        seen.add(marker)
        yield current

        text = current.get("text")
        if isinstance(text, str) and text:
            try:
                parsed = json.loads(_decode_payload_text(text))
            except (TypeError, ValueError):
                parsed = None
            if isinstance(parsed, dict):
                stack.append(parsed)

        for value in current.values():
            if isinstance(value, dict):
                stack.append(value)
            elif isinstance(value, list):
                stack.extend(item for item in value if isinstance(item, dict))


def _extract_stream_url(body: dict, header: dict) -> str:
    if header.get("stream_url"):
        return str(header.get("stream_url") or "")
    for item in _iter_payload_dicts(body):
        for key in ("stream_url", "streamUrl", "url"):
            value = item.get(key)
            if isinstance(value, str) and value:
                return value
        text = item.get("text")
        if isinstance(text, str) and text:
            decoded = _decode_payload_text(text)
            if re.match(r"^(xrtcs?|webrtc|rtmps?|https?)://", decoded, re.I):
                return decoded
    return ""


def _extract_stream_extend(body: dict) -> dict:
    for item in _iter_payload_dicts(body):
        stream_extend = item.get("stream_extend")
        if isinstance(stream_extend, dict):
            return stream_extend
        if item.get("user_sign") or item.get("appid") or item.get("app_id"):
            return item
    return {}


@avatar_bp.get("/api/avatar/config")
def avatar_config():
    return jsonify(create_avatar_config())


@avatar_bp.get("/api/avatar/diagnostics")
def avatar_diagnostics():
    avatar_id = str(request.args.get("avatarId") or get_setting("AVATAR_ID") or get_setting("AVATAR_LEGACY_ID") or "").strip()
    protocol = str(request.args.get("protocol") or get_setting("AVATAR_STREAM_PROTOCOL", "xrtc") or "xrtc").strip()
    width = _int_setting("AVATAR_LEGACY_WIDTH", 1280)
    height = _int_setting("AVATAR_LEGACY_HEIGHT", 720)
    app_id = get_setting("AVATAR_APP_ID")
    api_key = get_setting("AVATAR_API_KEY")
    diagnostics = {
        "ok": False,
        "config": {
            "appId": _redact(app_id),
            "apiKey": _redact(api_key),
            "sceneId": get_setting("AVATAR_SCENE_ID"),
            "avatarId": avatar_id,
            "protocol": protocol,
            "alpha": _int_setting("AVATAR_STREAM_ALPHA", 1),
            "legacyHost": get_setting("AVATAR_LEGACY_HOST", "vms.cn-huadong-1.xf-yun.com"),
            "serverUrl": get_setting("AVATAR_SERVER_URL"),
        },
        "primaryStart": None,
        "legacyStart": None,
        "hint": "",
    }
    if not app_id or not api_key or not get_setting("AVATAR_API_SECRET"):
        diagnostics["hint"] = "credential_missing"
        return jsonify(diagnostics), 200

    primary = _primary_probe(avatar_id, protocol)
    diagnostics["primaryStart"] = primary
    uid = f"diag_{secrets.token_hex(4)}"
    result = _legacy_post(
        "/v1/private/vms2d_start",
        {
            "header": {"app_id": app_id, "uid": uid},
            "parameter": {
                "vmr": {
                    "stream": {"protocol": protocol},
                    "avatar_id": avatar_id,
                    "width": width,
                    "height": height,
                }
            },
        },
        timeout=18.0,
    )
    body = result.get("body") or {}
    header = body.get("header") or {}
    session = header.get("session") or ""
    stream_url = _extract_stream_url(body, header)
    stream_extend = _extract_stream_extend(body)
    xrtc_user_sign = stream_extend.get("user_sign") or stream_extend.get("userSign") or ""
    diagnostics["legacyStart"] = {
        "success": bool(result.get("success")),
        "httpStatus": result.get("status"),
        "code": header.get("code"),
        "message": header.get("message"),
        "hasSession": bool(session),
        "hasStreamUrl": bool(stream_url),
        "streamProtocol": stream_url.split(":", 1)[0] if stream_url else "",
        "hasXrtcUserSign": bool(xrtc_user_sign),
    }
    diagnostics["ok"] = bool(result.get("success") and stream_url and (protocol != "xrtc" or xrtc_user_sign))
    if primary.get("success"):
        diagnostics["ok"] = True
        diagnostics["hint"] = ""
    elif diagnostics["ok"]:
        diagnostics["hint"] = ""
    else:
        diagnostics["hint"] = _auth_hint(
            primary.get("code") or header.get("code"),
            primary.get("message") or header.get("message"),
        )
    if session:
        _legacy_post(
            "/v1/private/vms2d_stop",
            {"header": {"app_id": app_id, "uid": uid, "session": session}},
            timeout=8.0,
        )
    return jsonify(diagnostics), 200


@avatar_bp.post("/api/avatar/legacy/start")
def avatar_legacy_start():
    payload = request.get_json(silent=True) or {}
    avatar_id = str(payload.get("avatarId") or get_setting("AVATAR_LEGACY_ID") or get_setting("AVATAR_ID")).strip()
    protocol = str(payload.get("protocol") or "xrtc").strip() or "xrtc"
    width = _int_setting("AVATAR_LEGACY_WIDTH", 1280)
    height = _int_setting("AVATAR_LEGACY_HEIGHT", 720)
    app_id = get_setting("AVATAR_APP_ID")
    attempts = []
    for index in range(4):
        uid = f"web_{secrets.token_hex(4)}"
        result = _legacy_post(
            "/v1/private/vms2d_start",
            {
                "header": {"app_id": app_id, "uid": uid},
                "parameter": {
                    "vmr": {
                        "stream": {"protocol": protocol},
                        "avatar_id": avatar_id,
                        "width": width,
                        "height": height,
                    }
                },
            },
            timeout=18.0,
        )
        body = result.get("body") or {}
        header = body.get("header") or {}
        attempts.append({"status": result.get("status"), "code": header.get("code"), "message": header.get("message")})
        if result.get("success"):
            stream_url = _extract_stream_url(body, header)
            stream_extend = _extract_stream_extend(body)
            return jsonify(
                {
                    "success": True,
                    "mode": "legacy-vms",
                    "avatarId": avatar_id,
                    "appId": app_id,
                    "xrtcAppId": stream_extend.get("appid") or stream_extend.get("app_id") or "",
                    "xrtcUserSign": stream_extend.get("user_sign") or stream_extend.get("userSign") or "",
                    "session": header.get("session") or "",
                    "sid": header.get("sid") or "",
                    "streamUrl": stream_url,
                    "width": width,
                    "height": height,
                    "attempts": attempts,
                }
            )
        time.sleep(0.45 + index * 0.25)
    return jsonify({"success": False, "mode": "legacy-vms", "error": "legacy avatar start failed", "attempts": attempts}), 502


def _session_payload(path: str, session: str) -> dict:
    return _legacy_post(
        path,
        {"header": {"app_id": get_setting("AVATAR_APP_ID"), "uid": "", "session": session}},
    )


@avatar_bp.post("/api/avatar/legacy/stop")
def avatar_legacy_stop():
    session = str((request.get_json(silent=True) or {}).get("session") or "").strip()
    if not session:
        return jsonify({"success": True, "skipped": True})
    result = _session_payload("/v1/private/vms2d_stop", session)
    return jsonify({"success": bool(result.get("success")), "result": result.get("body")})


@avatar_bp.post("/api/avatar/legacy/ping")
def avatar_legacy_ping():
    session = str((request.get_json(silent=True) or {}).get("session") or "").strip()
    if not session:
        return jsonify({"success": False, "error": "session missing"}), 400
    result = _session_payload("/v1/private/vms2d_ping", session)
    return jsonify({"success": bool(result.get("success")), "result": result.get("body")})


@avatar_bp.post("/api/avatar/legacy/text")
def avatar_legacy_text():
    payload = request.get_json(silent=True) or {}
    session = str(payload.get("session") or "").strip()
    text = str(payload.get("text") or "").strip()
    if not session:
        return jsonify({"success": False, "error": "session missing"}), 400
    if not text:
        return jsonify({"success": True, "skipped": True})
    result = _legacy_post(
        "/v1/private/vms2d_tts",
        {
            "header": {"app_id": get_setting("AVATAR_APP_ID"), "uid": "", "session": session},
            "parameter": {
                "tts": {
                    "vcn": str(payload.get("vcn") or get_setting("AVATAR_LEGACY_VCN", "x3_yezi")),
                    "speed": _int_setting("AVATAR_TTS_SPEED", 50),
                    "pitch": _int_setting("AVATAR_TTS_PITCH", 50),
                    "volume": _int_setting("AVATAR_TTS_VOLUME", 100),
                }
            },
            "payload": {
                "text": {
                    "encoding": "utf8",
                    "compress": "raw",
                    "format": "plain",
                    "status": 3,
                    "seq": 0,
                    "text": base64.b64encode(text.encode("utf-8")).decode("utf-8"),
                },
                "ctrl_w": {
                    "encoding": "utf8",
                    "compress": "raw",
                    "format": "json",
                    "status": 3,
                    "seq": 0,
                    "text": base64.b64encode(b'{"avatar":[],"scene":[],"tts":[]}').decode("utf-8"),
                },
            },
        },
    )
    return jsonify({"success": bool(result.get("success")), "result": result.get("body")})
