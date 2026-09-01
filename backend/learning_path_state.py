"""Learning-path persistence, evidence, feedback, and assessment state."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime
from urllib.parse import quote, urlencode, urlparse

try:
    import knowledge_growth
    from common import now_iso
    from domain_errors import LearningProfileRequiredError
    from learning_agents import (
        LEARNING_PATH_REQUIRED_RESOURCE_TYPES,
        LEARNING_PATH_RESOURCE_PLAN_VERSION,
        sanitize_learning_path_resource_params,
    )
    from learning_profile_versions import active_profile_for_user
    from mcu_catalog import normalize_mcu_resource_params, normalize_mcu_route
    from question_generator_storage import list_history
except ImportError:  # pragma: no cover - package import fallback
    from . import knowledge_growth
    from .common import now_iso
    from .domain_errors import LearningProfileRequiredError
    from .learning_agents import (
        LEARNING_PATH_REQUIRED_RESOURCE_TYPES,
        LEARNING_PATH_RESOURCE_PLAN_VERSION,
        sanitize_learning_path_resource_params,
    )
    from .learning_profile_versions import active_profile_for_user
    from .mcu_catalog import normalize_mcu_resource_params, normalize_mcu_route
    from .question_generator_storage import list_history


def utc_timestamp() -> str:
    return now_iso()


def json_loads_safe(value, default):
    try:
        return json.loads(value or "")
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def parse_json_safely(value: str, fallback):
    return json_loads_safe(value, fallback)


# Domain constants and functions are mechanically moved below this marker.

DEFAULT_LEARNING_PATH_WEEKS = [
    ("week-1-embedded-foundation", "第一周", "嵌入式基础与开发环境", "完成开发环境搭建并理解最小系统与程序运行流程", "current", "cpu", "green", 150),
    ("week-2-gpio-practice", "第二周", "GPIO 输入输出实操", "围绕 GPIO 建立配置思路并完成可运行实验", "locked", "book-open", "green", 180),
    ("week-3-uart-debug", "第三周", "串口通信与调试链路", "跑通串口收发、日志输出和调试定位流程", "locked", "clipboard-check", "green", 210),
    ("week-4-timer-interrupt", "第四周", "定时器 PWM 与中断响应", "完成定时器、PWM 和中断的案例跟做与专项测评", "locked", "target", "green", 240),
    ("week-5-sensor-project", "第五周", "传感器采集与项目案例", "把传感器采集、数据处理和小项目联调结合起来", "locked", "layers", "green", 270),
    ("week-6-integrated-training", "第六周", "综合项目实训与复盘", "完成综合任务、整理证据并更新下一轮学习重点", "locked", "rocket", "green", 320),
]

LEGACY_LEARNING_PATH_STAGE_IDS = {
    "profile-diagnosis",
    "courseware-recommend",
    "practice-recommend",
    "assessment-recommend",
    "case-recommend",
    "project-recommend",
}


DEFAULT_STAGE_NODE_COORDS = [
    {"x": 112, "y": 420, "popX": 180, "popY": 250},
    {"x": 402, "y": 292, "popX": 402, "popY": 122},
    {"x": 646, "y": 316, "popX": 646, "popY": 270},
    {"x": 942, "y": 369, "popX": 942, "popY": 198},
    {"x": 1188, "y": 284, "popX": 1188, "popY": 114},
    {"x": 1398, "y": 185, "popX": 1260, "popY": 112},
]

DEFAULT_STAGE_NODE_BLUEPRINTS = [
    ("目标拆解", "查找学习视频", "/personalized-resources/video-search", "通过导学视频明确本周主题、学习目标和验收标准。"),
    ("概念建模", "生成导图", "/personalized-resources/mind-map", "围绕本周主题整理知识结构图，标出关键概念、前置知识和易错点。"),
    ("示例跟做", "生成学习课件", "/personalized-resources/ppt", "通过最小可运行示例理解配置流程、关键代码和运行现象。"),
    ("实操验证", "进入单片机实验", "/personalized-resources/mcu-simulator", "在开发板或模拟器完成一个小实验，记录代码、接线和现象。"),
    ("专项测评", "生成练习题单", "/personalized-resources/question-bank", "完成针对性题目或代码改错题，检查本周知识是否真正掌握。"),
    ("复盘迭代", "生成复盘导图", "/personalized-resources/mind-map", "通过复盘导图整理错因、实验证据和下一周要继续追踪的问题。"),
]

DEFAULT_STAGE_NODE_RESOURCE_TYPES = {
    "目标拆解": ["video"],
    "概念建模": ["mindmap", "ppt"],
    "示例跟做": ["ppt", "video"],
    "实操验证": ["mcu", "video"],
    "专项测评": ["question-bank"],
    "复盘迭代": ["mindmap", "ppt"],
}

LEARNING_PATH_REQUIRED_TASK_RESOURCE_TYPES = LEARNING_PATH_REQUIRED_RESOURCE_TYPES
LEARNING_PATH_DEFAULT_RESOURCE_TYPES = list(LEARNING_PATH_REQUIRED_TASK_RESOURCE_TYPES)

LEARNING_PATH_TASK_RESOURCE_ALIASES = {
    "question_bank": "question-bank",
    "quiz": "question-bank",
    "document": "ppt",
    "simulator": "ppt",
    "code": "ppt",
    "mind-map": "mindmap",
    "handout": "ppt",
    "learning-document": "ppt",
    "animated-lesson": "animation",
    "learning-animation": "animation",
    "simulator": "mcu",
    "code": "mcu",
}
LEARNING_PATH_TASK_RESOURCE_ACTIONS = {
    "generated_video": "生成 AI 视频讲解",
    "video": "查找学习视频",
    "animation": "生成动画微课",
    "ppt": "生成学习课件",
    "mindmap": "生成思维导图",
    "question-bank": "生成练习题单",
    "mcu": "进入单片机实验",
}
LEARNING_PATH_RESOURCE_ROUTE_TYPES = {
    "/personalized-resources/video-generator": "generated_video",
    "/personalized-resources/video-search": "video",
    "/personalized-resources/animation": "animation",
    "/personalized-resources/document": "ppt",
    "/personalized-resources/ppt": "ppt",
    "/personalized-resources/mind-map": "mindmap",
    "/personalized-resources/question-bank": "question-bank",
    "/personalized-resources/mcu-simulator": "mcu",
}

def _canonical_learning_path_task_resource(raw_node: dict, node_index: int) -> str:
    candidates = [raw_node.get("resourceType")]
    route_path = urlparse(str(raw_node.get("actionRoute") or "")).path.rstrip("/")
    for prefix, resource_type in LEARNING_PATH_RESOURCE_ROUTE_TYPES.items():
        if route_path == prefix or route_path.startswith(f"{prefix}/"):
            candidates.append(resource_type)
            break
    for candidate in candidates:
        resource_type = str(candidate or "").strip().lower()
        resource_type = LEARNING_PATH_TASK_RESOURCE_ALIASES.get(resource_type, resource_type)
        if resource_type in LEARNING_PATH_TASK_RESOURCE_ACTIONS:
            return resource_type
    task_text = " ".join(
        [
            str(raw_node.get("title") or ""),
            str(raw_node.get("description") or raw_node.get("desc") or ""),
            str(raw_node.get("deliverable") or ""),
        ]
    ).lower()
    semantic_rules = [
        ("mcu", ["实验", "实操", "仿真", "开发板", "烧录", "波形", "接线", "调试"]),
        ("question-bank", ["测评", "题", "错因", "诊断", "考试"]),
        ("animation", ["动画", "动态过程", "时序流程", "状态迁移", "信号流", "可视化"]),
        ("ppt", ["讲义", "文档", "手册", "笔记", "总结"]),
        ("mindmap", ["导图", "建模", "结构", "概念", "复盘"]),
        ("ppt", ["课件", "汇报", "展示", "演示"]),
        ("video", ["视频", "导学", "讲解", "示例", "目标"]),
    ]
    for resource_type, keywords in semantic_rules:
        if any(keyword in task_text for keyword in keywords):
            return resource_type
    return "video"


def _is_legacy_learning_path_document_node(raw_node: dict) -> bool:
    resource_type = str(raw_node.get("resourceType") or "").strip().lower()
    route_path = urlparse(str(raw_node.get("actionRoute") or "")).path.rstrip("/")
    task_route = ""
    if isinstance(raw_node.get("resourceTask"), dict):
        task_route = urlparse(str(raw_node["resourceTask"].get("route") or "")).path.rstrip("/")
    return resource_type in {"document", "handout", "learning-document"} or route_path == "/personalized-resources/document" or task_route == "/personalized-resources/document"


def _migrate_learning_path_document_text(value: object) -> str:
    text = str(value or "")
    for old, new in (
        ("课程讲义", "学习课件"),
        ("学习讲义", "学习课件"),
        ("实验讲义", "实验课件"),
        ("生成讲义", "生成课件"),
        ("讲义", "课件"),
    ):
        text = text.replace(old, new)
    return text


def _learning_path_task_resource_route(
    resource_type: str,
    topic: str,
    stage_id: str,
    node_id: str,
    cache_key: str,
    resource_params: dict | None = None,
) -> str:
    resource_params = resource_params if isinstance(resource_params, dict) else {}
    common = {
        "source": "learning-path",
        "stageId": stage_id,
        "nodeId": node_id,
        "cacheKey": cache_key,
    }
    if resource_type == "generated_video":
        path = "/personalized-resources/video-generator"
        resource_topic = str(resource_params.get("topic") or topic).strip()
        params = {
            "topic": resource_topic,
            "prompt": resource_params.get("prompt") or f"围绕“{resource_topic}”生成面向当前学习阶段的 AI 讲解视频",
            **common,
        }
    elif resource_type == "video":
        path = "/personalized-resources/video-search"
        resource_topic = str(resource_params.get("topic") or topic).strip()
        params = {"keyword": resource_params.get("keyword") or resource_topic, "topic": resource_topic, "autostart": "1", **common}
    elif resource_type == "animation":
        path = "/personalized-resources/animation"
        resource_topic = str(resource_params.get("topic") or topic).strip()
        params = {
            "topic": resource_topic,
            "requirements": resource_params.get("requirements") or resource_params.get("prompt") or f"围绕{topic}生成可播放 H5 动画微课",
            "autostart": "1",
            **common,
        }
    elif resource_type == "ppt":
        path = "/personalized-resources/ppt"
        resource_topic = str(resource_params.get("topic") or topic).strip()
        params = {
            "topic": resource_topic,
            "prompt": resource_params.get("prompt") or resource_params.get("userMessage") or f"围绕{topic}生成本周学习课件",
            "pageCount": resource_params.get("pageCount") or resource_params.get("pages") or 6,
            "autostart": "1",
            **common,
        }
    elif resource_type == "mindmap":
        path = "/personalized-resources/mind-map"
        resource_topic = str(resource_params.get("topic") or topic).strip()
        params = {"topic": resource_topic, "keyword": resource_params.get("keyword") or resource_topic, "autostart": "1", **common}
    elif resource_type == "question-bank":
        path = "/personalized-resources/question-bank"
        params = {
            "module": "generate",
            "course": resource_params.get("course") or resource_params.get("courseName") or "嵌入式系统",
            "chapter": resource_params.get("chapter") or resource_params.get("targetTopic") or topic,
            "count": resource_params.get("count") or resource_params.get("questionCount") or 10,
            "autostart": "1",
            **common,
        }
    else:
        resource_params = normalize_mcu_resource_params(resource_params, topic)
        board = str(resource_params["board"])
        project_id = str(resource_params["projectId"])
        path = f"/personalized-resources/mcu-simulator/{quote(board)}/{quote(project_id)}"
        params = common
    return f"{path}?{urlencode({key: value for key, value in params.items() if value})}"


def _ensure_learning_path_task_resource_coverage(nodes: list[dict], topic: str, stage_id: str) -> list[dict]:
    """Keep every weekly task set covered by the required learner-facing tools."""
    normalized_nodes = [node for node in nodes if isinstance(node, dict)]
    if len(normalized_nodes) < len(LEARNING_PATH_REQUIRED_TASK_RESOURCE_TYPES):
        return normalized_nodes
    required = list(LEARNING_PATH_REQUIRED_TASK_RESOURCE_TYPES)

    def replace_resource(index: int, resource_type: str) -> None:
        node = normalized_nodes[index]
        node_id = str(node.get("id") or index + 1)
        cache_key = re.sub(r"[^a-zA-Z0-9_.:-]+", "-", f"{stage_id}-{node_id}-{resource_type}").strip("-")
        params = sanitize_learning_path_resource_params(resource_type, node.get("resourceParams"), include_runtime=True)
        node.update(
            {
                "resourceType": resource_type,
                "resourceTypes": [resource_type],
                "resourceParams": params,
                "cacheKey": cache_key,
                "actionText": LEARNING_PATH_TASK_RESOURCE_ACTIONS[resource_type],
                "actionRoute": _learning_path_task_resource_route(resource_type, topic, stage_id, node_id, cache_key, params),
                "resourcePrompt": f"根据当前学习画像完成“{node.get('title') or '学习任务'}”并生成对应学习资源。",
                "resourceSelectionReason": "每周六类资源覆盖规则已补齐当前任务。",
                "resourceSelectionSource": "weekly-resource-coverage",
                "resourceTask": {"status": "waiting", "progress": 0},
            }
        )

    counts = {resource_type: 0 for resource_type in required}
    unsupported_indexes: list[int] = []
    for index, node in enumerate(normalized_nodes):
        resource_type = str(node.get("resourceType") or "")
        if resource_type in counts:
            counts[resource_type] += 1
        else:
            unsupported_indexes.append(index)

    missing = [resource_type for resource_type in required if counts[resource_type] == 0]
    for resource_type in missing:
        if unsupported_indexes:
            index = unsupported_indexes.pop(0)
        else:
            index = next(
                (
                    candidate
                    for candidate in range(len(normalized_nodes) - 1, -1, -1)
                    if str(normalized_nodes[candidate].get("resourceType") or "") in counts
                    and counts[str(normalized_nodes[candidate].get("resourceType") or "")] > 1
                ),
                -1,
            )
        if index < 0:
            break
        previous_type = str(normalized_nodes[index].get("resourceType") or "")
        if previous_type in counts:
            counts[previous_type] -= 1
        replace_resource(index, resource_type)
        counts[resource_type] += 1

    for index in unsupported_indexes:
        replace_resource(index, required[index % len(required)])
    return normalized_nodes

def build_default_stage_nodes(week_label: str, week_title: str = "") -> list[dict]:
    topic = week_title or "嵌入式学习任务"
    nodes = []
    for index, (title, action_text, action_route, description) in enumerate(DEFAULT_STAGE_NODE_BLUEPRINTS, start=1):
        coords = DEFAULT_STAGE_NODE_COORDS[index - 1]
        node_id = str(index).zfill(2)
        resource_type = _canonical_learning_path_task_resource(
            {"title": title, "description": description},
            index,
        )
        cache_key = f"default-{node_id}-{resource_type}"
        state = "done" if index == 1 else "current" if index == 2 and week_label == "第一周" else "locked"
        status_text = "已完成" if state == "done" else "进行中" if state == "current" else "待解锁"
        nodes.append(
            {
                "id": node_id,
                "cacheKey": cache_key,
                "resourceType": resource_type,
                "label": node_id,
                "title": title,
                "statusText": status_text,
                "description": f"{week_label} · {topic}：{description}",
                "state": state,
                "x": coords["x"],
                "y": coords["y"],
                "popX": coords["popX"],
                "popY": coords["popY"],
                "actionText": LEARNING_PATH_TASK_RESOURCE_ACTIONS[resource_type],
                "actionRoute": _learning_path_task_resource_route(resource_type, topic, "", node_id, cache_key),
                "resourceTypes": [resource_type],
            }
        )
    return nodes


def build_week_one_embedded_nodes() -> list[dict]:
    return [
        {
            "id": "01",
            "cacheKey": "week1-stm32-video",
            "resourceType": "video",
            "resourceTypes": ["video"],
            "label": "01",
            "title": "STM32 开发环境与最小系统视频",
            "statusText": "可进入",
            "description": "调用视频查找工具，检索 STM32 开发环境、最小系统和程序下载调试视频。",
            "state": "current",
            "x": 112,
            "y": 420,
            "popX": 190,
            "popY": 250,
            "actionText": "查找视频",
            "actionRoute": "/personalized-resources/video-search?keyword=STM32开发环境最小系统&topic=嵌入式基础",
            "order": 1,
        },
        {
            "id": "02",
            "cacheKey": "week1-stm32-ppt",
            "resourceType": "ppt",
            "resourceTypes": ["ppt"],
            "label": "02",
            "title": "嵌入式基础与开发流程 PPT",
            "statusText": "可进入",
            "description": "进入 PPT 生成页面，梳理嵌入式系统组成、开发工具链和程序运行流程。",
            "state": "available",
            "x": 402,
            "y": 292,
            "popX": 402,
            "popY": 122,
            "actionText": "生成 PPT",
            "actionRoute": "/personalized-resources/ppt?topic=嵌入式基础与开发流程&prompt=生成一份面向嵌入式初学者的课件，包含最小系统、工具链、编译下载与调试流程。&pageCount=6&autostart=1",
            "order": 2,
        },
        {
            "id": "03",
            "cacheKey": "week1-stm32-mind-map",
            "resourceType": "mindmap",
            "resourceTypes": ["mindmap"],
            "label": "03",
            "title": "嵌入式开发知识思维导图",
            "statusText": "可进入",
            "description": "进入思维导图工具，围绕 MCU、GPIO、工具链、编译下载和调试整理知识结构。",
            "state": "available",
            "x": 646,
            "y": 316,
            "popX": 646,
            "popY": 146,
            "actionText": "生成导图",
            "actionRoute": "/personalized-resources/mind-map?topic=嵌入式开发知识思维导图&keyword=MCU GPIO 工具链 调试&autostart=1",
            "order": 3,
        },
        {
            "id": "04",
            "cacheKey": "week1-stm32-question-bank",
            "resourceType": "question-bank",
            "resourceTypes": ["quiz"],
            "label": "04",
            "title": "题库练习小测",
            "statusText": "可进入",
            "description": "进入题库生成页面，预填嵌入式基础主题，生成一组用于自测的巩固练习。",
            "state": "available",
            "x": 942,
            "y": 369,
            "popX": 942,
            "popY": 198,
            "actionText": "开始小测",
            "actionRoute": "/personalized-resources/question-bank?module=generate&course=嵌入式系统&chapter=开发环境与GPIO基础&count=10&autostart=1",
            "order": 4,
        },
        {
            "id": "05",
            "cacheKey": "week1-stm32-mcu-lab",
            "resourceType": "mcu",
            "resourceTypes": ["mcu"],
            "label": "05",
            "title": "GPIO LED 最小实验",
            "statusText": "可进入",
            "description": "进入单片机模拟器完成 GPIO 输出与 LED 控制，记录代码和运行现象。",
            "state": "available",
            "x": 1188,
            "y": 284,
            "popX": 1188,
            "popY": 114,
            "actionText": "进入实验",
            "actionRoute": "/personalized-resources/mcu-simulator/arduino/uno-led-ready?source=learning-path",
            "order": 5,
        },
        {
            "id": "06",
            "cacheKey": "week1-stm32-review",
            "resourceType": "generated_video",
            "resourceTypes": ["generated_video"],
            "label": "06",
            "title": "开发流程 AI 视频讲解",
            "statusText": "可进入",
            "description": "生成开发环境、代码编译、程序下载和运行调试流程的 AI 视频讲解，打开后由用户确认生成。",
            "state": "available",
            "x": 1398,
            "y": 185,
            "popX": 1260,
            "popY": 112,
            "actionText": "生成 AI 视频",
            "actionRoute": "/personalized-resources/video-generator?topic=嵌入式开发流程&autostart=0&source=learning-path",
            "order": 6,
        },
    ]


def default_learning_path_config() -> dict:
    return {
        "version": 2,
        "meta": {
            "eyebrow": "学习路径",
            "title": "个性化周学习计划",
            "placeholderWeekLabel": "...",
            "placeholderTitle": "后续周数",
            "needsRegeneration": True,
            "refreshRecommended": False,
            "persisted": False,
            "savedAt": "",
            "generationState": "idle",
            "taskResourceModel": LEARNING_PATH_RESOURCE_PLAN_VERSION,
            "profileReportId": 0,
            "activeProfileReportId": 0,
            "personalizationStatus": "not-generated",
            "profileSwitchPending": False,
            "pendingProfileReportId": 0,
            "totalWeeks": 6,
        },
        "planner": {
            "agent": "learning-path-planner-agent",
            "source": "bootstrap",
            "division": [],
        },
        "weeks": [],
        "stages": {},
        "updatedAt": utc_timestamp(),
    }


def _json_copy(value):
    return json.loads(json.dumps(value, ensure_ascii=False))


def _clean_text(value: object, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _clean_number(value: object, fallback: float, minimum: float | None = None, maximum: float | None = None) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = fallback
    if minimum is not None:
        number = max(minimum, number)
    if maximum is not None:
        number = min(maximum, number)
    return number


def normalize_learning_path_config(raw_config: object) -> dict:
    defaults = default_learning_path_config()
    if not isinstance(raw_config, dict):
        return defaults
    if int(_clean_number(raw_config.get("version"), 1, 1)) < 2:
        return defaults

    raw_week_ids = {
        str(item.get("id") or "").strip()
        for item in raw_config.get("weeks", [])
        if isinstance(item, dict)
    }
    if raw_week_ids and raw_week_ids.issubset(LEGACY_LEARNING_PATH_STAGE_IDS):
        return defaults

    raw_meta = raw_config.get("meta") if isinstance(raw_config.get("meta"), dict) else {}
    meta = {**defaults["meta"], **raw_meta}
    if "taskResourceModel" not in raw_meta:
        meta["taskResourceModel"] = ""
    planner = raw_config.get("planner") if isinstance(raw_config.get("planner"), dict) else defaults.get("planner", {})
    raw_weeks = raw_config.get("weeks") if isinstance(raw_config.get("weeks"), list) else []
    weeks = []
    seen_ids = set()
    for index, raw_week in enumerate(raw_weeks, start=1):
        if not isinstance(raw_week, dict):
            continue
        stage_id = re.sub(r"[^a-zA-Z0-9_-]+", "-", _clean_text(raw_week.get("id"), f"week-{index}")).strip("-") or f"week-{index}"
        if stage_id in seen_ids:
            stage_id = f"{stage_id}-{index}"
        seen_ids.add(stage_id)
        weeks.append(
            {
                "id": stage_id,
                "order": int(_clean_number(raw_week.get("order"), index, 1)),
                "weekLabel": _clean_text(raw_week.get("weekLabel") or raw_week.get("week"), f"第{index}周"),
                "title": _clean_text(raw_week.get("title"), "学习任务"),
                "description": _clean_text(raw_week.get("description") or raw_week.get("desc"), ""),
                "status": _clean_text(raw_week.get("status"), "locked"),
                "icon": _clean_text(raw_week.get("icon"), "book-open"),
                "tone": _clean_text(raw_week.get("tone"), "green"),
                "xp": int(_clean_number(raw_week.get("xp"), 0, 0)),
                "enabled": bool(raw_week.get("enabled", True)),
                "placeholder": bool(raw_week.get("placeholder", False)),
            }
        )
    weeks = sorted(weeks, key=lambda item: int(item.get("order") or 0))

    raw_stages = raw_config.get("stages") if isinstance(raw_config.get("stages"), dict) else {}
    stages = {}
    for week in weeks:
        default_stage = defaults["stages"].get(week["id"]) or {
            "id": week["id"],
            "weekLabel": week["weekLabel"],
            "title": f"{week['weekLabel']}学习路径",
            "hint": "点击节点查看任务",
            "board": {"width": 1440, "height": 640, "initialScale": 1, "minScale": 0.68, "maxScale": 1.42},
            "nodes": build_default_stage_nodes(week["weekLabel"], week.get("title", "")),
        }
        raw_stage = raw_stages.get(week["id"]) if isinstance(raw_stages.get(week["id"]), dict) else {}
        raw_board = raw_stage.get("board") if isinstance(raw_stage.get("board"), dict) else {}
        nodes = []
        raw_nodes = raw_stage.get("nodes") if isinstance(raw_stage.get("nodes"), list) else []
        for node_index, raw_node in enumerate(raw_nodes, start=1):
            if not isinstance(raw_node, dict):
                continue
            node_label = _clean_text(raw_node.get("label"), str(node_index).zfill(2))
            node_id = _clean_text(raw_node.get("id"), node_label)
            legacy_document_node = _is_legacy_learning_path_document_node(raw_node)
            resource_type = _canonical_learning_path_task_resource(raw_node, node_index)
            default_cache_key = re.sub(
                r"[^a-zA-Z0-9_.:-]+",
                "-",
                f"{week['id']}-{node_id}-{resource_type}",
            ).strip("-")
            cache_key = default_cache_key if legacy_document_node else re.sub(
                r"[^a-zA-Z0-9_.:-]+",
                "-",
                _clean_text(raw_node.get("cacheKey"), default_cache_key),
            ).strip("-") or default_cache_key
            resource_params = sanitize_learning_path_resource_params(
                resource_type,
                raw_node.get("resourceParams"),
                include_runtime=True,
            )
            if resource_type == "mcu":
                resource_params = normalize_mcu_resource_params(
                    resource_params,
                    " ".join(
                        [
                            str(week.get("title") or ""),
                            str(raw_node.get("title") or ""),
                            str(raw_node.get("description") or raw_node.get("desc") or ""),
                        ]
                    ),
                )
            raw_resource_task = (
                {}
                if legacy_document_node
                else raw_node.get("resourceTask") if isinstance(raw_node.get("resourceTask"), dict) else {}
            )
            resource_task = {
                "taskId": _clean_text(raw_resource_task.get("taskId"), ""),
                "status": _clean_text(raw_resource_task.get("status"), ""),
                "route": _clean_text(raw_resource_task.get("route"), ""),
                "progress": int(_clean_number(raw_resource_task.get("progress"), 0, 0, 100)),
                "message": _clean_text(raw_resource_task.get("message"), ""),
                "error": _clean_text(raw_resource_task.get("error"), ""),
                "lastError": _clean_text(raw_resource_task.get("lastError"), ""),
                "attemptCount": int(_clean_number(raw_resource_task.get("attemptCount"), 0, 0)),
                "generationAttemptCount": int(
                    _clean_number(raw_resource_task.get("generationAttemptCount"), 0, 0)
                ),
                "retryOfTaskId": _clean_text(raw_resource_task.get("retryOfTaskId"), ""),
                "retryable": bool(raw_resource_task.get("retryable", False)),
            }
            resource_task = {key: value for key, value in resource_task.items() if value not in {"", None}}
            if resource_type == "mcu" and resource_task.get("route"):
                resource_task["route"] = normalize_mcu_route(
                    str(resource_task["route"]),
                    resource_params,
                    str(raw_node.get("description") or ""),
                )
            generated_route = _learning_path_task_resource_route(
                resource_type,
                week.get("title") or week.get("weekLabel") or "嵌入式学习任务",
                week["id"],
                node_id,
                cache_key,
                resource_params,
            )
            nodes.append(
                {
                    "id": node_id,
                    "cacheKey": cache_key,
                    "resourceType": resource_type,
                    "label": node_label,
                    "title": _clean_text(
                        _migrate_learning_path_document_text(raw_node.get("title")) if legacy_document_node else raw_node.get("title"),
                        "学习节点",
                    ),
                    "statusText": _clean_text(raw_node.get("statusText"), ""),
                    "description": _clean_text(
                        _migrate_learning_path_document_text(raw_node.get("description") or raw_node.get("desc")) if legacy_document_node else raw_node.get("description") or raw_node.get("desc"),
                        "",
                    ),
                    "state": _clean_text(raw_node.get("state"), "locked"),
                    "x": int(_clean_number(raw_node.get("x"), 120 + node_index * 220, 0)),
                    "y": int(_clean_number(raw_node.get("y"), 320, 0)),
                    "popX": int(_clean_number(raw_node.get("popX"), _clean_number(raw_node.get("x"), 120 + node_index * 220, 0), 0)),
                    "popY": int(_clean_number(raw_node.get("popY"), max(80, _clean_number(raw_node.get("y"), 320, 0) - 170), 0)),
                    "actionText": LEARNING_PATH_TASK_RESOURCE_ACTIONS[resource_type],
                    "actionRoute": _clean_text(resource_task.get("route"), generated_route),
                    "resourceTypes": [resource_type],
                    "resourceParams": resource_params,
                    "resourcePrompt": _clean_text(
                        _migrate_learning_path_document_text(raw_node.get("resourcePrompt")) if legacy_document_node else raw_node.get("resourcePrompt"),
                        "",
                    ),
                    "resourceSelectionReason": _clean_text(
                        "旧版文档资源已下线，旧任务已迁移为学习课件。" if legacy_document_node else raw_node.get("resourceSelectionReason"),
                        "",
                    ),
                    "resourceSelectionSource": _clean_text(
                        "legacy-document-migration" if legacy_document_node else raw_node.get("resourceSelectionSource"),
                        "",
                    ),
                    "resourceTask": resource_task,
                    "deliverable": _clean_text(raw_node.get("deliverable"), ""),
                    "order": int(_clean_number(raw_node.get("order"), node_index, 0)),
                }
            )
        nodes = _ensure_learning_path_task_resource_coverage(
            nodes or _json_copy(default_stage["nodes"]),
            week.get("title") or week.get("weekLabel") or "嵌入式学习任务",
            week["id"],
        )
        stages[week["id"]] = {
            "id": week["id"],
            "weekLabel": _clean_text(raw_stage.get("weekLabel"), week["weekLabel"]),
            "title": _clean_text(raw_stage.get("title"), f"{week['weekLabel']}学习路径"),
            "hint": _clean_text(raw_stage.get("hint"), "点击节点查看任务"),
            "board": {
                "width": int(_clean_number(raw_board.get("width"), default_stage["board"]["width"], 640)),
                "height": int(_clean_number(raw_board.get("height"), default_stage["board"]["height"], 360)),
                "initialScale": _clean_number(raw_board.get("initialScale"), 1, 0.35, 2.5),
                "minScale": _clean_number(raw_board.get("minScale"), 0.68, 0.2, 2),
                "maxScale": _clean_number(raw_board.get("maxScale"), 1.42, 0.5, 4),
            },
            "nodes": nodes,
            "focus": _clean_text(raw_stage.get("focus"), week.get("title") or ""),
            "goal": _clean_text(raw_stage.get("goal"), week.get("description") or ""),
            "resourcePlanVersion": _clean_text(raw_stage.get("resourcePlanVersion"), ""),
            "resourceProfileReportId": int(_clean_number(raw_stage.get("resourceProfileReportId"), 0, 0)),
            "resourcePlanner": _json_copy(raw_stage.get("resourcePlanner")) if isinstance(raw_stage.get("resourcePlanner"), dict) else {},
            "resourcePlannerRuns": _json_copy(raw_stage.get("resourcePlannerRuns"))[-20:] if isinstance(raw_stage.get("resourcePlannerRuns"), list) else [],
            "resourcePreparation": _json_copy(raw_stage.get("resourcePreparation")) if isinstance(raw_stage.get("resourcePreparation"), dict) else {},
        }

    return {
        "version": 2,
        "meta": meta,
        "planner": planner,
        "weeks": weeks,
        "stages": stages,
        "updatedAt": _clean_text(raw_config.get("updatedAt"), defaults["updatedAt"]),
    }


def learning_path_profile_report_id(config: dict) -> int:
    """Return the persisted profile basis without treating legacy paths as personalized."""
    if not isinstance(config, dict):
        return 0
    meta = config.get("meta") if isinstance(config.get("meta"), dict) else {}
    candidates: list[object] = [meta.get("profileReportId")]
    planner = config.get("planner") if isinstance(config.get("planner"), dict) else {}
    profile_context = planner.get("profileContext") if isinstance(planner.get("profileContext"), dict) else {}
    evidence = profile_context.get("evidence") if isinstance(profile_context.get("evidence"), dict) else {}
    candidates.append(evidence.get("profileReportId"))
    stages = config.get("stages") if isinstance(config.get("stages"), dict) else {}
    candidates.extend(
        stage.get("resourceProfileReportId")
        for stage in stages.values()
        if isinstance(stage, dict)
    )
    for candidate in candidates:
        try:
            profile_id = int(candidate or 0)
        except (TypeError, ValueError):
            continue
        if profile_id > 0:
            return profile_id
    return 0


def learning_path_config_is_degraded(config: dict) -> bool:
    """Return whether a persisted path came from a fallback generation contract."""
    if not isinstance(config, dict):
        return False
    meta = config.get("meta") if isinstance(config.get("meta"), dict) else {}
    planner = config.get("planner") if isinstance(config.get("planner"), dict) else {}
    generation_status = str(meta.get("generationStatus") or "").strip().lower()
    planner_source = str(planner.get("source") or "").strip().lower()
    return (
        bool(meta.get("degraded"))
        or generation_status == "fallback"
        or planner_source in {"fallback-rule", "profile-rule-agent"}
    )


def annotate_learning_path_personalization(config: dict, profile: dict | None) -> dict:
    """Attach current profile compatibility without mutating the persisted path."""
    annotated = _json_copy(config if isinstance(config, dict) else default_learning_path_config())
    meta = annotated.setdefault("meta", {})
    path_profile_id = learning_path_profile_report_id(annotated)
    active_profile = profile if isinstance(profile, dict) else {}
    active_profile_id = int(active_profile.get("id") or active_profile.get("_profileReportId") or 0)
    active_profile_summary = (
        {
            "id": active_profile_id,
            "profileName": _clean_text(active_profile.get("profileName"), "当前画像"),
            "version": max(1, int(_clean_number(active_profile.get("version"), 1, 1))),
            "updatedAt": _clean_text(
                active_profile.get("updatedAt") or active_profile.get("_profileUpdatedAt"),
                "",
            ),
        }
        if active_profile_id > 0
        else None
    )
    has_saved_path = bool(annotated.get("weeks"))
    degraded_path = has_saved_path and learning_path_config_is_degraded(annotated)
    pending_profile_id = int(meta.get("pendingProfileReportId") or 0)
    profile_switch_pending = bool(meta.get("profileSwitchPending")) and pending_profile_id == active_profile_id

    if not has_saved_path:
        status = "not-generated"
    elif degraded_path:
        status = "degraded"
    elif profile_switch_pending:
        status = "stale-profile"
    elif path_profile_id <= 0:
        status = "legacy-generic"
    elif active_profile_id <= 0:
        status = "historical-profile"
    elif path_profile_id == active_profile_id:
        status = "active-profile"
    else:
        status = "stale-profile"

    meta.update(
        {
            "profileReportId": path_profile_id,
            "activeProfileReportId": active_profile_id,
            "activeProfileSummary": active_profile_summary,
            "personalizationStatus": status,
            "isPersonalized": status == "active-profile",
            "profileSwitchPending": profile_switch_pending,
            "pendingProfileReportId": pending_profile_id if profile_switch_pending else 0,
            "profileRequired": active_profile_id <= 0,
            "canGeneratePersonalized": active_profile_id > 0,
            "canPrepareResources": active_profile_id > 0 and not degraded_path,
            "needsRegeneration": degraded_path and active_profile_id > 0,
        }
    )
    return annotated


def mark_learning_path_profile_switch(conn: sqlite3.Connection, user_id: int, profile_id: int) -> bool:
    """Select the target profile's saved path without rewriting another profile's path."""

    config = read_learning_path_config(
        conn,
        int(user_id),
        profile_report_id=int(profile_id),
    )
    if config.get("weeks"):
        return True

    placeholder = default_learning_path_config()
    timestamp = utc_timestamp()
    placeholder["updatedAt"] = timestamp
    placeholder.setdefault("meta", {}).update({
        "activeProfileReportId": int(profile_id),
        "profileReportId": 0,
        "personalizationStatus": "not-generated",
        "isPersonalized": False,
        "profileSwitchPending": False,
        "pendingProfileReportId": 0,
        "needsRegeneration": True,
        "pathStorageScope": "profile",
        "pathSwitchedAt": timestamp,
    })
    _mirror_learning_path_config(
        conn,
        int(user_id),
        json.dumps(placeholder, ensure_ascii=False),
        timestamp,
        timestamp,
    )
    return True


def seed_learning_path_config(conn: sqlite3.Connection) -> None:
    existing = conn.execute("SELECT config_json FROM learning_path_configs WHERE id = 1").fetchone()
    if existing:
        try:
            raw_config = json.loads(existing["config_json"])
        except (TypeError, json.JSONDecodeError):
            raw_config = None
        normalized = normalize_learning_path_config(raw_config)
        if raw_config != normalized:
            timestamp = utc_timestamp()
            conn.execute(
                """
                UPDATE learning_path_configs
                SET config_json = ?, updated_at = ?
                WHERE id = 1
                """,
                (json.dumps(normalized, ensure_ascii=False), timestamp),
            )
        return
    timestamp = utc_timestamp()
    conn.execute(
        """
        INSERT INTO learning_path_configs (id, config_json, created_at, updated_at)
        VALUES (1, ?, ?, ?)
        """,
        (json.dumps(default_learning_path_config(), ensure_ascii=False), timestamp, timestamp),
    )


def _learning_path_active_profile_id(conn: sqlite3.Connection, user_id: int) -> int:
    profile = active_profile_for_user(conn, int(user_id))
    return int(profile.get("id") or profile.get("_profileReportId") or 0)


def _mirror_learning_path_config(
    conn: sqlite3.Connection,
    user_id: int,
    config_json: str,
    created_at: str,
    updated_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO user_learning_path_configs (user_id, config_json, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            config_json = excluded.config_json,
            updated_at = excluded.updated_at
        """,
        (int(user_id), config_json, created_at, updated_at),
    )


def read_learning_path_config(
    conn: sqlite3.Connection,
    user_id: int | None = None,
    profile_report_id: int | None = None,
) -> dict:
    if user_id is not None:
        resolved_profile_id = int(profile_report_id or 0)
        if resolved_profile_id <= 0:
            resolved_profile_id = _learning_path_active_profile_id(conn, int(user_id))

        row = None
        row_source = ""
        if resolved_profile_id > 0:
            row = conn.execute(
                """
                SELECT config_json, created_at, updated_at
                FROM learning_path_profile_configs
                WHERE user_id = ? AND profile_report_id = ?
                """,
                (int(user_id), resolved_profile_id),
            ).fetchone()
            if row:
                row_source = "profile"

        legacy_row = conn.execute(
            "SELECT config_json, created_at, updated_at FROM user_learning_path_configs WHERE user_id = ?",
            (int(user_id),),
        ).fetchone()
        if legacy_row:
            try:
                legacy_raw = json.loads(legacy_row["config_json"])
                legacy_profile_id = learning_path_profile_report_id(legacy_raw)
            except (TypeError, json.JSONDecodeError):
                legacy_profile_id = 0
            legacy_is_compatible = resolved_profile_id <= 0 or legacy_profile_id in {0, resolved_profile_id}
            legacy_is_newer = not row or str(legacy_row["updated_at"] or "") > str(row["updated_at"] or "")
            if legacy_is_compatible and legacy_is_newer:
                row = legacy_row
                row_source = "legacy"

        if not row:
            config = default_learning_path_config()
            config.setdefault("meta", {}).update({
                "activeProfileReportId": resolved_profile_id,
                "pathStorageScope": "profile",
            })
            return config
        try:
            raw_config = json.loads(row["config_json"])
            config = normalize_learning_path_config(raw_config)
            if raw_config != config:
                serialized = json.dumps(config, ensure_ascii=False)
                if row_source == "profile":
                    conn.execute(
                        """
                        UPDATE learning_path_profile_configs
                        SET config_json = ?
                        WHERE user_id = ? AND profile_report_id = ?
                        """,
                        (serialized, int(user_id), resolved_profile_id),
                    )
                else:
                    conn.execute(
                        "UPDATE user_learning_path_configs SET config_json = ? WHERE user_id = ?",
                        (serialized, int(user_id)),
                    )
            config["updatedAt"] = str(row["updated_at"] or config.get("updatedAt") or "")
            meta = config.setdefault("meta", {})
            meta["savedAt"] = config["updatedAt"]
            meta["pathStorageScope"] = "profile"
            meta["activeProfileReportId"] = resolved_profile_id
            return config
        except (TypeError, json.JSONDecodeError):
            return default_learning_path_config()
    row = conn.execute("SELECT config_json, updated_at FROM learning_path_configs WHERE id = 1").fetchone()
    if not row:
        seed_learning_path_config(conn)
        return default_learning_path_config()
    try:
        raw_config = json.loads(row["config_json"])
        config = normalize_learning_path_config(raw_config)
        if raw_config != config:
            conn.execute(
                "UPDATE learning_path_configs SET config_json = ? WHERE id = 1",
                (json.dumps(config, ensure_ascii=False),),
            )
        config["updatedAt"] = str(row["updated_at"] or config.get("updatedAt") or "")
        config.setdefault("meta", {})["savedAt"] = config["updatedAt"]
        return config
    except (TypeError, json.JSONDecodeError):
        return default_learning_path_config()


def write_learning_path_config(
    conn: sqlite3.Connection,
    config: dict,
    user_id: int | None = None,
    profile_report_id: int | None = None,
) -> dict:
    normalized = normalize_learning_path_config(config)
    timestamp = utc_timestamp()
    normalized["updatedAt"] = timestamp
    meta = normalized.setdefault("meta", {})
    meta["persisted"] = bool(normalized.get("weeks"))
    meta["savedAt"] = timestamp
    if user_id is not None:
        active_profile_id = _learning_path_active_profile_id(conn, int(user_id))
        candidate_profile_id = int(profile_report_id or learning_path_profile_report_id(normalized) or 0)
        profile_exists = False
        if candidate_profile_id > 0:
            profile_exists = bool(conn.execute(
                "SELECT 1 FROM learning_profile_reports WHERE id = ? AND user_id = ? AND archived = 0",
                (candidate_profile_id, int(user_id)),
            ).fetchone())
        resolved_profile_id = candidate_profile_id if profile_exists else 0
        if resolved_profile_id > 0:
            meta["profileReportId"] = resolved_profile_id
            meta["pathStorageScope"] = "profile"
        meta["activeProfileReportId"] = active_profile_id
        serialized = json.dumps(normalized, ensure_ascii=False)
        if resolved_profile_id > 0 and bool(normalized.get("weeks")):
            conn.execute(
                """
                INSERT INTO learning_path_profile_configs
                    (user_id, profile_report_id, config_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, profile_report_id) DO UPDATE SET
                    config_json = excluded.config_json,
                    updated_at = excluded.updated_at
                """,
                (int(user_id), resolved_profile_id, serialized, timestamp, timestamp),
            )
        if resolved_profile_id <= 0 or resolved_profile_id == active_profile_id:
            _mirror_learning_path_config(conn, int(user_id), serialized, timestamp, timestamp)
        return normalized
    conn.execute(
        """
        INSERT INTO learning_path_configs (id, config_json, created_at, updated_at)
        VALUES (1, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET config_json = excluded.config_json, updated_at = excluded.updated_at
        """,
        (json.dumps(normalized, ensure_ascii=False), timestamp, timestamp),
    )
    return normalized


def migrate_user_learning_path_configs(conn: sqlite3.Connection) -> int:
    migrated = 0
    rows = conn.execute(
        "SELECT user_id, config_json, created_at, updated_at FROM user_learning_path_configs"
    ).fetchall()
    for row in rows:
        try:
            raw_config = json.loads(row["config_json"])
        except (TypeError, json.JSONDecodeError):
            continue
        config = normalize_learning_path_config(raw_config)
        config["updatedAt"] = str(row["updated_at"] or config.get("updatedAt") or "")
        config.setdefault("meta", {})["savedAt"] = config["updatedAt"]
        serialized = json.dumps(config, ensure_ascii=False)
        if raw_config != config:
            conn.execute(
                "UPDATE user_learning_path_configs SET config_json = ? WHERE user_id = ?",
                (serialized, int(row["user_id"])),
            )
            migrated += 1
        profile_id = learning_path_profile_report_id(config)
        if profile_id > 0 and bool(config.get("weeks")):
            profile_exists = conn.execute(
                "SELECT 1 FROM learning_profile_reports WHERE id = ? AND user_id = ?",
                (profile_id, int(row["user_id"])),
            ).fetchone()
            if profile_exists:
                inserted = conn.execute(
                    """
                    INSERT INTO learning_path_profile_configs
                        (user_id, profile_report_id, config_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, profile_report_id) DO NOTHING
                    """,
                    (
                        int(row["user_id"]),
                        profile_id,
                        serialized,
                        str(row["created_at"] or row["updated_at"] or config["updatedAt"]),
                        str(row["updated_at"] or config["updatedAt"]),
                    ),
                )
                migrated += max(0, int(inserted.rowcount or 0))
    return migrated


def normalize_learning_path_node_cache(cache_key: str, raw_entry: object, timestamp: str | None = None) -> dict:
    key = str(cache_key or "").strip()
    entry = raw_entry if isinstance(raw_entry, dict) else {}
    try:
        normalized = json.loads(json.dumps(entry, ensure_ascii=False, default=str))
    except (TypeError, ValueError):
        normalized = {}
    normalized["cacheKey"] = key
    normalized["status"] = _clean_text(normalized.get("status"), "running")
    normalized["resourceType"] = _clean_text(normalized.get("resourceType") or normalized.get("resource_type"), "")
    if normalized["resourceType"] and isinstance(normalized.get("resourceParams"), dict):
        normalized["resourceParams"] = sanitize_learning_path_resource_params(
            normalized["resourceType"],
            normalized["resourceParams"],
            include_runtime=True,
        )
    normalized["title"] = _clean_text(normalized.get("title"), "")
    normalized["route"] = _clean_text(normalized.get("route"), "")
    if timestamp:
        normalized.setdefault("createdAt", timestamp)
        normalized["updatedAt"] = timestamp
    return normalized


def learning_path_node_cache_from_row(row: sqlite3.Row) -> dict:
    payload = parse_json_safely(row["payload_json"], {})
    entry = payload if isinstance(payload, dict) else {}
    entry["cacheKey"] = row["cache_key"]
    entry["status"] = entry.get("status") or row["status"]
    entry["resourceType"] = entry.get("resourceType") or row["resource_type"]
    if entry["resourceType"] and isinstance(entry.get("resourceParams"), dict):
        entry["resourceParams"] = sanitize_learning_path_resource_params(
            str(entry["resourceType"]),
            entry["resourceParams"],
            include_runtime=True,
        )
    entry["title"] = entry.get("title") or row["title"]
    entry["route"] = entry.get("route") or row["route"]
    entry["createdAt"] = entry.get("createdAt") or row["created_at"]
    entry["updatedAt"] = entry.get("updatedAt") or row["updated_at"]
    return entry


def upsert_learning_path_node_cache(conn: sqlite3.Connection, user_id: int, cache_key: str, raw_entry: object) -> dict:
    key = re.sub(r"[^a-zA-Z0-9_.:-]+", "-", str(cache_key or "").strip()).strip("-")
    if not key:
        raise ValueError("cache_key is required")
    timestamp = utc_timestamp()
    entry = normalize_learning_path_node_cache(key, raw_entry, timestamp)
    conn.execute(
        """
        INSERT INTO learning_path_node_caches
            (user_id, cache_key, status, resource_type, title, route, payload_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, cache_key) DO UPDATE SET
            status = excluded.status,
            resource_type = excluded.resource_type,
            title = excluded.title,
            route = excluded.route,
            payload_json = excluded.payload_json,
            updated_at = excluded.updated_at
        """,
        (
            user_id,
            key,
            entry.get("status", "running"),
            entry.get("resourceType", ""),
            entry.get("title", ""),
            entry.get("route", ""),
            json.dumps(entry, ensure_ascii=False),
            timestamp,
            timestamp,
        ),
    )
    return entry


LEARNING_FEEDBACK_OUTCOMES = {"completed", "needs_review", "blocked"}
LEARNING_FEEDBACK_DIFFICULTIES = {"easy", "appropriate", "hard"}


def _optional_bool(value: object) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "是", "有帮助"}:
        return True
    if text in {"0", "false", "no", "n", "否", "没帮助", "无帮助"}:
        return False
    return None


_INTERNAL_EVIDENCE_PREFIX_RE = re.compile(
    r"^\[[^\]]*(?:harness|e2e|function[-_ ]?check|smoke|test)[^\]]*\]\s*",
    flags=re.IGNORECASE,
)
_RESOURCE_AGENT_TITLE_SUFFIX_RE = re.compile(
    r"\s*[·｜|]\s*(?:题库生成|PPT生成|思维导图|视频查找|历史实践|课程讲义|动画讲解|智能辅导|效果评估)?(?:智能体|agent)\s*$",
    flags=re.IGNORECASE,
)
_CORRUPTED_LEARNING_TEXT_RE = re.compile(r"\?{2,}|\ufffd")


def normalize_learning_weak_point(value: object) -> str:
    """Keep learner-facing concepts while dropping internal task/test labels."""

    text = " ".join(str(value or "").strip().split())
    if not text:
        return ""
    if _CORRUPTED_LEARNING_TEXT_RE.search(text):
        return ""
    text = _RESOURCE_AGENT_TITLE_SUFFIX_RE.sub("", text).strip()
    if _INTERNAL_EVIDENCE_PREFIX_RE.match(text):
        return ""
    if not text or text.lower() in {"unknown", "none", "null", "暂无", "无"}:
        return ""
    return text[:80]


def learning_feedback_from_row(row: sqlite3.Row) -> dict:
    return {
        "id": int(row["id"]),
        "profileReportId": int(row["profile_report_id"] or 0),
        "taskId": str(row["task_id"] or ""),
        "runId": str(row["run_id"] or ""),
        "resourceType": str(row["resource_type"] or ""),
        "topic": str(row["topic"] or ""),
        "route": str(row["route"] or ""),
        "cacheKey": str(row["cache_key"] or ""),
        "outcome": str(row["outcome"] or "completed"),
        "difficulty": str(row["difficulty"] or "appropriate"),
        "helpful": None if row["helpful"] is None else bool(row["helpful"]),
        "rating": int(row["rating"]) if row["rating"] is not None else None,
        "note": str(row["note"] or ""),
        "evidence": json_loads_safe(row["evidence_json"], {}),
        "createdAt": str(row["created_at"] or ""),
        "updatedAt": str(row["updated_at"] or ""),
    }


def normalize_learning_feedback_cache_key(value: object) -> str:
    raw_key = str(value or "").strip()
    normalized = re.sub(
        r"[^a-zA-Z0-9_.:-]+",
        "-",
        raw_key,
    ).strip("-")
    if not raw_key:
        return ""
    if normalized == raw_key and len(raw_key) <= 160:
        return raw_key
    digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]
    prefix = normalized[: 160 - len(digest) - 1].rstrip("-")
    return f"{prefix}-{digest}" if prefix else digest


def list_learning_feedback_records(
    conn: sqlite3.Connection,
    user_id: int,
    *,
    task_id: str = "",
    cache_key: str = "",
    limit: int = 40,
) -> list[dict]:
    safe_limit = max(1, min(200, int(limit or 40)))
    values: list[object] = [int(user_id)]
    record_filters: list[str] = []
    if str(task_id or "").strip():
        record_filters.append("task_id = ?")
        values.append(str(task_id).strip())
    cache_key = normalize_learning_feedback_cache_key(cache_key)
    if cache_key:
        record_filters.append("cache_key = ?")
        values.append(cache_key)
    record_filter = f" AND {' AND '.join(record_filters)}" if record_filters else ""
    values.append(safe_limit)
    rows = conn.execute(
        f"""
        SELECT * FROM learning_feedback_records
        WHERE user_id = ?{record_filter}
        ORDER BY updated_at DESC, id DESC
        LIMIT ?
        """,
        values,
    ).fetchall()
    return [learning_feedback_from_row(row) for row in rows]


def record_learning_feedback(conn: sqlite3.Connection, user_id: int, payload: dict) -> dict:
    payload = payload if isinstance(payload, dict) else {}
    outcome = str(payload.get("outcome") or "completed").strip().lower()
    if outcome not in LEARNING_FEEDBACK_OUTCOMES:
        raise ValueError("outcome 必须是 completed、needs_review 或 blocked")
    difficulty = str(payload.get("difficulty") or "appropriate").strip().lower()
    if difficulty not in LEARNING_FEEDBACK_DIFFICULTIES:
        raise ValueError("difficulty 必须是 easy、appropriate 或 hard")
    rating_value = payload.get("rating")
    try:
        rating = int(rating_value) if rating_value not in {None, ""} else None
    except (TypeError, ValueError):
        raise ValueError("rating 必须是 1 到 5 的整数") from None
    if rating is not None and not 1 <= rating <= 5:
        raise ValueError("rating 必须是 1 到 5 的整数")

    task_id = str(payload.get("taskId") or payload.get("task_id") or "").strip()[:100]
    cache_key = normalize_learning_feedback_cache_key(
        payload.get("cacheKey") or payload.get("cache_key")
    )
    task_row = None
    task_result: dict = {}
    if task_id:
        task_row = conn.execute(
            """
            SELECT task_id, task_type, title, route, status, result_json
            FROM xiaozhi_tasks
            WHERE user_id = ? AND task_id = ?
            LIMIT 1
            """,
            (int(user_id), task_id),
        ).fetchone()
        if not task_row:
            raise LookupError("反馈对应的嵌小智任务不存在或不属于当前用户")
        task_result = json_loads_safe(task_row["result_json"], {})

    active_profile = active_profile_for_user(conn, int(user_id))
    profile_report_id = int(
        payload.get("profileReportId")
        or payload.get("_profileReportId")
        or (active_profile or {}).get("id")
        or 0
    )
    if not profile_report_id:
        raise LearningProfileRequiredError("当前没有激活画像，暂不能记录画像驱动的学习反馈。")

    orchestration_context = payload.get("orchestrationContext") if isinstance(payload.get("orchestrationContext"), dict) else {}
    run_id = str(payload.get("runId") or orchestration_context.get("runId") or "").strip()[:100]
    resource_type = str(
        payload.get("resourceType")
        or payload.get("resource_type")
        or (task_row["task_type"] if task_row else "")
    ).strip()[:80]
    topic = str(
        payload.get("topic")
        or payload.get("title")
        or (task_row["title"] if task_row else "学习资源")
    ).strip()[:200]
    route = str(payload.get("route") or (task_row["route"] if task_row else "")).strip()[:1000]
    note = str(payload.get("note") or payload.get("message") or "").strip()[:2000]
    helpful = _optional_bool(payload.get("helpful"))
    quality = task_result.get("qualityEvaluation") if isinstance(task_result.get("qualityEvaluation"), dict) else {}
    if not quality:
        selected = task_result.get("selectedResource") if isinstance(task_result.get("selectedResource"), dict) else {}
        quality = selected.get("qualityEvaluation") if isinstance(selected.get("qualityEvaluation"), dict) else {}
    evidence = {
        "source": "learner-explicit-feedback",
        "taskStatus": str(task_row["status"] or "") if task_row else "",
        "qualityEvaluation": quality,
        "submittedBy": "xiaozhi-learning-feedback-agent",
    }
    timestamp = now_iso()

    existing_row = None
    if task_id and cache_key:
        existing_row = conn.execute(
            """
            SELECT id, task_id, cache_key, created_at
            FROM learning_feedback_records
            WHERE user_id = ? AND task_id = ? AND cache_key = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (int(user_id), task_id, cache_key),
        ).fetchone()
        if existing_row is None:
            legacy_rows = conn.execute(
                """
                SELECT id, task_id, cache_key, created_at
                FROM learning_feedback_records
                WHERE user_id = ? AND task_id = ?
                ORDER BY id DESC
                LIMIT 2
                """,
                (int(user_id), task_id),
            ).fetchall()
            if len(legacy_rows) == 1 and not str(legacy_rows[0]["cache_key"] or "").strip():
                existing_row = legacy_rows[0]
    elif task_id:
        existing_row = conn.execute(
            """
            SELECT id, task_id, cache_key, created_at
            FROM learning_feedback_records
            WHERE user_id = ? AND task_id = ? AND cache_key = ''
            ORDER BY id DESC
            LIMIT 1
            """,
            (int(user_id), task_id),
        ).fetchone()
        # A legacy caller may only know the task id. Preserve its sole resource
        # feedback, but never guess once the task has multiple resource records.
        if existing_row is None:
            task_rows = conn.execute(
                """
                SELECT id, task_id, cache_key, created_at
                FROM learning_feedback_records
                WHERE user_id = ? AND task_id = ?
                ORDER BY id DESC
                LIMIT 2
                """,
                (int(user_id), task_id),
            ).fetchall()
            if len(task_rows) == 1:
                existing_row = task_rows[0]
    elif cache_key:
        existing_row = conn.execute(
            """
            SELECT id, task_id, cache_key, created_at
            FROM learning_feedback_records
            WHERE user_id = ? AND cache_key = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (int(user_id), cache_key),
        ).fetchone()
    if existing_row:
        if not task_id:
            task_id = str(existing_row["task_id"] or "").strip()
        if not cache_key:
            cache_key = str(existing_row["cache_key"] or "").strip()

    values = (
        profile_report_id,
        task_id,
        run_id,
        resource_type,
        topic,
        route,
        cache_key,
        outcome,
        difficulty,
        None if helpful is None else int(helpful),
        rating,
        note,
        json.dumps(evidence, ensure_ascii=False),
        timestamp,
    )
    if existing_row:
        feedback_id = int(existing_row["id"])
        conn.execute(
            """
            UPDATE learning_feedback_records
            SET profile_report_id = ?, task_id = ?, run_id = ?, resource_type = ?, topic = ?,
                route = ?, cache_key = ?, outcome = ?, difficulty = ?, helpful = ?, rating = ?,
                note = ?, evidence_json = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (*values, feedback_id, int(user_id)),
        )
    else:
        cursor = conn.execute(
            """
            INSERT INTO learning_feedback_records
                (user_id, profile_report_id, task_id, run_id, resource_type, topic, route,
                 cache_key, outcome, difficulty, helpful, rating, note, evidence_json,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (int(user_id), *values[:-1], timestamp, timestamp),
        )
        feedback_id = int(cursor.lastrowid)

    path_cache = None
    if cache_key:
        cache_row = conn.execute(
            "SELECT * FROM learning_path_node_caches WHERE user_id = ? AND cache_key = ?",
            (int(user_id), cache_key),
        ).fetchone()
    else:
        cache_row = None
    if cache_row:
        cache_entry = learning_path_node_cache_from_row(cache_row)
        previous_feedback = (
            cache_entry.get("learningFeedback")
            if isinstance(cache_entry.get("learningFeedback"), dict)
            else {}
        )
        feedback_state = {
            "feedbackId": feedback_id,
            "outcome": outcome,
            "difficulty": difficulty,
            "updatedAt": timestamp,
        }
        for key in (
            "statusBeforeCompletion",
            "completedAtBeforeCompletion",
            "completionSourceBeforeCompletion",
        ):
            if key in previous_feedback:
                feedback_state[key] = previous_feedback.get(key)
        if outcome == "completed" and previous_feedback.get("outcome") != "completed":
            feedback_state.update(
                {
                    "statusBeforeCompletion": cache_entry.get("status") or "running",
                    "completedAtBeforeCompletion": cache_entry.get("completedAt"),
                    "completionSourceBeforeCompletion": cache_entry.get("completionSource"),
                }
            )
        cache_entry.update(
            {
                "cacheKey": cache_key,
                "resourceType": resource_type or cache_entry.get("resourceType") or "",
                "title": topic or cache_entry.get("title") or "",
                "route": route or cache_entry.get("route") or "",
                "learningFeedback": feedback_state,
            }
        )
        if outcome == "completed":
            cache_entry["status"] = "complete"
            cache_entry["completedAt"] = timestamp
            cache_entry["completionSource"] = "learning-feedback"
        elif cache_entry.get("completionSource") == "learning-feedback":
            cache_entry["status"] = str(feedback_state.get("statusBeforeCompletion") or "running")
            previous_completed_at = feedback_state.get("completedAtBeforeCompletion")
            previous_completion_source = feedback_state.get("completionSourceBeforeCompletion")
            if previous_completed_at:
                cache_entry["completedAt"] = previous_completed_at
            else:
                cache_entry.pop("completedAt", None)
            if previous_completion_source:
                cache_entry["completionSource"] = previous_completion_source
            else:
                cache_entry.pop("completionSource", None)
        path_cache = upsert_learning_path_node_cache(conn, int(user_id), cache_key, cache_entry)

    conn.execute(
        """
        INSERT INTO xiaozhi_events (user_id, event_type, route, title, payload_json, created_at)
        VALUES (?, 'learning_feedback', ?, ?, ?, ?)
        """,
        (
            int(user_id),
            route,
            topic,
            json.dumps(
                {
                    "feedbackId": feedback_id,
                    "taskId": task_id,
                    "resourceType": resource_type,
                    "outcome": outcome,
                    "difficulty": difficulty,
                    "helpful": helpful,
                    "rating": rating,
                    "cacheKey": cache_key,
                },
                ensure_ascii=False,
            ),
            timestamp,
        ),
    )
    row = conn.execute(
        "SELECT * FROM learning_feedback_records WHERE id = ? AND user_id = ?",
        (feedback_id, int(user_id)),
    ).fetchone()
    feedback = learning_feedback_from_row(row)
    if path_cache:
        feedback["pathCache"] = path_cache
    return feedback


def latest_learning_profile_for_user(conn: sqlite3.Connection, user_id: int) -> dict:
    return active_profile_for_user(conn, user_id)


RESOURCE_VISIT_ROUTES = (
    ("/personalized-resources/question-bank", "question-bank", "题库"),
    ("/personalized-resources/mind-map", "mindmap", "思维导图"),
    ("/personalized-resources/video-search", "video", "学习视频"),
    ("/personalized-resources/mcu-simulator", "mcu", "单片机实验"),
    ("/personalized-resources/knowledge-base", "knowledge-base", "私有知识库"),
    ("/personalized-resources/document", "document", "PPT 课件"),
    ("/personalized-resources/animation", "animation", "动画讲解"),
    ("/personalized-resources/ppt", "ppt", "PPT"),
    ("/smart-tutor", "smart-tutor", "智能辅导"),
)


def learning_resource_visit(route: object) -> dict:
    raw_route = str(route or "").strip()
    if not raw_route:
        return {}
    path = urlparse(raw_route).path.rstrip("/")
    for prefix, resource_type, label in RESOURCE_VISIT_ROUTES:
        if path == prefix or path.startswith(f"{prefix}/"):
            return {"type": resource_type, "label": label}
    return {}


def learning_evidence_for_user(conn: sqlite3.Connection, user_id: int) -> dict:
    assistant_chats = conn.execute(
        """
        SELECT role, content, created_at
        FROM xiaozhi_messages
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 20
        """,
        (user_id,),
    ).fetchall()
    profile_chats = conn.execute(
        """
        SELECT m.role, m.content, m.created_at
        FROM learning_profile_session_messages m
        JOIN learning_profile_sessions s ON s.id = m.session_id
        WHERE s.user_id = ?
        ORDER BY m.id DESC
        LIMIT 20
        """,
        (user_id,),
    ).fetchall()
    conversation_memories = knowledge_growth.recent_memory_context(conn, int(user_id), limit=12)
    experiments = conn.execute(
        """
        SELECT experiment_name, passed, weak_points, run_data, created_at
        FROM mcu_experiments
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 12
        """,
        (user_id,),
    ).fetchall()
    node_rows = conn.execute(
        """
        SELECT status, resource_type, title, updated_at
        FROM learning_path_node_caches
        WHERE user_id = ?
        ORDER BY updated_at DESC
        LIMIT 40
        """,
        (user_id,),
    ).fetchall()
    page_view_rows = conn.execute(
        """
        SELECT route, title, payload_json, created_at
        FROM xiaozhi_events
        WHERE user_id = ? AND event_type = 'page_view'
        ORDER BY id DESC
        LIMIT 200
        """,
        (user_id,),
    ).fetchall()
    activity_rows = conn.execute(
        """
        SELECT session_id, route, route_name, started_at, last_seen_at,
               active_seconds, status, ended_at, updated_at
        FROM learning_activity_sessions
        WHERE user_id = ?
        ORDER BY updated_at DESC
        LIMIT 500
        """,
        (user_id,),
    ).fetchall()
    feedback_rows = conn.execute(
        """
        SELECT * FROM learning_feedback_records
        WHERE user_id = ?
        ORDER BY updated_at DESC, id DESC
        LIMIT 80
        """,
        (user_id,),
    ).fetchall()
    try:
        question_history = list_history(user_id)
    except Exception:
        question_history = {"question_sheets": [], "exam_results": []}

    path_config_row = conn.execute(
        "SELECT config_json, updated_at FROM user_learning_path_configs WHERE user_id = ?",
        (user_id,),
    ).fetchone()

    weak_points: list[str] = []
    knowledge_point_stats: dict[str, dict] = {}

    def add_knowledge_point_evidence(label: object, correct: bool, source: str) -> None:
        point = normalize_learning_weak_point(label)
        if not point:
            return
        entry = knowledge_point_stats.setdefault(
            point,
            {
                "knowledgePoint": point,
                "attempts": 0,
                "correctCount": 0,
                "incorrectCount": 0,
                "evidenceTypes": [],
            },
        )
        entry["attempts"] += 1
        if correct:
            entry["correctCount"] += 1
        else:
            entry["incorrectCount"] += 1
        if source and source not in entry["evidenceTypes"]:
            entry["evidenceTypes"].append(source)

    exam_summaries: list[dict] = []
    for exam in (question_history.get("exam_results") or [])[:10]:
        question_count = int(exam.get("question_count") or 0)
        correct_count = int(exam.get("correct_count") or 0)
        accuracy = round(correct_count / question_count * 100) if question_count else 0
        exam_summaries.append(
            {
                "title": exam.get("title"),
                "score": exam.get("score"),
                "totalScore": exam.get("total_score"),
                "accuracy": accuracy,
                "createdAt": exam.get("created_at"),
            }
        )
        detail_items = exam.get("detail") or []
        if isinstance(detail_items, dict):
            detail_items = detail_items.get("items") or detail_items.get("details") or []
        for item in detail_items if isinstance(detail_items, list) else []:
            if not isinstance(item, dict):
                continue
            question = item.get("question") if isinstance(item.get("question"), dict) else {}
            knowledge_point = (
                item.get("knowledge_point")
                or item.get("knowledgePoint")
                or question.get("knowledge_point")
                or question.get("knowledgePoint")
                or item.get("type")
                or question.get("type")
            )
            is_correct = bool(item.get("correct") or item.get("isCorrect"))
            add_knowledge_point_evidence(knowledge_point, is_correct, "question-bank")
            if is_correct:
                continue
            if knowledge_point:
                weak_points.append(str(knowledge_point))

    experiment_summaries: list[dict] = []
    for row in experiments:
        row_weak_points = json_loads_safe(row["weak_points"], [])
        row_weak_points = row_weak_points if isinstance(row_weak_points, list) else []
        passed = bool(row["passed"])
        if isinstance(row_weak_points, list) and row_weak_points:
            for point in row_weak_points:
                add_knowledge_point_evidence(point, passed, "mcu-experiment")
        elif row["experiment_name"]:
            add_knowledge_point_evidence(row["experiment_name"], passed, "mcu-experiment")
        if not row["passed"]:
            weak_points.extend(str(item) for item in row_weak_points if str(item).strip())
        experiment_summaries.append(
            {
                "name": row["experiment_name"],
                "passed": bool(row["passed"]),
                "weakPoints": row_weak_points,
                "createdAt": row["created_at"],
            }
        )

    learning_feedbacks = [learning_feedback_from_row(row) for row in feedback_rows]
    for item in learning_feedbacks:
        if item.get("outcome") in {"needs_review", "blocked"} and item.get("topic"):
            weak_points.append(str(item["topic"]))

    deduped_weak_points = list(dict.fromkeys(
        point
        for item in weak_points
        if (point := normalize_learning_weak_point(item))
    ))[:10]
    completed_nodes = sum(1 for row in node_rows if row["status"] == "complete")
    resource_calls = [
        {
            "title": str(row["title"] or ""),
            "type": str(row["resource_type"] or ""),
            "status": str(row["status"] or ""),
            "updatedAt": str(row["updated_at"] or ""),
        }
        for row in node_rows
    ]
    resource_visits = []
    for row in page_view_rows:
        visit = learning_resource_visit(row["route"])
        if not visit:
            continue
        event_payload = json_loads_safe(row["payload_json"], {})
        resource_visits.append(
            {
                **visit,
                "route": str(row["route"] or ""),
                "title": str(row["title"] or visit["label"]),
                "routeName": str(event_payload.get("name") or ""),
                "createdAt": str(row["created_at"] or ""),
            }
        )
    activity_sessions = [
        {
            "sessionId": str(row["session_id"] or ""),
            "route": str(row["route"] or ""),
            "routeName": str(row["route_name"] or ""),
            "startedAt": str(row["started_at"] or ""),
            "lastSeenAt": str(row["last_seen_at"] or ""),
            "activeSeconds": max(0, int(row["active_seconds"] or 0)),
            "status": str(row["status"] or "active"),
            "endedAt": str(row["ended_at"] or ""),
            "updatedAt": str(row["updated_at"] or ""),
        }
        for row in activity_rows
    ]
    active_learning_seconds = sum(item["activeSeconds"] for item in activity_sessions)
    question_sheets = [
        {
            "title": str(item.get("title") or ""),
            "course": str(item.get("course_name") or item.get("course") or ""),
            "questionCount": int(item.get("question_count") or item.get("questionCount") or 0),
            "createdAt": str(item.get("created_at") or item.get("createdAt") or ""),
        }
        for item in (question_history.get("question_sheets") or [])[:10]
        if isinstance(item, dict)
    ]
    recent_chats = [
        {
            "source": source,
            "role": str(row["role"] or ""),
            "content": str(row["content"] or "")[:500],
            "createdAt": str(row["created_at"] or ""),
        }
        for source, rows in (("xiaozhi", assistant_chats), ("profile-dialogue", profile_chats))
        for row in rows
    ]
    recent_chats.sort(key=lambda item: item["createdAt"], reverse=True)
    knowledge_stats = []
    for item in knowledge_point_stats.values():
        attempts = max(0, int(item.get("attempts") or 0))
        correct_count = max(0, int(item.get("correctCount") or 0))
        mastery_rate = round(correct_count / attempts * 100) if attempts else 0
        knowledge_stats.append(
            {
                **item,
                "masteryRate": mastery_rate,
                "status": "mastered" if mastery_rate >= 80 else "developing" if mastery_rate >= 60 else "weak",
            }
        )
    knowledge_stats.sort(key=lambda item: (item["masteryRate"], -item["attempts"], item["knowledgePoint"]))
    config = parse_json_safely(path_config_row["config_json"], {}) if path_config_row else {}
    weeks = config.get("weeks") if isinstance(config, dict) else []
    weeks = weeks if isinstance(weeks, list) else []
    week_progress = [
        {
            "weekId": str(week.get("id") or ""),
            "week": str(week.get("weekLabel") or week.get("title") or ""),
            "title": str(week.get("title") or ""),
            "status": str(week.get("status") or ""),
        }
        for week in weeks if isinstance(week, dict)
    ]
    evidence_payload = {
        "source": "platform-learning-evidence",
        "recentChats": recent_chats[:20],
        "conversationMemories": conversation_memories,
        "questionSheets": question_sheets,
        "examResults": exam_summaries,
        "mcuExperiments": experiment_summaries,
        "resourceCalls": resource_calls,
        "resourceVisits": resource_visits,
        "activitySessions": activity_sessions,
        "learningFeedbacks": learning_feedbacks,
        "activeLearningSeconds": active_learning_seconds,
        "knowledgePointStats": knowledge_stats[:20],
        "weakPoints": deduped_weak_points,
        "pathProgress": {
            "completedNodes": completed_nodes,
            "trackedNodes": len(node_rows),
            "weeks": week_progress,
            "updatedAt": str(path_config_row["updated_at"] or "") if path_config_row else "",
        },
    }
    version_payload = {
        "recentChats": recent_chats[:20],
        "questionSheets": question_sheets,
        "examResults": exam_summaries,
        "mcuExperiments": experiment_summaries,
        "resourceCalls": resource_calls,
        "resourceVisits": resource_visits,
        "learningFeedbacks": learning_feedbacks,
        "activeLearningSeconds": active_learning_seconds,
        "knowledgePointStats": knowledge_stats[:20],
        "weakPoints": deduped_weak_points,
    }
    evidence_payload["evidenceVersion"] = hashlib.sha256(
        json.dumps(version_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    timestamps = [
        str(item.get("createdAt") or item.get("updatedAt") or item.get("startedAt") or "")
        for item in [
            *recent_chats,
            *question_sheets,
            *exam_summaries,
            *experiment_summaries,
            *resource_calls,
            *resource_visits,
            *activity_sessions,
            *learning_feedbacks,
        ]
        if item.get("createdAt") or item.get("updatedAt") or item.get("startedAt")
    ]
    timestamps.extend(str(row["updated_at"] or "") for row in node_rows if row["updated_at"])
    evidence_payload["updatedAt"] = max(timestamps) if timestamps else ""
    return evidence_payload


EFFECT_RADAR_LABELS = ["基础知识", "编程调试", "实验动手", "项目实践", "学习投入", "工程素养"]
EFFECT_DOMAIN_KEYWORDS = {
    "foundation": ("嵌入式", "单片机", "MCU", "STM32", "C语言", "寄存器", "计算机基础"),
    "diagnosis": ("编程", "调试", "串口", "UART", "中断", "定时器", "PWM", "状态机", "日志"),
    "medicine": ("实验", "GPIO", "开发板", "接线", "烧录", "仿真", "示波器", "传感器"),
    "cases": ("项目", "Linux驱动", "RTOS", "FreeRTOS", "BSP", "设备树", "综合实训", "复盘"),
}


def _bounded_percentage(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return round(max(0.0, min(100.0, number)), 1)


def _weighted_evidence_rate(components: list[dict]) -> tuple[float, list[dict]]:
    available = [
        item for item in components
        if isinstance(item, dict) and item.get("available") and float(item.get("weight") or 0) > 0
    ]
    total_weight = sum(float(item.get("weight") or 0) for item in available)
    if not available or total_weight <= 0:
        return 0.0, components
    score = sum(
        _bounded_percentage(item.get("rate")) * float(item.get("weight") or 0)
        for item in available
    ) / total_weight
    return _bounded_percentage(score), components


def _effect_profile_weak_points(profile: dict) -> list[str]:
    candidates: list[object] = []
    student_profile = profile.get("chatStudentProfile") if isinstance(profile.get("chatStudentProfile"), dict) else {}
    for key, value in student_profile.items():
        normalized_key = str(key or "").lower()
        if any(marker in normalized_key for marker in ("薄弱", "易错", "weak", "error")):
            candidates.append(value)
    analysis = profile.get("aiAnalysis") if isinstance(profile.get("aiAnalysis"), dict) else {}
    candidates.extend(
        analysis.get(key)
        for key in ("weaknesses", "weakPoints", "knowledgeWeaknesses")
        if analysis.get(key)
    )

    points: list[str] = []
    for candidate in candidates:
        values = candidate if isinstance(candidate, list) else [candidate]
        for value in values:
            text = normalize_learning_weak_point(value)
            if not text:
                continue
            concise = re.split(r"[，。；;]", text, maxsplit=1)[0].strip()[:80]
            if not concise:
                continue
            if "阶段" in concise and not any(
                marker in concise.lower()
                for marker in ("嵌入式", "单片机", "mcu", "stm32", "gpio", "串口", "中断", "定时器", "驱动", "rtos", "项目", "实验")
            ):
                continue
            if any(point in concise or concise in point for point in points):
                continue
            points.append(concise)
    return points[:10]


def _effect_knowledge_heatmap(evidence: dict, profile_weak_points: list[str] | None = None) -> list[dict]:
    heatmap = []
    seen: set[str] = set()
    for raw in evidence.get("knowledgePointStats") or []:
        if not isinstance(raw, dict):
            continue
        label = " ".join(str(raw.get("knowledgePoint") or "").strip().split())[:80]
        if not label or label in seen:
            continue
        seen.add(label)
        attempts = max(0, int(raw.get("attempts") or 0))
        correct_count = max(0, min(attempts, int(raw.get("correctCount") or 0)))
        mastery_rate = _bounded_percentage(
            raw.get("masteryRate") if raw.get("masteryRate") is not None
            else (correct_count / attempts * 100 if attempts else 0)
        )
        status = "unverified" if attempts == 0 else "mastered" if mastery_rate >= 80 else "developing" if mastery_rate >= 60 else "weak"
        heatmap.append(
            {
                "knowledgePoint": label,
                "masteryRate": mastery_rate,
                "attempts": attempts,
                "correctCount": correct_count,
                "incorrectCount": max(0, attempts - correct_count),
                "status": status,
                "evidenceTypes": list(dict.fromkeys(str(item) for item in (raw.get("evidenceTypes") or []) if str(item).strip())),
            }
        )

    evidence_weak_points = [*(evidence.get("weakPoints") or []), *(profile_weak_points or [])]
    for raw_point in evidence_weak_points:
        label = normalize_learning_weak_point(raw_point)
        if not label or label in seen:
            continue
        seen.add(label)
        heatmap.append(
            {
                "knowledgePoint": label,
                "masteryRate": 0.0,
                "attempts": 0,
                "correctCount": 0,
                "incorrectCount": 0,
                "status": "unverified",
                "evidenceTypes": [
                    "weak-point-record"
                    if raw_point in (evidence.get("weakPoints") or [])
                    else "profile-reported-weakness"
                ],
            }
        )
    heatmap.sort(key=lambda item: (item["masteryRate"], -item["attempts"], item["knowledgePoint"]))
    return heatmap[:16]


def _effect_path_adjustment_plan(profile: dict, evidence: dict, heatmap: list[dict]) -> dict:
    weeks = (evidence.get("pathProgress") or {}).get("weeks") or []
    target_week = next(
        (item for item in weeks if str(item.get("status") or "").lower() in {"current", "active", "in-progress"}),
        weeks[0] if weeks else {},
    )
    focus_points = [
        item for item in heatmap
        if item.get("status") in {"weak", "developing", "unverified"}
    ][:3]
    profile_id = int(profile.get("id") or profile.get("_profileReportId") or 0)
    evidence_version = str(evidence.get("evidenceVersion") or "no-evidence")
    plan_seed = f"{profile_id}:{evidence_version}:{','.join(item['knowledgePoint'] for item in focus_points)}"
    plan_id = f"effect-{hashlib.sha256(plan_seed.encode('utf-8')).hexdigest()[:12]}"
    resource_cycle = ["question-bank", "mindmap", "ppt"]
    task_actions = {
        "question-bank": "完成 8 道专项题，正确率达到 80%，并复盘全部错题。",
        "mindmap": "输出一张包含核心概念、配置链路、实验现象和易错点的复盘导图。",
        "ppt": "完成一套包含工作原理、关键代码与调试要点的复习课件。",
    }
    tasks = []
    for index, point in enumerate(focus_points, start=1):
        resource_type = resource_cycle[(index - 1) % len(resource_cycle)]
        point_name = point["knowledgePoint"]
        node_hash = hashlib.sha256(f"{plan_id}:{point_name}".encode("utf-8")).hexdigest()[:8]
        tasks.append(
            {
                "nodeId": f"adjust-{node_hash}",
                "order": index,
                "title": f"{point_name}专项巩固",
                "description": f"针对当前掌握率 {point['masteryRate']:.0f}% 的证据，完成一次诊断、学习与再验证。",
                "knowledgePoint": point_name,
                "currentMasteryRate": point["masteryRate"],
                "resourceType": resource_type,
                "resourceParams": {
                    "topic": f"{point_name}专项巩固与再验证",
                    "course": "嵌入式系统",
                    "chapter": point_name,
                    "count": 8,
                    "autostart": 1,
                    "source": "effect-assessment",
                    "assessmentPlanId": plan_id,
                },
                "resourcePrompt": f"围绕{point_name}生成个性化巩固资源，先诊断错因，再完成可验收学习任务。",
                "selectionReason": f"知识点热力图显示该项状态为 {point['status']}，当前掌握率 {point['masteryRate']:.0f}%。",
                "acceptanceCriteria": task_actions[resource_type],
            }
        )
    return {
        "planId": plan_id,
        "profileReportId": profile_id,
        "evidenceVersion": evidence_version,
        "targetWeekId": str(target_week.get("weekId") or ""),
        "targetWeekLabel": str(target_week.get("week") or target_week.get("title") or ""),
        "reason": "优先把热力图中掌握率最低或尚待验证的知识点加入当前周，形成再学习与再验证闭环。",
        "tasks": tasks,
        "canApply": bool(profile.get("isActive", True) and target_week.get("weekId") and tasks),
        "status": "recommended",
    }


def _format_active_learning_duration(active_seconds: int, session_count: int) -> str:
    seconds = max(0, int(active_seconds or 0))
    if seconds <= 0:
        return "不足 1 分钟" if session_count else "暂无可核验时长"
    total_minutes = max(1, round(seconds / 60))
    hours, minutes = divmod(total_minutes, 60)
    if hours and minutes:
        return f"{hours} 小时 {minutes} 分钟"
    if hours:
        return f"{hours} 小时"
    return f"{minutes} 分钟"


def effect_assessment_snapshot(profile: dict, evidence: dict) -> dict:
    """Derive a transparent, deterministic assessment from persisted learning evidence."""
    stored_assessment = profile.get("effectAssessment") if isinstance(profile.get("effectAssessment"), dict) else {}
    profile_analysis = profile.get("aiAnalysis") if isinstance(profile.get("aiAnalysis"), dict) else {}
    stored_labels = stored_assessment.get("labels") if isinstance(stored_assessment.get("labels"), list) else []
    baseline_candidates = [
        stored_assessment.get("radarScores") if stored_labels == EFFECT_RADAR_LABELS else None,
        profile_analysis.get("radarScores"),
        profile.get("scaleScores"),
    ]
    baseline = next((item for item in baseline_candidates if isinstance(item, list) and len(item) == 6), [])
    baseline = [max(1, min(5, float(baseline[index] if index < len(baseline) else 2))) for index in range(6)]
    exams = evidence.get("examResults") or []
    exam_accuracy = sum(float(item.get("accuracy") or 0) for item in exams) / len(exams) if exams else 0
    generated_resources = evidence.get("resourceCalls") or []
    resource_visits = evidence.get("resourceVisits") or []
    learning_feedbacks = evidence.get("learningFeedbacks") or []
    activity_sessions = evidence.get("activitySessions") or []
    active_learning_seconds = max(0, int(evidence.get("activeLearningSeconds") or 0))
    completed_nodes = int((evidence.get("pathProgress") or {}).get("completedNodes") or 0)
    tracked_nodes = int((evidence.get("pathProgress") or {}).get("trackedNodes") or 0)
    path_completion_rate = completed_nodes / tracked_nodes * 100 if tracked_nodes else 0
    resource_types = {str(item.get("type") or "") for item in resource_visits if item.get("type")}
    knowledge_stats = [item for item in (evidence.get("knowledgePointStats") or []) if isinstance(item, dict)]

    def domain_mastery(domain: str) -> tuple[float, int]:
        keywords = EFFECT_DOMAIN_KEYWORDS[domain]
        matching = [
            item for item in knowledge_stats
            if any(keyword in str(item.get("knowledgePoint") or "") for keyword in keywords)
        ]
        attempts = sum(max(0, int(item.get("attempts") or 0)) for item in matching)
        correct = sum(max(0, int(item.get("correctCount") or 0)) for item in matching)
        return ((correct / attempts) if attempts else 0.0), attempts

    def matching_evidence_count(items: list[dict], domain: str) -> int:
        keywords = EFFECT_DOMAIN_KEYWORDS[domain]
        return sum(
            1 for item in items
            if isinstance(item, dict)
            and any(
                keyword in " ".join(str(item.get(field) or "") for field in ("title", "topic", "route", "label", "type"))
                for keyword in keywords
            )
        )

    quantified_stats = [item for item in knowledge_stats if max(0, int(item.get("attempts") or 0)) > 0]
    total_knowledge_attempts = sum(max(0, int(item.get("attempts") or 0)) for item in quantified_stats)
    total_knowledge_correct = sum(max(0, int(item.get("correctCount") or 0)) for item in quantified_stats)
    overall_knowledge_rate = total_knowledge_correct / total_knowledge_attempts if total_knowledge_attempts else 0.0
    foundation_mastery, _ = domain_mastery("foundation")
    diagnosis_mastery, _ = domain_mastery("diagnosis")
    medicine_mastery, _ = domain_mastery("medicine")
    case_mastery, _ = domain_mastery("cases")
    completed_feedbacks = [item for item in learning_feedbacks if item.get("outcome") == "completed"]
    experiment_visits = sum(
        1
        for item in resource_visits
        if str(item.get("type") or "") in {"mcu", "simulator", "code"}
        or matching_evidence_count([item], "medicine") > 0
    )
    experiment_feedbacks = matching_evidence_count(completed_feedbacks, "medicine")
    debugging_feedbacks = matching_evidence_count(completed_feedbacks, "diagnosis")
    project_feedbacks = matching_evidence_count(completed_feedbacks, "cases")
    exam_rate = exam_accuracy / 100
    path_rate = path_completion_rate / 100
    activity_count = (
        len(evidence.get("recentChats") or [])
        + len(exams)
        + len(resource_visits)
        + len(learning_feedbacks)
        + min(20, active_learning_seconds // 900)
    )
    gains = [
        min(
            1.6,
            exam_rate * 0.55
            + overall_knowledge_rate * 0.55
            + foundation_mastery * 0.35
            + min(0.2, len(quantified_stats) * 0.025),
        ),
        min(
            1.6,
            diagnosis_mastery * 0.75
            + exam_rate * 0.35
            + path_rate * 0.3
            + min(0.2, debugging_feedbacks * 0.08),
        ),
        min(
            1.6,
            medicine_mastery * 0.75
            + exam_rate * 0.25
            + min(0.4, experiment_visits * 0.12)
            + min(0.2, experiment_feedbacks * 0.08),
        ),
        min(
            1.6,
            case_mastery * 0.7
            + path_rate * 0.45
            + min(0.3, project_feedbacks * 0.12)
            + min(0.25, completed_nodes * 0.025),
        ),
        min(1.5, activity_count * 0.025 + min(0.7, active_learning_seconds / 900 * 0.08)),
        min(
            1.5,
            exam_rate * 0.35
            + path_rate * 0.35
            + min(0.4, len(resource_types) * 0.08)
            + min(0.3, len(quantified_stats) * 0.03)
            + min(0.2, len(completed_feedbacks) * 0.025),
        ),
    ]
    scores = [round(min(5, baseline[index] + gains[index]), 1) for index in range(6)]
    improvements = [
        {"label": EFFECT_RADAR_LABELS[index], "delta": round(scores[index] - baseline[index], 1)}
        for index in range(6) if scores[index] > baseline[index]
    ]
    heatmap = _effect_knowledge_heatmap(evidence, _effect_profile_weak_points(profile))
    quantified_points = [item for item in heatmap if int(item.get("attempts") or 0) > 0]
    total_point_attempts = sum(int(item.get("attempts") or 0) for item in quantified_points)
    knowledge_mastery_rate = (
        sum(float(item.get("masteryRate") or 0) * int(item.get("attempts") or 0) for item in quantified_points)
        / total_point_attempts
        if total_point_attempts else 0
    )
    achievement_rate, achievement_breakdown = _weighted_evidence_rate(
        [
            {"label": "学习路径任务", "rate": path_completion_rate, "weight": 0.6, "available": tracked_nodes > 0},
            {"label": "题单与考试", "rate": exam_accuracy, "weight": 0.4, "available": bool(exams)},
        ]
    )
    mastery_rate, mastery_breakdown = _weighted_evidence_rate(
        [
            {"label": "知识点答题", "rate": knowledge_mastery_rate, "weight": 0.7, "available": bool(quantified_points)},
            {"label": "综合考试", "rate": exam_accuracy, "weight": 0.3, "available": bool(exams)},
        ]
    )
    timestamps = [
        item.get("createdAt") or item.get("updatedAt") or item.get("startedAt")
        for key in (
            "recentChats",
            "questionSheets",
            "examResults",
            "resourceVisits",
            "activitySessions",
            "learningFeedbacks",
        )
        for item in (evidence.get(key) or [])
        if item.get("createdAt") or item.get("updatedAt") or item.get("startedAt")
    ]
    duration_days = 0
    active_dates: set[str] = set()
    if timestamps:
        try:
            parsed_dates = [
                datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
                for value in timestamps
            ]
            earliest = min(parsed_dates)
            duration_days = max(1, (datetime.now().date() - earliest).days + 1)
            active_dates = {item.isoformat() for item in parsed_dates}
        except (TypeError, ValueError):
            duration_days = 1
    activity_dates: set[str] = set()
    for item in activity_sessions:
        value = item.get("startedAt") or item.get("updatedAt")
        if not value:
            continue
        try:
            activity_dates.add(datetime.fromisoformat(str(value).replace("Z", "+00:00")).date().isoformat())
        except (TypeError, ValueError):
            continue
    evidence_count = sum(
        len(evidence.get(key) or [])
        for key in ("recentChats", "questionSheets", "examResults", "resourceVisits", "learningFeedbacks")
    )
    confidence_score = min(
        100,
        min(10, len(evidence.get("recentChats") or [])) * 2
        + min(5, len(evidence.get("questionSheets") or [])) * 4
        + min(5, len(exams)) * 8
        + min(10, completed_nodes) * 2
        + min(10, len(resource_visits)) * 2
        + min(10, len(learning_feedbacks)) * 2
        + min(10, active_learning_seconds // 900) * 2
        + min(5, len(quantified_points)) * 8,
    )
    adjustment_plan = _effect_path_adjustment_plan(profile, evidence, heatmap)
    weak_points = list(dict.fromkeys(
        [item["knowledgePoint"] for item in heatmap if item.get("status") in {"weak", "unverified"}]
        + [
            point
            for item in (evidence.get("weakPoints") or [])
            if (point := normalize_learning_weak_point(item))
        ]
    ))[:10]
    return {
        "schemaVersion": "2.2",
        "profileReportId": int(profile.get("id") or profile.get("_profileReportId") or 0),
        "evidenceVersion": str(evidence.get("evidenceVersion") or ""),
        "labels": EFFECT_RADAR_LABELS,
        "previousRadarScores": [round(value, 1) for value in baseline],
        "radarScores": scores,
        "improvements": improvements,
        "achievementRate": achievement_rate,
        "masteryRate": mastery_rate,
        "achievementBreakdown": achievement_breakdown,
        "masteryBreakdown": mastery_breakdown,
        "knowledgeHeatmap": heatmap,
        "pathAdjustmentPlan": adjustment_plan,
        "learningDurationDays": duration_days,
        "activeLearningDays": len(activity_dates),
        "activeLearningSeconds": active_learning_seconds,
        "activeLearningMinutes": round(active_learning_seconds / 60, 1),
        "learningDurationText": _format_active_learning_duration(active_learning_seconds, len(activity_sessions)),
        "learningDurationBasis": "server-heartbeat",
        "resourceTypes": sorted(resource_types),
        "resourceCount": len(resource_visits),
        "resourceVisits": resource_visits[:40],
        "learningFeedbacks": learning_feedbacks[:40],
        "generatedResourceCount": len(generated_resources),
        "completedNodes": completed_nodes,
        "trackedNodes": tracked_nodes,
        "weakPoints": weak_points,
        "evidenceCount": evidence_count,
        "confidenceScore": confidence_score,
        "confidenceLevel": "high" if confidence_score >= 75 else "medium" if confidence_score >= 40 else "low",
        "evidenceUsed": {
            "recentChats": len(evidence.get("recentChats") or []),
            "questionSheets": len(evidence.get("questionSheets") or []),
            "examResults": len(exams),
            "resourceVisits": len(resource_visits),
            "learningFeedbacks": len(learning_feedbacks),
            "generatedResources": len(generated_resources),
            "activitySessions": len(activity_sessions),
            "knowledgePoints": len(heatmap),
            "legacyMcuExperimentsIgnored": len(evidence.get("mcuExperiments") or []),
        },
        "summary": (
            f"本次评估基于 {evidence_count} 条平台学习证据，"
            f"当前学习达成率为 {achievement_rate:.1f}%，掌握率为 {mastery_rate:.1f}%。"
        ),
        "updatedAt": evidence.get("updatedAt") or now_iso(),
    }



def _effect_assessment_records(
    conn: sqlite3.Connection,
    user_id: int,
    profile_report_id: int,
    *,
    limit: int = 10,
) -> list[dict]:
    rows = conn.execute(
        """
        SELECT id, run_id, assessment_json, path_adjustment_json, status, created_at, applied_at
        FROM learning_effect_assessments
        WHERE user_id = ? AND profile_report_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (int(user_id), int(profile_report_id), max(1, min(50, int(limit or 10)))),
    ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "runId": str(row["run_id"] or ""),
            "assessment": json_loads_safe(row["assessment_json"], {}),
            "pathAdjustment": json_loads_safe(row["path_adjustment_json"], {}),
            "status": str(row["status"] or "evaluated"),
            "createdAt": str(row["created_at"] or ""),
            "appliedAt": str(row["applied_at"] or ""),
        }
        for row in rows
    ]


def _find_effect_assessment_plan_record(records: list[dict], plan_id: str) -> dict:
    expected = str(plan_id or "").strip()
    if not expected:
        return {}
    return next(
        (
            item for item in records
            if str((item.get("pathAdjustment") or {}).get("planId") or "") == expected
        ),
        {},
    )


def _effect_path_adjustment_preview(profile: dict, assessment: dict) -> dict:
    plan = assessment.get("pathAdjustmentPlan") if isinstance(assessment.get("pathAdjustmentPlan"), dict) else {}
    tasks = [item for item in (plan.get("tasks") or []) if isinstance(item, dict)]
    return {
        "planId": str(plan.get("planId") or ""),
        "profileReportId": int(profile.get("id") or 0),
        "targetWeekId": str(plan.get("targetWeekId") or ""),
        "targetWeekLabel": str(plan.get("targetWeekLabel") or ""),
        "addedNodeIds": [str(item.get("nodeId") or "") for item in tasks if item.get("nodeId")],
        "addedCount": len(tasks),
        "alreadyApplied": False,
        "appliedAt": "",
        "status": "pending_review",
    }


def _apply_effect_path_adjustment(
    conn: sqlite3.Connection,
    user_id: int,
    profile: dict,
    assessment: dict,
) -> dict:
    plan = assessment.get("pathAdjustmentPlan") if isinstance(assessment.get("pathAdjustmentPlan"), dict) else {}
    plan_id = str(plan.get("planId") or "").strip()
    target_week_id = str(plan.get("targetWeekId") or "").strip()
    if not profile.get("isActive"):
        raise ValueError("只能把当前使用画像的评估结果应用到学习路径")
    if not plan_id or not target_week_id or not plan.get("tasks"):
        raise ValueError("当前评估没有可应用的路径调整任务")

    conn.execute("BEGIN IMMEDIATE")
    config = read_learning_path_config(conn, int(user_id))
    stage = (config.get("stages") or {}).get(target_week_id)
    if not isinstance(stage, dict):
        raise LookupError("当前学习路径中不存在目标周，请先生成学习路径")

    meta = config.setdefault("meta", {})
    applied_plans = meta.get("appliedEffectPlans") if isinstance(meta.get("appliedEffectPlans"), list) else []
    existing_plan = next(
        (item for item in applied_plans if isinstance(item, dict) and str(item.get("planId") or "") == plan_id),
        None,
    )
    nodes = stage.get("nodes") if isinstance(stage.get("nodes"), list) else []
    expected_node_ids = {
        str(item.get("nodeId") or "")
        for item in (plan.get("tasks") or [])
        if isinstance(item, dict) and item.get("nodeId")
    }
    if existing_plan or (expected_node_ids and expected_node_ids.issubset({str(item.get("id") or "") for item in nodes if isinstance(item, dict)})):
        return {
            "planId": plan_id,
            "profileReportId": int(profile.get("id") or 0),
            "targetWeekId": target_week_id,
            "targetWeekLabel": str(plan.get("targetWeekLabel") or stage.get("weekLabel") or ""),
            "addedNodeIds": sorted(expected_node_ids),
            "addedCount": 0,
            "alreadyApplied": True,
            "appliedAt": str((existing_plan or {}).get("appliedAt") or ""),
            "status": "applied",
        }

    max_order = max((int(item.get("order") or 0) for item in nodes if isinstance(item, dict)), default=0)
    added_node_ids: list[str] = []
    for offset, task in enumerate(plan.get("tasks") or [], start=1):
        if not isinstance(task, dict):
            continue
        node_id = str(task.get("nodeId") or "").strip()
        if not node_id or any(str(item.get("id") or "") == node_id for item in nodes if isinstance(item, dict)):
            continue
        order = max_order + offset
        coordinate = DEFAULT_STAGE_NODE_COORDS[(order - 1) % len(DEFAULT_STAGE_NODE_COORDS)]
        resource_type = str(task.get("resourceType") or "question-bank")
        resource_params = _json_copy(task.get("resourceParams")) if isinstance(task.get("resourceParams"), dict) else {}
        resource_params.update(
            {
                "source": "effect-assessment",
                "assessmentPlanId": plan_id,
                "profileReportId": int(profile.get("id") or 0),
                "stageId": target_week_id,
                "nodeId": node_id,
            }
        )
        cache_key = re.sub(
            r"[^a-zA-Z0-9_.:-]+",
            "-",
            f"{target_week_id}-{node_id}-{resource_type}-{plan_id}",
        ).strip("-")
        nodes.append(
            {
                "id": node_id,
                "cacheKey": cache_key,
                "resourceType": resource_type,
                "label": str(order).zfill(2),
                "title": str(task.get("title") or "效果评估专项巩固"),
                "statusText": "效果评估追加",
                "description": str(task.get("description") or "完成一次诊断、学习与再验证。"),
                "state": "available",
                "x": coordinate["x"],
                "y": coordinate["y"],
                "popX": coordinate["popX"],
                "popY": coordinate["popY"],
                "resourceParams": resource_params,
                "resourcePrompt": str(task.get("resourcePrompt") or ""),
                "resourceSelectionReason": str(task.get("selectionReason") or plan.get("reason") or ""),
                "resourceSelectionSource": "effect-assessment",
                "resourceTask": {"status": "waiting", "progress": 0},
                "deliverable": str(task.get("acceptanceCriteria") or "完成任务并留下可复盘证据。"),
                "order": order,
            }
        )
        added_node_ids.append(node_id)

    if not added_node_ids:
        raise ValueError("路径调整任务已存在或无法写入")

    applied_at = now_iso()
    stage["nodes"] = nodes
    existing_task_count = sum(
        1
        for node in nodes
        if isinstance(node, dict) and str((node.get("resourceTask") or {}).get("taskId") or "")
    )
    stage["resourcePreparation"] = {
        **(stage.get("resourcePreparation") if isinstance(stage.get("resourcePreparation"), dict) else {}),
        "version": LEARNING_PATH_RESOURCE_PLAN_VERSION,
        "status": "running",
        "profileReportId": int(profile.get("id") or 0),
        "plannedCount": existing_task_count,
        "resolvedCount": existing_task_count,
        "totalCount": len(nodes),
        "currentNodeId": added_node_ids[0],
        "updatedAt": applied_at,
        "error": "",
    }
    applied_plans.append(
        {
            "planId": plan_id,
            "profileReportId": int(profile.get("id") or 0),
            "targetWeekId": target_week_id,
            "addedNodeIds": added_node_ids,
            "appliedAt": applied_at,
        }
    )
    meta["appliedEffectPlans"] = applied_plans[-20:]
    meta["lastEffectAssessmentPlanId"] = plan_id
    meta["lastEffectAssessmentAppliedAt"] = applied_at
    write_learning_path_config(conn, config, int(user_id))
    return {
        "planId": plan_id,
        "profileReportId": int(profile.get("id") or 0),
        "targetWeekId": target_week_id,
        "targetWeekLabel": str(plan.get("targetWeekLabel") or stage.get("weekLabel") or ""),
        "addedNodeIds": added_node_ids,
        "addedCount": len(added_node_ids),
        "alreadyApplied": False,
        "appliedAt": applied_at,
        "status": "applied",
    }
