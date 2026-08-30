"""Unified multi-agent orchestration runtime controlled by XiaoZhi.

The runtime follows a supervisor/blackboard architecture:

1. XiaoZhi plans the execution.
2. Context and knowledge agents enrich a shared blackboard.
3. A specialist worker executes the domain task.
4. Reviewer and safety agents validate the result.
5. Failed structural reviews can be handed back for one revision.
6. A feedback agent records how the result should affect later learning.

Agents exchange structured artifacts through ``handoffs`` rather than holding
unbounded peer-to-peer conversations. This keeps the execution observable and
avoids losing profile, knowledge, or review context between modules.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from typing import Any, Callable, TypedDict

try:
    from langgraph.graph import END, START, StateGraph
except Exception:  # pragma: no cover - optional fallback
    END = START = StateGraph = None

try:
    from course_knowledge import retrieve_course_knowledge
    from agent_manifest import AGENT_CATALOG, TASK_POLICIES, XIAOZHI_MASTER_AGENT_ID
except ImportError:  # pragma: no cover - package-style import fallback
    from .course_knowledge import retrieve_course_knowledge
    from .agent_manifest import AGENT_CATALOG, TASK_POLICIES, XIAOZHI_MASTER_AGENT_ID


XIAOZHI_ARCHITECTURE = "supervisor-shared-blackboard"

RUNTIME_AGENT_DISPLAY_NAMES = {
    "learner-context-agent": "学习上下文智能体",
    "course-knowledge-retrieval-agent": "知识检索智能体",
    "skill-registry-agent": "能力注册智能体",
    "mcp-tool-gateway": "MCP 工具网关",
    "quality-review-agent": "资源审核智能体",
    "content-safety-agent": "内容安全智能体",
    "learning-feedback-agent": "学习反馈智能体",
}


def _agent_name(agent_id: str) -> str:
    return str(
        (AGENT_CATALOG.get(agent_id) or {}).get("name")
        or RUNTIME_AGENT_DISPLAY_NAMES.get(agent_id)
        or agent_id
    )


TASK_TYPE_ALIASES = {
    "profile": "profile_update",
    "learning_profile": "profile_update",
    "profile_management": "profile_management",
    "background": "learning_background",
    "path": "learning_path",
    "stage": "learning_path_stage",
    "resources": "personalized_resources",
    "quiz": "question_bank",
    "question": "question_bank",
    "ppt_h5": "ppt",
    "handout": "document",
    "learning_document": "document",
    "mind_map": "mindmap",
    "video_search": "video",
    "animated_lesson": "animation",
    "learning_animation": "animation",
    "simulator": "mcu",
    "assessment": "effect_assessment",
    "tutor": "smart_tutor",
    "feedback": "learning_feedback",
    "learning_feedback": "learning_feedback",
}


ProgressCallback = Callable[[dict[str, Any]], None]
SpecialistHandler = Callable[[dict[str, Any], ProgressCallback], dict[str, Any]]


class MultiAgentState(TypedDict, total=False):
    run_id: str
    task_id: str
    user_id: int
    task_type: str
    topic: str
    payload: dict[str, Any]
    platform_context: dict[str, Any]
    blackboard: dict[str, Any]
    plan: list[dict[str, Any]]
    knowledge: dict[str, Any]
    output: dict[str, Any]
    review: dict[str, Any]
    feedback: dict[str, Any]
    attempt: int
    max_retries: int
    status: str
    error: str
    events: list[dict[str, Any]]
    handoffs: list[dict[str, Any]]
    specialist_handler: SpecialistHandler
    on_event: ProgressCallback | None
    final_result: dict[str, Any]


def normalize_task_type(task_type: object) -> str:
    raw = str(task_type or "").strip()
    return TASK_TYPE_ALIASES.get(raw, raw)


def _json_safe(value: Any, max_chars: int = 6000) -> Any:
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
        if len(text) > max_chars:
            return {"summary": text[:max_chars], "truncated": True}
        return json.loads(text)
    except Exception:
        return str(value)[:max_chars]


def _conversation_citations(citations: Any) -> list[dict[str, Any]]:
    """Keep citation evidence structured while bounding shared-chat payload size."""
    compact: list[dict[str, Any]] = []
    for item in citations if isinstance(citations, list) else []:
        if not isinstance(item, dict):
            continue
        compact.append(
            {
                key: value
                for key, value in {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "source": item.get("source"),
                    "sourceType": item.get("sourceType"),
                    "route": item.get("route"),
                    "page": item.get("page"),
                    "section": item.get("section"),
                    "excerpt": str(item.get("excerpt") or item.get("snippet") or "")[:320],
                }.items()
                if value not in (None, "")
            }
        )
    return compact[:7]


def _emit(
    state: MultiAgentState,
    agent_id: str,
    stage: str,
    status: str,
    message: str,
    progress: int,
    payload: dict[str, Any] | None = None,
) -> None:
    event = {
        "runId": state.get("run_id"),
        "taskId": state.get("task_id") or "",
        "sequence": len(state.setdefault("events", [])) + 1,
        "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "agentId": agent_id,
        "agentName": _agent_name(agent_id),
        "stage": stage,
        "status": status,
        "message": message,
        "progress": max(0, min(100, int(progress))),
        "payload": _json_safe(payload or {}, 8000),
    }
    state["events"].append(event)
    callback = state.get("on_event")
    if callback:
        try:
            callback(event)
        except Exception:
            pass


def _handoff(
    state: MultiAgentState,
    from_agent: str,
    to_agent: str,
    artifact_type: str,
    summary: str,
    payload: Any = None,
) -> None:
    state.setdefault("handoffs", []).append(
        {
            "runId": state.get("run_id"),
            "sequence": len(state["handoffs"]) + 1,
            "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "fromAgent": from_agent,
            "fromAgentName": _agent_name(from_agent),
            "toAgent": to_agent,
            "toAgentName": _agent_name(to_agent),
            "artifactType": artifact_type,
            "summary": summary,
            "payload": _json_safe(payload or {}, 4000),
        }
    )


def _profile_from_context(state: MultiAgentState) -> dict[str, Any]:
    payload = state.get("payload") or {}
    context = state.get("platform_context") or {}
    profile = {}
    for source in [
        context.get("questionnaire"),
        context.get("profile"),
        payload.get("profile"),
    ]:
        if isinstance(source, dict):
            profile.update(source)
    evidence = {}
    existing_evidence = profile.get("learningEvidence")
    if isinstance(existing_evidence, dict):
        evidence.update(existing_evidence)
    payload_evidence = payload.get("learningEvidence")
    if isinstance(payload_evidence, dict):
        evidence.update(payload_evidence)
    evidence.update(
        {
            "examResults": context.get("examResults") or evidence.get("examResults") or [],
            "mcuExperiments": context.get("mcuExperiments") or evidence.get("mcuExperiments") or [],
            "recentEvents": context.get("recentEvents") or evidence.get("recentEvents") or [],
        }
    )
    profile["learningEvidence"] = evidence
    return profile


def _weak_points(profile: dict[str, Any]) -> list[str]:
    values: list[str] = []
    ai = profile.get("aiAnalysis") if isinstance(profile.get("aiAnalysis"), dict) else {}
    evidence = profile.get("learningEvidence") if isinstance(profile.get("learningEvidence"), dict) else {}
    for source in [profile, ai, evidence]:
        for key in ["weaknesses", "weakPoints", "薄弱知识点", "recommendations"]:
            value = source.get(key) if isinstance(source, dict) else None
            if isinstance(value, list):
                values.extend(str(item).strip() for item in value if str(item).strip())
            elif isinstance(value, str) and value.strip():
                values.append(value.strip())
    for experiment in evidence.get("mcuExperiments") or []:
        if not isinstance(experiment, dict):
            continue
        values.extend(
            str(item).strip()
            for item in (experiment.get("weakPoints") or experiment.get("weak_points") or [])
            if str(item).strip()
        )
    return list(dict.fromkeys(values))[:12]


def _plan_for_task(task_type: str, worker: str, use_knowledge: bool) -> list[dict[str, Any]]:
    steps = [
        {
            "id": "supervisor_plan",
            "agentId": XIAOZHI_MASTER_AGENT_ID,
            "purpose": "识别目标、约束、依赖和验收条件",
        },
        {
            "id": "load_context",
            "agentId": "learner-context-agent",
            "purpose": "汇总学习画像、行为和效果证据",
        },
    ]
    if use_knowledge:
        steps.append(
            {
                "id": "retrieve_knowledge",
                "agentId": "course-knowledge-retrieval-agent",
                "purpose": "检索课程知识库并生成可追溯引用",
            }
        )
    if task_type == "personalized_resources":
        for resource_agent in [
            "learning-document-agent",
            "mindmap-agent",
            "ppt-agent",
            "question-generator-workflow",
            "video-search-agent",
            "mcu-agent",
        ]:
            steps.append(
                {
                    "id": f"resource_worker_{resource_agent}",
                    "agentId": resource_agent,
                    "purpose": "协作生成一种个性化学习资源",
                }
            )
    else:
        steps.append({"id": "specialist_worker", "agentId": worker, "purpose": "执行领域任务并输出结构化产物"})
    steps.extend(
        [
            {
                "id": "quality_review",
                "agentId": "quality-review-agent",
                "purpose": "检查结构、个性化、知识依据和可执行性",
            },
            {
                "id": "content_safety",
                "agentId": "content-safety-agent",
                "purpose": "检查敏感信息和高风险内容",
            },
            {
                "id": "learning_feedback",
                "agentId": "learning-feedback-agent",
                "purpose": "形成下一轮画像、资源和路径调整依据",
            },
            {
                "id": "supervisor_finalize",
                "agentId": XIAOZHI_MASTER_AGENT_ID,
                "purpose": "收口结果并保留完整执行链",
            },
        ]
    )
    return steps


def node_supervisor_plan(state: MultiAgentState) -> MultiAgentState:
    task_type = normalize_task_type(state.get("task_type"))
    if task_type not in TASK_POLICIES:
        raise ValueError(f"岐小智不支持的任务类型: {task_type}")
    state["task_type"] = task_type
    policy = TASK_POLICIES[task_type]
    state["plan"] = _plan_for_task(task_type, policy["worker"], bool(policy.get("knowledge")))
    state["blackboard"] = {
        "task": {
            "type": task_type,
            "topic": state.get("topic") or "",
            "payload": _json_safe(state.get("payload") or {}, 8000),
        },
        "artifacts": {},
        "reviewHistory": [],
        "profileConversation": _json_safe(
            (state.get("platform_context") or {}).get("agentConversation") or {},
            16000,
        ),
    }
    state["status"] = "running"
    _emit(
        state,
        XIAOZHI_MASTER_AGENT_ID,
        "supervisor_plan",
        "complete",
        f"岐小智已规划 {len(state['plan'])} 个协作步骤",
        8,
        {"taskType": task_type, "worker": policy["worker"], "plan": state["plan"]},
    )
    _handoff(
        state,
        XIAOZHI_MASTER_AGENT_ID,
        "learner-context-agent",
        "task_plan",
        "交接任务目标、执行计划和验收标准",
        {"topic": state.get("topic"), "taskType": task_type},
    )
    return state


def node_load_context(state: MultiAgentState) -> MultiAgentState:
    profile = _profile_from_context(state)
    context = state.get("platform_context") or {}
    learner_context = {
        "profile": profile,
        "weakPoints": _weak_points(profile),
        "longTermMemories": (context.get("longTermMemories") or [])[:10],
        "examResults": context.get("examResults") or [],
        "questionSheets": context.get("questionSheets") or [],
        "mcuExperiments": context.get("mcuExperiments") or [],
        "recentEvents": context.get("recentEvents") or [],
        "recentTasks": context.get("recentTasks") or [],
        "sharedAgentConversation": context.get("agentConversation") or {},
    }
    state["blackboard"]["learnerContext"] = learner_context
    state["blackboard"]["artifacts"]["learner_context"] = learner_context
    _emit(
        state,
        "learner-context-agent",
        "load_context",
        "complete",
        "已汇总学习画像、答题、实验和行为证据",
        18,
        {
            "hasProfile": bool(profile),
            "weakPointCount": len(learner_context["weakPoints"]),
            "examCount": len(learner_context["examResults"]),
            "experimentCount": len(learner_context["mcuExperiments"]),
            "memoryCount": len(learner_context["longTermMemories"]),
            "memoryIds": [item.get("id") for item in learner_context["longTermMemories"] if isinstance(item, dict)],
        },
    )
    next_agent = (
        "course-knowledge-retrieval-agent"
        if TASK_POLICIES[state["task_type"]].get("knowledge")
        else TASK_POLICIES[state["task_type"]]["worker"]
    )
    _handoff(
        state,
        "learner-context-agent",
        next_agent,
        "learner_context",
        "交接画像、薄弱点、学习效果和历史行为",
        learner_context,
    )
    return state


def node_retrieve_knowledge(state: MultiAgentState) -> MultiAgentState:
    policy = TASK_POLICIES[state["task_type"]]
    if not policy.get("knowledge"):
        state["knowledge"] = {"grounded": False, "chunks": [], "citations": [], "skipped": True}
        _emit(
            state,
            "course-knowledge-retrieval-agent",
            "knowledge_skipped",
            "complete",
            "当前任务不需要课程知识检索",
            25,
        )
        return state

    learner_context = state["blackboard"].get("learnerContext") or {}
    query_parts = [
        state.get("topic") or "",
        state["task_type"],
        *learner_context.get("weakPoints", [])[:6],
        "中医药 高校课程 四诊 辨证 方药 医案",
    ]
    query = " ".join(str(item) for item in query_parts if str(item).strip())
    try:
        knowledge = retrieve_course_knowledge(query, top_k=7)
    except Exception as exc:
        knowledge = {
            "grounded": False,
            "chunks": [],
            "citations": [],
            "error": str(exc),
            "query": query,
        }
    state["knowledge"] = knowledge
    state["blackboard"]["knowledge"] = knowledge
    state["blackboard"]["artifacts"]["course_knowledge"] = knowledge
    citations = knowledge.get("citations") or []
    routing = knowledge.get("routing") or {}
    verification = routing.get("crossValidation") or {}
    conversation_citations = _conversation_citations(citations)
    _emit(
        state,
        "course-knowledge-retrieval-agent",
        "retrieve_knowledge",
        "complete" if citations else "warning",
        f"混合知识路由完成，命中 {len(citations)} 条可追溯证据；审核结论：{verification.get('status') or '待核验'}",
        30,
        {
            "query": query,
            "citations": conversation_citations,
            "routing": routing,
            "cache": knowledge.get("cache") or {},
        },
    )
    _handoff(
        state,
        "course-knowledge-retrieval-agent",
        policy["worker"],
        "grounded_knowledge",
        f"交接 {len(citations)} 条混合知识证据与交叉验证结论",
        {
            "citations": citations,
            "chunks": (knowledge.get("chunks") or knowledge.get("hits") or [])[:7],
            "routing": routing,
            "cache": knowledge.get("cache") or {},
        },
    )
    return state


def _specialist_payload(state: MultiAgentState) -> dict[str, Any]:
    payload = dict(state.get("payload") or {})
    payload.setdefault("topic", str(state.get("topic") or "").strip())
    learner_context = state["blackboard"].get("learnerContext") or {}
    profile = learner_context.get("profile") or {}
    if profile and (not isinstance(payload.get("profile"), dict) or not payload.get("profile")):
        payload["profile"] = profile
    if isinstance(payload.get("profile"), dict):
        payload["profile"] = {
            **profile,
            **payload["profile"],
            "learningEvidence": profile.get("learningEvidence") or {},
        }
    payload.setdefault("learningEvidence", profile.get("learningEvidence") or {})
    payload["xiaozhiContext"] = learner_context
    payload["longTermMemories"] = learner_context.get("longTermMemories") or []
    payload["knowledgeSources"] = (state.get("knowledge") or {}).get("citations") or []
    knowledge = state.get("knowledge") or {}
    payload["knowledgeContext"] = knowledge.get("chunks") or knowledge.get("hits") or []
    payload["knowledgeRouting"] = knowledge.get("routing") or {}
    payload["knowledgeVerification"] = (knowledge.get("routing") or {}).get("crossValidation") or {}
    payload["orchestrationContext"] = {
        "runId": state.get("run_id"),
        "rootAgent": XIAOZHI_MASTER_AGENT_ID,
        "architecture": XIAOZHI_ARCHITECTURE,
        "attempt": state.get("attempt", 0) + 1,
        "reviewFeedback": (state.get("review") or {}).get("issues") or [],
        "profileConversation": learner_context.get("sharedAgentConversation") or {},
        "memoryIds": [
            item.get("id")
            for item in (learner_context.get("longTermMemories") or [])
            if isinstance(item, dict)
        ],
    }
    return payload


def node_run_specialist(state: MultiAgentState) -> MultiAgentState:
    policy = TASK_POLICIES[state["task_type"]]
    worker = policy["worker"]
    state["attempt"] = int(state.get("attempt") or 0) + 1
    _emit(
        state,
        worker,
        "specialist_start",
        "running",
        f"{_agent_name(worker)}开始执行第 {state['attempt']} 次生成",
        38,
        {"attempt": state["attempt"]},
    )

    def specialist_progress(event: dict[str, Any]) -> None:
        event = event if isinstance(event, dict) else {"message": str(event)}
        progress = event.get("progress")
        try:
            normalized_progress = 40 + round(max(0, min(100, float(progress or 50))) * 0.35)
        except (TypeError, ValueError):
            normalized_progress = 55
        _emit(
            state,
            str(event.get("agentId") or event.get("agent") or worker),
            str(event.get("stage") or "specialist_progress"),
            str(event.get("status") or "running"),
            str(event.get("message") or "专业智能体正在执行"),
            normalized_progress,
            event,
        )

    handler = state.get("specialist_handler")
    if not callable(handler):
        raise RuntimeError("未注册专业子智能体处理器")
    output = handler(_specialist_payload(state), specialist_progress)
    if not isinstance(output, dict):
        output = {"result": output}
    state["output"] = output
    state["blackboard"]["artifacts"]["specialist_output"] = output
    _emit(
        state,
        worker,
        "specialist_complete",
        "complete",
        f"{_agent_name(worker)}已提交结构化产物",
        73,
        {"outputKeys": list(output.keys())[:30], "attempt": state["attempt"]},
    )
    _handoff(
        state,
        worker,
        "quality-review-agent",
        "specialist_output",
        "交接专业智能体产物，等待结构、引用与个性化审核",
        output,
    )
    return state


def _resource_items(output: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = [
        output.get("resources"),
        (output.get("workflow") or {}).get("resources") if isinstance(output.get("workflow"), dict) else None,
        (output.get("llmResources") or {}).get("resources")
        if isinstance(output.get("llmResources"), dict)
        else None,
    ]
    for value in candidates:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _question_items(output: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = [
        (output.get("question_bank") or {}).get("questions")
        if isinstance(output.get("question_bank"), dict)
        else None,
        ((output.get("questionGenerator") or {}).get("question_bank") or {}).get("questions")
        if isinstance(output.get("questionGenerator"), dict)
        else None,
    ]
    for value in candidates:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _page_items(output: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = [
        output.get("pages"),
        (output.get("ppt") or {}).get("pages") if isinstance(output.get("ppt"), dict) else None,
    ]
    for value in candidates:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _profile_dimensions(output: dict[str, Any]) -> int:
    report = output.get("report") if isinstance(output.get("report"), dict) else {}
    candidate = output.get("aiAnalysis") if isinstance(output.get("aiAnalysis"), dict) else None
    if not isinstance(candidate, dict):
        candidate = report.get("aiAnalysis") if isinstance(report.get("aiAnalysis"), dict) else output
    dimensions = candidate.get("dimensionScores") if isinstance(candidate, dict) else None
    if isinstance(dimensions, list):
        return len(dimensions)
    profile = candidate.get("studentProfile") if isinstance(candidate, dict) else None
    if isinstance(profile, dict):
        return len([key for key, value in profile.items() if value not in (None, "", [], {})])
    return 0


def _path_stage_count(output: dict[str, Any]) -> int:
    path = output.get("learningPath") if isinstance(output.get("learningPath"), dict) else output
    phases = path.get("phases") if isinstance(path, dict) else None
    if isinstance(phases, list):
        return len(phases)
    config = path.get("config") if isinstance(path, dict) else None
    stages = config.get("stages") if isinstance(config, dict) else None
    if isinstance(stages, dict):
        return len(stages)
    if isinstance(stages, list):
        return len(stages)
    return 0


def _path_generation_state(output: dict[str, Any]) -> str:
    path = output.get("learningPath") if isinstance(output.get("learningPath"), dict) else output
    config = path.get("config") if isinstance(path, dict) and isinstance(path.get("config"), dict) else {}
    meta = config.get("meta") if isinstance(config.get("meta"), dict) else {}
    return str(meta.get("generationState") or "").strip().lower()


def _contains_sensitive_secret(output: dict[str, Any]) -> bool:
    text = json.dumps(output, ensure_ascii=False, default=str)
    patterns = [
        r"(?i)(api[_-]?key|api[_-]?secret|password|authorization)\s*[:=]\s*[\"']?[A-Za-z0-9:/+_.-]{16,}",
        r"(?i)bearer\s+[A-Za-z0-9._-]{24,}",
    ]
    return any(re.search(pattern, text) for pattern in patterns)


def _specialist_quality_evaluation(output: dict[str, Any]) -> dict[str, Any]:
    """Return the resource specialist's inspectable score instead of a template score."""
    candidates: list[dict[str, Any]] = []

    def collect(value: Any, depth: int = 0) -> None:
        if depth > 3 or not isinstance(value, dict):
            return
        quality = value.get("qualityEvaluation")
        if isinstance(quality, dict) and isinstance(quality.get("score"), (int, float)):
            candidates.append(quality)
        for key in (
            "questionGenerator",
            "ppt",
            "document",
            "animation",
            "tutor",
            "selectedResource",
            "metadata",
        ):
            collect(value.get(key), depth + 1)
        resources = value.get("resources")
        if isinstance(resources, list):
            for item in resources:
                collect(item, depth + 1)

    collect(output)
    if not candidates:
        return {}
    if len(candidates) == 1:
        return dict(candidates[0])
    scores = [max(0, min(100, int(item["score"]))) for item in candidates]
    return {
        "score": round(sum(scores) / len(scores)),
        "passed": all(item.get("passed") is not False for item in candidates),
        "criteria": {"resourceAverage": round(sum(scores) / len(scores))},
        "resourceCount": len(scores),
    }


def review_specialist_output(
    task_type: str,
    output: dict[str, Any],
    knowledge: dict[str, Any],
    min_score: int,
) -> dict[str, Any]:
    score = 55
    issues: list[str] = []
    strengths: list[str] = []
    structural_ok = bool(output)

    if structural_ok:
        score += 10
        strengths.append("专业智能体返回了结构化结果")
    else:
        issues.append("专业智能体没有返回有效结构化结果")

    if task_type == "profile_update":
        count = _profile_dimensions(output)
        if count >= 6:
            score += 18
            strengths.append(f"学习画像包含 {count} 个有效维度")
        else:
            structural_ok = False
            issues.append(f"学习画像有效维度不足 6 个，当前为 {count} 个")
    elif task_type == "profile_management":
        management = output.get("profileManagement") if isinstance(output.get("profileManagement"), dict) else {}
        if management.get("action") in {"list", "activate", "reset"} and output.get("message"):
            score += 18
            strengths.append("画像管理动作已由总控执行并返回结构化状态")
        else:
            structural_ok = False
            issues.append("画像管理缺少有效动作或结构化结果")
    elif task_type == "learning_background":
        dialogue = output.get("dialogue") if isinstance(output.get("dialogue"), dict) else {}
        if output.get("reply") or output.get("question") or dialogue.get("reply") or dialogue.get("question"):
            score += 18
            strengths.append("包含可继续追问的对话回复")
        else:
            structural_ok = False
            issues.append("缺少对话回复或下一轮追问")
    elif task_type == "learning_path":
        path = output.get("learningPath") if isinstance(output.get("learningPath"), dict) else output
        count = _path_stage_count(output)
        generation_state = _path_generation_state(output)
        progressive_partial = generation_state == "partial"
        generation_error = str(path.get("error") or "") if isinstance(path, dict) else ""
        degraded = bool(path.get("degraded")) if isinstance(path, dict) else False
        if generation_error or degraded:
            structural_ok = False
            issues.append("学习路径未由模型完成有效结构化生成，规则降级结果不能冒充成功")
        elif progressive_partial and count >= 1:
            score += 18
            strengths.append(f"渐进式学习路径已生成 {count} 个阶段，后续阶段可继续补全")
        elif count >= 3:
            score += 18
            strengths.append(f"学习路径包含 {count} 个阶段")
        else:
            structural_ok = False
            issues.append("完整学习路径至少需要 3 个阶段；渐进式 partial 路径至少需要 1 个阶段")
    elif task_type == "learning_path_stage":
        detail = output.get("stageDetail") if isinstance(output.get("stageDetail"), dict) else output
        baseline = output.get("learningPath") if isinstance(output.get("learningPath"), dict) else {}
        baseline_error = str(baseline.get("error") or "")
        baseline_source = str(baseline.get("source") or "").strip().lower()
        baseline_status = str(baseline.get("generationStatus") or "").strip().lower()
        baseline_degraded = (
            bool(baseline.get("degraded"))
            or baseline_status == "fallback"
            or baseline_source in {"fallback-rule", "profile-rule-agent"}
        )
        generation_error = str(detail.get("error") or "") if isinstance(detail, dict) else ""
        degraded = bool(detail.get("degraded")) if isinstance(detail, dict) else False
        if baseline_error or baseline_degraded:
            structural_ok = False
            issues.append("阶段细化依赖的学习路径基线为规则降级结果，不能冒充模型生成成功")
        if generation_error or degraded:
            structural_ok = False
            issues.append("阶段细化未由模型完成有效结构化生成，规则降级结果不能冒充成功")
        if not (baseline_error or baseline_degraded or generation_error or degraded) and any(
            detail.get(key) for key in ["weeks", "goals", "resources", "checkpoints", "tasks"]
        ):
            score += 18
            strengths.append("阶段详情包含目标、任务、资源或检查点")
        elif not (baseline_error or baseline_degraded or generation_error or degraded):
            structural_ok = False
            issues.append("阶段详情缺少可执行任务结构")
    elif task_type == "personalized_resources":
        resources = _resource_items(output)
        resource_types = {str(item.get("type") or "") for item in resources}
        quality_passed = sum(
            1
            for item in resources
            if isinstance(item.get("qualityEvaluation"), dict)
            and item["qualityEvaluation"].get("passed")
        )
        if len(resources) >= 5 and quality_passed >= 5:
            score += 18
            strengths.append(f"已生成 {len(resources)} 项个性化资源，其中 {quality_passed} 项通过质量评价")
        else:
            structural_ok = False
            issues.append(f"通过质量评价的个性化资源少于 5 项，当前为 {quality_passed} 项")
        if len(resource_types) >= 4:
            score += 5
            strengths.append("资源类型覆盖较丰富")
    elif task_type == "question_bank":
        questions = _question_items(output)
        quality = output.get("qualityEvaluation") if isinstance(output.get("qualityEvaluation"), dict) else {}
        if not quality and isinstance(output.get("questionGenerator"), dict):
            quality = output["questionGenerator"].get("qualityEvaluation") if isinstance(output["questionGenerator"].get("qualityEvaluation"), dict) else {}
        if questions and quality.get("passed"):
            score += 18
            strengths.append(f"题库包含 {len(questions)} 道结构化题目，质量评分 {int(quality.get('score') or 0)}")
        else:
            structural_ok = False
            issues.append("题库缺少结构化题目或质量评价未通过")
    elif task_type == "ppt":
        pages = _page_items(output)
        quality = output.get("qualityEvaluation") if isinstance(output.get("qualityEvaluation"), dict) else {}
        if not quality and isinstance(output.get("ppt"), dict):
            quality = output["ppt"].get("qualityEvaluation") if isinstance(output["ppt"].get("qualityEvaluation"), dict) else {}
        if pages and quality.get("passed"):
            score += 18
            strengths.append(f"PPT 包含 {len(pages)} 个可展示页面，质量评分 {int(quality.get('score') or 0)}")
        else:
            structural_ok = False
            issues.append("PPT 没有返回可展示页面或质量评价未通过")
    elif task_type == "document":
        document = output.get("document") if isinstance(output.get("document"), dict) else {}
        sections = document.get("sections") if isinstance(document.get("sections"), list) else []
        quality = output.get("qualityEvaluation") if isinstance(output.get("qualityEvaluation"), dict) else {}
        if len(sections) >= 4 and int(quality.get("score") or 0) >= 65:
            score += 18
            strengths.append(f"课程讲义包含 {len(sections)} 个章节，内容质量评分 {int(quality.get('score') or 0)}")
        else:
            structural_ok = False
            issues.append("课程讲义章节不足或内容质量评价未达标")
    elif task_type in {"mindmap", "video", "mcu"}:
        selected = output.get("selectedResource")
        quality = output.get("qualityEvaluation") if isinstance(output.get("qualityEvaluation"), dict) else {}
        if not quality and isinstance(selected, dict):
            quality = selected.get("qualityEvaluation") if isinstance(selected.get("qualityEvaluation"), dict) else {}
        if (
            isinstance(selected, dict)
            and (selected.get("content") or selected.get("metadata"))
            and quality.get("passed")
        ):
            score += 18
            strengths.append(f"已返回目标资源并通过质量评价，评分 {int(quality.get('score') or 0)}")
        else:
            structural_ok = False
            issues.append("未找到目标资源产物或质量评价未通过")
    elif task_type == "animation":
        animation = output.get("animation") if isinstance(output.get("animation"), dict) else {}
        scenes = animation.get("scenes") if isinstance(animation.get("scenes"), list) else []
        quality = output.get("qualityEvaluation") if isinstance(output.get("qualityEvaluation"), dict) else {}
        visual_types = {str(item.get("visualType") or "") for item in scenes if isinstance(item, dict)}
        if len(scenes) >= 4 and len(visual_types) >= 3 and quality.get("passed"):
            score += 23
            strengths.append(f"H5 动画包含 {len(scenes)} 个场景、{len(visual_types)} 种视觉表达并通过质量评价")
        else:
            structural_ok = False
            issues.append("H5 动画场景、视觉表达或质量评价未达标")
    elif task_type == "interview":
        interview = output.get("interview") if isinstance(output.get("interview"), dict) else output
        if any(interview.get(key) for key in ["sessionId", "session_id", "question", "reply"]):
            score += 18
            strengths.append("已创建可继续交互的面试会话")
        else:
            structural_ok = False
            issues.append("面试会话缺少会话标识或首轮问题")
    elif task_type == "smart_tutor":
        tutor = output.get("tutor") if isinstance(output.get("tutor"), dict) else output
        quality = tutor.get("qualityEvaluation") if isinstance(tutor.get("qualityEvaluation"), dict) else {}
        has_guidance = (
            len(tutor.get("socraticQuestions") or []) >= 3
            and len(tutor.get("hintLadder") or []) == 3
            and bool((tutor.get("feynmanTask") or {}).get("prompt"))
        )
        has_practice = bool(tutor.get("practiceTasks"))
        multimodal = tutor.get("multimodal") if isinstance(tutor.get("multimodal"), dict) else {}
        has_multimodal = bool(multimodal.get("mermaid") and multimodal.get("learningCard"))
        if tutor.get("answer") and has_guidance and has_practice and has_multimodal and quality.get("passed"):
            score += 23
            strengths.append("智能辅导包含苏格拉底追问、费曼复述、三级提示、练习和多模态学习卡")
        else:
            structural_ok = False
            issues.append("智能辅导缺少完整引导链、巩固练习、多模态学习卡或质量评价未通过")
    elif task_type == "effect_assessment":
        if any(output.get(key) for key in ["scores", "summary", "recommendations", "adjustments"]):
            score += 18
            strengths.append("效果评估包含指标或调整建议")
        else:
            structural_ok = False
            issues.append("效果评估缺少指标和动态调整建议")
    elif task_type == "learning_feedback":
        feedback = output.get("feedback") if isinstance(output.get("feedback"), dict) else {}
        if (
            feedback.get("id")
            and feedback.get("outcome") in {"completed", "needs_review", "blocked"}
            and feedback.get("profileReportId")
        ):
            score += 18
            strengths.append("学习反馈已持久化并关联当前画像")
        else:
            structural_ok = False
            issues.append("学习反馈缺少持久化记录、结果状态或画像关联")
    elif task_type == "knowledge_base":
        knowledge_base = output.get("knowledgeBase") if isinstance(output.get("knowledgeBase"), dict) else output
        has_catalog = isinstance(knowledge_base.get("collections"), list)
        has_retrieval = isinstance(knowledge_base.get("hits"), list)
        if has_catalog or has_retrieval:
            score += 18
            strengths.append("私有知识库返回了可验证的目录或检索结果")
        else:
            structural_ok = False
            issues.append("私有知识库缺少目录或检索结果")

    citations = knowledge.get("citations") or []
    if TASK_POLICIES[task_type].get("knowledge"):
        if citations:
            score += 8
            strengths.append(f"知识库提供 {len(citations)} 条可追溯引用")
        else:
            issues.append("课程知识库没有命中直接引用，具体事实需要人工核验")

    specialist_quality = _specialist_quality_evaluation(output)
    score_source = "orchestration-rubric"
    if specialist_quality:
        score_source = "resource-quality-evaluation"
        strengths.append(
            f"采用资源专家的可检查质量评分 {max(0, min(100, int(specialist_quality.get('score') or 0)))}"
        )
        if specialist_quality.get("passed") is False:
            structural_ok = False
            issues.append("资源专家质量评价未通过")

    sensitive = _contains_sensitive_secret(output)
    if sensitive:
        score -= 35
        structural_ok = False
        issues.append("结果疑似包含密钥、口令或授权信息")
    else:
        score += 4
        strengths.append("未检测到明显敏感凭据泄露")

    if specialist_quality:
        score = max(0, min(100, int(specialist_quality.get("score") or 0)))
        if TASK_POLICIES[task_type].get("knowledge") and not citations:
            score = min(score, max(0, int(min_score) - 1))
        if sensitive:
            score -= 35

    score = max(0, min(100, score))
    retry_recommended = not structural_ok
    return {
        "agent": "quality-review-agent",
        "safetyAgent": "content-safety-agent",
        "score": score,
        "scoreSource": score_source,
        "qualityEvaluation": specialist_quality,
        "threshold": min_score,
        "passed": bool(structural_ok and score >= min_score),
        "structuralOk": structural_ok,
        "retryRecommended": retry_recommended,
        "issues": issues,
        "strengths": strengths,
        "grounded": bool(citations),
        "citationCount": len(citations),
        "sensitiveContentDetected": sensitive,
    }


def node_review_output(state: MultiAgentState) -> MultiAgentState:
    policy = TASK_POLICIES[state["task_type"]]
    review = review_specialist_output(
        state["task_type"],
        state.get("output") or {},
        state.get("knowledge") or {},
        int(policy.get("min_score") or 70),
    )
    state["review"] = review
    state["blackboard"].setdefault("reviewHistory", []).append(review)
    state["blackboard"]["artifacts"]["quality_review"] = review
    _emit(
        state,
        "quality-review-agent",
        "quality_review",
        "complete" if review["passed"] else "warning",
        f"质量审核完成：{review['score']} 分，{'通过' if review['passed'] else '需要修订'}",
        82,
        review,
    )
    _emit(
        state,
        "content-safety-agent",
        "content_safety",
        "complete" if not review["sensitiveContentDetected"] else "failed",
        "内容安全检查完成"
        if not review["sensitiveContentDetected"]
        else "检测到疑似敏感凭据，结果不予通过",
        85,
        {"sensitiveContentDetected": review["sensitiveContentDetected"]},
    )
    if (
        review.get("retryRecommended")
        and state.get("attempt", 0) <= state.get("max_retries", 1)
    ):
        _handoff(
            state,
            "quality-review-agent",
            policy["worker"],
            "revision_request",
            "审核未通过，携带问题清单退回专业智能体修订",
            {"issues": review["issues"], "score": review["score"]},
        )
    else:
        _handoff(
            state,
            "quality-review-agent",
            "learning-feedback-agent",
            "review_result",
            "交接质量、安全和知识依据审核结论",
            review,
        )
    return state


def route_after_review(state: MultiAgentState) -> str:
    review = state.get("review") or {}
    if (
        not review.get("passed")
        and review.get("retryRecommended")
        and state.get("attempt", 0) <= state.get("max_retries", 1)
    ):
        return "revise"
    return "feedback"


def node_learning_feedback(state: MultiAgentState) -> MultiAgentState:
    learner_context = state["blackboard"].get("learnerContext") or {}
    review = state.get("review") or {}
    weak_points = learner_context.get("weakPoints") or []
    feedback = {
        "agent": "learning-feedback-agent",
        "taskType": state["task_type"],
        "reviewScore": review.get("score", 0),
        "weakPoints": weak_points[:8],
        "nextActions": [],
        "shouldRefreshProfile": state["task_type"]
        in {"question_bank", "mcu", "interview", "effect_assessment", "learning_feedback"},
        "shouldAdaptLearningPath": state["task_type"]
        in {"profile_update", "question_bank", "mcu", "interview", "effect_assessment", "learning_feedback"},
    }
    if review.get("passed"):
        feedback["nextActions"].append("记录本次产物和资源使用行为，供后续效果评估使用")
    else:
        feedback["nextActions"].append("保留审核问题并在下一次生成时作为硬约束")
    if weak_points:
        feedback["nextActions"].append(f"继续围绕薄弱点“{weak_points[0]}”安排练习和实验")
    if feedback["shouldAdaptLearningPath"]:
        feedback["nextActions"].append("学习效果证据变化后重新计算学习路径优先级")
    state["feedback"] = feedback
    state["blackboard"]["artifacts"]["learning_feedback"] = feedback
    _emit(
        state,
        "learning-feedback-agent",
        "learning_feedback",
        "complete",
        "已形成画像更新和学习路径动态调整建议",
        92,
        feedback,
    )
    _handoff(
        state,
        "learning-feedback-agent",
        XIAOZHI_MASTER_AGENT_ID,
        "feedback_summary",
        "交接审核结果、薄弱点和下一轮学习调整建议",
        feedback,
    )
    return state


def _agent_runs(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    runs: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for event in events:
        agent_id = str(event.get("agentId") or "")
        if not agent_id:
            continue
        if agent_id not in runs:
            order.append(agent_id)
            runs[agent_id] = {
                "id": agent_id,
                "name": event.get("agentName") or agent_id,
                "role": AGENT_CATALOG.get(agent_id, {}).get("role") or "specialist",
                "status": "running",
                "detail": "",
                "progress": 0,
                "eventCount": 0,
            }
        run = runs[agent_id]
        run["eventCount"] += 1
        run["detail"] = event.get("message") or run["detail"]
        run["progress"] = max(run["progress"], int(event.get("progress") or 0))
        event_status = event.get("status")
        if event_status in {"failed", "error"}:
            run["status"] = "failed"
        elif event_status in {"complete", "done", "warning"} and run["status"] != "failed":
            run["status"] = "complete" if event_status != "warning" else "warning"
        elif run["status"] not in {"failed", "complete", "warning"}:
            run["status"] = "running"
    return [runs[agent_id] for agent_id in order]


def node_finalize(state: MultiAgentState) -> MultiAgentState:
    output = dict(state.get("output") or {})
    review = state.get("review") or {}
    status = (
        "complete"
        if output
        and review.get("passed") is True
        and not review.get("sensitiveContentDetected")
        else "failed"
    )
    state["status"] = status
    trace = {
        "runId": state.get("run_id"),
        "taskId": state.get("task_id") or "",
        "rootAgent": XIAOZHI_MASTER_AGENT_ID,
        "rootAgentName": _agent_name(XIAOZHI_MASTER_AGENT_ID),
        "architecture": XIAOZHI_ARCHITECTURE,
        "coordinationMode": "profile-scoped-shared-conversation",
        "taskType": state["task_type"],
        "topic": state.get("topic") or "",
        "status": status,
        "attempts": state.get("attempt", 0),
        "plan": state.get("plan") or [],
        "agentRuns": _agent_runs(state.get("events") or []),
        "handoffs": state.get("handoffs") or [],
        "review": review,
        "feedback": state.get("feedback") or {},
        "knowledgeSources": (state.get("knowledge") or {}).get("citations") or [],
        "events": (state.get("events") or [])[-100:],
    }
    output["orchestrator"] = XIAOZHI_MASTER_AGENT_ID
    output["orchestration"] = trace
    output.setdefault("agentRuns", trace["agentRuns"])
    output.setdefault("handoffs", trace["handoffs"])
    output.setdefault("review", review)
    state["final_result"] = output
    _emit(
        state,
        XIAOZHI_MASTER_AGENT_ID,
        "supervisor_finalize",
        status,
        (
            "岐小智已完成结果收口并保存协作执行链"
            if status == "complete"
            else "岐小智已保存失败结果与审核问题，未将产物标记为完成"
        ),
        100,
        {"reviewScore": review.get("score"), "attempts": state.get("attempt", 0)},
    )
    # Include the final event in the persisted trace.
    output["orchestration"]["events"] = (state.get("events") or [])[-100:]
    output["orchestration"]["agentRuns"] = _agent_runs(state.get("events") or [])
    output["agentRuns"] = output["orchestration"]["agentRuns"]
    return state


def build_multi_agent_graph():
    if StateGraph is None:
        return None
    graph = StateGraph(MultiAgentState)
    graph.add_node("supervisor_plan", node_supervisor_plan)
    graph.add_node("load_context", node_load_context)
    graph.add_node("retrieve_knowledge", node_retrieve_knowledge)
    graph.add_node("specialist_worker", node_run_specialist)
    graph.add_node("quality_review", node_review_output)
    graph.add_node("learning_feedback", node_learning_feedback)
    graph.add_node("supervisor_finalize", node_finalize)
    graph.add_edge(START, "supervisor_plan")
    graph.add_edge("supervisor_plan", "load_context")
    graph.add_edge("load_context", "retrieve_knowledge")
    graph.add_edge("retrieve_knowledge", "specialist_worker")
    graph.add_edge("specialist_worker", "quality_review")
    graph.add_conditional_edges(
        "quality_review",
        route_after_review,
        {"revise": "specialist_worker", "feedback": "learning_feedback"},
    )
    graph.add_edge("learning_feedback", "supervisor_finalize")
    graph.add_edge("supervisor_finalize", END)
    return graph.compile()


def _run_without_langgraph(state: MultiAgentState) -> MultiAgentState:
    state = node_supervisor_plan(state)
    state = node_load_context(state)
    state = node_retrieve_knowledge(state)
    while True:
        state = node_run_specialist(state)
        state = node_review_output(state)
        if route_after_review(state) != "revise":
            break
    state = node_learning_feedback(state)
    return node_finalize(state)


def run_multi_agent_workflow(
    task_type: str,
    topic: str,
    payload: dict[str, Any],
    platform_context: dict[str, Any],
    specialist_handler: SpecialistHandler,
    *,
    user_id: int = 0,
    task_id: str = "",
    on_event: ProgressCallback | None = None,
    max_retries: int = 1,
) -> dict[str, Any]:
    state: MultiAgentState = {
        "run_id": f"mar_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}",
        "task_id": str(task_id or ""),
        "user_id": int(user_id or 0),
        "task_type": normalize_task_type(task_type),
        "topic": str(topic or "").strip(),
        "payload": payload if isinstance(payload, dict) else {},
        "platform_context": platform_context if isinstance(platform_context, dict) else {},
        "blackboard": {},
        "plan": [],
        "knowledge": {},
        "output": {},
        "review": {},
        "feedback": {},
        "attempt": 0,
        "max_retries": max(0, min(2, int(max_retries))),
        "status": "queued",
        "error": "",
        "events": [],
        "handoffs": [],
        "specialist_handler": specialist_handler,
        "on_event": on_event,
    }
    app = build_multi_agent_graph()
    try:
        final_state = app.invoke(state) if app is not None else _run_without_langgraph(state)
        return final_state.get("final_result") or final_state.get("output") or {}
    except Exception as exc:
        state["status"] = "failed"
        state["error"] = str(exc)
        _emit(
            state,
            XIAOZHI_MASTER_AGENT_ID,
            "orchestration_error",
            "failed",
            str(exc) or "多智能体协作执行失败",
            100,
        )
        raise


def multi_agent_runtime_status() -> dict[str, Any]:
    return {
        "rootAgent": XIAOZHI_MASTER_AGENT_ID,
        "architecture": XIAOZHI_ARCHITECTURE,
        "framework": "LangGraph" if StateGraph is not None else "sequential-fallback",
        "coordinationMode": "profile-scoped-shared-conversation",
        "agents": [
            {"id": agent_id, **metadata}
            for agent_id, metadata in AGENT_CATALOG.items()
        ],
        "taskPolicies": TASK_POLICIES,
        "features": [
            "shared_blackboard",
            "profile_scoped_shared_conversation",
            "automatic_context_compaction",
            "structured_handoffs",
            "course_rag",
            "user_private_knowledge",
            "quality_review",
            "content_safety",
            "conditional_retry",
            "learning_feedback_loop",
            "observable_execution_trace",
            "modality_aware_model_routing",
            "kimi_vision_to_spark_handoff",
            "document_text_to_spark_handoff",
        ],
    }
