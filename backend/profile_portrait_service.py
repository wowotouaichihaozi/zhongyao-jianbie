"""Server-side Seedream portraits for learning-profile reports."""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


PORTRAIT_DIR = Path(__file__).resolve().parent / "data" / "profile_portraits"
RETRYABLE_HTTP_CODES = {408, 429, 500, 502, 503, 504, 524}
DEFAULT_SEEDREAM_BASE_URL = "https://api.apimart.ai/v1"
SEEDREAM_MODEL = "seedream-4-5"
FAILED_TASK_STATUSES = {"failed", "failure", "error", "cancelled", "canceled"}


def _image2_settings() -> tuple[str, str, str]:
    base_url = (
        os.getenv("SEEDREAM_BASE_URL", "").strip()
        or os.getenv("IMAGE2_BASE_URL", "").strip()
        or DEFAULT_SEEDREAM_BASE_URL
    )
    api_key = os.getenv("SEEDREAM_API_KEY", "").strip() or os.getenv("IMAGE2_API_KEY", "").strip()
    return base_url, api_key, SEEDREAM_MODEL


def _max_request_attempts() -> int:
    try:
        configured = int(os.getenv("IMAGE2_MAX_ATTEMPTS", "2"))
    except (TypeError, ValueError):
        configured = 2
    return max(1, min(configured, 3))


def _bounded_env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        configured = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        configured = default
    return max(minimum, min(configured, maximum))


def _http_error_detail(exc: urllib.error.HTTPError) -> str:
    try:
        raw = exc.read().decode("utf-8", errors="replace")
    except Exception:
        raw = ""
    message = ""
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        payload = {}
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = str(error.get("message") or error.get("code") or "")
        elif isinstance(error, str):
            message = error
        message = message or str(payload.get("detail") or payload.get("message") or "")
    if not message and exc.code == 524:
        message = "relay origin response timeout"
    return " ".join(message.split())[:240]


def _profile_text(profile: dict[str, Any], key: str) -> str:
    value = (profile.get("chatStudentProfile") or {}).get(key) if isinstance(profile.get("chatStudentProfile"), dict) else ""
    if isinstance(value, list):
        return "、".join(str(item) for item in value[:3] if str(item).strip())
    return str(value or "").strip()


def _walk_payload(value: Any):
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _walk_payload(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_payload(nested)


def _first_payload_string(payload: Any, keys: tuple[str, ...]) -> str:
    for item in _walk_payload(payload):
        for key in keys:
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def _extract_image_source(payload: Any) -> tuple[str, str]:
    for item in _walk_payload(payload):
        for key in ("b64_json", "b64", "base64", "image_base64"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return "b64", value.strip()
        for key in ("url", "image_url", "imageUrl"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return "url", value.strip()
            if isinstance(value, list):
                image_url = next((str(entry).strip() for entry in value if isinstance(entry, str) and entry.strip()), "")
                if image_url:
                    return "url", image_url
    return "", ""


def _api_url(base_url: str, path: str) -> str:
    normalized_base = base_url.rstrip("/")
    normalized_path = path.lstrip("/")
    if normalized_base.lower().endswith("/v1") and normalized_path.lower().startswith("v1/"):
        normalized_path = normalized_path[3:]
    return f"{normalized_base}/{normalized_path}"


def _candidate_status_urls(base_url: str, payload: Any) -> list[str]:
    urls: list[str] = []
    direct_url = _first_payload_string(
        payload,
        ("status_url", "statusUrl", "status_endpoint", "statusEndpoint", "polling_url", "pollingUrl"),
    )
    if direct_url:
        urls.append(urllib.parse.urljoin(base_url.rstrip("/") + "/", direct_url))
    task_id = _first_payload_string(payload, ("task_id", "taskId", "job_id", "jobId"))
    if task_id:
        for path in (
            f"v1/tasks/{task_id}",
            f"v1/images/generations/{task_id}",
            f"v1/images/tasks/{task_id}",
            f"v1/tasks/{task_id}/result",
        ):
            urls.append(_api_url(base_url, path))
    return list(dict.fromkeys(urls))


def _poll_image_task(base_url: str, api_key: str, payload: Any) -> Any:
    urls = _candidate_status_urls(base_url, payload)
    if not urls:
        return payload

    deadline = time.monotonic() + _bounded_env_int("IMAGE2_POLL_TIMEOUT_SECONDS", 360, 30, 900)
    interval = _bounded_env_int("IMAGE2_POLL_INTERVAL_SECONDS", 5, 1, 30)
    active_urls = urls
    first_round = True
    last_detail = ""
    while time.monotonic() < deadline:
        supported_urls: list[str] = []
        for url in active_urls:
            request = urllib.request.Request(url, method="GET", headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                "User-Agent": "codex-image2-api-generator/1.0",
            })
            try:
                with urllib.request.urlopen(request, timeout=45) as response:
                    raw = response.read().decode("utf-8", errors="replace")
                current = json.loads(raw)
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    last_detail = f"status endpoint not found: {url}"
                    continue
                detail = _http_error_detail(exc)
                suffix = f": {detail}" if detail else ""
                raise RuntimeError(f"Image2 task status failed with HTTP {exc.code}{suffix}") from exc
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise RuntimeError("Image2 task status returned invalid JSON") from exc
            except Exception as exc:
                raise RuntimeError(f"Image2 task status failed: {exc}") from exc

            supported_urls.append(url)
            if _extract_image_source(current)[0]:
                return current
            status = _first_payload_string(current, ("status", "state", "task_status", "taskStatus")).lower()
            if status in FAILED_TASK_STATUSES:
                raise RuntimeError(f"Image2 task failed with status {status}")
            last_detail = raw[:500]

        if first_round and not supported_urls:
            raise RuntimeError(last_detail or "Image2 task status endpoint is unavailable")
        if supported_urls:
            active_urls = supported_urls
        first_round = False
        time.sleep(interval)

    raise RuntimeError(f"Image2 task polling timed out: {last_detail or 'no image result'}")


def _download_image(image_url: str, api_key: str) -> bytes:
    headers = {"User-Agent": "codex-image2-api-generator/1.0"}
    for attempt in range(2):
        if attempt:
            headers["Authorization"] = f"Bearer {api_key}"
        request = urllib.request.Request(image_url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read()
        except urllib.error.HTTPError:
            if attempt == 0:
                continue
            raise
    return b""


def portrait_prompt(profile: dict[str, Any]) -> str:
    analysis = profile.get("aiAnalysis") if isinstance(profile.get("aiAnalysis"), dict) else {}
    return (
        "Create one square 3D stylized illustration avatar for a Chinese traditional medicine learner. "
        "This is a non-identifying fictional learning persona, not a photorealistic person. "
        "Friendly university student bust portrait, intelligent expression, subtle glasses, short dark hair, "
        "deep green and warm ivory student clothing with a subtle botanical pattern, soft off-white studio background, "
        "clean rounded-square composition, premium educational dashboard visual, no text, no logo, no watermark. "
        f"Learning direction: {_profile_text(profile, '专业/课程背景') or 'traditional Chinese medicine'}. "
        f"Learning style: {analysis.get('learningStyle') or _profile_text(profile, '学习风格/认知偏好') or 'case-based study'}. "
        f"Goals: {_profile_text(profile, '学习目标') or 'TCM theory and case analysis'}. "
        f"Focus areas: {_profile_text(profile, '薄弱知识点') or 'syndrome differentiation and formula reasoning'}."
    )


def generate_profile_portrait(
    profile: dict[str, Any],
    report_id: int,
    *,
    force: bool = False,
) -> dict[str, Any]:
    PORTRAIT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"profile-{int(report_id)}.png"
    output_path = PORTRAIT_DIR / filename
    if not force and output_path.exists() and output_path.stat().st_size > 1024:
        image_bytes = output_path.read_bytes()
        if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return {"imageBytes": image_bytes, "mimeType": "image/png", "source": "filesystem-cache"}

    base_url, api_key, model = _image2_settings()
    if not base_url or not api_key:
        raise RuntimeError("Image2 service is not configured on the server")
    endpoint = _api_url(base_url, "v1/images/generations")
    body = json.dumps({
        "model": model,
        "prompt": portrait_prompt(profile),
        "size": "1:1",
        "resolution": "2K",
        "n": 1,
        "watermark": False,
    }, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(endpoint, data=body, method="POST", headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "codex-image2-api-generator/1.0",
    })
    payload: dict[str, Any] = {}
    max_attempts = _max_request_attempts()
    for attempt in range(1, max_attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            detail = _http_error_detail(exc)
            suffix = f": {detail}" if detail else ""
            message = f"Image2 request failed with HTTP {exc.code}{suffix}"
            if exc.code not in RETRYABLE_HTTP_CODES or attempt >= max_attempts:
                raise RuntimeError(message) from exc
        except Exception as exc:
            if attempt >= max_attempts:
                raise RuntimeError(f"Image2 request failed: {exc}") from exc
        time.sleep(min(2 ** (attempt - 1), 4))

    source_kind, source_value = _extract_image_source(payload)
    if not source_kind:
        payload = _poll_image_task(base_url, api_key, payload)
        source_kind, source_value = _extract_image_source(payload)
    if source_kind == "b64":
        image_bytes = base64.b64decode(source_value)
    else:
        if source_kind != "url" or not source_value:
            raise RuntimeError("Image2 did not return portrait image data")
        image_bytes = _download_image(source_value, api_key)
    if len(image_bytes) < 1024 or not image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("Image2 returned invalid PNG portrait data")
    output_path.write_bytes(image_bytes)
    return {"imageBytes": image_bytes, "mimeType": "image/png", "source": "image2"}
