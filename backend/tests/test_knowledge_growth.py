import sqlite3
import unittest

from backend.database_schema import init_auth_schema
from backend.knowledge_growth import (
    conversation_growth_overview,
    extract_conversation_core,
    recent_memory_context,
    record_conversation_memory,
)


class KnowledgeGrowthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        init_auth_schema(self.conn)
        for user_id, username in ((1, "owner"), (2, "other")):
            self.conn.execute(
                """
                INSERT INTO users
                    (id, username, display_name, password_hash, role, avatar_url, created_at, updated_at)
                VALUES (?, ?, ?, 'hash', 'user', '', '2026-07-31T10:00:00+08:00', '2026-07-31T10:00:00+08:00')
                """,
                (user_id, username, username),
            )

    def tearDown(self) -> None:
        self.conn.close()

    def test_extracts_topics_and_user_learning_signals_without_inventing_facts(self) -> None:
        core = extract_conversation_core(
            "我想学 FreeRTOS，但总是弄不懂优先级反转。我更喜欢先看结构图。",
            "后续会安排互斥量实验。",
            {"topic": "任务同步"},
        )
        self.assertIn("FreeRTOS", core["topics"])
        self.assertIn("任务同步", core["topics"])
        signal_types = {item["type"] for item in core["signals"]}
        self.assertIn("学习目标", signal_types)
        self.assertIn("薄弱点", signal_types)
        self.assertIn("内容偏好", signal_types)
        self.assertIn("优先级反转", core["summary"])

    def test_turn_is_captured_then_completed_by_source_key(self) -> None:
        timestamp = "2026-07-31T10:00:00+08:00"
        captured = record_conversation_memory(
            self.conn, 1, source_type="xiaozhi", source_key="101",
            user_message="我想学习 STM32 DMA", timestamp=timestamp,
        )
        self.assertEqual(captured["status"], "captured")

        completed = record_conversation_memory(
            self.conn, 1, source_type="xiaozhi", source_key="101",
            user_message="我想学习 STM32 DMA", assistant_message="先从循环模式和剩余计数开始。",
            metadata={"topic": "STM32 DMA"}, timestamp="2026-07-31T10:00:02+08:00",
        )
        self.assertEqual(completed["id"], captured["id"])
        self.assertEqual(completed["status"], "complete")
        self.assertEqual(conversation_growth_overview(self.conn, 1)["stats"]["conversationTurns"], 1)

    def test_memories_are_user_isolated_and_available_to_agent_context(self) -> None:
        record_conversation_memory(
            self.conn, 1, source_type="profile-dialogue", source_key="1:1",
            user_message="我每天学习一小时", assistant_message="已记录学习节奏。",
            metadata={"topic": "学习节奏"}, timestamp="2026-07-31T10:00:00+08:00",
        )
        self.assertEqual(len(conversation_growth_overview(self.conn, 1)["memories"]), 1)
        self.assertEqual(len(recent_memory_context(self.conn, 1)), 1)
        self.assertEqual(conversation_growth_overview(self.conn, 2)["memories"], [])
        self.assertEqual(recent_memory_context(self.conn, 2), [])


if __name__ == "__main__":
    unittest.main()
