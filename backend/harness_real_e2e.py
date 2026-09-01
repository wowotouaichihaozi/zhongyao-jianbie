"""Run every XiaoZhi skill against the real local service and XFYun model."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import requests


PREFIX = "[HARNESS-E2E-20260710]"
SENSITIVE_KEY_PARTS = ("api_key", "apikey", "api-secret", "apisecret", "password", "authorization", "token")
LEGACY_MODEL_MARKER = "mimo" + "-v2.5"


CASES = [
    (
        "learner.background.collect",
        {
            "topic": f"{PREFIX} 我正在学习 STM32 基础，希望补全学习目标、基础、偏好和每周时间",
            "message": "我会 C 语言基础，每周可学习 8 小时，希望完成 GPIO、串口和中断项目。",
        },
    ),
    (
        "learner.profile.refresh",
        {
            "topic": f"{PREFIX} 根据最近答题、实验和学习记录更新六维画像",
            "profileName": f"{PREFIX} 真实验收画像",
        },
    ),
    (
        "learner.profile.manage",
        {
            "topic": f"{PREFIX} 列出当前用户保留的画像及激活状态",
            "action": "list",
        },
    ),
    (
        "learning.path.generate",
        {"topic": f"{PREFIX} 基于当前画像生成 STM32 六周学习路径"},
    ),
    (
        "learning.path.stage-detail",
        {"topic": f"{PREFIX} 细化 STM32 基础第一阶段，包含目标、任务、资源、产出物和检查点"},
    ),
    (
        "resource.package.generate",
        {"topic": f"{PREFIX} STM32 基础五类资源包"},
    ),
    (
        "resource.question-bank.generate",
        {
            "topic": f"{PREFIX} STM32 GPIO 与中断题单",
            "course": "STM32",
            "chapter": "GPIO 与外部中断",
            "count": 10,
            "constraints": "题型、答案、解析完整，标记真实验收前缀。",
        },
    ),
    (
        "resource.ppt.generate",
        {
            "topic": f"{PREFIX} STM32 GPIO 与中断浅绿色课件",
            "pageCount": 6,
            "styleName": "嵌智学航工程教学风",
        },
    ),
    (
        "resource.document.generate",
        {
            "topic": f"{PREFIX} STM32 GPIO 与中断个性化课程讲义",
            "requirements": "至少四个章节，包含课程知识库引用、常见错误、实践任务和资源质量评价。",
        },
    ),
    (
        "resource.mindmap.generate",
        {"topic": f"{PREFIX} STM32 基础知识思维导图"},
    ),
    (
        "resource.video.search",
        {"topic": f"{PREFIX} STM32 GPIO 与中断学习视频"},
    ),
    (
        "resource.animation.generate",
        {
            "topic": f"{PREFIX} STM32 外部中断响应 H5 动画微课",
            "requirements": "至少四个场景、三种视觉表达、完整讲解词、知识检查和课程知识库引用。",
        },
    ),
    (
        "mcu.experiment.recommend",
        {"topic": f"{PREFIX} STM32 GPIO LED 与按键中断仿真实验"},
    ),
    (
        "knowledge.base.manage",
        {
            "topic": f"{PREFIX} 列出当前用户的私有课程知识库和激活状态",
            "action": "list",
        },
    ),
    (
        "interview.session.run",
        {"topic": f"{PREFIX} STM32 GPIO、中断与 UART 模拟面试"},
    ),
    (
        "learning.tutor.answer",
        {"topic": f"{PREFIX} 为什么 STM32 外部中断需要清除挂起标志，请结合当前画像讲解并给巩固任务"},
    ),
    (
        "learning.feedback.submit",
        {
            "topic": f"{PREFIX} STM32 GPIO 调试复盘反馈",
            "outcome": "needs_review",
            "resourceType": "document",
            "route": "/personalized-resources/document",
            "cacheKey": "harness-e2e-feedback-20260713",
            "difficulty": "appropriate",
            "helpful": True,
            "rating": 4,
            "note": "需要继续巩固 GPIO 时钟、模式配置和寄存器排查顺序。",
        },
    ),
    (
        "learning.effect.evaluate",
        {"topic": f"{PREFIX} 汇总答题、实验和面试证据，评估学习效果并给出路径调整建议"},
    ),
]


# The registry needs one probe per Skill, while the rubric requires five
# independently inspectable tutoring cases. Keep the four extra calls outside
# CASES so registry cardinality checks continue to describe the real Skill set.
ADDITIONAL_TUTOR_CASES = [
    (
        "learning.tutor.answer",
        {"topic": f"{PREFIX} GPIO output stays low after initialization. Guide me with Socratic questions and a Feynman recap."},
    ),
    (
        "learning.tutor.answer",
        {"topic": f"{PREFIX} UART output is garbled. Help me diagnose clock, baud rate, and frame format step by step."},
    ),
    (
        "learning.tutor.answer",
        {"topic": f"{PREFIX} A push-button interrupt triggers repeatedly. Guide me through debounce and interrupt-flag checks."},
    ),
    (
        "learning.tutor.answer",
        {"topic": f"{PREFIX} An ADC reading is unstable. Use progressive hints, a practice task, and knowledge citations."},
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:3000")
    parser.add_argument("--username", default=os.getenv("HARNESS_E2E_USERNAME", "admin123"))
    parser.add_argument("--password", default=os.getenv("HARNESS_E2E_PASSWORD", ""))
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--poll-seconds", type=float, default=3.0)
    parser.add_argument("--task-timeout", type=int, default=720)
    parser.add_argument(
        "--tool",
        action="append",
        choices=[tool_name for tool_name, _ in CASES],
        help="只运行指定 MCP Tool；可重复传入以续跑失败或未完成项",
    )
    return parser.parse_args()


def scrub(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            lowered = str(key).lower().replace("_", "")
            if any(part.replace("_", "").replace("-", "") in lowered for part in SENSITIVE_KEY_PARTS):
                if isinstance(item, bool):
                    cleaned[key] = item
                else:
                    cleaned[key] = "<redacted>"
            else:
                cleaned[key] = scrub(item)
        return cleaned
    if isinstance(value, list):
        return [scrub(item) for item in value]
    return value


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def nested(result: dict[str, Any], *keys: str) -> Any:
    value: Any = result
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def route_matches_manifest(expected_route: str, actual_route: str) -> bool:
    """Accept a manifest route or one of its concrete child pages."""
    expected_path = str(expected_route or "").split("?", 1)[0].rstrip("/") or "/"
    actual_path = str(actual_route or "").split("?", 1)[0].rstrip("/") or "/"
    if not str(expected_route or "").strip():
        return True
    return actual_path == expected_path or (
        expected_path != "/" and actual_path.startswith(f"{expected_path}/")
    )


def validate_specific(task_type: str, result: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if task_type == "learning_background":
        dialogue = result.get("dialogue") or {}
        if not isinstance(dialogue, dict) or not (dialogue.get("reply") or dialogue.get("question")):
            errors.append("学习背景未返回有效追问")
        if not isinstance(dialogue.get("missingFields") or [], list):
            errors.append("学习背景缺少 missingFields")
    elif task_type == "profile_update":
        analysis = nested(result, "report", "aiAnalysis") or {}
        dimensions = [
            analysis.get("learningStyle"),
            analysis.get("summary"),
            analysis.get("strengths"),
            analysis.get("weaknesses"),
            analysis.get("recommendations"),
            analysis.get("overallScore"),
        ]
        if sum(bool(item) for item in dimensions) < 6:
            errors.append("学习画像不足六个有效分析维度")
        if analysis.get("source") != "llm" or analysis.get("error"):
            errors.append("学习画像未由真实模型完成结构化生成")
    elif task_type == "profile_management":
        management = result.get("profileManagement") or {}
        if management.get("action") != "list":
            errors.append("画像管理未执行只读 list 动作")
        if not isinstance(management.get("profiles"), list):
            errors.append("画像管理未返回画像列表")
        if int(management.get("activeReportId") or 0) <= 0:
            errors.append("画像管理未返回当前激活画像")
    elif task_type == "learning_path":
        learning_path = result.get("learningPath") or {}
        phases = learning_path.get("phases") or []
        if len(phases) < 3:
            errors.append("学习路径阶段少于 3 个")
        if learning_path.get("source") != "llm" or learning_path.get("error") or learning_path.get("degraded"):
            errors.append("学习路径使用了规则降级结果，未完成真实模型结构化生成")
        profile_context = learning_path.get("profileContext") or {}
        time_budget = str(profile_context.get("timeBudget") or "").strip()
        if not time_budget or re.match(r"^\d{4}-\d{2}-\d{2}T", time_budget):
            errors.append("学习路径可投入时间缺失或被时间戳污染")
        goals = [str(item or "").strip() for item in profile_context.get("goals") or []]
        if any(re.match(r"^week-\d", item, flags=re.I) or re.fullmatch(r"第[一二三四五六七八九十百\d]+周", item) for item in goals):
            errors.append("学习路径目标混入周次或路由标识")
        preferences = [str(item or "").strip() for item in profile_context.get("resourcePreferences") or []]
        if any(item.startswith("{") or "updatedAt" in item or "'type':" in item for item in preferences):
            errors.append("学习路径资源偏好混入历史资源记录")
        topic_keywords = [str(item or "").strip() for item in profile_context.get("topicKeywords") or []]
        semantic_context = {
            key: value
            for key, value in profile_context.items()
            if key not in {"topicKeywords", "evidence"}
        }
        semantic_text = json_text(semantic_context)
        if "驱动开发基础" in topic_keywords and not re.search(r"Linux\s*驱动|设备驱动|驱动开发", semantic_text, flags=re.I):
            errors.append("学习路径把非驱动语义误判为驱动开发主题")
    elif task_type == "learning_path_stage":
        detail = result.get("stageDetail") or {}
        detail_text = json_text(detail)
        if not isinstance(detail, dict) or len(detail_text) < 200:
            errors.append("阶段细化内容为空或过短")
        if detail.get("source") != "llm" or detail.get("error") or detail.get("degraded"):
            errors.append("阶段细化使用了规则降级结果，未完成真实模型结构化生成")
        for key in ("goals", "weeks", "resources", "checkpoints"):
            if not detail.get(key):
                errors.append(f"阶段细化缺少 {key}")
    elif task_type == "personalized_resources":
        resources = nested(result, "workflow", "resources") or []
        resource_types = {str(item.get("type") or "") for item in resources if isinstance(item, dict)}
        expected = {"document", "mindmap", "ppt", "quiz", "video", "simulator"}
        if len(resource_types & expected) < 6:
            errors.append(f"六类资源不完整: {sorted(resource_types)}")
    elif task_type == "question_bank":
        question_bank = nested(result, "questionGenerator", "question_bank") or {}
        questions = question_bank.get("questions") or question_bank.get("items") or []
        if len(questions) != 10:
            errors.append(f"题库数量不是 10: {len(questions)}")
        if questions and not all(
            isinstance(item, dict)
            and (item.get("answer") is not None or item.get("correct_answer") is not None)
            and (item.get("analysis") or item.get("explanation"))
            for item in questions
        ):
            errors.append("题库答案或解析结构不完整")
    elif task_type == "ppt":
        ppt = result.get("ppt") or {}
        pages = ppt.get("pages") or ppt.get("slides") or nested(ppt, "presentation", "slides") or []
        if len(pages) != 6:
            errors.append(f"PPT 页数不是 6: {len(pages)}")
        if "浅绿" not in json_text(ppt) and "green" not in json_text(ppt).lower():
            errors.append("PPT 未体现默认浅绿色风格")
    elif task_type == "document":
        document = result.get("document") or {}
        quality = result.get("qualityEvaluation") or {}
        if len(document.get("sections") or []) < 4:
            errors.append("课程讲义章节少于 4 个")
        if not document.get("references"):
            errors.append("课程讲义缺少知识库引用")
        if int(quality.get("score") or 0) < 75 or not quality.get("passed"):
            errors.append("课程讲义质量评价未通过")
    elif task_type == "mindmap":
        selected = result.get("selectedResource") or {}
        content = str(selected.get("content") or "")
        branch_count = len([line for line in content.splitlines() if line.startswith("## ")])
        if not selected or not content.startswith("# ") or branch_count < 4:
            errors.append("思维导图资源为空")
    elif task_type == "video":
        selected = result.get("selectedResource") or {}
        selected_text = json_text(selected).lower()
        if not selected or not any(word in selected_text for word in ("thumbnail", "cover", "封面", "image")):
            errors.append("视频结果缺少有效封面字段")
    elif task_type == "animation":
        animation = result.get("animation") or {}
        scenes = animation.get("scenes") or []
        visual_types = {str(item.get("visualType") or "") for item in scenes if isinstance(item, dict)}
        if len(scenes) < 4:
            errors.append(f"H5 动画场景少于 4 个: {len(scenes)}")
        if len(visual_types) < 3:
            errors.append(f"H5 动画视觉类型少于 3 种: {sorted(visual_types)}")
        if not all(isinstance(item, dict) and item.get("narration") for item in scenes):
            errors.append("H5 动画存在缺少讲解词的场景")
        if not animation.get("references"):
            errors.append("H5 动画缺少课程知识库引用")
        if not (result.get("qualityEvaluation") or {}).get("passed"):
            errors.append("H5 动画质量评价未通过")
    elif task_type == "mcu":
        selected = result.get("selectedResource") or {}
        experiments = nested(selected, "metadata", "experiments") or []
        experiment_urls = [
            item.get("url")
            for item in experiments
            if isinstance(item, dict) and item.get("url")
        ]
        if not selected or not (selected.get("route") or selected.get("url") or experiment_urls):
            errors.append("MCU 实验缺少启动路由")
    elif task_type == "knowledge_base":
        knowledge_base = result.get("knowledgeBase") or {}
        if not isinstance(knowledge_base.get("collections"), list):
            errors.append("私有知识库未返回用户隔离的知识库目录")
        if "activeCollectionId" not in knowledge_base:
            errors.append("私有知识库未返回当前激活状态")
    elif task_type == "interview":
        interview = result.get("interview") or {}
        if not interview.get("sessionId"):
            errors.append("AI 面试未创建 sessionId")
        if not (interview.get("question") or interview.get("firstQuestion") or interview.get("message")):
            errors.append("AI 面试未返回首题")
    elif task_type == "smart_tutor":
        tutor = result.get("tutor") or {}
        if not (result.get("answer") or tutor.get("answer") or tutor.get("explanation")):
            errors.append("智能辅导未返回答案")
        if len(tutor.get("socraticQuestions") or []) < 3:
            errors.append("智能辅导缺少至少 3 个苏格拉底式追问")
        if len(tutor.get("hintLadder") or []) != 3:
            errors.append("智能辅导缺少三级提示")
        if not (tutor.get("feynmanTask") or {}).get("prompt"):
            errors.append("智能辅导缺少费曼复述任务")
        if not tutor.get("practiceTasks"):
            errors.append("智能辅导缺少巩固任务")
        if not (tutor.get("multimodal") or {}).get("mermaid") or not (tutor.get("multimodal") or {}).get("learningCard"):
            errors.append("智能辅导缺少 Mermaid 或学习卡多模态产物")
        if not (tutor.get("qualityEvaluation") or {}).get("passed"):
            errors.append("智能辅导质量评价未通过")
    elif task_type == "learning_feedback":
        feedback = result.get("feedback") or {}
        if int(feedback.get("id") or 0) <= 0:
            errors.append("学习反馈未持久化")
        if feedback.get("outcome") != "needs_review":
            errors.append("学习反馈结果与验收输入不一致")
        if int(feedback.get("profileReportId") or 0) <= 0:
            errors.append("学习反馈未关联当前画像")
        path_cache = feedback.get("pathCache") or {}
        cache_feedback = path_cache.get("learningFeedback") or {}
        if cache_feedback.get("outcome") != "needs_review":
            errors.append("学习反馈未回写学习路径证据")
    elif task_type == "effect_assessment":
        assessment = result.get("assessment") or {}
        if not assessment.get("summary"):
            errors.append("效果评估缺少总结")
        for metric in ("achievementRate", "masteryRate"):
            if not isinstance(assessment.get(metric), (int, float)):
                errors.append(f"效果评估缺少量化指标 {metric}")
        if len(assessment.get("previousRadarScores") or []) != 6 or len(assessment.get("radarScores") or []) != 6:
            errors.append("效果评估前后雷达数据不完整")
        if not assessment.get("knowledgeHeatmap"):
            errors.append("效果评估缺少知识点热力图")
        plan = assessment.get("pathAdjustmentPlan") or {}
        if not plan.get("planId") or not isinstance(plan.get("tasks"), list):
            errors.append("效果评估缺少可追踪的路径调整计划")
        if not (assessment.get("adjustments") or assessment.get("recommendations") or plan.get("tasks")):
            errors.append("效果评估缺少路径调整建议")
    return errors


def validate_common(
    tool_name: str,
    skill: dict[str, Any],
    task: dict[str, Any],
    expected_profile_id: int,
    expected_model: str,
) -> tuple[list[str], dict[str, Any]]:
    result = task.get("result") if isinstance(task.get("result"), dict) else {}
    orchestration = result.get("orchestration") if isinstance(result.get("orchestration"), dict) else {}
    harness = result.get("harness") if isinstance(result.get("harness"), dict) else {}
    mcp = harness.get("mcp") if isinstance(harness.get("mcp"), dict) else {}
    tool_calls = mcp.get("toolCalls") if isinstance(mcp.get("toolCalls"), list) else []
    review = orchestration.get("review") if isinstance(orchestration.get("review"), dict) else {}
    errors: list[str] = []
    if task.get("status") != "complete":
        errors.append(f"任务状态不是 complete: {task.get('status')}")
    if orchestration.get("rootAgent") != "xiaozhi-companion-agent":
        errors.append("rootAgent 不是嵌小智")
    if not orchestration.get("runId"):
        errors.append("缺少 runId")
    if not orchestration.get("handoffs"):
        errors.append("缺少 Handoff")
    if "score" not in review:
        errors.append("缺少质量审核")
    elif review.get("passed") is not True:
        errors.append(f"质量审核未通过: {review.get('issues') or []}")
    if "sensitiveContentDetected" not in review:
        errors.append("缺少安全审核")
    if nested(harness, "skill", "id") != skill.get("id"):
        errors.append("Skill ID 不匹配")
    if nested(harness, "skill", "mcpTool") != tool_name:
        errors.append("MCP Tool 不匹配")
    expected_route = str(skill.get("route") or "").split("?", 1)[0]
    actual_route = str(task.get("route") or "").split("?", 1)[0]
    if expected_route and not route_matches_manifest(expected_route, actual_route):
        errors.append(f"任务路由不匹配: expected={expected_route}, actual={actual_route}")
    if not tool_calls or any(call.get("status") != "complete" for call in tool_calls):
        errors.append("MCP Tool Call 未完成")
    if tool_calls and any(
        nested(call, "contract", "input") != "passed"
        or nested(call, "contract", "output") != "passed"
        for call in tool_calls
    ):
        errors.append("Skill 输入或输出 JSON 契约校验未通过")
    actual_model = str(nested(harness, "modelRuntime", "model") or "")
    if actual_model != expected_model:
        errors.append(f"模型与当前用户配置不一致: expected={expected_model}, actual={actual_model}")
    if int(harness.get("profileReportId") or 0) != int(expected_profile_id or 0):
        errors.append(
            f"画像 ID 不匹配: expected={expected_profile_id}, actual={harness.get('profileReportId')}"
        )
    response_text = json_text(scrub(task))
    if LEGACY_MODEL_MARKER in response_text.lower():
        errors.append("响应中仍出现旧模型标识")
    errors.extend(validate_specific(str(skill.get("taskType") or ""), result))
    summary = {
        "taskId": task.get("taskId"),
        "status": task.get("status"),
        "runId": orchestration.get("runId"),
        "profileReportId": harness.get("profileReportId"),
        "skillId": nested(harness, "skill", "id"),
        "mcpTool": nested(harness, "skill", "mcpTool"),
        "mcpStatus": [call.get("status") for call in tool_calls],
        "contractStatus": [call.get("contract") for call in tool_calls],
        "reviewScore": review.get("score"),
        "safetyPassed": not bool(review.get("sensitiveContentDetected")),
        "model": nested(harness, "modelRuntime", "model"),
        "outputKeys": sorted(result.keys()),
    }
    return errors, summary


def request_json(
    session: requests.Session,
    method: str,
    url: str,
    *,
    timeout: int = 60,
    **kwargs: Any,
) -> dict[str, Any]:
    response = session.request(method, url, timeout=timeout, **kwargs)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError(f"expected object response from {url}")
    return data


def mcp_request(
    session: requests.Session,
    base_url: str,
    method: str,
    params: dict[str, Any] | None = None,
    *,
    request_id: str,
) -> dict[str, Any]:
    response = session.post(
        f"{base_url.rstrip('/')}/api/xiaozhi/mcp",
        json={
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        },
        timeout=60,
    )
    response.raise_for_status()
    if not response.content.strip():
        return {"statusCode": response.status_code}
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError(f"MCP {method} returned a non-object response")
    if payload.get("error"):
        raise RuntimeError(f"MCP {method} failed: {json_text(payload['error'])}")
    return payload.get("result") if isinstance(payload.get("result"), dict) else {}


def main() -> int:
    args = parse_args()
    if not args.password:
        raise SystemExit("HARNESS_E2E_PASSWORD is required")
    output_dir = Path(args.output_dir).resolve()
    artifacts_dir = output_dir / "真实讯飞接口结果"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    login = request_json(
        session,
        "POST",
        f"{args.base_url.rstrip('/')}/api/auth/login",
        json={"username": args.username, "password": args.password},
    )
    token = str(login.get("token") or nested(login, "data", "token") or "")
    if not token:
        raise RuntimeError("login response did not contain a token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    profiles_payload = request_json(
        session,
        "GET",
        f"{args.base_url.rstrip('/')}/api/learning-profile/profiles",
    )
    active_profile_id = int(nested(profiles_payload, "data", "activeReportId") or 0)
    if active_profile_id <= 0:
        raise RuntimeError(
            "当前验收账号没有激活画像；请先通过真实多轮对话生成并激活画像。"
            "E2E 不会创建或注入假画像。"
        )
    skills_payload = request_json(session, "GET", f"{args.base_url.rstrip('/')}/api/xiaozhi/skills")
    skills = nested(skills_payload, "data", "skills") or []
    by_tool = {str(item.get("mcpTool")): item for item in skills if isinstance(item, dict)}
    if set(by_tool) != {tool for tool, _ in CASES}:
        raise RuntimeError(f"skill registry mismatch: {sorted(by_tool)}")
    selected_tools = set(args.tool or [])
    evidence_cases = [*CASES, *ADDITIONAL_TUTOR_CASES]
    run_cases = [case for case in evidence_cases if not selected_tools or case[0] in selected_tools]

    status_payload = request_json(session, "GET", f"{args.base_url.rstrip('/')}/api/xiaozhi/status")
    architecture = nested(status_payload, "data", "architecture") or {}
    configured_model = str(nested(status_payload, "data", "modelRuntime", "model") or "astron-code-latest")
    architecture_summary = {
        "rootAgent": architecture.get("rootAgent"),
        "architecture": architecture.get("architecture"),
        "agentCount": len(nested(architecture, "orchestration", "agents") or []),
        "skillCount": int(nested(architecture, "skillRegistry", "skillCount") or 0),
        "handlerCount": int(nested(architecture, "handlerRegistry", "handlerCount") or 0),
        "mcpToolCount": int(nested(architecture, "mcpGateway", "toolCount") or 0),
        "mcpResourceCount": int(nested(architecture, "mcpGateway", "resourceCount") or 0),
        "mcpPromptCount": int(nested(architecture, "mcpGateway", "promptCount") or 0),
        "mcpServerCount": len(nested(architecture, "mcpGateway", "servers") or []),
        "mcpProtocolVersion": nested(architecture, "mcpGateway", "protocolVersion"),
    }
    expected_counts = {
        "skillCount": len(CASES),
        "handlerCount": len(CASES),
        "mcpToolCount": len(CASES),
    }
    count_errors = [
        f"{key}: expected={expected}, actual={architecture_summary.get(key)}"
        for key, expected in expected_counts.items()
        if architecture_summary.get(key) != expected
    ]
    minimum_counts = {"agentCount": 23, "mcpServerCount": 6}
    count_errors.extend(
        f"{key}: expected>={minimum}, actual={architecture_summary.get(key)}"
        for key, minimum in minimum_counts.items()
        if int(architecture_summary.get(key) or 0) < minimum
    )
    if architecture_summary.get("rootAgent") != "xiaozhi-companion-agent":
        count_errors.append(f"rootAgent={architecture_summary.get('rootAgent')}")
    if count_errors:
        raise RuntimeError(f"architecture registry mismatch: {count_errors}")

    initialize_result = mcp_request(
        session,
        args.base_url,
        "initialize",
        {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "harness-real-e2e", "version": "1.0.0"},
        },
        request_id="mcp-initialize",
    )
    initialized_result = mcp_request(
        session,
        args.base_url,
        "notifications/initialized",
        request_id="mcp-initialized",
    )
    listed_tools = mcp_request(session, args.base_url, "tools/list", request_id="mcp-tools-list").get("tools") or []
    listed_resources = mcp_request(session, args.base_url, "resources/list", request_id="mcp-resources-list").get("resources") or []
    listed_prompts = mcp_request(session, args.base_url, "prompts/list", request_id="mcp-prompts-list").get("prompts") or []
    if len(listed_tools) != len(CASES) or len(listed_resources) < 5 or len(listed_prompts) < 2:
        raise RuntimeError(
            f"MCP discovery mismatch: tools={len(listed_tools)}, resources={len(listed_resources)}, prompts={len(listed_prompts)}"
        )
    first_resource_uri = str((listed_resources[0] if listed_resources else {}).get("uri") or "")
    first_prompt_name = str((listed_prompts[0] if listed_prompts else {}).get("name") or "")
    resource_read_result = mcp_request(
        session,
        args.base_url,
        "resources/read",
        {"uri": first_resource_uri},
        request_id="mcp-resource-read",
    )
    prompt_get_result = mcp_request(
        session,
        args.base_url,
        "prompts/get",
        {"name": first_prompt_name, "arguments": {"taskType": "smart_tutor", "topic": "STM32 UART"}},
        request_id="mcp-prompt-get",
    )
    mcp_protocol_probe = {
        "initialize": {
            "protocolVersion": initialize_result.get("protocolVersion"),
            "serverInfo": initialize_result.get("serverInfo"),
        },
        "notificationsInitialized": initialized_result,
        "toolsListCount": len(listed_tools),
        "resourcesListCount": len(listed_resources),
        "promptsListCount": len(listed_prompts),
        "resourceReadUri": first_resource_uri,
        "resourceReadContentCount": len(resource_read_result.get("contents") or []),
        "promptGetName": first_prompt_name,
        "promptGetMessageCount": len(prompt_get_result.get("messages") or []),
    }
    if not mcp_protocol_probe["resourceReadContentCount"] or not mcp_protocol_probe["promptGetMessageCount"]:
        raise RuntimeError(f"MCP read/get probe failed: {mcp_protocol_probe}")

    report: dict[str, Any] = {
        "prefix": PREFIX,
        "startedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "baseUrl": args.base_url,
        "username": args.username,
        "model": configured_model,
        "total": len(run_cases),
        "passed": 0,
        "failed": 0,
        "architecture": architecture_summary,
        "mcpProtocolProbe": mcp_protocol_probe,
        "cases": [],
    }

    for index, (tool_name, arguments) in enumerate(run_cases, start=1):
        skill = by_tool[tool_name]
        profiles_payload = request_json(
            session,
            "GET",
            f"{args.base_url.rstrip('/')}/api/learning-profile/profiles",
        )
        expected_profile_id = int(nested(profiles_payload, "data", "activeReportId") or 0)
        if expected_profile_id <= 0:
            raise RuntimeError("测试过程中当前画像被重置，已停止后续 Skill 调用")
        started = time.perf_counter()
        case_record: dict[str, Any] = {
            "index": index,
            "tool": tool_name,
            "skillId": skill.get("id"),
            "taskType": skill.get("taskType"),
            "expectedProfileReportId": expected_profile_id,
            "startedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
            "arguments": scrub(arguments),
            "errors": [],
        }
        try:
            rpc = request_json(
                session,
                "POST",
                f"{args.base_url.rstrip('/')}/api/xiaozhi/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": index,
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": arguments},
                },
            )
            if rpc.get("error"):
                raise RuntimeError(json_text(rpc["error"]))
            task_id = str(nested(rpc, "result", "structuredContent", "task", "taskId") or "")
            if not task_id:
                raise RuntimeError("MCP tools/call did not return taskId")
            case_record["taskId"] = task_id
            deadline = time.monotonic() + args.task_timeout
            task: dict[str, Any] = {}
            while time.monotonic() < deadline:
                detail = request_json(
                    session,
                    "GET",
                    f"{args.base_url.rstrip('/')}/api/xiaozhi/tasks/{task_id}",
                )
                task = nested(detail, "data", "task") or {}
                status = str(task.get("status") or "")
                print(
                    f"[{index:02d}/{len(run_cases)}] {tool_name} {task_id} status={status}",
                    flush=True,
                )
                if status in {"complete", "failed"}:
                    break
                time.sleep(args.poll_seconds)
            if task.get("status") not in {"complete", "failed"}:
                raise TimeoutError(f"task timed out after {args.task_timeout}s")
            errors, summary = validate_common(
                tool_name,
                skill,
                task,
                expected_profile_id,
                configured_model,
            )
            case_record.update(summary)
            case_record["errors"] = errors
            artifact = scrub(task)
            (artifacts_dir / f"{index:02d}-{skill['taskType']}-{task_id}.json").write_text(
                json.dumps(artifact, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
        except Exception as exc:
            case_record["errors"] = [*case_record.get("errors", []), str(exc)]
        case_record["elapsedSeconds"] = round(time.perf_counter() - started, 2)
        case_record["passed"] = not case_record["errors"]
        report["passed" if case_record["passed"] else "failed"] += 1
        report["cases"].append(case_record)
        (output_dir / "真实讯飞全量验收.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    report["finishedAt"] = datetime.now().astimezone().isoformat(timespec="seconds")
    report["success"] = report["failed"] == 0
    (output_dir / "真实讯飞全量验收.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(json.dumps({key: report[key] for key in ("total", "passed", "failed", "success")}, ensure_ascii=False))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
