import json
import tempfile
import unittest
from pathlib import Path

from backend import app as app_module
from backend.database_schema import init_auth_schema
from backend.private_knowledge import create_knowledge_collection, retrieve_private_knowledge


class ShowcaseNetworkApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.original_db_path = app_module.AUTH_DB_PATH
        app_module.AUTH_DB_PATH = Path(cls.tempdir.name) / "showcase-network.sqlite3"
        app_module.app.config.update(TESTING=True)
        timestamp = "2026-07-28T10:00:00+08:00"
        with app_module.auth_db() as conn:
            init_auth_schema(conn)
            users = (
                (901, "showcase-owner", "user"),
                (902, "showcase-other", "user"),
                (903, "admin123", "admin"),
            )
            for user_id, username, role in users:
                conn.execute(
                    """
                    INSERT INTO users
                        (id, username, display_name, password_hash, role, avatar_url, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, '/userlogo.png', ?, ?)
                    """,
                    (user_id, username, username, app_module.password_hash("test-password"), role, timestamp, timestamp),
                )
                with app_module.app.test_request_context("/api/auth/login", headers={"User-Agent": "showcase-test"}):
                    token = app_module.create_session(conn, user_id)
                setattr(cls, f"token_{user_id}", token)
            cls.collection = create_knowledge_collection(
                conn, 901, "反哺目标库", "审核通过后写入", timestamp=timestamp
            )
            other_collection = create_knowledge_collection(
                conn, 902, "其他用户知识库", "隔离测试", timestamp=timestamp
            )
            cls.other_collection_id = other_collection["id"]
            conn.execute(
                """
                INSERT INTO agent_orchestration_runs
                    (run_id, task_id, user_id, root_agent, task_type, topic, status, architecture,
                     skill_id, mcp_server, mcp_tool, created_at, updated_at)
                VALUES ('run-owner', 'task-owner', 901, 'xiaozhi-companion-agent', 'mindmap',
                        'FreeRTOS 调度', 'complete', 'supervisor-shared-blackboard',
                        'mindmap.generate', 'platform-mcp', 'mindmap.generate', ?, ?)
                """,
                (timestamp, timestamp),
            )
            conn.execute(
                """
                INSERT INTO agent_orchestration_handoffs
                    (run_id, sequence, from_agent, to_agent, artifact_type, summary, created_at)
                VALUES ('run-owner', 2, 'xiaozhi-companion-agent', 'mindmap-agent',
                        'task-context', '交接主题与画像', ?)
                """,
                (timestamp,),
            )
            conn.execute(
                """
                INSERT INTO agent_orchestration_events
                    (run_id, sequence, agent_id, stage, status, message, progress, created_at)
                VALUES ('run-owner', 1, 'xiaozhi-companion-agent', 'dispatch', 'running',
                        '主控开始分发', 20, ?)
                """,
                (timestamp,),
            )
        cls.client = app_module.app.test_client()

    @classmethod
    def tearDownClass(cls) -> None:
        app_module.AUTH_DB_PATH = cls.original_db_path
        cls.tempdir.cleanup()

    def headers(self, user_id: int) -> dict[str, str]:
        return {"Authorization": f"Bearer {getattr(self, f'token_{user_id}')}"}

    def test_feedback_requires_owner_collection_and_evidence(self) -> None:
        cross_user = self.client.post(
            "/api/knowledge-network/feedback",
            headers=self.headers(901),
            json={
                "collectionId": self.other_collection_id,
                "title": "跨用户候选",
                "content": "这段内容足够长，但不能写入其他用户的知识库。",
                "evidence": [{"source": "run-owner"}],
            },
        )
        self.assertEqual(cross_user.status_code, 404)
        missing_evidence = self.client.post(
            "/api/knowledge-network/feedback",
            headers=self.headers(901),
            json={
                "collectionId": self.collection["id"],
                "title": "没有证据",
                "content": "这段内容足够长，但缺少可追溯的来源证据。",
            },
        )
        self.assertEqual(missing_evidence.status_code, 400)

    def test_growth_timeline_reports_persisted_user_summary(self) -> None:
        response = self.client.get(
            "/api/knowledge-network/timeline?limit=20",
            headers=self.headers(901),
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()["data"]
        self.assertTrue(any(item["type"] == "agent_run" for item in data["events"]))
        self.assertEqual(data["summary"]["agentRuns"], 1)
        self.assertEqual(data["summary"]["completedRuns"], 1)
        self.assertEqual(data["summary"]["collections"], 1)
        self.assertIn("ingestedDocuments", data["summary"])

        other = self.client.get(
            "/api/knowledge-network/timeline?limit=20",
            headers=self.headers(902),
        ).get_json()["data"]
        self.assertEqual(other["summary"]["agentRuns"], 0)
        self.assertEqual(other["summary"]["collections"], 1)

    def test_pending_feedback_is_not_retrievable_until_admin123_approves(self) -> None:
        unique_term = "QuartzAuditKernelRule"
        created = self.client.post(
            "/api/knowledge-network/feedback",
            headers=self.headers(901),
            json={
                "collectionId": self.collection["id"],
                "runId": "run-owner",
                "title": "审核后的内核规则",
                "content": f"{unique_term} 是本测试中只有审核通过后才能检索的知识内容。",
                "confidence": 0.8,
                "evidence": [{"title": "Harness 运行证据", "source": "run-owner", "citation": "event-1"}],
            },
        )
        self.assertEqual(created.status_code, 201)
        candidate_id = created.get_json()["data"]["id"]

        pending_result = retrieve_private_knowledge(
            unique_term, user_id=901, db_path=app_module.AUTH_DB_PATH, collection_id=self.collection["id"]
        )
        self.assertFalse(pending_result["grounded"])

        forbidden = self.client.post(
            f"/api/knowledge-network/feedback/{candidate_id}/review",
            headers=self.headers(901),
            json={"decision": "approved"},
        )
        self.assertEqual(forbidden.status_code, 403)

        approved = self.client.post(
            f"/api/knowledge-network/feedback/{candidate_id}/review",
            headers=self.headers(903),
            json={"decision": "approved", "reviewNote": "来源与内容已核验"},
        )
        self.assertEqual(approved.status_code, 200)
        self.assertIsNotNone(approved.get_json()["data"]["approvedDocumentId"])

        approved_result = retrieve_private_knowledge(
            unique_term, user_id=901, db_path=app_module.AUTH_DB_PATH, collection_id=self.collection["id"]
        )
        self.assertTrue(approved_result["grounded"])
        self.assertTrue(approved_result["hits"][0]["source"].startswith("knowledge-feedback-"))

    def test_atlas_view_returns_real_document_nodes_and_traceable_edges(self) -> None:
        index_path = Path(self.tempdir.name) / "atlas-index.json"
        index_path.write_text(
            json.dumps({
                "chunks": [
                    {"source": "freertos/tasks.md", "title": "FreeRTOS Tasks", "content": "FreeRTOS task scheduling"},
                    {"source": "freertos/tasks.md", "title": "FreeRTOS Tasks", "content": "task priority and timer"},
                    {"source": "lvgl/widgets.md", "title": "LVGL Widgets", "content": "LVGL display and GUI widgets"},
                    {"source": "mcu/freertos-stm32.md", "title": "STM32 STM32 STM32 MCU FreeRTOS", "content": "STM32 STM32 MCU GPIO ADC PWM interface with FreeRTOS tasks"},
                ]
            }),
            encoding="utf-8",
        )
        with app_module.auth_db() as conn:
            result = app_module.showcase_network.knowledge_overview(
                conn, 901, index_path, view="atlas", node_limit=500
            )

        document_nodes = [node for node in result["nodes"] if node["type"] == "document"]
        self.assertEqual(result["view"], "atlas")
        self.assertEqual(result["stats"]["courseDocuments"], 3)
        self.assertEqual(result["stats"]["indexedChunks"], 4)
        self.assertEqual(len(document_nodes), 3)
        self.assertTrue(all(node.get("source") for node in document_nodes))
        self.assertTrue(all(node.get("excerpt") for node in document_nodes))
        self.assertTrue(all(isinstance(node.get("topics"), list) for node in document_nodes))
        node_ids = {node["id"] for node in result["nodes"]}
        self.assertTrue(all(edge["source"] in node_ids and edge["target"] in node_ids for edge in result["edges"]))
        shared_topic_edges = [edge for edge in result["edges"] if edge.get("relation") == "shared_topic"]
        self.assertTrue(shared_topic_edges)
        self.assertTrue(all(edge.get("sharedTopic") == "freertos" for edge in shared_topic_edges))

    def test_atlas_prefers_matching_compact_catalog(self) -> None:
        index_path = Path(self.tempdir.name) / "portable-index.json"
        index_path.write_text("not valid json", encoding="utf-8")
        catalog_path = index_path.with_name(f"{index_path.stem}_catalog.json")
        catalog_path.write_text(
            json.dumps({
                "version": 1,
                "sourceIndexBytes": index_path.stat().st_size,
                "indexedChunks": 12,
                "documents": [{
                    "source": "freertos/tasks.md",
                    "title": "FreeRTOS Tasks",
                    "chunks": 12,
                    "sample": "FreeRTOS task scheduling",
                    "detail": "FreeRTOS task scheduling and priorities",
                    "topics": ["FreeRTOS"],
                    "domainKey": "rtos",
                    "domain": "Real-time operating systems",
                }],
            }),
            encoding="utf-8",
        )
        app_module.showcase_network._catalog_cache.update({"key": None, "documents": []})
        with app_module.auth_db() as conn:
            result = app_module.showcase_network.knowledge_overview(
                conn, 901, index_path, view="atlas", node_limit=500
            )
        self.assertEqual(result["stats"]["courseDocuments"], 1)
        self.assertEqual(result["stats"]["indexedChunks"], 12)
        self.assertTrue(any(node.get("source") == "freertos/tasks.md" for node in result["nodes"]))


if __name__ == "__main__":
    unittest.main()
