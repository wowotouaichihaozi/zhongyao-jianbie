"""Grounded H5 learning-animation generation and deterministic quality review."""

from __future__ import annotations

import json
import re
from typing import Any

try:
    from learning_agents import call_llm_json
except ImportError:  # pragma: no cover
    from .learning_agents import call_llm_json


ANIMATION_MIN_SCENES = 4
ANIMATION_MAX_SCENES = 8
ALLOWED_VISUAL_TYPES = {
    "concept",
    "flow",
    "signal",
    "register",
    "code",
    "comparison",
    "experiment",
}


def _text(value: object, limit: int = 2000) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _string_list(value: object, limit: int = 8, item_limit: int = 300) -> list[str]:
    if isinstance(value, str):
        values = re.split(r"[\n；;]+", value)
    elif isinstance(value, list):
        values = value
    else:
        values = []
    return list(dict.fromkeys(_text(item, item_limit) for item in values if _text(item, item_limit)))[:limit]


def _scene_item_text(value: object, item_limit: int) -> str:
    if not isinstance(value, dict):
        return _text(value, item_limit)

    label = _text(
        value.get("title") or value.get("label") or value.get("name") or value.get("heading"),
        item_limit,
    )
    content = _text(
        value.get("content")
        or value.get("description")
        or value.get("text")
        or value.get("detail")
        or value.get("narration"),
        item_limit,
    )
    if label and content and label != content:
        return _text(f"{label}：{content}", item_limit)
    if label or content:
        return label or content

    scalar_values = [
        _text(item, item_limit)
        for item in value.values()
        if isinstance(item, (str, int, float, bool)) and _text(item, item_limit)
    ]
    return _text("：".join(dict.fromkeys(scalar_values)), item_limit)


def _scene_string_list(value: object, limit: int = 8, item_limit: int = 300) -> list[str]:
    if isinstance(value, str):
        values = re.split(r"[\n；;]+", value)
    elif isinstance(value, list):
        values = value
    elif isinstance(value, dict):
        values = [value]
    else:
        values = []
    normalized = [_scene_item_text(item, item_limit) for item in values]
    return list(dict.fromkeys(item for item in normalized if item))[:limit]


def _profile_summary(profile: dict[str, Any]) -> dict[str, Any]:
    student = profile.get("chatStudentProfile") if isinstance(profile.get("chatStudentProfile"), dict) else {}
    analysis = profile.get("aiAnalysis") if isinstance(profile.get("aiAnalysis"), dict) else {}
    return {
        "profileReportId": int(profile.get("id") or profile.get("_profileReportId") or 0),
        "learningStyle": _text(analysis.get("learningStyle") or student.get("学习风格/认知偏好"), 300),
        "goals": _string_list(student.get("学习目标") or analysis.get("goals"), 5),
        "weakPoints": _string_list(
            analysis.get("weaknesses") or student.get("薄弱知识点") or profile.get("weakPoints"),
            8,
        ),
        "resourcePreference": _text(student.get("资源偏好") or analysis.get("resourcePreference"), 300),
    }


def _normalize_reference(item: object) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    reference_id = _text(item.get("id") or item.get("citationId"), 40)
    title = _text(item.get("title") or item.get("source"), 240)
    if not reference_id or not title:
        return None
    page = item.get("page")
    section = item.get("section")
    locator = _text(item.get("locator"), 120)
    if not locator:
        locator = f"第 {page} 页" if page else f"第 {section or 1} 节"
    return {
        "id": reference_id,
        "title": title,
        "source": _text(item.get("source"), 240),
        "locator": locator,
    }


def _known_references(payload: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in payload.get("knowledgeSources") or []:
        normalized = _normalize_reference(item)
        if not normalized or normalized["id"] in seen:
            continue
        result.append(normalized)
        seen.add(normalized["id"])
    return result[:10]


def _normalize_scene(item: object, index: int) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    title = _text(item.get("title") or item.get("heading"), 120)
    narration = _text(item.get("narration") or item.get("script") or item.get("description"), 1400)
    if not title or not narration:
        return None
    visual_type = _text(item.get("visualType") or item.get("visual_type") or "concept", 30).lower()
    if visual_type not in ALLOWED_VISUAL_TYPES:
        visual_type = "concept"
    try:
        duration = max(8, min(45, int(item.get("durationSeconds") or item.get("duration") or 16)))
    except (TypeError, ValueError):
        duration = 16
    signal = item.get("signal") if isinstance(item.get("signal"), dict) else {}
    return {
        "id": f"scene-{index}",
        "order": index,
        "title": title,
        "durationSeconds": duration,
        "narration": narration,
        "visualType": visual_type,
        "headline": _text(item.get("headline") or title, 140),
        "primaryLabel": _text(item.get("primaryLabel") or item.get("input") or title, 80),
        "secondaryLabel": _text(item.get("secondaryLabel") or item.get("output"), 80),
        "steps": _scene_string_list(item.get("steps"), 6, 180),
        "keyPoints": _scene_string_list(item.get("keyPoints") or item.get("points"), 6, 220),
        "codeSnippet": str(item.get("codeSnippet") or item.get("code") or "").strip()[:2600],
        "signal": {
            "input": _text(signal.get("input") or item.get("input"), 80),
            "process": _text(signal.get("process") or item.get("process"), 80),
            "output": _text(signal.get("output") or item.get("output"), 80),
        },
    }


def _normalize_quiz(item: object, index: int) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    question = _text(item.get("question") or item.get("stem"), 500)
    answer = _text(item.get("answer"), 500)
    if not question or not answer:
        return None
    return {
        "id": f"check-{index}",
        "question": question,
        "answer": answer,
        "explanation": _text(item.get("explanation") or item.get("analysis"), 700),
    }


def _normalize_animation(raw: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    topic = _text(payload.get("topic") or payload.get("title") or "嵌入式系统专题", 120)
    scenes = [
        scene
        for index, item in enumerate(raw.get("scenes") or [], start=1)
        if (scene := _normalize_scene(item, index)) is not None
    ][:ANIMATION_MAX_SCENES]
    if len(scenes) < ANIMATION_MIN_SCENES:
        raise ValueError(f"动画有效场景不足 {ANIMATION_MIN_SCENES} 个")

    known = _known_references(payload)
    known_by_id = {item["id"]: item for item in known}
    requested_ids: list[str] = []
    for item in raw.get("references") or []:
        if isinstance(item, dict):
            requested_ids.append(_text(item.get("id") or item.get("citationId"), 40))
        else:
            requested_ids.append(_text(item, 40))
    references = [known_by_id[item] for item in requested_ids if item in known_by_id]
    if not references:
        references = known

    quiz = [
        check
        for index, item in enumerate(raw.get("knowledgeChecks") or raw.get("quiz") or [], start=1)
        if (check := _normalize_quiz(item, index)) is not None
    ][:4]
    if not quiz:
        quiz = [
            {
                "id": "check-1",
                "question": f"请用自己的话说明{topic}的输入、处理和输出。",
                "answer": "答案应包含关键对象、处理步骤与可观察结果。",
                "explanation": "用于费曼式复述与学习验证。",
            }
        ]

    uncertainties = _string_list(raw.get("uncertainties") or raw.get("verificationNotes"), 8, 500)
    if not references and not uncertainties:
        uncertainties.append("课程知识库未命中直接证据，具体硬件参数与寄存器定义需进一步核验。")
    return {
        "title": _text(raw.get("title") or f"{topic}动画讲解", 180),
        "subtitle": _text(raw.get("subtitle") or raw.get("summary") or f"用动态过程讲清{topic}", 500),
        "audience": _text(raw.get("audience") or "高校嵌入式课程学习者", 240),
        "learningObjectives": _string_list(raw.get("learningObjectives") or raw.get("objectives"), 6, 300),
        "scenes": scenes,
        "totalDurationSeconds": sum(scene["durationSeconds"] for scene in scenes),
        "recap": _string_list(raw.get("recap") or raw.get("summaryPoints"), 8, 300),
        "knowledgeChecks": quiz,
        "references": references,
        "uncertainties": uncertainties,
        "source": "llm",
    }


def _fallback_animation(payload: dict[str, Any], reason: str) -> dict[str, Any]:
    topic = _text(payload.get("topic") or payload.get("title") or "嵌入式系统专题", 120)
    hits = [item for item in (payload.get("knowledgeContext") or []) if isinstance(item, dict)]
    references = _known_references(payload)
    scene_templates = [
        ("concept", "先建立概念边界", "对象与作用"),
        ("flow", "再观察完整工作流程", "输入到输出"),
        ("signal", "追踪关键状态变化", "信号与寄存器"),
        ("experiment", "最后完成最小验证", "现象与复盘"),
    ]
    scenes: list[dict[str, Any]] = []
    for index, (visual_type, title, headline) in enumerate(scene_templates, start=1):
        hit = hits[index - 1] if index <= len(hits) else {}
        excerpt = _text(hit.get("excerpt") or hit.get("content"), 900)
        citation = _text(hit.get("citationId"), 40)
        if excerpt:
            narration = f"{excerpt} {'[' + citation + ']' if citation else '（具体事实需进一步核验）'}"
        else:
            narration = f"围绕{topic}完成“{title}”。当前没有足够直接证据，具体硬件参数需进一步核验。"
        scenes.append(
            {
                "id": f"scene-{index}",
                "order": index,
                "title": title,
                "durationSeconds": 16,
                "narration": narration,
                "visualType": visual_type,
                "headline": headline,
                "primaryLabel": topic,
                "secondaryLabel": "可验证学习结果",
                "steps": ["观察输入", "解释处理", "核对输出"],
                "keyPoints": ["保留学习证据", "不确定事实需核验"],
                "codeSnippet": "",
                "signal": {"input": "输入", "process": topic, "output": "输出"},
            }
        )
    return {
        "title": f"{topic}动画讲解",
        "subtitle": "基于课程知识库组织的动态微课",
        "audience": "高校嵌入式课程学习者",
        "learningObjectives": [f"解释{topic}的核心机制", "完成一次可观察、可复盘的最小验证"],
        "scenes": scenes,
        "totalDurationSeconds": sum(scene["durationSeconds"] for scene in scenes),
        "recap": ["先说明输入与前置条件", "再解释处理过程", "最后用实验结果验证"],
        "knowledgeChecks": [
            {
                "id": "check-1",
                "question": f"请用自己的话解释{topic}的输入、处理和输出。",
                "answer": "回答需覆盖关键对象、处理步骤和可观察结果。",
                "explanation": "用于费曼式复述和学习验证。",
            }
        ],
        "references": references,
        "uncertainties": [] if references else ["具体硬件参数、寄存器位和时序结论需进一步核验。"],
        "source": "knowledge-template-fallback",
        "fallbackReason": _text(reason, 500),
    }


def evaluate_learning_animation(animation: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    scenes = animation.get("scenes") if isinstance(animation.get("scenes"), list) else []
    references = animation.get("references") if isinstance(animation.get("references"), list) else []
    checks = animation.get("knowledgeChecks") if isinstance(animation.get("knowledgeChecks"), list) else []
    visual_types = {str(item.get("visualType") or "") for item in scenes if isinstance(item, dict)}
    narration_count = sum(1 for item in scenes if isinstance(item, dict) and _text(item.get("narration")))
    profile_summary = _profile_summary(profile)
    serialized = json.dumps(animation, ensure_ascii=False, default=str)
    sensitive = bool(re.search(r"(?i)(api[_-]?key|api[_-]?secret|password|bearer)\s*[:=]\s*[A-Za-z0-9._:/+-]{16,}", serialized))

    structure_score = 25 if ANIMATION_MIN_SCENES <= len(scenes) <= ANIMATION_MAX_SCENES else 10
    pedagogy_score = 15 if animation.get("learningObjectives") and animation.get("recap") and checks else 6
    multimodal_score = 20 if narration_count == len(scenes) and len(visual_types) >= 3 else 10
    grounding_score = min(25, len(references) * 5)
    if not references and animation.get("uncertainties"):
        grounding_score = 10
    personalization_score = 10 if any(profile_summary.get(key) for key in ("learningStyle", "goals", "weakPoints", "resourcePreference")) else 4
    safety_score = 0 if sensitive else 5
    score = max(0, min(100, structure_score + pedagogy_score + multimodal_score + grounding_score + personalization_score + safety_score))
    issues: list[str] = []
    if len(scenes) < ANIMATION_MIN_SCENES:
        issues.append("有效动画场景不足")
    if narration_count != len(scenes):
        issues.append("部分场景缺少讲解词")
    if len(visual_types) < 3:
        issues.append("视觉表达类型不足三种")
    if not references:
        issues.append("课程知识库未命中直接引用，具体事实需要人工核验")
    if sensitive:
        issues.append("检测到疑似敏感凭据")
    return {
        "score": score,
        "passed": bool(score >= 75 and len(scenes) >= ANIMATION_MIN_SCENES and narration_count == len(scenes) and not sensitive),
        "criteria": {
            "structure": structure_score,
            "pedagogy": pedagogy_score,
            "multimodal": multimodal_score,
            "knowledgeGrounding": grounding_score,
            "personalization": personalization_score,
            "safety": safety_score,
        },
        "sceneCount": len(scenes),
        "visualTypeCount": len(visual_types),
        "citationCount": len(references),
        "knowledgeCheckCount": len(checks),
        "issues": issues,
        "verificationRequired": not bool(references),
    }


def generate_learning_animation(payload: dict[str, Any]) -> dict[str, Any]:
    topic = _text(payload.get("topic") or payload.get("title") or "嵌入式系统专题", 120)
    profile = payload.get("profile") if isinstance(payload.get("profile"), dict) else {}
    profile_summary = _profile_summary(profile)
    references = _known_references(payload)
    knowledge_hits = [item for item in (payload.get("knowledgeContext") or []) if isinstance(item, dict)][:8]
    knowledge_text = "\n\n".join(
        f"[{_text(item.get('citationId'), 40)}] {_text(item.get('title'), 180)}\n{_text(item.get('excerpt') or item.get('content'), 1600)}"
        for item in knowledge_hits
    )
    system = """
你是嵌小智总控调用的 H5 动画讲解生成智能体。请为高校嵌入式课程生成可直接播放的结构化动画故事板。
只输出 JSON，字段必须为 title、subtitle、audience、learningObjectives、scenes、recap、knowledgeChecks、references、uncertainties。
scenes 为 4-8 项，每项包含 title、durationSeconds、narration、visualType、headline、primaryLabel、secondaryLabel、steps、keyPoints、codeSnippet、signal。
visualType 只能是 concept、flow、signal、register、code、comparison、experiment。每个场景都必须有讲解词，至少使用三种视觉类型。
涉及定义、寄存器、参数、接线和时序结论时必须使用给定 [KBn] 来源；references 只能引用输入中存在的 id。没有依据的事实写入 uncertainties，不得编造来源。
"""
    prompt = f"""
动画主题：{topic}
补充要求：{_text(payload.get('requirements') or payload.get('prompt'), 1200)}
当前画像：{json.dumps(profile_summary, ensure_ascii=False)}
允许引用：{json.dumps(references, ensure_ascii=False)}
课程知识片段：
{knowledge_text or '未检索到直接片段。所有具体硬件事实必须写入 uncertainties。'}
"""
    attempts: list[dict[str, Any]] = []
    try:
        raw = call_llm_json(system, prompt, max_tokens=5000, repair=True, timeout=120)
        attempts.append({"stage": "initial", "status": "complete", "keys": list(raw.keys())[:30]})
        try:
            animation = _normalize_animation(raw, payload)
        except ValueError as validation_error:
            attempts.append({"stage": "schema_validation", "status": "failed", "error": str(validation_error)})
            repair_system = """
你是动画故事板 JSON 修订器。只补齐结构，不改变主题，不新增输入中不存在的知识来源。
只输出字段 title、subtitle、audience、learningObjectives、scenes、recap、knowledgeChecks、references、uncertainties。
scenes 必须为 4-8 项，每项都包含 title、durationSeconds、narration、visualType、headline、primaryLabel、secondaryLabel、steps、keyPoints、codeSnippet、signal。
"""
            repaired = call_llm_json(
                repair_system,
                f"校验错误：{validation_error}\n允许引用：{json.dumps(references, ensure_ascii=False)}\n原始 JSON：{json.dumps(raw, ensure_ascii=False)[:15000]}",
                max_tokens=5000,
                repair=True,
                timeout=120,
            )
            animation = _normalize_animation(repaired, payload)
            animation["source"] = "llm-schema-repaired"
            attempts.append({"stage": "schema_repair", "status": "complete", "keys": list(repaired.keys())[:30]})
    except Exception as exc:
        attempts.append({"stage": "fallback", "status": "complete", "error": _text(exc, 500)})
        animation = _fallback_animation(payload, str(exc))

    animation["profile"] = profile_summary
    animation["generationAttempts"] = attempts
    quality = evaluate_learning_animation(animation, profile)
    return {
        "agent": "learning-animation-agent",
        "source": animation.get("source") or "llm",
        "animation": animation,
        "qualityEvaluation": quality,
        "generationAttempts": attempts,
    }


__all__ = ["evaluate_learning_animation", "generate_learning_animation"]
