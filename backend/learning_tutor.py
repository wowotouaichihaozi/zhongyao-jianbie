"""Structured, knowledge-grounded intelligent tutoring output."""

from __future__ import annotations

import json
import re
from typing import Any

try:
    from learning_agents import call_llm_json
except ImportError:  # pragma: no cover
    from .learning_agents import call_llm_json


TUTOR_SCHEMA_VERSION = "1.0"


def _text(value: object, default: str = "") -> str:
    normalized = " ".join(str(value or "").strip().split())
    return normalized or default


def _string_list(value: object, *, limit: int = 8) -> list[str]:
    values = value if isinstance(value, list) else [value] if value else []
    result: list[str] = []
    for item in values:
        text = _text(item)
        if text and text not in result:
            result.append(text[:500])
    return result[:limit]


def _dict_list(value: object, *, limit: int = 8) -> list[dict[str, Any]]:
    return [dict(item) for item in value if isinstance(item, dict)][:limit] if isinstance(value, list) else []


def _knowledge_references(payload: dict[str, Any]) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    for index, raw in enumerate(payload.get("knowledgeSources") or [], start=1):
        if not isinstance(raw, dict):
            continue
        source = _text(raw.get("source") or raw.get("file") or raw.get("document"))
        title = _text(raw.get("title") or source, f"课程资料 {index}")
        reference_id = _text(raw.get("id") or raw.get("chunkId") or raw.get("chunk_id"), f"KB{index}")
        if not source and not title:
            continue
        references.append(
            {
                "id": reference_id[:80],
                "title": title[:160],
                "source": source[:240],
                "page": raw.get("page"),
                "section": raw.get("section"),
            }
        )
    return references[:8]


def _safe_mermaid(value: object) -> str:
    code = str(value or "").strip()
    code = re.sub(r"^```(?:mermaid)?\s*|\s*```$", "", code, flags=re.I | re.S).strip()
    if not re.match(r"^(flowchart|graph|mindmap)\b", code, flags=re.I):
        return "flowchart TD\n  A[识别问题] --> B[回忆前置概念]\n  B --> C[逐步验证]\n  C --> D[完成练习]\n  D --> E[复述与迁移]"
    return "\n".join(code.splitlines()[:40])[:3000]


def _normalize_socratic_questions(value: object, question: str) -> list[dict[str, str]]:
    result = []
    for index, item in enumerate(_dict_list(value, limit=6), start=1):
        prompt = _text(item.get("question") or item.get("prompt"))
        if not prompt:
            continue
        result.append(
            {
                "id": _text(item.get("id"), f"SQ{index}"),
                "question": prompt,
                "intent": _text(item.get("intent"), "检查当前理解"),
                "expectedKeyPoints": _text(item.get("expectedKeyPoints") or item.get("expected"), "说出关键依据"),
                "revealCondition": _text(item.get("revealCondition"), "学习者先独立作答后再揭示下一步"),
            }
        )
    defaults = [
        ("你已经确定了哪些已知条件，哪些信息还需要查证？", "区分已知与未知"),
        ("如果只改变一个关键条件，你预计现象会怎样变化？为什么？", "建立因果关系"),
        (f"请用自己的话解释“{question[:40]}”背后的核心机制。", "检验是否真正理解"),
    ]
    for prompt, intent in defaults:
        if len(result) >= 3:
            break
        result.append(
            {
                "id": f"SQ{len(result) + 1}",
                "question": prompt,
                "intent": intent,
                "expectedKeyPoints": "给出结论、依据和可验证现象",
                "revealCondition": "学习者提交一次独立回答后再提供提示",
            }
        )
    return result


def _normalize_hint_ladder(value: object) -> list[dict[str, Any]]:
    result = []
    for index, item in enumerate(_dict_list(value, limit=5), start=1):
        hint = _text(item.get("hint") or item.get("content"))
        if not hint:
            continue
        result.append(
            {
                "level": int(item.get("level") or index),
                "title": _text(item.get("title"), f"第 {index} 级提示"),
                "hint": hint,
                "revealWhen": _text(item.get("revealWhen") or item.get("revealCondition"), "上一层提示后仍无法推进时"),
            }
        )
    defaults = [
        ("方向提示", "先判断问题属于概念、配置、代码还是实验现象。"),
        ("关键提示", "列出输入、状态变化、输出以及它们之间的因果链。"),
        ("接近答案", "对照课程资料逐项验证关键配置，并记录预期现象与实际现象。"),
    ]
    while len(result) < 3:
        title, hint = defaults[len(result)]
        result.append(
            {
                "level": len(result) + 1,
                "title": title,
                "hint": hint,
                "revealWhen": "学习者完成上一层尝试但仍无法推进时",
            }
        )
    return result[:3]


def _normalize_practice_tasks(value: object, question: str) -> list[dict[str, str]]:
    result = []
    for index, item in enumerate(_dict_list(value, limit=4), start=1):
        prompt = _text(item.get("question") or item.get("prompt") or item.get("task"))
        if not prompt:
            continue
        result.append(
            {
                "id": _text(item.get("id"), f"PT{index}"),
                "type": _text(item.get("type"), "诊断练习"),
                "question": prompt,
                "answer": _text(item.get("answer"), "完成后对照课程资料核验"),
                "explanation": _text(item.get("explanation") or item.get("analysis"), "说明结论、依据和验证方法"),
                "difficulty": _text(item.get("difficulty"), "medium"),
                "acceptanceCriteria": _text(
                    item.get("acceptanceCriteria"),
                    "能独立给出结论、关键依据和至少一个可验证现象",
                ),
            }
        )
    if not result:
        result.append(
            {
                "id": "PT1",
                "type": "费曼迁移练习",
                "question": f"请用一个最小示例说明：{question}",
                "answer": "答案应包含输入条件、关键步骤、预期输出和验证方法。",
                "explanation": "重点不是背诵结论，而是把机制映射到可运行或可观察的例子。",
                "difficulty": "medium",
                "acceptanceCriteria": "示例可复现，解释中不存在未说明的关键跳步",
            }
        )
    return result


def _raw_schema_warnings(raw: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if not _text(raw.get("answer") or raw.get("reply") or raw.get("content")):
        warnings.append("原始输出缺少 answer")
    if not isinstance(raw.get("explanation"), dict):
        warnings.append("原始输出 explanation 不是对象")
    socratic = raw.get("socraticQuestions") if isinstance(raw.get("socraticQuestions"), list) else []
    if len(socratic) < 3:
        warnings.append("原始输出 socraticQuestions 少于 3 个")
    if not isinstance(raw.get("feynmanTask"), dict):
        warnings.append("原始输出缺少 feynmanTask")
    hints = raw.get("hintLadder") if isinstance(raw.get("hintLadder"), list) else []
    if len(hints) != 3:
        warnings.append("原始输出 hintLadder 不是 3 级")
    if not isinstance(raw.get("practiceTasks"), list) or not raw.get("practiceTasks"):
        warnings.append("原始输出缺少 practiceTasks")
    multimodal = raw.get("multimodal") if isinstance(raw.get("multimodal"), dict) else {}
    if not isinstance(multimodal.get("mermaid"), dict) or not isinstance(multimodal.get("learningCard"), dict):
        warnings.append("原始输出缺少 Mermaid 或学习卡")
    return warnings


def normalize_tutor_output(raw: object, payload: dict[str, Any], *, source: str) -> dict[str, Any]:
    raw = dict(raw) if isinstance(raw, dict) else {}
    generation_warnings = _raw_schema_warnings(raw)
    question = _text(payload.get("question") or payload.get("message") or payload.get("topic"), "当前学习问题")
    explanation_raw = raw.get("explanation") if isinstance(raw.get("explanation"), dict) else {}
    explanation_text = _text(raw.get("explanation")) if not explanation_raw else ""
    steps = _string_list(raw.get("steps") or explanation_raw.get("steps"), limit=8)
    if len(steps) < 3:
        steps = [
            "明确问题边界与已知条件",
            "用课程知识解释关键机制",
            "通过题目、代码或实验现象验证结论",
        ]

    feynman_raw = raw.get("feynmanTask") if isinstance(raw.get("feynmanTask"), dict) else {}
    multimodal_raw = raw.get("multimodal") if isinstance(raw.get("multimodal"), dict) else {}
    card_raw = multimodal_raw.get("learningCard") if isinstance(multimodal_raw.get("learningCard"), dict) else {}
    narration = _string_list(multimodal_raw.get("narrationScript"), limit=6)
    if not narration:
        narration = ["先说结论，再解释依据。", "指出最容易混淆的地方。", "最后给出一个可验证的小任务。"]

    references = _knowledge_references(payload)
    uncertainties = _string_list(raw.get("uncertainties"), limit=6)
    if not references and not uncertainties:
        uncertainties.append("当前知识库没有命中可直接引用的资料，具体芯片参数和寄存器位定义需查阅对应芯片手册。")

    result = {
        "schemaVersion": TUTOR_SCHEMA_VERSION,
        "agent": "smart-tutor-agent",
        "source": source,
        "question": question,
        "answer": _text(raw.get("answer") or raw.get("reply") or raw.get("content"), "先梳理已知条件，再沿着机制、配置和现象三层逐步验证。"),
        "diagnosis": {
            "learnerStage": _text((raw.get("diagnosis") or {}).get("learnerStage") if isinstance(raw.get("diagnosis"), dict) else "", "根据当前画像分层讲解"),
            "likelyMisconception": _text((raw.get("diagnosis") or {}).get("likelyMisconception") if isinstance(raw.get("diagnosis"), dict) else "", "可能把结论记忆与机制理解混在一起"),
            "profileEvidence": _string_list((raw.get("diagnosis") or {}).get("profileEvidence") if isinstance(raw.get("diagnosis"), dict) else [], limit=5),
        },
        "explanation": {
            "concept": _text(explanation_raw.get("concept") or explanation_text, "先定位关键概念，再建立输入、状态变化与输出之间的关系。"),
            "analogy": _text(explanation_raw.get("analogy"), "把系统看作一条可逐段观测的信号链，每一段都应有输入、配置和输出。"),
            "steps": steps,
        },
        "socraticQuestions": _normalize_socratic_questions(raw.get("socraticQuestions"), question),
        "feynmanTask": {
            "prompt": _text(feynman_raw.get("prompt"), f"假设向刚开始学习的同学解释“{question[:60]}”，请在 90 秒内完成复述。"),
            "audience": _text(feynman_raw.get("audience"), "刚接触该知识点的同学"),
            "checklist": _string_list(
                feynman_raw.get("checklist"),
                limit=6,
            ) or ["没有照抄术语", "说明了因果关系", "给出了可验证例子", "指出了适用边界"],
        },
        "hintLadder": _normalize_hint_ladder(raw.get("hintLadder")),
        "practiceTasks": _normalize_practice_tasks(raw.get("practiceTasks") or raw.get("practice"), question),
        "multimodal": {
            "mermaid": {
                "type": "flowchart",
                "code": _safe_mermaid((multimodal_raw.get("mermaid") or {}).get("code") if isinstance(multimodal_raw.get("mermaid"), dict) else multimodal_raw.get("mermaid")),
            },
            "learningCard": {
                "title": _text(card_raw.get("title"), question[:40]),
                "front": _text(card_raw.get("front"), f"如何判断：{question[:70]}"),
                "back": _text(card_raw.get("back"), "从关键条件、机制链和可验证现象三方面回答。"),
                "keyPoints": _string_list(card_raw.get("keyPoints"), limit=6) or ["条件", "机制", "现象", "验证"],
            },
            "narrationScript": narration,
        },
        "followUp": _text(raw.get("followUp"), "先回答第一道苏格拉底问题，我会根据你的答案决定是否揭示下一层提示。"),
        "references": references,
        "uncertainties": uncertainties,
        "responseModes": [
            "concept-explanation",
            "socratic-dialogue",
            "feynman-retelling",
            "graded-hints",
            "practice",
            "learning-card",
            "mermaid",
        ],
        "generationWarnings": generation_warnings,
    }
    result["practice"] = result["practiceTasks"][0]
    result["qualityEvaluation"] = tutor_quality_evaluation(result)
    return result


def validate_tutor_output(result: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if str(result.get("source") or "").startswith("llm") and result.get("generationWarnings"):
        errors.extend(_string_list(result.get("generationWarnings"), limit=10))
    if len(_text(result.get("answer"))) < 20:
        errors.append("answer 过短")
    explanation = result.get("explanation") if isinstance(result.get("explanation"), dict) else {}
    if not explanation.get("concept") or len(explanation.get("steps") or []) < 3:
        errors.append("explanation 缺少概念或三步讲解")
    if len(result.get("socraticQuestions") or []) < 3:
        errors.append("socraticQuestions 少于 3 个")
    feynman = result.get("feynmanTask") if isinstance(result.get("feynmanTask"), dict) else {}
    if not feynman.get("prompt") or len(feynman.get("checklist") or []) < 3:
        errors.append("feynmanTask 不完整")
    hints = result.get("hintLadder") or []
    if len(hints) != 3 or {int(item.get("level") or 0) for item in hints if isinstance(item, dict)} != {1, 2, 3}:
        errors.append("hintLadder 必须包含 3 级提示")
    practices = result.get("practiceTasks") or []
    if not practices or not all(
        isinstance(item, dict)
        and item.get("question")
        and item.get("answer")
        and item.get("explanation")
        and item.get("acceptanceCriteria")
        for item in practices
    ):
        errors.append("practiceTasks 缺少答案、解析或验收标准")
    multimodal = result.get("multimodal") if isinstance(result.get("multimodal"), dict) else {}
    mermaid = multimodal.get("mermaid") if isinstance(multimodal.get("mermaid"), dict) else {}
    card = multimodal.get("learningCard") if isinstance(multimodal.get("learningCard"), dict) else {}
    if not mermaid.get("code") or not card.get("front") or not card.get("back") or not card.get("keyPoints"):
        errors.append("multimodal 缺少 Mermaid 或学习卡")
    if not result.get("references") and not result.get("uncertainties"):
        errors.append("缺少知识引用或不确定项标记")
    return errors


def tutor_quality_evaluation(result: dict[str, Any]) -> dict[str, Any]:
    validation_errors = validate_tutor_output(result)
    dimensions = {
        "structure": 25 if not any("answer" in item or "explanation" in item for item in validation_errors) else 12,
        "guidedPedagogy": 25 if len(result.get("socraticQuestions") or []) >= 3 and len(result.get("hintLadder") or []) == 3 else 10,
        "actionability": 20 if result.get("practiceTasks") and (result.get("feynmanTask") or {}).get("prompt") else 8,
        "multimodal": 15 if (result.get("multimodal") or {}).get("mermaid") and (result.get("multimodal") or {}).get("learningCard") else 5,
        "groundingAndSafety": 15 if result.get("references") or result.get("uncertainties") else 0,
    }
    score = min(100, sum(dimensions.values()))
    return {
        "score": score,
        "passed": not validation_errors and score >= 80,
        "dimensions": dimensions,
        "issues": validation_errors,
        "grounded": bool(result.get("references")),
        "uncertaintyMarked": bool(result.get("uncertainties")),
    }


def _grounded_fallback(payload: dict[str, Any], previous: object, errors: list[str]) -> dict[str, Any]:
    chunks = [item for item in (payload.get("knowledgeContext") or []) if isinstance(item, dict)]
    excerpt = _text((chunks[0] if chunks else {}).get("content"))[:900]
    question = _text(payload.get("question") or payload.get("message") or payload.get("topic"), "当前学习问题")
    answer = (
        f"围绕“{question}”，先把问题拆成条件、机制、配置和可观察现象四部分。"
        + (f"课程知识库命中的要点是：{excerpt}" if excerpt else "当前知识库没有命中足够正文，具体参数需查阅课程资料或芯片手册后再确认。")
    )
    raw = {
        "answer": answer,
        "explanation": {
            "concept": excerpt or "在没有充分知识依据时，不直接猜测硬件参数；应先确认器件、手册版本和关键配置。",
            "steps": ["列出已知条件", "检索课程资料或芯片手册", "用最小实验验证结论"],
        },
        "uncertainties": [
            "模型结构化输出连续两次未通过校验，当前回答采用知识库约束兜底。",
            *(errors[:3] or []),
        ],
    }
    return normalize_tutor_output(raw, payload, source="grounded-fallback")


def generate_learning_tutor(payload: dict[str, Any]) -> dict[str, Any]:
    question = _text(payload.get("question") or payload.get("message") or payload.get("topic"), "当前学习问题")
    profile = payload.get("profile") or (payload.get("xiaozhiContext") or {}).get("profile") or {}
    knowledge_context = payload.get("knowledgeContext") or []
    knowledge_sources = payload.get("knowledgeSources") or []
    conversation_context = str(payload.get("conversationContext") or "").strip()[:12000]
    previous_turn = payload.get("previousTurn") if isinstance(payload.get("previousTurn"), dict) else {}
    schema = {
        "answer": "string",
        "diagnosis": {"learnerStage": "string", "likelyMisconception": "string", "profileEvidence": ["string"]},
        "explanation": {"concept": "string", "analogy": "string", "steps": ["string"]},
        "socraticQuestions": [{"question": "string", "intent": "string", "expectedKeyPoints": "string", "revealCondition": "string"}],
        "feynmanTask": {"prompt": "string", "audience": "string", "checklist": ["string"]},
        "hintLadder": [{"level": 1, "title": "string", "hint": "string", "revealWhen": "string"}],
        "practiceTasks": [{"type": "string", "question": "string", "answer": "string", "explanation": "string", "difficulty": "medium", "acceptanceCriteria": "string"}],
        "multimodal": {"mermaid": {"type": "flowchart", "code": "flowchart TD..."}, "learningCard": {"title": "string", "front": "string", "back": "string", "keyPoints": ["string"]}, "narrationScript": ["string"]},
        "followUp": "string",
        "uncertainties": ["string"],
    }
    system = """
你是嵌小智调度的嵌入式课程智能辅导子智能体。
必须依据学习画像与提供的课程知识片段答疑，禁止编造芯片参数、寄存器位或实验现象。
采用苏格拉底式追问、费曼复述、三级提示和可验收练习；先引导思考，再揭示答案。
输出必须是单个 JSON 对象，不要 Markdown 代码围栏，不要输出 Schema 以外的解释文字。
"""
    prompt = f"""
当前用户问题（必须优先、精准回应）：{question}
连续辅导对话上下文：{conversation_context or "无"}
上一轮辅导证据：{json.dumps(previous_turn, ensure_ascii=False, default=str)[:8000]}
学习画像：{json.dumps(profile, ensure_ascii=False, default=str)[:6000]}
课程知识片段：{json.dumps(knowledge_context, ensure_ascii=False, default=str)[:10000]}
可追溯引用：{json.dumps(knowledge_sources, ensure_ascii=False, default=str)[:4000]}
严格 JSON Schema：{json.dumps(schema, ensure_ascii=False)}
要求：先直接处理当前用户问题，再结合上一轮内容判断理解程度；至少 3 个递进追问、恰好 3 级提示、至少 1 个带答案/解析/验收标准的练习，同时输出 Mermaid 学习流程与学习卡。没有知识依据的内容写入 uncertainties。
"""
    try:
        first_raw = call_llm_json(system, prompt, max_tokens=3800)
    except Exception:
        return _grounded_fallback(
            payload,
            {},
            ["模型连续两次返回的 JSON 均无法解析，已启用知识库约束兜底。"],
        )
    first = normalize_tutor_output(first_raw, payload, source="llm")
    first_errors = validate_tutor_output(first)
    if not first_errors:
        first["qualityEvaluation"] = tutor_quality_evaluation(first)
        return first

    repair_prompt = f"""
原始问题：{question}
连续辅导对话上下文：{conversation_context or "无"}
上一轮辅导证据：{json.dumps(previous_turn, ensure_ascii=False, default=str)[:8000]}
上次输出：{json.dumps(first_raw, ensure_ascii=False, default=str)[:12000]}
校验错误：{json.dumps(first_errors, ensure_ascii=False)}
目标 Schema：{json.dumps(schema, ensure_ascii=False)}
请修复为严格 JSON。必须保留知识依据，不得补造未提供的硬件事实。
"""
    try:
        repaired_raw = call_llm_json(system, repair_prompt, max_tokens=4200)
    except Exception:
        return _grounded_fallback(
            payload,
            first_raw,
            ["模型修订结果仍无法解析，已启用知识库约束兜底。", *first_errors],
        )
    repaired = normalize_tutor_output(repaired_raw, payload, source="llm-repaired")
    repaired_errors = validate_tutor_output(repaired)
    if not repaired_errors:
        repaired["qualityEvaluation"] = tutor_quality_evaluation(repaired)
        return repaired
    return _grounded_fallback(payload, repaired_raw, repaired_errors)


__all__ = [
    "TUTOR_SCHEMA_VERSION",
    "generate_learning_tutor",
    "normalize_tutor_output",
    "tutor_quality_evaluation",
    "validate_tutor_output",
]
