import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch


import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database_schema import init_auth_schema
from profile_agent_context import ProfileAgentContextStore


class ProfileAgentContextStoreTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "agent-context.sqlite3"
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.row_factory = sqlite3.Row
            init_auth_schema(conn)
            conn.execute(
                """
                INSERT INTO users
                    (id, username, display_name, password_hash, role, status,
                     avatar_url, created_at, updated_at)
                VALUES (1, 'learner', '学习者', 'hash', 'user', 'enabled', '', 'now', 'now')
                """
            )
            conn.execute(
                """
                INSERT INTO learning_profile_reports
                    (id, user_id, report_json, profile_name, created_at, updated_at)
                VALUES (11, 1, '{}', '画像 A', 'now', 'now'),
                       (12, 1, '{}', '画像 B', 'now', 'now')
                """
            )
        self.store = ProfileAgentContextStore(self.db_path)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_agents_share_one_ordered_conversation_per_profile(self):
        first = self.store.append_event(
            1,
            11,
            {
                "runId": "run-path",
                "taskId": "task-path",
                "sequence": 1,
                "agentId": "xiaozhi-companion-agent",
                "agentName": "岐小智总控智能体",
                "stage": "supervisor_plan",
                "status": "complete",
                "message": "已派发第一周学习路径规划",
                "progress": 8,
                "payload": {"route": "/learning-path/week/week-1"},
            },
        )
        second = self.store.append_handoff(
            1,
            11,
            {
                "runId": "run-resource",
                "sequence": 1,
                "fromAgent": "course-knowledge-retrieval-agent",
                "fromAgentName": "知识检索智能体",
                "toAgent": "ppt-agent",
                "toAgentName": "PPT 生成智能体",
                "artifactType": "grounded_knowledge",
                "summary": "交接 6 条知识引用",
                "payload": {"taskId": "ppt-1", "citationId": "doc-8#3"},
            },
        )
        duplicate = self.store.append_event(
            1,
            11,
            {
                "runId": "run-path",
                "sequence": 1,
                "agentId": "xiaozhi-companion-agent",
                "message": "重复事件不会再次写入",
            },
        )

        context = self.store.context(1, 11)

        self.assertEqual(first["sequence"], 1)
        self.assertEqual(second["sequence"], 2)
        self.assertEqual(duplicate["id"], first["id"])
        self.assertEqual(context["messageCount"], 2)
        self.assertEqual([item["sequence"] for item in context["recentMessages"]], [1, 2])
        self.assertEqual(context["supervisor"]["name"], "岐小智总控智能体")
        refs = context["recentMessages"][1]["resourceReferences"]
        self.assertIn({"type": "task", "id": "ppt-1"}, refs)
        self.assertIn({"type": "citation", "id": "doc-8#3"}, refs)

        other_profile = self.store.context(1, 12)
        self.assertNotEqual(context["conversationId"], other_profile["conversationId"])
        self.assertEqual(other_profile["messageCount"], 0)

    def test_trace_records_events_handoffs_and_review(self):
        result = {
            "orchestration": {
                "runId": "run-complete",
                "events": [
                    {
                        "runId": "run-complete",
                        "taskId": "task-1",
                        "sequence": 1,
                        "agentId": "mindmap-agent",
                        "agentName": "思维导图智能体",
                        "status": "complete",
                        "message": "导图生成完成",
                    }
                ],
                "handoffs": [
                    {
                        "runId": "run-complete",
                        "sequence": 1,
                        "fromAgent": "mindmap-agent",
                        "toAgent": "quality-review-agent",
                        "summary": "交接导图产物",
                    }
                ],
                "review": {"passed": True, "score": 87, "reasons": ["引用完整"]},
            }
        }

        self.store.record_trace(1, 11, result, task_id="task-1")
        context = self.store.context(1, 11)

        self.assertEqual(context["messageCount"], 3)
        self.assertEqual(
            [item["type"] for item in context["recentMessages"]],
            ["agent_event", "handoff", "review"],
        )
        self.assertIn("质量分 87", context["recentMessages"][-1]["content"])
        self.assertEqual(
            [item["taskId"] for item in context["recentMessages"]],
            ["task-1", "task-1", "task-1"],
        )
        self.assertIn(
            {"type": "task", "id": "task-1"},
            context["recentMessages"][1]["resourceReferences"],
        )

    def test_backfills_existing_orchestration_records(self):
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute(
                """
                INSERT INTO agent_orchestration_runs
                    (run_id, task_id, user_id, task_type, topic, status,
                     profile_report_id, input_json, output_json, review_json,
                     feedback_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, '{}', '{}', ?, '{}', ?, ?)
                """,
                (
                    "run-legacy",
                    "task-legacy",
                    1,
                    "ppt",
                    "麻黄桂枝对比",
                    "complete",
                    11,
                    '{"passed": true, "score": 91}',
                    "now",
                    "now",
                ),
            )
            conn.execute(
                """
                INSERT INTO agent_orchestration_events
                    (run_id, sequence, agent_id, stage, status, message,
                     progress, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "run-legacy",
                    1,
                    "course-knowledge-retrieval-agent",
                    "knowledge_retrieved",
                    "complete",
                    "知识检索智能体命中 6 条证据",
                    60,
                    '{"route": "/personalized-resources/ppt?xzTask=task-legacy"}',
                    "now",
                ),
            )
            conn.execute(
                """
                INSERT INTO agent_orchestration_handoffs
                    (run_id, sequence, from_agent, to_agent, artifact_type,
                     summary, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "run-legacy",
                    1,
                    "course-knowledge-retrieval-agent",
                    "ppt-agent",
                    "grounded_knowledge",
                    "交接 6 条知识引用",
                    '{"taskId": "task-legacy", "citationId": "qa-1"}',
                    "now",
                ),
            )

        inserted = self.store.backfill_from_orchestration(1, 11)
        context = self.store.context(1, 11)

        self.assertEqual(inserted, 3)
        self.assertEqual(context["messageCount"], 3)
        self.assertEqual(
            [item["type"] for item in context["recentMessages"]],
            ["agent_event", "handoff", "review"],
        )
        self.assertEqual(context["recentMessages"][0]["taskId"], "task-legacy")
        refs = context["recentMessages"][1]["resourceReferences"]
        self.assertIn({"type": "task", "id": "task-legacy"}, refs)
        self.assertIn("质量分 91", context["recentMessages"][2]["content"])
        self.assertEqual(self.store.backfill_from_orchestration(1, 11), 3)
        self.assertEqual(self.store.context(1, 11)["messageCount"], 3)

    def test_old_messages_are_compacted_before_context_limit(self):
        settings = {
            "PROFILE_AGENT_CONTEXT_MAX_TOKENS": "2000",
            "PROFILE_AGENT_CONTEXT_COMPACTION_RATIO": "0.5",
            "PROFILE_AGENT_CONTEXT_RECENT_MESSAGES": "8",
        }
        with patch.dict(os.environ, settings, clear=False):
            for index in range(24):
                self.store.append(
                    1,
                    11,
                    agent_id="course-knowledge-retrieval-agent",
                    agent_name="知识检索智能体",
                    message_type="agent_event",
                    status="complete",
                    content=f"第 {index + 1} 次检索完成：" + ("本草证据与引用片段。" * 32),
                    run_id=f"run-{index}",
                    dedupe_key=f"message-{index}",
                )
            context = self.store.context(1, 11)

        self.assertEqual(context["messageCount"], 24)
        self.assertGreater(context["summaryVersion"], 0)
        self.assertGreater(context["compactedThroughSequence"], 0)
        self.assertIn("画像级智能体群聊压缩摘要", context["summary"])
        self.assertLessEqual(len(context["recentMessages"]), 8)
        with closing(sqlite3.connect(self.db_path)) as conn:
            snapshot_count = conn.execute(
                "SELECT COUNT(*) FROM profile_agent_context_snapshots"
            ).fetchone()[0]
            compacted_count = conn.execute(
                "SELECT COUNT(*) FROM profile_agent_messages WHERE compacted = 1"
            ).fetchone()[0]
        self.assertGreater(snapshot_count, 0)
        self.assertGreater(compacted_count, 0)

    def test_compacted_messages_are_restored_after_budget_increases(self):
        compact_settings = {
            "PROFILE_AGENT_CONTEXT_MAX_TOKENS": "2000",
            "PROFILE_AGENT_CONTEXT_COMPACTION_RATIO": "0.5",
            "PROFILE_AGENT_CONTEXT_RECENT_MESSAGES": "8",
        }
        with patch.dict(os.environ, compact_settings, clear=False):
            for index in range(24):
                self.store.append(
                    1,
                    11,
                    agent_id="course-knowledge-retrieval-agent",
                    agent_name="知识检索智能体",
                    message_type="agent_event",
                    status="complete",
                    content=f"第 {index + 1} 次检索完成：" + ("本草证据与引用片段。" * 32),
                    run_id=f"restore-run-{index}",
                    dedupe_key=f"restore-message-{index}",
                )
            compacted_context = self.store.context(1, 11)

        self.assertGreater(compacted_context["summaryVersion"], 0)
        self.assertLessEqual(len(compacted_context["recentMessages"]), 8)

        expanded_settings = {
            "PROFILE_AGENT_CONTEXT_MAX_TOKENS": "128000000",
            "PROFILE_AGENT_CONTEXT_COMPACTION_RATIO": "0.90",
            "PROFILE_AGENT_CONTEXT_RECENT_MESSAGES": "4096",
        }
        with patch.dict(os.environ, expanded_settings, clear=False):
            restored_context = self.store.context(1, 11)

        self.assertEqual(restored_context["summaryVersion"], 0)
        self.assertEqual(restored_context["compactedThroughSequence"], 0)
        self.assertEqual(restored_context["summary"], "")
        self.assertEqual(len(restored_context["recentMessages"]), 24)
        self.assertEqual(restored_context["contextBudget"]["maxTokens"], 128_000_000)
        with closing(sqlite3.connect(self.db_path)) as conn:
            compacted_count = conn.execute(
                "SELECT COUNT(*) FROM profile_agent_messages WHERE compacted = 1"
            ).fetchone()[0]
        self.assertEqual(compacted_count, 0)


if __name__ == "__main__":
    unittest.main()
