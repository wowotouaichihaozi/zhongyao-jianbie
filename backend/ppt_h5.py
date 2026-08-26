from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from html import escape
from typing import Any, Callable

try:
    from common import build_anthropic_messages_url, create_llm_headers, get_setting
    from api_config import setting_default
    from course_knowledge import grounded_prompt_block
    from ohmyppt_client import generate_with_ohmyppt, ohmyppt_health
except ImportError:  # pragma: no cover
    from .common import build_anthropic_messages_url, create_llm_headers, get_setting
    from .api_config import setting_default
    from .course_knowledge import grounded_prompt_block
    from .ohmyppt_client import generate_with_ohmyppt, ohmyppt_health


PLATFORM_PPT_STYLE_PROMPT = """
Highest-priority platform style: make every slide look like the 嵌智学航 platform.
- Overall tone: clean, bright, professional education-tech UI. Use pure white or very pale gray/mint backgrounds, generous whitespace, and calm information density.
- Palette: primary text #1F2937 / #172033, secondary text #64748B, main brand green #21B978, light green #58D89C, soft mint surfaces #F7FFFC / #EEF9F4. Use neutral gray as the base and green only for titles, section markers, key numbers, icons, progress bars, and active states.
- Layout: modular full-slide sections, left-aligned or centered content, clear hierarchy through size/weight/spacing. Prefer white cards with subtle mint borders, thin dividers, compact dashboards, learning-platform panels, timelines, metric blocks, and outline icons.
- Typography: clean sans-serif, bold concise titles, readable body text, line-height at least 1.6 for paragraphs. Avoid cramped text and avoid tiny paragraphs.
- Motion cues: use ppth5-compatible data-anim attributes only when helpful. Preferred values are fade-up, fade-right, scale-in, slide-up, wipe, and zoom-in, with 400-650ms duration and ease-out. Use data-anim-trigger="click" only for step-by-step bullet/card reveals. The slide must still be fully readable without animation.
- Avoid: dark themes, dominant purple/blue/orange palettes, high-saturation colors, heavy gradients, big blurry decorative blobs, complex shadows, noisy backgrounds, and flashy transitions.
- If any selected template/style conflicts with these rules, prioritize this platform style.
"""


def ppt_h5_health() -> dict[str, Any]:
    return ohmyppt_health()


StageCallback = Callable[[dict[str, Any]], None]


def _emit_stage(on_stage: StageCallback | None, stage: str, message: str, progress: int, **extra: Any) -> None:
    if not on_stage:
        return
    try:
        on_stage({"stage": stage, "message": message, "progress": progress, **extra})
    except Exception:
        pass


def generate_ppt_h5(payload: dict[str, Any], on_stage: StageCallback | None = None) -> dict[str, Any]:
    session_id = str(payload.get("sessionId") or "").strip()
    topic = str(payload.get("topic") or "Untitled").strip() or "Untitled"
    user_message = str(payload.get("userMessage") or "").strip()
    page_count = _clamp_int(payload.get("pageCount"), 5, 1, 20)
    _emit_stage(on_stage, "prepare", "正在整理主题、页数和平台风格要求", 10, pageCount=page_count, topic=topic)
    knowledge_context, knowledge_sources = grounded_prompt_block(
        f"{topic} {user_message} 中医药课程 四诊 辨证 方药 医案",
        top_k=6,
        max_context_chars=10000,
    )
    _emit_stage(
        on_stage,
        "knowledge_retrieval",
        f"已从课程知识库检索到 {len(knowledge_sources)} 条可引用资料",
        14,
        knowledgeSourceCount=len(knowledge_sources),
    )

    request_data = {
        "sessionId": session_id,
        "topic": topic,
        "userMessage": user_message,
        "pageCount": page_count,
        "styleName": str(payload.get("styleName") or ""),
        "styleDescription": str(payload.get("styleDescription") or ""),
        "styleSkill": "\n\n".join(
            item
            for item in [PLATFORM_PPT_STYLE_PROMPT.strip(), str(payload.get("styleSkill") or "").strip()]
            if item
        ),
        "knowledgeContext": knowledge_context,
    }
    result = generate_with_ohmyppt(request_data, on_stage=on_stage)
    result["grounded"] = bool(knowledge_sources)
    result["knowledgeSources"] = knowledge_sources
    return result


def _clamp_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(maximum, number))


def _setting_int(name: str, default: int, minimum: int, maximum: int) -> int:
    return _clamp_int(get_setting(name, setting_default(name, str(default))), default, minimum, maximum)


def call_llm_sync(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
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
    if not value:
        return value
    suspicious = ("\u00c3", "\u00c2", "\u00f0", "\u00e6", "\u00e8", "\u00e9", "\u00e4", "\u00e5", "\u00e7", "\u00ef")
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


def _openai_chat_url(base_url: str) -> str:
    cleaned = str(base_url or "").strip().rstrip("/")
    if cleaned.endswith("/chat/completions"):
        return cleaned
    if cleaned.endswith("/v2") or cleaned.endswith("/v1"):
        return f"{cleaned}/chat/completions"
    return f"{cleaned}/v1/chat/completions"


def call_llm(req: dict[str, Any], on_stage: StageCallback | None = None) -> list[dict[str, Any]]:
    protocol = str(get_setting("LLM_PROTOCOL", "anthropic")).strip().lower()
    if protocol not in {"openai", "anthropic"}:
        protocol = "anthropic"
    default_base = (
        get_setting("OPENAI_BASE_URL", setting_default("OPENAI_BASE_URL"))
        if protocol == "openai"
        else get_setting("ANTHROPIC_BASE_URL", setting_default("ANTHROPIC_BASE_URL"))
    )
    base_url = str(default_base).rstrip("/")
    api_key = str(get_setting("ANTHROPIC_AUTH_TOKEN", setting_default("ANTHROPIC_AUTH_TOKEN")))
    model = str(get_setting("ANTHROPIC_MODEL", setting_default("ANTHROPIC_MODEL")) or "astron-code-latest")
    timeout = _setting_int("PPT_H5_LLM_TIMEOUT", 45, 10, 180)
    retries = _setting_int("PPT_H5_LLM_RETRIES", 2, 1, 5)
    if not base_url or not api_key:
        _emit_stage(on_stage, "fallback", "PPT model config is missing; using local template pages.", 80)
        return []
    _emit_stage(on_stage, "model_config", f"已读取模型配置：{model}", 18, model=model)

    style_parts = []
    if req.get("styleName"):
        style_parts.append(f"Style name: {req['styleName']}")
    if req.get("styleDescription"):
        style_parts.append(f"Style description: {req['styleDescription']}")
    if req.get("styleSkill"):
        style_parts.append(f"Style rules: {req['styleSkill']}")
    style_parts.append(PLATFORM_PPT_STYLE_PROMPT)
    style_text = "\n".join(style_parts)
    knowledge_context = str(req.get("knowledgeContext") or "").strip()

    prompt = f"""Generate exactly {req["pageCount"]} visually rich 16:9 HTML presentation slides about: {req["topic"]}.

For EACH slide, output in this EXACT format (separated by ---):

SLIDE_TITLE: [title here]
SLIDE_OUTLINE: [one sentence outline]
SLIDE_HTML: [complete slide BODY fragment, including optional <style>]

Rules:
- The final answer must contain exactly {req["pageCount"]} complete slide blocks.
- Do not stop early. Continue until SLIDE {req["pageCount"]} is fully written.
- Put a line containing only --- between slide blocks.
- Create modern presentation design, not plain document pages.
- Each slide must fill a 1600x900 canvas and should feel like a polished PPT page.
- Use layout variety across slides: hero page, comparison cards, process/timeline, diagram, table/dashboard, summary.
- Use visual hierarchy: large titles, strong spacing, cards, badges, accent blocks, subtle backgrounds, icons made with text/simple CSS shapes when helpful.
- Use CSS freely inside SLIDE_HTML with a <style> tag scoped to the slide.
- Do not use external images, external fonts, external scripts, iframes, videos, or network resources.
- Do not output <html>, <head>, <body>, or <script> tags.
- You may add ppth5-compatible animation markers: data-anim="fade|fade-up|fade-down|fade-left|fade-right|scale-in|slide-up|slide-left|fly-in|wipe|zoom-in|spin-in|grow-shrink|pulse" plus optional data-anim-trigger="click", data-anim-duration, data-anim-delay, and data-anim-from.
- Prefer gentle fade-up, fade-right, scale-in, slide-up, wipe, and zoom-in. Avoid unsupported values such as slide-right.
- The slide must be fully readable as static HTML before any script runs.
- Do not rely on delayed reveal, opacity:0, external assets, or runtime-only effects to show core text, diagrams, icons, or images.
- Keep text concise but informative; avoid tiny dense paragraphs.
- Language: match the topic/user request language.
- User request: {req.get("userMessage") or "Create a clear, well-structured presentation."}
- Course facts, definitions, procedures, parameters, and conclusions must be grounded in the course knowledge excerpts below.
- Put compact [KB1], [KB2] source markers beside important factual statements. If the excerpts do not support a specific fact, label it as requiring verification instead of inventing it.
{style_text}

COURSE KNOWLEDGE EXCERPTS:
{knowledge_context}

Generate exactly {req["pageCount"]} slides."""

    max_tokens = _setting_int("PPT_H5_MAX_TOKENS", 8192, 2048, 32000)
    max_tokens = max(max_tokens, min(32000, int(req["pageCount"]) * 2600 + 4096))
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": 0.7,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = create_llm_headers(api_key, anthropic=protocol == "anthropic")
    request_url = (
        _openai_chat_url(base_url)
        if protocol == "openai"
        else build_anthropic_messages_url(base_url)
    )
    _emit_stage(on_stage, "prompt_ready", "已构建 PPT 生成提示词，准备请求大模型", 24, maxTokens=max_tokens)

    last_error = ""
    best_pages: list[dict[str, Any]] = []
    for _attempt in range(retries):
        attempt = _attempt + 1
        try:
            _emit_stage(on_stage, "llm_request", f"正在调用大模型生成内容（第 {attempt}/3 次）", 34, attempt=attempt)
            data = call_llm_sync(request_url, headers, payload, timeout)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            last_error = str(exc)
            _emit_stage(on_stage, "llm_retry", f"本次模型请求失败，准备重试：{last_error}", 42, attempt=attempt)
            continue

        text = ""
        if protocol == "openai":
            message = ((data.get("choices") or [{}])[0].get("message") or {})
            content = message.get("content")
            if isinstance(content, list):
                text = "\n".join(
                    str(item.get("text") or item.get("content") or "")
                    for item in content
                    if isinstance(item, dict)
                )
            else:
                text = str(content or "")
            text = repair_text(text)
        else:
            for item in data.get("content", []):
                if isinstance(item, dict) and item.get("type") == "text":
                    text = repair_text(str(item.get("text") or ""))
                    break
        if not text:
            last_error = "Empty response"
            _emit_stage(on_stage, "llm_retry", "模型返回为空，准备重试", 50, attempt=attempt)
            continue

        _emit_stage(on_stage, "llm_response", f"模型已返回内容，正在解析 {req['pageCount']} 页结构", 70, attempt=attempt, textLength=len(text))
        text = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
        text = re.sub(r"\n?```\s*$", "", text.strip())
        pages = parse_sep(text) or extract_pages_regex(text)
        if len(pages) >= int(req["pageCount"]):
            _emit_stage(on_stage, "parse_success", f"已解析出 {len(pages)} 页幻灯片", 80, pageCount=len(pages))
            return pages
        if pages:
            if len(pages) > len(best_pages):
                best_pages = pages
            last_error = f"Only parsed {len(pages)}/{req['pageCount']} slides"
            _emit_stage(on_stage, "parse_retry", f"只解析到 {len(pages)}/{req['pageCount']} 页，准备重试", 76, attempt=attempt)
            continue
        last_error = "Parse failed"
        _emit_stage(on_stage, "parse_retry", "模型输出格式解析失败，准备重试", 76, attempt=attempt)

    if best_pages:
        _emit_stage(on_stage, "fallback", f"Model returned {len(best_pages)} pages; remaining pages will use local templates.", 80, pageCount=len(best_pages))
        return best_pages
    _emit_stage(on_stage, "fallback", f"Model unavailable; using local template pages. {last_error}", 80)
    return []


def fallback_title(topic: str, page_number: int, page_count: int) -> str:
    if page_number == 1:
        return topic
    if page_number == page_count:
        return "总结与行动建议"
    return f"{topic} 核心要点 {page_number}"


def make_fallback_body(topic: str, title: str, page_number: int, page_count: int) -> str:
    safe_topic = escape(repair_text(topic))
    safe_title = escape(repair_text(title))
    return f"""
<style>
.fallback-wrap{{height:100%;display:grid;grid-template-columns:1.05fr .95fr;gap:46px;align-items:center}}
.fallback-kicker{{display:inline-flex;padding:10px 18px;border-radius:999px;background:rgba(33,185,120,.12);color:#0e9f6e;font-size:20px;font-weight:800;margin-bottom:24px}}
.fallback-title{{font-size:66px;line-height:1.05;margin:0 0 24px;color:#172033}}
.fallback-lead{{font-size:26px;line-height:1.6;color:#53656a;max-width:760px}}
.fallback-panel{{padding:38px;border-radius:26px;background:rgba(255,255,255,.9);border:1px solid rgba(33,185,120,.16);box-shadow:0 20px 56px rgba(18,84,68,.08)}}
.fallback-item{{display:flex;gap:18px;padding:18px 0;border-bottom:1px solid rgba(148,163,184,.22)}}
.fallback-item:last-child{{border-bottom:0}}
.fallback-dot{{width:34px;height:34px;border-radius:12px;background:linear-gradient(135deg,#21B978,#58D89C);color:white;display:grid;place-items:center;font-weight:900;flex:0 0 auto}}
.fallback-item strong{{display:block;font-size:24px;margin-bottom:6px}}
.fallback-item span{{font-size:20px;color:#64748b;line-height:1.45}}
</style>
<section class="fallback-wrap">
  <div>
    <div class="fallback-kicker" data-anim="fade-up">P{page_number} / {page_count}</div>
    <h1 class="fallback-title" data-anim="fade-right">{safe_title}</h1>
    <p class="fallback-lead" data-anim="fade-up">这一页由系统根据主题自动补齐，用于保证完整导出。你可以继续编辑内容，或点击重新生成获得更细化的设计。</p>
  </div>
  <div class="fallback-panel">
    <div class="fallback-item" data-anim="fade-up" data-anim-trigger="click"><div class="fallback-dot">1</div><div><strong>主题聚焦</strong><span>围绕“{safe_topic}”保持结构完整。</span></div></div>
    <div class="fallback-item" data-anim="fade-up" data-anim-trigger="click"><div class="fallback-dot">2</div><div><strong>内容衔接</strong><span>承接前后页面，避免演示文稿中断。</span></div></div>
    <div class="fallback-item" data-anim="fade-up" data-anim-trigger="click"><div class="fallback-dot">3</div><div><strong>后续优化</strong><span>可在编辑器中替换为更具体的案例、流程或总结。</span></div></div>
  </div>
</section>
"""


def parse_sep(text: str) -> list[dict[str, Any]]:
    text = repair_text(text)
    parts = re.split(r"SLIDE_TITLE:\s*", text)
    pages: list[dict[str, Any]] = []
    for part in parts[1:]:
        title_m = re.match(r"(.+?)\n", part)
        outline_m = re.search(r"SLIDE_OUTLINE:\s*(.+?)\n", part)
        html_m = re.search(r"SLIDE_HTML:\s*(.+)", part, re.DOTALL)
        if title_m and outline_m and html_m:
            html = re.sub(r"\n---\s*$", "", html_m.group(1).strip()).strip()
            pages.append(
                {
                    "title": repair_text(title_m.group(1).strip()),
                    "contentOutline": repair_text(outline_m.group(1).strip()),
                    "h": repair_text(html),
                }
            )
    return pages


def extract_pages_regex(text: str) -> list[dict[str, Any]]:
    text = repair_text(text)
    pages: list[dict[str, Any]] = []
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
                    html_m = re.search(r'"(?:html|bodyHtml|h)"\s*:\s*"((?:[^"\\]|\\.)*)"', block)
                    outline_m = re.search(r'"(?:contentOutline|b)"\s*:\s*"([^"]*)"', block)
                    pages.append(
                        {
                            "title": repair_text(title_m.group(1)),
                            "contentOutline": repair_text(outline_m.group(1) if outline_m else ""),
                            "h": repair_text(html_m.group(1).replace('\\"', '"').replace("\\n", "\n") if html_m else ""),
                        }
                    )
                start = -1
    return pages


def make_slide(body_html: str, title: str, page_number: int = 1) -> str:
    body_html = re.sub(r"<script[\s\S]*?</script>", "", body_html, flags=re.IGNORECASE)
    body_html = re.sub(r"<!doctype[^>]*>", "", body_html, flags=re.IGNORECASE)
    body_html = re.sub(r"</?(?:html|head|body)[^>]*>", "", body_html, flags=re.IGNORECASE)
    safe_title = escape(title)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{safe_title}</title>
<style>
*{{box-sizing:border-box}}
html,body{{margin:0;width:100%;height:100%;background:#f4faf9;font-family:'Inter','Segoe UI','PingFang SC','Microsoft YaHei',system-ui,sans-serif;color:#172033;overflow:hidden}}
body{{display:grid;place-items:center}}
.slide.ppt-page-root{{width:1600px;height:900px;position:relative;overflow:hidden;background:radial-gradient(circle at 10% 12%,rgba(33,185,120,.12),transparent 30%),radial-gradient(circle at 90% 16%,rgba(88,216,156,.14),transparent 30%),linear-gradient(135deg,#ffffff 0%,#f7fffc 52%,#eef9f4 100%);padding:72px 86px;box-shadow:0 28px 72px rgba(18,84,68,.12)}}
.slide.ppt-page-root::before{{content:'';position:absolute;inset:28px;border:1px solid rgba(33,185,120,.13);border-radius:26px;pointer-events:none}}
.slide.ppt-page-root::after{{content:'';position:absolute;left:0;right:0;bottom:0;height:7px;background:linear-gradient(90deg,#21B978,#58D89C,#10B981);pointer-events:none}}
.slide h1{{margin:0 0 26px;font-size:64px;line-height:1.05;font-weight:850;letter-spacing:0;color:#172033}}
.slide h2{{margin:0 0 18px;font-size:38px;line-height:1.12;font-weight:780;color:#1F2937}}
.slide h3{{margin:0 0 12px;font-size:27px;line-height:1.18;font-weight:740;color:#25342f}}
.slide p{{margin:0 0 16px;font-size:24px;line-height:1.6;color:#53656a}}
.slide ul,.slide ol{{margin:0 0 16px 28px;font-size:22px;line-height:1.6;color:#53656a}}
.slide li{{margin-bottom:9px}}
.slide table{{width:100%;border-collapse:separate;border-spacing:0;margin:18px 0;overflow:hidden;border-radius:18px;box-shadow:0 16px 42px rgba(18,84,68,.08)}}
.slide th,.slide td{{padding:16px 20px;border-bottom:1px solid rgba(33,185,120,.14);text-align:left;font-size:20px}}
.slide th{{background:linear-gradient(135deg,#f1fbf7,#e4f8ee);font-weight:760;color:#1f2a24}}
.slide strong{{color:#172033;font-weight:800}}
.page-num{{position:absolute;right:46px;bottom:28px;color:rgba(71,85,105,.44);font-size:17px;z-index:30}}
.ppt-h5-card{{border-radius:22px;background:rgba(255,255,255,.9);box-shadow:0 20px 54px rgba(18,84,68,.08);border:1px solid rgba(33,185,120,.16);backdrop-filter:blur(12px)}}
[data-anim]{{opacity:1;transform:none;filter:none;clip-path:inset(0 0 0 0);will-change:opacity,transform,filter,clip-path}}
[data-anim].ppt-anim-ready{{opacity:0;transform:translate3d(0,24px,0);filter:none;clip-path:inset(0 0 0 0);transition:opacity var(--ppt-anim-duration,.52s) var(--ppt-anim-ease,cubic-bezier(.2,.86,.28,1)),transform var(--ppt-anim-duration,.52s) var(--ppt-anim-ease,cubic-bezier(.2,.86,.28,1)),filter var(--ppt-anim-duration,.52s) var(--ppt-anim-ease,cubic-bezier(.2,.86,.28,1)),clip-path var(--ppt-anim-duration,.52s) var(--ppt-anim-ease,cubic-bezier(.2,.86,.28,1))}}
[data-anim].ppt-anim-ready.ppt-anim-in{{opacity:1;transform:translate3d(0,0,0) scale(1) rotate(0deg);filter:none;clip-path:inset(0 0 0 0)}}
[data-anim="fade"].ppt-anim-ready{{transform:none}}
[data-anim="fade-up"].ppt-anim-ready{{transform:translate3d(0,24px,0)}}
[data-anim="fade-down"].ppt-anim-ready{{transform:translate3d(0,-24px,0)}}
[data-anim="fade-left"].ppt-anim-ready{{transform:translate3d(34px,0,0)}}
[data-anim="fade-right"].ppt-anim-ready{{transform:translate3d(-34px,0,0)}}
[data-anim="scale-in"].ppt-anim-ready{{transform:scale(.94)}}
[data-anim="slide-up"].ppt-anim-ready{{transform:translate3d(0,48px,0)}}
[data-anim="slide-left"].ppt-anim-ready{{transform:translate3d(58px,0,0)}}
[data-anim="fly-in"].ppt-anim-ready{{transform:translate3d(-76px,30px,0);filter:blur(4px)}}
[data-anim="wipe"].ppt-anim-ready{{opacity:1;transform:none;clip-path:inset(0 100% 0 0)}}
[data-anim="zoom-in"].ppt-anim-ready{{transform:scale(.86);filter:blur(2px)}}
[data-anim="spin-in"].ppt-anim-ready{{transform:scale(.9) rotate(-7deg)}}
[data-anim="grow-shrink"].ppt-anim-ready{{transform:scale(.82)}}
[data-anim="pulse"].ppt-anim-ready{{opacity:1;transform:none}}
[data-anim="pulse"].ppt-anim-ready.ppt-anim-in{{animation:pptDataPulse var(--ppt-anim-duration,.82s) ease-out both}}
[data-anim="exit-fade"].ppt-anim-ready,[data-anim="exit-fly"].ppt-anim-ready{{opacity:1;transform:none}}
[data-anim="exit-fade"].ppt-anim-ready.ppt-anim-in{{opacity:0}}
[data-anim="exit-fly"].ppt-anim-ready.ppt-anim-in{{opacity:0;transform:translate3d(64px,-20px,0)}}
[data-anim-from="left"].ppt-anim-ready{{transform:translate3d(-44px,0,0)}}
[data-anim-from="right"].ppt-anim-ready{{transform:translate3d(44px,0,0)}}
[data-anim-from="top"].ppt-anim-ready{{transform:translate3d(0,-44px,0)}}
[data-anim-from="bottom"].ppt-anim-ready{{transform:translate3d(0,44px,0)}}
[data-anim-from="center"].ppt-anim-ready{{transform:scale(.9)}}
@keyframes pptDataPulse{{0%{{transform:scale(.98)}}48%{{transform:scale(1.035)}}100%{{transform:scale(1)}}}}
@media (prefers-reduced-motion: reduce){{[data-anim]{{opacity:1!important;transform:none!important;transition:none!important;filter:none!important;clip-path:inset(0 0 0 0)!important;animation:none!important}}}}
</style>
</head>
<body>
<div class="slide ppt-page-root" data-page-id="page-{page_number}" data-ppt-guard-root="1">
{body_html}
<div class="page-num">{page_number}</div>
</div>
<script>
(() => {{
  const supported = new Set(['fade','fade-up','fade-down','fade-left','fade-right','scale-in','slide-up','slide-left','fly-in','wipe','zoom-in','spin-in','grow-shrink','pulse','exit-fade','exit-fly','path']);
  const aliases = new Map([['zoom','zoom-in'],['slide-right','fade-right'],['slide-down','fade-down'],['slide-in','slide-up']]);
  let nodes = Array.from(document.querySelectorAll('[data-anim]'));
  const normalizeType = (node) => {{
    let type = String(node.getAttribute('data-anim') || 'fade-up').trim();
    type = aliases.get(type) || type;
    if (!supported.has(type) || type === 'path') type = 'fade-up';
    node.setAttribute('data-anim', type);
    return type;
  }};
  const parseMs = (value, fallback, min = 80, max = 5000) => {{
    const raw = String(value || '').trim();
    if (!raw) return fallback;
    const numeric = Number(raw.replace(/ms|s/gi, ''));
    if (!Number.isFinite(numeric)) return fallback;
    const ms = /s$/i.test(raw) && !/ms$/i.test(raw) ? numeric * 1000 : numeric;
    return Math.max(min, Math.min(max, ms));
  }};
  const setupNode = (node) => {{
    normalizeType(node);
    const duration = parseMs(node.getAttribute('data-anim-duration'), 520, 120, 5000);
    const easing = node.getAttribute('data-anim-easing') || 'cubic-bezier(.2,.86,.28,1)';
    node.style.setProperty('--ppt-anim-duration', `${{duration}}ms`);
    node.style.setProperty('--ppt-anim-ease', easing);
    node.classList.add('ppt-anim-ready');
  }};
  const autoNodes = () => nodes.filter((node) => String(node.getAttribute('data-anim-trigger') || 'load').trim() !== 'click');
  const clickNodes = () => nodes.filter((node) => String(node.getAttribute('data-anim-trigger') || '').trim() === 'click');
  const reveal = (node, index = 0) => {{
    const rawDelay = String(node.getAttribute('data-anim-delay') || '').trim();
    const stagger = rawDelay.match(/^stagger\\((\\d+)\\)$/i);
    const delay = stagger ? index * Number(stagger[1]) : parseMs(rawDelay, Math.min(index * 96, 760), 0, 8000);
    window.setTimeout(() => node.classList.add('ppt-anim-in'), delay);
  }};
  const start = () => {{
    if (!nodes.length) {{
      Array.from(document.querySelectorAll('.slide > *:not(style):not(script):not(.page-num)')).slice(0, 14).forEach((node, index) => {{
        node.setAttribute('data-anim', index === 0 ? 'fade-right' : 'fade-up');
      }});
      nodes = Array.from(document.querySelectorAll('[data-anim]'));
    }}
    nodes.forEach(setupNode);
    autoNodes().forEach(reveal);
  }};
  let clickIndex = 0;
  const advance = () => {{
    const list = clickNodes();
    if (clickIndex >= list.length) return false;
    reveal(list[clickIndex], 0);
    clickIndex += 1;
    return true;
  }};
  document.addEventListener('click', () => advance());
  document.addEventListener('keydown', (event) => {{
    if ([' ', 'ArrowRight', 'ArrowDown', 'PageDown', 'Enter'].includes(event.key) && advance()) event.preventDefault();
  }});
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
}})();
</script>
</body>
</html>"""
