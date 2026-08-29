"""Plan auditable multi-query retrieval for TCM learning resources."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parent / "data"
GRAPH_PATH = DATA_DIR / "tcm_graph_index.json"
AGENT_VERSION = "knowledge-retrieval-agent-v1"

ASPECT_TERMS = (
    "性味归经",
    "四气五味",
    "升降浮沉",
    "药用部位",
    "性状鉴别",
    "适用证候",
    "配伍禁忌",
    "方剂组成",
    "君臣佐使",
    "辨证论治",
    "八纲辨证",
    "四诊合参",
    "舌象",
    "脉象",
    "病机",
    "治法",
    "功效",
    "主治",
    "炮制",
    "用法",
    "用量",
    "鉴别",
    "医案",
    "证候",
    "方药",
)

GENERIC_GRAPH_TITLES = {
    "中医",
    "中药",
    "方剂",
    "中医药",
    "知识",
    "学习",
    "基础",
    "概述",
}

GENERIC_KEYWORDS = {"一份", "一个", "一种", "对应", "相关", "内容", "当前", "本周"}

INSTRUCTION_PATTERN = re.compile(
    r"(?:第[一二三四五六七八九十0-9]+周|任务\s*\d+|围绕|请|需要|完成|生成|制作|"
    r"整理|梳理|形成|输出|开展|进行|学习|课程|课件|题库|选择题|专项测评|"
    r"思维导图|PPT|ppt|讲义|视频|资源|知识点|相关内容)"
)

CLAUSE_SPLITTER = re.compile(
    r"[\s，,。；;：:、/|·（）()【】\[\]<>《》]+|(?:以及|并且|然后|针对|关于|围绕)"
)


def _clean(value: object) -> str:
    text = str(value or "").replace("\x00", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _dedupe(values: list[str], *, limit: int) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = _clean(raw).strip("的与和及、，。:：-_")
        compact = re.sub(r"\s+", "", value).lower()
        if (
            len(compact) < 2
            or compact in seen
            or value in GENERIC_KEYWORDS
            or re.fullmatch(r"\d+(?:道|个|页|题|项)", value)
        ):
            continue
        seen.add(compact)
        result.append(value)
        if len(result) >= limit:
            break
    return result


@lru_cache(maxsize=1)
def _graph_titles() -> tuple[str, ...]:
    try:
        payload = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return ()
    titles = {
        _clean(item.get("title"))
        for item in (payload.get("nodes") or [])
        if isinstance(item, dict)
    }
    return tuple(
        sorted(
            (
                title
                for title in titles
                if 2 <= len(title) <= 24
                and title not in GENERIC_GRAPH_TITLES
                and not re.search(r"[的和与及]", title)
                and title not in ASPECT_TERMS
                and not re.search(r"(?:功效|区别|性味归经|适用证候|病机|治法|方药)$", title)
            ),
            key=lambda item: (-len(item), item),
        )
    )


def _extract_entities(message: str) -> list[str]:
    matches = [title for title in _graph_titles() if title in message]
    # Prefer the most specific title when a shorter graph title is contained in it.
    selected: list[str] = []
    for title in matches:
        if any(title in existing for existing in selected):
            continue
        selected.append(title)
        if len(selected) >= 8:
            break

    syntactic: list[str] = []
    for left, right in re.findall(
        r"([\u4e00-\u9fff]{2,10})[与和及]([\u4e00-\u9fff]{2,10})(?=的(?:功效|性味|主治|区别|异同|鉴别|配伍))",
        message,
    ):
        left = re.sub(r"^(?:比较|对比|辨析|鉴别|分析)", "", left)
        right = re.sub(r"(?:之间)?$", "", right)
        syntactic.extend([left, right])
    for entity in re.findall(
        r"(?:如|例如|观察|识别|辨认|学习|关于|围绕)?([\u4e00-\u9fff]{2,8})的[\u4e00-\u9fff]{0,4}(?:性味归经|功效|主治|药用部位|性状|炮制|用法|用量)",
        message,
    ):
        entity = re.sub(r"^(?:比较|对比|辨析|鉴别|分析|关于|围绕|观察|识别|辨认|学习)", "", entity)
        if not re.search(r"[与和及]", entity):
            syntactic.append(entity)
    for entity in re.findall(
        r"(?:分析|辨析|围绕|关于)?([\u4e00-\u9fff]{2,10}?)(?:医案)?的(?:病机|治法|证候|方药)",
        message,
    ):
        entity = re.sub(r"^(?:分析|辨析|围绕|关于)", "", entity)
        syntactic.append(entity)

    quoted = re.findall(r"[“\"]([^”\"]{2,24})[”\"]", message)
    candidates = _dedupe([*syntactic, *selected, *quoted], limit=10)
    return [
        item
        for item in candidates
        if not any(item != other and item in other for other in candidates)
    ][:8]


def _extract_clause_keywords(message: str) -> list[str]:
    simplified = INSTRUCTION_PATTERN.sub(" ", message)
    candidates: list[str] = []
    for part in CLAUSE_SPLITTER.split(simplified):
        part = _clean(part).strip("的与和及、，。:：-_")
        if not part:
            continue
        if 2 <= len(part) <= 16:
            candidates.append(part)
            continue
        # Long task clauses often end with the actual learning target.
        suffix = re.search(r"([\u4e00-\u9fff]{2,12})(?:对比|区别|鉴别|分析|判断|应用)$", part)
        if suffix:
            candidates.append(suffix.group(1) + part[-2:])
    return _dedupe(candidates, limit=8)


def _intent(message: str) -> str:
    if re.search(r"对比|比较|区别|异同|鉴别", message):
        return "compare"
    if re.search(r"为什么|病机|机制|关系|如何|怎样", message):
        return "reasoning"
    if re.search(r"题|测评|判断|练习", message):
        return "assessment"
    if re.search(r"医案|证候|辨证|治法|方药", message):
        return "case-analysis"
    return "concept"


def plan_knowledge_retrieval(message: str, *, max_subqueries: int = 4) -> dict[str, Any]:
    """Convert a resource request into deterministic, inspectable search queries."""
    original = _clean(message)
    if not original:
        return {
            "agent": "knowledge-retrieval-agent",
            "version": AGENT_VERSION,
            "source": "domain-query-parser",
            "status": "empty",
            "originalQuery": "",
            "intent": "concept",
            "entities": [],
            "aspects": [],
            "keywords": [],
            "subQueries": [],
        }

    entities = _extract_entities(original)
    aspects = [term for term in ASPECT_TERMS if term in original]
    clause_keywords = _extract_clause_keywords(original)
    keywords = _dedupe([*entities, *aspects, *clause_keywords], limit=14)
    if not keywords:
        keywords = [original[:80]]

    intent = _intent(original)
    query_candidates: list[tuple[str, list[str], list[str]]] = []
    core = " ".join(keywords[:8])
    if core:
        query_candidates.append((core, entities, aspects))

    if len(entities) >= 2 and intent == "compare":
        requested_aspects = aspects[:4] or ["功效", "主治", "鉴别"]
        query_candidates.append(
            (
                f"{'与'.join(entities[:4])}的{'、'.join(requested_aspects)}有何区别",
                entities[:4],
                aspects[:4],
            )
        )

    for entity in entities[:3]:
        requested_aspects = aspects[:4] or ["定义", "功效", "主治"]
        query_candidates.append(
            (f"{entity}的{'、'.join(requested_aspects)}是什么", [entity], aspects[:4])
        )

    for phrase in clause_keywords[:3]:
        query_candidates.append((" ".join([phrase, *aspects[:3]]), [], aspects[:3]))

    subqueries: list[dict[str, Any]] = []
    seen_queries: set[str] = set()
    for query, query_entities, query_aspects in query_candidates:
        normalized = _clean(query)
        key = re.sub(r"\s+", "", normalized).lower()
        if len(key) < 2 or key in seen_queries:
            continue
        seen_queries.add(key)
        subqueries.append(
            {
                "id": f"SQ{len(subqueries) + 1}",
                "query": normalized[:180],
                "entities": _dedupe(query_entities, limit=6),
                "aspects": _dedupe(query_aspects, limit=6),
                "intent": intent,
            }
        )
        if len(subqueries) >= max(1, min(int(max_subqueries), 6)):
            break

    return {
        "agent": "knowledge-retrieval-agent",
        "version": AGENT_VERSION,
        "source": "domain-query-parser",
        "status": "planned" if subqueries else "empty",
        "originalQuery": original,
        "intent": intent,
        "entities": entities,
        "aspects": _dedupe(aspects, limit=10),
        "keywords": keywords,
        "subQueries": subqueries,
    }
