from __future__ import annotations

import sqlite3
import unittest
from unittest.mock import patch

from database_schema import init_auth_schema
from learning_document import generate_learning_document, get_learning_document, list_learning_documents, save_learning_document


class LearningDocumentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = {
            "topic": "STM32 GPIO",
            "requirements": "面向初学者，突出调试证据",
            "profile": {
                "id": 7,
                "chatStudentProfile": {
                    "学习目标": "完成 GPIO 实验",
                    "资源偏好": "图文讲义",
                },
                "aiAnalysis": {
                    "learningStyle": "项目实践驱动",
                    "weaknesses": ["GPIO 模式辨析", "调试效率"],
                },
            },
            "knowledgeSources": [
                {"id": "KB1", "title": "GPIO 课程资料", "source": "gpio.txt", "section": 1},
                {"id": "KB2", "title": "STM32 实验指导", "source": "lab.txt", "section": 2},
            ],
            "knowledgeContext": [
                {"citationId": "KB1", "title": "GPIO 课程资料", "excerpt": "GPIO 可配置为输入或输出模式。"},
                {"citationId": "KB2", "title": "STM32 实验指导", "excerpt": "实验前应先定义输入、预期输出和测量方式。"},
            ],
        }

    def test_llm_document_is_normalized_and_evaluated(self) -> None:
        raw = {
            "title": "STM32 GPIO 个性化讲义",
            "abstract": "结合画像和课程资料生成。",
            "audience": "嵌入式初学者",
            "learningObjectives": ["理解模式", "完成实验"],
            "sections": [
                {"title": f"章节 {index}", "content": f"课程内容 [KB{1 if index < 3 else 2}]", "keyPoints": ["关键点"]}
                for index in range(1, 5)
            ],
            "keyPoints": ["GPIO 配置"],
            "commonMistakes": ["型号不匹配"],
            "practiceTasks": [{"task": "完成 LED 实验", "expectedEvidence": "代码与现象", "hint": "先定义验收"}],
            "summary": "完成概念到实验闭环。",
            "references": [{"id": "KB1"}, {"id": "KB2"}],
            "verificationNotes": [],
        }
        with patch("learning_document.call_llm_json", return_value=raw):
            result = generate_learning_document(self.payload)
        self.assertEqual(result["source"], "llm")
        self.assertEqual(len(result["document"]["sections"]), 4)
        self.assertEqual(len(result["document"]["references"]), 2)
        self.assertTrue(result["qualityEvaluation"]["passed"])
        self.assertIn("# STM32 GPIO 个性化讲义", result["document"]["markdown"])

    def test_failed_llm_uses_grounded_marked_fallback(self) -> None:
        with patch("learning_document.call_llm_json", side_effect=RuntimeError("model timeout")):
            result = generate_learning_document(self.payload)
        self.assertEqual(result["source"], "knowledge-template-fallback")
        self.assertGreaterEqual(len(result["document"]["sections"]), 4)
        self.assertIn("model timeout", result["document"]["fallbackReason"])
        self.assertTrue(result["qualityEvaluation"]["passed"])

    def test_invalid_schema_is_repaired_by_second_model_call(self) -> None:
        invalid = {"title": "初稿", "sections": [{"title": "只有一节", "content": "内容 [KB1]"}]}
        repaired = {
            "title": "修订后的 GPIO 讲义",
            "abstract": "结构修订完成。",
            "learningObjectives": ["理解 GPIO"],
            "sections": [
                {"title": f"章节 {index}", "content": f"结构化内容 [KB1]", "keyPoints": ["要点"]}
                for index in range(1, 5)
            ],
            "practiceTasks": [{"task": "完成实验", "expectedEvidence": "实验记录"}],
            "references": [{"id": "KB1"}],
        }
        with patch("learning_document.call_llm_json", side_effect=[invalid, repaired]) as model:
            result = generate_learning_document(self.payload)
        self.assertEqual(model.call_count, 2)
        self.assertEqual(result["source"], "llm-schema-repaired")
        self.assertEqual(len(result["document"]["sections"]), 4)
        self.assertEqual(result["generationAttempts"][-1]["stage"], "schema_repair")

    def test_document_storage_is_user_isolated(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        init_auth_schema(conn)
        conn.executemany(
            "INSERT INTO users (id, username, display_name, password_hash, role, created_at, updated_at) VALUES (?, ?, ?, 'hash', 'user', 'now', 'now')",
            [(1, "user-1", "用户一"), (2, "user-2", "用户二")],
        )
        generated = {
            "source": "llm",
            "document": {"title": "测试讲义", "sections": [{"order": 1, "title": "一", "content": "内容"}]},
            "qualityEvaluation": {"score": 88, "passed": True},
        }
        saved = save_learning_document(
            conn,
            user_id=1,
            profile_report_id=0,
            task_id="task-document-1",
            run_id="run-1",
            topic="GPIO",
            generated=generated,
            timestamp="2026-07-11T23:00:00+08:00",
        )
        self.assertEqual(saved["title"], "测试讲义")
        self.assertEqual(len(list_learning_documents(conn, user_id=1)), 1)
        self.assertEqual(list_learning_documents(conn, user_id=2), [])
        self.assertEqual(get_learning_document(conn, user_id=2, document_id=saved["id"]), {})
        conn.close()


if __name__ == "__main__":
    unittest.main()
