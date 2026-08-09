from __future__ import annotations

import io
import sqlite3
import tempfile
import unittest
from pathlib import Path

import app as app_module
from course_knowledge import retrieve_course_knowledge
from database_schema import init_auth_schema
from private_knowledge import (
    add_knowledge_document,
    create_knowledge_collection,
    private_knowledge_scope,
    retrieve_private_knowledge,
)


class PrivateKnowledgeStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = Path(self.tempdir.name) / "private-knowledge.sqlite3"
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        init_auth_schema(self.conn)
        now = "2026-07-12T12:00:00+08:00"
        for user_id in (1, 2):
            self.conn.execute(
                """
                INSERT INTO users
                    (id, username, display_name, password_hash, role, avatar_url, created_at, updated_at)
                VALUES (?, ?, ?, 'hash', 'user', '/userlogo.png', ?, ?)
                """,
                (user_id, f"kb-user-{user_id}", f"KB User {user_id}", now, now),
            )
        self.conn.commit()

    def tearDown(self) -> None:
        self.conn.close()
        self.tempdir.cleanup()

    def test_private_retrieval_is_user_isolated_and_context_aware(self) -> None:
        collection = create_knowledge_collection(self.conn, 1, "用户一课程资料")
        add_knowledge_document(
            self.conn,
            1,
            collection["id"],
            filename="private-note.md",
            content="ZephyrPrivateConcept 是用户一自定义的 GPIO 调试口诀。".encode("utf-8"),
            mime_type="text/markdown",
        )
        self.conn.commit()

        owner = retrieve_private_knowledge(
            "ZephyrPrivateConcept",
            user_id=1,
            db_path=self.db_path,
        )
        stranger = retrieve_private_knowledge(
            "ZephyrPrivateConcept",
            user_id=2,
            db_path=self.db_path,
        )
        self.assertTrue(owner["grounded"])
        self.assertEqual(owner["hits"][0]["citationId"], "PKB1")
        self.assertEqual(owner["hits"][0]["scope"], "private")
        self.assertFalse(stranger["grounded"])

        with private_knowledge_scope(1, self.db_path):
            merged = retrieve_course_knowledge("ZephyrPrivateConcept", top_k=4)
        self.assertTrue(merged["grounded"])
        self.assertEqual(merged["activePrivateCollection"]["id"], collection["id"])
        self.assertIn("PKB1", {item["id"] for item in merged["citations"]})


class PrivateKnowledgeApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.original_db_path = app_module.AUTH_DB_PATH
        app_module.AUTH_DB_PATH = Path(cls.tempdir.name) / "private-knowledge-api.sqlite3"
        app_module.app.config.update(TESTING=True)
        with app_module.auth_db() as conn:
            init_auth_schema(conn)
            now = "2026-07-12T12:30:00+08:00"
            for user_id in (801, 802):
                conn.execute(
                    """
                    INSERT INTO users
                        (id, username, display_name, password_hash, role, avatar_url, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 'user', '/userlogo.png', ?, ?)
                    """,
                    (
                        user_id,
                        f"private-kb-api-{user_id}",
                        f"Private KB API {user_id}",
                        app_module.password_hash("private-kb-password"),
                        now,
                        now,
                    ),
                )
                with app_module.app.test_request_context(
                    "/api/auth/login",
                    headers={"User-Agent": "private-kb-api-test"},
                ):
                    token = app_module.create_session(conn, user_id)
                if user_id == 801:
                    cls.owner_token = token
                else:
                    cls.other_token = token
        cls.client = app_module.app.test_client()

    @classmethod
    def tearDownClass(cls) -> None:
        app_module.AUTH_DB_PATH = cls.original_db_path
        cls.tempdir.cleanup()

    @property
    def owner_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.owner_token}"}

    @property
    def other_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.other_token}"}

    def test_collection_upload_retrieve_and_cross_user_protection(self) -> None:
        created = self.client.post(
            "/api/knowledge/collections",
            headers=self.owner_headers,
            json={"name": "API 私有资料", "description": "用户上传课程资料"},
        )
        self.assertEqual(created.status_code, 201)
        collection_id = created.get_json()["data"]["id"]

        uploaded = self.client.post(
            f"/api/knowledge/collections/{collection_id}/documents",
            headers=self.owner_headers,
            data={
                "file": (
                    io.BytesIO("AuroraRegisterRule 仅属于用户一的寄存器规则。".encode("utf-8")),
                    "aurora.md",
                )
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(uploaded.status_code, 201)
        document_id = uploaded.get_json()["data"]["id"]

        retrieved = self.client.post(
            "/api/knowledge/retrieve",
            headers=self.owner_headers,
            json={"query": "AuroraRegisterRule", "topK": 4},
        )
        self.assertEqual(retrieved.status_code, 200)
        data = retrieved.get_json()["data"]
        self.assertEqual(data["activePrivateCollection"]["id"], collection_id)
        self.assertTrue(any(item.get("scope") == "private" for item in data["hits"]))

        other = self.client.post(
            "/api/knowledge/retrieve",
            headers=self.other_headers,
            json={"query": "AuroraRegisterRule", "topK": 4},
        )
        self.assertEqual(other.status_code, 200)
        self.assertFalse(any(item.get("scope") == "private" for item in other.get_json()["data"]["hits"]))

        forbidden_delete = self.client.delete(
            f"/api/knowledge/documents/{document_id}",
            headers=self.other_headers,
        )
        self.assertEqual(forbidden_delete.status_code, 404)


if __name__ == "__main__":
    unittest.main()
