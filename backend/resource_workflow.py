"""Personalized resource generation workflow.

The workflow produces resources from real local state where possible:
- course handouts are generated from private knowledge-base excerpts,
- videos are discovered through web search,
- quiz resources are retrieved from generated question sheets,
- simulator resources point to existing MCU simulator experiments,
- mindmaps and PPT HTML are generated deterministically from the learning profile.
"""

from __future__ import annotations

import html
import json
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

try:
    from course_knowledge import retrieve_course_knowledge
    from question_generator_storage import list_question_sheets
except ImportError:  # pragma: no cover
    from .course_knowledge import retrieve_course_knowledge
    from .question_generator_storage import list_question_sheets


@dataclass
class ResourceContext:
    profile: dict[str, Any]
    route: dict[str, Any]
    question_sheets: list[dict[str, Any]]
    mcu_experiments: list[dict[str, Any]]
    knowledge: dict[str, Any]


DEFAULT_TOPICS = ["GPIO", "定时器", "串口通信", "中断系统", "C语言指针"]
VIDEO_DETAIL_CACHE_TTL_SECONDS = 6 * 60 * 60
VIDEO_DETAIL_FAILURE_TTL_SECONDS = 60
_VIDEO_DETAIL_CACHE: dict[str, tuple[float, dict[str, str]]] = {}

VIDEO_PLATFORM_TERMS = {
    "STM32": ("stm32", "stm 32"),
    "MSPM0": ("mspm0", "msp m0"),
    "Arduino": ("arduino",),
    "8051": ("8051", "51单片机", "51 单片机"),
    "ESP32": ("esp32", "esp 32"),
    "RP2040": ("rp2040", "raspberry pi pico"),
}

VIDEO_CONCEPT_TERMS = {
    "GPIO": ("gpio", "通用输入输出"),
    "时钟": ("时钟", "rcc"),
    "中断": ("中断", "exti", "nvic"),
    "定时器": ("定时器", "timer"),
    "PWM": ("pwm", "脉宽调制"),
    "串口": ("串口", "uart", "usart"),
    "ADC": ("adc", "模数转换"),
    "DAC": ("dac", "数模转换"),
    "DMA": ("dma",),
    "I2C": ("i2c", "iic"),
    "SPI": ("spi",),
    "调试": ("调试", "排错", "debug"),
    "寄存器": ("寄存器", "register"),
    "按键": ("按键", "button", "key"),
    "LED": ("led",),
}

SIMULATOR_EXPERIMENTS = [
    {
        "id": "uno-led-ready",
        "title": "Arduino LED 闪烁实验",
        "board": "arduino",
        "url": "/mcu-simulator/arduino/uno-led-ready",
        "keywords": ["gpio", "led", "输出", "闪烁", "arduino"],
    },
    {
        "id": "uno-button-ready",
        "title": "Arduino 按键控制 LED 实验",
        "board": "arduino",
        "url": "/mcu-simulator/arduino/uno-button-ready",
        "keywords": ["按键", "输入", "gpio", "led", "上拉"],
    },
    {
        "id": "8051-led-ready",
        "title": "8051 P1 跑马灯实验",
        "board": "8051",
        "url": "/mcu-simulator/8051/8051-led-ready",
        "keywords": ["51", "8051", "p1", "led", "跑马灯", "汇编"],
    },
    {
        "id": "8051-ram-ready",
        "title": "8051 RAM 写入实验",
        "board": "8051",
        "url": "/mcu-simulator/8051/8051-ram-ready",
        "keywords": ["51", "8051", "ram", "寄存器", "寻址", "汇编"],
    },
]


def generate_resource_workflow(
    payload: dict[str, Any],
    mcu_experiments: list[dict[str, Any]] | None = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    """Generate personalized resources using a small deterministic workflow."""
    context = ResourceContext(
        profile=payload.get("profile") or {},
        route=payload.get("route") or {},
        question_sheets=list_question_sheets(user_id),
        mcu_experiments=mcu_experiments or [],
        knowledge={},
    )
    requested = payload.get("request") if isinstance(payload.get("request"), dict) else {}
    requested_topic = str(requested.get("topic") or "").strip()
    topics = extract_topics(context, requested_topic=requested_topic)
    knowledge_query = " ".join(
        [
            str(requested.get("topic") or ""),
            *topics,
            "嵌入式系统 单片机 课程知识",
        ]
    )
    context.knowledge = retrieve_course_knowledge(knowledge_query, top_k=6)
    builders = {
        "document": build_document_resource,
        "mindmap": build_mindmap_resource,
        "ppt": build_ppt_resource,
        "video": build_video_resource,
        "question-bank": build_quiz_resource,
        "mcu": build_simulator_resource,
    }
    requested_type = str(requested.get("resourceType") or requested.get("type") or "").strip().lower()
    requested_type = {
        "quiz": "question-bank",
        "question_bank": "question-bank",
        "simulator": "mcu",
        "mind-map": "mindmap",
        "handout": "document",
    }.get(requested_type, requested_type)
    selected_builders = [builders[requested_type]] if requested_type in builders else list(builders.values())
    resources = [builder(topics, context) for builder in selected_builders]
    return {
        "agent": "personalized-resource-workflow",
        "source": "workflow-real-data",
        "planner": {
            "targetWeakPoints": topics[:5],
            "strategy": "先用知识库讲义建立可追溯基础，再用导图和 HTML PPT 组织重点，视频来自在线检索，题库用于验证，最后进入单片机模拟器实验。",
            "nodes": [
                "profile_topic_extractor",
                *[
                    str((item.get("metadata") or {}).get("workflowNode") or "resource_specialist")
                    for item in resources
                ],
                "resource_ranker",
            ],
            "requestedResourceType": requested_type or "resource-package",
            "references": {
                "pptStyle": "lewislulu/html-ppt-skill: static HTML/CSS slide deck style",
                "questionSheets": len(context.question_sheets),
                "mcuExperiments": len(context.mcu_experiments),
                "knowledgeBase": context.knowledge.get("stats") or {},
            },
        },
        "resources": resources,
        "grounded": bool(context.knowledge.get("grounded")),
        "knowledgeSources": context.knowledge.get("citations") or [],
    }


def knowledge_source_markdown(context: ResourceContext) -> str:
    citations = context.knowledge.get("citations") or []
    if not citations:
        return "\n\n> 课程知识库未检索到直接相关片段，具体硬件参数请结合芯片手册核验。"
    lines = ["", "## 课程知识库来源"]
    for citation in citations[:6]:
        locator = f"第 {citation.get('page')} 页" if citation.get("page") else f"第 {citation.get('section') or 1} 节"
        lines.append(f"- [{citation.get('id')}] {citation.get('title')}（{locator}）")
    return "\n".join(lines)


def build_quality_evaluation(
    criteria: dict[str, int],
    *,
    citations: list[dict[str, Any]] | None = None,
    verified_item_count: int = 0,
    content_ready: bool = True,
    verification_required: bool | None = None,
) -> dict[str, Any]:
    """Build a consistent, inspectable quality result for every resource type."""
    normalized_criteria = {
        str(name): max(0, int(value))
        for name, value in criteria.items()
    }
    score = min(100, sum(normalized_criteria.values()))
    source_list = [item for item in (citations or []) if isinstance(item, dict)]
    needs_verification = (
        not bool(source_list or verified_item_count)
        if verification_required is None
        else bool(verification_required)
    )
    passed = bool(content_ready and score >= 70)
    return {
        "score": score,
        "passed": passed,
        "criteria": normalized_criteria,
        "citationCount": len(source_list),
        "verifiedItemCount": max(0, int(verified_item_count)),
        "verificationRequired": needs_verification,
        "reviewStatus": "passed" if passed and not needs_verification else ("needs-verification" if passed else "failed"),
    }


def evaluate_question_bank_resource(
    question_bank: dict[str, Any],
    *,
    expected_count: int,
    citations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    questions = [item for item in (question_bank.get("questions") or []) if isinstance(item, dict)]
    expected = max(1, int(expected_count or 1))
    complete_count = sum(
        1
        for item in questions
        if str(item.get("stem") or "").strip()
        and str(item.get("answer") or "").strip()
        and str(item.get("analysis") or item.get("explanation") or "").strip()
    )
    type_count = len({str(item.get("type") or "").strip() for item in questions if str(item.get("type") or "").strip()})
    question_ratio = min(1.0, len(questions) / expected)
    completeness_ratio = complete_count / max(1, len(questions))
    source_list = [item for item in (citations or []) if isinstance(item, dict)]
    quality = build_quality_evaluation(
        {
            "questionCount": round(30 * question_ratio),
            "answerAndAnalysis": round(30 * completeness_ratio),
            "typeCoverage": min(15, 5 + type_count * 3),
            "knowledgeGrounding": min(15, 6 + len(source_list) * 2),
            "safety": 10,
        },
        citations=source_list,
        verified_item_count=complete_count,
        content_ready=len(questions) >= expected and completeness_ratio >= 0.9,
        verification_required=not bool(source_list),
    )
    technical_corrections = [
        item
        for item in (question_bank.get("technical_corrections") or [])
        if isinstance(item, dict)
    ]
    consistency_penalty = min(15, len(technical_corrections) * 4)
    if consistency_penalty:
        quality["score"] = max(0, int(quality["score"]) - consistency_penalty)
        quality["passed"] = bool(quality["score"] >= 70 and len(questions) >= expected and completeness_ratio >= 0.9)
        quality["reviewStatus"] = (
            "passed"
            if quality["passed"] and not quality["verificationRequired"]
            else ("needs-verification" if quality["passed"] else "failed")
        )
    quality.update(
        {
            "questionCount": len(questions),
            "expectedQuestionCount": expected,
            "questionTypeCount": type_count,
            "technicalCorrectionCount": len(technical_corrections),
            "technicalConsistencyPenalty": consistency_penalty,
        }
    )
    return quality


def evaluate_ppt_resource(
    ppt: dict[str, Any],
    *,
    expected_page_count: int,
    citations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    pages = [item for item in (ppt.get("pages") or []) if isinstance(item, dict)]
    expected = max(1, int(expected_page_count or 1))
    complete_count = sum(
        1
        for item in pages
        if str(item.get("title") or "").strip()
        and len(str(item.get("h") or item.get("html") or item.get("bodyHtml") or "").strip()) >= 40
    )
    page_ratio = min(1.0, len(pages) / expected)
    completeness_ratio = complete_count / max(1, len(pages))
    source_list = [item for item in (citations or ppt.get("knowledgeSources") or []) if isinstance(item, dict)]
    quality = build_quality_evaluation(
        {
            "pageCount": round(30 * page_ratio),
            "contentStructure": round(25 * completeness_ratio),
            "knowledgeGrounding": min(20, 8 + len(source_list) * 2),
            "usability": 15 if complete_count >= min(3, expected) else 5,
            "safety": 10,
        },
        citations=source_list,
        verified_item_count=complete_count,
        content_ready=len(pages) >= expected and completeness_ratio >= 0.8,
        verification_required=not bool(source_list),
    )
    quality.update({"pageCount": len(pages), "expectedPageCount": expected, "completePageCount": complete_count})
    return quality


def build_document_resource(topics: list[str], context: ResourceContext) -> dict[str, Any]:
    """Generate a persistent-ready Markdown handout from retrieved course evidence."""
    topic = topics[0] if topics else "嵌入式系统"
    citations = context.knowledge.get("citations") or []
    hits = context.knowledge.get("hits") or context.knowledge.get("chunks") or []
    lines = [
        f"# {topic}个性化学习讲义",
        "",
        "## 学习目标",
        f"- 建立{topic}的输入、处理和输出模型",
        "- 识别常见配置错误并给出诊断顺序",
        "- 完成一次可复盘的实验或代码验证",
        "",
    ]
    section_count = 0
    for index, hit in enumerate(hits[:6], start=1):
        if not isinstance(hit, dict):
            continue
        excerpt = re.sub(r"\s+", " ", str(hit.get("excerpt") or hit.get("content") or "")).strip()[:1400]
        if not excerpt:
            continue
        citation_id = str(hit.get("citationId") or (citations[index - 1].get("id") if index <= len(citations) else "")).strip()
        section_count += 1
        lines.extend(
            [
                f"## {section_count}. {str(hit.get('title') or topic).strip()[:80]}",
                "",
                f"{excerpt}{f' [{citation_id}]' if citation_id else '（需进一步核验）'}",
                "",
            ]
        )
    framework_sections = [
        ("核心概念与工作流程", f"用流程图或伪代码描述{topic}的关键步骤，并为具体硬件参数保留数据手册核验项。"),
        ("常见错误与诊断顺序", "按现象、配置、代码、硬件连接和测量证据的顺序定位问题。"),
        ("最小实验与验收条件", "先定义输入、预期输出、异常分支和记录格式，再执行实验。"),
        ("复盘与迁移", "用自己的话复述核心机制，并说明它如何迁移到另一个外设或项目。"),
    ]
    while section_count < 4:
        title, body = framework_sections[section_count]
        section_count += 1
        lines.extend([f"## {section_count}. {title}", "", f"{body}（需进一步核验）", ""])
    lines.extend(
        [
            "## 巩固任务",
            f"1. 用费曼复述解释{topic}的核心机制，提交 150-300 字复述。",
            f"2. 完成一个{topic}最小实验，提交代码、配置、运行现象和错误修正记录。",
            "",
        ]
    )
    lines.append(knowledge_source_markdown(context).strip())
    grounding_score = min(30, len(citations) * 5 + (10 if citations else 0))
    quality = build_quality_evaluation(
        {
            "structure": 30,
            "knowledgeGrounding": grounding_score,
            "personalization": 20,
            "practiceReadiness": 10,
            "safety": 10,
        },
        citations=citations,
        verified_item_count=section_count,
        content_ready=bool(citations and section_count >= 4),
        verification_required=not bool(citations),
    )
    quality["sectionCount"] = section_count
    return resource(
        "document",
        f"{topic}个性化学习讲义",
        "根据当前画像与私有课程知识库生成的可追溯 Markdown 讲义。",
        "\n".join(lines).strip(),
        93,
        {
            "workflowNode": "learning_document_agent",
            "format": "markdown",
            "generated": True,
            "grounded": bool(citations),
            "knowledgeSources": citations,
            "qualityEvaluation": quality,
        },
    )


def extract_topics(context: ResourceContext, requested_topic: str = "") -> list[str]:
    pieces: list[str] = []
    profile = context.profile
    ai = profile.get("aiAnalysis") if isinstance(profile.get("aiAnalysis"), dict) else {}
    for source in [profile, ai, context.route]:
        for key in ["weaknesses", "weakPoints", "strengths", "recommendations"]:
            value = source.get(key) if isinstance(source, dict) else None
            if isinstance(value, list):
                pieces.extend(str(item) for item in value)
            elif isinstance(value, str):
                pieces.append(value)
    for key in ["chat", "chatBackground", "summary"]:
        value = profile.get(key)
        if value:
            pieces.append(str(value))

    text = " ".join([requested_topic, *pieces]).lower()
    topic_map = [
        ("GPIO", ["gpio", "io", "输入", "输出", "led", "按键"]),
        ("定时器", ["定时器", "timer", "pwm", "延时"]),
        ("串口通信", ["串口", "uart", "usart", "通信"]),
        ("中断系统", ["中断", "interrupt", "外部中断"]),
        ("C语言指针", ["指针", "数组", "结构体", "c语言", "c 语言"]),
        ("8051 汇编", ["8051", "51", "汇编", "p1", "ram"]),
        ("STM32 外设配置", ["stm32", "cube", "hal", "寄存器"]),
    ]
    topics: list[str] = []
    if requested_topic:
        topics.append(re.sub(r"\s+", " ", requested_topic).strip()[:60])
    for topic, keywords in topic_map:
        if any(keyword in text for keyword in keywords):
            if topic not in topics:
                topics.append(topic)
    for fallback in DEFAULT_TOPICS:
        if len(topics) >= 5:
            break
        if fallback not in topics:
            topics.append(fallback)
    return topics


def build_video_search_query(topics: list[str], context: ResourceContext) -> str:
    topic_text = " ".join(str(item or "") for item in topics[:5]).lower()
    primary_topic_text = str(topics[0] if topics else "").lower()
    try:
        profile_text = json.dumps(context.profile, ensure_ascii=False).lower()
    except (TypeError, ValueError):
        profile_text = str(context.profile or "").lower()

    platforms = [
        label
        for label, aliases in VIDEO_PLATFORM_TERMS.items()
        if any(alias in profile_text or alias in topic_text for alias in aliases)
    ]
    primary_concepts = [
        label
        for label, aliases in VIDEO_CONCEPT_TERMS.items()
        if any(alias in primary_topic_text for alias in aliases)
    ]
    secondary_concepts = [
        label
        for label, aliases in VIDEO_CONCEPT_TERMS.items()
        if label not in primary_concepts and any(alias in topic_text for alias in aliases)
    ]
    concepts = [*primary_concepts, *secondary_concepts]
    if not concepts:
        concepts = [str(topics[0]).strip()[:24]] if topics else ["嵌入式系统"]

    terms = [*(platforms[:1] or []), *concepts[:2], "教程"]
    return " ".join(dict.fromkeys(term for term in terms if term))


def build_mindmap_resource(topics: list[str], context: ResourceContext) -> dict[str, Any]:
    root = topics[0] if topics else "嵌入式学习"
    citations = context.knowledge.get("citations") or []
    hits = context.knowledge.get("hits") or context.knowledge.get("chunks") or []
    lines = [f"# {root}专项学习导图", ""]
    branch_topics = list(dict.fromkeys(str(item).strip() for item in topics[:4] if str(item).strip()))
    for fallback_topic in ["核心机制", "配置流程", "错误诊断", "实践验证"]:
        if len(branch_topics) >= 4:
            break
        if fallback_topic not in branch_topics:
            branch_topics.append(fallback_topic)

    for index, topic in enumerate(branch_topics[:4]):
        hit = hits[index] if index < len(hits) and isinstance(hits[index], dict) else {}
        excerpt = re.sub(r"\s+", " ", str(hit.get("excerpt") or hit.get("content") or "")).strip()
        excerpt = excerpt[:150].rstrip("，,；;。 ")
        citation_id = str(
            hit.get("citationId")
            or (citations[index].get("id") if index < len(citations) and isinstance(citations[index], dict) else "")
        ).strip()
        evidence = (
            f"{excerpt}{f' [{citation_id}]' if citation_id else ''}"
            if excerpt
            else "先核对课程资料与芯片手册，未被资料支持的硬件参数标记为需核验。"
        )
        lines.extend(
            [
                f"## {topic}",
                "### 核心依据",
                f"- {evidence}",
                "### 配置与观察",
                f"- 写出{topic}的输入、处理、输出，并标记关键配置入口。",
                f"- 通过寄存器值、日志、波形或运行现象验证{topic}是否按预期工作。",
                "### 易错点",
                "- 区分未初始化、参数不匹配、调用顺序错误和硬件连接异常。",
                "",
            ]
        )

    lines.extend(
        [
            "## 学习闭环",
            "### 建模",
            "- 先用导图明确概念关系和前置条件。",
            "### 验证",
            "- 再用题单检查理解，用实验记录配置、代码、现象和修正过程。",
            "### 复盘",
            "- 根据错题与实验异常更新薄弱点，并调整下一周学习路径。",
        ]
    )
    content = "\n".join(lines).strip()
    branch_count = len([line for line in lines if line.startswith("## ")])
    quality = build_quality_evaluation(
        {
            "structure": min(25, 10 + branch_count * 3),
            "relevance": 24,
            "knowledgeGrounding": min(25, 8 + len(citations) * 4),
            "usability": 15,
            "safety": 10,
        },
        citations=citations,
        verified_item_count=max(branch_count, len(citations)),
        content_ready=branch_count >= 4 and content.startswith("# "),
        verification_required=not bool(citations),
    )
    return resource(
        "mindmap",
        f"{root}知识结构思维导图",
        f"围绕{root}、画像薄弱点和课程知识依据生成的交互式思维导图。",
        content,
        94,
        {
            "workflowNode": "mindmap_agent",
            "format": "mindmap-markdown",
            "renderer": "mind-map-wizard",
            "grounded": bool(context.knowledge.get("grounded")),
            "knowledgeSources": citations,
            "qualityEvaluation": quality,
        },
    )


def build_ppt_resource(topics: list[str], context: ResourceContext) -> dict[str, Any]:
    title = f"{topics[0]}专项突破课件" if topics else "嵌入式专项突破课件"
    citations = context.knowledge.get("citations") or []
    slide_count = 1 + len(topics[:5])
    cards = "\n".join(
        f"""<section class="slide">
  <p class="eyebrow">Module {index + 1}</p>
  <h2>{html.escape(topic)}</h2>
  <ul>
    <li>建立{html.escape(topic)}的输入、处理、输出模型</li>
    <li>拆解常见配置步骤和易错点</li>
    <li>匹配题库练习和仿真实验进行验证</li>
  </ul>
</section>"""
        for index, topic in enumerate(topics[:5])
    )
    source_badges = " ".join(
        f"<span>[{html.escape(str(item.get('id') or 'KB'))}] {html.escape(str(item.get('title') or '课程资料'))}</span>"
        for item in citations[:4]
    )
    content = f"""<article class="html-ppt-deck" data-theme="engineering-whiteprint">
<style>
.html-ppt-deck {{ font-family: 'Noto Sans SC', system-ui, sans-serif; color: #173f36; }}
.slide {{ min-height: 420px; padding: 44px 56px; border-radius: 24px; margin: 0 0 18px; background: linear-gradient(135deg,#f8fffb,#e8f8f0); border: 1px solid rgba(31,166,112,.18); box-shadow: 0 18px 40px rgba(31,166,112,.10); }}
.cover h1 {{ font-size: 44px; margin: 0 0 16px; }}
.eyebrow {{ color: #0d8b5c; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }}
.slide h2 {{ font-size: 30px; margin: 0 0 18px; }}
.slide li {{ margin: 10px 0; line-height: 1.7; }}
.knowledge-sources {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:24px; font-size:13px; color:#527269; }}
.knowledge-sources span {{ padding:6px 9px; border:1px solid rgba(31,166,112,.18); border-radius:6px; background:#f7fffb; }}
</style>
<section class="slide cover">
  <p class="eyebrow">Personalized HTML PPT</p>
  <h1>{html.escape(title)}</h1>
  <p>参考 html-ppt-skill 的静态 HTML/CSS deck 思路：卡片式页面、主题 token、无构建步骤、可直接渲染。</p>
  <div class="knowledge-sources">{source_badges}</div>
</section>
{cards}
</article>"""
    quality = build_quality_evaluation(
        {
            "structure": min(25, 7 + slide_count * 3),
            "relevance": 24,
            "knowledgeGrounding": min(25, 8 + len(citations) * 4),
            "usability": 15,
            "safety": 10,
        },
        citations=citations,
        verified_item_count=slide_count,
        content_ready=slide_count >= 4 and "<section" in content,
        verification_required=not bool(citations),
    )
    return resource(
        "ppt",
        title,
        "HTML/CSS 课件内容，按 html-ppt-skill 的静态 deck 思路组织。",
        content,
        90,
        {
            "workflowNode": "html_ppt_agent",
            "format": "html",
            "grounded": bool(context.knowledge.get("grounded")),
            "knowledgeSources": citations,
            "qualityEvaluation": quality,
        },
    )


def build_video_resource(topics: list[str], context: ResourceContext) -> dict[str, Any]:
    query = build_video_search_query(topics, context)
    results = search_videos(query)
    # 只保留有 BV 号的视频结果
    video_results = [r for r in results if r.get("bvid")]
    lines = [f"# {query} 在线视频检索", "", "以下结果来自联网检索，请点击播放："]
    for index, item in enumerate(video_results[:8], start=1):
        lines.append(f"{index}. [{item['title']}]({item['url']})")
        if item.get("snippet"):
            lines.append(f"   - {item['snippet']}")
    citations = context.knowledge.get("citations") or []
    valid_link_count = sum(1 for item in video_results if str(item.get("url") or "").startswith("https://"))
    cover_count = sum(1 for item in video_results if str(item.get("cover") or "").startswith("https://"))
    relevance_scores = [max(0, video_relevance_score(query, item)) for item in video_results]
    relevance_ceiling = max(1, video_relevance_ceiling(query))
    relevance_ratio = (
        sum(min(score, relevance_ceiling) for score in relevance_scores)
        / max(1, len(relevance_scores) * relevance_ceiling)
    )
    quality = build_quality_evaluation(
        {
            "resultCompleteness": min(25, 10 + len(video_results) * 5) if video_results else 0,
            "relevance": round(8 + relevance_ratio * 17) if video_results else 0,
            "sourceValidity": min(25, 10 + valid_link_count * 5) if valid_link_count else 0,
            "usability": min(15, 6 + cover_count * 3) if cover_count else 0,
            "safety": 10,
        },
        citations=citations,
        verified_item_count=valid_link_count,
        content_ready=valid_link_count > 0,
        verification_required=valid_link_count < 3,
    )
    return resource(
        "video",
        f"{topics[0] if topics else '嵌入式'}在线视频教程检索",
        f"从B站检索到 {len(video_results)} 个相关视频教程，可直接在线播放。",
        "\n".join(lines) + knowledge_source_markdown(context),
        88,
        {
            "workflowNode": "video_search_agent",
            "query": query,
            "results": video_results[:8],
            "relevanceScores": relevance_scores[:8],
            "knowledgeSources": citations,
            "qualityEvaluation": quality,
        },
    )


def build_quiz_resource(topics: list[str], context: ResourceContext) -> dict[str, Any]:
    matches = rank_question_sheets(topics, context.question_sheets)
    if matches:
        lines = ["# 相关题单推荐", "", "以下题单来自你已经生成过的题库记录："]
        for index, sheet in enumerate(matches[:5], start=1):
            count = sheet.get("question_count") or len((sheet.get("question_bank") or {}).get("questions") or [])
            lines.append(f"{index}. **{sheet.get('title') or '未命名题单'}**")
            lines.append(f"   - 课程：{sheet.get('course_name') or '未填写'}")
            lines.append(f"   - 主题：{sheet.get('target_topic') or '未填写'}")
            lines.append(f"   - 题量：{count} 题")
            lines.append(f"   - 生成时间：{sheet.get('created_at') or ''}")
        description = f"从 {len(context.question_sheets)} 份历史题单中检索出的相关练习。"
        match_score = 86
        metadata = {"matchedSheetIds": [item.get("id") for item in matches[:5]]}
    else:
        lines = ["# 暂无可推荐题单", "", "当前账号还没有与薄弱点匹配的题单。请先在“题库生成”里生成相关题单，再回到这里推荐。"]
        description = "未找到历史题单，等待用户生成题库后再推荐。"
        match_score = 55
        metadata = {"matchedSheetIds": []}
    citations = context.knowledge.get("citations") or []
    matched_question_count = sum(
        int(item.get("question_count") or len((item.get("question_bank") or {}).get("questions") or []))
        for item in matches[:5]
    )
    quality = build_quality_evaluation(
        {
            "resultCompleteness": min(25, matched_question_count * 2),
            "relevance": 24 if matches else 6,
            "sourceValidity": min(25, len(matches) * 5),
            "usability": 15 if matches else 4,
            "safety": 10,
        },
        citations=citations,
        verified_item_count=len(matches),
        content_ready=bool(matches and matched_question_count),
        verification_required=not bool(matches),
    )
    metadata["workflowNode"] = "question_bank_retrieval_agent"
    metadata["knowledgeSources"] = citations
    metadata["qualityEvaluation"] = quality
    return resource(
        "quiz",
        "历史题库相关题单推荐",
        description,
        "\n".join(lines) + knowledge_source_markdown(context),
        match_score,
        metadata,
    )


def build_simulator_resource(topics: list[str], context: ResourceContext) -> dict[str, Any]:
    ranked = rank_simulator_experiments(topics)
    lines = ["# 单片机模拟器实验推荐", "", "建议按顺序完成以下仿真实验："]
    for index, item in enumerate(ranked[:4], start=1):
        lines.append(f"{index}. [{item['title']}]({item['url']})")
        lines.append(f"   - 主板：{item['board']}")
        lines.append(f"   - 匹配知识点：{', '.join(item['keywords'][:4])}")
    if context.mcu_experiments:
        lines.extend(["", "## 近期实验记录"])
        for record in context.mcu_experiments[:3]:
            lines.append(
                f"- {record.get('experiment_name') or record.get('experiment_id')}："
                f"{'已通过' if record.get('passed') else '待巩固'}"
            )
    citations = context.knowledge.get("citations") or []
    valid_experiment_count = sum(
        1
        for item in ranked[:4]
        if str(item.get("url") or "").startswith("/mcu-simulator/") and item.get("board") in {"arduino", "8051"}
    )
    quality = build_quality_evaluation(
        {
            "resultCompleteness": min(25, len(ranked[:4]) * 7),
            "relevance": 22,
            "routeValidity": min(25, valid_experiment_count * 7),
            "usability": 15 if valid_experiment_count else 4,
            "safety": 10,
        },
        citations=citations,
        verified_item_count=valid_experiment_count,
        content_ready=valid_experiment_count > 0,
        verification_required=valid_experiment_count < len(ranked[:4]),
    )
    return resource(
        "simulator",
        f"{topics[0] if topics else '嵌入式'}仿真实验推荐",
        "根据薄弱点推荐当前系统里真实存在的单片机模拟器实验。",
        "\n".join(lines) + knowledge_source_markdown(context),
        84,
        {
            "workflowNode": "mcu_simulator_recommender",
            "experiments": ranked[:4],
            "knowledgeSources": citations,
            "qualityEvaluation": quality,
        },
    )


def extract_bvid(url: str) -> str:
    """从 Bilibili URL 中提取 BV 号。"""
    m = re.search(r'(BV[\w]{10})', url)
    return m.group(1) if m else ''


def search_bilibili_web(query: str) -> list[dict[str, str]]:
    """直接爬取 Bilibili 搜索页面提取视频列表。"""
    results: list[dict[str, str]] = []
    bvid_info: dict[str, dict] = {}  # bvid -> {title, author, duration, cover}
    try:
        search_url = f"https://search.bilibili.com/all?keyword={urllib.parse.quote(query)}"
        req = urllib.request.Request(search_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://www.bilibili.com",
        })
        with urllib.request.urlopen(req, timeout=12) as resp:
            body = resp.read().decode("utf-8", errors="ignore")

        # 从 __INITIAL_STATE__ JSON 中提取视频数据（最可靠）
        state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});\s*(?:\(function|</script>)', body, re.S)
        if state_match:
            try:
                state = json.loads(state_match.group(1))
                result_lists = [
                    state.get("flow", {}).get("result", []),
                    state.get("flow", {}).get("pageData", {}).get("result", []),
                    state.get("searchVideo", {}).get("result", []),
                ]
                for result_list in result_lists:
                    if not isinstance(result_list, list):
                        continue
                    for item in result_list:
                        if not isinstance(item, dict):
                            continue
                        bvid = item.get("bvid", "")
                        if not bvid:
                            continue
                        title_raw = item.get("title", "")
                        title_clean = re.sub(r'<[^>]+>', '', str(title_raw)).strip() if title_raw else ""
                        pic = item.get("pic", "")
                        if pic and not str(pic).startswith("http"):
                            pic = "https:" + str(pic)
                        bvid_info[bvid] = {
                            "title": title_clean[:120] if title_clean else f"Bilibili 视频",
                            "author": item.get("author", ""),
                            "duration": item.get("duration", ""),
                            "cover": pic,
                        }
            except (json.JSONDecodeError, TypeError):
                pass

        # 备用：从 HTML href 中提取 BV 号
        for m in re.finditer(r'href="[^"]*?(?:bilibili\.com/video/(BV[\w]{10})|/video/(BV[\w]{10}))', body):
            bvid = m.group(1) or m.group(2)
            if bvid and bvid not in bvid_info:
                bvid_info[bvid] = {"title": "Bilibili 视频", "author": "", "duration": "", "cover": ""}

        # 构建结果列表
        for bvid, info in list(bvid_info.items())[:10]:
            results.append({
                "title": info["title"],
                "url": f"https://www.bilibili.com/video/{bvid}",
                "bvid": bvid,
                "embedUrl": f"https://player.bilibili.com/player.html?bvid={bvid}&high_quality=1",
                "snippet": f"UP主：{info['author']}" if info["author"] else "",
                "cover": info["cover"],
                "duration": info["duration"],
                "author": info["author"],
            })
    except Exception:
        pass
    return results


def search_bilibili_api(query: str) -> list[dict[str, str]]:
    """通过 Bilibili 搜索 API 获取视频列表（备用方案）。"""
    results: list[dict[str, str]] = []
    try:
        api_url = (
            "https://api.bilibili.com/x/web-interface/search/type"
            f"?search_type=video&keyword={urllib.parse.quote(query)}&page=1&page_size=10"
        )
        req = urllib.request.Request(api_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://search.bilibili.com",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
        for item in (data.get("data", {}).get("result") or [])[:10]:
            bvid = item.get("bvid", "")
            title = re.sub(r'<[^>]+>', '', item.get("title", "")).strip()
            if not bvid or not title:
                continue
            duration = item.get("duration", "")
            pic = item.get("pic", "")
            if pic and not pic.startswith("http"):
                pic = "https:" + pic
            author = item.get("author", "")
            results.append({
                "title": title[:120],
                "url": f"https://www.bilibili.com/video/{bvid}",
                "bvid": bvid,
                "embedUrl": f"https://player.bilibili.com/player.html?bvid={bvid}&high_quality=1",
                "snippet": f"UP主：{author}　时长：{duration}" if author else f"时长：{duration}",
                "cover": pic,
                "duration": duration,
                "author": author,
            })
    except Exception:
        pass
    return results


def search_bing_videos(query: str) -> list[dict[str, str]]:
    """通过 Bing 搜索 Bilibili 视频。"""
    results: list[dict[str, str]] = []
    try:
        url = f"https://www.bing.com/search?q={urllib.parse.quote(query + ' site:bilibili.com/video')}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
        # 提取带 BV 号的链接
        for m in re.finditer(r'href="([^"]*bilibili\.com/video/BV[\w]{10}[^"]*)"', body):
            raw_url = html.unescape(m.group(1))
            if not raw_url.startswith("http"):
                continue
            bvid = extract_bvid(raw_url)
            if bvid and bvid not in [r.get("bvid") for r in results]:
                results.append({
                    "title": f"Bilibili 视频",
                    "url": f"https://www.bilibili.com/video/{bvid}",
                    "bvid": bvid,
                    "embedUrl": f"https://player.bilibili.com/player.html?bvid={bvid}&high_quality=1",
                    "snippet": "",
                    "cover": "",
                    "duration": "",
                    "author": "",
                })
    except Exception:
        pass
    return results


def _video_duration_label(value: Any) -> str:
    try:
        seconds = max(0, int(value or 0))
    except (TypeError, ValueError):
        return str(value or "").strip()
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"


def fetch_bilibili_video_detail(bvid: str) -> dict[str, str]:
    bvid = str(bvid or "").strip()
    if not bvid:
        return {}
    now = time.monotonic()
    cached = _VIDEO_DETAIL_CACHE.get(bvid)
    if cached and cached[0] > now:
        return dict(cached[1])

    detail: dict[str, str] = {}
    try:
        url = f"https://api.bilibili.com/x/web-interface/view?bvid={urllib.parse.quote(bvid)}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.bilibili.com/",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
        data = payload.get("data") if payload.get("code") == 0 and isinstance(payload.get("data"), dict) else {}
        owner = data.get("owner") if isinstance(data.get("owner"), dict) else {}
        cover = str(data.get("pic") or "").strip()
        if cover.startswith("http://"):
            cover = "https://" + cover.removeprefix("http://")
        author = str(owner.get("name") or "").strip()
        duration = _video_duration_label(data.get("duration"))
        detail = {
            "title": re.sub(r"<[^>]+>", "", str(data.get("title") or "")).strip()[:120],
            "cover": cover,
            "author": author,
            "duration": duration,
            "snippet": "　".join(part for part in [f"UP主：{author}" if author else "", f"时长：{duration}" if duration else ""] if part),
        }
        detail = {key: value for key, value in detail.items() if value}
    except Exception:
        detail = {}

    ttl = VIDEO_DETAIL_CACHE_TTL_SECONDS if detail else VIDEO_DETAIL_FAILURE_TTL_SECONDS
    _VIDEO_DETAIL_CACHE[bvid] = (now + ttl, detail)
    return dict(detail)


def enrich_bilibili_video_metadata(results: list[dict[str, str]]) -> list[dict[str, str]]:
    enriched = [dict(item) for item in results]
    missing_indexes = [
        index
        for index, item in enumerate(enriched)
        if item.get("bvid")
        and (
            not item.get("cover")
            or not item.get("author")
            or not item.get("duration")
            or str(item.get("title") or "").strip() == "Bilibili 视频"
        )
    ]
    if not missing_indexes:
        return enriched

    worker_count = min(4, len(missing_indexes))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        details = list(
            executor.map(
                fetch_bilibili_video_detail,
                [str(enriched[index].get("bvid") or "") for index in missing_indexes],
            )
        )
    for index, detail in zip(missing_indexes, details):
        for key, value in detail.items():
            current = str(enriched[index].get(key) or "").strip()
            if value and (not current or (key == "title" and current == "Bilibili 视频")):
                enriched[index][key] = value
    return enriched


def _video_requested_platform(query: str) -> str:
    text = str(query or "").lower()
    for label, aliases in VIDEO_PLATFORM_TERMS.items():
        if any(alias in text for alias in aliases):
            return label
    return ""


def _video_requested_concepts(query: str) -> list[str]:
    text = str(query or "").lower()
    return [
        label
        for label, aliases in VIDEO_CONCEPT_TERMS.items()
        if any(alias in text for alias in aliases)
    ]


def video_relevance_ceiling(query: str) -> int:
    return (8 if _video_requested_platform(query) else 0) + 4 * len(_video_requested_concepts(query))


def video_relevance_score(query: str, item: dict[str, Any]) -> int:
    title = str(item.get("title") or "").lower()
    details = " ".join(
        [
            title,
            str(item.get("snippet") or "").lower(),
            str(item.get("author") or "").lower(),
        ]
    )
    if not title or title == "bilibili 视频":
        return 0

    score = 0
    requested_platform = _video_requested_platform(query)
    if requested_platform:
        requested_aliases = VIDEO_PLATFORM_TERMS[requested_platform]
        requested_match = any(alias in details for alias in requested_aliases)
        if requested_match:
            score += 8
        conflicting_platform = any(
            label != requested_platform and any(alias in details for alias in aliases)
            for label, aliases in VIDEO_PLATFORM_TERMS.items()
        )
        if conflicting_platform and not requested_match:
            score -= 10

    for concept in _video_requested_concepts(query):
        aliases = VIDEO_CONCEPT_TERMS[concept]
        if any(alias in details for alias in aliases):
            score += 4
    return score


def video_matches_requested_platform(query: str, item: dict[str, Any]) -> bool:
    requested_platform = _video_requested_platform(query)
    if not requested_platform:
        return False
    details = " ".join(
        [
            str(item.get("title") or "").lower(),
            str(item.get("snippet") or "").lower(),
            str(item.get("author") or "").lower(),
        ]
    )
    return any(alias in details for alias in VIDEO_PLATFORM_TERMS[requested_platform])


def rank_video_results(query: str, results: list[dict[str, str]]) -> list[dict[str, str]]:
    scored = [
        (video_relevance_score(query, item), index, item)
        for index, item in enumerate(results)
    ]
    scored.sort(key=lambda entry: (entry[0], -entry[1]), reverse=True)
    platform_matches = [entry for entry in scored if video_matches_requested_platform(query, entry[2])]
    relevant = [entry for entry in scored if entry[0] > 0]
    if len(platform_matches) >= 3:
        selected = platform_matches
    elif len(relevant) >= 3:
        selected = relevant
    else:
        selected = scored
    return [dict(item) for _, _, item in selected[:8]]


def search_videos(query: str) -> list[dict[str, str]]:
    # The search API exposes the actual cover, title, author and duration. The
    # HTML page often contains enough links to look successful while omitting
    # all metadata, so link count alone must not short-circuit the API path.
    result_groups: list[list[dict[str, str]]] = [search_bilibili_api(query)]
    api_results = result_groups[0]
    api_cover_count = sum(1 for item in api_results if item.get("cover"))
    if len(api_results) < 5 or api_cover_count < min(5, len(api_results)):
        result_groups.append(search_bilibili_web(query))

    current_count = len({item.get("bvid") for group in result_groups for item in group if item.get("bvid")})
    if current_count < 5:
        result_groups.append(search_bing_videos(query))

    merged: dict[str, dict[str, str]] = {}
    order: list[str] = []
    for group in result_groups:
        for raw_item in group:
            bvid = str(raw_item.get("bvid") or "").strip()
            if not bvid:
                continue
            if bvid not in merged:
                merged[bvid] = dict(raw_item)
                order.append(bvid)
                continue
            item = merged[bvid]
            for key in ["title", "url", "embedUrl", "snippet", "cover", "duration", "author"]:
                incoming = str(raw_item.get(key) or "").strip()
                current = str(item.get(key) or "").strip()
                if incoming and (not current or (key == "title" and current == "Bilibili 视频")):
                    item[key] = incoming

    enriched = enrich_bilibili_video_metadata([merged[bvid] for bvid in order])
    return rank_video_results(query, enriched)


def parse_search_results(body: str) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    for match in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', body, flags=re.I | re.S):
        url = html.unescape(match.group(1))
        title = clean_html(match.group(2))
        if not title or len(title) < 4:
            continue
        if "bing.com" in url and "RU=" in url:
            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            if "u" in parsed:
                url = parsed["u"][0]
        if not url.startswith("http"):
            continue
        lower = url.lower()
        if not any(domain in lower for domain in ["bilibili.com", "youtube.com", "youku.com", "cnblogs.com", "csdn.net"]):
            continue
        found.append({"title": title[:120], "url": url, "snippet": ""})
    return found


def rank_question_sheets(topics: list[str], sheets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored: list[tuple[int, dict[str, Any]]] = []
    topic_terms = [term.lower() for topic in topics for term in re.split(r"[\s/、，,]+", topic) if term]
    for sheet in sheets:
        bank = sheet.get("question_bank") or {}
        questions = bank.get("questions") or []
        text = " ".join([
            str(sheet.get("title") or ""),
            str(sheet.get("course_name") or ""),
            str(sheet.get("target_topic") or ""),
            str(sheet.get("summary") or ""),
            " ".join(str(q.get("stem") or "") + " " + str(q.get("knowledge_point") or "") for q in questions[:20] if isinstance(q, dict)),
        ]).lower()
        score = sum(1 for term in topic_terms if term and term in text)
        if score:
            scored.append((score, sheet))
    scored.sort(key=lambda item: (item[0], item[1].get("id") or 0), reverse=True)
    return [sheet for _, sheet in scored]


def rank_simulator_experiments(topics: list[str]) -> list[dict[str, Any]]:
    text = " ".join(topics).lower()
    ranked = []
    for item in SIMULATOR_EXPERIMENTS:
        score = sum(1 for keyword in item["keywords"] if keyword.lower() in text)
        ranked.append((score, item))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in ranked]


def resource(resource_type: str, title: str, description: str, content: str, match_score: int, metadata: dict[str, Any]) -> dict[str, Any]:
    result = {
        "title": title,
        "description": description,
        "type": resource_type,
        "matchScore": match_score,
        "content": content,
        "metadata": metadata,
    }
    quality = metadata.get("qualityEvaluation") if isinstance(metadata, dict) else None
    if isinstance(quality, dict):
        result["qualityEvaluation"] = quality
    return result


def clean_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def safe_mermaid_label(value: str) -> str:
    value = re.sub(r"[(){}\[\]:;]", " ", str(value))
    return re.sub(r"\s+", " ", value).strip()[:32] or "嵌入式"
