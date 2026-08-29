from backend.course_knowledge import retrieve_course_knowledge
from backend.knowledge_retrieval_agent import AGENT_VERSION, plan_knowledge_retrieval


def test_retrieval_agent_splits_comparison_into_entities_and_subqueries():
    plan = plan_knowledge_retrieval(
        "比较麻黄与桂枝的功效区别、性味归经和适用证候，并生成一份课程讲义"
    )

    assert plan["version"] == AGENT_VERSION
    assert plan["intent"] == "compare"
    assert plan["entities"] == ["麻黄", "桂枝"]
    assert {"性味归经", "适用证候", "功效"}.issubset(set(plan["aspects"]))
    queries = [item["query"] for item in plan["subQueries"]]
    assert any(query.startswith("麻黄的") for query in queries)
    assert any(query.startswith("桂枝的") for query in queries)
    assert any("麻黄与桂枝" in query and "区别" in query for query in queries)


def test_retrieval_agent_extracts_herb_from_assessment_instruction():
    plan = plan_knowledge_retrieval("围绕紫珠叶的止血功效生成10道选择题")

    assert plan["intent"] == "assessment"
    assert plan["entities"] == ["紫珠叶"]
    assert "功效" in plan["aspects"]
    assert all("10道" not in item["query"] for item in plan["subQueries"])


def test_multi_query_retrieval_returns_three_routes_and_persistable_excerpts():
    result = retrieve_course_knowledge(
        "比较麻黄与桂枝的功效区别、性味归经和适用证候",
        top_k=8,
        include_private=False,
    )

    assert result["retrievalAgent"]["version"] == AGENT_VERSION
    assert result["routing"]["mode"] == "agentic-multi-query"
    assert len(result["routing"]["subQueryRuns"]) >= 3
    routes = {item["route"] for item in result["hits"]}
    assert routes == {"qa", "document", "graph"}
    qa_titles = {item["title"] for item in result["hits"] if item["route"] == "qa"}
    assert "麻黄的性味归经和主要功效是什么？" in qa_titles
    assert "桂枝的性味归经和主要功效是什么？" in qa_titles
    document_titles = {item["title"] for item in result["hits"] if item["route"] == "document"}
    assert {"麻黄", "桂枝"}.issubset(document_titles)
    assert all(str(item.get("excerpt") or "").strip() for item in result["citations"])
    assert all(item.get("matchedSubQueries") for item in result["citations"])
