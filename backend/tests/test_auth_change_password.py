from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import app as app_module
from database_schema import init_auth_schema


class ChangePasswordApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.original_db_path = app_module.AUTH_DB_PATH
        app_module.AUTH_DB_PATH = Path(cls.tempdir.name) / "auth-test.sqlite3"
        app_module.app.config.update(TESTING=True)
        now = "2026-07-10T10:00:00+08:00"
        with app_module.auth_db() as conn:
            init_auth_schema(conn)
            conn.execute(
                """
                INSERT INTO users
                    (id, username, display_name, password_hash, role, avatar_url, created_at, updated_at)
                VALUES (201, 'password-user', 'Password User', ?, 'user', '/userlogo.png', ?, ?)
                """,
                (app_module.password_hash("Old-password-1"), now, now),
            )
            with app_module.app.test_request_context(
                "/api/auth/change-password",
                headers={"User-Agent": "auth-change-test"},
            ):
                cls.token = app_module.create_session(conn, 201)
        cls.client = app_module.app.test_client()
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    @classmethod
    def tearDownClass(cls) -> None:
        app_module.AUTH_DB_PATH = cls.original_db_path
        cls.tempdir.cleanup()

    def test_change_password_requires_current_password(self) -> None:
        response = self.client.post(
            "/api/auth/change-password",
            headers=self.headers,
            json={"currentPassword": "wrong-password", "newPassword": "New-password-2"},
        )
        self.assertEqual(response.status_code, 400)

    def test_change_password_updates_hash_without_storing_plaintext(self) -> None:
        response = self.client.post(
            "/api/auth/change-password",
            headers=self.headers,
            json={"currentPassword": "Old-password-1", "newPassword": "New-password-2"},
        )
        self.assertEqual(response.status_code, 200)
        with app_module.auth_db() as conn:
            row = conn.execute("SELECT password_hash FROM users WHERE id = 201").fetchone()
        self.assertTrue(app_module.password_matches("New-password-2", row["password_hash"]))
        self.assertNotIn("New-password-2", row["password_hash"])


if __name__ == "__main__":
    unittest.main()
