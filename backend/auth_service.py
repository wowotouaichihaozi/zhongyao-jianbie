"""Authentication persistence, validation, sessions, and access decorators."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import smtplib
import sqlite3
import threading
import time
from dataclasses import dataclass
from email.message import EmailMessage
from functools import wraps
from pathlib import Path
from typing import Callable, Optional

import bcrypt
from flask import Response, g, jsonify, request

try:
    from api_config import setting_default
    from common import get_setting
    from database_schema import (
        init_auth_schema,
        recover_interrupted_learning_profile_portraits,
    )
    from learning_path_state import (
        migrate_user_learning_path_configs,
        seed_learning_path_config,
    )
except ImportError:  # pragma: no cover - package import fallback
    from .api_config import setting_default
    from .common import get_setting
    from .database_schema import (
        init_auth_schema,
        recover_interrupted_learning_profile_portraits,
    )
    from .learning_path_state import (
        migrate_user_learning_path_configs,
        seed_learning_path_config,
    )


@dataclass(frozen=True)
class AuthSettings:
    database_path: Path | Callable[[], Path]
    default_avatar: str
    admin_username: str
    admin_password: str
    session_cookie_name: str = "fswy_session"
    session_ttl_seconds: int = 7 * 24 * 60 * 60
    preview_token: str = "codex-preview-token"
    preview_username: str = "codex-preview"
    email_code_ttl_seconds: int = 10 * 60


class AuthService:
    """Owns authentication state instead of leaking it through the Flask entrypoint."""

    def __init__(self, settings: AuthSettings, timestamp: Callable[[], str]):
        self.settings = settings
        self.timestamp = timestamp
        self._rate_lock = threading.Lock()
        self._rate_buckets: dict[str, list[float]] = {}
        self._captcha_lock = threading.Lock()
        self._captchas: dict[str, dict] = {}
        self._email_code_lock = threading.Lock()
        self._email_codes: dict[str, dict] = {}

    @staticmethod
    def now_ts() -> int:
        return int(time.time())

    def database_path(self) -> Path:
        configured = self.settings.database_path
        return Path(configured() if callable(configured) else configured)

    def connect(self) -> sqlite3.Connection:
        database_path = self.database_path()
        database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(database_path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    def initialize_database(self) -> None:
        with self.connect() as connection:
            init_auth_schema(connection)
            recover_interrupted_learning_profile_portraits(connection)
            self.seed_admin(connection)
            seed_learning_path_config(connection)
            migrate_user_learning_path_configs(connection)

    @staticmethod
    def ensure_user_email_column(connection: sqlite3.Connection) -> None:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)").fetchall()}
        if "email" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN email TEXT")
        if "status" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN status TEXT NOT NULL DEFAULT 'enabled'")
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique "
            "ON users(email) WHERE email IS NOT NULL"
        )

    @staticmethod
    def password_hash(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")

    @staticmethod
    def password_matches(password: str, stored_hash: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
        except ValueError:
            return False

    def seed_admin(self, connection: sqlite3.Connection) -> None:
        timestamp = self.timestamp()
        username = self.settings.admin_username
        existing = connection.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            connection.execute(
                """
                UPDATE users
                SET display_name = ?, role = 'admin', avatar_url = ?, updated_at = ?,
                    failed_login_count = 0, locked_until = 0
                WHERE username = ?
                """,
                ("管理员", self.settings.default_avatar, timestamp, username),
            )
            return
        if not self.settings.admin_password:
            raise RuntimeError("首次启动必须通过环境变量 ADMIN_PASSWORD 配置管理员密码")
        connection.execute(
            """
            INSERT INTO users (username, display_name, password_hash, role, avatar_url, created_at, updated_at)
            VALUES (?, ?, ?, 'admin', ?, ?, ?)
            """,
            (
                username,
                "管理员",
                self.password_hash(self.settings.admin_password),
                self.settings.default_avatar,
                timestamp,
                timestamp,
            ),
        )

    def ensure_preview_user(self, connection: sqlite3.Connection) -> sqlite3.Row:
        timestamp = self.timestamp()
        username = self.settings.preview_username
        existing = connection.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            connection.execute(
                """
                UPDATE users
                SET email = ?, display_name = ?, role = 'user', status = 'enabled', avatar_url = ?, updated_at = ?
                WHERE username = ?
                """,
                ("codex-preview@local.dev", "Codex Preview", self.settings.default_avatar, timestamp, username),
            )
        else:
            connection.execute(
                """
                INSERT INTO users (username, email, display_name, password_hash, role, status, avatar_url, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'user', 'enabled', ?, ?, ?)
                """,
                (
                    username,
                    "codex-preview@local.dev",
                    "Codex Preview",
                    self.password_hash(secrets.token_urlsafe(32)),
                    self.settings.default_avatar,
                    timestamp,
                    timestamp,
                ),
            )
        return connection.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

    @staticmethod
    def normalize_username(value: object) -> str:
        return str(value or "").strip()

    @staticmethod
    def normalize_email(value: object) -> str:
        return str(value or "").strip().lower()

    @staticmethod
    def validate_username(username: str) -> Optional[str]:
        if not 3 <= len(username) <= 32:
            return "账号长度必须为 3-32 位"
        if not re.fullmatch(r"[A-Za-z0-9_@.\-\u4e00-\u9fa5]+", username):
            return "账号只能包含中文、字母、数字、下划线、点、@ 或短横线"
        return None

    @staticmethod
    def validate_email(email: str) -> Optional[str]:
        if not email:
            return "请输入邮箱"
        if len(email) > 254:
            return "邮箱长度不能超过 254 位"
        pattern = r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+"
        if not re.fullmatch(pattern, email):
            return "请输入正确的邮箱地址"
        return None

    def validate_login_identifier(self, identifier: str) -> Optional[str]:
        return self.validate_email(identifier) if "@" in identifier else self.validate_username(identifier)

    @staticmethod
    def validate_password(password: str) -> Optional[str]:
        if len(password) < 8:
            return "密码至少 8 位"
        kinds = sum(
            (
                bool(re.search(r"[a-z]", password)),
                bool(re.search(r"[A-Z]", password)),
                bool(re.search(r"\d", password)),
                bool(re.search(r"[^A-Za-z0-9]", password)),
            )
        )
        return "密码需至少包含字母、数字、符号中的两类" if kinds < 2 else None

    def public_user(self, row: sqlite3.Row | dict) -> dict:
        return {
            "id": int(row["id"]),
            "username": row["username"],
            "email": row["email"] if "email" in row.keys() else "",
            "displayName": row["display_name"],
            "role": row["role"],
            "status": row["status"] if "status" in row.keys() else "enabled",
            "avatarUrl": row["avatar_url"] or self.settings.default_avatar,
        }

    def auth_payload(self, row: sqlite3.Row | dict, token: str) -> dict:
        return {
            **self.public_user(row),
            "token": token,
            "expiresIn": self.settings.session_ttl_seconds,
        }

    @staticmethod
    def token_digest(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def client_ip() -> str:
        forwarded = request.headers.get("X-Forwarded-For", "")
        return (forwarded.split(",")[0].strip() or request.remote_addr or "unknown")[:80]

    @staticmethod
    def is_secure_request() -> bool:
        return request.is_secure or request.headers.get("X-Forwarded-Proto", "").lower() == "https"

    def set_session_cookie(self, response: Response, token: str) -> Response:
        response.set_cookie(
            self.settings.session_cookie_name,
            token,
            max_age=self.settings.session_ttl_seconds,
            httponly=True,
            secure=self.is_secure_request(),
            samesite="Strict",
            path="/",
        )
        return response

    def clear_session_cookie(self, response: Response) -> Response:
        response.delete_cookie(
            self.settings.session_cookie_name,
            path="/",
            samesite="Strict",
            secure=self.is_secure_request(),
        )
        return response

    def create_session(self, connection: sqlite3.Connection, user_id: int) -> str:
        token = secrets.token_urlsafe(48)
        issued = self.now_ts()
        connection.execute(
            """
            INSERT INTO sessions (user_id, token_hash, created_at, expires_at, ip, user_agent)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                self.token_digest(token),
                issued,
                issued + self.settings.session_ttl_seconds,
                self.client_ip(),
                request.headers.get("User-Agent", "")[:300],
            ),
        )
        return token

    def request_session_token(self) -> str:
        authorization = request.headers.get("Authorization", "")
        if authorization.lower().startswith("bearer "):
            return authorization.split(" ", 1)[1].strip()
        return request.cookies.get(self.settings.session_cookie_name, "")

    @staticmethod
    def is_local_preview_request() -> bool:
        host = (request.host or "").split(":", 1)[0].strip("[]").lower()
        origin = request.headers.get("Origin", "")
        referer = request.headers.get("Referer", "")
        return host in {"localhost", "127.0.0.1", "::1"} or any(
            value.startswith(prefix)
            for value in (origin, referer)
            for prefix in ("http://localhost:", "http://127.0.0.1:", "http://[::1]:")
        )

    def current_user_from_request(self) -> Optional[sqlite3.Row | dict]:
        token = self.request_session_token()
        if not token:
            return None
        with self.connect() as connection:
            if token == self.settings.preview_token and self.is_local_preview_request():
                return self.ensure_preview_user(connection)
            return connection.execute(
                """
                SELECT u.* FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token_hash = ? AND s.revoked_at = 0 AND s.expires_at > ?
                """,
                (self.token_digest(token), self.now_ts()),
            ).fetchone()

    def revoke_current_session(self) -> None:
        token = self.request_session_token()
        if not token:
            return
        with self.connect() as connection:
            connection.execute(
                "UPDATE sessions SET revoked_at = ? WHERE token_hash = ?",
                (self.now_ts(), self.token_digest(token)),
            )

    def rate_limit_bucket(self, name: str, limit: int, window_seconds: int) -> bool:
        now = time.time()
        key = f"{name}:{self.client_ip()}"
        with self._rate_lock:
            bucket = [item for item in self._rate_buckets.get(key, []) if now - item < window_seconds]
            if len(bucket) >= limit:
                self._rate_buckets[key] = bucket
                return False
            bucket.append(now)
            self._rate_buckets[key] = bucket
        return True

    def get_login_failure_count(self, username: str) -> int:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT failed_login_count FROM users WHERE username = ? OR email = ?",
                (username, self.normalize_email(username)),
            ).fetchone()
        return int(row["failed_login_count"]) if row else 0

    def captcha_required(self, username: str) -> bool:
        return self.get_login_failure_count(username) >= 2

    def create_captcha(self) -> dict:
        left, right = secrets.randbelow(8) + 2, secrets.randbelow(8) + 2
        captcha_id = secrets.token_urlsafe(18)
        with self._captcha_lock:
            self._captchas[captcha_id] = {
                "answer": str(left + right),
                "expires_at": self.now_ts() + 5 * 60,
            }
        return {"captchaId": captcha_id, "question": f"{left} + {right} = ?"}

    def verify_captcha(self, captcha_id: str, answer: str) -> bool:
        with self._captcha_lock:
            item = self._captchas.pop(str(captcha_id or ""), None)
        return bool(
            item
            and item["expires_at"] >= self.now_ts()
            and hmac.compare_digest(str(item["answer"]), str(answer or "").strip())
        )

    def email_code_digest(self, email: str, code: str) -> str:
        return hmac.new(
            self.settings.admin_password.encode("utf-8"),
            f"{self.normalize_email(email)}:{str(code or '').strip()}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def create_email_code(self, email: str) -> str:
        code = f"{secrets.randbelow(900000) + 100000}"
        with self._email_code_lock:
            self._email_codes[self.normalize_email(email)] = {
                "digest": self.email_code_digest(email, code),
                "expires_at": self.now_ts() + self.settings.email_code_ttl_seconds,
                "attempts": 0,
            }
        return code

    def verify_email_code(self, email: str, code: str) -> bool:
        normalized = self.normalize_email(email)
        with self._email_code_lock:
            item = self._email_codes.get(normalized)
            if not item or item["expires_at"] < self.now_ts():
                self._email_codes.pop(normalized, None)
                return False
            item["attempts"] = int(item.get("attempts") or 0) + 1
            if item["attempts"] > 5:
                self._email_codes.pop(normalized, None)
                return False
            valid = hmac.compare_digest(item["digest"], self.email_code_digest(normalized, code))
            if valid:
                self._email_codes.pop(normalized, None)
            return valid

    @staticmethod
    def smtp_enabled() -> bool:
        return bool(
            get_setting("SMTP_HOST", setting_default("SMTP_HOST"))
            and get_setting("SMTP_USERNAME", setting_default("SMTP_USERNAME"))
            and get_setting("SMTP_PASSWORD", setting_default("SMTP_PASSWORD"))
        )

    def send_email_code(self, email: str, code: str) -> None:
        host = get_setting("SMTP_HOST", setting_default("SMTP_HOST"))
        port = int(get_setting("SMTP_PORT", setting_default("SMTP_PORT") or "465"))
        username = get_setting("SMTP_USERNAME", setting_default("SMTP_USERNAME"))
        password = get_setting("SMTP_PASSWORD", setting_default("SMTP_PASSWORD"))
        from_email = get_setting("SMTP_FROM_EMAIL", setting_default("SMTP_FROM_EMAIL")) or username
        from_name = get_setting("SMTP_FROM_NAME", setting_default("SMTP_FROM_NAME")) or "飞声望影"
        use_ssl = get_setting("SMTP_USE_SSL", setting_default("SMTP_USE_SSL")).lower() == "true"
        use_tls = get_setting("SMTP_USE_TLS", setting_default("SMTP_USE_TLS")).lower() == "true"
        if not (host and username and password and from_email):
            raise RuntimeError("SMTP mail service is not configured")
        message = EmailMessage()
        message["Subject"] = "飞声望影注册验证码"
        message["From"] = f"{from_name} <{from_email}>"
        message["To"] = email
        message.set_content(
            "\n".join(
                (
                    "您好，",
                    "",
                    f"您的注册验证码是：{code}",
                    f"验证码 {self.settings.email_code_ttl_seconds // 60} 分钟内有效，请勿转发给他人。",
                    "",
                    "如非本人操作，请忽略此邮件。",
                )
            )
        )
        smtp_factory = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
        with smtp_factory(host, port, timeout=15) as server:
            if use_tls and not use_ssl:
                server.starttls()
            server.login(username, password)
            server.send_message(message)

    def require_auth(self, function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            user = self.current_user_from_request()
            if not user:
                return jsonify({"code": 401, "msg": "请先登录"}), 401
            g.current_user = user
            return function(*args, **kwargs)

        return wrapper

    @staticmethod
    def admin_ok(data: dict | list | str | int | None = None, msg: str = "ok"):
        return jsonify({"code": "0000", "msg": msg, "data": data})

    def require_admin(self, function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            user = getattr(g, "current_user", None) or self.current_user_from_request()
            if not user:
                return jsonify({"code": 401, "msg": "请先登录"}), 401
            if user["role"] != "admin":
                return jsonify({"code": 403, "msg": "需要管理员权限"}), 403
            g.current_user = user
            return function(*args, **kwargs)

        return wrapper

    def require_super_admin(self, function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            user = getattr(g, "current_user", None) or self.current_user_from_request()
            if not user:
                return jsonify({"code": 401, "msg": "请先登录"}), 401
            if user["role"] != "admin" or str(user["username"]).lower() != self.settings.admin_username.lower():
                return jsonify({"code": 403, "msg": "仅超级管理员可查看服务器运行状态"}), 403
            g.current_user = user
            return function(*args, **kwargs)

        return wrapper

    def admin_user_info(self, row: sqlite3.Row | dict) -> dict:
        return {
            "userId": str(row["id"]),
            "userName": row["display_name"] or row["username"],
            "roles": ["R_SUPER", "admin"],
            "buttons": ["B_CODE1", "B_CODE2", "B_CODE3"],
            "avatar": row["avatar_url"] or self.settings.default_avatar,
            "email": row["email"] if "email" in row.keys() else "",
        }

    @staticmethod
    def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict]:
        return [dict(row) for row in rows]

    @staticmethod
    def day_key(timestamp: str | None) -> str:
        return str(timestamp or "")[:10] or "未知"
