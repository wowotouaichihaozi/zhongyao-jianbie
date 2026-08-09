"""Grounded course handout generation and deterministic quality evaluation."""

from __future__ import annotations

import json
import re
import sqlite3
from typing import Any

try:
    from learning_agents import call_llm_json
except ImportError:  # pragma: no cover
    from .learning_agents import call_llm_json


DOCUMENT_MIN_SECTIONS = 4
DOCUMENT_MAX_SECTIONS = 8


def _text(value: object, limit: int = 6000) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _string_list(value: object, limit: int = 8) -> list[str]:
    if isinstance(value, str):
        values = re.split(r"[\n；;]+", value)
    elif isinstance(value, list):
        values = value
    else:
        values = []
    return list(dict.fromkeys(_text(item, 500) for item in values if _text(item, 500)))[:limit]


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


def _normalize_section(item: object, index: int) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    title = _text(item.get("title") or item.get("heading"), 160)
    content = _text(item.get("content") or item.get("body") or item.get("summary"), 6000)
    if not title or not content:
        return None
    return {
        "order": index,
        "title": title,
        "summary": _text(item.get("summary"), 500),
        "content": content,
        "keyPoints": _string_list(item.get("keyPoints") or item.get("points"), 8),
        "example": _text(item.get("example"), 2000),
        "codeExample": str(item.get("codeExample") or item.get("code") or "").strip()[:5000],
    }


def _normalize_practice(item: object, index: int) -> dict[str, Any] | None:
    if isinstance(item, str):
        task = _text(item, 600)
        return {"order": index, "task": task, "expectedEvidence": "提交可复盘的答案或实验记录", "hint": ""} if task else None
    if not isinstance(item, dict):
        return None
    task = _text(item.get("task") or item.get("question") or item.get("title"), 800)
    if not task:
        return None
    return {
        "order": index,
        "task": task,
        "expectedEvidence": _text(item.get("expectedEvidence") or item.get("output"), 600),
        "hint": _text(item.get("hint"), 600),
    }


def _fallback_document(payload: dict[str, Any], reason: str) -> dict[str, Any]:
    topic = _text(payload.get("topic") or payload.get("title") or "嵌入式系统专题", 120)
    hits = [item for item in (payload.get("knowledgeContext") or []) if isinstance(item, dict)]
    references = _known_references(payload)
    sections: list[dict[str, Any]] = []
    for index, hit in enumerate(hits[:DOCUMENT_MAX_SECTIONS], start=1):
        citation_id = _text(hit.get("citationId") or (references[index - 1]["id"] if index <= len(references) else ""), 40)
        excerpt = _text(hit.get("excerpt") or hit.get("content"), 3000)
        if not excerpt:
            continue
        suffix = f" [{citation_id}]" if citation_id else "（需进一步核验）"
        sections.append(
            {
                "order": index,
                "title": _text(hit.get("title") or f"{topic}知识单元 {index}", 160),
                "summary": f"根据课程知识库整理的第 {index} 个学习单元。",
                "content": f"{excerpt}{suffix}",
                "keyPoints": [f"从知识库片段提炼并使用 {citation_id or '待核验标记'} 追溯"],
                "example": "",
                "codeExample": "",
            }
        )
    fallback_titles = ["学习目标与前置知识", "核心概念与工作流程", "常见错误与诊断方法", "实验验证与复盘"]
    while len(sections) < DOCUMENT_MIN_SECTIONS:
        index = len(sections)
        sections.append(
            {
                "order": index + 1,
                "title": fallback_titles[index],
                "summary": f"围绕{topic}建立可执行的学习步骤。",
                "content": "课程知识库未提供足够直接证据，本节只给出学习组织框架；涉及硬件参数、寄存器位定义和时序结论时需进一步核验。",
                "keyPoints": ["先确认数据手册或课程资料", "完成最小实验并记录输入、输出和异常"],
                "example": "",
                "codeExample": "",
            }
        )
    return {
        "title": f"{topic}个性化学习讲义",
        "abstract": f"面向当前学习画像整理的{topic}课程讲义。由于模型生成未完成，正文优先使用课程知识库片段并标注待核验内容。",
        "audience": "嵌入式课程学习者",
        "learningObjectives": [f"建立{topic}的概念结构", "完成一次可复盘的实践验证", "识别并解释至少两类常见错误"],
        "sections": sections,
        "keyPoints": [f"围绕{topic}形成概念、实践、测评和复盘闭环"],
        "commonMistakes": ["没有先核对芯片型号和数据手册", "只记录成功现象，没有保留错误与修正证据"],
        "practiceTasks": [
            {"order": 1, "task": f"用自己的话解释{topic}的输入、处理和输出", "expectedEvidence": "一段费曼式复述", "hint": "避免照抄术语"},
            {"order": 2, "task": f"完成一个{topic}最小实验并记录现象", "expectedEvidence": "代码、配置、现象和复盘记录", "hint": "先定义验收条件"},
        ],
        "summary": f"本讲义将{topic}拆成知识理解、错误诊断和实践验证三个层次。",
        "references": references,
        "verificationNotes": ["涉及具体硬件参数、寄存器位定义和时序要求时，请以芯片手册为准。"],
        "source": "knowledge-template-fallback",
        "fallbackReason": _text(reason, 500),
    }


def _normalize_document(raw: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    topic = _text(payload.get("topic") or payload.get("title") or "嵌入式系统专题", 120)
    sections = [
        section
        for index, item in enumerate(raw.get("sections") or [], start=1)
        if (section := _normalize_section(item, index)) is not None
    ][:DOCUMENT_MAX_SECTIONS]
    if len(sections) < DOCUMENT_MIN_SECTIONS:
        raise ValueError(f"课程讲义有效章节不足 {DOCUMENT_MIN_SECTIONS} 个")
    practices = [
        practice
        for index, item in enumerate(raw.get("practiceTasks") or raw.get("practice") or [], start=1)
        if (practice := _normalize_practice(item, index)) is not None
    ][:8]
    if not practices:
        practices = [{"order": 1, "task": f"完成一个{topic}最小验证任务", "expectedEvidence": "答案、代码或实验记录", "hint": "先写验收条件"}]
    known = _known_references(payload)
    known_by_id = {item["id"]: item for item in known}
    requested_ids = _string_list(
        [item.get("id") for item in raw.get("references") or [] if isinstance(item, dict)],
        12,
    )
    references = [known_by_id[item] for item in requested_ids if item in known_by_id]
    if not references:
        references = known
    document = {
        "title": _text(raw.get("title") or f"{topic}个性化学习讲义", 180),
        "abstract": _text(raw.get("abstract") or raw.get("summary"), 1200),
        "audience": _text(raw.get("audience") or "嵌入式课程学习者", 300),
        "learningObjectives": _string_list(raw.get("learningObjectives") or raw.get("objectives"), 8),
        "sections": sections,
        "keyPoints": _string_list(raw.get("keyPoints"), 12),
        "commonMistakes": _string_list(raw.get("commonMistakes"), 10),
        "practiceTasks": practices,
        "summary": _text(raw.get("summary"), 1200),
        "references": references,
        "verificationNotes": _string_list(raw.get("verificationNotes"), 8),
        "source": "llm",
    }
    if not references:
        document["verificationNotes"].append("课程知识库未命中直接证据，具体硬件事实需进一步核验。")
    return document


def document_markdown(document: dict[str, Any]) -> str:
    lines = [f"# {document.get('title') or '课程学习讲义'}", ""]
    if document.get("abstract"):
        lines.extend([str(document["abstract"]), ""])
    objectives = document.get("learningObjectives") or []
    if objectives:
        lines.append("## 学习目标")
        lines.extend(f"- {item}" for item in objectives)
        lines.append("")
    for section in document.get("sections") or []:
        lines.extend([f"## {section.get('order')}. {section.get('title')}", "", str(section.get("content") or ""), ""])
        if section.get("keyPoints"):
            lines.extend(f"- {item}" for item in section["keyPoints"])
            lines.append("")
        if section.get("example"):
            lines.extend(["### 示例", str(section["example"]), ""])
        if section.get("codeExample"):
            lines.extend(["```c", str(section["codeExample"]), "```", ""])
    if document.get("commonMistakes"):
        lines.append("## 常见错误")
        lines.extend(f"- {item}" for item in document["commonMistakes"])
        lines.append("")
    if document.get("practiceTasks"):
        lines.append("## 巩固任务")
        for item in document["practiceTasks"]:
            lines.append(f"{item.get('order')}. {item.get('task')}")
            if item.get("expectedEvidence"):
                lines.append(f"   - 验收证据：{item['expectedEvidence']}")
        lines.append("")
    if document.get("references"):
        lines.append("## 课程知识库来源")
        lines.extend(f"- [{item['id']}] {item['title']}（{item['locator']}）" for item in document["references"])
        lines.append("")
    if document.get("verificationNotes"):
        lines.append("## 核验说明")
        lines.extend(f"- {item}" for item in document["verificationNotes"])
    return "\n".join(lines).strip() + "\n"


def evaluate_learning_document(document: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    sections = document.get("sections") or []
    references = document.get("references") or []
    practices = document.get("practiceTasks") or []
    profile_summary = _profile_summary(profile)
    serialized = json.dumps(document, ensure_ascii=False, default=str)
    sensitive = bool(re.search(r"(?i)(api[_-]?key|api[_-]?secret|password|bearer)\s*[:=]\s*[A-Za-z0-9._:/+-]{16,}", serialized))
    structure_score = min(30, 10 + len(sections) * 4 + (4 if document.get("learningObjectives") else 0))
    grounding_score = min(30, len(references) * 5 + (10 if "[KB" in serialized else 0))
    personalization_score = 20 if any(profile_summary.get(key) for key in ("learningStyle", "goals", "weakPoints", "resourcePreference")) else 8
    practice_score = min(10, len(practices) * 4 + (2 if any(item.get("expectedEvidence") for item in practices) else 0))
    safety_score = 0 if sensitive else 10
    score = max(0, min(100, structure_score + grounding_score + personalization_score + practice_score + safety_score))
    issues: list[str] = []
    if len(sections) < DOCUMENT_MIN_SECTIONS:
        issues.append("有效章节不足")
    if not references:
        issues.append("课程知识库未命中直接引用，硬件事实需要人工核验")
    if sensitive:
        issues.append("检测到疑似敏感凭据")
    return {
        "score": score,
        "passed": bool(score >= 75 and len(sections) >= DOCUMENT_MIN_SECTIONS and not sensitive),
        "criteria": {
            "structure": structure_score,
            "knowledgeGrounding": grounding_score,
            "personalization": personalization_score,
            "practiceReadiness": practice_score,
            "safety": safety_score,
        },
        "sectionCount": len(sections),
        "citationCount": len(references),
        "practiceCount": len(practices),
        "issues": issues,
        "verificationRequired": not bool(references),
    }


def generate_learning_document(payload: dict[str, Any]) -> dict[str, Any]:
    topic = _text(payload.get("topic") or payload.get("title") or "嵌入式系统专题", 120)
    profile = payload.get("profile") if isinstance(payload.get("profile"), dict) else {}
    profile_summary = _profile_summary(profile)
    references = _known_references(payload)
    knowledge_hits = [item for item in (payload.get("knowledgeContext") or []) if isinstance(item, dict)][:8]
    knowledge_text = "\n\n".join(
        f"[{_text(item.get('citationId'), 40)}] {_text(item.get('title'), 180)}\n{_text(item.get('excerpt') or item.get('content'), 1800)}"
        for item in knowledge_hits
    )
    system = """
你是嵌小智总控调用的课程讲解文档生成子智能体。
请生成面向高校嵌入式课程的个性化学习讲义，严格使用给定画像和课程知识片段。
涉及定义、寄存器、参数、接线和时序结论时必须使用给定 [KBn] 引用；没有依据的事实写“需进一步核验”，不得编造来源。
只输出 JSON，字段必须为 title、abstract、audience、learningObjectives、sections、keyPoints、commonMistakes、practiceTasks、summary、references、verificationNotes。
sections 为 4-8 项，每项包含 title、summary、content、keyPoints、example、codeExample；practiceTasks 每项包含 task、expectedEvidence、hint；references 只能引用输入中存在的 id。
"""
    prompt = f"""
讲义主题：{topic}
补充要求：{_text(payload.get('requirements') or payload.get('prompt'), 1200)}
当前画像：{json.dumps(profile_summary, ensure_ascii=False)}
允许引用：{json.dumps(references, ensure_ascii=False)}
课程知识片段：
{knowledge_text or '未检索到直接片段。所有具体硬件事实必须标记为需进一步核验。'}
"""
    attempts: list[dict[str, Any]] = []
    try:
        raw = call_llm_json(system, prompt, max_tokens=5200, repair=True, timeout=120)
        attempts.append({"stage": "initial", "status": "complete", "keys": list(raw.keys())[:30]})
        try:
            document = _normalize_document(raw, payload)
        except ValueError as validation_error:
            attempts.append({"stage": "schema_validation", "status": "failed", "error": str(validation_error)})
            repair_system = """
你是课程讲义 JSON 结构修订器。只修订输入 JSON 的结构和缺失内容，不改变主题，不新增输入中不存在的知识来源。
只输出一个 JSON 对象，字段为 title、abstract、audience、learningObjectives、sections、keyPoints、commonMistakes、practiceTasks、summary、references、verificationNotes。
sections 必须为 4-8 项且每项包含 title、summary、content、keyPoints、example、codeExample；references 只能使用允许引用中的 id；没有证据的硬件事实写“需进一步核验”。
"""
            repair_prompt = f"""
校验错误：{validation_error}
允许引用：{json.dumps(references, ensure_ascii=False)}
原始 JSON：{json.dumps(raw, ensure_ascii=False)[:14000]}
请补齐并返回完整合法对象。
"""
            repaired = call_llm_json(repair_system, repair_prompt, max_tokens=5200, repair=True, timeout=120)
            document = _normalize_document(repaired, payload)
            document["source"] = "llm-schema-repaired"
            attempts.append({"stage": "schema_repair", "status": "complete", "keys": list(repaired.keys())[:30]})
    except Exception as exc:
        attempts.append({"stage": "fallback", "status": "complete", "error": _text(exc, 500)})
        document = _fallback_document(payload, str(exc))
    document["profile"] = profile_summary
    document["generationAttempts"] = attempts
    document["markdown"] = document_markdown(document)
    quality = evaluate_learning_document(document, profile)
    return {
        "agent": "learning-document-agent",
        "source": document.get("source") or "llm",
        "document": document,
        "qualityEvaluation": quality,
        "generationAttempts": attempts,
    }


def save_learning_document(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    profile_report_id: int,
    task_id: str,
    run_id: str,
    topic: str,
    generated: dict[str, Any],
    timestamp: str,
) -> dict[str, Any]:
    document = generated.get("document") if isinstance(generated.get("document"), dict) else {}
    quality = generated.get("qualityEvaluation") if isinstance(generated.get("qualityEvaluation"), dict) else {}
    cursor = conn.execute(
        """
        INSERT INTO generated_learning_documents
            (user_id, profile_report_id, task_id, run_id, topic, title, document_json,
             quality_json, source, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(task_id) DO UPDATE SET
            profile_report_id = excluded.profile_report_id,
            run_id = excluded.run_id,
            topic = excluded.topic,
            title = excluded.title,
            document_json = excluded.document_json,
            quality_json = excluded.quality_json,
            source = excluded.source,
            updated_at = excluded.updated_at
        RETURNING id
        """,
        (
            int(user_id),
            int(profile_report_id or 0) or None,
            str(task_id or ""),
            str(run_id or ""),
            _text(topic, 180),
            _text(document.get("title") or topic, 240),
            json.dumps(document, ensure_ascii=False),
            json.dumps(quality, ensure_ascii=False),
            _text(generated.get("source"), 80),
            timestamp,
            timestamp,
        ),
    )
    row_id = int(cursor.fetchone()["id"])
    return get_learning_document(conn, user_id=user_id, document_id=row_id)


def _document_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "profileReportId": int(row["profile_report_id"] or 0),
        "taskId": str(row["task_id"] or ""),
        "runId": str(row["run_id"] or ""),
        "topic": str(row["topic"] or ""),
        "title": str(row["title"] or ""),
        "document": json.loads(str(row["document_json"] or "{}")),
        "qualityEvaluation": json.loads(str(row["quality_json"] or "{}")),
        "source": str(row["source"] or ""),
        "createdAt": str(row["created_at"] or ""),
        "updatedAt": str(row["updated_at"] or ""),
    }


def get_learning_document(conn: sqlite3.Connection, *, user_id: int, document_id: int) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM generated_learning_documents WHERE id = ? AND user_id = ? LIMIT 1",
        (int(document_id), int(user_id)),
    ).fetchone()
    return _document_row(row) if row else {}


def list_learning_documents(conn: sqlite3.Connection, *, user_id: int, limit: int = 30) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM generated_learning_documents WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (int(user_id), max(1, min(int(limit), 100))),
    ).fetchall()
    return [_document_row(row) for row in rows]
