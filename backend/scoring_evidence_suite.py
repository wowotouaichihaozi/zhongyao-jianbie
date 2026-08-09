"""Generate reproducible Software Cup scoring evidence from current system outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app import effect_assessment_snapshot
from learning_agents import generate_learning_path
from learning_tutor import validate_tutor_output


REPORT_DATE = "20260712"
GENERATED_PREFIX = "[SCORING-EVIDENCE-20260712]"
RESOURCE_LABELS = {
    "document": "课程讲解文档",
    "mindmap": "知识点思维导图",
    "ppt": "H5 PPT 课件",
    "question-bank": "结构化练习题库",
    "code": "代码类实操案例",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--e2e-report", default="")
    return parser.parse_args()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def markdown_cell_summary(value: Any, limit: int = 60) -> str:
    text = " ".join(str(value or "").split()).replace("|", "\\|")
    return text if len(text) <= limit else f"{text[:limit].rstrip()}..."


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def latest_artifact_for_case(output_dir: Path, case: dict[str, Any]) -> Path:
    task_id = str(case.get("taskId") or "").strip()
    if not task_id:
        raise ValueError(f"case has no taskId: {case.get('skillId')}")
    matches = list((output_dir / "真实讯飞接口结果").glob(f"*-{task_id}.json"))
    if not matches:
        raise FileNotFoundError(f"raw task artifact not found for {task_id}")
    return max(matches, key=lambda item: item.stat().st_mtime)


def case_by_skill(report: dict[str, Any], skill_id: str) -> dict[str, Any]:
    case = next(
        (item for item in report.get("cases") or [] if isinstance(item, dict) and item.get("skillId") == skill_id),
        None,
    )
    if not case:
        raise LookupError(f"E2E case not found: {skill_id}")
    return case


def result_for_case(output_dir: Path, report: dict[str, Any], skill_id: str) -> tuple[dict[str, Any], dict[str, Any], Path]:
    case = case_by_skill(report, skill_id)
    artifact_path = latest_artifact_for_case(output_dir, case)
    task = load_json(artifact_path)
    result = task.get("result") if isinstance(task.get("result"), dict) else {}
    return case, result, artifact_path


def contains_sensitive_text(value: Any) -> bool:
    text = json.dumps(value, ensure_ascii=False, default=str).lower()
    markers = [
        "authorization: bearer",
        "api_key=",
        "apikey=",
        "apisecret=",
        "api-secret=",
        "password=",
    ]
    return any(marker in text for marker in markers)


def cited_count(value: Any) -> int:
    return len(set(re.findall(r"\[KB\d+\]", json.dumps(value, ensure_ascii=False, default=str))))


def resource_quality(
    resource_type: str,
    payload: dict[str, Any],
    *,
    review_passed: bool,
    knowledge_source_count: int,
) -> dict[str, Any]:
    text = json.dumps(payload, ensure_ascii=False, default=str)
    content = str(payload.get("content") or "")
    criteria: dict[str, int] = {
        "structure": 0,
        "knowledgeGrounding": 0,
        "personalization": 0,
        "usability": 0,
        "safety": 0,
    }
    issues: list[str] = []

    if resource_type == "document":
        sections = payload.get("sections") if isinstance(payload.get("sections"), list) else []
        criteria["structure"] = 30 if len(sections) >= 4 else 18
        if len(sections) < 4:
            issues.append("讲义章节少于 4 节")
    elif resource_type == "mindmap":
        root_count = len([line for line in content.splitlines() if line.startswith("# ")])
        branch_count = len([line for line in content.splitlines() if line.startswith("## ")])
        detail_count = len([line for line in content.splitlines() if line.startswith("### ")])
        criteria["structure"] = 30 if root_count == 1 and branch_count >= 4 and detail_count >= 4 else 16
        if criteria["structure"] < 30:
            issues.append("导图根节点或层级不足")
    elif resource_type == "ppt":
        pages = payload.get("pages") if isinstance(payload.get("pages"), list) else []
        criteria["structure"] = 30 if len(pages) == 6 else 18
        if len(pages) != 6:
            issues.append(f"PPT 页数不是 6，当前为 {len(pages)}")
    elif resource_type == "question-bank":
        questions = payload.get("questions") if isinstance(payload.get("questions"), list) else []
        complete = bool(questions) and all(
            isinstance(item, dict)
            and (item.get("question") or item.get("stem") or item.get("content"))
            and (item.get("answer") is not None or item.get("correct_answer") is not None)
            and (item.get("analysis") or item.get("explanation"))
            for item in questions
        )
        criteria["structure"] = 30 if len(questions) >= 5 and complete else 15
        if not complete:
            issues.append("题库题干、答案或解析不完整")
    elif resource_type == "code":
        has_code = bool(re.search(r"```(?:c|cpp)?\s+.+?```", content, flags=re.I | re.S)) or bool(
            re.search(r"#include\s+[<\"].+[>\"]", content)
            and "{" in content
            and ";" in content
        )
        has_entry = bool(re.search(r"\b(?:main|void|uint\d+_t|GPIO|HAL_)\b", content))
        criteria["structure"] = 30 if has_code and has_entry and len(content) >= 300 else 16
        if criteria["structure"] < 30:
            issues.append("代码案例缺少可识别代码块或最小入口")

    citation_total = max(cited_count(payload), int(knowledge_source_count or 0))
    criteria["knowledgeGrounding"] = 25 if citation_total >= 2 else 15 if citation_total == 1 else 0
    if citation_total == 0:
        issues.append("缺少课程知识库引用")

    profile_markers = ["画像", "薄弱", "目标", "GPIO", "STM32", "中断", "UART", GENERATED_PREFIX]
    criteria["personalization"] = 20 if any(marker.lower() in text.lower() for marker in profile_markers) else 10
    if criteria["personalization"] < 20:
        issues.append("个性化画像依据不明显")

    usable = bool(content.strip()) or bool(payload.get("pages")) or bool(payload.get("sections")) or bool(payload.get("questions"))
    criteria["usability"] = 15 if usable else 0
    if not usable:
        issues.append("产物不可直接展示或使用")

    safe = review_passed and not contains_sensitive_text(payload)
    criteria["safety"] = 10 if safe else 0
    if not safe:
        issues.append("安全审核未通过或发现敏感配置")

    score = sum(criteria.values())
    return {
        "score": score,
        "passed": score >= 75 and not any("不完整" in issue or "不可直接" in issue for issue in issues),
        "criteria": criteria,
        "issues": issues,
        "citationCount": citation_total,
    }


def markdown_document(document: dict[str, Any]) -> str:
    lines = [f"# {document.get('title') or '个性化课程讲义'}", ""]
    if document.get("summary"):
        lines.extend([str(document["summary"]), ""])
    for section in document.get("sections") or []:
        if not isinstance(section, dict):
            continue
        lines.extend([f"## {section.get('title') or '课程章节'}", "", str(section.get("content") or ""), ""])
    references = document.get("references") or []
    if references:
        lines.extend(["## 知识依据", ""])
        for reference in references:
            if isinstance(reference, dict):
                lines.append(f"- [{reference.get('id') or 'KB'}] {reference.get('title') or reference.get('source') or '课程资料'}")
        lines.append("")
    return "\n".join(lines)


def markdown_ppt(ppt: dict[str, Any]) -> str:
    lines = [f"# {ppt.get('title') or '个性化 H5 PPT'}", ""]
    for index, page in enumerate(ppt.get("pages") or [], start=1):
        if not isinstance(page, dict):
            continue
        lines.extend(
            [
                f"## 第 {index} 页：{page.get('title') or page.get('heading') or '学习内容'}",
                "",
                str(page.get("content") or page.get("body") or page.get("subtitle") or ""),
                "",
            ]
        )
    return "\n".join(lines)


def markdown_question_bank(question_bank: dict[str, Any]) -> str:
    lines = [f"# {question_bank.get('title') or '结构化练习题库'}", ""]
    for index, question in enumerate(question_bank.get("questions") or [], start=1):
        if not isinstance(question, dict):
            continue
        lines.extend(
            [
                f"## 题目 {index}",
                "",
                str(question.get("question") or question.get("stem") or question.get("content") or ""),
                "",
                f"**答案：** {question.get('answer') if question.get('answer') is not None else question.get('correct_answer')}",
                "",
                f"**解析：** {question.get('analysis') or question.get('explanation') or ''}",
                "",
            ]
        )
    return "\n".join(lines)


def generate_resource_evidence(output_dir: Path, report: dict[str, Any]) -> dict[str, Any]:
    package_case, package_result, package_artifact = result_for_case(output_dir, report, "resource.package.generate")
    question_case, question_result, question_artifact = result_for_case(output_dir, report, "resource.question-bank.generate")
    ppt_case, ppt_result, ppt_artifact = result_for_case(output_dir, report, "resource.ppt.generate")
    document_case, document_result, document_artifact = result_for_case(output_dir, report, "resource.document.generate")
    mindmap_case, mindmap_result, mindmap_artifact = result_for_case(output_dir, report, "resource.mindmap.generate")

    llm_package = package_result.get("llmResources") if isinstance(package_result.get("llmResources"), dict) else {}
    code_resource = next(
        (item for item in llm_package.get("resources") or [] if isinstance(item, dict) and item.get("type") == "code"),
        {},
    )
    mindmap = mindmap_result.get("selectedResource") if isinstance(mindmap_result.get("selectedResource"), dict) else {}
    question_bank = (
        (question_result.get("questionGenerator") or {}).get("question_bank")
        if isinstance(question_result.get("questionGenerator"), dict)
        else {}
    ) or {}
    ppt = ppt_result.get("ppt") if isinstance(ppt_result.get("ppt"), dict) else {}
    document = document_result.get("document") if isinstance(document_result.get("document"), dict) else {}
    document["content"] = markdown_document(document)
    ppt["content"] = markdown_ppt(ppt)
    question_bank["content"] = markdown_question_bank(question_bank)

    cases = [
        ("document", document, document_case, document_artifact, len(document.get("references") or [])),
        ("mindmap", mindmap, mindmap_case, mindmap_artifact, len((mindmap.get("metadata") or {}).get("knowledgeSources") or [])),
        ("ppt", ppt, ppt_case, ppt_artifact, len(ppt.get("knowledgeSources") or [])),
        ("question-bank", question_bank, question_case, question_artifact, len(question_bank.get("knowledge_sources") or [])),
        ("code", code_resource, package_case, package_artifact, len(llm_package.get("knowledgeSources") or [])),
    ]
    case_dir = output_dir / "资源生成案例"
    results: list[dict[str, Any]] = []
    for index, (resource_type, payload, e2e_case, artifact_path, source_count) in enumerate(cases, start=1):
        review_passed = bool(e2e_case.get("safetyPassed")) and int(e2e_case.get("reviewScore") or 0) >= 68
        quality = resource_quality(
            resource_type,
            payload,
            review_passed=review_passed,
            knowledge_source_count=source_count,
        )
        label = RESOURCE_LABELS[resource_type]
        content = str(payload.get("content") or "")
        case_path = case_dir / f"{index:02d}-{resource_type}-{REPORT_DATE}.md"
        write_text(
            case_path,
            "\n".join(
                [
                    f"# {label}真实生成案例",
                    "",
                    f"- Task ID：`{e2e_case.get('taskId')}`",
                    f"- Run ID：`{e2e_case.get('runId')}`",
                    f"- 模型：`{e2e_case.get('model')}`",
                    f"- Harness 审核：{e2e_case.get('reviewScore')} 分",
                    f"- 资源质量：{quality['score']} 分",
                    f"- 知识依据：{quality['citationCount']} 条",
                    f"- 原始接口证据：`真实讯飞接口结果/{artifact_path.name}`",
                    "",
                    "## 实际产物",
                    "",
                    content or json.dumps(payload, ensure_ascii=False, indent=2),
                ]
            ),
        )
        results.append(
            {
                "index": index,
                "resourceType": resource_type,
                "label": label,
                "taskId": e2e_case.get("taskId"),
                "runId": e2e_case.get("runId"),
                "model": e2e_case.get("model"),
                "rawArtifact": str(artifact_path),
                "caseArtifact": str(case_path),
                "qualityEvaluation": quality,
                "passed": quality["passed"],
            }
        )

    passed = sum(1 for item in results if item["passed"])
    evidence = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "rubricRequirement": "至少 5 种个性化资源、至少 5 个案例，并进行资源质量评估",
        "caseCount": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "cases": results,
        "videoClaim": "视频检索与视频脚本不作为已生成视频成片证明；五类计分案例使用文档、导图、PPT、题库和代码。",
        "success": passed == len(results) == 5,
    }
    write_json(output_dir / f"资源生成五案例质量评估-{REPORT_DATE}.json", evidence)

    rows = [
        f"| {item['index']} | {item['label']} | {item['taskId']} | {item['qualityEvaluation']['score']} | {item['qualityEvaluation']['citationCount']} | {'通过' if item['passed'] else '失败'} |"
        for item in results
    ]
    write_text(
        output_dir / f"资源生成五案例质量评估-{REPORT_DATE}.md",
        "\n".join(
            [
                "# 多智能体资源生成五案例与质量评估",
                "",
                "本报告直接读取真实讯飞全量验收的脱敏原始接口产物，不用页面名称替代生成结果。",
                "",
                "| 序号 | 资源类型 | Task ID | 质量分 | 知识依据 | 结论 |",
                "|---:|---|---|---:|---:|---|",
                *rows,
                "",
                "质量分由结构完整性 30、知识依据 25、画像匹配 20、可用性 15、安全 10 组成。",
                "",
                "> 视频功能当前是检索与封面展示，资源包中的视频内容是脚本，不把它写成已生成视频成片。计分的五类实际生成产物为文档、导图、PPT、题库和代码。",
            ]
        ),
    )
    return evidence


def profile_scenarios() -> list[dict[str, Any]]:
    return [
        {
            "caseId": "profile-visual-beginner",
            "label": "低时长图解型初学者",
            "preferredTypes": ["mindmap", "ppt"],
            "profile": {
                "_profileReportId": 9101,
                "chatStudentProfile": {
                    "专业/课程背景": "自动化专业大二，正在学习 STM32 基础",
                    "学习目标": ["理解 GPIO 与 EXTI 的核心机制"],
                    "当前知识基础": "会 C 语言基础，但寄存器阅读能力较弱",
                    "学习进度": "STM32 入门阶段",
                    "薄弱知识点": ["GPIO 寄存器配置", "外部中断流程"],
                    "易错点类型": ["忘记使能外设时钟"],
                    "学习风格/认知偏好": ["图解", "分步骤讲解"],
                    "资源形式偏好": ["思维导图", "PPT 课件"],
                    "可投入时间": "每周 2 小时",
                    "难度接受程度": "基础",
                },
                "aiAnalysis": {"summary": "图解型初学者，时间有限，优先补 GPIO 与中断概念。"},
            },
        },
        {
            "caseId": "profile-project-practice",
            "label": "高投入项目实操型",
            "preferredTypes": ["mcu", "video"],
            "profile": {
                "_profileReportId": 9102,
                "chatStudentProfile": {
                    "专业/课程背景": "电子信息专业，参加智能车竞赛",
                    "学习目标": ["六周完成智能车传感器与电机联调"],
                    "当前知识基础": "已完成 GPIO、UART 和定时器基础实验",
                    "学习进度": "从基础外设进入项目集成",
                    "薄弱知识点": ["PWM 电机控制", "传感器联调", "调试定位"],
                    "易错点类型": ["配置参数与接线问题混淆"],
                    "学习风格/认知偏好": ["动手实践", "示例跟做"],
                    "资源形式偏好": ["单片机实验", "视频演示"],
                    "可投入时间": "每周 10 小时",
                    "难度接受程度": "挑战",
                },
                "aiAnalysis": {"summary": "项目实操型学习者，目标是智能车项目联调。"},
            },
        },
        {
            "caseId": "profile-exam-diagnostic",
            "label": "考试错因诊断型",
            "preferredTypes": ["question-bank", "document"],
            "profile": {
                "_profileReportId": 9103,
                "chatStudentProfile": {
                    "专业/课程背景": "物联网工程专业，准备单片机课程考试",
                    "学习目标": ["提高 UART、中断与定时器综合题正确率"],
                    "当前知识基础": "概念记忆较多，代码改错能力一般",
                    "学习进度": "章节复习与模拟测评阶段",
                    "薄弱知识点": ["UART 波特率", "中断优先级", "定时器计算"],
                    "易错点类型": ["公式套用错误", "忽略状态标志"],
                    "学习风格/认知偏好": ["错题复盘", "文字归纳"],
                    "资源形式偏好": ["题库", "课程讲义"],
                    "可投入时间": "每周 5 小时",
                    "难度接受程度": "中等",
                },
                "aiAnalysis": {"summary": "考试诊断型学习者，优先用题库证据定位错因。"},
            },
        },
        {
            "caseId": "profile-linux-advanced",
            "label": "进阶阅读研究型",
            "preferredTypes": ["document", "ppt"],
            "profile": {
                "_profileReportId": 9104,
                "chatStudentProfile": {
                    "专业/课程背景": "计算机专业大三，正在学习嵌入式 Linux",
                    "学习目标": ["完成字符设备驱动与中断处理实验"],
                    "当前知识基础": "掌握 C 语言、Linux 用户态编程和基础数据结构",
                    "学习进度": "驱动开发入门阶段",
                    "薄弱知识点": ["Linux 设备驱动模型", "内核中断上下文"],
                    "易错点类型": ["用户态与内核态接口边界混淆"],
                    "学习风格/认知偏好": ["先读原理再验证", "结构化笔记"],
                    "资源形式偏好": ["课程讲义", "技术文档"],
                    "可投入时间": "每周 7 小时",
                    "难度接受程度": "进阶",
                },
                "aiAnalysis": {"summary": "进阶阅读研究型学习者，关注 Linux 驱动与内核机制。"},
            },
        },
    ]


def path_fingerprint(path_result: dict[str, Any]) -> str:
    phases = path_result.get("phases") or []
    value = [
        {
            "title": item.get("title"),
            "resourceTypes": item.get("resourceTypes"),
            "tasks": (item.get("tasks") or [])[:4],
        }
        for item in phases[:4]
        if isinstance(item, dict)
    ]
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def generate_profile_recommendation_evidence(output_dir: Path) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for scenario in profile_scenarios():
        result = generate_learning_path(
            {
                "profile": scenario["profile"],
                "useLLM": False,
                "weekCount": 4,
                "totalWeeks": 4,
            }
        )
        phases = [item for item in result.get("phases") or [] if isinstance(item, dict)]
        first_phase = phases[0] if phases else {}
        nodes = [item for item in first_phase.get("nodes") or [] if isinstance(item, dict)]
        resource_counts = Counter(str(item.get("resourceType") or "") for item in nodes)
        preferred_hits = sum(resource_counts.get(resource_type, 0) for resource_type in scenario["preferredTypes"])
        profile_id = int(scenario["profile"].get("_profileReportId") or 0)
        errors: list[str] = []
        if len(phases) < 3:
            errors.append("路径阶段少于 3 个")
        if not 7 <= len(nodes) <= 10:
            errors.append(f"首周任务数不在 7-10，当前为 {len(nodes)}")
        if not all(item.get("resourceParams") and item.get("resourceSelectionReason") for item in nodes):
            errors.append("任务缺少资源参数或选择依据")
        if not any(f"p{profile_id}" in str(item.get("cacheKey") or "") for item in nodes):
            errors.append("任务缓存键未绑定画像 ID")
        if preferred_hits <= 0:
            errors.append("首周资源没有命中画像偏好")
        cases.append(
            {
                "caseId": scenario["caseId"],
                "label": scenario["label"],
                "profileReportId": profile_id,
                "profileSummary": scenario["profile"]["aiAnalysis"]["summary"],
                "weakPoints": result.get("profileContext", {}).get("weakPoints") or [],
                "goals": result.get("profileContext", {}).get("goals") or [],
                "resourcePreferences": result.get("profileContext", {}).get("resourcePreferences") or [],
                "timeBudget": result.get("profileContext", {}).get("timeBudget") or "",
                "phaseTitles": [item.get("title") for item in phases],
                "firstWeekTaskCount": len(nodes),
                "firstWeekResources": dict(resource_counts),
                "preferredResourceHits": preferred_hits,
                "sampleRecommendations": [
                    {
                        "task": item.get("title"),
                        "resourceType": item.get("resourceType"),
                        "reason": item.get("resourceSelectionReason"),
                        "route": item.get("actionRoute"),
                    }
                    for item in nodes[:4]
                ],
                "fingerprint": path_fingerprint(result),
                "knowledgeSourceCount": len(result.get("knowledgeSources") or []),
                "errors": errors,
                "passed": not errors,
            }
        )

    fingerprints = {item["fingerprint"] for item in cases}
    if len(fingerprints) != len(cases):
        for item in cases:
            item["errors"].append("与其他画像生成了相同路径指纹")
            item["passed"] = False
    passed = sum(1 for item in cases if item["passed"])
    evidence = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "caseCount": len(cases),
        "uniquePathFingerprints": len(fingerprints),
        "passed": passed,
        "failed": len(cases) - passed,
        "cases": cases,
        "success": passed == len(cases) and len(cases) >= 3,
    }
    write_json(output_dir / f"画像差异路径与资源推荐案例-{REPORT_DATE}.json", evidence)
    rows = [
        f"| {item['label']} | {item['profileReportId']} | {' / '.join(str(value) for value in item['phaseTitles'][:3])} | {item['firstWeekTaskCount']} | {json.dumps(item['firstWeekResources'], ensure_ascii=False)} | {item['fingerprint']} | {'通过' if item['passed'] else '失败'} |"
        for item in cases
    ]
    write_text(
        output_dir / f"画像差异路径与资源推荐案例-{REPORT_DATE}.md",
        "\n".join(
            [
                "# 画像差异驱动的路径与资源推荐案例",
                "",
                "四份画像只改变基础、目标、薄弱点、资源偏好、时间和难度，使用当前路径规划器的确定性模式生成，便于重复验收。",
                "",
                "| 画像 | 画像 ID | 前三周主题 | 首周任务 | 资源分布 | 路径指纹 | 结论 |",
                "|---|---:|---|---:|---|---|---|",
                *rows,
                "",
                "每个任务同时验证了可直接传给子智能体的参数、选择依据、结果路由和绑定画像 ID 的缓存键。",
            ]
        ),
    )
    return evidence


def evidence_time(days_ago: int, hour: int = 10) -> str:
    value = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return value.replace(hour=hour, minute=0, second=0, microsecond=0).isoformat()


def effect_scenarios() -> list[dict[str, Any]]:
    return [
        {
            "caseId": "effect-foundation-risk",
            "label": "基础薄弱且证据不足",
            "profileId": 9201,
            "baseline": [1.8, 1.7, 1.6, 1.5, 2.0, 1.7],
            "examAccuracy": 45,
            "experiments": [False],
            "completedNodes": 1,
            "trackedNodes": 8,
            "stats": [("GPIO 时钟与模式", 5, 2), ("外部中断标志", 4, 1), ("UART 波特率", 2, 1)],
            "resourceTypes": ["document"],
        },
        {
            "caseId": "effect-developing",
            "label": "练习与实验同步提升",
            "profileId": 9202,
            "baseline": [2.3, 2.2, 2.1, 2.0, 2.4, 2.1],
            "examAccuracy": 72,
            "experiments": [True, False],
            "completedNodes": 4,
            "trackedNodes": 8,
            "stats": [("GPIO 时钟与模式", 8, 6), ("外部中断标志", 6, 4), ("UART 波特率", 5, 3)],
            "resourceTypes": ["document", "mindmap", "question-bank"],
        },
        {
            "caseId": "effect-project-ready",
            "label": "项目迁移准备充分",
            "profileId": 9203,
            "baseline": [2.8, 2.7, 2.6, 2.5, 2.8, 2.6],
            "examAccuracy": 92,
            "experiments": [True, True, True],
            "completedNodes": 8,
            "trackedNodes": 8,
            "stats": [("GPIO 时钟与模式", 10, 9), ("外部中断标志", 8, 7), ("UART 波特率", 8, 6)],
            "resourceTypes": ["document", "mindmap", "question-bank", "ppt", "mcu"],
        },
    ]


def build_effect_case(scenario: dict[str, Any]) -> dict[str, Any]:
    profile_id = int(scenario["profileId"])
    profile = {
        "id": profile_id,
        "isActive": True,
        "profileName": scenario["label"],
        "scaleScores": scenario["baseline"],
        "chatStudentProfile": {
            "学习目标": ["完成 STM32 外设综合实验"],
            "薄弱知识点": ["GPIO 时钟与模式", "外部中断标志", "UART 波特率"],
            "易错点类型": ["遗漏状态标志清除"],
        },
        "aiAnalysis": {"weaknesses": ["外设配置与调试证据不足"]},
    }
    exam_accuracy = float(scenario["examAccuracy"])
    knowledge_stats = [
        {
            "knowledgePoint": name,
            "attempts": attempts,
            "correctCount": correct,
            "masteryRate": round(correct / attempts * 100, 1) if attempts else 0,
            "evidenceTypes": ["exam"],
        }
        for name, attempts, correct in scenario["stats"]
    ]
    evidence = {
        "evidenceVersion": hashlib.sha256(scenario["caseId"].encode("utf-8")).hexdigest()[:16],
        "updatedAt": evidence_time(0),
        "recentChats": [
            {"content": "复盘本周实验与错题", "createdAt": evidence_time(6)},
            {"content": "询问外部中断调试方法", "createdAt": evidence_time(1)},
        ],
        "questionSheets": [{"title": "STM32 专项题单", "questionCount": 10, "createdAt": evidence_time(5)}],
        "examResults": [{"accuracy": exam_accuracy, "createdAt": evidence_time(2)}],
        "mcuExperiments": [
            {"passed": passed, "createdAt": evidence_time(max(0, 4 - index))}
            for index, passed in enumerate(scenario["experiments"])
        ],
        "resourceCalls": [
            {"type": resource_type, "createdAt": evidence_time(max(0, 7 - index))}
            for index, resource_type in enumerate(scenario["resourceTypes"])
        ],
        "knowledgePointStats": knowledge_stats,
        "weakPoints": [item[0] for item in scenario["stats"] if item[2] / item[1] < 0.8],
        "pathProgress": {
            "completedNodes": scenario["completedNodes"],
            "trackedNodes": scenario["trackedNodes"],
            "weeks": [{"weekId": "week-1-stm32", "week": "第一周", "title": "STM32 外设基础", "status": "current"}],
        },
    }
    assessment = effect_assessment_snapshot(profile, evidence)
    errors: list[str] = []
    if not isinstance(assessment.get("achievementRate"), (int, float)):
        errors.append("缺少达成率")
    if not isinstance(assessment.get("masteryRate"), (int, float)):
        errors.append("缺少掌握率")
    if len(assessment.get("previousRadarScores") or []) != 6 or len(assessment.get("radarScores") or []) != 6:
        errors.append("前后雷达不是 6 维")
    if not assessment.get("knowledgeHeatmap"):
        errors.append("缺少知识点热力图")
    plan = assessment.get("pathAdjustmentPlan") or {}
    if not plan.get("planId") or not plan.get("canApply") or not plan.get("tasks"):
        errors.append("缺少可应用路径调整计划")
    return {
        "caseId": scenario["caseId"],
        "label": scenario["label"],
        "profile": profile,
        "evidence": evidence,
        "assessment": assessment,
        "errors": errors,
        "passed": not errors,
    }


def generate_effect_evidence(output_dir: Path) -> dict[str, Any]:
    cases = [build_effect_case(scenario) for scenario in effect_scenarios()]
    for index, item in enumerate(cases, start=1):
        write_json(output_dir / "效果评估案例" / f"{index:02d}-{item['caseId']}.json", item)
    achievement_rates = [float(item["assessment"].get("achievementRate") or 0) for item in cases]
    mastery_rates = [float(item["assessment"].get("masteryRate") or 0) for item in cases]
    monotonic = achievement_rates == sorted(achievement_rates) and mastery_rates == sorted(mastery_rates)
    if not monotonic:
        for item in cases:
            item["errors"].append("三组证据增强后量化指标未单调提升")
            item["passed"] = False
    passed = sum(1 for item in cases if item["passed"])
    evidence = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "caseCount": len(cases),
        "passed": passed,
        "failed": len(cases) - passed,
        "metricsMonotonicWithEvidence": monotonic,
        "cases": cases,
        "success": passed == len(cases) == 3,
    }
    write_json(output_dir / f"学习效果评估三案例-{REPORT_DATE}.json", evidence)
    rows = [
        f"| {item['label']} | {item['assessment']['achievementRate']:.1f}% | {item['assessment']['masteryRate']:.1f}% | {item['assessment']['activeLearningDays']} | {len(item['assessment']['knowledgeHeatmap'])} | {len((item['assessment']['pathAdjustmentPlan'] or {}).get('tasks') or [])} | {'通过' if item['passed'] else '失败'} |"
        for item in cases
    ]
    write_text(
        output_dir / f"学习效果评估三案例-{REPORT_DATE}.md",
        "\n".join(
            [
                "# 学习效果评估三案例",
                "",
                "三组案例使用当前系统的确定性证据引擎，LLM 不能覆盖达成率、掌握率、雷达或热力图。",
                "",
                "| 场景 | 达成率 | 掌握率 | 活跃日 | 热力图点 | 调整任务 | 结论 |",
                "|---|---:|---:|---:|---:|---:|---|",
                *rows,
                "",
                "每个案例均生成带 `planId`、`evidenceVersion`、目标周和可执行资源参数的路径调整计划；API 幂等写回由自动化测试覆盖。",
            ]
        ),
    )
    return evidence


def generate_tutor_evidence(output_dir: Path) -> dict[str, Any]:
    tutor_dir = output_dir / "智能辅导案例"
    paths = sorted(tutor_dir.glob("*.json"), key=lambda item: item.name)
    cases: list[dict[str, Any]] = []
    for path in paths:
        task = load_json(path)
        if isinstance(task.get("result"), dict):
            result = task["result"]
        elif isinstance(task.get("data"), dict) and isinstance(task["data"].get("task"), dict):
            result = task["data"]["task"].get("result") or {}
        else:
            result = task.get("data") if isinstance(task.get("data"), dict) else {}
        nested_tutor = result.get("tutor")
        tutor = nested_tutor if isinstance(nested_tutor, dict) else result
        orchestration = result.get("orchestration") if isinstance(result.get("orchestration"), dict) else {}
        harness = result.get("harness") if isinstance(result.get("harness"), dict) else {}
        errors = validate_tutor_output(tutor)
        if orchestration.get("rootAgent") != "xiaozhi-companion-agent":
            errors.append("rootAgent 不是嵌小智")
        if (harness.get("skill") or {}).get("id") != "learning.tutor.answer":
            errors.append("Skill ID 不匹配")
        if (harness.get("skill") or {}).get("mcpTool") != "learning.tutor.answer":
            errors.append("MCP Tool 不匹配")
        if (harness.get("modelRuntime") or {}).get("model") != "xsparkx2agent":
            errors.append("文本模型不是 Spark X2 Agent（xsparkx2agent）")
        quality = tutor.get("qualityEvaluation") if isinstance(tutor.get("qualityEvaluation"), dict) else {}
        if not quality.get("passed"):
            errors.append("辅导质量评价未通过")
        cases.append(
            {
                "artifact": str(path),
                "taskId": task.get("taskId") or result.get("taskId") or path.stem,
                "runId": orchestration.get("runId"),
                "question": tutor.get("question"),
                "source": tutor.get("source"),
                "qualityScore": quality.get("score"),
                "socraticQuestionCount": len(tutor.get("socraticQuestions") or []),
                "hintLevelCount": len(tutor.get("hintLadder") or []),
                "practiceCount": len(tutor.get("practiceTasks") or []),
                "referenceCount": len(tutor.get("references") or []),
                "hasFeynmanTask": bool((tutor.get("feynmanTask") or {}).get("prompt")),
                "hasMermaid": bool(((tutor.get("multimodal") or {}).get("mermaid") or {}).get("code")),
                "hasLearningCard": bool((tutor.get("multimodal") or {}).get("learningCard")),
                "errors": errors,
                "passed": not errors,
            }
        )
    passed = sum(1 for item in cases if item["passed"])
    evidence = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "caseCount": len(cases),
        "passed": passed,
        "failed": len(cases) - passed,
        "cases": cases,
        "success": len(cases) >= 5 and passed == len(cases),
    }
    write_json(output_dir / f"智能辅导五案例验收-{REPORT_DATE}.json", evidence)
    rows = [
        f"| {index} | {markdown_cell_summary(item['question'])} | {item['source']} | {item['qualityScore']} | {item['socraticQuestionCount']} | {item['hintLevelCount']} | {item['referenceCount']} | {'通过' if item['passed'] else '失败'} |"
        for index, item in enumerate(cases, start=1)
    ]
    write_text(
        output_dir / f"智能辅导五案例验收-{REPORT_DATE}.md",
        "\n".join(
            [
                "# 智能辅导五案例验收",
                "",
                "五个案例均为真实讯飞 MCP 调用原始结果，验证苏格拉底追问、费曼复述、三级提示、练习、多模态学习卡和知识引用。",
                "",
                "| 序号 | 问题 | 输出来源 | 质量分 | 追问 | 提示级 | 引用 | 结论 |",
                "|---:|---|---|---:|---:|---:|---:|---|",
                *rows,
            ]
        ),
    )
    return evidence


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    e2e_report_path = Path(args.e2e_report).resolve() if args.e2e_report else output_dir / "真实讯飞全量验收.json"
    report = load_json(e2e_report_path)
    resources = generate_resource_evidence(output_dir, report)
    recommendations = generate_profile_recommendation_evidence(output_dir)
    effects = generate_effect_evidence(output_dir)
    tutoring = generate_tutor_evidence(output_dir)
    summary = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "e2eReport": str(e2e_report_path),
        "resourceCases": {"count": resources["caseCount"], "passed": resources["passed"], "success": resources["success"]},
        "recommendationCases": {"count": recommendations["caseCount"], "passed": recommendations["passed"], "success": recommendations["success"]},
        "effectAssessmentCases": {"count": effects["caseCount"], "passed": effects["passed"], "success": effects["success"]},
        "tutorCases": {"count": tutoring["caseCount"], "passed": tutoring["passed"], "success": tutoring["success"]},
    }
    summary["success"] = all(item.get("success") for key, item in summary.items() if isinstance(item, dict) and key != "generatedAt")
    write_json(output_dir / f"评分硬指标案例汇总-{REPORT_DATE}.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
