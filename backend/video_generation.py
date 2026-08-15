"""Persisted, server-side AI learning-video generation workflow."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.utils import formatdate
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

import requests
import websocket

try:
    from common import get_setting
    from learning_agents import call_llm_json
except ImportError:  # pragma: no cover
    from .common import get_setting
    from .learning_agents import call_llm_json

VIDEO_MEDIA_EXECUTOR = ThreadPoolExecutor(max_workers=6, thread_name_prefix="video-media")
VIDEO_COMPOSE_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="video-compose")
_MEDIA_GATE = threading.BoundedSemaphore(6)
MAX_ATTEMPTS = 5
SEGMENT_SECONDS = 10
MIN_SEGMENT_SECONDS = 5
MAX_SEGMENT_SECONDS = 15
MIN_VIDEO_SECONDS = 10
MAX_VIDEO_SECONDS = 60
TARGET_DURATION_TOLERANCE = 5
ROOT = Path(__file__).resolve().parent / "generated" / "video"
DEFAULT_VIDEO_ENGINE = "seedance_1_5_coze"
DEFAULT_VIDEO_RESOLUTION = "720p"
VIDEO_OUTPUT_SIZE = "16:9"
SEEDREAM_MODEL = "seedream-4-5"
SEEDREAM_RESOLUTION = "2K"
DEFAULT_TTS_PROVIDER = "xfyun"
DEFAULT_XFYUN_TTS_URL = "wss://cbm01.cn-huabei-1.xf-yun.com/v1/private/mcd9m97e6"
DEFAULT_XFYUN_TTS_VOICE = "x6_lingxiaoxuan_pro"
VIDEO_ENGINE_MODELS: dict[str, str | None] = {
    "seedance_1_5_coze": None,
    "seedance_2_mini": "doubao-seedance-2.0-mini",
    "seedance_2": "doubao-seedance-2.0",
}
VIDEO_ENGINE_LABELS = {
    "seedance_1_5_coze": "Seedance 1.5",
    "seedance_2_mini": "Seedance 2 Mini",
    "seedance_2": "Seedance 2",
}
VIDEO_RESOLUTION_DIMENSIONS = {
    "480p": (854, 480),
    "720p": (1280, 720),
    "1080p": (1920, 1080),
}
SUPPORTED_VIDEO_ENGINES = frozenset(VIDEO_ENGINE_MODELS)
SUPPORTED_VIDEO_RESOLUTIONS = frozenset(VIDEO_RESOLUTION_DIMENSIONS)
SUPPORTED_VIDEO_SIZES = frozenset({VIDEO_OUTPUT_SIZE})


class VideoGenerationError(RuntimeError):
    pass


def _setting(key: str, default: str = "") -> str:
    return str(get_setting(key, default) or default).strip()


def _safe_id(value: object) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "", str(value or ""))[:96]


def _video_engine(params: dict[str, Any]) -> str:
    selected = str(
        params.get("videoEngine")
        or params.get("video_engine")
        or DEFAULT_VIDEO_ENGINE
    ).strip()
    return selected if selected in SUPPORTED_VIDEO_ENGINES else DEFAULT_VIDEO_ENGINE


def _normalize_video_resolution(value: object) -> str:
    selected = str(value or DEFAULT_VIDEO_RESOLUTION).strip().lower()
    return selected if selected in SUPPORTED_VIDEO_RESOLUTIONS else DEFAULT_VIDEO_RESOLUTION


def _video_resolution(params: dict[str, Any]) -> str:
    return _normalize_video_resolution(
        params.get("resolution")
        or params.get("videoResolution")
        or params.get("video_resolution")
    )


def _normalize_video_size(value: object) -> str:
    selected = str(value or VIDEO_OUTPUT_SIZE).strip()
    return selected if selected in SUPPORTED_VIDEO_SIZES else VIDEO_OUTPUT_SIZE


def _video_size(params: dict[str, Any]) -> str:
    return _normalize_video_size(
        params.get("size")
        or params.get("aspectRatio")
        or params.get("aspect_ratio")
    )


def _normalize_video_params(params: dict[str, Any] | None) -> dict[str, Any]:
    normalized = dict(params or {})
    normalized["videoEngine"] = _video_engine(normalized)
    normalized["resolution"] = _video_resolution(normalized)
    normalized["size"] = _video_size(normalized)
    try:
        duration = int(normalized.get("duration") or 30)
    except (TypeError, ValueError):
        duration = 30
    normalized["duration"] = max(MIN_VIDEO_SECONDS, min(MAX_VIDEO_SECONDS, duration))
    return normalized


def _normalize_segment_duration(value: object) -> int:
    try:
        duration = int(value or SEGMENT_SECONDS)
    except (TypeError, ValueError):
        duration = SEGMENT_SECONDS
    return max(MIN_SEGMENT_SECONDS, min(MAX_SEGMENT_SECONDS, duration))


def _image_api_token() -> str:
    return (
        _setting("SEEDREAM_API_KEY", "")
        or _setting("VIDEO_IMAGE_API_KEY", "")
        or _setting("IMAGE2_API_KEY", "")
    )


def _tts_provider() -> str:
    return _setting("VIDEO_TTS_PROVIDER", DEFAULT_TTS_PROVIDER).lower()


def _xfyun_tts_credentials() -> tuple[str, str, str]:
    return (
        _setting("XFYUN_TTS_APP_ID", ""),
        _setting("XFYUN_TTS_API_KEY", ""),
        _setting("XFYUN_TTS_API_SECRET", ""),
    )


def _legacy_tts_api_token() -> str:
    return _setting("VIDEO_TTS_API_KEY", "") or _setting("TTS_API_KEY", "")


def _seedance_15_api_token() -> str:
    return (
        _setting("COZE_SEEDANCE_15_API_TOKEN", "")
        or _setting("COZE_API_TOKEN", "")
        or _setting("COZE_WORKFLOW_TOKEN", "")
    )


def _seedance_2_model(engine: str) -> str:
    if engine == "seedance_2_mini":
        configured = _setting("VIDEO_VIDEO_MODEL_MINI", "")
        if configured:
            return configured
        return _setting("VIDEO_VIDEO_MODEL", VIDEO_ENGINE_MODELS[engine] or "")
    if engine == "seedance_2":
        return _setting("VIDEO_VIDEO_MODEL_FULL", VIDEO_ENGINE_MODELS[engine] or "")
    raise VideoGenerationError(f"不支持通过视频生成接口调用引擎：{engine}")


def _validate_video_configuration(engine: str) -> None:
    required = [("SEEDREAM_API_KEY/VIDEO_IMAGE_API_KEY/IMAGE2_API_KEY", _image_api_token())]
    if _tts_provider() == "xfyun":
        app_id, api_key, api_secret = _xfyun_tts_credentials()
        required.extend(
            [
                ("XFYUN_TTS_APP_ID", app_id),
                ("XFYUN_TTS_API_KEY", api_key),
                ("XFYUN_TTS_API_SECRET", api_secret),
            ]
        )
    elif _tts_provider() == "openai_compatible":
        required.extend(
            [
                ("VIDEO_TTS_API_KEY/TTS_API_KEY", _legacy_tts_api_token()),
                ("VIDEO_TTS_MODEL/TTS_MODEL", _setting("VIDEO_TTS_MODEL", _setting("TTS_MODEL", ""))),
            ]
        )
    else:
        raise VideoGenerationError(f"Unsupported TTS provider: {_tts_provider()}")
    if engine == DEFAULT_VIDEO_ENGINE:
        required.extend(
            [
                (
                    "COZE_SEEDANCE_15_API_TOKEN/COZE_API_TOKEN/COZE_WORKFLOW_TOKEN",
                    _seedance_15_api_token(),
                ),
                (
                    "COZE_SEEDANCE_15_WORKFLOW_ID",
                    _setting("COZE_SEEDANCE_15_WORKFLOW_ID", ""),
                ),
            ]
        )
    else:
        required.extend(
            [
                ("VIDEO_VIDEO_API_KEY", _setting("VIDEO_VIDEO_API_KEY", "")),
                (
                    "VIDEO_VIDEO_MODEL_MINI/VIDEO_VIDEO_MODEL"
                    if engine == "seedance_2_mini"
                    else "VIDEO_VIDEO_MODEL_FULL",
                    _seedance_2_model(engine),
                ),
            ]
        )
    missing = [name for name, value in required if not value]
    if missing:
        raise VideoGenerationError(f"视频生成配置缺失：{'、'.join(missing)}")


def task_directory(user_id: int, task_id: str) -> Path:
    safe_task_id = _safe_id(task_id)
    if not safe_task_id:
        raise VideoGenerationError("Invalid video task id")
    return ROOT / str(int(user_id)) / safe_task_id


def media_file(user_id: int, task_id: str, name: str) -> Path:
    directory = task_directory(user_id, task_id).resolve()
    target = (directory / name).resolve()
    if directory not in target.parents:
        raise VideoGenerationError("Invalid generated video file")
    return target


def _retry(label: str, operation: Callable[[], Any], notice: Callable[[str], None]) -> Any:
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with _MEDIA_GATE:
                return operation()
        except Exception as exc:
            last_error = exc
            if attempt >= MAX_ATTEMPTS:
                break
            notice(f"{label} 第 {attempt + 1}/{MAX_ATTEMPTS} 次重试：{str(exc)[:120]}")
            time.sleep(min(2 ** (attempt - 1), 8))
    raise VideoGenerationError(f"{label} 连续 {MAX_ATTEMPTS} 次失败：{last_error}")


def _headers(token: str) -> dict[str, str]:
    if not token:
        raise VideoGenerationError("视频服务尚未配置访问凭据")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _json_response(response: requests.Response) -> dict[str, Any]:
    if not response.ok:
        raise VideoGenerationError(f"上游服务 HTTP {response.status_code}: {response.text[:300]}")
    try:
        payload = response.json()
    except ValueError as exc:
        raise VideoGenerationError("上游服务返回了非 JSON 响应") from exc
    if isinstance(payload, dict) and payload.get("code") not in {None, 0, 200}:
        raise VideoGenerationError(str(payload.get("msg") or payload)[:500])
    return payload if isinstance(payload, dict) else {}


def _first_url(value: Any, *, video: bool = False) -> str:
    if isinstance(value, dict):
        for key in ("video_url", "video", "url", "download_url", "output", "content", "data", "result"):
            found = _first_url(value.get(key), video=video)
            if found:
                return found
        for nested in value.values():
            found = _first_url(nested, video=video)
            if found:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = _first_url(nested, video=video)
            if found:
                return found
    elif isinstance(value, str):
        urls = re.findall(r"https?://[^\s\"'<>\\]+", value.replace("\\/", "/"))
        for url in urls:
            clean = url.rstrip("),]}. ")
            if not video or re.search(r"\.(mp4|mov|webm)(\?|$)", clean, re.I):
                return clean
    return ""


def _wait_media_task(base_url: str, token: str, task_id: str) -> dict[str, Any]:
    deadline = time.monotonic() + max(60, min(3600, int(_setting("VIDEO_MEDIA_TASK_TIMEOUT_SECONDS", "900"))))
    while time.monotonic() < deadline:
        response = requests.get(f"{base_url.rstrip('/')}/tasks/{task_id}", headers=_headers(token), params={"language": "zh"}, timeout=45)
        payload = _json_response(response)
        data = payload.get("data") or payload
        status = str(data.get("status") or "").lower()
        if status == "completed":
            return data
        if status in {"failed", "cancelled", "canceled"}:
            raise VideoGenerationError(str(data.get("error") or f"媒体任务{status}"))
        time.sleep(max(1, min(20, int(_setting("VIDEO_MEDIA_POLL_SECONDS", "3")))))
    raise VideoGenerationError("媒体任务超时")


def _create_image(prompt: str) -> str:
    base_url = _setting(
        "SEEDREAM_BASE_URL",
        _setting("VIDEO_MEDIA_BASE_URL", _setting("MEDIA_BASE_URL", "https://api.apimart.ai/v1")),
    )
    token = _image_api_token()
    response = requests.post(
        f"{base_url.rstrip('/')}/images/generations",
        headers=_headers(token),
        json={
            "model": SEEDREAM_MODEL,
            "prompt": prompt,
            "size": VIDEO_OUTPUT_SIZE,
            "resolution": SEEDREAM_RESOLUTION,
            "n": 1,
            "watermark": False,
        },
        timeout=60,
    )
    payload = _json_response(response)
    first = (payload.get("data") or [{}])[0]
    task_id = str(first.get("task_id") or first.get("id") or "")
    if not task_id:
        raise VideoGenerationError("图片服务未返回任务 ID")
    return _first_url((_wait_media_task(base_url, token, task_id).get("result") or {}).get("images"))


def _xfyun_tts_signed_url(base_url: str, api_key: str, api_secret: str, *, date: str | None = None) -> str:
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"ws", "wss"} or not parsed.hostname:
        raise VideoGenerationError("Invalid XFYun TTS WebSocket URL")
    request_date = date or formatdate(timeval=None, localtime=False, usegmt=True)
    signature_origin = f"host: {parsed.hostname}\ndate: {request_date}\nGET {parsed.path} HTTP/1.1"
    signature = base64.b64encode(
        hmac.new(api_secret.encode("utf-8"), signature_origin.encode("utf-8"), hashlib.sha256).digest()
    ).decode("ascii")
    authorization_origin = (
        f'api_key="{api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature}"'
    )
    query = urlencode(
        {
            "authorization": base64.b64encode(authorization_origin.encode("utf-8")).decode("ascii"),
            "date": request_date,
            "host": parsed.hostname,
        },
        quote_via=quote,
    )
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, ""))


def _xfyun_tts_request(text: str, app_id: str, voice: str) -> dict[str, Any]:
    return {
        "header": {"app_id": app_id, "status": 2},
        "parameter": {
            "tts": {
                "vcn": voice,
                "speed": int(_setting("XFYUN_TTS_SPEED", "50")),
                "volume": int(_setting("XFYUN_TTS_VOLUME", "50")),
                "pitch": int(_setting("XFYUN_TTS_PITCH", "50")),
                "audio": {
                    "encoding": "lame",
                    "sample_rate": 24000,
                    "channels": 1,
                    "bit_depth": 16,
                    "frame_size": 0,
                },
            }
        },
        "payload": {
            "text": {
                "encoding": "utf8",
                "compress": "raw",
                "format": "plain",
                "status": 2,
                "text": base64.b64encode(text.encode("utf-8")).decode("ascii"),
            }
        },
    }


def _create_xfyun_tts(text: str, voice: str, destination: Path) -> None:
    app_id, api_key, api_secret = _xfyun_tts_credentials()
    selected_voice = _setting("XFYUN_TTS_VOICE", DEFAULT_XFYUN_TTS_VOICE)
    signed_url = _xfyun_tts_signed_url(
        _setting("XFYUN_TTS_URL", DEFAULT_XFYUN_TTS_URL), api_key, api_secret
    )
    timeout = max(10, min(120, int(_setting("XFYUN_TTS_TIMEOUT_SECONDS", "45"))))
    connection = websocket.create_connection(signed_url, timeout=timeout)
    mp3 = bytearray()
    try:
        connection.send(json.dumps(_xfyun_tts_request(text, app_id, selected_voice), ensure_ascii=False))
        while True:
            response = json.loads(connection.recv())
            header = response.get("header") or {}
            if int(header.get("code") or 0) != 0:
                raise VideoGenerationError(
                    f"XFYun TTS error {header.get('code')}: {str(header.get('message') or '')[:200]}"
                )
            audio = (response.get("payload") or {}).get("audio") or {}
            if audio.get("audio"):
                mp3.extend(base64.b64decode(audio["audio"], validate=True))
            if int(audio.get("status", header.get("status", 0)) or 0) == 2:
                break
    finally:
        connection.close()
    if not mp3:
        raise VideoGenerationError("XFYun TTS returned empty audio")
    destination.parent.mkdir(parents=True, exist_ok=True)
    mp3_path = destination.with_suffix(".mp3")
    mp3_path.write_bytes(mp3)
    try:
        _run(
            [
                _ffmpeg_path("ffmpeg"), "-y", "-i", str(mp3_path),
                "-c:a", "aac", "-b:a", "96k", str(destination),
            ]
        )
    finally:
        mp3_path.unlink(missing_ok=True)


def _create_legacy_tts(text: str, voice: str, destination: Path) -> None:
    base_url = _setting("VIDEO_MEDIA_BASE_URL", _setting("MEDIA_BASE_URL", "https://api.apib.ai/v1"))
    token = _legacy_tts_api_token()
    model = _setting("VIDEO_TTS_MODEL", _setting("TTS_MODEL", ""))
    if not model:
        raise VideoGenerationError("VIDEO_TTS_MODEL/TTS_MODEL is required for openai_compatible TTS")
    response = requests.post(f"{base_url.rstrip('/')}/audio/speech", headers=_headers(token), json={"model": model, "input": text, "voice": voice, "response_format": "aac", "speed": 1.0}, timeout=90)
    if not response.ok or not response.content:
        raise VideoGenerationError(f"配音服务失败：HTTP {response.status_code}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.content)


def _create_tts(text: str, voice: str, destination: Path) -> None:
    if _tts_provider() == "xfyun":
        _create_xfyun_tts(text, voice, destination)
        return
    _create_legacy_tts(text, voice, destination)


def _create_seedance_15(image_url: str, prompt: str) -> str:
    token = _seedance_15_api_token()
    workflow_id = _setting("COZE_SEEDANCE_15_WORKFLOW_ID", "")
    if not workflow_id:
        raise VideoGenerationError("COZE_SEEDANCE_15_WORKFLOW_ID 未配置")
    base_url = _setting(
        "COZE_SEEDANCE_15_API_BASE_URL",
        "https://api.coze.cn/v1",
    ).rstrip("/")
    response = requests.post(
        f"{base_url}/workflow/run",
        headers=_headers(token),
        json={
            "workflow_id": workflow_id,
            "parameters": {
                "img_head": image_url,
                "prompt": prompt,
            },
            "is_async": True,
        },
        timeout=60,
    )
    payload = _json_response(response)
    data = payload.get("data") or payload
    if isinstance(data, list):
        data = data[0] if data else {}
    execute_id = str(data.get("execute_id") or "") if isinstance(data, dict) else ""
    if not execute_id:
        raise VideoGenerationError("Seedance 1.5 工作流未返回执行 ID")
    deadline = time.monotonic() + max(60, min(3600, int(_setting("COZE_WORKFLOW_TIMEOUT_SECONDS", "1200"))))
    history_url = f"{base_url}/workflows/{workflow_id}/run_histories/{execute_id}"
    while time.monotonic() < deadline:
        body = _json_response(requests.get(history_url, headers=_headers(token), timeout=45))
        histories = body.get("data") or []
        latest = histories[0] if isinstance(histories, list) and histories else {}
        status = str(latest.get("execute_status") or latest.get("status") or "").upper()
        if status in {"SUCCESS", "COMPLETED"}:
            url = _first_url(latest.get("output") or latest, video=True)
            if url:
                return url
            raise VideoGenerationError("Seedance 1.5 未返回有效视频地址")
        if status in {"FAIL", "FAILED", "CANCELED", "CANCELLED"}:
            raise VideoGenerationError(str(latest.get("error") or latest.get("msg") or "Seedance 1.5 生成失败"))
        time.sleep(3)
    raise VideoGenerationError("Seedance 1.5 工作流超时")


def _create_seedance_2_api(
    engine: str,
    image_url: str,
    prompt: str,
    resolution: str,
    size: str = VIDEO_OUTPUT_SIZE,
    duration: int = SEGMENT_SECONDS,
) -> str:
    model = _seedance_2_model(engine)
    resolution = _normalize_video_resolution(resolution)
    size = _normalize_video_size(size)
    duration = _normalize_segment_duration(duration)
    base_url = _setting("VIDEO_MEDIA_BASE_URL", _setting("MEDIA_BASE_URL", "https://api.apib.ai/v1"))
    token = _setting("VIDEO_VIDEO_API_KEY", "")
    response = requests.post(
        f"{base_url.rstrip('/')}/videos/generations",
        headers=_headers(token),
        json={
            "model": model,
            "prompt": prompt,
            "image_urls": [image_url],
            "duration": duration,
            "resolution": resolution,
            "size": size,
            "generate_audio": False,
        },
        timeout=60,
    )
    payload = _json_response(response)
    first = (payload.get("data") or [{}])[0]
    task_id = str(first.get("task_id") or first.get("id") or "")
    if not task_id:
        raise VideoGenerationError(f"{VIDEO_ENGINE_LABELS[engine]} 未返回任务 ID")
    task = _wait_media_task(base_url, token, task_id)
    url = _first_url((task.get("result") or {}).get("videos") or task, video=True)
    if not url:
        raise VideoGenerationError(f"{VIDEO_ENGINE_LABELS[engine]} 未返回有效视频地址")
    return url


def _create_seedance_2_mini(
    image_url: str,
    prompt: str,
    resolution: str,
    size: str = VIDEO_OUTPUT_SIZE,
    duration: int = SEGMENT_SECONDS,
) -> str:
    return _create_seedance_2_api(
        "seedance_2_mini",
        image_url,
        prompt,
        resolution,
        size,
        duration,
    )


def _create_seedance_2(
    image_url: str,
    prompt: str,
    resolution: str,
    size: str = VIDEO_OUTPUT_SIZE,
    duration: int = SEGMENT_SECONDS,
) -> str:
    return _create_seedance_2_api(
        "seedance_2",
        image_url,
        prompt,
        resolution,
        size,
        duration,
    )


def _create_seedance_video(
    engine: str,
    image_url: str,
    prompt: str,
    resolution: str,
    size: str,
    duration: int = SEGMENT_SECONDS,
) -> str:
    if engine == DEFAULT_VIDEO_ENGINE:
        return _create_seedance_15(image_url, prompt)
    return _create_seedance_2_api(
        engine,
        image_url,
        prompt,
        resolution,
        size,
        duration,
    )


def _download(url: str, destination: Path) -> None:
    if not url.startswith(("http://", "https://")):
        raise VideoGenerationError("上游素材地址无效")
    response = requests.get(url, stream=True, timeout=180, allow_redirects=True)
    if not response.ok:
        raise VideoGenerationError(f"素材下载失败：HTTP {response.status_code}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    with temporary.open("wb") as output:
        for chunk in response.iter_content(1024 * 256):
            if chunk:
                output.write(chunk)
    temporary.replace(destination)


def _fit_narration(text: str, seconds: int) -> str:
    normalized = re.sub(r"\s+", " ", str(text or "")).strip()
    limit = max(8, int((seconds - 0.6) * 4))
    if len(re.findall(r"[\u3400-\u9fffA-Za-z0-9]", normalized)) <= limit:
        return normalized
    result, used = [], 0
    for char in normalized:
        used += bool(re.match(r"[\u3400-\u9fffA-Za-z0-9]", char))
        if used > limit:
            break
        result.append(char)
    return "".join(result).rstrip("，、；：,.!?。！") + "。"


def _rebalance_durations(values: list[int], target_total: int) -> list[int]:
    durations = [_normalize_segment_duration(value) for value in values]
    target_total = max(
        len(durations) * MIN_SEGMENT_SECONDS,
        min(len(durations) * MAX_SEGMENT_SECONDS, int(target_total)),
    )
    while sum(durations) < target_total:
        changed = False
        for index, value in enumerate(durations):
            if value >= MAX_SEGMENT_SECONDS:
                continue
            durations[index] += 1
            changed = True
            if sum(durations) == target_total:
                break
        if not changed:
            break
    while sum(durations) > target_total:
        changed = False
        for index in range(len(durations) - 1, -1, -1):
            if durations[index] <= MIN_SEGMENT_SECONDS:
                continue
            durations[index] -= 1
            changed = True
            if sum(durations) == target_total:
                break
        if not changed:
            break
    return durations


def _planned_segment_durations(
    reference_duration: int,
    planned_segments: list[dict[str, Any]],
    engine: str,
) -> list[int]:
    reference_duration = max(
        MIN_VIDEO_SECONDS,
        min(MAX_VIDEO_SECONDS, int(reference_duration)),
    )
    if engine == DEFAULT_VIDEO_ENGINE:
        count = max(1, min(6, round(reference_duration / SEGMENT_SECONDS)))
        return [SEGMENT_SECONDS] * count

    raw_durations = [
        _normalize_segment_duration(item.get("duration"))
        for item in planned_segments
        if isinstance(item, dict)
    ]
    raw_total = sum(raw_durations)
    target_total = (
        raw_total
        if raw_durations
        and abs(raw_total - reference_duration) <= TARGET_DURATION_TOLERANCE
        else reference_duration
    )
    min_count = max(1, (target_total + MAX_SEGMENT_SECONDS - 1) // MAX_SEGMENT_SECONDS)
    max_count = max(min_count, target_total // MIN_SEGMENT_SECONDS)
    preferred_count = max(
        min_count,
        min(max_count, round(target_total / SEGMENT_SECONDS)),
    )
    if len(raw_durations) < min_count:
        count = preferred_count
    else:
        count = max(
            min_count,
            min(len(raw_durations), max_count, preferred_count + 1),
        )
    initial = raw_durations[:count] + [SEGMENT_SECONDS] * max(0, count - len(raw_durations))
    return _rebalance_durations(initial, target_total)


def _fallback_segment(
    topic: str,
    style: str,
    index: int,
    duration: int,
) -> dict[str, Any]:
    phases = [
        "建立概念场景",
        "拆解核心原理",
        "演示关键步骤",
        "验证运行结果",
        "总结易错点",
        "给出复习建议",
    ]
    phase = phases[(index - 1) % len(phases)]
    return {
        "id": f"segment_{index:02d}",
        "title": f"片段 {index}",
        "duration": duration,
        "narration": _fit_narration(
            f"{topic}：{phase}。请结合当前学习阶段理解这一部分内容。",
            duration,
        ),
        "image_prompt": (
            f"16:9 educational cinematic scene about {topic}, {phase}, {style}, "
            "clean composition, no text"
        ),
        "video_prompt": (
            f"Educational visual explanation of {topic}: {phase}. Smooth camera "
            "movement, coherent scene, no captions, no text."
        ),
    }


def _fallback_plan(
    topic: str,
    duration: int,
    style: str,
    engine: str = DEFAULT_VIDEO_ENGINE,
) -> dict[str, Any]:
    durations = _planned_segment_durations(duration, [], engine)
    segments = [
        _fallback_segment(topic, style, index, segment_duration)
        for index, segment_duration in enumerate(durations, start=1)
    ]
    return {
        "title": f"{topic} AI 讲解视频",
        "summary": f"面向当前学习阶段的 {topic} 自动讲解视频。",
        "totalDuration": sum(durations),
        "segments": segments,
    }


def _build_plan(
    topic: str,
    params: dict[str, Any],
    profile: dict[str, Any],
    sources: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized_params = _normalize_video_params(params)
    duration = normalized_params["duration"]
    engine = normalized_params["videoEngine"]
    style = str(normalized_params.get("style") or "二维科普动画")[:80]
    profile_summary = json.dumps(profile or {}, ensure_ascii=False)[:2600]
    source_summary = json.dumps(sources or [], ensure_ascii=False)[:3600]
    engine_label = VIDEO_ENGINE_LABELS[engine]
    segment_rule = (
        "Seedance 1.5 单段固定 10 秒，请生成足够数量的连续镜头。"
        if engine == DEFAULT_VIDEO_ENGINE
        else "每段 duration 必须在 5 到 15 秒之间，可按内容动态分配。"
    )
    prompt = f'''请为高校嵌入式课程生成一份 16:9 AI 讲解视频脚本。主题：{topic}
目标时长：约{duration}秒，总时长应控制在目标前后 {TARGET_DURATION_TOLERANCE} 秒内。视频模型：{engine_label}。{segment_rule}画面风格：{style}。
学习画像：{profile_summary}
知识来源：{source_summary}
约束：必须生成足够数量的连续镜头，不能用单个短镜头代替完整视频；仅陈述来源支持的知识；不确定内容要在 narration 中标注“待验证”；中文旁白按每秒约 4 个汉字控制；相邻镜头保持人物和场景连续；提示词不得要求在画面内生成文字。
只返回 JSON：{{"title":"","summary":"","totalDuration":{duration},"segments":[{{"id":"segment_01","title":"","duration":10,"narration":"","image_prompt":"","video_prompt":""}}]}}'''
    try:
        planned = call_llm_json(
            "你是严谨的课程视频编导，只输出符合约束的 JSON。",
            prompt,
            max_tokens=3000,
            timeout=90,
        )
    except Exception:
        return _fallback_plan(topic, duration, style, engine)

    raw_segments = planned.get("segments") if isinstance(planned, dict) else []
    if not isinstance(raw_segments, list):
        raw_segments = []
    raw_segments = [item for item in raw_segments if isinstance(item, dict)]
    durations = _planned_segment_durations(duration, raw_segments, engine)
    normalized = []
    for index, segment_duration in enumerate(durations, start=1):
        fallback = _fallback_segment(topic, style, index, segment_duration)
        item = raw_segments[index - 1] if index <= len(raw_segments) else {}
        normalized.append(
            {
                "id": f"segment_{index:02d}",
                "title": str(item.get("title") or fallback["title"]),
                "duration": segment_duration,
                "narration": _fit_narration(
                    str(item.get("narration") or fallback["narration"]),
                    segment_duration,
                ),
                "image_prompt": str(
                    item.get("image_prompt") or fallback["image_prompt"]
                ),
                "video_prompt": str(
                    item.get("video_prompt") or fallback["video_prompt"]
                ),
            }
        )
    return {
        "title": str(
            (planned.get("title") if isinstance(planned, dict) else "")
            or f"{topic} AI 讲解视频"
        ),
        "summary": str(
            (planned.get("summary") if isinstance(planned, dict) else "")
            or f"面向当前学习阶段的 {topic} 自动讲解视频。"
        ),
        "totalDuration": sum(durations),
        "segments": normalized,
    }


def _run(command: list[str]) -> None:
    completed = subprocess.run(command, capture_output=True, text=True, timeout=600, check=False)
    if completed.returncode != 0:
        raise VideoGenerationError((completed.stderr or completed.stdout or "FFmpeg failed")[-1200:])


def _ffmpeg_path(binary: str) -> str:
    configured = _setting(f"VIDEO_{binary.upper()}_PATH", "")
    return configured or binary


def _srt_timestamp(seconds: int) -> str:
    hours, remainder = divmod(max(0, int(seconds)), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},000"


def _compose(
    directory: Path,
    segments: list[dict[str, Any]],
    progress: Callable[[str, int, str], None],
    resolution: str = DEFAULT_VIDEO_RESOLUTION,
) -> tuple[Path, Path, int]:
    resolution = _normalize_video_resolution(resolution)
    width, height = VIDEO_RESOLUTION_DIMENSIONS[resolution]
    normalized_dir = directory / "normalized"
    normalized_dir.mkdir(parents=True, exist_ok=True)
    rendered = []
    for index, segment in enumerate(segments, start=1):
        segment_duration = _normalize_segment_duration(segment.get("duration"))
        video = directory / "segments" / f"{segment['id']}.mp4"
        audio = directory / "audio" / f"{segment['id']}.aac"
        subtitle = directory / "segments" / f"{segment['id']}.srt"
        subtitle.write_text(
            "1\n"
            f"00:00:00,000 --> {_srt_timestamp(segment_duration)}\n"
            f"{segment['narration']}\n",
            encoding="utf-8",
        )
        output = normalized_dir / f"{segment['id']}.mp4"
        subtitle_filter = str(subtitle.resolve()).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
        video_filter = (
            f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},fps=30,trim=duration={segment_duration},"
            "setpts=PTS-STARTPTS,"
            f"subtitles='{subtitle_filter}':force_style='FontSize=20,"
            "PrimaryColour=&HFFFFFF&,OutlineColour=&H80000000&,"
            "BorderStyle=1,Outline=2'[v]"
        )
        audio_filter = (
            f"[1:a]apad=pad_dur={segment_duration},"
            f"atrim=duration={segment_duration},asetpts=PTS-STARTPTS[a]"
        )
        _run(
            [
                _ffmpeg_path("ffmpeg"),
                "-y",
                "-stream_loop",
                "-1",
                "-i",
                str(video),
                "-i",
                str(audio),
                "-filter_complex",
                f"{video_filter};{audio_filter}",
                "-map",
                "[v]",
                "-map",
                "[a]",
                "-t",
                str(segment_duration),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                str(output),
            ]
        )
        rendered.append(output)
        progress("composing", 84 + round(index / len(segments) * 8), f"正在服务端剪辑 {index}/{len(segments)} 个片段")
    concat_list = directory / "concat.txt"
    concat_list.write_text("".join(f"file '{path.as_posix()}'\n" for path in rendered), encoding="utf-8")
    final = directory / "final.mp4"
    _run([_ffmpeg_path("ffmpeg"), "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", "-movflags", "+faststart", str(final)])
    poster = directory / "poster.jpg"
    _run([_ffmpeg_path("ffmpeg"), "-y", "-ss", "00:00:01", "-i", str(final), "-frames:v", "1", "-q:v", "2", str(poster)])
    probe = subprocess.run([_ffmpeg_path("ffprobe"), "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height", "-of", "json", str(final)], capture_output=True, text=True, timeout=60, check=False)
    if probe.returncode != 0:
        raise VideoGenerationError("ffprobe 无法校验最终视频")
    data = json.loads(probe.stdout or "{}")
    streams = [item for item in data.get("streams") or [] if isinstance(item, dict)]
    stream_types = {str(item.get("codec_type")) for item in streams}
    video_stream = next((item for item in streams if item.get("codec_type") == "video"), {})
    final_duration = int(round(float((data.get("format") or {}).get("duration") or 0)))
    if final_duration <= 0 or not {"video", "audio"}.issubset(stream_types):
        raise VideoGenerationError("最终视频缺少有效时长、视频流或音频流")
    if int(video_stream.get("width") or 0) != width or int(video_stream.get("height") or 0) != height:
        raise VideoGenerationError(f"最终视频尺寸不符合 {resolution}（应为 {width}x{height}）")
    planned_duration = sum(
        _normalize_segment_duration(segment.get("duration"))
        for segment in segments
    )
    if abs(final_duration - planned_duration) > 1:
        raise VideoGenerationError(
            f"最终视频时长 {final_duration} 秒与规划时长 {planned_duration} 秒不一致"
        )
    return final, poster, final_duration


def execute_generated_video_task(task_id: str, user_id: int, topic: str, params: dict[str, Any], profile: dict[str, Any], sources: list[dict[str, Any]], update: Callable[..., None]) -> dict[str, Any]:
    params = _normalize_video_params(params)
    engine = params["videoEngine"]
    resolution = params["resolution"]
    size = params["size"]
    engine_label = VIDEO_ENGINE_LABELS[engine]
    _validate_video_configuration(engine)
    directory = task_directory(user_id, task_id)
    for name in ("segments", "audio", "images"):
        (directory / name).mkdir(parents=True, exist_ok=True)

    logs: list[dict[str, Any]] = []
    plan_snapshot: dict[str, Any] = {}
    def progress(stage: str, value: int, message: str, segments: list[dict[str, Any]] | None = None) -> None:
        logs.append({"stage": stage, "progress": value, "message": message, "time": time.strftime("%Y-%m-%dT%H:%M:%S")})
        update(status="running", result_json={"message": message, "topic": topic, "progress": value, "currentStage": stage, "segments": segments or [], "plan": plan_snapshot, "selectedResource": None, "logs": logs[-40:], "engine": engine, "resolution": resolution, "size": size})

    progress("planning", 8, "正在结合学习画像与知识来源规划视频脚本")
    plan = _build_plan(topic, params, profile, sources)
    plan_snapshot.update({
        "title": str(plan.get("title") or ""),
        "summary": str(plan.get("summary") or ""),
        "totalDuration": sum(int(item.get("duration") or 0) for item in plan.get("segments") or []),
        "targetDuration": int(params.get("duration") or 30),
    })
    segments = plan["segments"]
    progress(
        "planning",
        20,
        f"已规划 {len(segments)} 个镜头，约 {plan_snapshot['totalDuration']} 秒",
        segments,
    )

    def create_segment(segment: dict[str, Any]) -> dict[str, Any]:
        segment_id = segment["id"]
        image_path = directory / "images" / f"{segment_id}.jpg"
        audio_path = directory / "audio" / f"{segment_id}.aac"
        video_path = directory / "segments" / f"{segment_id}.mp4"
        image_url = _retry(f"{segment_id} 首帧", lambda: _create_image(segment["image_prompt"]), lambda note: progress("images", 26, note, segments))
        _retry(f"{segment_id} 首帧下载", lambda: _download(image_url, image_path), lambda note: progress("images", 31, note, segments))
        _retry(f"{segment_id} 配音", lambda: _create_tts(segment["narration"], str(params.get("voice") or "nova"), audio_path), lambda note: progress("tts", 42, note, segments))
        video_url = _retry(
            f"{segment_id} {engine_label}",
            lambda: _create_seedance_video(
                engine,
                image_url,
                segment["video_prompt"],
                resolution,
                size,
                int(segment.get("duration") or SEGMENT_SECONDS),
            ),
            lambda note: progress("videos", 58, note, segments),
        )
        _retry(f"{segment_id} 视频下载", lambda: _download(video_url, video_path), lambda note: progress("videos", 72, note, segments))
        preview_base = f"/api/personalized-resources/generated-videos/{task_id}/segments/{segment_id}"
        return {
            **segment,
            "imageReady": True,
            "audioReady": True,
            "videoReady": True,
            "imageUrl": f"{preview_base}/image",
            "audioUrl": f"{preview_base}/audio",
            "videoUrl": f"{preview_base}/video",
        }

    progress("images", 24, f"正在生成首帧、配音与 {engine_label} 视频素材", segments)
    completed: list[dict[str, Any]] = []
    futures = [VIDEO_MEDIA_EXECUTOR.submit(create_segment, segment) for segment in segments]
    for index, future in enumerate(as_completed(futures), start=1):
        completed.append(future.result())
        progress("videos", 24 + round(index / len(segments) * 56), f"已完成 {index}/{len(segments)} 个视频素材", completed)
    completed.sort(key=lambda item: item["id"])
    progress("composing", 82, "素材已就绪，正在服务端自动剪辑并烧录字幕", completed)
    future = VIDEO_COMPOSE_EXECUTOR.submit(_compose, directory, completed, progress, resolution)
    final, poster, duration = future.result()
    progress("validating", 97, "已通过 MP4 视频流、音频流和时长校验", completed)
    return {"message": "AI 讲解视频已在后台生成并自动剪辑完成", "topic": topic, "progress": 100, "currentStage": "complete", "engine": engine, "resolution": resolution, "size": size, "plan": plan_snapshot, "segments": completed, "selectedResource": {"type": "generated_video", "title": plan["title"], "description": plan["summary"], "content": {"videoUrl": f"/api/personalized-resources/generated-videos/{task_id}/file", "posterUrl": f"/api/personalized-resources/generated-videos/{task_id}/poster", "duration": duration, "targetDuration": int(params.get("duration") or 30), "resolution": resolution, "size": size}, "metadata": {"taskId": task_id, "profileReportId": params.get("profileReportId") or "", "knowledgeSources": sources, "engine": engine, "resolution": resolution, "size": size, "targetDuration": int(params.get("duration") or 30), "plannedDuration": plan_snapshot["totalDuration"]}, "qualityEvaluation": {"status": "validated", "checks": ["h264", "aac", "subtitle", "duration", "target-duration", "dimensions"]}}, "logs": logs[-40:]}
