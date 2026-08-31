"""Public authentication and administrator HTTP routes."""

from __future__ import annotations

import hmac
import sqlite3
from dataclasses import dataclass
from typing import Callable

from flask import Blueprint, current_app, g, jsonify, request

try:
    from auth_service import AuthService
except ImportError:  # pragma: no cover - package import fallback
    from .auth_service import AuthService


@dataclass(frozen=True)
class AuthRouteDependencies:
    service: AuthService
    timestamp: Callable[[], str]
    platform_tools: Callable[[], dict]
    parse_json: Callable[[object, object], object]
    system_monitor: Callable[[], object]
    default_avatar: str
    preview_username: str
    auth_lock_seconds: int
    auth_max_failed_attempts: int
    login_ip_limit: int
    login_ip_window: int
    register_ip_limit: int
    register_ip_window: int
    email_ip_limit: int
    email_ip_window: int


def create_auth_blueprint(dependencies: AuthRouteDependencies) -> Blueprint:
    blueprint = Blueprint("auth_and_admin", __name__)
    auth = dependencies.service

    def agent_rows(connection: sqlite3.Connection) -> list[dict]:
        definitions = {
            task_type: (tool.get("label") or task_type, tool["agent"])
            for task_type, tool in dependencies.platform_tools().items()
        }
        rows = connection.execute(
            """
            SELECT task_type, COUNT(*) AS total_runs,
                   SUM(CASE WHEN status IN ('complete', 'completed', 'done', 'success') THEN 1 ELSE 0 END) AS success_runs,
                   SUM(CASE WHEN status IN ('failed', 'error') THEN 1 ELSE 0 END) AS failed_runs,
                   MAX(updated_at) AS last_run_at
            FROM xiaozhi_tasks GROUP BY task_type
            """
        ).fetchall()
        by_type = {row["task_type"]: row for row in rows}
        profile_count = connection.execute("SELECT COUNT(*) AS total FROM learning_profile_reports").fetchone()["total"]
        profile_last = connection.execute("SELECT MAX(created_at) AS last_at FROM learning_profile_reports").fetchone()["last_at"]
        result = []
        for task_type, (name, agent_id) in definitions.items():
            row = by_type.get(task_type)
            total = int(row["total_runs"] or 0) if row else 0
            success = int(row["success_runs"] or 0) if row else 0
            failed = int(row["failed_runs"] or 0) if row else 0
            last_run = row["last_run_at"] if row else ""
            if task_type == "profile_update":
                total += int(profile_count or 0)
                success += int(profile_count or 0)
                last_run = max([item for item in (last_run, profile_last) if item] or [""])
            result.append(
                {
                    "id": agent_id,
                    "type": task_type,
                    "name": name,
                    "status": "运行中" if total > success + failed else "就绪",
                    "totalRuns": total,
                    "successRuns": success,
                    "failedRuns": failed,
                    "successRate": round(success * 100 / total) if total else 100,
                    "avgDuration": "-",
                    "lastRunAt": last_run or "-",
                }
            )
        return result

    @staticmethod
    def region_demo(total_users: int, total_tasks: int) -> list[dict]:
        provinces = (
            ("北京", 96, "中医基础活跃度高", "阴阳、藏象"),
            ("上海", 88, "课件与题库生成较多", "四诊合参"),
            ("江苏", 82, "医案学习提交稳定", "八纲辨证"),
            ("浙江", 76, "视频检索使用频繁", "中药、方剂"),
            ("广东", 92, "学习访谈参与度高", "舌脉辨析"),
            ("四川", 68, "学习路径完成率提升中", "气血津液"),
            ("湖北", 63, "医案辨析练习较多", "脏腑辨证"),
            ("陕西", 58, "资料生成需求增加", "经络腧穴"),
        )
        base_users, base_tasks = max(total_users, 8), max(total_tasks, 16)
        return [
            {
                "name": name,
                "value": value,
                "userCount": max(1, base_users * (index + 2) // 18),
                "activity": value,
                "resourceCount": max(1, base_tasks * (index + 3) // 22),
                "profileRate": f"{min(96, 58 + index * 5)}%",
                "summary": summary,
                "weakPoints": weak,
            }
            for index, (name, value, summary, weak) in enumerate(provinces)
        ]

    @blueprint.post("/api/auth/email-code")
    def email_code():
        payload = request.get_json(silent=True) or {}
        if not auth.rate_limit_bucket("email-code", dependencies.email_ip_limit, dependencies.email_ip_window):
            return jsonify({"code": 429, "msg": "验证码发送过于频繁，请稍后再试"}), 429
        email = auth.normalize_email(payload.get("email"))
        error = auth.validate_email(email)
        if error:
            return jsonify({"code": 400, "msg": error}), 400
        with auth.connect() as connection:
            if connection.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
                return jsonify({"code": 409, "msg": "该邮箱已注册"}), 409
        if not auth.smtp_enabled():
            return jsonify({"code": 503, "msg": "邮件服务未配置，请先配置 SMTP 发件邮箱"}), 503
        code = auth.create_email_code(email)
        try:
            auth.send_email_code(email, code)
        except Exception:
            current_app.logger.exception("failed to send email verification code")
            return jsonify({"code": 502, "msg": "验证码发送失败，请检查邮箱服务配置"}), 502
        return jsonify(
            {
                "ok": True,
                "msg": "验证码已发送，请查收邮箱",
                "expiresIn": auth.settings.email_code_ttl_seconds,
            }
        )

    @blueprint.post("/api/auth/register")
    def register():
        payload = request.get_json(silent=True) or {}
        if not auth.rate_limit_bucket("register", dependencies.register_ip_limit, dependencies.register_ip_window):
            return jsonify({"code": 429, "msg": "注册请求过于频繁，请稍后再试"}), 429
        username = auth.normalize_username(payload.get("username"))
        email = auth.normalize_email(payload.get("email"))
        password = str(payload.get("password") or "")
        display_name = str(payload.get("displayName") or username).strip() or username
        error = auth.validate_username(username) or auth.validate_email(email) or auth.validate_password(password)
        if error:
            return jsonify({"code": 400, "msg": error}), 400
        if not auth.verify_email_code(email, str(payload.get("emailCode") or "").strip()):
            return jsonify({"code": 400, "msg": "邮箱验证码错误或已过期"}), 400
        if len(display_name) > 40:
            return jsonify({"code": 400, "msg": "昵称不能超过 40 个字符"}), 400
        timestamp = dependencies.timestamp()
        try:
            with auth.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO users (username, email, display_name, password_hash, role, avatar_url, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 'user', ?, ?, ?)
                    """,
                    (username, email, display_name, auth.password_hash(password), dependencies.default_avatar, timestamp, timestamp),
                )
                row = connection.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
                token = auth.create_session(connection, int(row["id"]))
                return auth.set_session_cookie(jsonify(auth.auth_payload(row, token)), token), 201
        except sqlite3.IntegrityError:
            return jsonify({"code": 409, "msg": "账号或邮箱已存在"}), 409

    @blueprint.post("/api/auth/login")
    def login():
        payload = request.get_json(silent=True) or {}
        if not auth.rate_limit_bucket("login", dependencies.login_ip_limit, dependencies.login_ip_window):
            return jsonify({"code": 429, "msg": "登录请求过于频繁，请稍后再试"}), 429
        username = auth.normalize_username(payload.get("username"))
        password = str(payload.get("password") or "")
        error = auth.validate_login_identifier(username)
        if error or not password:
            return jsonify({"code": 400, "msg": error or "请输入密码"}), 400
        if auth.captcha_required(username) and not auth.verify_captcha(
            str(payload.get("captchaId") or ""), str(payload.get("captchaAnswer") or "")
        ):
            return jsonify({"code": 403, "msg": "请输入正确验证码", "captchaRequired": True, **auth.create_captcha()}), 403
        with auth.connect() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE username = ? OR email = ?",
                (username, auth.normalize_email(username)),
            ).fetchone()
            if not row:
                return jsonify({"code": 401, "msg": "账号或密码错误", "captchaRequired": True, **auth.create_captcha()}), 401
            if int(row["locked_until"] or 0) > auth.now_ts():
                retry_after = int(row["locked_until"]) - auth.now_ts()
                return jsonify({"code": 423, "msg": f"账号已临时锁定，请 {max(1, retry_after // 60)} 分钟后再试"}), 423
            if "status" in row.keys() and row["status"] == "disabled":
                return jsonify({"code": 423, "msg": "账号已被管理员禁用，请联系管理员"}), 423
            if not auth.password_matches(password, row["password_hash"]):
                failures = int(row["failed_login_count"] or 0) + 1
                locked_until = auth.now_ts() + dependencies.auth_lock_seconds if failures >= dependencies.auth_max_failed_attempts else 0
                connection.execute(
                    "UPDATE users SET failed_login_count = ?, locked_until = ?, updated_at = ? WHERE id = ?",
                    (failures, locked_until, dependencies.timestamp(), row["id"]),
                )
                captcha = auth.create_captcha() if failures >= 2 else {}
                status = 423 if locked_until else 401
                message = "账号已临时锁定，请 10 分钟后再试" if locked_until else "账号或密码错误"
                return jsonify({"code": status, "msg": message, "captchaRequired": failures >= 2, **captcha}), status
            now = dependencies.timestamp()
            connection.execute(
                "UPDATE users SET failed_login_count = 0, locked_until = 0, last_login_at = ?, updated_at = ? WHERE id = ?",
                (now, now, row["id"]),
            )
            token = auth.create_session(connection, int(row["id"]))
            refreshed = connection.execute("SELECT * FROM users WHERE id = ?", (row["id"],)).fetchone()
            return auth.set_session_cookie(jsonify(auth.auth_payload(refreshed, token)), token)

    @blueprint.post("/api/admin-auth/login")
    def admin_login():
        payload = request.get_json(silent=True) or {}
        username = auth.normalize_username(payload.get("username") or payload.get("userName"))
        password = str(payload.get("password") or "")
        if not username or not password:
            return jsonify({"code": 400, "msg": "请输入管理员账号和密码"}), 400
        with auth.connect() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE username = ? OR email = ?",
                (username, auth.normalize_email(username)),
            ).fetchone()
            if not row or not auth.password_matches(password, row["password_hash"]):
                return jsonify({"code": 401, "msg": "账号或密码错误"}), 401
            if row["role"] != "admin":
                return jsonify({"code": 403, "msg": "当前账号不是管理员"}), 403
            if "status" in row.keys() and row["status"] == "disabled":
                return jsonify({"code": 423, "msg": "账号已被禁用"}), 423
            now = dependencies.timestamp()
            connection.execute(
                "UPDATE users SET failed_login_count = 0, locked_until = 0, last_login_at = ?, updated_at = ? WHERE id = ?",
                (now, now, row["id"]),
            )
            token = auth.create_session(connection, int(row["id"]))
            refreshed = connection.execute("SELECT * FROM users WHERE id = ?", (row["id"],)).fetchone()
            response = auth.admin_ok({"token": token, "refreshToken": token, "userInfo": auth.admin_user_info(refreshed)})
            return auth.set_session_cookie(response, token)

    @blueprint.get("/api/admin-auth/getUserInfo")
    @auth.require_admin
    def admin_user_info():
        return auth.admin_ok(auth.admin_user_info(g.current_user))

    @blueprint.post("/api/admin-auth/refreshToken")
    def refresh_admin_token():
        user = auth.current_user_from_request()
        if not user or user["role"] != "admin":
            return jsonify({"code": 401, "msg": "登录已失效"}), 401
        token = auth.request_session_token()
        return auth.admin_ok({"token": token, "refreshToken": token})

    @blueprint.post("/api/auth/logout")
    def logout():
        auth.revoke_current_session()
        return auth.clear_session_cookie(jsonify({"ok": True}))

    @blueprint.get("/api/auth/captcha")
    def captcha():
        return jsonify(auth.create_captcha())

    @blueprint.get("/api/auth/me")
    def me():
        return jsonify(auth.public_user(g.current_user))

    @blueprint.post("/api/auth/change-password")
    def change_password():
        payload = request.get_json(silent=True) or {}
        current_password = str(payload.get("currentPassword") or "")
        new_password = str(payload.get("newPassword") or "")
        if not current_password:
            return jsonify({"code": 400, "msg": "请输入当前密码"}), 400
        error = auth.validate_password(new_password)
        if error:
            return jsonify({"code": 400, "msg": error}), 400
        if hmac.compare_digest(current_password, new_password):
            return jsonify({"code": 400, "msg": "新密码不能与当前密码相同"}), 400
        user_id = int(g.current_user["id"])
        with auth.connect() as connection:
            row = connection.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,)).fetchone()
            if not row or not auth.password_matches(current_password, row["password_hash"]):
                return jsonify({"code": 400, "msg": "当前密码不正确"}), 400
            connection.execute(
                "UPDATE users SET password_hash = ?, failed_login_count = 0, locked_until = 0, updated_at = ? WHERE id = ?",
                (auth.password_hash(new_password), dependencies.timestamp(), user_id),
            )
        return jsonify({"ok": True, "msg": "密码修改成功"})

    @blueprint.get("/api/admin/dashboard")
    @auth.require_admin
    def dashboard():
        with auth.connect() as connection:
            counts = {
                "totalUsers": connection.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"],
                "enabledUsers": connection.execute("SELECT COUNT(*) AS n FROM users WHERE COALESCE(status, 'enabled') != 'disabled'").fetchone()["n"],
                "profileReports": connection.execute("SELECT COUNT(*) AS n FROM learning_profile_reports").fetchone()["n"],
                "agentRuns": connection.execute("SELECT COUNT(*) AS n FROM xiaozhi_tasks").fetchone()["n"],
                "eventCount": connection.execute("SELECT COUNT(*) AS n FROM xiaozhi_events").fetchone()["n"],
                "activeUsers": connection.execute("SELECT COUNT(DISTINCT user_id) AS n FROM xiaozhi_events WHERE created_at >= datetime('now', '-7 days')").fetchone()["n"],
            }
            user_trend = auth.rows_to_dicts(connection.execute("SELECT substr(created_at, 1, 10) AS date, COUNT(*) AS count FROM users GROUP BY substr(created_at, 1, 10) ORDER BY date DESC LIMIT 7").fetchall())[::-1]
            distribution = auth.rows_to_dicts(connection.execute("SELECT task_type AS name, COUNT(*) AS value FROM xiaozhi_tasks GROUP BY task_type ORDER BY value DESC").fetchall())
            recent_events = auth.rows_to_dicts(connection.execute("SELECT e.id, e.event_type AS type, e.title, e.route, e.created_at AS createdAt, u.username, u.display_name AS displayName FROM xiaozhi_events e JOIN users u ON u.id = e.user_id ORDER BY e.id DESC LIMIT 10").fetchall())
            recent_tasks = auth.rows_to_dicts(connection.execute("SELECT t.id, t.task_id AS taskId, t.task_type AS taskType, t.title, t.status, t.route, t.error, t.created_at AS createdAt, t.updated_at AS updatedAt, u.username, u.display_name AS displayName FROM xiaozhi_tasks t JOIN users u ON u.id = t.user_id ORDER BY t.id DESC LIMIT 10").fetchall())
            agents = agent_rows(connection)
        counts["agentRuns"] = int(counts["agentRuns"] or 0) + int(counts["profileReports"] or 0)
        metrics = {key: int(value or 0) for key, value in counts.items()}
        return auth.admin_ok({
            "metrics": metrics,
            "userTrend": user_trend,
            "resourceDistribution": distribution,
            "recentEvents": recent_events,
            "recentTasks": recent_tasks,
            "agents": agents,
            "regions": region_demo(metrics["totalUsers"], metrics["agentRuns"]),
        })

    @blueprint.get("/api/admin/users")
    @auth.require_admin
    def users():
        page = max(1, int(request.args.get("current") or request.args.get("page") or 1))
        size = min(100, max(1, int(request.args.get("size") or request.args.get("pageSize") or 10)))
        keyword = str(request.args.get("keyword") or request.args.get("userName") or "").strip()
        role, status = str(request.args.get("role") or "").strip(), str(request.args.get("status") or "").strip()
        where, params = ["LOWER(u.username) <> LOWER(?)"], [dependencies.preview_username]
        if keyword:
            where.append("(u.username LIKE ? OR u.email LIKE ? OR u.display_name LIKE ?)")
            params.extend([f"%{keyword}%"] * 3)
        if role:
            where.append("u.role = ?")
            params.append(role)
        if status:
            where.append("COALESCE(u.status, 'enabled') = ?")
            params.append(status)
        where_sql = f"WHERE {' AND '.join(where)}"
        with auth.connect() as connection:
            total = connection.execute(f"SELECT COUNT(*) AS n FROM users u {where_sql}", params).fetchone()["n"]
            rows = connection.execute(
                f"""
                SELECT u.id, u.username, u.email, u.display_name AS displayName, u.role,
                       COALESCE(u.status, 'enabled') AS status, u.avatar_url AS avatarUrl,
                       u.created_at AS createdAt, u.updated_at AS updatedAt, u.last_login_at AS lastLoginAt,
                       COALESCE(r.report_count, 0) AS reportCount, COALESCE(t.task_count, 0) AS taskCount,
                       COALESCE(e.event_count, 0) AS eventCount, COALESCE(e.last_active_at, '') AS lastActiveAt
                FROM users u
                LEFT JOIN (SELECT user_id, COUNT(*) AS report_count FROM learning_profile_reports GROUP BY user_id) r ON r.user_id = u.id
                LEFT JOIN (SELECT user_id, COUNT(*) AS task_count FROM xiaozhi_tasks GROUP BY user_id) t ON t.user_id = u.id
                LEFT JOIN (SELECT user_id, COUNT(*) AS event_count, MAX(created_at) AS last_active_at FROM xiaozhi_events GROUP BY user_id) e ON e.user_id = u.id
                {where_sql} ORDER BY u.id DESC LIMIT ? OFFSET ?
                """,
                [*params, size, (page - 1) * size],
            ).fetchall()
        return auth.admin_ok({"records": auth.rows_to_dicts(rows), "total": int(total or 0), "current": page, "size": size})

    @blueprint.get("/api/admin/users/<int:user_id>")
    @auth.require_admin
    def user_detail(user_id: int):
        with auth.connect() as connection:
            user = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if not user:
                return jsonify({"code": 404, "msg": "用户不存在"}), 404
            profile_row = connection.execute("SELECT id, report_json, created_at FROM learning_profile_reports WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
            tasks = auth.rows_to_dicts(connection.execute("SELECT task_id AS taskId, task_type AS taskType, title, status, route, error, created_at AS createdAt, updated_at AS updatedAt FROM xiaozhi_tasks WHERE user_id = ? ORDER BY id DESC LIMIT 20", (user_id,)).fetchall())
            events = auth.rows_to_dicts(connection.execute("SELECT event_type AS type, title, route, payload_json AS payloadJson, created_at AS createdAt FROM xiaozhi_events WHERE user_id = ? ORDER BY id DESC LIMIT 20", (user_id,)).fetchall())
            messages = auth.rows_to_dicts(connection.execute("SELECT role, content, created_at AS createdAt FROM xiaozhi_messages WHERE user_id = ? ORDER BY id DESC LIMIT 20", (user_id,)).fetchall())
        profile = dependencies.parse_json(profile_row["report_json"], {}) if profile_row else None
        public = auth.public_user(user) | {"createdAt": user["created_at"], "updatedAt": user["updated_at"], "lastLoginAt": user["last_login_at"]}
        latest = {"id": profile_row["id"], "createdAt": profile_row["created_at"], "report": profile} if profile_row else None
        return auth.admin_ok({"user": public, "latestProfile": latest, "tasks": tasks, "events": events, "messages": messages})

    @blueprint.patch("/api/admin/users/<int:user_id>/status")
    @auth.require_admin
    def user_status(user_id: int):
        enabled = bool((request.get_json(silent=True) or {}).get("enabled"))
        if int(g.current_user["id"]) == user_id and not enabled:
            return jsonify({"code": 400, "msg": "不能禁用当前登录的管理员账号"}), 400
        status = "enabled" if enabled else "disabled"
        with auth.connect() as connection:
            connection.execute("UPDATE users SET status = ?, updated_at = ? WHERE id = ?", (status, dependencies.timestamp(), user_id))
        return auth.admin_ok({"id": user_id, "status": status})

    @blueprint.patch("/api/admin/users/<int:user_id>/role")
    @auth.require_admin
    def user_role(user_id: int):
        role = str((request.get_json(silent=True) or {}).get("role") or "").strip()
        if role not in {"user", "admin"}:
            return jsonify({"code": 400, "msg": "角色只能是 user 或 admin"}), 400
        if int(g.current_user["id"]) == user_id and role != "admin":
            return jsonify({"code": 400, "msg": "不能降低当前登录管理员的权限"}), 400
        with auth.connect() as connection:
            connection.execute("UPDATE users SET role = ?, updated_at = ? WHERE id = ?", (role, dependencies.timestamp(), user_id))
        return auth.admin_ok({"id": user_id, "role": role})

    @blueprint.post("/api/admin/users/<int:user_id>/reset-password")
    @auth.require_admin
    def reset_password(user_id: int):
        password = str((request.get_json(silent=True) or {}).get("password") or "")
        error = auth.validate_password(password)
        if error:
            return jsonify({"code": 400, "msg": error}), 400
        with auth.connect() as connection:
            connection.execute("UPDATE users SET password_hash = ?, failed_login_count = 0, locked_until = 0, updated_at = ? WHERE id = ?", (auth.password_hash(password), dependencies.timestamp(), user_id))
        return auth.admin_ok({"id": user_id}, "密码已重置")

    @blueprint.get("/api/admin/agents/overview")
    @auth.require_admin
    def agents_overview():
        with auth.connect() as connection:
            agents = agent_rows(connection)
            tasks = auth.rows_to_dicts(connection.execute("SELECT task_id AS taskId, task_type AS taskType, title, status, route, error, created_at AS createdAt, updated_at AS updatedAt FROM xiaozhi_tasks ORDER BY id DESC LIMIT 30").fetchall())
            trend = auth.rows_to_dicts(connection.execute("SELECT substr(created_at, 1, 10) AS date, COUNT(*) AS runs, SUM(CASE WHEN status IN ('failed', 'error') THEN 1 ELSE 0 END) AS failed FROM xiaozhi_tasks GROUP BY substr(created_at, 1, 10) ORDER BY date DESC LIMIT 7").fetchall())[::-1]
        return auth.admin_ok({"agents": agents, "recentTasks": tasks, "trend": trend})

    @blueprint.get("/api/admin/logs")
    @auth.require_admin
    def logs():
        page = max(1, int(request.args.get("current") or request.args.get("page") or 1))
        size = min(100, max(1, int(request.args.get("size") or request.args.get("pageSize") or 20)))
        with auth.connect() as connection:
            total = connection.execute("SELECT COUNT(*) AS n FROM xiaozhi_events").fetchone()["n"]
            rows = auth.rows_to_dicts(connection.execute("SELECT e.id, e.event_type AS type, e.title, e.route, e.payload_json AS payloadJson, e.created_at AS createdAt, u.username, u.display_name AS displayName FROM xiaozhi_events e JOIN users u ON u.id = e.user_id ORDER BY e.id DESC LIMIT ? OFFSET ?", (size, (page - 1) * size)).fetchall())
        return auth.admin_ok({"records": rows, "total": int(total or 0), "current": page, "size": size})

    @blueprint.get("/api/admin/runtime")
    @auth.require_super_admin
    def runtime():
        limit = min(240, max(10, int(request.args.get("limit") or 80)))
        monitor = dependencies.system_monitor()
        return auth.admin_ok({"snapshot": monitor.snapshot_and_record(), "history": monitor.recent(limit), "logFile": "logs/system-monitor.jsonl", "refreshSeconds": 10})

    return blueprint
