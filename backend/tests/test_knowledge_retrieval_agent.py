from backend.course_knowledge import clear_retrieval_cache, retrieve_course_knowledge
from backend.knowledge_retrieval_agent import AGENT_VERSION, plan_knowledge_retrieval


def test_retrieval_agent_splits_comparison_into_entities_and_subqueries():
    plan = plan_knowledge_retrieval(
        "比较 GPIO 与 UART 的工作原理、初始化流程和调试方法，并生成一份课程讲义"
    )

    assert plan["version"] == AGENT_VERSION
    assert plan["intent"] == "compare"
    assert plan["entities"][:2] == ["GPIO", "UART"]
    assert {"工作原理", "初始化流程", "调试方法"}.issubset(set(plan["aspects"]))
    queries = [item["query"] for item in plan["subQueries"]]
    assert any(query.startswith("GPIO的") for query in queries)
    assert any(query.startswith("UART的") for query in queries)
    assert any("GPIO与UART" in query and "区别" in query for query in queries)


def test_retrieval_agent_extracts_peripheral_from_assessment_instruction():
    plan = plan_knowledge_retrieval("围绕 STM32 GPIO 的中断配置生成10道选择题")

    assert plan["intent"] == "assessment"
    assert {"STM32", "GPIO"}.issubset(set(plan["entities"]))
    assert "中断配置" in plan["aspects"]
    assert all("10道" not in item["query"] for item in plan["subQueries"])


def test_multi_query_retrieval_uses_embedded_documents_and_persistable_excerpts():
    clear_retrieval_cache()
    result = retrieve_course_knowledge(
        "比较 GPIO 与 UART 的工作原理、初始化流程和调试方法",
        top_k=8,
        include_private=False,
    )

    assert result["retrievalAgent"]["version"] == AGENT_VERSION
    assert result["routing"]["mode"] == "agentic-multi-query"
    assert len(result["routing"]["subQueryRuns"]) >= 3
    assert {item["route"] for item in result["hits"]} == {"document", "graph"}
    assert result["stats"]["qaMatched"] == 0
    assert result["stats"]["graphMatched"] > 0
    assert not any("\ufffd" in str(item) for item in result["hits"])
    assert all(str(item.get("excerpt") or "").strip() for item in result["citations"])
    assert all(item.get("matchedSubQueries") for item in result["citations"])


def test_repeated_hybrid_retrieval_hits_cache_without_losing_citations():
    clear_retrieval_cache()
    first = retrieve_course_knowledge(
        "比较 GPIO 与 UART 的工作原理、初始化流程和调试方法",
        top_k=8,
        include_private=False,
    )
    second = retrieve_course_knowledge(
        "比较 GPIO 与 UART 的工作原理、初始化流程和调试方法",
        top_k=8,
        include_private=False,
    )

    assert first["cache"]["hit"] is False
    assert second["cache"]["hit"] is True
    assert second["cache"]["key"] == first["cache"]["key"]
    assert second["citations"] == first["citations"]
    assert {item["route"] for item in second["hits"]} == {"document", "graph"}


def test_equivalent_task_wording_reuses_semantic_retrieval_cache():
    clear_retrieval_cache()
    first = retrieve_course_knowledge(
        "比较 GPIO 与 UART 的工作原理、初始化流程和调试方法",
        top_k=8,
        include_private=False,
    )
    second = retrieve_course_knowledge(
        "请比较 GPIO 与 UART 的工作原理、初始化流程和调试方法并生成PPT",
        top_k=8,
        include_private=False,
    )

    assert first["retrievalAgent"]["entities"][:2] == ["GPIO", "UART"]
    assert second["retrievalAgent"]["entities"][:2] == ["GPIO", "UART"]
    assert second["cache"]["hit"] is True
    assert second["cache"]["key"] == first["cache"]["key"]
    assert len(second["citations"]) == len(first["citations"])


def test_exact_gpio_question_cross_validates_qa_graph_and_documents():
    clear_retrieval_cache()
    result = retrieve_course_knowledge(
        "STM32 GPIO 输出前为什么必须先使能外设时钟？",
        top_k=8,
        include_private=False,
    )

    routes = {item["route"] for item in result["hits"]}
    assert routes == {"qa", "document", "graph"}
    assert result["routing"]["crossValidation"]["status"] == "corroborated"
    assert any(item.get("qaId") == "EMB-QA-001" for item in result["hits"])


def test_private_cache_scope_is_isolated_by_user(tmp_path):
    clear_retrieval_cache()
    missing_db = tmp_path / "missing.sqlite3"
    owner = retrieve_course_knowledge("GPIO配置", user_id=101, db_path=missing_db)
    other = retrieve_course_knowledge("GPIO配置", user_id=202, db_path=missing_db)
    owner_again = retrieve_course_knowledge("GPIO配置", user_id=101, db_path=missing_db)

    assert owner["cache"]["hit"] is False
    assert other["cache"]["hit"] is False
    assert owner["cache"]["key"] != other["cache"]["key"]
    assert owner_again["cache"]["hit"] is True
