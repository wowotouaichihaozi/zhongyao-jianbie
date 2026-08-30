"""Learning-profile dialogue workflow agent.

This module wraps the learning-profile chat into a small workflow:
1. Load existing context.
2. Extract obvious evidence with deterministic rules.
3. Ask the configured LLM to classify mentioned/missing dimensions.
4. Merge and persist evidence.
5. Pick the next missing dimension and ask one follow-up question.

The workflow is intentionally defensive because the current Xunfei Coding Plan
model may return malformed JSON under pressure. Rules always win for obvious
facts, and LLM output is used as extra evidence instead of a single point of
failure.
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, TypedDict

try:
    from langgraph.graph import END, START, StateGraph
except Exception:  # pragma: no cover - fallback for minimal deployments
    END = "__end__"
    START = "__start__"
    StateGraph = None

try:
    from api_config import setting_default
    from common import get_setting
except ImportError:  # pragma: no cover
    from .api_config import setting_default
    from .common import get_setting


PROFILE_DIMENSIONS = [
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

PROFILE_COLLECTION_ORDER = [
    "专业/课程背景",
    "学习目标",
    "当前知识基础",
    "学习进度",
    "薄弱知识点",
    "可投入时间",
    "易错点类型",
    "学习风格/认知偏好",
    "资源形式偏好",
    "难度接受程度",
]

LIST_DIMENSIONS = {
    "学习目标",
    "薄弱知识点",
    "易错点类型",
    "学习风格/认知偏好",
    "资源形式偏好",
}

DB_PATH = Path(__file__).resolve().parent / "data" / "profile_workflow.sqlite"
PROFILE_AGENT_MAX_TOKENS = 128000


class LearningProfileModelUnavailable(RuntimeError):
    """Raised when a profile turn cannot obtain a usable model response."""


class WorkflowState(TypedDict, total=False):
    user_id: str
    messages: List[Dict[str, str]]
    profile: Dict[str, Any]
    latest_user_input: str
    rule_result: Dict[str, Any]
    agent_raw: str
    agent_json: Dict[str, Any]
    classifier_result: Dict[str, Any]
    db_saved: Dict[str, Any]
    next_dimension: str
    final_reply: str
    logs: List[Dict[str, Any]]
    verbose: bool


def _request_llm_text(system: str, prompt: str, **kwargs: Any) -> str:
    try:
        from learning_agents import request_llm_text
    except ImportError:  # pragma: no cover
        from .learning_agents import request_llm_text
    return request_llm_text(system, prompt, **kwargs)


def _extract_json(text: str) -> Dict[str, Any]:
    try:
        from learning_agents import extract_json
    except ImportError:  # pragma: no cover
        from .learning_agents import extract_json
    return extract_json(text)


def _log(state: WorkflowState, stage: str, payload: Any) -> None:
    state.setdefault("logs", []).append({"stage": stage, "payload": payload})
    if state.get("verbose"):
        print("\n" + "=" * 18 + f" {stage} " + "=" * 18)
        if isinstance(payload, str):
            print(payload)
        else:
            print(json.dumps(payload, ensure_ascii=False, indent=2))


def normalize_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    normalized: List[Dict[str, str]] = []
    for item in messages or []:
        role = "assistant" if item.get("role") in {"assistant", "bot"} else "user"
        content = str(item.get("content") or item.get("text") or "").strip()
        if content:
            normalized.append({"role": role, "content": content})
    return normalized


def normalize_value(dimension: str, value: Any) -> Any:
    if dimension in LIST_DIMENSIONS:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            parts = re.split(r"[、,，;；/]\s*", value.strip())
            return [item for item in parts if item]
        return []
    if isinstance(value, list):
        return "；".join(str(item).strip() for item in value if str(item).strip())
    return str(value or "").strip()


def merge_profile_value(dimension: str, old: Any, new: Any) -> Any:
    old_value = normalize_value(dimension, old)
    new_value = normalize_value(dimension, new)
    if dimension in LIST_DIMENSIONS:
        merged: List[str] = []
        for item in [*old_value, *new_value]:
            candidate = normalize_list_item(str(item))
            if not candidate:
                continue
            duplicate_index = next(
                (
                    index
                    for index, existing in enumerate(merged)
                    if candidate == existing or candidate in existing or existing in candidate
                ),
                -1,
            )
            if duplicate_index >= 0:
                if len(candidate) < len(merged[duplicate_index]):
                    merged[duplicate_index] = candidate
            else:
                merged.append(candidate)
        return merged
    if dimension == "可投入时间" and old_value and re.fullmatch(r"\s*\d{1,2}(?:\.\d)?\s*", str(new_value or "")):
        return old_value
    return new_value or old_value


def normalize_list_item(value: str) -> str:
    clean = re.sub(r"\s+", "", value or "").strip("，,。；; ")
    clean = re.sub(r"^(学习目标是|目标是|为了|想要|准备|希望|打算)", "", clean)
    return clean.strip("，,。；; ")


def append_profile_value(profile: Dict[str, Any], dimension: str, value: Any) -> None:
    if dimension not in PROFILE_DIMENSIONS:
        return
    normalized = normalize_value(dimension, value)
    if not is_filled(normalized):
        return
    profile[dimension] = merge_profile_value(dimension, profile.get(dimension), normalized)


def is_filled(value: Any) -> bool:
    if isinstance(value, list):
        return bool([item for item in value if str(item).strip()])
    return bool(str(value or "").strip())


def user_text(messages: List[Dict[str, str]]) -> str:
    return "；".join(
        item["content"].strip()
        for item in messages
        if item.get("role") == "user" and item.get("content", "").strip()
    )


def latest_user_text(messages: List[Dict[str, str]]) -> str:
    for item in reversed(messages):
        if item.get("role") == "user" and item.get("content", "").strip():
            return item["content"].strip()
    return ""


def previous_assistant_text_for_latest_user(messages: List[Dict[str, str]]) -> str:
    seen_latest_user = False
    for item in reversed(messages):
        role = item.get("role")
        content = item.get("content", "").strip()
        if not content:
            continue
        if not seen_latest_user:
            if role == "user":
                seen_latest_user = True
            continue
        if role == "assistant":
            return content
    return ""


def assistant_user_turns(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    turns: List[Dict[str, str]] = []
    previous_assistant = ""
    for item in messages:
        role = item.get("role")
        content = item.get("content", "").strip()
        if not content:
            continue
        if role == "assistant":
            previous_assistant = content
        elif role == "user":
            turns.append({"assistant": previous_assistant, "user": content})
    return turns


def is_short_contextual_answer(text: str) -> bool:
    clean = re.sub(r"\s+", "", text or "")
    return bool(clean) and len(clean) <= 24


def is_greeting_only(text: str) -> bool:
    clean = re.sub(r"[\s。！？!?，,～~.]+", "", text or "").lower()
    return clean in {"你好", "您好", "hi", "hello", "嗨", "在吗", "开始", "我们开始", "重新开始"}


def latest_user_message_matching(messages: List[Dict[str, str]], pattern: str) -> str:
    for item in reversed(messages):
        if item.get("role") != "user":
            continue
        content = str(item.get("content") or "").strip()
        if content and re.search(pattern, content, re.I):
            return content
    return ""


def extract_by_rules(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    text = user_text(messages)
    latest = latest_user_text(messages)
    previous_assistant = previous_assistant_text_for_latest_user(messages)
    turns = assistant_user_turns(messages)
    profile: Dict[str, Any] = {}
    evidence: List[Dict[str, Any]] = []

    grade = re.search(r"(大一|大二|大三|大四|研一|研二|研三|研究生|本科|专科)", text)
    major = re.search(r"([\u4e00-\u9fa5A-Za-z0-9]{2,18}(?:专业|学院|方向))", text)
    courses: List[str] = []
    if re.search(r"中医|tcm", text, re.I):
        courses.append("中医")
    course_patterns = [
        ("中医基础理论", r"中医基础|阴阳|五行|藏象|气血津液|经络"),
        ("中医诊断学", r"中医诊断|四诊|望诊|闻诊|问诊|切诊|舌诊|脉诊|八纲|辨证"),
        ("中药学", r"中药学|中药|性味归经"),
        ("方剂学", r"方剂学|方剂|君臣佐使|配伍"),
        ("针灸推拿学", r"针灸|腧穴|推拿"),
        ("中医临床医案", r"中医内科|医案|临床"),
    ]
    for course, pattern in course_patterns:
        if re.search(pattern, text, re.I):
            courses.append(course)
    if grade or major or courses:
        value = "；".join([part for part in [
            grade.group(0) if grade else "",
            major.group(1) if major else "",
            *courses,
        ] if part])
        append_profile_value(profile, "专业/课程背景", value)
        evidence.append({"dimension": "专业/课程背景", "text": value, "confidence": 0.9, "source": "rule"})

    goals: List[str] = []
    if re.search(r"执业医师|考研|升学", text):
        goals.append("夯实中医基础并准备专业考试")
    if re.search(r"竞赛|比赛|参赛", text) and not goals:
        goals.append("参加中医药相关竞赛")
    if re.search(r"课程设计|课程作业|医案作业", text):
        goals.append("完成中医课程与医案学习任务")
    if "就业" in text or "找工作" in text:
        goals.append("提升中医临床思维与岗位能力")
    goal_match = re.search(r"(?:学习目标是|目标是|为了|想要|准备|希望|打算)([^。！？!?；;，,]{2,40})", latest)
    if goal_match:
        goal_text = goal_match.group(1).strip(" ，,。")
        if goal_text:
            goals.append(goal_text)
    if re.search(r"目标|想|希望|打算|准备|课程|医案|竞赛|比赛|就业|找工作", text) and not goals:
        goals.append("提升中医辨证与医案实践能力")
    if goals:
        goals = list(dict.fromkeys(goals))
        append_profile_value(profile, "学习目标", goals)
        evidence.append({"dimension": "学习目标", "text": "；".join(goals), "confidence": 0.95, "source": "rule"})

    foundation_text = latest_user_message_matching(
        messages,
        r"零基础|没有(?:任何)?基础|基础(?:一般|较好|薄弱|扎实)|"
        r"有(?:一点|一定|些)?(?:中医|中药|方剂|辨证)?基础|学过|接触过|了解过|熟悉|已经掌握",
    )
    if foundation_text and not re.search(r"想|希望|准备|打算|目标|为了", foundation_text):
        value = foundation_text[:120]
        append_profile_value(profile, "当前知识基础", value)
        evidence.append({"dimension": "当前知识基础", "text": value, "confidence": 0.88, "source": "rule-explicit"})

    progress_text = latest_user_message_matching(
        messages,
        r"刚学(?:完|到)?|最近在学|正在学|目前(?:在)?学到|已经学到|学完了?|课程进度|学习进度",
    )
    if progress_text and not re.search(r"想|希望|准备|打算|目标|为了", progress_text):
        value = progress_text[:120]
        append_profile_value(profile, "学习进度", value)
        evidence.append({"dimension": "学习进度", "text": value, "confidence": 0.88, "source": "rule-explicit"})

    weak_points: List[str] = []
    weak_patterns = [
        ("阴阳五行", r"阴阳|五行"),
        ("藏象与气血津液", r"藏象|气血|津液|经络"),
        ("四诊信息归纳", r"四诊|望诊|闻诊|问诊|切诊|舌诊|脉诊"),
        ("八纲辨证", r"八纲|表里|寒热|虚实"),
        ("中药性味归经", r"中药|性味|归经|功效"),
        ("方剂配伍", r"方剂|君臣佐使|配伍"),
        ("医案辨析", r"医案|病机|治法|辨证"),
    ]
    for label, pattern in weak_patterns:
        if re.search(pattern, text, re.I) and re.search(r"不会|不熟|不太熟|卡|困难|薄弱|问题|攻克|实操|调试|排查", text):
            weak_points.append(label)
        else:
            for turn in turns:
                if re.search(r"哪一块|卡住|薄弱|辨证|四诊|中药|方剂|医案", turn["assistant"], re.I) and re.fullmatch(pattern, turn["user"], re.I):
                    weak_points.append(label)
                    break
    if re.search(r"辨证.*不会|不会.*辨证|医案.*不会|医案.*卡|方剂.*不熟|中药.*易混|病机.*不清", text):
        weak_points.append("中医理论到医案迁移")
    if weak_points:
        weak_points = list(dict.fromkeys(weak_points))
        append_profile_value(profile, "薄弱知识点", weak_points)
        evidence.append({"dimension": "薄弱知识点", "text": "；".join(weak_points), "confidence": 0.86, "source": "rule"})

    if re.search(r"容易|经常|总是|常常|卡|不熟|薄弱|错误|混淆", text) and re.search(r"辨证|病机|舌|脉|中药|方剂|配伍|医案", text):
        error_types = []
        if re.search(r"四诊|舌|脉", text):
            error_types.append("四诊信息提取不完整")
        if re.search(r"辨证|病机", text):
            error_types.append("证候鉴别与病机判断偏差")
        if re.search(r"中药|方剂|配伍", text):
            error_types.append("方药功效与配伍混淆")
        append_profile_value(profile, "易错点类型", error_types or ["理论到医案迁移困难"])
        evidence.append({"dimension": "易错点类型", "text": "；".join(profile["易错点类型"]), "confidence": 0.74, "source": "rule"})
    else:
        error_types = []
        for turn in turns:
            if not re.search(r"更容易错|错在|配置参数|硬件接线|代码逻辑|调试定位", turn["assistant"]):
                continue
            answer = turn["user"]
            if re.search(r"配置|参数|寄存器", answer):
                error_types.append("外设配置参数错误")
            if re.search(r"接线|硬件|时序", answer):
                error_types.append("硬件连接与时序问题")
            if re.search(r"代码|逻辑", answer):
                error_types.append("代码逻辑调试困难")
            if re.search(r"调试|定位|编译", answer):
                error_types.append("调试定位困难")
        if error_types:
            error_types = list(dict.fromkeys(error_types))
            append_profile_value(profile, "易错点类型", error_types)
            evidence.append({"dimension": "易错点类型", "text": "；".join(error_types), "confidence": 0.92, "source": "rule-context"})

    if re.search(r"视频|图文|文档|PPT|课件|代码|例程|实验|题", text, re.I):
        prefs = []
        for label, pattern in [
            ("视频讲解", r"视频"),
            ("图文步骤", r"图文|文档"),
            ("PPT课件", r"ppt|课件"),
            ("代码例程", r"代码|例程"),
            ("实验任务", r"实验"),
            ("练习题", r"题|练习"),
        ]:
            if re.search(pattern, text, re.I):
                prefs.append(label)
        append_profile_value(profile, "资源形式偏好", prefs)
        evidence.append({"dimension": "资源形式偏好", "text": "；".join(prefs), "confidence": 0.78, "source": "rule"})

    if re.search(r"喜欢|适合|希望|更想|先看|最后|步骤", text) and re.search(r"一步步|一步一步|步骤|案例|项目|先讲|先看|边做|实践|图解|思维导图|导图", text):
        styles = []
        if re.search(r"一步步|一步一步|步骤|图解|先讲|先看|思维导图|导图", text):
            styles.append("分步骤讲解")
        if re.search(r"案例|项目|边做|实践", text):
            styles.append("项目实践驱动")
        append_profile_value(profile, "学习风格/认知偏好", styles)
        evidence.append({"dimension": "学习风格/认知偏好", "text": "；".join(styles), "confidence": 0.78, "source": "rule"})
    else:
        styles = []
        for turn in turns:
            if not re.search(r"更适合|学习风格|原理图解|案例|一步步|直接做项目|回头补概念", turn["assistant"]):
                continue
            answer = turn["user"]
            if re.search(r"原理|图解|先学|先看|先讲", answer):
                styles.append("先理解原理图解")
            if re.search(r"一步|步骤|案例|跟着|手把手", answer):
                styles.append("分步骤案例练习")
            if re.search(r"项目|直接做|实战|实践", answer):
                styles.append("项目实践驱动")
        if styles:
            styles = list(dict.fromkeys(styles))
            append_profile_value(profile, "学习风格/认知偏好", styles)
            evidence.append({"dimension": "学习风格/认知偏好", "text": "；".join(styles), "confidence": 0.92, "source": "rule-context"})

    time_match = re.search(
        r"(?:每周|一周|每天|每日|周末)[^。！？!?；;]{0,18}(?:\d+|一|二|两|三|四|五|六|七|八|九|十)[^。！？!?；;]{0,8}(?:小时|h|天)|(?:\d+|一|二|两|三|四|五|六|七|八|九|十)\s*(?:小时|h|天)[^。！？!?；;]{0,8}(?:每周|一周|每天|每日|周末)",
        text,
        re.I,
    )
    if time_match:
        append_profile_value(profile, "可投入时间", time_match.group(0))
        evidence.append({"dimension": "可投入时间", "text": profile["可投入时间"], "confidence": 0.92, "source": "rule"})
    else:
        for turn in reversed(turns):
            answer = turn["user"]
            assistant_question = turn["assistant"]
            if re.search(r"每天|每日|每周|一周|周末|投入|多少时间|实验|复盘", assistant_question) and re.fullmatch(r"\s*(?:\d{1,2}(?:\.\d)?|半|一|二|两|三|四|五|六|七|八|九|十)(?:\s*(?:小时|h|天))?\s*", answer, re.I):
                unit = "天" if re.search(r"天", answer) else "小时"
                if re.search(r"每天|每日", assistant_question):
                    cadence = "每天"
                elif re.search(r"周末", assistant_question):
                    cadence = "每周末"
                else:
                    cadence = "每周"
                value = f"{cadence}约 {answer.strip()} {unit}"
                append_profile_value(profile, "可投入时间", value)
                evidence.append({"dimension": "可投入时间", "text": value, "confidence": 0.95, "source": "rule-context"})
                break

    if re.search(r"难一点|挑战|高难|简单一点|基础一点|循序渐进|逐步|从基础|别太难|进阶", text):
        if re.search(r"难一点|挑战|高难", text):
            value = "可以接受较高挑战，适合竞赛项目驱动训练"
        else:
            value = "适合从基础实验循序渐进到综合项目"
        append_profile_value(profile, "难度接受程度", value)
        evidence.append({"dimension": "难度接受程度", "text": value, "confidence": 0.8, "source": "rule"})

    mentioned = [dimension for dimension in PROFILE_DIMENSIONS if is_filled(profile.get(dimension))]
    missing = [dimension for dimension in PROFILE_DIMENSIONS if dimension not in mentioned]
    return {
        "mentioned_dimensions": mentioned,
        "missing_dimensions": missing,
        "candidate_evidence": evidence,
        "profile_patch": profile,
        "next_dimension": missing[0] if missing else "",
        "user_intent": "补充画像信息" if mentioned else "普通对话",
    }


def validate_classifier_json(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    mentioned = [item for item in data.get("mentioned_dimensions", []) if item in PROFILE_DIMENSIONS]
    missing = [item for item in data.get("missing_dimensions", []) if item in PROFILE_DIMENSIONS]
    evidence = []
    for item in data.get("candidate_evidence", []):
        if not isinstance(item, dict):
            continue
        dimension = item.get("dimension")
        text = str(item.get("text") or "").strip()
        if dimension not in PROFILE_DIMENSIONS or not text:
            continue
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
    if next_dimension not in PROFILE_DIMENSIONS:
        next_dimension = missing[0] if missing else ""
    return {
        "mentioned_dimensions": mentioned,
        "missing_dimensions": missing,
        "candidate_evidence": evidence,
        "next_dimension": next_dimension,
        "user_intent": str(data.get("user_intent") or "").strip() or "未知",
    }


def validate_agent_json(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    evidence = []
    raw_evidence = data.get("evidence")
    if raw_evidence is None:
        raw_evidence = data.get("candidate_evidence")
    for item in raw_evidence or []:
        if not isinstance(item, dict):
            continue
        dimension = str(item.get("dimension") or "").strip()
        text = str(item.get("value") or item.get("text") or "").strip()
        if dimension not in PROFILE_DIMENSIONS or not text:
            continue
        try:
            confidence = float(item.get("confidence", 0.75))
        except (TypeError, ValueError):
            confidence = 0.75
        evidence.append({
            "dimension": dimension,
            "text": text,
            "confidence": max(0.0, min(1.0, confidence)),
            "source": "llm-agent",
        })
    next_dimension = str(data.get("next_dimension") or data.get("nextDimension") or "").strip()
    if next_dimension not in PROFILE_DIMENSIONS:
        next_dimension = ""
    reply = str(data.get("reply") or data.get("question") or "").strip()
    user_intent = str(data.get("user_intent") or data.get("userIntent") or "补充画像信息").strip()
    return {
        "reply": reply,
        "candidate_evidence": evidence,
        "next_dimension": next_dimension,
        "user_intent": user_intent,
    }


def evidence_to_profile_patch(evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    profile: Dict[str, Any] = {}
    for item in evidence:
        dimension = item.get("dimension")
        text = str(item.get("text") or "").strip()
        if dimension in PROFILE_DIMENSIONS and text:
            append_profile_value(profile, dimension, [text] if dimension in LIST_DIMENSIONS else text)
    return profile


def merge_agent_result(current_profile: Dict[str, Any], agent_result: Dict[str, Any], rule_result: Dict[str, Any]) -> Dict[str, Any]:
    evidence = [*agent_result.get("candidate_evidence", [])]
    profile_patch = evidence_to_profile_patch(evidence)
    for item in rule_result.get("candidate_evidence", []):
        dimension = item.get("dimension")
        if dimension in PROFILE_DIMENSIONS and not is_filled(profile_patch.get(dimension)) and not is_filled(current_profile.get(dimension)):
            evidence.append({**item, "source": item.get("source") or "rule-fallback"})
            append_profile_value(profile_patch, dimension, item.get("text"))
    merged_profile = {}
    for source in [current_profile, profile_patch]:
        for dimension in PROFILE_DIMENSIONS:
            if dimension in source:
                append_profile_value(merged_profile, dimension, source.get(dimension))
    missing = [dimension for dimension in PROFILE_DIMENSIONS if not is_filled(merged_profile.get(dimension))]
    agent_next_dimension = agent_result.get("next_dimension") or ""
    next_dimension = agent_next_dimension if agent_next_dimension in missing else ""
    mentioned = [dimension for dimension in PROFILE_DIMENSIONS if is_filled(profile_patch.get(dimension))]
    return {
        "mentioned_dimensions": mentioned,
        "missing_dimensions": missing,
        "candidate_evidence": evidence,
        "profile_patch": profile_patch,
        "agent_next_dimension": agent_next_dimension,
        "next_dimension": next_dimension,
        "reply": agent_result.get("reply") or "",
        "user_intent": agent_result.get("user_intent") or "补充画像信息",
    }


def merge_classifier(rule_result: Dict[str, Any], llm_result: Dict[str, Any]) -> Dict[str, Any]:
    evidence = [*rule_result.get("candidate_evidence", []), *llm_result.get("candidate_evidence", [])]
    profile_patch = {}
    for source_patch in [rule_result.get("profile_patch") or {}, evidence_to_profile_patch(llm_result.get("candidate_evidence", []))]:
        for dimension, value in source_patch.items():
            append_profile_value(profile_patch, dimension, value)
    mentioned = [dimension for dimension in PROFILE_DIMENSIONS if is_filled(profile_patch.get(dimension))]
    for dimension in [*rule_result.get("mentioned_dimensions", []), *llm_result.get("mentioned_dimensions", [])]:
        if dimension in PROFILE_DIMENSIONS and dimension not in mentioned:
            mentioned.append(dimension)
    missing = [dimension for dimension in PROFILE_DIMENSIONS if dimension not in mentioned]
    next_dimension = llm_result.get("next_dimension") or rule_result.get("next_dimension") or (missing[0] if missing else "")
    if next_dimension not in missing and missing:
        next_dimension = missing[0]
    return {
        "mentioned_dimensions": mentioned,
        "missing_dimensions": missing,
        "candidate_evidence": evidence,
        "profile_patch": profile_patch,
        "next_dimension": next_dimension,
        "user_intent": llm_result.get("user_intent") or rule_result.get("user_intent") or "补充画像信息",
    }


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS learning_profile_dialogue_turn (
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
            CREATE TABLE IF NOT EXISTS learning_profile_evidence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                dimension TEXT NOT NULL,
                evidence_text TEXT NOT NULL,
                confidence REAL NOT NULL,
                source TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )


def persist_evidence(user_id: str, messages: List[Dict[str, str]], evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    init_db()
    now = int(time.time())
    with sqlite3.connect(DB_PATH) as conn:
        for item in messages[-2:]:
            conn.execute(
                "INSERT INTO learning_profile_dialogue_turn(user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (user_id, item.get("role") or "user", item.get("content") or "", now),
            )
        saved = 0
        for item in evidence:
            dimension = item.get("dimension")
            text = str(item.get("text") or "").strip()
            if dimension not in PROFILE_DIMENSIONS or not text:
                continue
            conn.execute(
                """
                INSERT INTO learning_profile_evidence(user_id, dimension, evidence_text, confidence, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    dimension,
                    text,
                    float(item.get("confidence") or 0.65),
                    str(item.get("source") or "unknown"),
                    now,
                ),
            )
            saved += 1
    return {"dialogue_turns": min(2, len(messages)), "evidence_rows": saved, "db": str(DB_PATH)}


def load_persisted_profile(user_id: str) -> Dict[str, Any]:
    if not DB_PATH.exists():
        return {}
    init_db()
    profile: Dict[str, Any] = {}
    try:
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                """
                SELECT dimension, evidence_text
                FROM learning_profile_evidence
                WHERE user_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (user_id,),
            ).fetchall()
        for dimension, text in rows:
            append_profile_value(profile, dimension, [text] if dimension in LIST_DIMENSIONS else text)
    except sqlite3.Error:
        return {}
    return profile


def clear_persisted_profile_dialogue(user_id: str) -> Dict[str, Any]:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        evidence_deleted = conn.execute(
            "DELETE FROM learning_profile_evidence WHERE user_id = ?",
            (user_id,),
        ).rowcount
        turns_deleted = conn.execute(
            "DELETE FROM learning_profile_dialogue_turn WHERE user_id = ?",
            (user_id,),
        ).rowcount
    return {
        "dialogue_turns_deleted": max(0, turns_deleted),
        "evidence_rows_deleted": max(0, evidence_deleted),
        "db": str(DB_PATH),
    }


def node_load_context(state: WorkflowState) -> WorkflowState:
    messages = normalize_messages(state.get("messages") or [])
    user_id = str(state.get("user_id") or "current-user")
    profile = {}
    for source in [load_persisted_profile(user_id), state.get("profile") or {}]:
        for dimension in PROFILE_DIMENSIONS:
            if dimension in source:
                append_profile_value(profile, dimension, source.get(dimension))
    state.update({"messages": messages, "user_id": user_id, "profile": profile, "latest_user_input": latest_user_text(messages)})
    _log(state, "load_context", {"user_id": user_id, "messages": messages, "profile": profile})
    return state


def node_rule_extract(state: WorkflowState) -> WorkflowState:
    result = extract_by_rules(state.get("messages") or [])
    state["rule_result"] = result
    _log(state, "rule_extract", result)
    return state


def node_llm_agent_decide(state: WorkflowState) -> WorkflowState:
    latest = state.get("latest_user_input") or ""
    previous_assistant = previous_assistant_text_for_latest_user(state.get("messages") or [])
    effective_profile: Dict[str, Any] = {}
    for source in [state.get("profile") or {}, (state.get("rule_result") or {}).get("profile_patch") or {}]:
        for dimension in PROFILE_DIMENSIONS:
            if dimension in source:
                append_profile_value(effective_profile, dimension, source.get(dimension))
    missing = [dimension for dimension in PROFILE_DIMENSIONS if not is_filled(effective_profile.get(dimension))]
    system = "你是中药鉴别的学习画像对话智能体。必须只返回一个 JSON 对象，不要 Markdown。"
    prompt = f"""
你需要基于中医学习对话完成两件事：
1. 理解用户最新回复，抽取本轮可以作为学习画像证据的信息。
2. 生成给用户看的自然回复，并只追问一个下一步最需要补齐的维度。

画像维度只能从以下列表选择：
{json.dumps(PROFILE_DIMENSIONS, ensure_ascii=False)}

当前已有画像（包含本轮已明确提取的信息）：
{json.dumps(effective_profile, ensure_ascii=False)}

当前缺失维度：
{json.dumps(missing, ensure_ascii=False)}

建议采集顺序：
{json.dumps(PROFILE_COLLECTION_ORDER, ensure_ascii=False)}

上一句助手问题：
{previous_assistant}

最新用户输入：
{latest}

完整对话：
{json.dumps(state.get("messages") or [], ensure_ascii=False)}

返回 JSON 结构，字段必须齐全：
{{
  "reply": "给学生看的 1 到 2 句自然回复，最后只问一个问题",
  "evidence": [
    {{"dimension": "学习风格/认知偏好", "value": "先理解原理，再按步骤练习", "confidence": 0.91}}
  ],
  "next_dimension": "资源形式偏好",
  "user_intent": "补充画像信息"
}}

要求：
1. 如果用户的短回复是在回答上一句助手问题，必须结合上一句问题理解，不要因为回答很短就忽略。
2. evidence 只记录用户明确表达或能从上一问一答直接推出的信息；不要编造用户没有说过的目标。
3. next_dimension 必须从当前缺失维度中选择，并尽量遵守建议采集顺序；已经有值的维度不要再追问。
4. reply 必须自然、简短、面向中医学习；如果本轮补齐了一个维度，先简短确认，再问 next_dimension。
5. 如果最新用户输入只是“你好/开始/在吗”这类寒暄，evidence 返回空数组，但 reply 必须继续追问专业/课程背景，不能只回复“你好”“我们开始”。
6. 如果所有维度都完整，next_dimension 为空字符串，reply 给出简短总结。
7. 只输出 JSON 对象。
"""
    last_error: Exception | None = None
    for attempt in range(2):
        retry_instruction = ""
        if attempt:
            retry_instruction = (
                "\n上一次输出无效或与上一句助手回复重复。请重新理解最新回答，"
                "生成不同且能推进画像采集的回复；不得复述上一句助手内容。"
            )
        try:
            raw = _request_llm_text(
                system,
                prompt + retry_instruction,
                max_tokens=PROFILE_AGENT_MAX_TOKENS,
                timeout=35,
                json_mode=True,
                allow_anthropic_fallback=False,
            )
            parsed = _extract_json(raw)
            validated = validate_agent_json(parsed)
            if is_greeting_only(latest):
                # A greeting may advance the conversation but cannot fill evidence.
                validated["candidate_evidence"] = []
            reply = str(validated.get("reply") or "").strip()
            next_dimension = str(validated.get("next_dimension") or "").strip()
            projected = merge_agent_result(
                state.get("profile") or {},
                validated,
                state.get("rule_result") or {},
            )
            projected_missing = projected.get("missing_dimensions") or []
            if not reply:
                raise ValueError("大模型未返回可显示回复")
            if previous_assistant and reply == previous_assistant.strip():
                raise ValueError("大模型连续返回重复回复")
            if projected_missing and next_dimension not in projected_missing:
                validated["next_dimension"] = projected_missing[0]
            if not projected_missing:
                validated["next_dimension"] = ""
            state["agent_raw"] = raw
            state["agent_json"] = validated
            break
        except Exception as exc:
            last_error = exc
    else:
        raise LearningProfileModelUnavailable(
            "学习画像大模型不可用或未返回有效回复，请稍后重试。"
        ) from last_error
    _log(state, "llm_agent_decide", {"raw": state.get("agent_raw"), "json": state.get("agent_json")})
    return state


def node_normalize_agent(state: WorkflowState) -> WorkflowState:
    agent_result = validate_agent_json(state.get("agent_json"))
    merged = merge_agent_result(state.get("profile") or {}, agent_result, state.get("rule_result") or {})
    for dimension, value in (merged.get("profile_patch") or {}).items():
        append_profile_value(state["profile"], dimension, value)
    state["classifier_result"] = merged
    _log(state, "normalize_agent", merged)
    return state


def node_persist_evidence(state: WorkflowState) -> WorkflowState:
    result = persist_evidence(
        state["user_id"],
        state.get("messages") or [],
        (state.get("classifier_result") or {}).get("candidate_evidence") or [],
    )
    state["db_saved"] = result
    _log(state, "persist_evidence", result)
    return state


def node_choose_next_dimension(state: WorkflowState) -> WorkflowState:
    missing = [dimension for dimension in PROFILE_DIMENSIONS if not is_filled((state.get("profile") or {}).get(dimension))]
    next_dimension = (state.get("classifier_result") or {}).get("next_dimension") or ""
    if missing and next_dimension not in missing:
        raise LearningProfileModelUnavailable(
            "学习画像大模型未返回有效的下一采集维度，请稍后重试。"
        )
    state["next_dimension"] = next_dimension
    _log(state, "choose_next_dimension", {"missing": missing, "next_dimension": next_dimension})
    return state


def node_finalize_reply(state: WorkflowState) -> WorkflowState:
    next_dimension = state.get("next_dimension") or ""
    classifier_result = state.get("classifier_result") or {}
    raw_reply = classifier_result.get("reply") or ""
    reply = shorten_reply(raw_reply, "")
    previous_assistant = previous_assistant_text_for_latest_user(state.get("messages") or [])
    if previous_assistant and reply and reply.strip() == previous_assistant.strip():
        raise LearningProfileModelUnavailable(
            "学习画像大模型连续返回重复回复，请稍后重试。"
        )
    if not reply:
        raise LearningProfileModelUnavailable(
            "学习画像大模型未返回可显示内容，请稍后重试。"
        )
    if next_dimension and not re.search(r"[？?]", reply):
        raise LearningProfileModelUnavailable(
            "学习画像大模型未返回有效追问，请稍后重试。"
        )
    state["final_reply"] = reply
    _log(state, "finalize_reply", {"reply": state.get("final_reply")})
    return state


def node_final(state: WorkflowState) -> WorkflowState:
    result = workflow_result_from_state(state)
    _log(state, "final", {key: value for key, value in result.items() if key != "workflow"})
    return state


def shorten_reply(text: str, fallback: str) -> str:
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if not clean:
        return fallback
    clean = re.sub(r"^```[a-zA-Z]*|```$", "", clean).strip()
    sentences = re.findall(r"[^。！？!?]+[。！？!?]?", clean)
    if sentences:
        question_index = next((idx for idx in range(len(sentences) - 1, -1, -1) if re.search(r"[？?]", sentences[idx])), -1)
        if question_index >= 0:
            context_candidates = [
                sentence
                for idx, sentence in enumerate(sentences[:question_index])
                if idx != question_index and len(sentence.strip("。！？!? ")) > 3 and sentence.strip("。！？!? ") not in {"收到", "好的", "明白"}
            ]
            clean = "".join([*(context_candidates[-1:] or []), sentences[question_index]]).strip()
        else:
            clean = "".join(sentences[:2]).strip()
    return clean[:120] or fallback


def build_workflow():
    if StateGraph is None:
        return None
    graph = StateGraph(WorkflowState)
    graph.add_node("load_context", node_load_context)
    graph.add_node("rule_extract", node_rule_extract)
    graph.add_node("llm_agent_decide", node_llm_agent_decide)
    graph.add_node("normalize_agent", node_normalize_agent)
    graph.add_node("persist_evidence", node_persist_evidence)
    graph.add_node("choose_next_dimension", node_choose_next_dimension)
    graph.add_node("finalize_reply", node_finalize_reply)
    graph.add_node("final", node_final)
    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "rule_extract")
    graph.add_edge("rule_extract", "llm_agent_decide")
    graph.add_edge("llm_agent_decide", "normalize_agent")
    graph.add_edge("normalize_agent", "persist_evidence")
    graph.add_edge("persist_evidence", "choose_next_dimension")
    graph.add_edge("choose_next_dimension", "finalize_reply")
    graph.add_edge("finalize_reply", "final")
    graph.add_edge("final", END)
    return graph.compile()


def run_without_langgraph(state: WorkflowState) -> WorkflowState:
    for node in [
        node_load_context,
        node_rule_extract,
        node_llm_agent_decide,
        node_normalize_agent,
        node_persist_evidence,
        node_choose_next_dimension,
        node_finalize_reply,
        node_final,
    ]:
        state = node(state)
    return state


def build_profile_summary(profile: Dict[str, Any]) -> str:
    parts = []
    for dimension in PROFILE_DIMENSIONS:
        value = profile.get(dimension)
        if not is_filled(value):
            continue
        if isinstance(value, list):
            display = "、".join(str(item) for item in value[:4])
        else:
            display = str(value)
        parts.append(f"{dimension}：{display}")
    return "；".join(parts)


def workflow_result_from_state(state: WorkflowState) -> Dict[str, Any]:
    profile = state.get("profile") or {}
    missing = [dimension for dimension in PROFILE_DIMENSIONS if not is_filled(profile.get(dimension))]
    completeness = round((len(PROFILE_DIMENSIONS) - len(missing)) / len(PROFILE_DIMENSIONS) * 100)
    reply = str(state.get("final_reply") or "").strip()
    next_dimension = state.get("next_dimension") or ""
    if not reply:
        raise LearningProfileModelUnavailable(
            "学习画像大模型未返回可显示内容，请稍后重试。"
        )
    profile_payload = {dimension: profile.get(dimension, [] if dimension in LIST_DIMENSIONS else "") for dimension in PROFILE_DIMENSIONS}
    profile_payload["补充信息"] = {
        "student_id": state.get("user_id") or "current-user",
        "source_type": "学习背景对话",
        "baseInfo": {},
        "证据摘要": build_profile_summary(profile)[:500],
    }
    return {
        "agent": "learning-profile-workflow-agent",
        "source": "llm",
        "provider": "configured-openai-compatible",
        "model": get_setting("ANTHROPIC_MODEL", setting_default("ANTHROPIC_MODEL")),
        "status": "complete" if not missing else "collecting",
        "completeness": completeness,
        "missingFields": missing,
        "missingProfileDimensions": missing,
        "studentProfile": profile_payload,
        "needFollowup": bool(missing),
        "followUpQuestions": [reply] if next_dimension else [],
        "question": reply,
        "reply": reply,
        "summary": build_profile_summary(profile),
        "nextDimension": next_dimension,
        "workflow": {
            "mentionedDimensions": (state.get("classifier_result") or {}).get("mentioned_dimensions") or [],
            "candidateEvidence": (state.get("classifier_result") or {}).get("candidate_evidence") or [],
            "dbSaved": state.get("db_saved") or {},
            "agentRaw": state.get("agent_raw") or "",
            "agentJson": state.get("agent_json") or {},
            "logs": state.get("logs") or [],
        },
    }


def run_learning_profile_workflow(
    messages: List[Dict[str, Any]],
    user_id: str = "current-user",
    profile: Dict[str, Any] | None = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    state: WorkflowState = {
        "messages": normalize_messages(messages),
        "user_id": str(user_id or "current-user"),
        "profile": profile or {},
        "logs": [],
        "verbose": verbose,
    }
    app = build_workflow()
    if app is None:
        final_state = run_without_langgraph(state)
    else:
        final_state = app.invoke(state)
    return workflow_result_from_state(final_state)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--user", default="我是中医学专业大二学生，正在学中医诊断学，八纲辨证和方剂配伍不太熟，每周能学习 6 小时。")
    parser.add_argument("--user-id", default="demo-user")
    args = parser.parse_args()
    result = run_learning_profile_workflow([{"role": "user", "content": args.user}], user_id=args.user_id, verbose=True)
    print("\nFINAL RESULT")
    print(json.dumps(result, ensure_ascii=False, indent=2))
