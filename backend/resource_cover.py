from __future__ import annotations

import hashlib
import html
import json
import re
import threading
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


COVER_SIZE = (960, 480)
_CACHE_LOCK = threading.Lock()
_TYPE_META = {
    "question_bank": ("练习题", "#9f3a32", "#fff3f1"),
    "ppt": ("PPT", "#315f9a", "#f1f5fb"),
    "mindmap": ("思维导图", "#6c568c", "#f7f3fa"),
    "video": ("视频", "#28747a", "#eff8f7"),
    "generated_video": ("AI 视频", "#8c4b68", "#faf2f5"),
    "herb_model": ("药材模型", "#7b6544", "#f7f5ef"),
    "document": ("学习资料", "#496b54", "#f2f7f3"),
    "animation": ("动画微课", "#8d6140", "#faf5f0"),
}
_PREFERRED_TEXT_KEYS = (
    "stem",
    "question",
    "contentOutline",
    "description",
    "topic",
    "label",
    "name",
    "text",
    "analysis",
    "answer",
)


def _font_candidates() -> list[Path]:
    project_root = Path(__file__).resolve().parent.parent
    return [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
        project_root / "img" / "digital-twin" / "plugins" / "UIdemo" / "fonts" / "优设标题黑.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = next((candidate for candidate in _font_candidates() if candidate.exists()), None)
    return ImageFont.truetype(str(path), size) if path else ImageFont.load_default()


def _plain_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"(?is)<(?:style|script)\b.*?</(?:style|script)>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"[`*_#>|{}\[\]]+", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -:：·|\t\r\n")
    return text


def _collect_preview_lines(value: Any, *, depth: int = 0, output: list[str] | None = None) -> list[str]:
    lines = output if output is not None else []
    if depth > 6 or len(lines) >= 12 or value is None:
        return lines
    if isinstance(value, dict):
        for key in _PREFERRED_TEXT_KEYS:
            if key in value:
                _collect_preview_lines(value.get(key), depth=depth + 1, output=lines)
        for key, nested in value.items():
            if key not in _PREFERRED_TEXT_KEYS and key not in {"html", "route", "url", "videoUrl", "posterUrl"}:
                _collect_preview_lines(nested, depth=depth + 1, output=lines)
        return lines
    if isinstance(value, (list, tuple)):
        for item in value[:10]:
            _collect_preview_lines(item, depth=depth + 1, output=lines)
        return lines
    if isinstance(value, str):
        candidates = re.split(r"[\r\n]+|(?<=[。！？；])", value)
        for candidate in candidates:
            text = _plain_text(candidate)
            if 4 <= len(text) <= 160 and text not in lines:
                lines.append(text)
            if len(lines) >= 12:
                break
    return lines


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int, max_lines: int) -> list[str]:
    source = _plain_text(text)
    if not source:
        return []
    lines: list[str] = []
    current = ""
    for character in source:
        candidate = current + character
        if current and draw.textlength(candidate, font=font) > max_width:
            lines.append(current)
            current = character
            if len(lines) >= max_lines:
                break
        else:
            current = candidate
    if len(lines) < max_lines and current:
        lines.append(current)
    consumed = "".join(lines)
    if len(consumed) < len(source) and lines:
        last = lines[-1]
        while last and draw.textlength(last + "...", font=font) > max_width:
            last = last[:-1]
        lines[-1] = last + "..."
    return lines


def _rounded_label(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, font, fill: str, color: str) -> None:
    draw.rounded_rectangle(box, radius=8, fill=fill)
    left, top, right, bottom = box
    text_box = draw.textbbox((0, 0), text, font=font)
    x = left + (right - left - (text_box[2] - text_box[0])) / 2
    y = top + (bottom - top - (text_box[3] - text_box[1])) / 2 - text_box[1]
    draw.text((x, y), text, font=font, fill=color)


def _draw_question_rows(draw: ImageDraw.ImageDraw, lines: list[str], accent: str, font) -> None:
    for index in range(3):
        top = 264 + index * 58
        draw.rounded_rectangle((62, top, 898, top + 44), radius=8, fill="#ffffff", outline="#e1e7e4", width=1)
        _rounded_label(draw, (76, top + 8, 104, top + 36), str(index + 1), font, "#f0f5f2", accent)
        text = lines[index] if index < len(lines) else "题目内容将在资源页中完整展开"
        wrapped = _wrap_text(draw, text, font, 750, 1)
        draw.text((122, top + 10), wrapped[0] if wrapped else text, font=font, fill="#40504a")


def _draw_mindmap(draw: ImageDraw.ImageDraw, title: str, lines: list[str], accent: str, font) -> None:
    center = (480, 328)
    labels = lines[:4] or ["核心概念", "前置知识", "关联关系", "易错点"]
    positions = [(94, 272, 314, 320), (646, 272, 866, 320), (94, 370, 314, 418), (646, 370, 866, 418)]
    for box, label in zip(positions, labels):
        left, top, right, bottom = box
        draw.line((center[0], center[1], (left + right) // 2, (top + bottom) // 2), fill="#cbd9d3", width=3)
        _rounded_label(draw, box, (_wrap_text(draw, label, font, right - left - 24, 1) or [label])[0], font, "#ffffff", "#43534d")
    center_text = (_wrap_text(draw, title, font, 230, 1) or ["学习主题"])[0]
    _rounded_label(draw, (350, 300, 610, 356), center_text, font, accent, "#ffffff")


def _draw_summary_blocks(draw: ImageDraw.ImageDraw, lines: list[str], accent: str, font) -> None:
    for index in range(3):
        left = 62 + index * 286
        right = left + 264
        draw.rounded_rectangle((left, 274, right, 412), radius=10, fill="#ffffff", outline="#e0e6e3", width=1)
        draw.rectangle((left, 274, left + 5, 412), fill=accent)
        text = lines[index] if index < len(lines) else ["核心要点", "学习任务", "复习与订正"][index]
        wrapped = _wrap_text(draw, text, font, 220, 3)
        for line_index, line in enumerate(wrapped):
            draw.text((left + 22, 296 + line_index * 30), line, font=font, fill="#41514b")


def render_resource_task_cover(task: dict[str, Any], cache_dir: Path) -> tuple[Path, str]:
    task_id = str(task.get("taskId") or "resource")
    task_type = str(task.get("taskType") or "document")
    title = _plain_text(task.get("title") or "个性化学习资源") or "个性化学习资源"
    result = task.get("result") if isinstance(task.get("result"), dict) else {}
    fingerprint_source = json.dumps(
        {
            "taskId": task_id,
            "taskType": task_type,
            "updatedAt": task.get("updatedAt"),
            "title": title,
            "status": task.get("status"),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    fingerprint = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()[:20]
    safe_task_id = re.sub(r"[^A-Za-z0-9_.-]+", "-", task_id).strip("-")[:90] or "resource"
    cache_dir.mkdir(parents=True, exist_ok=True)
    output_path = cache_dir / f"{safe_task_id}-{fingerprint}.png"
    if output_path.exists():
        return output_path, fingerprint

    with _CACHE_LOCK:
        if output_path.exists():
            return output_path, fingerprint
        type_label, accent, background = _TYPE_META.get(task_type, ("学习资源", "#386b57", "#f3f7f5"))
        image = Image.new("RGB", COVER_SIZE, background)
        draw = ImageDraw.Draw(image)
        label_font = _font(23)
        title_font = _font(38)
        body_font = _font(21)
        tiny_font = _font(17)
        draw.rectangle((0, 0, COVER_SIZE[0], 8), fill=accent)
        _rounded_label(draw, (62, 42, 190, 84), type_label, label_font, "#ffffff", accent)
        status = "资源已生成" if str(task.get("status")) == "complete" else "资源准备中"
        draw.text((744, 51), status, font=tiny_font, fill="#76847f")
        title_lines = _wrap_text(draw, title, title_font, 836, 2)
        for index, line in enumerate(title_lines):
            draw.text((62, 112 + index * 54), line, font=title_font, fill="#1d2925")

        preview_lines = [line for line in _collect_preview_lines(result) if line != title][:8]
        if task_type == "question_bank":
            _draw_question_rows(draw, preview_lines, accent, body_font)
        elif task_type == "mindmap":
            _draw_mindmap(draw, title, preview_lines, accent, body_font)
        else:
            _draw_summary_blocks(draw, preview_lines, accent, body_font)

        temp_path = output_path.with_suffix(".tmp.png")
        image.save(temp_path, format="PNG", optimize=True)
        temp_path.replace(output_path)
    return output_path, fingerprint
