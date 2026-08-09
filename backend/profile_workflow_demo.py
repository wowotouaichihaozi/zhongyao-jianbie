"""Small LangGraph demo for learning-profile dialogue workflow.

Run:
    python profile_workflow_demo.py
    python profile_workflow_demo.py --user "学习目标是为了参加智能车竞赛"

This file is intentionally verbose: it prints every intermediate state so the
workflow can be judged before wiring it into the production backend.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, START, StateGraph

from api_config import setting_default
from common import get_setting
from learning_agents import extract_json, request_llm_text


DIMENSIONS = [
    "专业/课程背景",
    "学习目标",
    "当前知识基础",
    "学习进度",
    "薄弱知识点",
    "易错点类型",
    "学习风格/认知偏好",
    "资源形式偏好",
    "可投入时间",
    "难度接受程度",
]

LIST_DIMENSIONS = {
    "学习目标",
    "薄弱知识点",
    "易错点类型",
    "学习风格/认知偏好",
    "资源形式偏好",
}

DB_PATH = Path(__file__).resolve().parent / "data" / "profile_workflow_demo.sqlite"


class WorkflowState(TypedDict, total=False):
    user_id: str
    messages: List[Dict[str, str]]
    profile: Dict[str, Any]
    latest_user_input: str
    rule_result: Dict[str, Any]
    llm1_raw: str
    llm1_json: Dict[str, Any]
    classifier_result: Dict[str, Any]
    db_saved: Dict[str, Any]
    next_dimension: str
    llm2_raw: str
    final_reply: str
    logs: List[Dict[str, Any]]
    verbose: bool


def log(state: WorkflowState, stage: str, payload: Any) -> None:
    state.setdefault("logs", []).append({"stage": stage, "payload": payload})
    if not state.get("verbose", False):
        return
    print("\n" + "=" * 18 + f" {stage} " + "=" * 18)
    if isinstance(payload, str):
        print(payload)
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


def normalize_value(dimension: str, value: Any) -> Any:
    if dimension in LIST_DIMENSIONS:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []
    if isinstance(value, list):
        return "，".join(str(item).strip() for item in value if str(item).strip())
    return str(value or "").strip()


def merge_profile_value(dimension: str, old: Any, new: Any) -> Any:
    old_value = normalize_value(dimension, old)
    new_value = normalize_value(dimension, new)
    if dimension in LIST_DIMENSIONS:
        return list(dict.fromkeys([*old_value, *new_value]))
    return old_value or new_value


def append_profile_value(profile: Dict[str, Any], dimension: str, value: Any) -> None:
    if not value:
        return
    profile[dimension] = merge_profile_value(dimension, profile.get(dimension), value)


def is_filled(value: Any) -> bool:
    if isinstance(value, list):
        return bool(value)
    return bool(str(value or "").strip())


def user_text(messages: List[Dict[str, str]]) -> str:
    return "，".join(
        str(item.get("content") or "").strip()
        for item in messages
        if item.get("role") == "user" and str(item.get("content") or "").strip()
    )


def rule_extract(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    text = user_text(messages)
    profile: Dict[str, Any] = {}
    evidence: List[Dict[str, Any]] = []

    grade_match = re.search(r"大[一二三四]|研[一二三]|本科|研究生", text)
    major_match = re.search(r"([\u4e00-\u9fa5A-Za-z0-9]+专业)", text)
    course_hits: List[str] = []
    if re.search(r"嵌入式|embedded", text, re.I):
        course_hits.append("嵌入式")
    if re.search(r"stm32", text, re.I):
        course_hits.append("STM32")
    if "单片机" in text:
        course_hits.append("单片机")
    if re.search(r"linux\s*驱动|Linux驱动", text, re.I):
        course_hits.append("Linux 驱动")
    if grade_match or major_match or course_hits:
        value = "，".join([item for item in [grade_match.group(0) if grade_match else "", major_match.group(1) if major_match else "", *course_hits] if item]).strip("，")
        profile["专业/课程背景"] = value
        evidence.append({"dimension": "专业/课程背景", "text": value, "confidence": 0.86, "source": "rule"})

    goal_match = re.search(r"(?:学习目标是|目标是|为了|想要|准备|希望|打算)([^。！？!?，,]{2,48})", text)
    goals: List[str] = []
    if "智能车" in text:
        goals.append("参加智能车竞赛")
    if re.search(r"竞赛|比赛|参赛", text) and not goals:
        goals.append("参加嵌入式相关竞赛")
    if "课程设计" in text:
        goals.append("完成课程设计")
    if "就业" in text:
        goals.append("提升就业项目能力")
    if goal_match:
        goal_text = goal_match.group(1).strip()
        if goal_text.startswith("为了"):
            goal_text = goal_text[2:].strip()
        goals.append(goal_text)
    if goals:
        goals = list(dict.fromkeys(goals))
        profile["学习目标"] = goals
        evidence.append({"dimension": "学习目标", "text": "；".join(goals), "confidence": 0.94, "source": "rule"})

    if re.search(r"刚学|最近在学|正在学|学习.*stm32|stm32", text, re.I):
        profile["当前知识基础"] = "已开始学习 STM32 和嵌入式基础内容"
        profile["学习进度"] = "处于 STM32 基础外设与实践训练阶段"
        evidence.append({"dimension": "当前知识基础", "text": profile["当前知识基础"], "confidence": 0.78, "source": "rule"})
        evidence.append({"dimension": "学习进度", "text": profile["学习进度"], "confidence": 0.78, "source": "rule"})

    weak_points: List[str] = []
    for label, pattern in [
        ("GPIO", r"gpio"),
        ("串口通信", r"串口|uart|usart"),
        ("定时器/PWM", r"定时器|pwm"),
        ("中断调试", r"中断"),
        ("编码器采集", r"编码器"),
        ("开发板调试", r"开发板|调试"),
    ]:
        if re.search(pattern, text, re.I):
            weak_points.append(label)
    if weak_points:
        profile["薄弱知识点"] = list(dict.fromkeys(weak_points))
        evidence.append({"dimension": "薄弱知识点", "text": "；".join(profile["薄弱知识点"]), "confidence": 0.82, "source": "rule"})

    time_match = re.search(
        r"(?:每周|一周|每星期|每星期|每天|每日|周末)[^。！？!?，,]{0,16}(?:\d+|一|二|两|三|四|五|六|七|八|九|十)[^。！？!?，,]{0,8}(?:小时|h|天)",
        text,
        re.I,
    )
    if time_match:
        profile["可投入时间"] = time_match.group(0)
        evidence.append({"dimension": "可投入时间", "text": profile["可投入时间"], "confidence": 0.9, "source": "rule"})

    missing = [dimension for dimension in DIMENSIONS if not is_filled(profile.get(dimension))]
    mentioned = [dimension for dimension in DIMENSIONS if is_filled(profile.get(dimension))]
    return {
        "mentioned_dimensions": mentioned,
        "missing_dimensions": missing,
        "candidate_evidence": evidence,
        "profile_patch": profile,
        "next_dimension": missing[0] if missing else "",
        "user_intent": "补充画像信息" if mentioned else "普通对话/未识别画像信息",
    }


def validate_classifier_json(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    mentioned = [item for item in data.get("mentioned_dimensions", []) if item in DIMENSIONS]
    missing = [item for item in data.get("missing_dimensions", []) if item in DIMENSIONS]
    evidence = []
    for item in data.get("candidate_evidence", []):
        if not isinstance(item, dict):
            continue
        dimension = item.get("dimension")
        text = str(item.get("text") or "").strip()
        if dimension in DIMENSIONS and text:
            try:
                confidence = float(item.get("confidence", 0.65))
            except (TypeError, ValueError):
                confidence = 0.65
            evidence.append({
                "dimension": dimension,
                "text": text,
                "confidence": max(0.0, min(1.0, confidence)),
                "source": "llm1",
            })
    next_dimension = data.get("next_dimension")
    if next_dimension not in DIMENSIONS:
        next_dimension = missing[0] if missing else ""
    return {
        "mentioned_dimensions": mentioned,
        "missing_dimensions": missing,
        "candidate_evidence": evidence,
        "next_dimension": next_dimension,
        "user_intent": str(data.get("user_intent") or "").strip() or "未知",
    }


def evidence_to_profile_patch(evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    profile: Dict[str, Any] = {}
    for item in evidence:
        dimension = item.get("dimension")
        text = str(item.get("text") or "").strip()
        source = item.get("source")
        if dimension not in DIMENSIONS or not text:
            continue
        # Rule extraction already has a cleaner profile_patch. Use LLM evidence
        # to patch values; keep rule evidence as provenance only to avoid duplicates.
        if source == "rule":
            continue
        append_profile_value(profile, dimension, text)
    return profile


def merge_classifier(rule_result: Dict[str, Any], llm_result: Dict[str, Any]) -> Dict[str, Any]:
    evidence = [*rule_result.get("candidate_evidence", []), *llm_result.get("candidate_evidence", [])]
    mentioned = list(dict.fromkeys([*rule_result.get("mentioned_dimensions", []), *llm_result.get("mentioned_dimensions", [])]))
    missing = [dimension for dimension in DIMENSIONS if dimension not in mentioned]
    next_dimension = llm_result.get("next_dimension") or rule_result.get("next_dimension") or (missing[0] if missing else "")
    return {
        "mentioned_dimensions": mentioned,
        "missing_dimensions": missing,
        "candidate_evidence": evidence,
        "next_dimension": next_dimension,
        "user_intent": llm_result.get("user_intent") or rule_result.get("user_intent"),
    }


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS demo_dialogue_turn (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id TEXT NOT NULL,
              role TEXT NOT NULL,
              content TEXT NOT NULL,
              created_at INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS demo_profile_evidence (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id TEXT NOT NULL,
              dimension_key TEXT NOT NULL,
              evidence_text TEXT NOT NULL,
              source TEXT NOT NULL,
              confidence REAL NOT NULL,
              created_at INTEGER NOT NULL
            )
            """
        )


def save_demo_records(user_id: str, messages: List[Dict[str, str]], evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    init_db()
    now = int(time.time())
    with sqlite3.connect(DB_PATH) as conn:
        for message in messages:
            conn.execute(
                "INSERT INTO demo_dialogue_turn (user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (user_id, message.get("role", ""), message.get("content", ""), now),
            )
        for item in evidence:
            conn.execute(
                """
                INSERT INTO demo_profile_evidence
                  (user_id, dimension_key, evidence_text, source, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    item.get("dimension", ""),
                    item.get("text", ""),
                    item.get("source", "unknown"),
                    float(item.get("confidence", 0.5)),
                    now,
                ),
            )
        dialogue_count = conn.execute("SELECT COUNT(*) FROM demo_dialogue_turn WHERE user_id = ?", (user_id,)).fetchone()[0]
        evidence_count = conn.execute("SELECT COUNT(*) FROM demo_profile_evidence WHERE user_id = ?", (user_id,)).fetchone()[0]
    return {"db_path": str(DB_PATH), "dialogue_rows_for_user": dialogue_count, "evidence_rows_for_user": evidence_count}


def node_load_context(state: WorkflowState) -> WorkflowState:
    log(state, "01_load_context", {
        "user_id": state["user_id"],
        "messages": state["messages"],
        "current_profile": state.get("profile", {}),
        "configured_model_id": get_setting("ANTHROPIC_MODEL", setting_default("ANTHROPIC_MODEL")),
        "note": "文本智能体默认使用 Spark X2 Agent（modelId: xsparkx2agent）。",
    })
    state["latest_user_input"] = next(
        (item["content"] for item in reversed(state["messages"]) if item.get("role") == "user"),
        "",
    )
    return state


def node_rule_extract(state: WorkflowState) -> WorkflowState:
    result = rule_extract(state["messages"])
    state["rule_result"] = result
    log(state, "02_rule_extract", result)
    return state


def node_llm1_classify(state: WorkflowState) -> WorkflowState:
    system = (
        "你是学习画像维度判定器。尽量只返回 JSON。"
        "如果无法严格 JSON，也不要编造事实。"
    )
    prompt = f"""
请基于对话和当前画像状态，判断用户输入补充了哪些画像维度，并选择下一个最该追问的维度。
画像维度：{json.dumps(DIMENSIONS, ensure_ascii=False)}

输出字段：
{{
  "mentioned_dimensions": ["维度名"],
  "missing_dimensions": ["维度名"],
  "candidate_evidence": [
    {{"dimension": "维度名", "text": "原文证据或归纳证据", "confidence": 0.0}}
  ],
  "next_dimension": "维度名",
  "user_intent": "补充画像信息|提问求助|闲聊"
}}

当前画像：
{json.dumps(state.get("profile", {}), ensure_ascii=False)}

对话：
{json.dumps(state["messages"], ensure_ascii=False)}
"""
    try:
        raw = request_llm_text(system, prompt, max_tokens=700, timeout=60, json_mode=False)
    except Exception as exc:
        raw = f"__LLM1_ERROR__ {type(exc).__name__}: {exc}"
    state["llm1_raw"] = raw
    log(state, "03_llm1_x2_flash_raw", raw)
    return state


def node_normalize_classifier(state: WorkflowState) -> WorkflowState:
    raw = state.get("llm1_raw", "")
    parsed: Dict[str, Any] = {}
    parse_error = ""
    if raw and not raw.startswith("__LLM1_ERROR__"):
        try:
            parsed = extract_json(raw)
        except Exception as exc:
            parse_error = f"{type(exc).__name__}: {exc}"
    llm_valid = validate_classifier_json(parsed)
    merged = merge_classifier(state["rule_result"], llm_valid)
    state["llm1_json"] = llm_valid
    state["classifier_result"] = merged

    profile = dict(state.get("profile", {}))
    for dimension, value in state["rule_result"].get("profile_patch", {}).items():
        append_profile_value(profile, dimension, value)
    for dimension, value in evidence_to_profile_patch(merged.get("candidate_evidence", [])).items():
        append_profile_value(profile, dimension, value)
    state["profile"] = profile

    log(state, "04_normalize_and_merge", {
        "json_parse_error": parse_error,
        "llm_validated": llm_valid,
        "merged_classifier_result": merged,
        "updated_profile": profile,
    })
    return state


def node_persist_evidence(state: WorkflowState) -> WorkflowState:
    result = save_demo_records(
        state["user_id"],
        state["messages"],
        state["classifier_result"].get("candidate_evidence", []),
    )
    state["db_saved"] = result
    log(state, "05_persist_demo_db", result)
    return state


def node_choose_next_dimension(state: WorkflowState) -> WorkflowState:
    profile = state.get("profile", {})
    missing = [dimension for dimension in DIMENSIONS if not is_filled(profile.get(dimension))]
    preferred = state["classifier_result"].get("next_dimension")
    if preferred not in missing:
        preferred = missing[0] if missing else ""
    state["next_dimension"] = preferred
    log(state, "06_choose_next_dimension", {
        "missing_after_merge": missing,
        "next_dimension": preferred,
    })
    return state


def node_llm2_respond(state: WorkflowState) -> WorkflowState:
    next_dimension = state.get("next_dimension") or "画像总结"
    system = "你是嵌智学航的数字人 AI 讲师。用中文自然回复，最多两句话。"
    prompt = f"""
你需要根据当前学习画像和下一个目标维度，生成自然追问或回答。

当前画像：
{json.dumps(state.get("profile", {}), ensure_ascii=False)}

本轮判定：
{json.dumps(state.get("classifier_result", {}), ensure_ascii=False)}

下一个目标维度：{next_dimension}

要求：
1. 如果用户是在补充画像，先简短确认已经记录的信息。
2. 只追问一个问题。
3. 问题必须服务于目标维度。
"""
    try:
        raw = request_llm_text(system, prompt, max_tokens=260, timeout=60, json_mode=False)
    except Exception as exc:
        raw = f"我已经记录了你的关键信息。接下来想补齐「{next_dimension}」，你可以简单说一下这一块的情况吗？（LLM2 调用失败：{type(exc).__name__}）"
    raw = str(raw or "").strip()
    if len(raw) < 12 or not re.search(r"[？?。！!]", raw):
        raw = deterministic_question(state, raw)
    state["llm2_raw"] = raw
    state["final_reply"] = str(raw).strip()
    log(state, "07_llm2_x2_response_raw", raw)
    return state


def deterministic_question(state: WorkflowState, bad_reply: str = "") -> str:
    next_dimension = state.get("next_dimension") or ""
    profile = state.get("profile", {})
    goal = normalize_value("学习目标", profile.get("学习目标"))
    weak = normalize_value("薄弱知识点", profile.get("薄弱知识点"))
    prefix = "我已经记录了"
    if goal:
        prefix += f"你的目标是{goal[0] if isinstance(goal, list) else goal}"
    if weak:
        weak_text = "、".join(weak[:2]) if isinstance(weak, list) else weak
        prefix += f"，目前薄弱点集中在{weak_text}"
    prefix += "。"
    question_map = {
        "易错点类型": "你在这些内容上更容易错在外设配置流程、代码逻辑，还是硬件接线和调试排查？",
        "学习风格/认知偏好": "你更喜欢先看原理再做实验，还是直接跟着项目步骤边做边学？",
        "资源形式偏好": "后续资源你更希望是视频讲解、图文步骤、代码案例，还是项目任务清单？",
        "可投入时间": "你每周大概能稳定投入多少时间做嵌入式实操练习？",
        "难度接受程度": "接下来的训练你希望从基础外设慢慢过渡，还是直接围绕智能车竞赛做进阶任务？",
    }
    question = question_map.get(next_dimension, "你可以再补充一个当前最想提升的嵌入式能力点吗？")
    if bad_reply:
        return f"{prefix}{question}（已替换过短回复：{bad_reply}）"
    return f"{prefix}{question}"


def node_final(state: WorkflowState) -> WorkflowState:
    completed = [dimension for dimension in DIMENSIONS if is_filled(state.get("profile", {}).get(dimension))]
    summary = {
        "final_reply": state.get("final_reply", ""),
        "completed_dimensions": completed,
        "completion": f"{len(completed)}/{len(DIMENSIONS)}",
        "next_dimension": state.get("next_dimension", ""),
        "profile": state.get("profile", {}),
        "db_saved": state.get("db_saved", {}),
    }
    log(state, "08_final_summary", summary)
    return state


def build_graph():
    graph = StateGraph(WorkflowState)
    graph.add_node("load_context", node_load_context)
    graph.add_node("rule_extract", node_rule_extract)
    graph.add_node("llm1_classify", node_llm1_classify)
    graph.add_node("normalize_classifier", node_normalize_classifier)
    graph.add_node("persist_evidence", node_persist_evidence)
    graph.add_node("choose_next_dimension", node_choose_next_dimension)
    graph.add_node("llm2_respond", node_llm2_respond)
    graph.add_node("final", node_final)

    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "rule_extract")
    graph.add_edge("rule_extract", "llm1_classify")
    graph.add_edge("llm1_classify", "normalize_classifier")
    graph.add_edge("normalize_classifier", "persist_evidence")
    graph.add_edge("persist_evidence", "choose_next_dimension")
    graph.add_edge("choose_next_dimension", "llm2_respond")
    graph.add_edge("llm2_respond", "final")
    graph.add_edge("final", END)
    return graph.compile()


def workflow_result_from_state(state: WorkflowState) -> Dict[str, Any]:
    profile = state.get("profile", {}) or {}
    completed = [dimension for dimension in DIMENSIONS if is_filled(profile.get(dimension))]
    missing = [dimension for dimension in DIMENSIONS if dimension not in completed]
    evidence = state.get("classifier_result", {}).get("candidate_evidence", [])
    reply = state.get("final_reply") or deterministic_question(state)
    return {
        "agent": "learning-profile-langgraph-agent",
        "source": "llm",
        "provider": "xunfei-coding-plan",
        "model": get_setting("ANTHROPIC_MODEL", setting_default("ANTHROPIC_MODEL")),
        "status": "complete" if not missing else "collecting",
        "completeness": round(len(completed) / len(DIMENSIONS) * 100),
        "missingFields": missing,
        "extracted": {
            "mentionedDimensions": state.get("classifier_result", {}).get("mentioned_dimensions", []),
            "nextDimension": state.get("next_dimension", ""),
            "userIntent": state.get("classifier_result", {}).get("user_intent", ""),
        },
        "studentProfile": profile,
        "needFollowup": bool(missing),
        "followUpQuestions": [reply] if missing else [],
        "missingProfileDimensions": missing,
        "question": reply,
        "reply": reply,
        "summary": build_profile_summary(profile),
        "evidence": evidence,
        "dialogueGoal": state.get("next_dimension", ""),
        "debug": {
            "workflow": "langgraph",
            "db": state.get("db_saved", {}),
            "llm1Raw": state.get("llm1_raw", ""),
            "llm2Raw": state.get("llm2_raw", ""),
            "logs": state.get("logs", []),
        },
    }


def build_profile_summary(profile: Dict[str, Any]) -> str:
    parts: List[str] = []
    for dimension in DIMENSIONS:
        value = profile.get(dimension)
        if not is_filled(value):
            continue
        if isinstance(value, list):
            parts.append(f"{dimension}：{'、'.join(str(item) for item in value)}")
        else:
            parts.append(f"{dimension}：{value}")
    return "；".join(parts)


def run_profile_workflow(
    messages: List[Dict[str, str]],
    *,
    user_id: str = "current-user",
    profile: Dict[str, Any] | None = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    normalized_messages = [
        {
            "role": "assistant" if item.get("role") in {"assistant", "bot"} else "user",
            "content": str(item.get("content") or item.get("text") or "").strip(),
        }
        for item in messages
        if str(item.get("content") or item.get("text") or "").strip()
    ]
    initial_state: WorkflowState = {
        "user_id": str(user_id or "current-user"),
        "messages": normalized_messages,
        "profile": profile or {},
        "logs": [],
        "verbose": verbose,
    }
    final_state = build_graph().invoke(initial_state)
    return workflow_result_from_state(final_state)


def default_messages(user_input: str) -> List[Dict[str, str]]:
    return [
        {"role": "assistant", "content": "你好，我是你的数字人 AI 讲师，会陪你梳理嵌入式学习画像。"},
        {"role": "user", "content": "大二 学习嵌入式 stm32"},
        {"role": "assistant", "content": "你目前对 GPIO、串口、定时器、中断这些核心外设的实操如何？"},
        {"role": "user", "content": user_input},
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Verbose LangGraph learning-profile workflow demo.")
    parser.add_argument("--user", default="学习目标是为了参加智能车竞赛，最近串口和中断调试不太会。", help="latest user input")
    parser.add_argument("--user-id", default="demo-user", help="demo user id")
    args = parser.parse_args()

    initial_state: WorkflowState = {
        "user_id": args.user_id,
        "messages": default_messages(args.user),
        "profile": {},
        "logs": [],
        "verbose": True,
    }
    graph = build_graph()
    graph.invoke(initial_state)


if __name__ == "__main__":
    main()
