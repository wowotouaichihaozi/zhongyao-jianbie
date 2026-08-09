import json
import operator
import re
from pathlib import Path
from typing import Annotated, Any

import requests
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from typing_extensions import TypedDict

try:
    from api_config import setting_default
    from common import get_setting
    from course_knowledge import grounded_prompt_block
except ImportError:  # pragma: no cover
    from .api_config import setting_default
    from .common import get_setting
    from .course_knowledge import grounded_prompt_block


DEFAULT_MODEL = "xsparkx2agent"
DEFAULT_API_URL = "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2/chat/completions"
TOKEN_PLAN_API_URL = DEFAULT_API_URL

QUESTION_AGENT_TYPES = ["单选题", "多选题", "判断题", "填空题", "简答题", "计算题", "综合应用题"]
QUESTION_TYPE_ALIASES = {
    "应用题": "综合应用题",
    "综合题": "综合应用题",
    "综合应用": "综合应用题",
}
QUESTION_TYPE_AGENT_SPECS = {
    "单选题": {"node": "single_choice_agent", "label": "单选题智能体"},
    "多选题": {"node": "multiple_choice_agent", "label": "多选题智能体"},
    "判断题": {"node": "true_false_agent", "label": "判断题智能体"},
    "填空题": {"node": "fill_blank_agent", "label": "填空题智能体"},
    "简答题": {"node": "short_answer_agent", "label": "简答题智能体"},
    "计算题": {"node": "calculation_agent", "label": "计算题智能体"},
    "综合应用题": {"node": "application_agent", "label": "综合应用题智能体"},
}

TASK_PLANNER_SYSTEM_PROMPT = """你是题库生成多智能体工作流中的总结压缩与任务说明智能体。
你只负责根据课程名称、章节主题、学生画像、额外要求和资料文本进行总结压缩，并给各题型智能体写出题重点。
你严禁重新分配题量，严禁修改用户输入的题型数量，严禁因为目标题量自行禁用任何用户已选择的题型。
如果资料文本是作业、试卷、题单或包含编号题目，你必须把它当作“原题锚点资料”处理：
1. compressed_context 不能只写知识点摘要，必须保留尽可能多的原题编号、题干核心数据、表达式、代码、选项关键词、正确答案和解析结论。
2. 每个题型 instruction 都要告诉对应题型智能体：优先围绕这些原题锚点生成原题或相似题；可以按用户配置改变题型，但题干场景、数字、代码、表达式、概念判断点要尽量沿用原题。
3. 如果用户要求“多出原题/原题相似/题干相似”，不要泛化成章节知识点列表，必须显式写入“优先复用原题题干信息”。

只输出 JSON，不要输出 Markdown。JSON 结构：
{
  "compressed_context": "压缩后的资料摘要；若有原题，按编号保留原题锚点",
  "task_summary": "整体出题目标",
  "assignments": {
    "单选题": {"instruction": "该题型智能体的出题重点"},
    "多选题": {"instruction": "该题型智能体的出题重点"}
  }
}
"""


def question_type_agent_node_name(question_type: str) -> str:
    return QUESTION_TYPE_AGENT_SPECS.get(question_type, {"node": f"{question_type}_agent"})["node"]


def question_type_agent_label(question_type: str) -> str:
    return QUESTION_TYPE_AGENT_SPECS.get(question_type, {"label": f"{question_type}智能体"})["label"]


def normalize_question_type(question_type: Any) -> str:
    text = str(question_type or "").strip()
    return QUESTION_TYPE_ALIASES.get(text, text)


def normalize_question_type_counts(counts: Any) -> dict[str, int]:
    if not isinstance(counts, dict):
        return {}
    normalized: dict[str, int] = {}
    for question_type, count in counts.items():
        canonical = normalize_question_type(question_type)
        if not canonical:
            continue
        try:
            numeric_count = int(count)
        except (TypeError, ValueError):
            continue
        if numeric_count <= 0:
            continue
        normalized[canonical] = normalized.get(canonical, 0) + numeric_count
    return normalized


def single_choice_agent(state: dict[str, Any], run_agent):
    return run_agent(state, "单选题")


def multiple_choice_agent(state: dict[str, Any], run_agent):
    return run_agent(state, "多选题")


def true_false_agent(state: dict[str, Any], run_agent):
    return run_agent(state, "判断题")


def fill_blank_agent(state: dict[str, Any], run_agent):
    return run_agent(state, "填空题")


def short_answer_agent(state: dict[str, Any], run_agent):
    return run_agent(state, "简答题")


def calculation_agent(state: dict[str, Any], run_agent):
    return run_agent(state, "计算题")


def application_agent(state: dict[str, Any], run_agent):
    return run_agent(state, "综合应用题")


QUESTION_TYPE_AGENT_FUNCTIONS = {
    "单选题": single_choice_agent,
    "多选题": multiple_choice_agent,
    "判断题": true_false_agent,
    "填空题": fill_blank_agent,
    "简答题": short_answer_agent,
    "计算题": calculation_agent,
    "综合应用题": application_agent,
}


class StructuredContentError(ValueError):
    def __init__(self, message: str, result: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.result = result


def _anthropic_base_to_chat_url(base_url: str) -> str:
    """Convert configured Anthropic-compatible base URL to chat-completions URL.

    The question-bank LangGraph workflow already speaks OpenAI-style
    /chat/completions. The shared project config stores the same token-plan
    service as an Anthropic base, usually ending in /anthropic, so normalize it
    here instead of asking users for a second MIMO_API_KEY/mimo_config.json.
    """
    configured_openai_base = get_setting("OPENAI_BASE_URL", setting_default("OPENAI_BASE_URL", ""))
    base = str(configured_openai_base or base_url or "").strip().rstrip("/")
    if not base:
        return DEFAULT_API_URL
    if base.endswith("/v1/chat/completions") or base.endswith("/chat/completions"):
        return base
    if base.endswith("/anthropic"):
        base = base[: -len("/anthropic")]
    elif base.endswith("/v1/messages"):
        base = base[: -len("/v1/messages")]
    elif base.endswith("/messages"):
        base = base[: -len("/messages")]
    if base.endswith("/v2") or base.endswith("/v1"):
        return f"{base}/chat/completions"
    if "maas-coding-api.cn-huabei-1.xf-yun.com" in base:
        return f"{base.rstrip('/')}/v2/chat/completions"
    return f"{base.rstrip('/')}/v1/chat/completions"


def get_mimo_api_key(payload: dict[str, Any]) -> str:
    return get_setting("ANTHROPIC_AUTH_TOKEN", setting_default("ANTHROPIC_AUTH_TOKEN")).strip()


def get_mimo_model(payload: dict[str, Any]) -> str:
    return (
        get_setting("ANTHROPIC_MODEL", setting_default("ANTHROPIC_MODEL"))
        or DEFAULT_MODEL
    ).strip()


def get_mimo_api_url(payload: dict[str, Any]) -> str:
    return _anthropic_base_to_chat_url(get_setting("ANTHROPIC_BASE_URL", setting_default("ANTHROPIC_BASE_URL")))


def get_mimo_token_plan_api_url(payload: dict[str, Any]) -> str:
    return _anthropic_base_to_chat_url(get_setting("ANTHROPIC_BASE_URL", setting_default("ANTHROPIC_BASE_URL")))


QUESTION_JSON_SYSTEM_PROMPT = """你是"结构化题库生成助手"。
请根据给定的学生画像、课程主题、学习目标和资源规划结果，输出适合生成题库文件的结构化 JSON。

要求：
1. 只输出 JSON，不要输出 Markdown，不要输出额外说明。
2. 题目总数以用户给出的目标题量为准，最多不超过 50 题。
3. 至少覆盖基础、提升、综合三个难度层次。
4. 每道题必须包含题干、答案、解析。
5. 若题型为选择题，需要给出 options；若不是选择题，可给空数组。
6. 概念必须准确，题目要贴合课程范围与学生基础。
7. 如果用户给出题型数量分布，必须逐项严格满足，不能全部改成单选题。
8. 如果资源规划结果中包含“原始上传题单/原题文本”、作业详情、试卷题目、编号题目、选项、答案或解析，你必须优先基于原题锚点生成：
   - 题干要尽量保留原题的核心场景、数字、代码、表达式、选项知识点和判断点。
   - 允许按用户配置改变题型，例如把判断题改成填空题、把单选题扩展为综合应用题，但不能脱离原题另起炉灶。
   - 当用户要求“原题/相似题/题干相似/尽量多出原题”时，至少 70% 的题目应能从题干看出对应的上传原题来源。
   - 不要把原题压缩成泛泛的“栈、队列、递归”概念题；优先保留“入栈序列、循环队列公式、中缀转后缀、链式栈指针修改、稀疏矩阵存储”等原题细节。

输出 JSON 结构如下：
{
  "title": "题库标题",
  "course_name": "课程名称",
  "target_topic": "目标主题",
  "summary": "本套题训练目标",
  "questions": [
    {
      "id": "Q1",
      "type": "单选题",
      "difficulty": "基础",
      "knowledge_point": "知识点名称",
      "stem": "题目内容",
      "options": ["A. ...", "B. ..."],
      "answer": "标准答案",
      "analysis": "解析内容",
      "mistake_alert": "易错提醒"
    }
  ]
}
"""


def validate_payload(payload: dict[str, Any]) -> list[str]:
    required_fields = ["student_profile", "course_name", "target_topic", "resource_plan_result"]
    errors = []
    for field in required_fields:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field} 为必填字符串")

    preferred_question_types = payload.get("preferred_question_types")
    if preferred_question_types is not None:
        if not isinstance(preferred_question_types, list) or not all(
            isinstance(item, str) and item.strip() for item in preferred_question_types
        ):
            errors.append("preferred_question_types 必须是非空字符串数组")

    question_count = payload.get("question_count")
    if question_count is not None:
        if not isinstance(question_count, int) or question_count < 1 or question_count > 50:
            errors.append("question_count 必须是 1 到 50 之间的整数")

    return errors


def build_question_json_prompt(payload: dict[str, Any]) -> str:
    preferred_question_types = payload.get("preferred_question_types", [])
    type_hint = "、".join(preferred_question_types) if preferred_question_types else "请自行选择合适题型"
    question_type_counts = payload.get("question_type_counts", {})
    if isinstance(question_type_counts, dict) and question_type_counts:
        type_count_hint = "、".join(
            f"{question_type} {count} 题"
            for question_type, count in question_type_counts.items()
            if isinstance(question_type, str) and isinstance(count, int) and count > 0
        )
    else:
        type_count_hint = ""
    source_text = str(payload.get("source_original_text") or payload.get("resource_plan_result") or "")
    source_is_question_sheet = (
        str(payload.get("source_mode") or "") == "question_sheet"
        or looks_like_uploaded_question_sheet(source_text)
        or should_prioritize_original_questions(payload)
    )
    original_anchor_requirement = ""
    if source_is_question_sheet:
        original_anchor_requirement = f"""

原题锚点生成要求：
1. 这批资料包含上传题单/原题文本。你必须优先从原题题干、选项、答案、解析中抽取锚点，再生成题目。
2. 当前批次如果只要求一种题型，也必须只输出该题型；可以把原题改写为该题型，但题干核心信息必须相似。
3. 尽量按原题编号顺序取材，避免只生成泛化概念题。
4. 如果资源中有“若让元素1,2,3,4,5依次进栈”“循环队列(rear+1) mod m”“链式栈 top->link”“中缀/后缀表达式”等具体信息，生成题干应保留这些具体信息。
5. 上传原题全文如下，供你逐题对齐，不要只看摘要：
{source_text[:20000]}
"""

    return f"""请为以下内容生成可直接用于题库文件的结构化 JSON。

学生画像：{payload["student_profile"].strip()}

课程名称：{payload["course_name"].strip()}

学习主题：{payload["target_topic"].strip()}

学习目标：{payload.get("learning_objectives", "").strip() or "请结合主题和学生基础合理推断"}

资源规划结果：{payload["resource_plan_result"].strip()}

建议题型：{type_hint}

目标题量：{payload.get("question_count", 8)} 题

题型数量分布：{type_count_hint or "未指定，请按建议题型合理分配"}

额外约束：{payload.get("constraints", "").strip() or "无"}

补充说明：{payload.get("notes", "").strip() or "无"}
{original_anchor_requirement}

请生成一套题目，覆盖基础、提升、综合三个难度层次，并严格输出 JSON。
额外要求：
1. 所有字段都必须完整闭合，确保返回的是可直接解析的合法 JSON。
2. 每道题的 analysis 控制在 2 到 4 句内，mistake_alert 控制在 1 句内，避免过长。
3. 必须尽量严格遵守题型数量分布和目标题量，不要自行改成单一题型。
4. 若题量较多，优先保持 JSON 完整，不要为了写更长解析而截断后续题目。
5. 如果本批次是原题锚点生成，所有题目都要尽量写出可识别的原题相似题干。"""


def resolve_mimo_api_url(api_key: str, payload: dict[str, Any]) -> str:
    if api_key.startswith("tp-"):
        return get_mimo_token_plan_api_url(payload)
    return get_mimo_api_url(payload)


def _escape_json_string_control_chars(text: str) -> str:
    result: list[str] = []
    in_string = False
    escaped = False
    for char in text:
        if not in_string:
            result.append(char)
            if char == '"':
                in_string = True
            continue
        if escaped:
            result.append(char)
            escaped = False
            continue
        if char == "\\":
            result.append(char)
            escaped = True
            continue
        if char == '"':
            result.append(char)
            in_string = False
            continue
        code = ord(char)
        if code < 32:
            if char == "\n":
                result.append("\\n")
            elif char == "\r":
                result.append("\\r")
            elif char == "\t":
                result.append("\\t")
            else:
                result.append(f"\\u{code:04x}")
        else:
            result.append(char)
    return "".join(result)


def _json_loads_lenient(candidate: str) -> dict[str, Any]:
    cleaned = candidate.strip().lstrip("\ufeff")
    variants = [
        cleaned,
        re.sub(r",(\s*[}\]])", r"\1", cleaned),
        _escape_json_string_control_chars(cleaned),
        re.sub(r",(\s*[}\]])", r"\1", _escape_json_string_control_chars(cleaned)),
    ]
    last_error: json.JSONDecodeError | None = None
    for variant in dict.fromkeys(variants):
        try:
            return json.loads(variant)
        except json.JSONDecodeError as exc:
            last_error = exc
    if last_error:
        raise last_error
    raise json.JSONDecodeError("empty JSON content", cleaned, 0)


def parse_json_text(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 3:
            cleaned = "\n".join(lines[1:-1]).strip()

    try:
        return _json_loads_lenient(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            candidate = cleaned[start : end + 1]
            return _json_loads_lenient(candidate)
        raise


def validate_question_json(data: dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise ValueError("题库结构化结果不是有效 JSON 对象")

    title = data.get("title")
    questions = data.get("questions")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("题库 JSON 缺少有效 title")
    if not isinstance(questions, list) or not questions:
        raise ValueError("题库 JSON 缺少有效 questions 数组")

    # LLM 偶尔使用别名字段（如 "top" 代替 "stem"），在此统一修正
    _field_aliases = {
        "top": "stem",
        "question": "stem",
        "content": "stem",
        "body": "stem",
        "explanation": "analysis",
        "solution": "analysis",
        "knowledge": "knowledge_point",
        "knowledge-point": "knowledge_point",
        "title": "stem",
        "question_text": "stem",
        "questionStem": "stem",
        "题干": "stem",
        "题目": "stem",
        "问题": "stem",
        "解析": "analysis",
        "答案解析": "analysis",
        "knowledgePoint": "knowledge_point",
        "知识点": "knowledge_point",
        "correct_answer": "answer",
        "correctAnswer": "answer",
        "正确答案": "answer",
        "答案": "answer",
        "题型": "type",
        "难度": "difficulty",
    }
    for question in questions:
        if not isinstance(question, dict):
            continue
        for alias, target in _field_aliases.items():
            if alias in question and target not in question:
                question[target] = question.pop(alias)
        raw_options = question.get("options")
        if raw_options is None:
            raw_options = question.get("选项") or question.get("choices") or question.get("Choices") or []
        if isinstance(raw_options, dict):
            question["options"] = [f"{key}. {value}" for key, value in raw_options.items()]
        elif isinstance(raw_options, str):
            question["options"] = [item.strip() for item in re.split(r"\n|(?=[A-D][\.、])", raw_options) if item.strip()]
        elif not isinstance(raw_options, list):
            question["options"] = []
        if not isinstance(question.get("stem"), str) or not question.get("stem", "").strip():
            option_text = " ".join(str(item) for item in question.get("options", [])[:4])
            question["stem"] = str(question.get("name") or question.get("prompt") or option_text or "请结合原资料完成本题").strip()
        for fallback_field, fallback_value in [
            ("id", ""),
            ("type", "题目"),
            ("difficulty", "中等"),
            ("knowledge_point", "综合知识点"),
            ("answer", "待复核"),
            ("analysis", "该题由智能体生成，建议结合原资料复核。"),
        ]:
            if not isinstance(question.get(fallback_field), str) or not question.get(fallback_field, "").strip():
                question[fallback_field] = fallback_value

    for index, question in enumerate(questions, start=1):
        if not isinstance(question, dict):
            raise ValueError(f"第 {index} 题不是对象")
        if not question.get("id"):
            question["id"] = f"Q{index}"
        for field in ["id", "type", "difficulty", "knowledge_point", "stem", "answer", "analysis"]:
            if not isinstance(question.get(field), str) or not question[field].strip():
                raise ValueError(f"第 {index} 题缺少有效 {field}")
        options = question.get("options", [])
        if not isinstance(options, list) or not all(isinstance(item, str) for item in options):
            raise ValueError(f"第 {index} 题的 options 格式无效")
        mistake_alert = question.get("mistake_alert", "")
        if mistake_alert is not None and not isinstance(mistake_alert, str):
            raise ValueError(f"第 {index} 题的 mistake_alert 格式无效")


STM32_F1_TECHNICAL_REPLACEMENTS = (
    (
        "SYSCFG_EXTILineConfig",
        "GPIO_EXTILineConfig",
        "STM32F1 标准外设库通过 AFIO/GPIO_EXTILineConfig 配置 EXTI 映射，不使用 SYSCFG_EXTILineConfig。",
    ),
    (
        "GPIO_InitStruct.GPIO_PuPd",
        "GPIO_InitStruct.GPIO_Mode",
        "STM32F1 标准外设库使用 GPIO_Mode_IPU/IPD 表示上下拉输入模式。",
    ),
    (
        "GPIO_PUPD_PULLUP",
        "GPIO_Mode_IPU",
        "STM32F1 标准外设库的上拉输入枚举为 GPIO_Mode_IPU。",
    ),
    (
        "GPIO_PUPD_PULLDOWN",
        "GPIO_Mode_IPD",
        "STM32F1 标准外设库的下拉输入枚举为 GPIO_Mode_IPD。",
    ),
)

UNSUPPORTED_TECHNICAL_TOKEN_PATTERN = re.compile(
    r"\b(?:[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+|[A-Za-z][A-Za-z0-9_]*->[A-Za-z0-9_]+|[A-Za-z][A-Za-z0-9_]+(?=\s*\())"
)


def _safe_grounded_question(question_id: str, question_type: str, sequence: int) -> dict[str, Any]:
    normalized_type = normalize_question_type(question_type)
    variant = (max(1, sequence) - 1) % 5
    if normalized_type == "判断题":
        return {
            "id": question_id,
            "type": normalized_type,
            "difficulty": "基础",
            "knowledge_point": "STM32F103 架构",
            "stem": "STM32F103 采用 ARM Cortex-M3 内核，最高系统主频可达 72MHz。",
            "options": [],
            "answer": "正确",
            "analysis": "课程知识库的 STM32F103 架构章节明确给出 Cortex-M3 内核和最高 72MHz 主频。[KB1]",
            "mistake_alert": "不要把 STM32F1 与采用 Cortex-M4 的 STM32F4 混淆。",
        }
    if normalized_type == "多选题":
        return {
            "id": question_id,
            "type": normalized_type,
            "difficulty": "基础",
            "knowledge_point": "嵌入式调试工具",
            "stem": "调试 STM32 GPIO 运行异常时，哪些工具或方法可以提供可观察证据？",
            "options": ["A. ST-Link 断点与单步", "B. LED 状态指示", "C. 逻辑分析仪或示波器", "D. 不记录现象直接修改代码"],
            "answer": "A、B、C",
            "analysis": "课程知识库列出了 ST-Link、LED 指示、逻辑分析仪和示波器等调试手段。[KB1]",
            "mistake_alert": "调试应先保留现象和证据，再缩小问题范围。",
        }
    if normalized_type == "填空题":
        return {
            "id": question_id,
            "type": normalized_type,
            "difficulty": "基础",
            "knowledge_point": "STM32F103 时钟",
            "stem": "STM32F103 的最高系统主频为 ____ MHz。",
            "options": [],
            "answer": "72",
            "analysis": "课程知识库的 STM32F103 时钟系统部分给出系统时钟最高 72MHz。[KB1]",
            "mistake_alert": "不要把 APB1 的最高 36MHz 与系统主频混淆。",
        }
    if normalized_type in {"简答题", "综合题"}:
        return {
            "id": question_id,
            "type": normalized_type,
            "difficulty": "提升",
            "knowledge_point": "GPIO 调试流程",
            "stem": "GPIO 实验没有出现预期电平变化时，请给出一套由硬件到软件的排查顺序。",
            "options": [],
            "answer": "依次检查电源与接线、时钟和复位、程序是否正确下载、引脚配置、运行状态与测量证据。",
            "analysis": "该顺序来自课程知识库的最小系统与常见问题调试方法，先验证基础条件，再检查配置和运行现象。[KB1]",
            "mistake_alert": "不要在没有测量证据时同时修改多处配置。",
        }
    single_variants = [
        (
            "GPIO 实验没有输出时，最合理的第一步是什么？",
            ["A. 检查电源、时钟、复位和程序下载", "B. 立即更换所有外设", "C. 删除调试信息", "D. 跳过现象记录"],
            "A",
            "课程知识库建议程序不运行时先检查电源、时钟、复位和下载状态。[KB1]",
        ),
        (
            "下列哪种工具适合观察 GPIO 数字电平随时间的变化？",
            ["A. 逻辑分析仪", "B. 文本编辑器", "C. 版本控制日志", "D. 压缩软件"],
            "A",
            "逻辑分析仪可分析数字信号并进行协议解码，适合观察 GPIO 时序。[KB1]",
        ),
        (
            "STM32F103 使用的处理器内核是：",
            ["A. Cortex-M0", "B. Cortex-M3", "C. Cortex-M4", "D. Cortex-M7"],
            "B",
            "课程知识库明确说明 STM32F103 属于 STM32F1 系列并采用 Cortex-M3 内核。[KB1]",
        ),
        (
            "完成 GPIO 调试后，哪项记录最有利于后续复盘？",
            ["A. 问题现象、复现步骤、修正方法和验证结果", "B. 只记录最终代码", "C. 只记录日期", "D. 不保留记录"],
            "A",
            "课程知识库的调试文档部分要求记录问题描述、复现步骤、解决方法和调试过程。[KB1]",
        ),
        (
            "STM32CubeMX 在 GPIO 学习流程中的主要作用是：",
            ["A. 图形化配置引脚并生成初始化代码", "B. 替代示波器测量", "C. 自动焊接电路", "D. 替代所有调试器"],
            "A",
            "课程知识库说明 STM32CubeMX 用于图形化配置引脚、时钟和外设，并生成初始化代码。[KB1]",
        ),
    ]
    stem, options, answer, analysis = single_variants[variant]
    return {
        "id": question_id,
        "type": normalized_type or "单选题",
        "difficulty": "基础" if variant < 3 else "提升",
        "knowledge_point": "GPIO 配置与调试",
        "stem": stem,
        "options": options,
        "answer": answer,
        "analysis": analysis,
        "mistake_alert": "依据可观察证据逐步排查，不要凭猜测同时修改多项配置。",
    }


def normalize_question_bank_technical_consistency(
    question_bank: dict[str, Any],
    payload: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Correct a small set of deterministic STM32-family API conflicts."""
    payload = payload if isinstance(payload, dict) else {}
    corrections: list[dict[str, str]] = []
    grounded_source = " ".join(
        [
            str(payload.get("resource_plan_result") or ""),
            str(payload.get("source_original_text") or ""),
        ]
    )
    for index, question in enumerate(question_bank.get("questions") or [], start=1):
        if not isinstance(question, dict):
            continue
        question_id = str(question.get("id") or f"Q{index}")
        searchable = " ".join(
            [
                str(payload.get("course_name") or ""),
                str(payload.get("target_topic") or ""),
                str(question.get("stem") or ""),
                " ".join(str(item) for item in (question.get("options") or [])),
                str(question.get("analysis") or ""),
            ]
        ).lower()
        is_stm32_f1 = any(marker in searchable for marker in ("stm32f1", "stm32f103", "f103"))
        if is_stm32_f1:
            for source, target, reason in STM32_F1_TECHNICAL_REPLACEMENTS:
                changed = False
                for field in ("stem", "answer", "analysis", "mistake_alert"):
                    value = question.get(field)
                    if isinstance(value, str) and source in value:
                        question[field] = value.replace(source, target)
                        changed = True
                options = question.get("options")
                if isinstance(options, list):
                    normalized_options = []
                    for option in options:
                        text = str(option)
                        if source in text:
                            text = text.replace(source, target)
                            changed = True
                        normalized_options.append(text)
                    question["options"] = normalized_options
                if changed:
                    corrections.append(
                        {
                            "questionId": question_id,
                            "from": source,
                            "to": target,
                            "reason": reason,
                        }
                    )

        rendered_question = " ".join(
            [
                str(question.get("stem") or ""),
                " ".join(str(item) for item in (question.get("options") or [])),
                str(question.get("answer") or ""),
                str(question.get("analysis") or ""),
            ]
        )
        unsupported_tokens = sorted(
            {
                token
                for token in UNSUPPORTED_TECHNICAL_TOKEN_PATTERN.findall(rendered_question)
                if token not in grounded_source
            }
        )
        if unsupported_tokens:
            replacement = _safe_grounded_question(
                question_id,
                str(question.get("type") or "单选题"),
                index,
            )
            question.clear()
            question.update(replacement)
            corrections.append(
                {
                    "questionId": question_id,
                    "from": "、".join(unsupported_tokens[:8]),
                    "to": "knowledge-grounded-safe-question",
                    "reason": "题目包含课程知识库原文未支持的函数或寄存器标识，已替换为可核验题目。",
                }
            )

    question_bank["technical_corrections"] = corrections
    return corrections


def call_mimo_for_question_json(payload: dict[str, Any], on_delta=None, on_stage=None) -> dict[str, Any]:
    api_key = get_mimo_api_key(payload)
    if not api_key:
        raise ValueError("缺少 AI API Key，请通过环境变量或 backend/.env 配置 ANTHROPIC_AUTH_TOKEN")

    attempts = [dict(payload)]
    fallback_payload = dict(payload)
    fallback_payload["notes"] = (
        (fallback_payload.get("notes", "").strip() + "\n" if fallback_payload.get("notes") else "")
        + "上一轮若题型数量不匹配，请修正为完全符合 question_type_counts；保持用户要求的题量与题型分布，优先保证 JSON 完整，适当缩短每题解析。"
    )
    attempts.append(fallback_payload)

    last_error: Exception | None = None
    last_result: dict[str, Any] | None = None
    debug_attempts: list[dict[str, Any]] = []
    model = get_mimo_model(payload)

    for attempt_index, attempt_payload in enumerate(attempts):
        user_prompt = build_question_json_prompt(attempt_payload)
        body = {
            "model": get_mimo_model(attempt_payload),
            "messages": [
                {"role": "system", "content": QUESTION_JSON_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": attempt_payload.get("temperature", 0.3 if attempt_index > 0 else 0.4),
            "max_tokens": attempt_payload.get("max_tokens", 4200 if attempt_index == 0 else 3200),
            "stream": bool(on_delta),
            "response_format": {"type": "json_object"},
        }
        debug_attempt = {
            "attempt": attempt_index + 1,
            "api_url": resolve_mimo_api_url(api_key, attempt_payload),
            "request_body": body,
            "requested_question_count": attempt_payload.get("question_count"),
            "question_type_counts": attempt_payload.get("question_type_counts", {}),
        }

        response = requests.post(
            debug_attempt["api_url"],
            headers={
                "api-key": api_key,
                "x-api-key": api_key,
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=120,
            stream=bool(on_delta),
        )
        debug_attempt["status_code"] = response.status_code
        if not response.ok:
            debug_attempt["response_text"] = response.text[:4000]
            debug_attempts.append(debug_attempt)
            raise StructuredContentError(f"MiMo API 调用失败：HTTP {response.status_code}", result={
                "debug_attempts": debug_attempts,
                "content": response.text[:4000],
                "model": model,
            })
        if on_delta:
            if on_stage:
                on_stage({"stage": "model_stream_start", "attempt": attempt_index + 1})
            content_parts: list[str] = []
            stream_raw: list[dict[str, Any]] = []
            usage: dict[str, Any] = {}
            response_model = model
            for line_bytes in response.iter_lines(decode_unicode=False):
                try:
                    line = line_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    line = line_bytes.decode("utf-8", errors="ignore")
                if not line:
                    continue
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                raw_data = line[5:].strip()
                if raw_data == "[DONE]":
                    break
                try:
                    chunk = json.loads(raw_data)
                except json.JSONDecodeError:
                    continue
                stream_raw.append(chunk)
                response_model = chunk.get("model", response_model)
                if chunk.get("usage"):
                    usage = chunk.get("usage") or {}
                choice = (chunk.get("choices") or [{}])[0]
                delta = choice.get("delta") or {}
                piece = delta.get("content") or (choice.get("message") or {}).get("content") or ""
                if piece:
                    content_parts.append(piece)
                    on_delta(piece)
            content = "".join(content_parts)
            data = {"model": response_model, "usage": usage, "stream_chunks": stream_raw[-20:]}
        else:
            data = response.json()
            choice = (data.get("choices") or [{}])[0]
            content = (choice.get("message") or {}).get("content", "")
            usage = data.get("usage", {})
        debug_attempt["response_json"] = data
        debug_attempt["raw_content"] = content
        debug_attempt["usage"] = usage
        last_result = {
            "model": data.get("model", model),
            "content": content,
            "usage": usage,
            "raw": data,
            "debug_attempts": debug_attempts,
        }

        try:
            parsed = parse_json_text(content)
            validate_question_json(parsed)
            expected_type_counts = attempt_payload.get("question_type_counts", {})
            if isinstance(expected_type_counts, dict) and len(expected_type_counts) == 1:
                expected_type, expected_count = next(iter(expected_type_counts.items()))
                questions = parsed.get("questions") or []
                if isinstance(expected_count, int) and expected_count > 0 and len(questions) > expected_count:
                    parsed["questions"] = questions[:expected_count]
                    questions = parsed["questions"]
                for question in questions:
                    question["type"] = expected_type
            validate_question_type_counts(parsed, expected_type_counts)
            last_result["parsed_content"] = parsed
            debug_attempt["parsed_question_count"] = len(parsed.get("questions") or [])
            debug_attempt["parse_status"] = "success"
            debug_attempts.append(debug_attempt)
            return last_result
        except (json.JSONDecodeError, ValueError) as exc:
            last_error = exc
            debug_attempt["parse_status"] = "failed"
            debug_attempt["parse_error"] = str(exc)
            debug_attempts.append(debug_attempt)

    fallback_result = _fallback_question_json_result(payload, str(last_error or "模型 JSON 解析失败"), last_result)
    fallback_result["debug_attempts"] = debug_attempts + [
        {
            "attempt": "local_fallback",
            "parse_status": "fallback",
            "parse_error": str(last_error or "模型 JSON 解析失败"),
            "parsed_question_count": len(fallback_result["parsed_content"].get("questions") or []),
        }
    ]
    if on_stage:
        on_stage({
            "stage": "local_fallback",
            "agent": "question_generator_fallback",
            "status": "done",
            "message": "模型返回的题库 JSON 不完整，已使用本地规则生成可用题单。",
            "question_count": len(fallback_result["parsed_content"].get("questions") or []),
        })
    return fallback_result


def build_task_plan_prompt(payload: dict[str, Any], normalized_counts: dict[str, int]) -> str:
    enabled_types = get_enabled_question_types(payload, normalized_counts)
    requested = "\n".join(
        f"- {question_type}: {normalized_counts.get(question_type, 0)} 题"
        for question_type in QUESTION_AGENT_TYPES
    )
    source_text = str(payload.get("source_original_text") or payload.get("resource_plan_result") or "")
    source_is_question_sheet = (
        str(payload.get("source_mode") or "") == "question_sheet"
        or looks_like_uploaded_question_sheet(source_text)
        or should_prioritize_original_questions(payload)
    )
    source_mode_hint = "上传题单/原题锚点资料" if source_is_question_sheet else "普通讲义/资料"
    return f"""请总结压缩资料，并给题型智能体写出题重点。不要分配题量。

课程名称：{payload["course_name"].strip()}
章节/主题：{payload["target_topic"].strip()}
学生画像：{payload.get("student_profile", "").strip() or "通用学生"}
学习目标：{payload.get("learning_objectives", "").strip() or "结合资料合理推断"}
额外要求：{payload.get("constraints", "").strip() or "无"}
资料类型判断：{source_mode_hint}

用户输入的题型与数量（只读，禁止修改）：
{requested}

目标题量：{int(payload.get("question_count") or 8)} 题
启用题型：{"、".join(enabled_types) or "无"}

资料文本：
{source_text.strip()[:12000]}

要求：
1. 你的职责只有总结压缩和写 instruction，不允许修改 count。
2. assignments 中可以只写 instruction；即使你输出 enabled/count，后端也会忽略。
3. compressed_context 控制在 2000 字以内；如果是原题资料，必须按编号保留尽可能多的原题题干锚点，不要只写知识点摘要。
4. 每个启用题型的 instruction 要明确知识点、难度覆盖、题目风格。
5. 如果是原题资料，每个启用题型的 instruction 必须包含：优先复用原题题干信息、可按题型改写但不得泛化、按用户配置数量生成。
6. 未启用题型可以不给 instruction，或说明“不派发”。"""


def get_enabled_question_types(payload: dict[str, Any], normalized_counts: dict[str, int]) -> list[str]:
    if normalized_counts:
        return [question_type for question_type in QUESTION_AGENT_TYPES if normalized_counts.get(question_type, 0) > 0]
    preferred = payload.get("preferred_question_types", [])
    if isinstance(preferred, list):
        enabled = [normalize_question_type(item) for item in preferred if normalize_question_type(item) in QUESTION_AGENT_TYPES]
        if enabled:
            return enabled
    return QUESTION_AGENT_TYPES[:]


def auto_allocate_counts(payload: dict[str, Any], enabled_types: list[str]) -> dict[str, int]:
    total = int(payload.get("question_count") or 8)
    total = max(1, min(total, 50))
    if not enabled_types:
        enabled_types = QUESTION_AGENT_TYPES[:]
    base = total // len(enabled_types)
    remainder = total % len(enabled_types)
    return {
        question_type: base + (1 if index < remainder else 0)
        for index, question_type in enumerate(enabled_types)
    }


def _fallback_knowledge_points(payload: dict[str, Any]) -> list[str]:
    text = " ".join(
        str(payload.get(key) or "")
        for key in ["target_topic", "learning_objectives", "resource_plan_result", "constraints"]
    )
    candidates = [
        "GPIO 输入输出",
        "STM32 外设时钟配置",
        "UART 串口通信",
        "中断优先级与 NVIC",
        "定时器 PWM",
        "寄存器与 HAL 初始化",
        "单片机仿真实验",
        "调试与故障排查",
    ]
    selected = [item for item in candidates if any(part.lower() in text.lower() for part in re.split(r"\s+|与|和", item) if part)]
    if not selected:
        topic = re.sub(r"\s+", " ", str(payload.get("target_topic") or "课程核心知识点")).strip()
        selected = [topic[:28] or "课程核心知识点", "基础概念理解", "实验操作与调试"]
    return selected[:6]


def _make_fallback_question(payload: dict[str, Any], question_type: str, sequence: int) -> dict[str, Any]:
    course = str(payload.get("course_name") or "嵌入式系统").strip()
    topic = re.sub(r"\s+", " ", str(payload.get("target_topic") or "课程复习").strip())
    topic_short = topic[:36] or "课程复习"
    points = _fallback_knowledge_points(payload)
    point = points[(sequence - 1) % len(points)]
    difficulty = ["基础", "提升", "综合"][(sequence - 1) % 3]
    base = {
        "id": f"Q{sequence}",
        "type": question_type,
        "difficulty": difficulty,
        "knowledge_point": point,
        "options": [],
        "mistake_alert": f"注意把 {point} 与具体实验现象对应起来，不要只背结论。",
    }
    if question_type == "单选题":
        base.update({
            "stem": f"在{course}的“{topic_short}”学习中，关于{point}的说法最合理的是哪一项？",
            "options": [
                f"A. 先确认{point}相关配置，再观察实验现象",
                "B. 可以跳过初始化步骤直接运行外设",
                "C. 出现异常时只需要重复下载程序",
                "D. 所有外设都不需要考虑时钟或引脚复用",
            ],
            "answer": "A",
            "analysis": f"{point}通常需要结合初始化配置、运行现象和调试记录一起判断。先确认关键配置，再定位现象，能减少盲目试错。",
        })
    elif question_type == "多选题":
        base.update({
            "stem": f"围绕{point}进行实验或复习时，哪些做法有助于完成“{topic_short}”任务？",
            "options": [
                "A. 核对初始化参数和引脚/外设映射",
                "B. 记录现象、假设和验证步骤",
                "C. 忽略报错信息，直接更换无关代码",
                "D. 将概念题、代码题和仿真实验串起来复盘",
            ],
            "answer": "A、B、D",
            "analysis": "配置核对、过程记录和跨资源复盘能形成稳定的学习闭环。忽略报错会让定位过程失去依据。",
        })
    elif question_type == "判断题":
        base.update({
            "stem": f"判断：学习{point}时，只要题目答案正确，就可以不做对应的仿真实验或调试记录。",
            "answer": "错误",
            "analysis": f"{point}既要理解概念，也要通过实验验证。仿真和调试记录能帮助发现配置遗漏和理解偏差。",
        })
    elif question_type == "填空题":
        base.update({
            "stem": f"在排查{point}相关问题时，建议按“配置检查 -> 现象记录 -> ______ -> 复盘总结”的顺序进行。",
            "answer": "对照资料或实验逐步验证",
            "analysis": "逐步验证能把问题限定在更小范围，避免只凭感觉修改代码。",
        })
    elif question_type == "简答题":
        base.update({
            "stem": f"简述在“{topic_short}”任务中学习{point}时，应如何结合课件、思维导图、题单和实验资源。",
            "answer": "先用课件把核心概念过一遍，再用思维导图梳理关系；随后通过题单检查薄弱点，最后进入实验或仿真验证配置和现象。",
            "analysis": "这一路径从理解、结构化、检测到实践，能把知识点从记忆推进到可操作能力。",
        })
    elif question_type == "计算题":
        base.update({
            "stem": f"某同学计划用 2 次课完成{point}复习，每次 45 分钟，其中课件学习占 30%，题单训练占 40%，实验验证占 30%。请计算题单训练总时长。",
            "answer": "36 分钟",
            "analysis": "总时长为 2 x 45 = 90 分钟，题单训练占 40%，所以 90 x 40% = 36 分钟。",
        })
    else:
        base.update({
            "stem": f"综合应用：为“{topic_short}”设计一个围绕{point}的学习闭环任务，要求包含资源使用顺序、检查点和实验验证方式。",
            "answer": "可按 PPT 概念学习、思维导图梳理、题单自测、单片机仿真实验、错题复盘的顺序设计；检查点包括关键配置是否能解释、题单正确率、实验现象是否符合预期。",
            "analysis": "综合应用题强调把多个资源组合成可执行计划，并用实验现象和错题复盘验证学习效果。",
        })
    return base


def build_local_question_bank(payload: dict[str, Any], expected_counts: Any = None, reason: str = "") -> dict[str, Any]:
    normalized_counts = normalize_question_type_counts(expected_counts or payload.get("question_type_counts", {}))
    enabled = get_enabled_question_types(payload, normalized_counts)
    effective_counts = normalized_counts or auto_allocate_counts(payload, enabled)
    questions: list[dict[str, Any]] = []
    sequence = 1
    for question_type in QUESTION_AGENT_TYPES:
        count = int(effective_counts.get(question_type) or 0)
        for _ in range(count):
            questions.append(_make_fallback_question(payload, question_type, sequence))
            sequence += 1
    if not questions:
        questions.append(_make_fallback_question(payload, "单选题", 1))
    question_bank = {
        "title": f"{payload.get('course_name', '课程')} - {payload.get('target_topic', '练习')} 练习题",
        "course_name": str(payload.get("course_name") or "课程"),
        "target_topic": str(payload.get("target_topic") or "练习"),
        "summary": clean_summary(f"本套题由本地规则兜底生成，用于覆盖核心概念、易错点与实验验证。{reason}"),
        "questions": questions,
    }
    validate_question_json(question_bank)
    validate_question_type_counts(question_bank, effective_counts)
    return question_bank


def _fallback_question_json_result(payload: dict[str, Any], reason: str, previous: dict[str, Any] | None = None) -> dict[str, Any]:
    question_bank = build_local_question_bank(payload, payload.get("question_type_counts", {}), reason)
    result = dict(previous or {})
    result.update({
        "model": result.get("model") or get_mimo_model(payload),
        "content": result.get("content") or "",
        "usage": result.get("usage") or {},
        "raw": result.get("raw") or {},
        "parsed_content": question_bank,
        "fallback_reason": reason,
        "source": "local-fallback",
    })
    return result


def fallback_task_plan(payload: dict[str, Any], normalized_counts: dict[str, int]) -> dict[str, Any]:
    resource_text = re.sub(r"\s+", " ", str(payload.get("resource_plan_result", ""))).strip()
    compressed_context = resource_text[:1200]
    effective_counts = normalized_counts or auto_allocate_counts(payload, get_enabled_question_types(payload, normalized_counts))
    return {
        "compressed_context": compressed_context,
        "task_summary": f"围绕 {payload.get('course_name', '')} - {payload.get('target_topic', '')} 生成分题型练习题。",
        "assignments": {
            question_type: {
                "enabled": effective_counts.get(question_type, 0) > 0,
                "count": int(effective_counts.get(question_type, 0)),
                "instruction": (
                    f"生成 {effective_counts.get(question_type, 0)} 道{question_type}，覆盖基础、提升、综合难度。"
                    if effective_counts.get(question_type, 0) > 0
                    else "用户未要求该题型，本轮不派发。"
                ),
            }
            for question_type in QUESTION_AGENT_TYPES
        },
    }


def looks_like_uploaded_question_sheet(text: str) -> bool:
    content = str(text or "")
    numbered = len(re.findall(r"(?m)^\s*\d+\s*[\.、)]\s*\S+", content))
    answers = len(re.findall(r"(答案|正确答案|解析|我的答案|A\.|B\.|C\.|D\.)", content, flags=re.I))
    return numbered >= 3 and answers >= 2


def build_source_context_for_agent(payload: dict[str, Any], task_plan: dict[str, Any] | None = None) -> str:
    original = str(payload.get("source_original_text") or "").strip()
    resource = str(payload.get("resource_plan_result") or "").strip()
    compressed = str((task_plan or {}).get("compressed_context") or "").strip()
    source_mode = str(payload.get("source_mode") or "")
    if original and (source_mode == "question_sheet" or looks_like_uploaded_question_sheet(original)):
        return (
            "【原始上传题单/原题文本】\n"
            + original[:24000]
            + "\n\n【任务规划摘要】\n"
            + compressed[:2200]
            + "\n\n强制要求：如果原始文本中已经包含题目、选项、答案或解析，必须优先围绕原题的题干场景、数据、表达式、代码、选项知识点进行保留或改写；可以按用户配置改变题型，但不能只根据摘要另起炉灶。"
        )
    if compressed:
        return compressed
    return resource[:12000]


def _strip_answer_prefix(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = re.sub(r"^(正确答案|答案|我的答案)\s*[:：]\s*", "", text)
    return text.strip(" ;；。")


def extract_original_questions_from_sheet(text: str) -> list[dict[str, Any]]:
    content = str(text or "").replace("\r\n", "\n")
    section_type = ""
    blocks: list[tuple[str, str]] = []
    matches = list(re.finditer(r"(?m)^\s*(\d{1,3})\s*[\.、]\s*", content))
    if len(matches) < 3:
        return []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(content)
        blocks.append((match.group(1), content[start:end].strip()))

    questions: list[dict[str, Any]] = []
    for number, block in blocks:
        header_before = content[: content.find(block)]
        for title, qtype in [
            ("单选题", "单选题"),
            ("多选题", "多选题"),
            ("判断题", "判断题"),
            ("填空题", "填空题"),
            ("简答题", "简答题"),
            ("综合应用题", "综合应用题"),
            ("计算题", "计算题"),
        ]:
            if re.search(rf"{title}", block[:80]):
                section_type = qtype
                break
        if not section_type:
            recent = header_before[-300:]
            if "判断题" in recent:
                section_type = "判断题"
            elif "单选题" in recent:
                section_type = "单选题"
            else:
                section_type = "题目"

        qtype = section_type
        if "单选题" in block:
            qtype = "单选题"
        elif "多选题" in block:
            qtype = "多选题"
        elif "判断题" in block:
            qtype = "判断题"

        answer_match = re.search(r"正确答案\s*[:：]\s*([^\n;；]+(?:[;；][^\n]*)?)", block)
        if not answer_match:
            answer_match = re.search(r"答案\s*[:：]\s*([^\n;；]+)", block)
        answer = _strip_answer_prefix(answer_match.group(1) if answer_match else "")

        analysis = ""
        analysis_match = re.search(r"(?:答案解析|解析|AI讲解)\s*[:：]?\s*([\s\S]*?)(?:\n\s*\d+\s*[\.、]|\Z)", block)
        if analysis_match:
            analysis = re.sub(r"\s+", " ", analysis_match.group(1)).strip()[:400]
        score_match = re.search(r"(\d+(?:\.\d+)?)\s*分", block)
        score = float(score_match.group(1)) if score_match else 0.0

        cleaned = re.sub(r"^\s*\d+\s*[\.、]\s*", "", block, count=1)
        cleaned = re.sub(r"^[（(]?[^）)\s]{1,12}题[)）]?", "", cleaned).strip()
        cleaned = re.split(r"\n\s*我的答案\s*[:：]", cleaned)[0]
        cleaned = re.split(r"\n\s*正确答案\s*[:：]", cleaned)[0]
        option_matches = re.findall(r"(?m)^\s*([A-D])\s*[\.、]\s*(.+?)(?=\n\s*[A-D]\s*[\.、]|\n\s*(?:我的答案|正确答案|答案解析|解析|AI讲解)|\Z)", cleaned, flags=re.S)
        options = [f"{label}. {re.sub(r'\\s+', ' ', body).strip()}" for label, body in option_matches]
        stem = cleaned
        if option_matches:
            first_option = re.search(r"(?m)^\s*[A-D]\s*[\.、]", cleaned)
            if first_option:
                stem = cleaned[: first_option.start()]
        stem = re.sub(r"\s+", " ", stem).strip(" 。")
        if not stem or len(stem) < 4:
            continue
        questions.append({
            "id": f"ORIG{number}",
            "type": qtype,
            "difficulty": "原题",
            "knowledge_point": "原题抽取",
            "stem": stem,
            "options": options if qtype in {"单选题", "多选题", "判断题"} else [],
            "answer": answer or "见原题",
            "analysis": analysis or "该题来自用户上传题单，已按原题保留。",
            "score": score,
            "mistake_alert": "注意按原题答案与解析复习。",
            "source": "uploaded_original_question",
            "original_number": int(number),
        })
    return questions


def should_prioritize_original_questions(payload: dict[str, Any]) -> bool:
    text = " ".join(str(payload.get(key) or "") for key in ["constraints", "notes", "source_mode"])
    return payload.get("source_mode") == "question_sheet" or any(key in text for key in ["原题", "题单", "原卷", "原始题"])


def _question_score_for_type(question_type: str, source_question: dict[str, Any], payload: dict[str, Any]) -> float:
    scores = payload.get("question_type_scores") if isinstance(payload.get("question_type_scores"), dict) else {}
    for configured_type, configured_score in scores.items():
        if str(configured_type) in str(question_type) or str(question_type) in str(configured_type):
            try:
                return float(configured_score)
            except (TypeError, ValueError):
                break
    try:
        return float(source_question.get("score") or 0)
    except (TypeError, ValueError):
        return 0.0


def adapt_original_question_to_type(source_question: dict[str, Any], question_type: str, sequence: int, payload: dict[str, Any]) -> dict[str, Any]:
    original_type = normalize_question_type(source_question.get("type"))
    stem = re.sub(r"\s+", " ", str(source_question.get("stem") or "")).strip()
    answer = str(source_question.get("answer") or "见原题").strip()
    analysis = str(source_question.get("analysis") or "该题基于上传原题改写。").strip()
    options = list(source_question.get("options") or [])
    score = _question_score_for_type(question_type, source_question, payload)
    adapted = {
        "id": f"Q{sequence}",
        "type": question_type,
        "difficulty": source_question.get("difficulty") if source_question.get("difficulty") != "原题" else "中等",
        "knowledge_point": source_question.get("knowledge_point") or "原题改写",
        "stem": stem,
        "options": options,
        "answer": answer,
        "analysis": analysis,
        "mistake_alert": source_question.get("mistake_alert") or "注意题干中的限制条件。",
        "score": score,
        "source": "uploaded_original_question" if original_type == question_type else "uploaded_original_adapted",
        "original_number": source_question.get("original_number"),
        "original_type": original_type,
    }
    if original_type == question_type:
        return adapted
    if "填空" in question_type:
        adapted["stem"] = f"基于原题“{stem}”，请填空：本题考查的关键结论或正确结果是______。"
        adapted["options"] = []
        adapted["answer"] = answer
        adapted["analysis"] = f"本题由原{original_type}改写为填空题，核心题干信息来自原题：{analysis}"
    elif "简答" in question_type:
        adapted["stem"] = f"请围绕原题“{stem}”作答：说明本题涉及的核心概念、判断依据和解题过程。"
        adapted["options"] = []
        adapted["answer"] = answer
        adapted["analysis"] = f"本题由原{original_type}改写为简答题，需解释原题对应知识点与推理过程。{analysis}"
    elif "综合" in question_type or "应用" in question_type or "计算" in question_type:
        adapted["stem"] = f"综合分析原题场景：“{stem}”。请写出判断过程、关键步骤，并给出最终结论。"
        adapted["options"] = []
        adapted["answer"] = answer
        adapted["analysis"] = f"本题由原{original_type}扩展为综合应用题，核心数据和场景来自原题。{analysis}"
    elif "判断" in question_type:
        adapted["stem"] = f"判断正误：{stem}"
        adapted["options"] = ["A. 对", "B. 错"]
        adapted["answer"] = "对" if answer in {"A", "对", "正确", "是"} else "错"
        adapted["analysis"] = f"本题由原{original_type}改写为判断题，判断依据来自原题解析。{analysis}"
    elif "单选" in question_type or "多选" in question_type:
        adapted["stem"] = stem
        adapted["options"] = options
    return adapted


def call_mimo_for_task_plan(payload: dict[str, Any], normalized_counts: dict[str, int], on_stage=None) -> dict[str, Any]:
    api_key = get_mimo_api_key(payload)
    if not api_key:
        raise ValueError("缺少 AI API Key，请通过环境变量或 backend/.env 配置 ANTHROPIC_AUTH_TOKEN")

    body = {
        "model": get_mimo_model(payload),
        "messages": [
            {"role": "system", "content": TASK_PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": build_task_plan_prompt(payload, normalized_counts)},
        ],
        "temperature": payload.get("planner_temperature", 0.2),
        "max_tokens": payload.get("planner_max_tokens", 1800),
        "response_format": {"type": "json_object"},
    }
    response = requests.post(
        resolve_mimo_api_url(api_key, payload),
        headers={
            "api-key": api_key,
            "x-api-key": api_key,
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=90,
    )
    if not response.ok:
        raise StructuredContentError(f"任务规划智能体调用失败：HTTP {response.status_code}", result={
            "content": response.text[:4000],
            "model": get_mimo_model(payload),
            "debug_attempts": [{"agent": "task_planner_agent", "status_code": response.status_code, "response_text": response.text[:4000]}],
        })

    data = response.json()
    content = ((data.get("choices") or [{}])[0].get("message") or {}).get("content", "")
    plan = parse_json_text(content)
    if not isinstance(plan.get("assignments"), dict):
        raise ValueError("任务规划结果缺少 assignments")

    fallback = fallback_task_plan(payload, normalized_counts)
    assignments = fallback["assignments"]
    for question_type in QUESTION_AGENT_TYPES:
        raw = plan.get("assignments", {}).get(question_type, {})
        fallback_count = int(assignments[question_type]["count"])
        planned_count = fallback_count
        enabled = planned_count > 0
        assignments[question_type] = {
            "enabled": enabled,
            "count": planned_count if enabled else 0,
            "instruction": str(raw.get("instruction") or assignments[question_type]["instruction"]),
        }
    plan["assignments"] = assignments
    plan["compressed_context"] = str(plan.get("compressed_context") or fallback["compressed_context"])[:2200]
    plan["task_summary"] = str(plan.get("task_summary") or fallback["task_summary"])
    if on_stage:
        on_stage({
            "stage": "agent_output",
            "agent": "task_planner_agent",
            "status": "done",
            "message": "任务规划智能体已完成资料压缩与题型任务分配。",
            "output": plan,
        })
    return {
        "model": data.get("model", get_mimo_model(payload)),
        "usage": data.get("usage", {}),
        "plan": plan,
        "raw_content": content,
    }


def validate_question_type_counts(data: dict[str, Any], expected_counts: Any) -> None:
    if not isinstance(expected_counts, dict) or not expected_counts:
        return

    normalized_expected = normalize_question_type_counts(expected_counts)
    if not normalized_expected:
        return

    questions = data.get("questions") or []
    for item in questions:
        if isinstance(item, dict):
            item["type"] = normalize_question_type(item.get("type"))
    actual_counts = {
        question_type: sum(1 for item in questions if item.get("type") == question_type)
        for question_type in normalized_expected
    }
    if actual_counts != normalized_expected:
        raise ValueError(f"题型数量不匹配，期望 {normalized_expected}，实际 {actual_counts}")


def clean_summary(summary: str) -> str:
    parts: list[str] = []
    for block in re.split(r"(?<=[\u3002\uff01\uff1f!?])\s*", str(summary or "").strip()):
        for index, item in enumerate(re.split(r"\s+\u672c\u5957\u9898", block)):
            if not item:
                continue
            parts.append(("\u672c\u5957\u9898" + item) if index > 0 else item)

    unique_parts: list[str] = []
    seen_tokens: list[set[str]] = []
    for part in parts:
        text = re.sub(r"\s+", " ", part).strip()
        if not text:
            continue
        key = re.sub(r"[\uff0c\u3002\uff01\uff1f\u3001\uff1b\uff1a,.!?;:\s]", "", text)
        if not key:
            continue
        tokens = set(re.findall(r"[\u4e00-\u9fa5]{2}", key))
        duplicate = False
        for old_tokens in seen_tokens:
            overlap = len(tokens & old_tokens)
            base = max(1, min(len(tokens), len(old_tokens)))
            if overlap / base > 0.55:
                duplicate = True
                break
        if duplicate:
            continue
        seen_tokens.append(tokens)
        unique_parts.append(text)
        if len(unique_parts) >= 1 or len(" ".join(unique_parts)) >= 180:
            break
    return " ".join(unique_parts)[:220]


class QuestionGraphState(TypedDict, total=False):
    payload: dict[str, Any]
    normalized_counts: dict[str, int]
    enabled_question_types: list[str]
    parsed_text: str
    task_plan: dict[str, Any]
    question_type: str
    count: int
    batches: Annotated[list[dict[str, Any]], operator.add]
    result: dict[str, Any]


def _build_question_generator_graph(question_type_counts: dict[str, int] | None = None, on_delta=None, on_stage=None):
    def planned_counts_from_task_plan(task_plan: dict[str, Any]) -> dict[str, int]:
        assignments = task_plan.get("assignments") if isinstance(task_plan, dict) else {}
        if not isinstance(assignments, dict):
            return {}
        planned_counts: dict[str, int] = {}
        for question_type in QUESTION_AGENT_TYPES:
            assignment = assignments.get(question_type, {})
            if not isinstance(assignment, dict):
                continue
            try:
                count = int(assignment.get("count") or 0)
            except (TypeError, ValueError):
                count = 0
            if count > 0:
                planned_counts[question_type] = count
        return planned_counts

    def parse_documents_to_text(state: QuestionGraphState) -> dict[str, Any]:
        payload = state["payload"]
        parsed_text = str(payload.get("resource_plan_result", ""))
        if on_stage:
            on_stage({
                "stage": "agent_output",
                "agent": "document_parser_agent",
                "status": "done",
                "message": "文档解析智能体已完成文本抽取并组合为题库输入 JSON。",
                "output": {
                    "course_name": payload.get("course_name"),
                    "target_topic": payload.get("target_topic"),
                    "text_length": len(parsed_text),
                    "question_type_counts": state["normalized_counts"],
                },
            })
        return {"parsed_text": parsed_text}

    def summarize_and_plan(state: QuestionGraphState) -> dict[str, Any]:
        if on_stage:
            on_stage({
                "stage": "agent_start",
                "agent": "task_planner_agent",
                "status": "running",
                "message": "总结压缩智能体正在压缩资料并分配各题型任务。",
            })
        try:
            plan_result = call_mimo_for_task_plan(state["payload"], state["normalized_counts"], on_stage=on_stage)
            plan = plan_result["plan"]
        except Exception as exc:
            # Planner JSON can be malformed even when generation is usable; fall back to deterministic assignment.
            plan = fallback_task_plan(state["payload"], state["normalized_counts"])
            if on_stage:
                on_stage({
                    "stage": "agent_output",
                    "agent": "task_planner_agent",
                    "status": "fallback",
                    "message": f"任务规划智能体输出不完整，已使用本地规则继续分配题型：{exc}",
                    "output": plan,
                })
        updates: dict[str, Any] = {"task_plan": plan}
        if not state["normalized_counts"]:
            planned_counts = planned_counts_from_task_plan(plan)
            if not planned_counts:
                raise ValueError("任务规划智能体未分配任何题型数量")
            updates["normalized_counts"] = planned_counts
        return updates

    def prepare_batches(state: QuestionGraphState) -> dict[str, Any]:
        planned_counts = state["normalized_counts"]
        if on_stage:
            on_stage({
                "stage": "langgraph_prepare",
                "agent": "route_by_requested_types",
                "message": "按用户题型配置判断启用智能体，只向数量大于 0 的题型派发任务。",
                "question_type_counts": planned_counts,
                "enabled_agents": [question_type_agent_node_name(qt) for qt, count in planned_counts.items() if count > 0],
            })
        return {"batches": []}

    def route_question_types(state: QuestionGraphState) -> list[Send]:
        return [
            Send(
                question_type_agent_node_name(question_type),
                {
                    "payload": state["payload"],
                    "normalized_counts": state["normalized_counts"],
                    "task_plan": state.get("task_plan", {}),
                    "question_type": question_type,
                    "count": count,
                },
            )
            for question_type, count in state["normalized_counts"].items()
            if count > 0
        ]

    def run_question_type_agent(state: QuestionGraphState, fixed_question_type: str | None = None) -> dict[str, Any]:
        payload = state["payload"]
        question_type = fixed_question_type or state["question_type"]
        agent_name = question_type_agent_node_name(question_type)
        agent_label = question_type_agent_label(question_type)
        task_plan = state.get("task_plan") or {}
        assignment = (task_plan.get("assignments") or {}).get(question_type, {})
        count = int((state.get("normalized_counts") or {}).get(question_type) or state.get("count") or 0)
        if count <= 0:
            if on_stage:
                on_stage({
                    "stage": "agent_skip",
                    "agent": agent_name,
                    "status": "idle",
                    "question_type": question_type,
                    "count": 0,
                    "message": f"{agent_label}未被用户要求，本轮不派发。",
                })
            return {"batches": []}
        sub_payload = dict(payload)
        sub_payload["preferred_question_types"] = [question_type]
        sub_payload["question_type_counts"] = {question_type: count}
        sub_payload["question_count"] = count
        sub_payload["resource_plan_result"] = build_source_context_for_agent(payload, task_plan)
        sub_payload["notes"] = (
            (sub_payload.get("notes", "").strip() + "\n" if sub_payload.get("notes") else "")
            + f"强制要求：本批次由{question_type}智能体生成，必须且只能生成 {count} 题；不得少于 {count} 题，不得多于 {count} 题；questions 数组长度必须等于 {count}；type 字段必须全部写成“{question_type}”。"
            + f"\n如果资料不足，也必须围绕压缩资料合理生成满 {count} 题，不能自行改成 1 题。"
            + "\n如果输入资料是上传题单/原题文本，必须优先围绕原题编号、题干数据、代码、表达式、选项知识点和答案解析生成相似题；可以改题型，但不能只生成泛化概念题。"
            + f"\n任务分配要求：{assignment.get('instruction', '')}"
        )
        if on_stage:
            on_stage({
                "stage": "agent_start",
                "agent": agent_name,
                "status": "running",
                "question_type": question_type,
                "count": count,
                "message": f"{agent_label}开始生成 {count} 题。",
                "output": {"instruction": assignment.get("instruction", "")},
            })
        def agent_delta(piece: str):
            if on_delta:
                on_delta(piece, {
                    "agent": agent_name,
                    "question_type": question_type,
                    "count": count,
                })

        result = call_mimo_for_question_json(sub_payload, on_delta=agent_delta if on_delta else None, on_stage=on_stage)
        if on_stage:
            on_stage({
                "stage": "agent_output",
                "agent": agent_name,
                "status": "done",
                "question_type": question_type,
                "count": count,
                "message": f"{agent_label}已完成 {count} 题。",
                "output": result["parsed_content"],
            })
        return {"batches": [{"question_type": question_type, "count": count, "result": result}]}

    def build_specific_question_agent_node(question_type: str):
        agent_fn = QUESTION_TYPE_AGENT_FUNCTIONS.get(question_type)

        def _node(state: QuestionGraphState) -> dict[str, Any]:
            if agent_fn:
                return agent_fn(state, run_question_type_agent)
            return run_question_type_agent(state, question_type)

        _node.__name__ = question_type_agent_node_name(question_type)
        return _node

    def aggregate_batches(state: QuestionGraphState) -> dict[str, Any]:
        payload = state["payload"]
        normalized_counts = state["normalized_counts"]
        batches = sorted(
            state.get("batches", []),
            key=lambda item: list(normalized_counts).index(item["question_type"]),
        )

        all_questions: list[dict[str, Any]] = []
        all_attempts: list[dict[str, Any]] = []
        usage: dict[str, int] = {}
        model = ""
        title = ""
        summary_parts: list[str] = []

        for batch in batches:
            result = batch["result"]
            model = model or result["model"]
            for key, value in (result.get("usage") or {}).items():
                if isinstance(value, int):
                    usage[key] = usage.get(key, 0) + value
            bank = result["parsed_content"]
            title = title or bank.get("title", "")
            if bank.get("summary"):
                summary_parts.append(str(bank["summary"]))
            all_attempts.extend(result.get("debug_attempts", []))
            all_questions.extend(bank.get("questions", []))

        for index, question in enumerate(all_questions, start=1):
            question["id"] = f"Q{index}"

        question_bank = {
            "title": title or f"{payload['course_name']} - {payload['target_topic']} 练习题",
            "course_name": payload["course_name"],
            "target_topic": payload["target_topic"],
            "summary": clean_summary(" ".join(summary_parts)),
            "questions": all_questions,
        }
        validate_question_type_counts(question_bank, normalized_counts)
        source_text = str(payload.get("source_original_text") or payload.get("resource_plan_result") or "")
        source_is_question_sheet = (
            str(payload.get("source_mode") or "") == "question_sheet"
            or looks_like_uploaded_question_sheet(source_text)
            or should_prioritize_original_questions(payload)
        )
        original_count = len(question_bank.get("questions", [])) if source_is_question_sheet else 0

        parsed_type_counts = {
            question_type: sum(1 for item in question_bank.get("questions", []) if item.get("type") == question_type)
            for question_type in sorted({item.get("type", "") for item in question_bank.get("questions", [])})
            if question_type
        }
        result_payload = {
            "message": "结构化题库生成成功",
            "model": model,
            "usage": usage,
            "question_bank": question_bank,
            "question_count": len(question_bank.get("questions", [])),
            "debug": {
                "agent": "question-generator",
                "framework": "langgraph",
                "mode": "langgraph-parallel-by-question-type",
                "backend_payload": payload,
                "system_prompt": QUESTION_JSON_SYSTEM_PROMPT,
                "attempts": all_attempts,
                "parsed_question_count": len(question_bank.get("questions", [])),
                "parsed_type_counts": parsed_type_counts,
                "original_question_count": original_count,
                "original_question_strategy": "llm_agent_prompted_original_anchor" if source_is_question_sheet else "none",
            },
        }
        if on_stage:
            on_stage({"stage": "langgraph_aggregate", "question_count": len(question_bank.get("questions", [])), "original_question_count": original_count})
        return {"result": result_payload}

    workflow = StateGraph(QuestionGraphState)
    workflow.add_node("document_parser_agent", parse_documents_to_text)
    workflow.add_node("task_planner_agent", summarize_and_plan)
    workflow.add_node("route_by_requested_types", prepare_batches)
    workflow.add_node("aggregate_batches", aggregate_batches)
    workflow.add_edge(START, "document_parser_agent")
    workflow.add_edge("document_parser_agent", "task_planner_agent")
    workflow.add_edge("task_planner_agent", "route_by_requested_types")
    question_agent_nodes = []
    for question_type in QUESTION_AGENT_TYPES:
        node_name = question_type_agent_node_name(question_type)
        question_agent_nodes.append(node_name)
        workflow.add_node(node_name, build_specific_question_agent_node(question_type))
        workflow.add_edge(node_name, "aggregate_batches")
    workflow.add_conditional_edges("route_by_requested_types", route_question_types, question_agent_nodes)
    workflow.add_edge("aggregate_batches", END)
    return workflow.compile()


def _build_runtime_workflow_mermaid(question_type_counts: dict[str, int | None]) -> str:
    lines = [
        "---",
        "config:",
        "  flowchart:",
        "    curve: linear",
        "---",
        "graph TD;",
        '    __start__([START]):::first',
        '    document_parser_agent["document_parser_agent<br/>解析文档/输入文本"]',
        '    task_planner_agent["task_planner_agent<br/>总结压缩/任务分配"]',
        '    route_by_requested_types{"route_by_requested_types<br/>是否启用该题型？"}',
    ]
    for index, (question_type, count) in enumerate(question_type_counts.items(), start=1):
        safe_label = str(question_type).replace('"', "'")
        node_name = question_type_agent_node_name(question_type)
        count_label = f"{safe_label} × {count}题" if count else "题量由任务规划智能体分配"
        lines.append(f'    {node_name}["{node_name}<br/>{count_label}"]')
    lines.extend([
        '    aggregate_batches["aggregate_batches<br/>汇总题库/校验数量"]',
        '    __end__([END]):::last',
        "    __start__ --> document_parser_agent;",
        "    document_parser_agent --> task_planner_agent;",
        "    task_planner_agent --> route_by_requested_types;",
    ])
    for question_type in question_type_counts:
        lines.append(f"    route_by_requested_types --> {question_type_agent_node_name(question_type)};")
    for question_type in question_type_counts:
        lines.append(f"    {question_type_agent_node_name(question_type)} --> aggregate_batches;")
    lines.extend([
        "    aggregate_batches --> __end__;",
        "    classDef default fill:#f2f0ff,stroke:#7868e6,line-height:1.2",
        "    classDef first fill:#e8fff4,stroke:#1c9b5f",
        "    classDef last fill:#fff3d6,stroke:#d48a00",
    ])
    return "\n".join(lines) + "\n"


def _draw_workflow_png_with_pillow(question_type_counts: dict[str, int | None], output_path: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    width = 1500
    branch_count = len(QUESTION_AGENT_TYPES)
    height = max(760, 260 + branch_count * 110)
    image = Image.new("RGB", (width, height), "#f7fbfb")
    draw = ImageDraw.Draw(image)

    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    font_path = next((path for path in font_paths if Path(path).exists()), None)
    title_font = ImageFont.truetype(font_path, 30) if font_path else ImageFont.load_default()
    font = ImageFont.truetype(font_path, 21) if font_path else ImageFont.load_default()
    small_font = ImageFont.truetype(font_path, 17) if font_path else ImageFont.load_default()

    def box(x: int, y: int, w: int, h: int, text: str, fill: str = "#ffffff", outline: str = "#7ccfcb"):
        draw.rounded_rectangle((x, y, x + w, y + h), radius=12, fill=fill, outline=outline, width=2)
        lines = text.split("\n")
        line_height = 28
        top = y + (h - line_height * len(lines)) / 2
        for offset, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            draw.text((x + (w - (bbox[2] - bbox[0])) / 2, top + offset * line_height), line, fill="#143533", font=font)

    def arrow(start: tuple[int, int], end: tuple[int, int]):
        draw.line((start, end), fill="#418c88", width=3)
        x1, y1 = start
        x2, y2 = end
        if abs(x2 - x1) > abs(y2 - y1):
            direction = 1 if x2 > x1 else -1
            points = [(x2, y2), (x2 - direction * 13, y2 - 7), (x2 - direction * 13, y2 + 7)]
        else:
            direction = 1 if y2 > y1 else -1
            points = [(x2, y2), (x2 - 7, y2 - direction * 13), (x2 + 7, y2 - direction * 13)]
        draw.polygon(points, fill="#418c88")

    draw.text((40, 28), "题库生成多智能体 LangGraph 实际工作流", fill="#143533", font=title_font)
    draw.text((42, 70), "图中七个题型智能体都是真实注册的 LangGraph 节点；运行时只派发到用户输入数量大于 0 的节点。", fill="#52706d", font=small_font)

    start = (70, 135, 150, 70)
    parser = (250, 120, 260, 100)
    planner = (620, 120, 280, 100)
    router = (1030, 120, 300, 100)
    aggregate = (620, height - 150, 280, 100)
    end = (1100, height - 135, 150, 70)

    box(*start, "START", fill="#e8fff4", outline="#1c9b5f")
    box(*parser, "document_parser_agent\n解析文档/文本")
    box(*planner, "task_planner_agent\n总结压缩/任务分配")
    box(*router, "route_by_requested_types\n按需判断派发", fill="#fff9e8", outline="#d48a00")
    box(*aggregate, "aggregate_batches\n汇总题库/校验数量", fill="#f2f0ff", outline="#7868e6")
    box(*end, "END", fill="#fff3d6", outline="#d48a00")

    arrow((start[0] + start[2], start[1] + start[3] // 2), (parser[0], parser[1] + parser[3] // 2))
    arrow((parser[0] + parser[2], parser[1] + parser[3] // 2), (planner[0], planner[1] + planner[3] // 2))
    arrow((planner[0] + planner[2], planner[1] + planner[3] // 2), (router[0], router[1] + router[3] // 2))
    arrow((aggregate[0] + aggregate[2], aggregate[1] + aggregate[3] // 2), (end[0], end[1] + end[3] // 2))

    left_x = 160
    branch_y = 285
    branch_w = 260
    branch_h = 72
    gap = 105
    for index, question_type in enumerate(QUESTION_AGENT_TYPES):
        y = branch_y + index * gap
        box(left_x, y, branch_w, branch_h, f"{question_type_agent_node_name(question_type)}\n按用户输入派发", fill="#ffffff", outline="#7ccfcb")
        arrow((router[0] + router[2] // 2, router[1] + router[3]), (left_x + branch_w // 2, y))
        arrow((left_x + branch_w, y + branch_h // 2), (aggregate[0], aggregate[1] + aggregate[3] // 2))

    image.save(output_path)


def _export_langgraph_workflow_image(graph, question_type_counts: dict[str, int | None] | None = None) -> dict[str, str]:
    output_dir = Path(__file__).resolve().parent / "data" / "langgraph"
    output_dir.mkdir(parents=True, exist_ok=True)
    png_path = output_dir / "question_generator_workflow.png"
    mermaid_path = output_dir / "question_generator_workflow.mmd"

    mermaid = graph.get_graph().draw_mermaid()
    mermaid_path.write_text(mermaid, encoding="utf-8")

    result = {"mermaid": str(mermaid_path)}
    try:
        graph.get_graph().draw_mermaid_png(output_file_path=str(png_path))
        result["png"] = str(png_path)
        print(f"LangGraph question-generator workflow image: {png_path}")
    except Exception as exc:
        print(f"LangGraph workflow PNG export failed, Mermaid source saved: {mermaid_path} ({exc})")
        if question_type_counts:
            _draw_workflow_png_with_pillow(question_type_counts, png_path)
            result["png"] = str(png_path)
            print(f"LangGraph question-generator workflow image rendered locally: {png_path}")
    return result


def _ground_question_payload(payload: dict[str, Any], on_stage=None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    grounded_payload = dict(payload)
    query = " ".join(
        [
            str(payload.get("course_name") or ""),
            str(payload.get("target_topic") or ""),
            str(payload.get("learning_objectives") or ""),
            "嵌入式系统 单片机 课程题库",
        ]
    )
    knowledge_context, knowledge_sources = grounded_prompt_block(query, top_k=7, max_context_chars=12000)
    existing = str(grounded_payload.get("resource_plan_result") or "").strip()
    grounded_payload["resource_plan_result"] = (
        f"{existing}\n\n课程知识库检索依据：\n{knowledge_context}".strip()
    )
    grounded_payload["knowledge_sources"] = knowledge_sources
    grounded_payload["constraints"] = (
        f"{str(grounded_payload.get('constraints') or '').strip()}\n"
        "题目中的定义、参数、结论和解析必须优先依据课程知识库，解析中使用 [KB1] 形式标注关键来源；"
        "资料不支持的具体事实必须标注需核验。"
    ).strip()
    if on_stage:
        on_stage(
            {
                "stage": "knowledge_retrieval",
                "agent": "course_knowledge_retrieval_agent",
                "status": "done",
                "message": f"课程知识库检索完成，命中 {len(knowledge_sources)} 条资料",
                "knowledge_source_count": len(knowledge_sources),
            }
        )
    return grounded_payload, knowledge_sources


def generate_question_bank(payload: dict[str, Any], on_delta=None, on_stage=None) -> dict[str, Any]:
    payload, knowledge_sources = _ground_question_payload(payload, on_stage=on_stage)
    errors = validate_payload(payload)
    if errors:
        raise ValueError("；".join(errors))

    expected_counts = normalize_question_type_counts(payload.get("question_type_counts", {}))
    if expected_counts:
        payload = dict(payload)
        payload["question_type_counts"] = expected_counts
        if isinstance(payload.get("preferred_question_types"), list):
            payload["preferred_question_types"] = [
                normalize_question_type(item)
                for item in payload["preferred_question_types"]
                if normalize_question_type(item) in QUESTION_AGENT_TYPES
            ]

        result = generate_question_bank_by_type(payload, expected_counts, on_delta=on_delta, on_stage=on_stage)
        result["knowledgeSources"] = knowledge_sources
        result["grounded"] = bool(knowledge_sources)
        if isinstance(result.get("question_bank"), dict):
            result["question_bank"]["knowledge_sources"] = knowledge_sources
            result["technicalCorrections"] = normalize_question_bank_technical_consistency(
                result["question_bank"], payload
            )
        return result

    preferred_types = payload.get("preferred_question_types", [])
    if isinstance(preferred_types, list) and preferred_types:
        result = generate_question_bank_by_type(payload, {}, on_delta=on_delta, on_stage=on_stage)
        result["knowledgeSources"] = knowledge_sources
        result["grounded"] = bool(knowledge_sources)
        if isinstance(result.get("question_bank"), dict):
            result["question_bank"]["knowledge_sources"] = knowledge_sources
            result["technicalCorrections"] = normalize_question_bank_technical_consistency(
                result["question_bank"], payload
            )
        return result

    result = call_mimo_for_question_json(payload, on_delta=on_delta, on_stage=on_stage)
    question_bank = result["parsed_content"]
    question_bank["summary"] = clean_summary(str(question_bank.get("summary", "")))
    technical_corrections = normalize_question_bank_technical_consistency(question_bank, payload)
    return {
        "message": "结构化题库生成成功",
        "model": result["model"],
        "usage": result["usage"],
        "question_bank": question_bank,
        "question_count": len(question_bank["questions"]),
        "knowledgeSources": knowledge_sources,
        "grounded": bool(knowledge_sources),
        "technicalCorrections": technical_corrections,
        "debug": {
            "agent": "question-generator",
            "backend_payload": payload,
            "system_prompt": QUESTION_JSON_SYSTEM_PROMPT,
            "attempts": result.get("debug_attempts", []),
            "parsed_question_count": len(question_bank["questions"]),
            "parsed_type_counts": {
                question_type: sum(1 for item in question_bank["questions"] if item.get("type") == question_type)
                for question_type in sorted({item.get("type", "") for item in question_bank["questions"]})
                if question_type
            },
        },
    }

def generate_question_bank_by_type(payload: dict[str, Any], expected_counts: dict[str, Any], on_delta=None, on_stage=None) -> dict[str, Any]:
    normalized_counts = normalize_question_type_counts(expected_counts)
    enabled_types = get_enabled_question_types(payload, normalized_counts)
    if not normalized_counts and not enabled_types:
        result = call_mimo_for_question_json(payload, on_delta=on_delta, on_stage=on_stage)
        question_bank = result["parsed_content"]
        return {
            "message": "结构化题库生成成功",
            "model": result["model"],
            "usage": result["usage"],
            "question_bank": question_bank,
            "question_count": len(question_bank["questions"]),
            "debug": {
                "agent": "question-generator",
                "backend_payload": payload,
                "system_prompt": QUESTION_JSON_SYSTEM_PROMPT,
                "attempts": result.get("debug_attempts", []),
                "parsed_question_count": len(question_bank["questions"]),
                "parsed_type_counts": {
                    question_type: sum(1 for item in question_bank["questions"] if item.get("type") == question_type)
                    for question_type in sorted({item.get("type", "") for item in question_bank["questions"]})
                    if question_type
                },
            },
        }

    graph_types = normalized_counts or {question_type: None for question_type in enabled_types}
    graph = _build_question_generator_graph(graph_types, on_delta=on_delta, on_stage=on_stage)
    workflow_images = _export_langgraph_workflow_image(graph, graph_types)
    try:
        state = graph.invoke({
            "payload": payload,
            "normalized_counts": normalized_counts,
            "enabled_question_types": enabled_types,
            "batches": [],
        })
    except Exception as exc:
        fallback_bank = build_local_question_bank(payload, normalized_counts, f"LangGraph 题型并联生成失败：{exc}")
        parsed_type_counts = {
            question_type: sum(1 for item in fallback_bank.get("questions", []) if item.get("type") == question_type)
            for question_type in normalize_question_type_counts(normalized_counts)
        }
        if on_stage:
            on_stage({
                "stage": "local_fallback",
                "agent": "question_generator_fallback",
                "status": "done",
                "message": "题型并联生成未完成，已使用本地规则生成可用题单。",
                "question_count": len(fallback_bank.get("questions", [])),
            })
        return {
            "message": "结构化题库生成成功（本地兜底）",
            "model": get_mimo_model(payload),
            "usage": {},
            "question_bank": fallback_bank,
            "question_count": len(fallback_bank.get("questions", [])),
            "data_source": "local_fallback_after_langgraph_error",
            "agent_runtime": "LangGraph question-generator multi-agent workflow",
            "debug": {
                "agent": "question-generator",
                "framework": "langgraph",
                "mode": "local-fallback-after-langgraph-error",
                "backend_payload": payload,
                "system_prompt": QUESTION_JSON_SYSTEM_PROMPT,
                "attempts": [],
                "parsed_question_count": len(fallback_bank.get("questions", [])),
                "parsed_type_counts": parsed_type_counts,
                "workflow_images": workflow_images,
                "fallback_reason": str(exc),
            },
        }

    result = state["result"]
    result.setdefault("debug", {})
    result["data_source"] = "real_langgraph_mimo_agent"
    result["agent_runtime"] = "LangGraph question-generator multi-agent workflow"
    result["debug"]["workflow_images"] = workflow_images
    result["debug"]["data_source"] = "real_langgraph_mimo_agent"
    result["debug"]["agent_runtime"] = "LangGraph question-generator multi-agent workflow"
    result["debug"]["langgraph_nodes"] = [
        "document_parser_agent",
        "task_planner_agent",
        "route_by_requested_types",
        *[question_type_agent_node_name(question_type) for question_type in QUESTION_AGENT_TYPES],
        "aggregate_batches",
    ]
    return result

    event_queue: queue.Queue[tuple[str, dict]] = queue.Queue()

    def thread_safe_delta(piece: str):
        event_queue.put(("delta", {"stage": "model_delta", "content": piece}))

    def thread_safe_stage(p: dict):
        event_queue.put(("progress", p))

    def generate_one(question_type: str, count: int) -> dict[str, Any]:
        sub_payload = dict(payload)
        sub_payload["preferred_question_types"] = [question_type]
        sub_payload["question_type_counts"] = {question_type: count}
        sub_payload["question_count"] = count
        sub_payload["notes"] = (
            (sub_payload.get("notes", "").strip() + "\n" if sub_payload.get("notes") else "")
            + f"本批次只生成 {question_type}，数量必须是 {count} 题，type 字段必须全部写成“{question_type}”。"
        )
        thread_safe_stage({"stage": "type_batch_start", "question_type": question_type, "count": count})
        result = call_mimo_for_question_json(sub_payload, on_delta=thread_safe_delta, on_stage=thread_safe_stage)
        return {"question_type": question_type, "count": count, "result": result}

    futures_list = []
    with ThreadPoolExecutor(max_workers=min(len(normalized_counts), 4)) as executor:
        for question_type, count in normalized_counts.items():
            futures_list.append(executor.submit(generate_one, question_type, count))

        # 主线程持续排空事件队列，直到所有 future 完成
        done_count = 0
        total = len(futures_list)
        while done_count < total:
            while True:
                try:
                    ev, payload_data = event_queue.get_nowait()
                    if on_delta and ev == "delta":
                        on_delta(payload_data.get("content", ""))
                    elif on_stage and ev == "progress":
                        on_stage(payload_data)
                except queue.Empty:
                    break
            done_now = sum(1 for f in futures_list if f.done())
            if done_now > done_count:
                done_count = done_now
                continue
            try:
                ev, payload_data = event_queue.get(timeout=0.15)
                if on_delta and ev == "delta":
                    on_delta(payload_data.get("content", ""))
                elif on_stage and ev == "progress":
                    on_stage(payload_data)
            except queue.Empty:
                pass

    # 排空剩余事件
    while True:
        try:
            ev, payload_data = event_queue.get_nowait()
            if on_delta and ev == "delta":
                on_delta(payload_data.get("content", ""))
            elif on_stage and ev == "progress":
                on_stage(payload_data)
        except queue.Empty:
            break

    # 收集结果
    all_questions: list[dict[str, Any]] = []
    all_attempts: list[dict[str, Any]] = []
    usage: dict[str, int] = {}
    model = ""
    title = ""
    summary_parts: list[str] = []

    for future in futures_list:
        try:
            batch = future.result()
        except Exception as exc:
            raise StructuredContentError(f"题型生成失败：{exc}") from exc
        result = batch["result"]
        model = model or result["model"]
        for key, value in (result.get("usage") or {}).items():
            if isinstance(value, int):
                usage[key] = usage.get(key, 0) + value
        bank = result["parsed_content"]
        title = title or bank.get("title", "")
        if bank.get("summary"):
            summary_parts.append(str(bank["summary"]))
        all_attempts.extend(result.get("debug_attempts", []))
        all_questions.extend(bank.get("questions", []))

    for index, question in enumerate(all_questions, start=1):
        question["id"] = f"Q{index}"

    question_bank = {
        "title": title or f"{payload['course_name']} - {payload['target_topic']} 练习题",
        "course_name": payload["course_name"],
        "target_topic": payload["target_topic"],
        "summary": clean_summary(" ".join(summary_parts)),
        "questions": all_questions,
    }
    validate_question_type_counts(question_bank, normalized_counts)

    parsed_type_counts = {
        question_type: sum(1 for item in all_questions if item.get("type") == question_type)
        for question_type in normalized_counts
    }
    return {
        "message": "结构化题库生成成功",
        "model": model,
        "usage": usage,
        "question_bank": question_bank,
        "question_count": len(all_questions),
        "debug": {
            "agent": "question-generator",
            "mode": "parallel-by-question-type",
            "backend_payload": payload,
            "system_prompt": QUESTION_JSON_SYSTEM_PROMPT,
            "attempts": all_attempts,
            "parsed_question_count": len(all_questions),
            "parsed_type_counts": parsed_type_counts,
        },
    }



