from backend.course_knowledge import clear_retrieval_cache, retrieve_course_knowledge
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
    clear_retrieval_cache()
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


def test_repeated_hybrid_retrieval_hits_cache_without_losing_citations():
    clear_retrieval_cache()
    first = retrieve_course_knowledge(
        "比较麻黄与桂枝的功效区别、性味归经和适用证候",
        top_k=8,
        include_private=False,
    )
    second = retrieve_course_knowledge(
        "比较麻黄与桂枝的功效区别、性味归经和适用证候",
        top_k=8,
        include_private=False,
    )

    assert first["cache"]["hit"] is False
    assert second["cache"]["hit"] is True
    assert second["cache"]["key"] == first["cache"]["key"]
    assert second["citations"] == first["citations"]
    assert {item["route"] for item in second["hits"]} == {"qa", "document", "graph"}


def test_equivalent_task_wording_reuses_semantic_retrieval_cache():
    clear_retrieval_cache()
    first = retrieve_course_knowledge(
        "比较麻黄与桂枝的功效区别、性味归经和适用证候",
        top_k=8,
        include_private=False,
    )
    second = retrieve_course_knowledge(
        "请围绕麻黄与桂枝的性味归经、功效区别和适用证候生成PPT",
        top_k=8,
        include_private=False,
    )

    assert first["retrievalAgent"]["entities"] == ["麻黄", "桂枝"]
    assert second["retrievalAgent"]["entities"] == ["麻黄", "桂枝"]
    assert second["cache"]["hit"] is True
    assert second["cache"]["key"] == first["cache"]["key"]
    assert len(second["citations"]) == len(first["citations"])


def test_private_cache_scope_is_isolated_by_user(tmp_path):
    clear_retrieval_cache()
    missing_db = tmp_path / "missing.sqlite3"
    owner = retrieve_course_knowledge("麻黄功效", user_id=101, db_path=missing_db)
    other = retrieve_course_knowledge("麻黄功效", user_id=202, db_path=missing_db)
    owner_again = retrieve_course_knowledge("麻黄功效", user_id=101, db_path=missing_db)

    assert owner["cache"]["hit"] is False
    assert other["cache"]["hit"] is False
    assert owner["cache"]["key"] != other["cache"]["key"]
    assert owner_again["cache"]["hit"] is True
