import logging
import os
import re
import secrets
import threading
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

try:
    from interview_profiles import (
        DEFAULT_POSITION_KEY,
        detect_profile_skills,
        get_interview_profile,
        public_interview_profiles,
    )
    from mimo_interview_client import (
        classify_answer_type,
        generate_interview_followup,
        generate_interview_question,
        generate_interview_summary,
        normalize_answer_text as mimo_normalize_answer_text,
        score_interview_answer,
    )
except Exception:  # pragma: no cover - package-style import fallback
    try:
        from .interview_profiles import (
            DEFAULT_POSITION_KEY,
            detect_profile_skills,
            get_interview_profile,
            public_interview_profiles,
        )
        from .mimo_interview_client import (
            classify_answer_type,
            generate_interview_followup,
            generate_interview_question,
            generate_interview_summary,
            normalize_answer_text as mimo_normalize_answer_text,
            score_interview_answer,
        )
    except Exception:  # pragma: no cover - keep the local interview available without model deps/config
        classify_answer_type = None
        generate_interview_followup = None
        generate_interview_question = None
        generate_interview_summary = None
        mimo_normalize_answer_text = None
        score_interview_answer = None
        DEFAULT_POSITION_KEY = "stm32_developer"

        def get_interview_profile(position_key: Optional[str] = None, position_label: Optional[str] = None) -> Dict[str, Any]:
            return {
                "positionKey": DEFAULT_POSITION_KEY,
                "label": position_label or "STM32 开发工程师",
                "coreSkills": [
                    "project_experience",
                    "c_language",
                    "gpio",
                    "interrupt",
                    "uart",
                    "debugging",
                    "result_quantification",
                ],
                "basicQuestions": [
                    "没关系，我们从基础开始。你能简单解释一下 GPIO 是什么吗？",
                    "那我们再换一个更基础的问题。你知道数字信号中的高电平和低电平是什么意思吗？",
                ],
                "projectQuestionTemplate": "请先介绍一个与你应聘岗位最相关的项目，重点说明你的职责、技术难点和结果。",
                "scoringHints": "重点看岗位基础、项目经历和问题分析能力。",
            }

        def detect_profile_skills(text: str, profile: Dict[str, Any]) -> List[str]:
            return []

        def public_interview_profiles() -> Dict[str, Dict[str, Any]]:
            return {}


_SESSION_LOCK = threading.Lock()
_SESSIONS: Dict[str, Dict[str, Any]] = {}
logger = logging.getLogger(__name__)

DEFAULT_MIN_ROUNDS = 3
DEFAULT_MAX_ROUNDS = 8
DEFAULT_MAX_DURATION_MINUTES = 15
LOW_SCORE_THRESHOLD = 20
VERY_LOW_SCORE_THRESHOLD = 10
EFFECTIVE_SCORE_THRESHOLD = 40
HIGH_SCORE_THRESHOLD = 80
EXCELLENT_SCORE_THRESHOLD = 85
SKILL_PROBE_QUESTIONS = {
    "c_language": "在 STM32 程序中，如果中断和主循环共享一个变量，为什么通常要使用 volatile？",
    "gpio": "如果 GPIO 控制的 LED 没有反应，你会按什么顺序检查时钟、模式和硬件接线？",
    "interrupt": "配置 EXTI 外部中断后一直不触发，你会检查哪些寄存器配置和 NVIC 设置？",
    "uart": "UART 收发出现乱码或丢包时，你会优先检查哪些参数和程序逻辑？",
    "timer_pwm": "如果 PWM 输出频率不正确，你会如何检查定时器时钟、预分频和重装值？",
    "adc": "使用 ADC 采集传感器数据时，你会如何处理采样误差并验证结果？",
    "sensor": "传感器采集值异常时，你会如何区分接线、时序、驱动和数据换算问题？",
    "debugging": "请说一个外设没有响应时的排查顺序，以及你会保留哪些调试证据。",
    "project_experience": "请选一个你实际负责的模块，说明它的输入、处理流程和输出结果。",
    "result_validation": "你会用什么现象、日志或测量数据证明功能已经稳定通过？",
    "result_quantification": "你会用哪些可量化指标说明项目最终达到了预期结果？",
}
CORE_SKILLS = set(get_interview_profile(DEFAULT_POSITION_KEY).get("coreSkills") or [])
DIFFICULTY_LABELS = {
    "intern": "实习",
    "campus": "校招",
    "basic": "基础",
    "medium": "中等",
    "advanced": "进阶",
    # Backward compatibility with older frontend values.
    "junior": "基础",
    "senior": "进阶",
}


def difficulty_label(value: Any, explicit_label: Any = None) -> str:
    label = _clean_text(explicit_label)
    if label:
        return label
    text = _clean_text(value, "medium")
    return DIFFICULTY_LABELS.get(text, text)


def difficulty_value(value: Any) -> str:
    text = _clean_text(value, "medium")
    reverse = {label: key for key, label in DIFFICULTY_LABELS.items() if key in {"intern", "campus", "basic", "medium", "advanced"}}
    aliases = {"junior": "basic", "senior": "advanced"}
    return aliases.get(text, reverse.get(text, text))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def normalize_answer_text(text: str) -> str:
    if mimo_normalize_answer_text:
        return mimo_normalize_answer_text(text)
    return "".join(str(text or "").strip().lower().split())


def classify_answer(answer: str, profile: Optional[Dict[str, Any]] = None, session: Optional[Dict[str, Any]] = None) -> str:
    active_profile = profile or (_profile_for_session(session) if session else get_interview_profile(DEFAULT_POSITION_KEY))
    if classify_answer_type:
        try:
            return classify_answer_type(answer, profile=active_profile)
        except TypeError:
            return classify_answer_type(answer)
    normalized = normalize_answer_text(answer)
    if not normalized:
        return "nonsense_answer"
    if len(normalized) < 2:
        return "too_short"
    return "vague_answer"


def _profile_for_session(session: Dict[str, Any]) -> Dict[str, Any]:
    profile = session.get("profile")
    if isinstance(profile, dict) and profile.get("coreSkills"):
        return profile
    return get_interview_profile(session.get("positionKey") or session.get("position_key"), session.get("position"))


def _profile_core_skills(profile: Dict[str, Any]) -> set[str]:
    return {str(item).strip() for item in profile.get("coreSkills", []) if str(item).strip()}


def _basic_question(profile: Dict[str, Any], index: int, fallback: str) -> str:
    questions = profile.get("basicQuestions") or []
    if questions:
        return _clean_text(questions[min(max(index, 0), len(questions) - 1)], fallback)
    return fallback


def _default_project_question(position: str, topic: str, profile: Dict[str, Any]) -> str:
    template = _clean_text(profile.get("projectQuestionTemplate"))
    if template:
        return template
    return f"请介绍一个与你应聘的{position}岗位最相关的项目，重点说明你的职责、关键问题和结果。"


def _safe_fallback_reason(exc: Any) -> str:
    reason = _clean_text(exc, "model unavailable")
    for key in ["MIMO_API_KEY", "XIAOMI_API_KEY", "ANTHROPIC_AUTH_TOKEN", "AVATAR_API_KEY", "AVATAR_API_SECRET"]:
        value = os.getenv(key, "")
        if value:
            reason = reason.replace(value, "***")
    reason = re.sub(r"mimo", "model", reason, flags=re.IGNORECASE)
    return reason[:500]


def _safe_console_print(message: str) -> None:
    try:
        print(message, flush=True)
    except (OSError, ValueError):
        logger.debug("interview console output is unavailable", exc_info=True)


def _log_runtime_event(event: str, **kwargs: Any) -> None:
    logger.info("[Interview Runtime] %s %s", event, kwargs)
    _safe_console_print(f"[Interview Runtime] {event} {kwargs}")


def _int_payload(value: Any, fallback: int) -> int:
    try:
        parsed = int(value)
        return parsed if parsed > 0 else fallback
    except (TypeError, ValueError):
        return fallback


def _total_answer_count(session: Dict[str, Any]) -> int:
    return len(session.get("answers") or [])


def _bool_payload(value: Any, fallback: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return fallback


def _minutes_since(value: Any) -> float:
    try:
        started_at = datetime.fromisoformat(str(value))
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - started_at).total_seconds() / 60
    except Exception:
        return 0.0


def _score_answer(answer: str, profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if score_interview_answer:
        try:
            result = score_interview_answer(answer, profile=profile)
            return {
                "answerType": _clean_text(result.get("answerType"), "vague_answer"),
                "answerScore": max(0, min(100, int(result.get("answerScore", 25)))),
            }
        except Exception:
            pass
    answer_type = classify_answer(answer, profile=profile)
    fallback_scores = {
        "strong_answer": 85,
        "normal_answer": 55,
            "weak_answer": 32,
            "vague_answer": 25,
            "too_short": 8,
            "no_experience": 8,
            "dont_know": 5,
            "irrelevant_answer": 5,
            "negative_answer": 5,
            "refuse_answer": 5,
            "end_request": 5,
            "nonsense_answer": 3,
        }
    return {"answerType": answer_type, "answerScore": fallback_scores.get(answer_type, 25)}


def _is_low_answer(answer_score: int) -> bool:
    return answer_score < LOW_SCORE_THRESHOLD


def _is_effective_answer(answer_score: int, answer_type: str) -> bool:
    return answer_score >= EFFECTIVE_SCORE_THRESHOLD and answer_type in {"normal_answer", "strong_answer"}


def _is_dont_know_type(answer_type: str) -> bool:
    return answer_type in {"dont_know", "no_experience"}


def _is_irrelevant_type(answer_type: str) -> bool:
    return answer_type in {"irrelevant_answer", "negative_answer", "nonsense_answer"}


def _is_refuse_type(answer_type: str) -> bool:
    return answer_type == "refuse_answer"


def _is_nonsense_type(answer_type: str) -> bool:
    return answer_type in {"nonsense_answer", "too_short"}


def _detect_covered_skills(text: str, profile: Optional[Dict[str, Any]] = None) -> List[str]:
    if profile:
        detected = detect_profile_skills(text, profile)
        if detected:
            return detected
    content = _clean_text(text).lower()
    skill_keywords = {
        "project_experience": ["项目", "课程设计", "实验", "职责", "需求", "方案"],
        "c_language": ["c语言", "指针", "结构体", "数组", "内存", "volatile", "static"],
        "gpio": ["gpio", "io口", "引脚", "高电平", "低电平", "输入模式", "输出模式", "led", "按键"],
        "interrupt": ["中断", "irq", "nvic", "中断服务", "外部中断", "优先级"],
        "uart": ["uart", "usart", "串口", "波特率", "通信", "收发", "上位机"],
        "debugging": ["调试", "排查", "定位", "解决", "bug", "异常", "示波器", "日志"],
        "result_quantification": ["提升", "降低", "优化", "稳定", "通过率", "延迟", "耗时", "资源", "%", "ms", "结果"],
    }
    covered = []
    for skill, keywords in skill_keywords.items():
        if any(keyword in content for keyword in keywords):
            covered.append(skill)
    return covered


def _has_answer_evidence_for_project_followup(answer: str) -> bool:
    content = normalize_answer_text(answer)
    markers = [
        "项目", "实验", "课程设计", "负责", "做过", "实现", "配置", "调试", "排查", "采集", "上传", "结果",
        "led", "gpio", "io口", "按键", "串口", "uart", "usart", "中断", "定时器", "pwm", "adc", "传感器",
        "外设", "寄存器", "hal", "标准库", "代码", "烧录", "示波器", "上位机",
        "stm32", "单片机", "环境监测", "终端",
    ]
    return any(normalize_answer_text(marker) in content for marker in markers)


def _basic_specific_followup(profile: Dict[str, Any], fallback: str) -> str:
    question = _basic_question(profile, 0, fallback)
    return (
        "你提到和当前方向有关，但还没有具体细节。请你具体说一个接触过的实验，"
        f"比如 LED 点亮、按键检测或串口通信。也可以先回答这个基础问题：{question}"
    )


def _normalized_question_text(value: Any) -> str:
    text = normalize_answer_text(_clean_text(value))
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", text)
    for filler in ("请你", "请", "刚才", "具体", "进一步", "可以", "一个"):
        text = text.replace(filler, "")
    return text


def _questions_are_similar(left: Any, right: Any) -> bool:
    normalized_left = _normalized_question_text(left)
    normalized_right = _normalized_question_text(right)
    if not normalized_left or not normalized_right:
        return False
    if normalized_left == normalized_right:
        return True
    shorter, longer = sorted((normalized_left, normalized_right), key=len)
    if len(shorter) >= 10 and shorter in longer:
        return True
    return SequenceMatcher(None, normalized_left, normalized_right).ratio() >= 0.72


def _is_repeated_question(candidate: Any, asked_questions: List[Any]) -> bool:
    return any(_questions_are_similar(candidate, asked) for asked in asked_questions if _clean_text(asked))


def _distinct_question_for_session(session: Dict[str, Any], preferred: str) -> str:
    profile = _profile_for_session(session)
    asked_questions = list(session.get("questions") or [])
    covered_skills = set(session.get("coveredSkills") or [])
    candidates = [_clean_text(preferred)]

    for skill in profile.get("coreSkills") or []:
        if skill not in covered_skills and skill in SKILL_PROBE_QUESTIONS:
            candidates.append(SKILL_PROBE_QUESTIONS[skill])

    basic_questions = [_clean_text(item) for item in profile.get("basicQuestions") or [] if _clean_text(item)]
    if basic_questions:
        offset = max(0, len(session.get("answers") or []) - 1) % len(basic_questions)
        candidates.extend(basic_questions[offset:] + basic_questions[:offset])

    candidates.extend(
        [
            "如果现在让你现场排查一个 STM32 外设没有响应的问题，你会先检查哪三项？",
            "请从 GPIO、中断和 UART 中任选一个，说明初始化步骤以及如何验证配置正确。",
        ]
    )
    for candidate in candidates:
        if candidate and not _is_repeated_question(candidate, asked_questions):
            return candidate

    round_no = len(session.get("answers") or []) + 1
    return f"我们换到第 {round_no} 个能力点。请说明你会如何验证一个外设功能已经正确且稳定。"


def _normalize_skills(value: Any, profile: Optional[Dict[str, Any]] = None) -> List[str]:
    if isinstance(value, str):
        items = [item.strip() for item in value.replace("；", ",").replace(";", ",").split(",")]
    elif isinstance(value, list):
        items = [str(item).strip() for item in value]
    else:
        items = []
    allowed = _profile_core_skills(profile or get_interview_profile(DEFAULT_POSITION_KEY))
    return [item for item in items if item in allowed]


def _normalize_frame_analysis_payload(value: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    analysis = _clean_text(value.get("analysis") or value.get("content"))
    suggestions_value = value.get("suggestions")
    if isinstance(suggestions_value, list):
        suggestions = [str(item).strip() for item in suggestions_value if str(item).strip()]
    elif isinstance(suggestions_value, str) and suggestions_value.strip():
        suggestions = [item.strip() for item in suggestions_value.replace("；", ";").split(";") if item.strip()]
    else:
        suggestions = []
    confidence = _clean_text(value.get("confidence"), "medium").lower()
    if confidence not in {"low", "medium", "high"}:
        confidence = "medium"
    confidence_signal = _clean_text(value.get("confidenceSignal") or value.get("confidence_signal"), "neutral")
    try:
        presentation_score = max(0, min(100, int(round(float(value.get("presentationScore", 60))))))
    except (TypeError, ValueError):
        presentation_score = 60
    try:
        score_delta = int(round(float(value.get("scoreDelta", 0))))
    except (TypeError, ValueError):
        score_delta = 0
    score_delta = max(-3, min(3, score_delta))
    try:
        round_no = int(value.get("round") or 0)
    except (TypeError, ValueError):
        round_no = 0
    timestamp = _clean_text(value.get("timestamp") or value.get("time") or value.get("created_at"))
    if not analysis and not suggestions:
        return None
    return {
        "success": bool(value.get("success", True)),
        "analysis": analysis,
        "suggestions": suggestions,
        "confidence": confidence,
        "confidenceSignal": confidence_signal,
        "presentationScore": presentation_score,
        "scoreDelta": score_delta,
        "round": round_no,
        "time": timestamp,
        "timestamp": timestamp,
    }


def _video_delta_from_frames(session: Dict[str, Any]) -> int:
    analyses = [
        item
        for item in session.get("frameAnalyses") or []
        if isinstance(item, dict) and item.get("success", True)
    ]
    delta = sum(int(item.get("scoreDelta") or 0) for item in analyses)
    return max(-5, min(5, delta))


def _video_summary_for_session(session: Dict[str, Any]) -> str:
    enabled = bool(session.get("videoAnalysisEnabled"))
    analyses = [
        item
        for item in session.get("frameAnalyses") or []
        if isinstance(item, dict) and item.get("success", True)
    ]
    if not enabled:
        return "本次未启用摄像头分析，评分仅基于文字回答。"
    if not analyses:
        return "本次未获得有效视频分析结果，评分未加入视频表现因素。"
    delta = _video_delta_from_frames(session)
    latest = analyses[-1]
    observation = _clean_text(latest.get("analysis"), "候选人的面试画面状态较为稳定。")
    if delta > 0:
        trend = f"整体表现对面试表达形成轻微加分，视频辅助加分 {delta} 分。"
    elif delta < 0:
        trend = f"画面状态对表达观感有轻微扣分，视频辅助扣分 {abs(delta)} 分。"
    else:
        trend = "视频表现整体中性，未对最终评分产生加减分。"
    return f"{observation}{trend}"


def _apply_video_score_delta(text_score: int, session: Dict[str, Any], end_type: str = "") -> int:
    delta = _video_delta_from_frames(session) if session.get("videoAnalysisEnabled") else 0
    score = max(0, min(100, int(text_score) + delta))
    if int(text_score) <= 0:
        score = min(score, 5)
    elif int(text_score) <= 10:
        score = min(score, 10)
    if session.get("effectiveAnswerCount", 0) <= 0 and _total_answer_count(session) > 0:
        score = min(score, 10)
    if end_type == "auto_low_performance":
        score = min(score, 10)
    if end_type == "auto_role_mismatch":
        score = min(score, 15)
    return max(0, min(100, score))


def _store_frame_analysis(session: Dict[str, Any], frame_analysis: Dict[str, Any], round_no: Optional[int] = None) -> Dict[str, Any]:
    normalized = _normalize_frame_analysis_payload({**frame_analysis, "round": round_no or frame_analysis.get("round") or session.get("currentRound", 0)})
    if not normalized:
        return {}
    if not normalized.get("time"):
        normalized["time"] = datetime.now().strftime("%H:%M:%S")
        normalized["timestamp"] = _now_iso()
    target_round = int(normalized.get("round") or session.get("currentRound") or 0)
    normalized["round"] = target_round
    analyses = [
        item
        for item in session.get("frameAnalyses") or []
        if not (isinstance(item, dict) and int(item.get("round") or 0) == target_round and item.get("success", True))
    ]
    analyses.append(normalized)
    session["frameAnalyses"] = analyses[-8:]
    session["latestFrameAnalysis"] = normalized
    session["lastFrameAnalysis"] = normalized
    session["videoScoreDelta"] = _video_delta_from_frames(session)
    session["videoScoreAdjustments"] = [int(item.get("scoreDelta") or 0) for item in session["frameAnalyses"] if isinstance(item, dict)]
    session["videoSummary"] = _video_summary_for_session(session)
    return normalized


def _merge_covered_skills(session: Dict[str, Any], skills: Any) -> None:
    existing = set(session.get("coveredSkills") or [])
    existing.update(_normalize_skills(skills, _profile_for_session(session)))
    session["coveredSkills"] = sorted(existing)


def _session_history(session: Dict[str, Any]) -> List[Dict[str, str]]:
    questions = session.get("questions") or []
    answers = session.get("answers") or []
    history: List[Dict[str, str]] = []
    for index, answer in enumerate(answers):
        if index < len(questions):
            question = _clean_text(questions[index])
            if question:
                history.append({"role": "interviewer", "content": question})
        content = _clean_text(answer.get("content") if isinstance(answer, dict) else answer)
        if content:
            history.append({"role": "candidate", "content": content})
    return history


def _session_context(session: Dict[str, Any], round_no: Optional[int] = None) -> Dict[str, Any]:
    profile = _profile_for_session(session)
    return {
        "sessionId": session.get("id"),
        "category": session.get("category"),
        "categoryKey": session.get("categoryKey"),
        "position": session.get("position"),
        "positionKey": session.get("positionKey"),
        "direction": session.get("direction") or session.get("topic"),
        "directionKey": session.get("directionKey"),
        "topic": session.get("topic"),
        "difficulty": session.get("difficulty"),
        "difficultyLabel": session.get("difficultyLabel") or difficulty_label(session.get("difficulty")),
        "profile": {
            "positionKey": profile.get("positionKey"),
            "label": profile.get("label"),
            "coreSkills": list(profile.get("coreSkills") or []),
            "basicQuestions": list(profile.get("basicQuestions") or []),
            "strongAnswerSignals": list(profile.get("strongAnswerSignals") or []),
            "weakAnswerSignals": list(profile.get("weakAnswerSignals") or []),
            "projectQuestionTemplate": profile.get("projectQuestionTemplate", ""),
            "scoringHints": profile.get("scoringHints", ""),
        },
        "round": round_no or session.get("current_index", 0) + 1,
        "history": _session_history(session),
        "answers": list(session.get("answers") or []),
        "scores": list(session.get("scores") or []),
        "answerScores": list(session.get("answerScores") or session.get("scores") or []),
        "coveredSkills": list(session.get("coveredSkills") or []),
        "videoAnalysisEnabled": bool(session.get("videoAnalysisEnabled")),
        "frameAnalysis": session.get("latestFrameAnalysis") or session.get("lastFrameAnalysis"),
        "frameAnalyses": list(session.get("frameAnalyses") or []),
        "latestFrameAnalysis": session.get("latestFrameAnalysis") or session.get("lastFrameAnalysis"),
        "videoScoreDelta": session.get("videoScoreDelta", 0),
        "videoSummary": session.get("videoSummary", ""),
        "sessionStats": {
            "totalAnswerCount": session.get("totalAnswerCount", len(session.get("answers") or [])),
            "currentRound": session.get("currentRound", len(session.get("answers") or [])),
            "maxRounds": session.get("maxRounds", DEFAULT_MAX_ROUNDS),
            "minRounds": session.get("minRounds", DEFAULT_MIN_ROUNDS),
            "maxDurationMinutes": session.get("maxDurationMinutes", DEFAULT_MAX_DURATION_MINUTES),
            "averageScore": session.get("averageScore", 0),
            "lowScoreCount": session.get("lowScoreCount", 0),
            "totalLowScoreCount": session.get("totalLowScoreCount", session.get("lowScoreCount", 0)),
            "consecutiveLowScoreCount": session.get("consecutiveLowScoreCount", 0),
            "consecutiveHighScoreCount": session.get("consecutiveHighScoreCount", 0),
            "dontKnowCount": session.get("dontKnowCount", 0),
            "consecutiveDontKnowCount": session.get("consecutiveDontKnowCount", 0),
            "irrelevantCount": session.get("irrelevantCount", 0),
            "refuseCount": session.get("refuseCount", 0),
            "consecutiveRefuseCount": session.get("consecutiveRefuseCount", 0),
            "nonsenseCount": session.get("nonsenseCount", 0),
            "consecutiveNonsenseCount": session.get("consecutiveNonsenseCount", 0),
            "tooShortCount": session.get("tooShortCount", 0),
            "endRequestCount": session.get("endRequestCount", 0),
            "consecutiveEndRequestCount": session.get("consecutiveEndRequestCount", 0),
            "effectiveAnswerCount": session.get("effectiveAnswerCount", 0),
            "scores": list(session.get("scores") or []),
            "answerScores": list(session.get("answerScores") or session.get("scores") or []),
            "coveredSkills": list(session.get("coveredSkills") or []),
            "endReason": session.get("endReason", ""),
            "endType": session.get("endType", ""),
        },
    }


def _copy_session(session: Dict[str, Any]) -> Dict[str, Any]:
    copied = dict(session)
    copied["questions"] = list(session.get("questions") or [])
    copied["questionPlan"] = list(session.get("questionPlan") or [])
    copied["answers"] = [dict(item) for item in session.get("answers") or []]
    copied["scores"] = list(session.get("scores") or [])
    copied["answerScores"] = list(session.get("answerScores") or session.get("scores") or [])
    copied["answerTypes"] = list(session.get("answerTypes") or [])
    copied["history"] = [dict(item) for item in session.get("history") or []]
    copied["coveredSkills"] = list(session.get("coveredSkills") or [])
    copied["frameAnalyses"] = [dict(item) for item in session.get("frameAnalyses") or [] if isinstance(item, dict)]
    if isinstance(session.get("latestFrameAnalysis"), dict):
        copied["latestFrameAnalysis"] = dict(session.get("latestFrameAnalysis") or {})
    if isinstance(session.get("lastFrameAnalysis"), dict):
        copied["lastFrameAnalysis"] = dict(session.get("lastFrameAnalysis") or {})
    copied["videoAnalysisEnabled"] = bool(session.get("videoAnalysisEnabled"))
    copied["videoScoreAdjustments"] = list(session.get("videoScoreAdjustments") or [])
    copied["videoScoreDelta"] = int(session.get("videoScoreDelta") or 0)
    copied["videoSummary"] = session.get("videoSummary", "")
    return copied


def _fallback_question_for_answer_type(
    answer_type: str,
    default_question: str,
    profile: Optional[Dict[str, Any]] = None,
    user_answer: str = "",
) -> str:
    profile = profile or get_interview_profile(DEFAULT_POSITION_KEY)
    has_evidence = _has_answer_evidence_for_project_followup(user_answer)
    followups = profile.get("followupTemplates") or {}
    followup_key = {
        "strong_answer": "strong",
        "normal_answer": "normal",
        "weak_answer": "weak",
        "vague_answer": "vague",
    }.get(answer_type)
    if followup_key and has_evidence:
        return _clean_text(followups.get(followup_key), _clean_text(profile.get("projectQuestionTemplate"), default_question))
    if answer_type in {"weak_answer", "vague_answer"} and not has_evidence:
        return _basic_specific_followup(profile, default_question)
    fallback_questions = {
        "no_experience": _basic_question(profile, 0, default_question),
        "dont_know": _basic_question(profile, 1, default_question),
        "irrelevant_answer": _basic_question(profile, 0, default_question),
        "negative_answer": _basic_question(profile, 0, default_question),
        "refuse_answer": f"这个问题需要继续确认一下岗位基础。{_basic_question(profile, 0, default_question)}",
        "end_request": _basic_question(profile, 0, default_question),
        "nonsense_answer": _basic_question(profile, 0, default_question),
        "too_short": _basic_question(profile, 0, default_question),
        "vague_answer": "你刚才的回答还比较概括。请你补充一个具体例子，说明你接触过的实验或技术点是什么。",
        "weak_answer": "你刚才提到了一些相关内容，请再具体说一下这个实验或技术点的一个具体步骤。",
    }
    return fallback_questions.get(answer_type, default_question)


def _rescue_question_for_session(session: Dict[str, Any], answer_type: str, default_question: str) -> str:
    profile = _profile_for_session(session)
    low_count = session.get("consecutiveLowScoreCount", 0)
    answers = session.get("answers") or []
    last_answer = _clean_text(answers[-1].get("content") if answers and isinstance(answers[-1], dict) else "")
    if answer_type in {"strong_answer", "normal_answer", "weak_answer", "vague_answer"}:
        return _fallback_question_for_answer_type(answer_type, default_question, profile, user_answer=last_answer)
    if answer_type == "refuse_answer":
        return f"面试需要继续确认基础能力，我们先换一个更基础的问题。{_basic_question(profile, 0, default_question)}"
    if answer_type == "end_request":
        return f"可以理解，我们再用一个很基础的问题快速确认一下。{_basic_question(profile, 0, default_question)}"
    if low_count <= 1:
        return _basic_question(profile, 0, default_question)
    if low_count == 2:
        return _basic_question(profile, 1, default_question)
    return _fallback_question_for_answer_type(answer_type, default_question, profile, user_answer=last_answer)


def _update_session_state_for_answer(session: Dict[str, Any], answer_type: str, answer_score: int) -> None:
    session["totalAnswerCount"] = _total_answer_count(session)
    session["currentRound"] = session["totalAnswerCount"]
    session.setdefault("scores", []).append(answer_score)
    session.setdefault("answerScores", []).append(answer_score)
    session.setdefault("answerTypes", []).append(answer_type)
    scores = session.get("answerScores") or session.get("scores") or []
    session["averageScore"] = round(sum(scores) / max(len(scores), 1), 1)
    _merge_covered_skills(
        session,
        _detect_covered_skills((session.get("answers") or [{}])[-1].get("content", ""), _profile_for_session(session)),
    )

    if _is_low_answer(answer_score):
        session["lowScoreCount"] = session.get("lowScoreCount", 0) + 1
        session["totalLowScoreCount"] = session.get("totalLowScoreCount", 0) + 1
        session["consecutiveLowScoreCount"] = session.get("consecutiveLowScoreCount", 0) + 1
    else:
        session["consecutiveLowScoreCount"] = 0

    if answer_score >= HIGH_SCORE_THRESHOLD:
        session["consecutiveHighScoreCount"] = session.get("consecutiveHighScoreCount", 0) + 1
    else:
        session["consecutiveHighScoreCount"] = 0

    if answer_score <= VERY_LOW_SCORE_THRESHOLD:
        session["veryLowScoreCount"] = session.get("veryLowScoreCount", 0) + 1

    if _is_dont_know_type(answer_type):
        session["dontKnowCount"] = session.get("dontKnowCount", 0) + 1
        session["consecutiveDontKnowCount"] = session.get("consecutiveDontKnowCount", 0) + 1
    else:
        session["consecutiveDontKnowCount"] = 0

    if _is_irrelevant_type(answer_type):
        session["irrelevantCount"] = session.get("irrelevantCount", 0) + 1

    if _is_refuse_type(answer_type):
        session["refuseCount"] = session.get("refuseCount", 0) + 1
        session["consecutiveRefuseCount"] = session.get("consecutiveRefuseCount", 0) + 1
    else:
        session["consecutiveRefuseCount"] = 0

    if _is_nonsense_type(answer_type):
        session["nonsenseCount"] = session.get("nonsenseCount", 0) + 1
        session["consecutiveNonsenseCount"] = session.get("consecutiveNonsenseCount", 0) + 1
        if answer_type == "too_short":
            session["tooShortCount"] = session.get("tooShortCount", 0) + 1
    else:
        session["consecutiveNonsenseCount"] = 0

    if answer_type == "end_request":
        session["endRequestCount"] = session.get("endRequestCount", 0) + 1
        session["consecutiveEndRequestCount"] = session.get("consecutiveEndRequestCount", 0) + 1
    else:
        session["consecutiveEndRequestCount"] = 0

    if _is_effective_answer(answer_score, answer_type):
        session["effectiveAnswerCount"] = session.get("effectiveAnswerCount", 0) + 1


def _score_converged(session: Dict[str, Any]) -> bool:
    scores = session.get("answerScores") or session.get("scores") or []
    if len(scores) < 6:
        return False
    recent = [int(score) for score in scores[-3:]]
    return max(recent) - min(recent) < 10


def _auto_end_decision(session: Dict[str, Any]) -> tuple[str, str]:
    current_round = session.get("currentRound", len(session.get("answers") or []))
    max_rounds = session.get("maxRounds", DEFAULT_MAX_ROUNDS)
    min_rounds = session.get("minRounds", DEFAULT_MIN_ROUNDS)
    average_score = float(session.get("averageScore") or 0)
    elapsed_minutes = _minutes_since(session.get("startTime") or session.get("created_at"))
    max_duration = session.get("maxDurationMinutes", DEFAULT_MAX_DURATION_MINUTES)
    profile = _profile_for_session(session)
    required_coverage_count = min(4, max(1, len(profile.get("coreSkills") or [])))

    if (
        session.get("consecutiveEndRequestCount", 0) >= 2
        or session.get("endRequestCount", 0) >= 2
        or session.get("consecutiveRefuseCount", 0) >= 2
        or session.get("refuseCount", 0) >= 2
    ):
        return "auto_user_unwilling", "候选人多次表达结束意愿，系统已自动结束面试。"
    if session.get("consecutiveLowScoreCount", 0) >= 3:
        return "auto_low_performance", "候选人连续多次无法回答岗位基础问题，系统已自动结束面试。"
    if session.get("totalLowScoreCount", session.get("lowScoreCount", 0)) >= 4:
        return "auto_low_performance", "候选人累计多次低质量回答，系统已自动结束面试。"
    if session.get("consecutiveDontKnowCount", 0) >= 2 and current_round >= min_rounds:
        return "auto_low_performance", "候选人连续多次明确表示不知道或不会，系统已自动结束面试。"
    if session.get("consecutiveNonsenseCount", 0) >= 2 and current_round >= min_rounds:
        return "auto_low_performance", "候选人连续多次给出过短或无意义回答，系统已自动结束面试。"
    if session.get("nonsenseCount", 0) >= 3:
        return "auto_low_performance", "候选人多次给出无意义回答，系统已自动结束面试。"
    if (
        current_round >= min_rounds
        and session.get("effectiveAnswerCount", 0) <= 0
        and session.get("totalLowScoreCount", session.get("lowScoreCount", 0)) >= min_rounds
    ):
        return "auto_role_mismatch", "候选人回答内容长期偏离岗位要求，系统判断岗位匹配度不足，已自动结束面试。"
    if (
        current_round >= min_rounds
        and session.get("veryLowScoreCount", 0) >= 2
        and session.get("irrelevantCount", 0) >= 1
    ):
        return "auto_role_mismatch", "候选人多次跑题或不配合，且未能回答基础补救问题，系统已自动结束面试。"
    if current_round >= max_rounds:
        return "auto_max_rounds", "已达到本次面试最大问答轮次，系统自动生成总结。"
    if elapsed_minutes >= max_duration and current_round >= min_rounds:
        return "auto_time_limit", "本次面试已达到时间上限，系统自动生成总结。"
    if (
        current_round >= min_rounds
        and len(set(session.get("coveredSkills") or [])) >= required_coverage_count
        and average_score >= 60
    ):
        return "auto_coverage_complete", "本次面试已覆盖主要岗位能力点，系统自动生成面试评价。"
    if (
        current_round >= min_rounds
        and session.get("consecutiveHighScoreCount", 0) >= 3
        and average_score >= HIGH_SCORE_THRESHOLD
        and session.get("effectiveAnswerCount", 0) >= 3
    ):
        return "auto_high_confidence_pass", "候选人在连续多轮回答中表现稳定，已获得足够评价依据，系统自动结束面试。"
    if current_round >= 6 and _score_converged(session):
        return "auto_score_converged", "候选人近期回答表现较稳定，评分结果已基本收敛，系统自动结束面试。"
    if session.get("mimoFailureCount", 0) >= 3:
        return "auto_service_fallback", "AI 面试服务暂时不可用，系统已根据已有回答生成阶段性评价。"
    return "", ""


def _final_score_from_session(
    session: Dict[str, Any],
    candidate_score: Optional[int] = None,
    end_type: str = "",
) -> int:
    if _total_answer_count(session) <= 0:
        return 0
    scores = [int(score) for score in session.get("answerScores") or session.get("scores") or [] if isinstance(score, (int, float))]
    average_score = int(round(sum(scores) / len(scores))) if scores else _score_session(session)
    if candidate_score is None:
        base_score = average_score
    else:
        base_score = int(round((int(candidate_score) + average_score) / 2))
    cap = 100
    floor = 0
    if session.get("effectiveAnswerCount", 0) <= 0 and scores:
        cap = min(cap, 10)
        base_score = min(base_score, average_score)
    if (
        session.get("dontKnowCount", 0) >= 2
        or session.get("endRequestCount", 0) >= 2
        or session.get("refuseCount", 0) >= 2
        or session.get("nonsenseCount", 0) >= 2
    ):
        cap = min(cap, 10)
    if session.get("consecutiveLowScoreCount", 0) >= 3:
        cap = min(cap, 10)
    elif session.get("totalLowScoreCount", session.get("lowScoreCount", 0)) >= 3:
        cap = min(cap, 15)
    if session.get("totalLowScoreCount", session.get("lowScoreCount", 0)) >= 1 and session.get("effectiveAnswerCount", 0) <= 0:
        cap = min(cap, 30)
    if end_type == "auto_role_mismatch":
        cap = min(cap, 15)
    if end_type == "auto_low_performance":
        cap = min(cap, 10)
    if end_type == "auto_high_confidence_pass":
        floor = 80
        cap = min(cap, 95)
        base_score = max(base_score, average_score)
    elif end_type == "auto_coverage_complete":
        cap = min(cap, 90)
        base_score = max(base_score, min(average_score + 5, 90))
    return max(floor, min(100, min(base_score, cap)))


def _fallback_summary_for_session(session: Dict[str, Any], score: int, end_reason: str) -> str:
    profile = _profile_for_session(session)
    position = _clean_text(session.get("position"), profile.get("label", "当前岗位"))
    core_skills = "、".join(profile.get("coreSkills") or []) or "岗位基础能力"
    if score <= 10:
        return (
            f"{end_reason or '本次面试已结束。'}"
            "候选人未能提供有效的岗位相关技术回答，且多次表示不知道、不会或偏离面试主题。"
            f"当前表现与{position}岗位要求明显不匹配，建议先补齐{core_skills}等基础能力。"
        )
    if score <= 30:
        return (
            f"{end_reason or '本次面试已结束。'}"
            f"候选人的{position}岗位基础和项目表达仍比较薄弱，需要系统复习岗位核心能力，并准备一个可复盘的小项目或案例。"
        )
    return (
        f"{end_reason or '本次面试已结束。'}"
        f"候选人有一定表达，但围绕{position}的关键细节、问题定位过程和结果量化仍需加强。"
    )


def _build_no_answer_summary_response(
    session_id: str,
    session_snapshot: Dict[str, Any],
    *,
    auto_ended: bool = False,
    end_reason: str = "",
    end_type: str = "manual_end_no_answer",
) -> Dict[str, Any]:
    reason = end_reason or "候选人尚未提交任何回答，面试未形成有效评价。"
    return {
        "sessionId": session_id,
        "status": "ended",
        "type": "summary",
        "autoEnded": auto_ended,
        "endType": end_type or "manual_end_no_answer",
        "endReason": reason,
        "source": "system",
        "usedAI": False,
        "fallbackReason": "",
        "score": None,
        "textScore": None,
        "videoAnalysisEnabled": bool(session_snapshot.get("videoAnalysisEnabled")),
        "videoScoreDelta": 0,
        "videoSummary": _video_summary_for_session(session_snapshot),
        "summary": "本次面试尚未完成，候选人没有提交任何有效回答，因此无法生成正式面试评分。建议重新开始面试并至少完成 3 轮问答。",
        "advantages": [],
        "weaknesses": [],
        "suggestions": ["请重新开始面试，并至少完成 3 轮有效问答。"],
        "totalAnswerCount": _total_answer_count(session_snapshot),
        "effectiveAnswerCount": session_snapshot.get("effectiveAnswerCount", 0),
        "answerScores": list(session_snapshot.get("answerScores") or []),
        "frameAnalyses": list(session_snapshot.get("frameAnalyses") or []),
    }


def _build_summary_response(
    session_id: str,
    session_snapshot: Dict[str, Any],
    *,
    auto_ended: bool,
    end_reason: str,
    end_type: str = "",
) -> Dict[str, Any]:
    if _total_answer_count(session_snapshot) <= 0:
        return _build_no_answer_summary_response(
            session_id,
            session_snapshot,
            auto_ended=auto_ended,
            end_reason=end_reason,
            end_type=end_type or "manual_end_no_answer",
        )

    fallback_reason = "generate_interview_summary is unavailable"
    text_score = _final_score_from_session(session_snapshot, end_type=end_type)
    video_score_delta = _video_delta_from_frames(session_snapshot) if session_snapshot.get("videoAnalysisEnabled") else 0
    final_score = _apply_video_score_delta(text_score, session_snapshot, end_type=end_type)
    video_summary = _video_summary_for_session(session_snapshot)
    if generate_interview_summary:
        fallback_reason = ""
        try:
            result = generate_interview_summary(_session_context(session_snapshot))
            model_score = result.get("score")
            text_score = _final_score_from_session(
                session_snapshot,
                model_score if model_score is not None else text_score,
                end_type=end_type,
            )
            video_score_delta = _video_delta_from_frames(session_snapshot) if session_snapshot.get("videoAnalysisEnabled") else 0
            final_score = _apply_video_score_delta(text_score, session_snapshot, end_type=end_type)
            video_summary = _video_summary_for_session(session_snapshot)
            _log_runtime_event("end_model_success", source="model", autoEnded=auto_ended, endType=end_type, score=final_score, textScore=text_score, videoScoreDelta=video_score_delta)
            return {
                "sessionId": session_id,
                "status": "ended",
                "type": "summary",
                "autoEnded": auto_ended,
                "endType": end_type,
                "endReason": end_reason,
                "source": "model",
                "usedAI": True,
                "fallbackReason": "",
                "score": final_score,
                "textScore": text_score,
                "videoAnalysisEnabled": bool(session_snapshot.get("videoAnalysisEnabled")),
                "videoScoreDelta": video_score_delta,
                "videoSummary": video_summary,
                "summary": _clean_text(result.get("content") or result.get("summary"), _fallback_summary_for_session(session_snapshot, final_score, end_reason)),
                "advantages": result.get("advantages", []),
                "weaknesses": result.get("weaknesses", []),
                "suggestions": result.get("suggestions", _suggestions_for_score(final_score, session_snapshot)),
                "totalAnswerCount": _total_answer_count(session_snapshot),
                "effectiveAnswerCount": session_snapshot.get("effectiveAnswerCount", 0),
                "answerScores": list(session_snapshot.get("answerScores") or []),
                "frameAnalyses": list(session_snapshot.get("frameAnalyses") or []),
            }
        except Exception as exc:
            fallback_reason = _safe_fallback_reason(exc)
            _log_runtime_event("end_fallback", source="local-fallback", autoEnded=auto_ended, endType=end_type, reason=fallback_reason)
    else:
        _log_runtime_event("end_fallback", source="local-fallback", autoEnded=auto_ended, endType=end_type, reason=fallback_reason)

    text_score = _final_score_from_session(session_snapshot, text_score, end_type=end_type)
    video_score_delta = _video_delta_from_frames(session_snapshot) if session_snapshot.get("videoAnalysisEnabled") else 0
    final_score = _apply_video_score_delta(text_score, session_snapshot, end_type=end_type)
    return {
        "sessionId": session_id,
        "status": "ended",
        "type": "summary",
        "autoEnded": auto_ended,
        "endType": end_type,
        "endReason": end_reason,
        "source": "local-fallback",
        "usedAI": False,
        "fallbackReason": fallback_reason,
        "score": final_score,
        "textScore": text_score,
        "videoAnalysisEnabled": bool(session_snapshot.get("videoAnalysisEnabled")),
        "videoScoreDelta": video_score_delta,
        "videoSummary": _video_summary_for_session(session_snapshot),
        "summary": _fallback_summary_for_session(session_snapshot, final_score, end_reason),
        "advantages": [],
        "weaknesses": [],
        "suggestions": _suggestions_for_score(final_score, session_snapshot),
        "totalAnswerCount": _total_answer_count(session_snapshot),
        "effectiveAnswerCount": session_snapshot.get("effectiveAnswerCount", 0),
        "answerScores": list(session_snapshot.get("answerScores") or []),
        "frameAnalyses": list(session_snapshot.get("frameAnalyses") or []),
    }


def _build_questions(position: str, topic: str, difficulty: str, profile: Optional[Dict[str, Any]] = None) -> List[str]:
    profile = profile or get_interview_profile(DEFAULT_POSITION_KEY)
    focus = topic or "岗位基础、项目经验和问题分析能力"
    role = position or _clean_text(profile.get("label"), "当前岗位")
    level = difficulty or "中等"
    return [
        _default_project_question(role, focus, profile),
        f"针对你刚才提到的经历，请说明其中一个关键难点，以及你是如何分析和解决的。",
        f"现在聚焦到{focus}。如果实际推进中出现一个反复发生的问题，你会按照什么步骤分析和处理？",
        f"最后一个问题：在{level}难度的真实任务中，你如何平衡交付质量、协作效率和时间要求？",
    ]


def _score_session(session: Dict[str, Any]) -> int:
    answers = session.get("answers", [])
    if not answers:
        return 0
    if classify_answer_type:
        profile = _profile_for_session(session)
        answer_types = [
            classify_answer(_clean_text(item.get("content") if isinstance(item, dict) else item), profile=profile)
            for item in answers
        ]
        weak_types = {
            "weak_answer",
            "vague_answer",
            "too_short",
            "no_experience",
            "dont_know",
            "irrelevant_answer",
            "negative_answer",
            "refuse_answer",
            "end_request",
            "nonsense_answer",
        }
        if answer_types and all(answer_type in weak_types for answer_type in answer_types):
            return 25
    avg_len = sum(len(item.get("content", "")) for item in answers) / max(len(answers), 1)
    coverage_bonus = min(len(answers) * 8, 32)
    detail_bonus = min(int(avg_len / 8), 18)
    score = max(50, min(92, 48 + coverage_bonus + detail_bonus))
    if classify_answer_type:
        if any(answer_type in {"no_experience", "dont_know", "irrelevant_answer", "negative_answer", "refuse_answer", "end_request", "nonsense_answer", "too_short"} for answer_type in answer_types):
            score = min(score, 60)
    return score


def _suggestions_for_score(score: int, session: Optional[Dict[str, Any]] = None) -> List[str]:
    profile = _profile_for_session(session or {}) if session else get_interview_profile(DEFAULT_POSITION_KEY)
    position = _clean_text((session or {}).get("position"), profile.get("label", "当前岗位"))
    core_skills = "、".join((profile.get("coreSkills") or [])[:4]) or "岗位基础能力"
    if score >= 85:
        return [
            "继续保持项目表达中的结构化描述，突出指标、约束和结果。",
            f"准备 1-2 个更深入的{position}案例，方便应对追问。",
        ]
    if score >= 70:
        return [
            "回答时建议按 背景-任务-行动-结果 的顺序组织，减少跳跃。",
            f"补充{position}相关关键细节，尤其是你的判断依据、处理步骤和取舍。",
            "为每个项目准备可量化结果，例如延迟、稳定性、资源占用或通过率。",
        ]
    return [
        f"先准备一个完整{position}案例复盘，覆盖背景、职责、行动、结果和反思。",
        f"强化{core_skills}等岗位基础知识的口头表达。",
        "回答追问时先给结论，再补充依据和排查步骤。",
    ]


def start_interview_session(user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    category_key = _clean_text(payload.get("categoryKey") or payload.get("category_key"))
    category = _clean_text(payload.get("category"))
    position_key = _clean_text(payload.get("positionKey") or payload.get("position_key"), DEFAULT_POSITION_KEY)
    position = _clean_text(payload.get("position"))
    profile = get_interview_profile(position_key, position)
    position_key = _clean_text(profile.get("positionKey"), position_key)
    category_key = _clean_text(category_key, profile.get("categoryKey", "mcu_development"))
    category = _clean_text(category, profile.get("category", "单片机与 MCU 开发"))
    position = _clean_text(position, profile.get("label", "STM32 开发工程师"))
    direction_key = _clean_text(payload.get("directionKey") or payload.get("direction_key"))
    direction = _clean_text(payload.get("direction") or payload.get("topic"), "GPIO / 中断 / UART")
    topic = direction
    difficulty = difficulty_value(payload.get("difficulty") or payload.get("difficultyKey") or payload.get("difficulty_key"))
    difficulty_display = difficulty_label(difficulty, payload.get("difficultyLabel") or payload.get("difficulty_label"))
    min_rounds = _int_payload(payload.get("minRounds") or payload.get("min_rounds"), DEFAULT_MIN_ROUNDS)
    max_rounds = _int_payload(payload.get("maxRounds") or payload.get("max_rounds"), DEFAULT_MAX_ROUNDS)
    max_duration_minutes = _int_payload(
        payload.get("maxDurationMinutes") or payload.get("max_duration_minutes"),
        DEFAULT_MAX_DURATION_MINUTES,
    )
    video_analysis_enabled = _bool_payload(
        payload.get("videoAnalysisEnabled", payload.get("video_analysis_enabled", payload.get("cameraEnabled", payload.get("camera_enabled")))),
        False,
    )
    if max_rounds < min_rounds:
        max_rounds = min_rounds
    question_plan = _build_questions(position, topic, difficulty_display, profile)
    question_source = "local-fallback"
    used_mimo = False
    mimo_error = "generate_interview_question is unavailable"
    if generate_interview_question:
        mimo_error = ""
        try:
            result = generate_interview_question(
                {
                    "category": category,
                    "categoryKey": category_key,
                    "position": position,
                    "positionKey": position_key,
                    "direction": direction,
                    "directionKey": direction_key,
                    "topic": topic,
                    "difficulty": difficulty,
                    "difficultyLabel": difficulty_display,
                    "profile": profile,
                    "round": 1,
                    "history": [],
                }
            )
            question_plan[0] = _clean_text(result.get("content"), question_plan[0])
            question_source = "model"
            used_mimo = True
            _log_runtime_event("start_model_success", source=question_source)
        except Exception as exc:
            mimo_error = _safe_fallback_reason(exc)
            _log_runtime_event("start_fallback", source="local-fallback", reason=mimo_error)
    else:
        _log_runtime_event("start_fallback", source="local-fallback", reason=mimo_error)
    session_id = secrets.token_urlsafe(18)
    session = {
        "id": session_id,
        "user_id": user_id,
        "category": category,
        "categoryKey": category_key,
        "position": position,
        "positionKey": position_key,
        "direction": direction,
        "directionKey": direction_key,
        "topic": topic,
        "difficulty": difficulty,
        "difficultyLabel": difficulty_display,
        "profile": profile,
        "questions": [question_plan[0]],
        "questionPlan": question_plan,
        "answers": [],
        "history": [],
        "frameAnalyses": [],
        "latestFrameAnalysis": None,
        "lastFrameAnalysis": None,
        "videoAnalysisEnabled": video_analysis_enabled,
        "videoScoreAdjustments": [],
        "videoScoreDelta": 0,
        "videoSummary": "本次未启用摄像头分析，评分仅基于文字回答。" if not video_analysis_enabled else "",
        "scores": [],
        "answerScores": [],
        "answerTypes": [],
        "coveredSkills": [],
        "totalAnswerCount": 0,
        "averageScore": 0,
        "current_index": 0,
        "currentRound": 0,
        "maxRounds": max_rounds,
        "minRounds": min_rounds,
        "startTime": _now_iso(),
        "maxDurationMinutes": max_duration_minutes,
        "lowScoreThreshold": LOW_SCORE_THRESHOLD,
        "veryLowScoreThreshold": VERY_LOW_SCORE_THRESHOLD,
        "lowScoreCount": 0,
        "totalLowScoreCount": 0,
        "consecutiveLowScoreCount": 0,
        "consecutiveHighScoreCount": 0,
        "veryLowScoreCount": 0,
        "dontKnowCount": 0,
        "consecutiveDontKnowCount": 0,
        "irrelevantCount": 0,
        "refuseCount": 0,
        "consecutiveRefuseCount": 0,
        "nonsenseCount": 0,
        "consecutiveNonsenseCount": 0,
        "tooShortCount": 0,
        "endRequestCount": 0,
        "consecutiveEndRequestCount": 0,
        "effectiveAnswerCount": 0,
        "endReason": "",
        "endType": "",
        "autoEnded": False,
        "mimoFailureCount": 0 if used_mimo else 1,
        "status": "asking",
        "question_source": question_source,
        "used_mimo": used_mimo,
        "last_mimo_error": mimo_error,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    with _SESSION_LOCK:
        _SESSIONS[session_id] = session
    return {
        "sessionId": session_id,
        "status": "asking",
        "type": "question",
        "category": category,
        "categoryKey": category_key,
        "position": position,
        "positionKey": position_key,
        "direction": direction,
        "directionKey": direction_key,
        "difficulty": difficulty,
        "difficultyLabel": difficulty_display,
        "videoAnalysisEnabled": video_analysis_enabled,
        "cameraEnabled": video_analysis_enabled,
        "source": question_source,
        "usedAI": used_mimo,
        "fallbackReason": "" if used_mimo else mimo_error,
        "round": 1,
        "content": question_plan[0],
        "message": {
            "role": "interviewer",
            "content": question_plan[0],
        },
    }


def handle_interview_message(user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    session_id = _clean_text(payload.get("sessionId"))
    answer = _clean_text(payload.get("answer"))
    frame_analysis = payload.get("frameAnalysis") or payload.get("frame_analysis")
    if not session_id:
        return {"code": 400, "msg": "缺少 sessionId"}
    if not answer:
        return {"code": 400, "msg": "回答不能为空"}

    with _SESSION_LOCK:
        session = _SESSIONS.get(session_id)
        if not session or session.get("user_id") != user_id:
            return {"code": 404, "msg": "面试会话不存在或已过期"}
        if session.get("status") == "ended":
            return {"code": 409, "msg": "面试已结束"}

        answer_eval = _score_answer(answer, _profile_for_session(session))
        answer_type = answer_eval["answerType"]
        answer_score = answer_eval["answerScore"]
        normalized_frame_analysis = _normalize_frame_analysis_payload(frame_analysis)
        answer_entry = {
            "round": len(session["answers"]) + 1,
            "content": answer,
            "answerType": answer_type,
            "answerScore": answer_score,
            "created_at": _now_iso(),
        }
        if normalized_frame_analysis and session.get("videoAnalysisEnabled"):
            normalized_frame_analysis = _store_frame_analysis(session, normalized_frame_analysis, round_no=answer_entry["round"])
            answer_entry["frameAnalysis"] = normalized_frame_analysis
        session["answers"].append(answer_entry)
        _update_session_state_for_answer(session, answer_type, answer_score)
        next_index = len(session["questions"])
        session["current_index"] = next_index
        session["updated_at"] = _now_iso()
        question_plan = session.get("questionPlan") or _build_questions(
            session.get("position", ""),
            session.get("topic", ""),
            session.get("difficultyLabel", ""),
            _profile_for_session(session),
        )
        plan_index = min(next_index, len(question_plan) - 1)
        question = question_plan[plan_index]
        is_final_question = next_index + 1 >= session.get("maxRounds", DEFAULT_MAX_ROUNDS)
        fallback_question = _rescue_question_for_session(session, answer_type, question)
        question = fallback_question
        auto_end_type, auto_end_reason = _auto_end_decision(session)
        if auto_end_reason:
            session["status"] = "ended"
            session["endType"] = auto_end_type
            session["endReason"] = auto_end_reason
            session["updated_at"] = _now_iso()
        session_snapshot = _copy_session(session)

    if auto_end_reason:
        _log_runtime_event(
            "message_auto_end",
            answerType=answer_type,
            answerScore=answer_score,
            round=session_snapshot.get("currentRound"),
            endType=auto_end_type,
            reason=auto_end_reason,
        )
        return _build_summary_response(
            session_id,
            session_snapshot,
            auto_ended=True,
            end_reason=auto_end_reason,
            end_type=auto_end_type,
        )

    question_source = "local-fallback"
    used_mimo = False
    mimo_error = "generate_interview_followup is unavailable"
    mimo_should_end = False
    mimo_end_reason = ""
    model_covered_skills: List[str] = []
    if generate_interview_followup:
        mimo_error = ""
        try:
            context = _session_context(session_snapshot, round_no=next_index + 1)
            result = generate_interview_followup(context, answer, frame_analysis=normalized_frame_analysis or frame_analysis)
            question = _clean_text(result.get("content"), fallback_question)
            answer_type = _clean_text(result.get("answerType") or result.get("answer_type"), answer_type)
            model_covered_skills = _normalize_skills(
                result.get("coveredSkills") or result.get("covered_skills"),
                _profile_for_session(session_snapshot),
            )
            mimo_should_end = bool(result.get("shouldEnd") or result.get("should_end"))
            mimo_end_reason = _clean_text(result.get("endReason") or result.get("end_reason"))
            try:
                answer_score = min(answer_score, max(0, min(100, int(result.get("answerScore", answer_score)))))
            except (TypeError, ValueError):
                pass
            question_source = "model"
            used_mimo = True
            _log_runtime_event(
                "message_model_success",
                source=question_source,
                answerType=answer_type,
                answerScore=answer_score,
                round=next_index + 1,
            )
        except Exception as exc:
            question = fallback_question
            mimo_error = _safe_fallback_reason(exc)
            _log_runtime_event("message_fallback", source="local-fallback", answerType=answer_type, answerScore=answer_score, round=next_index + 1, reason=mimo_error)
            with _SESSION_LOCK:
                session = _SESSIONS.get(session_id)
                if session and session.get("user_id") == user_id and session.get("status") != "ended":
                    session["mimoFailureCount"] = session.get("mimoFailureCount", 0) + 1
                    if session["mimoFailureCount"] >= 3:
                        service_reason = "AI 面试服务暂时不可用，系统已根据已有回答生成阶段性评价。"
                        session["status"] = "ended"
                        session["autoEnded"] = True
                        session["endType"] = "auto_service_fallback"
                        session["endReason"] = service_reason
                        session["updated_at"] = _now_iso()
                        session_snapshot = _copy_session(session)
                        return _build_summary_response(
                            session_id,
                            session_snapshot,
                            auto_ended=True,
                            end_reason=service_reason,
                            end_type="auto_service_fallback",
                        )
    else:
        _log_runtime_event("message_fallback", source="local-fallback", answerType=answer_type, answerScore=answer_score, round=next_index + 1, reason=mimo_error)

    question_deduplicated = _is_repeated_question(question, list(session_snapshot.get("questions") or []))
    if question_deduplicated:
        repeated_question = question
        question = _distinct_question_for_session(session_snapshot, fallback_question)
        question_source = f"{question_source}-deduplicated"
        _log_runtime_event(
            "message_question_deduplicated",
            round=next_index + 1,
            repeatedQuestion=repeated_question,
            replacementQuestion=question,
        )

    if mimo_should_end and (
        session_snapshot.get("currentRound", 0) >= session_snapshot.get("minRounds", DEFAULT_MIN_ROUNDS)
        or session_snapshot.get("endRequestCount", 0) >= 2
    ):
        end_reason = mimo_end_reason or "讯飞模型建议结束，且后端状态机已确认当前证据足够。"
        suggested_end_type = "auto_role_mismatch" if float(session_snapshot.get("averageScore") or 0) < 40 else "auto_score_converged"
        with _SESSION_LOCK:
            session = _SESSIONS.get(session_id)
            if session and session.get("user_id") == user_id and session.get("status") != "ended":
                session["status"] = "ended"
                session["endType"] = suggested_end_type
                session["endReason"] = end_reason
                session["updated_at"] = _now_iso()
                session_snapshot = _copy_session(session)
        _log_runtime_event("message_mimo_suggested_end", answerType=answer_type, answerScore=answer_score, reason=end_reason)
        return _build_summary_response(
            session_id,
            session_snapshot,
            auto_ended=True,
            end_reason=end_reason,
            end_type=suggested_end_type,
        )

    with _SESSION_LOCK:
        session = _SESSIONS.get(session_id)
        if session and session.get("user_id") == user_id and session.get("status") != "ended":
            session["questions"].append(question)
            session["question_source"] = question_source
            session["used_mimo"] = used_mimo
            session["last_answer_type"] = answer_type
            session["last_answer_score"] = answer_score
            _merge_covered_skills(session, model_covered_skills)
            if used_mimo:
                session["mimoFailureCount"] = 0
            session["last_mimo_error"] = mimo_error
            session["updated_at"] = _now_iso()
            session_snapshot = _copy_session(session)

    return {
        "sessionId": session_id,
        "status": "asking",
        "type": "question",
        "source": question_source,
        "usedAI": used_mimo,
        "questionDeduplicated": question_deduplicated,
        "fallbackReason": "" if used_mimo else mimo_error,
        "answerType": answer_type,
        "answerScore": answer_score,
        "shouldEnd": False,
        "autoEnded": False,
        "round": next_index + 1,
        "currentRound": session_snapshot.get("currentRound"),
        "averageScore": session_snapshot.get("averageScore", 0),
        "coveredSkills": list(session_snapshot.get("coveredSkills") or []),
        "content": question,
        "isFinalQuestion": is_final_question,
        "message": {
            "role": "interviewer",
            "content": question,
        },
    }


def get_interview_video_context(user_id: int, payload: Dict[str, Any]) -> tuple[bool, Dict[str, Any], Dict[str, Any]]:
    session_id = _clean_text(payload.get("sessionId"))
    if not session_id:
        return False, {"success": False, "errorCode": "CAMERA_NOT_ENABLED", "error": "缺少面试会话，无法分析关键帧"}, {}
    with _SESSION_LOCK:
        session = _SESSIONS.get(session_id)
        if not session or session.get("user_id") != user_id:
            return False, {"success": False, "errorCode": "SESSION_NOT_FOUND", "error": "面试会话不存在或已过期"}, {}
        if session.get("status") == "ended":
            return False, {"success": False, "errorCode": "CAMERA_NOT_ENABLED", "error": "面试已结束，无法继续分析关键帧"}, {}
        if not session.get("videoAnalysisEnabled"):
            return False, {"success": False, "errorCode": "CAMERA_NOT_ENABLED", "error": "本轮面试未启用摄像头分析"}, {}
        try:
            round_no = int(payload.get("round") or session.get("currentRound") or 1)
        except (TypeError, ValueError):
            round_no = session.get("currentRound") or 1
        if _clean_text(payload.get("reason")) != "manual-test":
            for item in session.get("frameAnalyses") or []:
                if isinstance(item, dict) and item.get("success", True) and int(item.get("round") or 0) == round_no:
                    return False, {"success": True, **item}, {}
        context = _session_context(session, round_no=round_no)
    return True, {}, context


def save_interview_frame_analysis(user_id: int, session_id: str, result: Dict[str, Any], round_no: Optional[int] = None) -> Dict[str, Any]:
    with _SESSION_LOCK:
        session = _SESSIONS.get(_clean_text(session_id))
        if not session or session.get("user_id") != user_id:
            return result
        if not session.get("videoAnalysisEnabled"):
            return result
        saved = _store_frame_analysis(session, result, round_no=round_no)
        session["updated_at"] = _now_iso()
        return {**result, **saved, "success": True}


def end_interview_session(user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    session_id = _clean_text(payload.get("sessionId"))
    if not session_id:
        return {"code": 400, "msg": "缺少 sessionId"}

    with _SESSION_LOCK:
        session = _SESSIONS.get(session_id)
        if not session or session.get("user_id") != user_id:
            return {"code": 404, "msg": "面试会话不存在或已过期"}
        session["status"] = "ended"
        if _total_answer_count(session) <= 0:
            session["endType"] = "manual_end_no_answer"
            session["endReason"] = "候选人尚未提交任何回答，面试未形成有效评价。"
        else:
            session["endType"] = "manual_end"
            session["endReason"] = "用户主动结束面试。"
        session["updated_at"] = _now_iso()
        session_snapshot = _copy_session(session)

    return _build_summary_response(
        session_id,
        session_snapshot,
        auto_ended=False,
        end_reason=session_snapshot.get("endReason", "用户主动结束面试。"),
        end_type=session_snapshot.get("endType", "manual_end"),
    )
