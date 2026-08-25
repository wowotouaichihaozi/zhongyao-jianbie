from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import re
import time
import urllib.request
import urllib.error
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import httpx
from pydantic import BaseModel, Field

LOCAL_BACKEND_ENV = Path(__file__).resolve().with_name(".env")
if LOCAL_BACKEND_ENV.exists():
    load_dotenv(LOCAL_BACKEND_ENV, override=False)

ROOT_BACKEND_ENV = Path(__file__).resolve().parents[2] / "backend" / ".env"
if ROOT_BACKEND_ENV.exists():
    load_dotenv(ROOT_BACKEND_ENV, override=False)

DEFAULT_ANTHROPIC_BASE_URL = "https://maas-coding-api.cn-huabei-1.xf-yun.com/anthropic"
DEFAULT_OPENAI_BASE_URL = "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2"
DEFAULT_ANTHROPIC_AUTH_TOKEN = ""
DEFAULT_ANTHROPIC_MODEL = "astron-code-latest"

ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", DEFAULT_ANTHROPIC_BASE_URL).rstrip("/")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL).rstrip("/")
ANTHROPIC_AUTH_TOKEN = os.getenv("ANTHROPIC_AUTH_TOKEN", DEFAULT_ANTHROPIC_AUTH_TOKEN)
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL)
LLM_PROTOCOL = os.getenv("LLM_PROTOCOL", "auto").strip().lower() or "auto"
OHMYPPT_INTERNAL_TOKEN = os.getenv("OHMYPPT_INTERNAL_TOKEN", "").strip() or ANTHROPIC_AUTH_TOKEN
ALLOW_LOCAL_BROWSER_DEFAULT = os.getenv("OHMYPPT_ALLOW_LOCAL_BROWSER_DEFAULT", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
ALLOWED_RUNTIME_HOSTS = {
    item.strip().lower()
    for item in os.getenv(
        "AGENT_RUNTIME_ALLOWED_HOSTS",
        "maas-coding-api.cn-huabei-1.xf-yun.com,localhost,127.0.0.1",
    ).split(",")
    if item.strip()
}

app = FastAPI(title="Oh My PPT H5 Backend", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    sessionId: str
    topic: str = "Untitled"
    pageCount: int = Field(default=5, ge=1, le=20)
    userMessage: str = ""
    styleName: str | None = None
    styleDescription: str | None = None
    styleSkill: str | None = None
    knowledgeContext: str = Field(default="", max_length=20000)


class GeneratedPage(BaseModel):
    pageNumber: int
    title: str
    contentOutline: str = ""
    html: str


class GenerateResponse(BaseModel):
    sessionId: str
    title: str
    pages: list[GeneratedPage]


@app.get("/api/health")
def health(response: Response) -> dict[str, Any]:
    ready = bool(ANTHROPIC_AUTH_TOKEN and OHMYPPT_INTERNAL_TOKEN)
    if not ready:
        response.status_code = 503
    return {
        "ok": ready,
        "version": app.version,
        "protocol": LLM_PROTOCOL,
        "model": ANTHROPIC_MODEL,
        "hasToken": bool(ANTHROPIC_AUTH_TOKEN),
    }


@app.post("/api/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest, request: Request) -> GenerateResponse:
    runtime = await runtime_from_request(request, req.sessionId)
    raw_pages = await call_llm(req, runtime)

    pages: list[GeneratedPage] = []
    for index, page in enumerate(raw_pages[: req.pageCount]):
        page_number = index + 1
        title = repair_text(str(page.get("title") or f"Page {page_number}"))
        outline = repair_text(str(page.get("contentOutline") or page.get("b") or ""))
        body = repair_text(str(page.get("h") or page.get("html") or page.get("bodyHtml") or ""))
        pages.append(
            GeneratedPage(
                pageNumber=page_number,
                title=title,
                contentOutline=outline,
                html=make_slide(body, title, page_number),
            )
        )

    if len(pages) < req.pageCount:
        raise HTTPException(
            status_code=502,
            detail=f"Model returned {len(pages)}/{req.pageCount} parseable slides.",
        )

    return GenerateResponse(sessionId=req.sessionId, title=repair_text(req.topic), pages=pages)


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

def call_llm_sync(url: str, headers: dict, payload: dict, timeout: int = 300) -> dict:
    """Use urllib to avoid httpx proxy issues."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=timeout) as resp:
        raw = resp.read()
        charset = resp.headers.get_content_charset() or "utf-8"
        try:
            text = raw.decode(charset)
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="replace")
        return repair_json_text(json.loads(text))


def repair_text(value: str) -> str:
    """Repair common UTF-8 bytes that were decoded as Latin-1 by model gateways."""
    if not value:
        return value
    suspicious = (
        "\u00c3",
        "\u00c2",
        "\u00f0",
        "\u00e6",
        "\u00e8",
        "\u00e9",
        "\u00e4",
        "\u00e5",
        "\u00e7",
        "\u00ef",
    )
    if not any(marker in value for marker in suspicious):
        return value
    try:
        repaired = value.encode("latin1").decode("utf-8")
    except UnicodeError:
        return value
    return repaired if repaired.count("\ufffd") <= value.count("\ufffd") else value


def repair_json_text(value: Any) -> Any:
    if isinstance(value, str):
        return repair_text(value)
    if isinstance(value, list):
        return [repair_json_text(item) for item in value]
    if isinstance(value, dict):
        return {key: repair_json_text(item) for key, item in value.items()}
    return value


def _allowed_runtime_host(hostname: str) -> bool:
    host = str(hostname or "").strip().lower()
    return any(host == allowed or host.endswith(f".{allowed}") for allowed in ALLOWED_RUNTIME_HOSTS)


def _validate_runtime_base_url(base_url: str) -> str:
    cleaned = str(base_url or "").strip().rstrip("/")
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=400, detail="Invalid model runtime URL.")
    if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise HTTPException(status_code=400, detail="Non-local model runtime must use HTTPS.")
    if parsed.username or parsed.password or parsed.fragment or not _allowed_runtime_host(parsed.hostname):
        raise HTTPException(status_code=400, detail="Model runtime URL is not allowed.")
    return cleaned


def signed_runtime_from_headers(request: Request, session_id: str) -> dict[str, str]:
    if not OHMYPPT_INTERNAL_TOKEN:
        raise HTTPException(status_code=503, detail="OhMyPPT internal authentication is not configured.")
    timestamp = str(request.headers.get("x-ohmyppt-timestamp") or "").strip()
    signed_session = str(request.headers.get("x-ohmyppt-session") or "").strip()
    protocol = str(request.headers.get("x-ohmyppt-protocol") or "auto").strip().lower()
    base_url = str(request.headers.get("x-ohmyppt-base-url") or "").strip().rstrip("/")
    model = str(request.headers.get("x-ohmyppt-model") or "").strip()
    signature = str(request.headers.get("x-ohmyppt-signature") or "").strip().lower()
    try:
        timestamp_number = int(timestamp)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid OhMyPPT request signature.") from exc
    if abs(int(time.time()) - timestamp_number) > 300 or signed_session != session_id:
        raise HTTPException(status_code=401, detail="Expired or mismatched OhMyPPT request signature.")
    if protocol not in {"auto", "openai", "anthropic"}:
        raise HTTPException(status_code=400, detail="Unsupported model protocol.")
    if not re.fullmatch(r"[A-Za-z0-9._:/-]{1,100}", model):
        raise HTTPException(status_code=400, detail="Invalid model identifier.")
    base_url = _validate_runtime_base_url(base_url)
    canonical = "\n".join([timestamp, signed_session, protocol, base_url, model])
    expected = hmac.new(
        OHMYPPT_INTERNAL_TOKEN.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not signature or not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid OhMyPPT request signature.")
    if protocol == "auto":
        protocol = "openai" if re.search(r"/(?:v1|v2)(?:/|$)", base_url, flags=re.I) else "anthropic"
    return {"protocol": protocol, "baseUrl": base_url, "model": model}


def _is_loopback_host(hostname: str | None) -> bool:
    return str(hostname or "").strip().lower() in {"127.0.0.1", "::1", "localhost"}


def server_default_runtime() -> dict[str, str]:
    protocol = LLM_PROTOCOL if LLM_PROTOCOL in {"auto", "openai", "anthropic"} else "auto"
    base_url = OPENAI_BASE_URL if protocol == "openai" else ANTHROPIC_BASE_URL
    if protocol == "auto":
        protocol = "openai" if re.search(r"/(?:v1|v2)(?:/|$)", base_url, flags=re.I) else "anthropic"
    return {"protocol": protocol, "baseUrl": base_url, "model": ANTHROPIC_MODEL}


def local_browser_default_runtime(request: Request) -> dict[str, str]:
    """Allow the standalone Vite page to use only the server-held default model."""
    origin = str(request.headers.get("origin") or "").strip()
    origin_host = urlparse(origin).hostname if origin else None
    client_host = request.client.host if request.client else None
    if not ALLOW_LOCAL_BROWSER_DEFAULT or not (
        _is_loopback_host(origin_host) and _is_loopback_host(client_host)
    ):
        raise HTTPException(status_code=401, detail="OhMyPPT request signature is required.")
    return server_default_runtime()


async def authenticated_browser_default_runtime(request: Request) -> dict[str, str]:
    """Validate the main-site session before allowing browser-side generation."""
    authorization = str(request.headers.get("authorization") or "").strip()
    cookie = str(request.headers.get("cookie") or "").strip()
    if not authorization and not cookie:
        raise HTTPException(status_code=401, detail="Please sign in before generating a PPT.")

    headers: dict[str, str] = {}
    if authorization:
        headers["authorization"] = authorization
    if cookie:
        headers["cookie"] = cookie
    try:
        async with httpx.AsyncClient(timeout=5.0, trust_env=False) as client:
            response = await client.get("http://127.0.0.1:3000/api/auth/me", headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="User authentication service is unavailable.") from exc
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="The main-site login session is invalid or expired.")
    try:
        user = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="User authentication returned invalid data.") from exc
    if not user.get("id"):
        raise HTTPException(status_code=401, detail="The main-site login session is invalid or expired.")
    return server_default_runtime()


async def runtime_from_request(request: Request, session_id: str) -> dict[str, str]:
    if request.headers.get("x-ohmyppt-signature"):
        return signed_runtime_from_headers(request, session_id)
    origin = str(request.headers.get("origin") or "").strip()
    origin_host = urlparse(origin).hostname if origin else None
    client_host = request.client.host if request.client else None
    if ALLOW_LOCAL_BROWSER_DEFAULT and _is_loopback_host(origin_host) and _is_loopback_host(client_host):
        return server_default_runtime()
    return await authenticated_browser_default_runtime(request)


def _anthropic_messages_url(base_url: str) -> str:
    cleaned = base_url.rstrip("/")
    lowered = cleaned.lower()
    if lowered.endswith("/v1/messages") or lowered.endswith("/messages"):
        return cleaned
    if lowered.endswith("/v1"):
        return f"{cleaned}/messages"
    return f"{cleaned}/v1/messages"


def _openai_chat_url(base_url: str) -> str:
    cleaned = base_url.rstrip("/")
    if cleaned.lower().endswith("/chat/completions"):
        return cleaned
    return f"{cleaned}/chat/completions"


def _style_prompt(req: GenerateRequest) -> str:
    style_parts = []
    if req.styleName:
        style_parts.append(f"Style name: {req.styleName}")
    if req.styleDescription:
        style_parts.append(f"Style description: {req.styleDescription}")
    if req.styleSkill:
        style_parts.append(f"Style rules: {req.styleSkill}")
    return "\n".join(style_parts)


def _batch_prompt(req: GenerateRequest, start_page: int, page_count: int) -> str:
    end_page = start_page + page_count - 1
    style_text = _style_prompt(req)
    position_rules = []
    if start_page == 1:
        position_rules.append("- Slide 1 is the opening/cover page; do not repeat a cover later in this batch.")
    else:
        position_rules.append("- This is a continuation batch; do not create another cover page.")
    if end_page == req.pageCount:
        position_rules.append(f"- Slide {req.pageCount} must close the deck with a useful summary or next action.")
    position_text = "\n".join(position_rules)

    return f"""Generate slides {start_page}-{end_page} of a {req.pageCount}-slide deck about: {req.topic}.

Generate exactly {page_count} visually rich 16:9 HTML slides for this batch only. Keep the batch coherent with the full deck and avoid repeating content assigned to other pages.

For EACH slide, output in this EXACT format (separated by ---):

SLIDE_TITLE: [title here]
SLIDE_OUTLINE: [one sentence outline]
SLIDE_HTML: [complete slide BODY fragment, including optional <style>]

---

SLIDE_TITLE: [next slide title]
...

Rules:
- This batch represents full-deck slide numbers {start_page}-{end_page}; preserve that narrative position.
{position_text}
- Create modern presentation design, not plain document pages.
- Each slide must fill a 1600x900 canvas and should feel like a polished PPT page.
- Use layout variety across slides: hero page, comparison cards, process/timeline, diagram, table/dashboard, summary.
- Use visual hierarchy: large titles, strong spacing, cards, badges, accent blocks, subtle backgrounds, icons made with text/emoji/simple CSS shapes when helpful.
- Use CSS freely inside SLIDE_HTML with a <style> tag scoped to the slide, plus class names and inline style attributes as needed.
- Keep each SLIDE_HTML body fragment under 4500 characters; prefer compact CSS and reuse the wrapper's typography/card styles.
- Do not use external images, external fonts, external scripts, iframes, videos, or network resources.
- Do not output <html>, <head>, <body>, or <script> tags. The app will wrap the slide.
- Add animation markers to important elements:
  - data-anim="fade-up" for titles/cards
  - data-anim="slide-left" or data-anim="slide-right" for diagrams/columns
  - data-anim="zoom" for key numbers/icons
  - data-anim-trigger="click" for 2-5 elements that should reveal step by step
  - optional data-anim-delay="120" in milliseconds
- Keep animations calm and professional; avoid flashing or shaking.
- Keep text concise but informative; avoid tiny dense paragraphs.
- Language: match the topic/user request language
- User request: {req.userMessage or "Create a clear, well-structured presentation."}
{style_text}
Grounding context (use only when relevant; do not invent citations):
{req.knowledgeContext or "No course knowledge context was supplied."}
Generate exactly {page_count} slide blocks and nothing else."""


def _response_text(data: dict[str, Any], protocol: str) -> str:
    if protocol == "openai":
        choices = data.get("choices") if isinstance(data.get("choices"), list) else []
        message = choices[0].get("message") if choices and isinstance(choices[0], dict) else {}
        return repair_text(str(message.get("content") or "")) if isinstance(message, dict) else ""

    for item in data.get("content", []):
        if isinstance(item, dict) and item.get("type") == "text":
            return repair_text(str(item.get("text") or ""))
    return ""


def _parse_model_pages(text: str) -> list[dict[str, Any]]:
    cleaned = clean_model_text(text)
    parsed_candidates = [
        parse_json_pages(cleaned),
        parse_sep(cleaned),
        extract_pages_regex(cleaned),
    ]
    return max((usable_pages(items) for items in parsed_candidates), key=len, default=[])


async def _generate_batch(
    req: GenerateRequest,
    *,
    start_page: int,
    page_count: int,
    url: str,
    headers: dict[str, str],
    protocol: str,
    model: str,
    request_timeout: int,
    attempts: int,
    semaphore: asyncio.Semaphore,
) -> tuple[int, list[dict[str, Any]]]:
    prompt = _batch_prompt(req, start_page, page_count)
    max_tokens = max(2800, min(9000, page_count * 2200 + 1200))
    payload: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": 0.5,
        "messages": [{"role": "user", "content": prompt}],
    }

    last_error = ""
    async with semaphore:
        for attempt in range(attempts):
            try:
                data = await asyncio.to_thread(call_llm_sync, url, headers, payload, request_timeout)
            except Exception as exc:
                last_error = str(exc) or exc.__class__.__name__
                continue

            text = _response_text(data, protocol)
            if not text:
                last_error = "Empty response"
                continue

            pages = _parse_model_pages(text)
            if len(pages) >= page_count:
                return start_page, pages[:page_count]

            last_error = f"Parsed {len(pages)}/{page_count} usable slides"
            payload["temperature"] = 0.2
            payload["messages"] = [{
                "role": "user",
                "content": prompt + f"""

FORMAT CORRECTION FOR RETRY {attempt + 2}:
- Your previous response was not parseable as exactly {page_count} slides.
- Output only the slide blocks. Do not add an introduction, explanation, JSON wrapper, or closing note.
- Every block must contain these three labels on separate lines: SLIDE_TITLE:, SLIDE_OUTLINE:, SLIDE_HTML:.
- Separate blocks with a line containing only ---.
- Start the response with SLIDE_TITLE: and generate exactly {page_count} complete blocks.""",
            }]

    end_page = start_page + page_count - 1
    raise RuntimeError(f"pages {start_page}-{end_page}: {last_error}")


async def call_llm(req: GenerateRequest, runtime: dict[str, str]) -> list[dict[str, Any]]:
    base_url = runtime["baseUrl"]
    api_key = ANTHROPIC_AUTH_TOKEN
    model = runtime["model"]
    protocol = runtime["protocol"]
    if not base_url or not api_key:
        raise HTTPException(status_code=400, detail="Missing base URL or API token.")

    url = _openai_chat_url(base_url) if protocol == "openai" else _anthropic_messages_url(base_url)
    headers = {
        "content-type": "application/json",
        "x-api-key": api_key,
        "authorization": f"Bearer {api_key}",
    }
    if protocol == "anthropic":
        headers["anthropic-version"] = "2023-06-01"

    try:
        request_timeout = max(30, min(600, int(os.getenv("OHMYPPT_LLM_TIMEOUT", "300"))))
    except (TypeError, ValueError):
        request_timeout = 300
    try:
        attempts = max(1, min(3, int(os.getenv("OHMYPPT_LLM_RETRIES", "2"))))
    except (TypeError, ValueError):
        attempts = 2
    try:
        batch_size = max(1, min(5, int(os.getenv("OHMYPPT_LLM_BATCH_SIZE", "3"))))
    except (TypeError, ValueError):
        batch_size = 3
    try:
        max_parallel = max(1, min(3, int(os.getenv("OHMYPPT_LLM_MAX_PARALLEL", "2"))))
    except (TypeError, ValueError):
        max_parallel = 2

    batches = [
        (start_page, min(batch_size, req.pageCount - start_page + 1))
        for start_page in range(1, req.pageCount + 1, batch_size)
    ]
    semaphore = asyncio.Semaphore(max_parallel)
    results = await asyncio.gather(
        *(
            _generate_batch(
                req,
                start_page=start_page,
                page_count=page_count,
                url=url,
                headers=headers,
                protocol=protocol,
                model=model,
                request_timeout=request_timeout,
                attempts=attempts,
                semaphore=semaphore,
            )
            for start_page, page_count in batches
        ),
        return_exceptions=True,
    )

    failures = [str(result) for result in results if isinstance(result, BaseException)]
    if failures:
        raise HTTPException(status_code=502, detail=f"PPT batch generation failed: {'; '.join(failures)}")

    ordered_results = sorted(
        (result for result in results if isinstance(result, tuple)),
        key=lambda item: item[0],
    )
    pages = [page for _, batch_pages in ordered_results for page in batch_pages]
    if len(pages) != req.pageCount:
        raise HTTPException(
            status_code=502,
            detail=f"PPT batch merge returned {len(pages)}/{req.pageCount} slides.",
        )
    return pages


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

TITLE_FIELD_RE = re.compile(
    r"^[ \t]*(?:#{1,6}[ \t]*)?(?:[-*][ \t]+)?(?:\*\*|__)?[ \t]*"
    r"(?:SLIDE[\s_-]*TITLE|PAGE[\s_-]*TITLE|TITLE|幻灯片标题|页面标题|页标题|标题)"
    r"[ \t]*(?:\*\*|__)?[ \t]*[:：][ \t]*(?:\*\*|__)?[ \t]*(.*?)[ \t]*(?:\*\*|__)?[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
OUTLINE_FIELD_RE = re.compile(
    r"^[ \t]*(?:#{1,6}[ \t]*)?(?:[-*][ \t]+)?(?:\*\*|__)?[ \t]*"
    r"(?:SLIDE[\s_-]*OUTLINE|PAGE[\s_-]*OUTLINE|CONTENT[\s_-]*OUTLINE|OUTLINE|幻灯片大纲|页面大纲|内容大纲|大纲|摘要)"
    r"[ \t]*(?:\*\*|__)?[ \t]*[:：][ \t]*(?:\*\*|__)?[ \t]*(.*?)[ \t]*(?:\*\*|__)?[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
HTML_FIELD_RE = re.compile(
    r"^[ \t]*(?:#{1,6}[ \t]*)?(?:[-*][ \t]+)?(?:\*\*|__)?[ \t]*"
    r"(?:SLIDE[\s_-]*HTML|PAGE[\s_-]*HTML|BODY[\s_-]*HTML|HTML|幻灯片HTML|页面HTML|正文HTML|页面内容)"
    r"[ \t]*(?:\*\*|__)?[ \t]*[:：][ \t]*(?:\*\*|__)?[ \t]*(.*?)[ \t]*(?:\*\*|__)?[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)


def clean_model_text(text: str) -> str:
    cleaned = repair_text(str(text or "")).strip()
    cleaned = re.sub(r"^```(?:json|html|markdown|md)?\s*\n?", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    return cleaned.strip()


def _strip_markdown_value(value: Any) -> str:
    text = repair_text(str(value or "")).strip()
    text = re.sub(r"^(?:\*\*|__)(.*?)(?:\*\*|__)$", r"\1", text).strip()
    return text


def _page_from_mapping(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    title = _strip_markdown_value(
        item.get("title") or item.get("slideTitle") or item.get("pageTitle") or item.get("标题")
    )
    outline = _strip_markdown_value(
        item.get("contentOutline") or item.get("outline") or item.get("b") or item.get("大纲")
    )
    html = repair_text(str(
        item.get("h") or item.get("html") or item.get("bodyHtml") or item.get("slideHtml") or item.get("页面HTML") or ""
    )).strip()
    if not title or not html:
        return None
    return {"title": title, "contentOutline": outline, "h": html}


def parse_json_pages(text: str) -> list[dict[str, Any]]:
    """Parse strict JSON responses before applying tolerant text extraction."""
    cleaned = clean_model_text(text)
    candidates = [cleaned]
    array_start, array_end = cleaned.find("["), cleaned.rfind("]")
    object_start, object_end = cleaned.find("{"), cleaned.rfind("}")
    if 0 <= array_start < array_end:
        candidates.append(cleaned[array_start : array_end + 1])
    if 0 <= object_start < object_end:
        candidates.append(cleaned[object_start : object_end + 1])

    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            payload = payload.get("pages") or payload.get("slides") or payload.get("data") or []
            if isinstance(payload, dict):
                payload = payload.get("pages") or payload.get("slides") or []
        if not isinstance(payload, list):
            continue
        pages = [page for page in (_page_from_mapping(item) for item in payload) if page]
        if pages:
            return pages
    return []


def usable_pages(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Reject empty or non-HTML pages before the API can report success."""
    usable: list[dict[str, Any]] = []
    for page in pages or []:
        normalized = _page_from_mapping(page)
        if not normalized:
            continue
        html = normalized["h"]
        if len(html) < 24 or not re.search(r"<[a-z][^>]*>", html, flags=re.IGNORECASE):
            continue
        usable.append(normalized)
    return usable

def parse_sep(text: str) -> list[dict[str, Any]]:
    """Parse labelled slide blocks with English, Chinese, or Markdown labels."""
    text = clean_model_text(text)
    title_matches = list(TITLE_FIELD_RE.finditer(text))
    pages: list[dict[str, Any]] = []
    for index, title_match in enumerate(title_matches):
        block_end = title_matches[index + 1].start() if index + 1 < len(title_matches) else len(text)
        block = text[title_match.end() : block_end]
        outline_match = OUTLINE_FIELD_RE.search(block)
        html_match = HTML_FIELD_RE.search(block)
        if not html_match:
            continue
        inline_html = _strip_markdown_value(html_match.group(1))
        trailing_html = block[html_match.end() :]
        trailing_html = re.sub(r"(?m)^\s*```(?:html|xml)?\s*$", "", trailing_html, flags=re.IGNORECASE)
        trailing_html = re.sub(r"(?m)^\s*```\s*$", "", trailing_html)
        trailing_html = re.sub(r"\n?\s*---\s*$", "", trailing_html).strip()
        html = "\n".join(part for part in (inline_html, trailing_html) if part).strip()
        page = {
            "title": _strip_markdown_value(title_match.group(1)),
            "contentOutline": _strip_markdown_value(outline_match.group(1) if outline_match else ""),
            "h": repair_text(html),
        }
        if page["title"] and page["h"]:
            pages.append(page)
    return pages


def extract_pages_regex(text: str) -> list[dict[str, Any]]:
    """Extract page objects from JSON-like text using regex, ignoring malformed quotes."""
    text = repair_text(text)
    pages: list[dict[str, Any]] = []
    # Find each {...} block that contains "title"
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                block = text[start : i + 1]
                title_m = re.search(r'"title"\s*:\s*"([^"]*)"', block)
                if title_m:
                    # Try to get html/bodyHtml/h
                    html_m = re.search(r'"(?:html|bodyHtml|h)"\s*:\s*"((?:[^"\\]|\\.)*)"', block)
                    outline_m = re.search(r'"(?:contentOutline|b)"\s*:\s*"([^"]*)"', block)
                    pages.append({
                        "title": repair_text(title_m.group(1)),
                        "contentOutline": repair_text(outline_m.group(1) if outline_m else ""),
                        "h": repair_text(html_m.group(1).replace('\\"', '"').replace("\\n", "\n") if html_m else ""),
                    })
                start = -1
    return pages


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

def make_slide(body_html: str, title: str, page_number: int = 1) -> str:
    body_html = re.sub(r"<script[\s\S]*?</script>", "", body_html, flags=re.IGNORECASE)
    body_html = re.sub(r"<!doctype[^>]*>", "", body_html, flags=re.IGNORECASE)
    body_html = re.sub(r"</?(?:html|head|body)[^>]*>", "", body_html, flags=re.IGNORECASE)
    body_html = re.sub(r"<\s*(?:iframe|object|embed|base|meta|video|audio)\b[^>]*>[\s\S]*?<\s*/\s*(?:iframe|object|embed|video|audio)\s*>", "", body_html, flags=re.IGNORECASE)
    body_html = re.sub(r"<\s*(?:iframe|object|embed|base|meta|video|audio)\b[^>]*?/?>", "", body_html, flags=re.IGNORECASE)
    body_html = re.sub(r"\s+on[a-z]+\s*=\s*(['\"]).*?\1", "", body_html, flags=re.IGNORECASE | re.DOTALL)
    body_html = re.sub(r"\s+(?:src|href)\s*=\s*(['\"])\s*(?:https?:|//|javascript:).*?\1", "", body_html, flags=re.IGNORECASE | re.DOTALL)
    body_html = re.sub(r"url\(\s*(['\"]?)\s*(?:https?:|//|javascript:)[^)]+\)", "none", body_html, flags=re.IGNORECASE)
    safe_title = escape(title)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{safe_title}</title>
<style>
*{{box-sizing:border-box}}
html,body{{margin:0;width:100%;height:100%;background:#111827;font-family:'Inter','Segoe UI','PingFang SC','Microsoft YaHei',system-ui,sans-serif;color:#172033;overflow:hidden}}
body{{display:grid;place-items:center}}
.slide.ppt-page-root{{width:1600px;height:900px;position:relative;overflow:hidden;background:
  linear-gradient(135deg,#ffffff 0%,#f7fffb 52%,#edf9f3 100%);
  padding:72px 86px;box-shadow:0 32px 80px rgba(15,23,42,.28)}}
.slide.ppt-page-root::before{{content:'';position:absolute;inset:28px;border:1px solid rgba(33,185,120,.14);border-radius:28px;pointer-events:none}}
.slide.ppt-page-root::after{{content:'';position:absolute;left:0;right:0;bottom:0;height:7px;background:linear-gradient(90deg,#21b978,#58d89c,#a7e6c8);pointer-events:none}}
.slide h1{{margin:0 0 26px;font-size:64px;line-height:1.05;font-weight:850;letter-spacing:0;color:#111827}}
.slide h2{{margin:0 0 18px;font-size:38px;line-height:1.12;font-weight:780;color:#18213a}}
.slide h3{{margin:0 0 12px;font-size:27px;line-height:1.18;font-weight:740;color:#24304f}}
.slide p{{margin:0 0 16px;font-size:24px;line-height:1.55;color:#44506a}}
.slide ul,.slide ol{{margin:0 0 16px 28px;font-size:22px;line-height:1.55;color:#44506a}}
.slide li{{margin-bottom:9px}}
.slide table{{width:100%;border-collapse:separate;border-spacing:0;margin:18px 0;overflow:hidden;border-radius:18px;box-shadow:0 18px 45px rgba(15,23,42,.09)}}
.slide th,.slide td{{padding:16px 20px;border-bottom:1px solid rgba(148,163,184,.24);text-align:left;font-size:20px}}
.slide th{{background:linear-gradient(135deg,#eef9f4,#e1f5eb);font-weight:760;color:#1f2a44}}
.slide strong{{color:#111827;font-weight:800}}
.slide pre{{background:#111827;color:#e5e7eb;padding:22px;border-radius:18px;margin:16px 0;overflow:hidden;box-shadow:0 20px 45px rgba(15,23,42,.18)}}
.slide code{{font-family:'Cascadia Code','Fira Code',Consolas,monospace;font-size:17px}}
.page-num{{position:absolute;right:46px;bottom:28px;color:rgba(71,85,105,.44);font-size:17px;z-index:30}}
.ppt-h5-card{{border-radius:24px;background:rgba(255,255,255,.78);box-shadow:0 22px 56px rgba(15,23,42,.11);border:1px solid rgba(148,163,184,.22);backdrop-filter:blur(12px)}}
[data-anim]{{opacity:0;transform:translate3d(0,22px,0);will-change:opacity,transform,filter}}
[data-anim].ppt-anim-in{{opacity:1;transform:translate3d(0,0,0);filter:none;transition:opacity .68s cubic-bezier(.22,.8,.28,1),transform .68s cubic-bezier(.22,.8,.28,1),filter .68s ease}}
[data-anim="fade"]{{transform:none}}
[data-anim="fade-up"]{{transform:translate3d(0,28px,0)}}
[data-anim="slide-left"]{{transform:translate3d(48px,0,0)}}
[data-anim="slide-right"]{{transform:translate3d(-48px,0,0)}}
[data-anim="zoom"]{{transform:scale(.86);filter:blur(2px)}}
[data-anim="flip"]{{transform:perspective(800px) rotateX(8deg) translateY(18px)}}
[data-anim-trigger="click"]:not(.ppt-anim-in){{opacity:0;transform:translate3d(0,24px,0)}}
@media (prefers-reduced-motion: reduce){{[data-anim]{{opacity:1!important;transform:none!important;transition:none!important;filter:none!important}}}}
</style>
</head>
<body>
<div class="slide ppt-page-root" data-page-id="page-{page_number}" data-ppt-guard-root="1">
{body_html}
<div class="page-num">{page_number}</div>
</div>
<script>
(() => {{
  const nodes = Array.from(document.querySelectorAll('[data-anim]'));
  const autoNodes = nodes.filter((node) => node.getAttribute('data-anim-trigger') !== 'click');
  const clickNodes = nodes.filter((node) => node.getAttribute('data-anim-trigger') === 'click');
  const reveal = (node, index = 0) => {{
    const explicit = Number(node.getAttribute('data-anim-delay') || '');
    const delay = Number.isFinite(explicit) ? explicit : Math.min(index * 110, 720);
    window.setTimeout(() => node.classList.add('ppt-anim-in'), delay);
  }};
  const start = () => {{
    if (!nodes.length) {{
      Array.from(document.querySelectorAll('.slide > *:not(style):not(script):not(.page-num)'))
        .slice(0, 12)
        .forEach((node, index) => {{
          node.setAttribute('data-anim', index === 0 ? 'slide-right' : 'fade-up');
          reveal(node, index);
        }});
      return;
    }}
    autoNodes.forEach(reveal);
  }};
  let clickIndex = 0;
  const advance = () => {{
    if (clickIndex >= clickNodes.length) return false;
    reveal(clickNodes[clickIndex], 0);
    clickIndex += 1;
    return true;
  }};
  document.addEventListener('click', () => advance());
  document.addEventListener('keydown', (event) => {{
    if ([' ', 'ArrowRight', 'ArrowDown', 'PageDown', 'Enter'].includes(event.key) && advance()) {{
      event.preventDefault();
    }}
  }});
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
}})();
</script>
</body>
</html>"""


def fallback_slide(title: str, page_number: int) -> str:
    safe_title = escape(title)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<style>
html,body{{margin:0;width:100%;height:100%;background:#eef2e8;font-family:system-ui,sans-serif}}
.slide{{width:1600px;height:900px;margin:0 auto;display:grid;place-items:center;background:linear-gradient(135deg,#f8f5ec,#d8e8cf);color:#30402b}}
h1{{font-size:72px;max-width:1100px;text-align:center}}
</style>
</head>
<body>
<div class="slide" data-page-id="page-{page_number}" data-ppt-guard-root="1">
<h1>{safe_title}</h1>
</div>
</body>
</html>"""
