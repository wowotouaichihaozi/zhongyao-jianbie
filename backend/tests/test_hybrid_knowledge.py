import json
import tempfile
import unittest
from pathlib import Path

from backend.hybrid_knowledge import HybridKnowledgeRouter, ROUTER_VERSION, _focused_fts_query


def document_result(query: str, excerpt: str) -> dict:
    return {
        "query": query,
        "grounded": True,
        "hits": [
            {
                "citationId": "KB1",
                "scope": "built-in",
                "sourceType": "course-corpus",
                "source": "02_四诊与八纲辨证.txt",
                "title": "四诊与八纲辨证",
                "section": 1,
                "score": 2.8,
                "excerpt": excerpt,
            }
        ],
        "activePrivateCollection": None,
        "stats": {"indexedChunks": 12, "matchedChunks": 1},
    }


class HybridKnowledgeRouterTests(unittest.TestCase):
    def test_faq_document_and_graph_are_cross_validated(self) -> None:
        router = HybridKnowledgeRouter()
        query = "八纲辨证中的八纲指什么"
        result = router.retrieve(
            query,
            document_result(query, "八纲包括表里、寒热、虚实、阴阳，阴阳为总纲。"),
            top_k=6,
        )

        self.assertEqual(result["routing"]["strategy"], ROUTER_VERSION)
        routes = {item["route"] for item in result["hits"]}
        self.assertTrue({"qa", "document", "graph"}.issubset(routes))
        self.assertEqual(result["routing"]["crossValidation"]["status"], "corroborated")
        self.assertEqual(
            result["routing"]["crossValidation"]["decision"],
            "allow_grounded_generation",
        )
        citation_ids = {item["id"] for item in result["citations"]}
        self.assertTrue(any(item.startswith("QA") for item in citation_ids))
        self.assertTrue(any(item.startswith("KB") for item in citation_ids))
        self.assertTrue(any(item.startswith("KG") for item in citation_ids))
        self.assertGreater(result["stats"]["qaPairs"], 100000)
        self.assertGreater(result["stats"]["documentCorpusChunks"], 10000)

    def test_relational_question_boosts_graph_route(self) -> None:
        router = HybridKnowledgeRouter()
        query = "阴阳消长和寒热证候之间有什么关系"
        result = router.retrieve(
            query,
            document_result(query, "阴阳偏盛偏衰可表现为寒热偏颇，需要结合证候判断。"),
            top_k=5,
        )

        routes = {item["id"]: item for item in result["routing"]["routes"]}
        self.assertGreater(routes["graph"]["weight"], routes["document"]["weight"])
        self.assertGreater(result["stats"]["graphNodes"], 1000)
        self.assertGreater(result["stats"]["graphMatched"], 0)

    def test_single_source_is_marked_for_verification(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tempdir:
            root = Path(tempdir)
            qa_path = root / "qa.json"
            graph_path = root / "graph.json"
            qa_path.write_text(json.dumps({"qaPairs": []}), encoding="utf-8")
            graph_path.write_text(json.dumps({"nodes": []}), encoding="utf-8")
            router = HybridKnowledgeRouter(qa_path=qa_path, graph_path=graph_path, corpus_path=None)
            query = "仅存在于私有资料的概念"
            result = router.retrieve(query, document_result(query, "唯一文档证据。"), top_k=4)

        validation = result["routing"]["crossValidation"]
        self.assertEqual(validation["status"], "single_source")
        self.assertTrue(validation["verificationRequired"])
        self.assertEqual(validation["decision"], "mark_for_verification")

    def test_subject_entity_drives_focused_retrieval(self) -> None:
        self.assertEqual(_focused_fts_query("黄连的性味归经和主要功效"), '"黄连"')
        self.assertEqual(
            _focused_fts_query("独活寄生汤的组成和功效是什么"),
            '"独活" AND "活寄" AND "寄生" AND "生汤"',
        )

        router = HybridKnowledgeRouter()
        herb_result = router.retrieve(
            "黄连的性味归经和主要功效",
            {"hits": [], "stats": {}},
            top_k=6,
        )
        herb_documents = [item for item in herb_result["hits"] if item["route"] == "document"]
        self.assertTrue(herb_documents)
        self.assertIn("黄连", f"{herb_documents[0]['title']} {herb_documents[0]['excerpt']}")

        formula_result = router.retrieve(
            "独活寄生汤的组成和功效是什么",
            {"hits": [], "stats": {}},
            top_k=8,
        )
        formula_evidence = " ".join(
            f"{item.get('title', '')} {item.get('excerpt', '')}"
            for item in formula_result["hits"]
        )
        self.assertIn("独活寄生汤", formula_evidence)
        self.assertIn("组成", formula_evidence)
        self.assertIn("功效", formula_evidence)


if __name__ == "__main__":
    unittest.main()
