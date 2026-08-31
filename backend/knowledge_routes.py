"""Knowledge-base, retrieval, network, and feedback HTTP routes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, ContextManager

from flask import Blueprint, g, jsonify, request

try:
    import knowledge_growth
    import private_knowledge as private_knowledge_service
    import showcase_network
    from course_knowledge import retrieve_course_knowledge
except ImportError:  # pragma: no cover - package import fallback
    from . import knowledge_growth
    from . import private_knowledge as private_knowledge_service
    from . import showcase_network
    from .course_knowledge import retrieve_course_knowledge


@dataclass(frozen=True)
class KnowledgeRouteDependencies:
    connection_factory: Callable[[], ContextManager]
    database_path: Callable[[], Path]
    knowledge_cache_path: Path
    now: Callable[[], str]


def create_knowledge_blueprint(dependencies: KnowledgeRouteDependencies) -> Blueprint:
    blueprint = Blueprint("knowledge", __name__)

    def current_user_id() -> int:
        return int(g.current_user["id"])

    def private_error_response(exc: Exception):
        if isinstance(exc, private_knowledge_service.PrivateKnowledgeNotFoundError):
            return jsonify({"code": 404, "msg": str(exc), "data": None}), 404
        if isinstance(exc, private_knowledge_service.PrivateKnowledgeConflictError):
            return jsonify({"code": 409, "msg": str(exc), "data": None}), 409
        if isinstance(exc, private_knowledge_service.PrivateKnowledgeError):
            return jsonify({"code": 400, "msg": str(exc), "data": None}), 400
        raise exc

    @blueprint.get("/api/knowledge/collections")
    def collections_list():
        with dependencies.connection_factory() as conn:
            data = private_knowledge_service.list_knowledge_collections(conn, current_user_id())
        return jsonify({"code": 0, "msg": "ok", "data": data})

    @blueprint.post("/api/knowledge/collections")
    def collection_create():
        payload = request.get_json(silent=True) or {}
        try:
            with dependencies.connection_factory() as conn:
                collection = private_knowledge_service.create_knowledge_collection(
                    conn,
                    current_user_id(),
                    payload.get("name"),
                    payload.get("description") or "",
                    activate=bool(payload.get("activate", True)),
                    timestamp=dependencies.now(),
                )
        except Exception as exc:
            return private_error_response(exc)
        return jsonify({"code": 0, "msg": "知识库已创建", "data": collection}), 201

    @blueprint.patch("/api/knowledge/collections/<int:collection_id>")
    def collection_update(collection_id: int):
        payload = request.get_json(silent=True) or {}
        try:
            with dependencies.connection_factory() as conn:
                collection = private_knowledge_service.update_knowledge_collection(
                    conn,
                    current_user_id(),
                    collection_id,
                    name=payload.get("name") if "name" in payload else None,
                    description=payload.get("description") if "description" in payload else None,
                    timestamp=dependencies.now(),
                )
        except Exception as exc:
            return private_error_response(exc)
        return jsonify({"code": 0, "msg": "知识库已更新", "data": collection})

    @blueprint.post("/api/knowledge/collections/<int:collection_id>/activate")
    def collection_activate(collection_id: int):
        try:
            with dependencies.connection_factory() as conn:
                collection = private_knowledge_service.activate_knowledge_collection(
                    conn,
                    current_user_id(),
                    collection_id,
                    timestamp=dependencies.now(),
                )
        except Exception as exc:
            return private_error_response(exc)
        return jsonify({"code": 0, "msg": "已设为当前知识库", "data": collection})

    @blueprint.delete("/api/knowledge/collections/<int:collection_id>")
    def collection_delete(collection_id: int):
        try:
            with dependencies.connection_factory() as conn:
                data = private_knowledge_service.delete_knowledge_collection(
                    conn,
                    current_user_id(),
                    collection_id,
                )
        except Exception as exc:
            return private_error_response(exc)
        return jsonify({"code": 0, "msg": "知识库已删除", "data": data})

    @blueprint.post("/api/knowledge/collections/<int:collection_id>/documents")
    def document_upload(collection_id: int):
        upload = request.files.get("file")
        if upload is None or not str(upload.filename or "").strip():
            return jsonify({"code": 400, "msg": "请选择要上传的文件", "data": None}), 400
        content = upload.stream.read(private_knowledge_service.MAX_UPLOAD_BYTES + 1)
        try:
            with dependencies.connection_factory() as conn:
                document = private_knowledge_service.add_knowledge_document(
                    conn,
                    current_user_id(),
                    collection_id,
                    filename=str(upload.filename),
                    content=content,
                    mime_type=str(upload.mimetype or "application/octet-stream"),
                    timestamp=dependencies.now(),
                )
        except Exception as exc:
            return private_error_response(exc)
        return jsonify({"code": 0, "msg": "文件已解析并写入知识库", "data": document}), 201

    @blueprint.delete("/api/knowledge/documents/<int:document_id>")
    def document_delete(document_id: int):
        try:
            with dependencies.connection_factory() as conn:
                data = private_knowledge_service.delete_knowledge_document(
                    conn,
                    current_user_id(),
                    document_id,
                )
        except Exception as exc:
            return private_error_response(exc)
        return jsonify({"code": 0, "msg": "文档已删除", "data": data})

    @blueprint.route("/api/knowledge/retrieve", methods=["GET", "POST"])
    def retrieve():
        payload = (request.get_json(silent=True) or {}) if request.method == "POST" else {}
        query = str(
            payload.get("query")
            or payload.get("topic")
            or request.args.get("query")
            or request.args.get("topic")
            or ""
        ).strip()
        if not query:
            return jsonify({"code": 400, "msg": "query 不能为空", "data": None}), 400
        try:
            top_k = max(1, min(12, int(payload.get("topK") or request.args.get("topK") or 6)))
        except (TypeError, ValueError):
            top_k = 6
        collection_id = payload.get("collectionId") or request.args.get("collectionId")
        try:
            collection_id = int(collection_id) if collection_id not in {None, ""} else None
        except (TypeError, ValueError):
            return jsonify({"code": 400, "msg": "collectionId 必须是整数", "data": None}), 400
        result = retrieve_course_knowledge(
            query,
            top_k=top_k,
            user_id=current_user_id(),
            db_path=dependencies.database_path(),
            private_collection_id=collection_id,
        )
        return jsonify({"code": 0, "msg": "ok", "data": result})

    @blueprint.get("/api/knowledge-network/overview")
    def network_overview():
        collection_id = request.args.get("collectionId", type=int)
        view = str(request.args.get("view") or "overview").strip().lower()
        if view not in {"overview", "atlas"}:
            return jsonify({"code": 400, "msg": "view 必须为 overview 或 atlas", "data": None}), 400
        node_limit = request.args.get("limit", default=15000 if view == "atlas" else 180, type=int)
        node_limit = max(180, min(20000, node_limit or 180))
        with dependencies.connection_factory() as conn:
            data = showcase_network.knowledge_overview(
                conn,
                current_user_id(),
                dependencies.knowledge_cache_path,
                collection_id=collection_id,
                view=view,
                node_limit=node_limit,
            )
        return jsonify({"code": 0, "msg": "ok", "data": data})

    @blueprint.get("/api/knowledge-network/expand")
    def network_expand():
        node_id = str(request.args.get("nodeId") or "").strip()
        if not node_id or len(node_id) > 500:
            return jsonify({"code": 400, "msg": "nodeId 无效", "data": None}), 400
        limit = max(1, min(50, request.args.get("limit", default=30, type=int) or 30))
        try:
            with dependencies.connection_factory() as conn:
                data = showcase_network.expand_knowledge_node(
                    conn,
                    current_user_id(),
                    dependencies.knowledge_cache_path,
                    node_id,
                    limit,
                )
        except (TypeError, ValueError):
            return jsonify({"code": 400, "msg": "节点标识无效", "data": None}), 400
        return jsonify({"code": 0, "msg": "ok", "data": data})

    @blueprint.get("/api/knowledge-network/timeline")
    def network_timeline():
        limit = max(1, min(100, request.args.get("limit", default=40, type=int) or 40))
        with dependencies.connection_factory() as conn:
            events = showcase_network.knowledge_timeline(conn, current_user_id(), limit)
            summary = showcase_network.knowledge_growth_summary(conn, current_user_id())
        return jsonify({"code": 0, "msg": "ok", "data": {"events": events, "summary": summary}})

    @blueprint.get("/api/knowledge-growth/overview")
    def growth_overview():
        limit = max(1, min(100, request.args.get("limit", default=60, type=int) or 60))
        with dependencies.connection_factory() as conn:
            data = knowledge_growth.conversation_growth_overview(conn, current_user_id(), limit=limit)
        return jsonify({"code": 0, "msg": "ok", "data": data})

    @blueprint.post("/api/knowledge-network/feedback")
    def feedback_create():
        payload = request.get_json(silent=True) or {}
        title = str(payload.get("title") or "").strip()[:160]
        content = str(payload.get("content") or "").strip()
        run_id = str(payload.get("runId") or "").strip()[:160]
        evidence = payload.get("evidence") if isinstance(payload.get("evidence"), list) else []
        evidence = [item for item in evidence if isinstance(item, dict)][:20]
        try:
            collection_id = int(payload.get("collectionId") or 0)
            confidence = max(0.0, min(1.0, float(payload.get("confidence") or 0)))
        except (TypeError, ValueError):
            return jsonify({"code": 400, "msg": "collectionId 或 confidence 无效", "data": None}), 400
        if not title or len(content) < 20 or len(content) > 50000:
            return jsonify({"code": 400, "msg": "标题不能为空，正文长度须为 20 至 50000 字符", "data": None}), 400
        if not evidence:
            return jsonify({"code": 400, "msg": "反哺候选必须包含至少一条来源证据", "data": None}), 400
        timestamp = dependencies.now()
        user_id = current_user_id()
        with dependencies.connection_factory() as conn:
            collection = conn.execute(
                "SELECT id FROM private_knowledge_collections WHERE id = ? AND user_id = ? AND archived = 0",
                (collection_id, user_id),
            ).fetchone()
            if not collection:
                return jsonify({"code": 404, "msg": "目标知识库不存在", "data": None}), 404
            if run_id:
                run = conn.execute(
                    "SELECT run_id FROM agent_orchestration_runs WHERE run_id = ? AND user_id = ?",
                    (run_id, user_id),
                ).fetchone()
                if not run:
                    return jsonify({"code": 404, "msg": "来源运行记录不存在", "data": None}), 404
            cursor = conn.execute(
                """
                INSERT INTO knowledge_feedback_candidates
                    (user_id, collection_id, run_id, title, content, evidence_json, confidence,
                     status, review_note, reviewed_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', '', '', ?, ?)
                """,
                (
                    user_id,
                    collection_id,
                    run_id,
                    title,
                    content,
                    json.dumps(evidence, ensure_ascii=False),
                    confidence,
                    timestamp,
                    timestamp,
                ),
            )
            row = conn.execute(
                "SELECT * FROM knowledge_feedback_candidates WHERE id = ?",
                (int(cursor.lastrowid),),
            ).fetchone()
        return jsonify({"code": 0, "msg": "已进入待审核知识队列", "data": showcase_network.public_feedback_candidate(row)}), 201

    @blueprint.get("/api/knowledge-network/feedback")
    def feedback_list():
        user = g.current_user
        status = str(request.args.get("status") or "").strip().lower()
        scope_all = request.args.get("scope") == "all" and str(user["username"]) == "admin123" and user["role"] == "admin"
        clauses = [] if scope_all else ["user_id = ?"]
        values: list = [] if scope_all else [int(user["id"])]
        if status in {"pending", "approved", "rejected"}:
            clauses.append("status = ?")
            values.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        values.append(max(1, min(100, request.args.get("limit", default=50, type=int) or 50)))
        with dependencies.connection_factory() as conn:
            rows = conn.execute(
                f"SELECT * FROM knowledge_feedback_candidates {where} ORDER BY id DESC LIMIT ?",
                values,
            ).fetchall()
        return jsonify({"code": 0, "msg": "ok", "data": {"items": [showcase_network.public_feedback_candidate(row) for row in rows]}})

    @blueprint.post("/api/knowledge-network/feedback/<int:candidate_id>/review")
    def feedback_review(candidate_id: int):
        reviewer = g.current_user
        if str(reviewer["username"]) != "admin123" or reviewer["role"] != "admin":
            return jsonify({"code": 403, "msg": "仅 admin123 可审核知识反哺", "data": None}), 403
        payload = request.get_json(silent=True) or {}
        decision = str(payload.get("decision") or "").strip().lower()
        review_note = str(payload.get("reviewNote") or "").strip()[:1000]
        if decision not in {"approved", "rejected"}:
            return jsonify({"code": 400, "msg": "decision 必须为 approved 或 rejected", "data": None}), 400
        timestamp = dependencies.now()
        try:
            with dependencies.connection_factory() as conn:
                row = conn.execute(
                    "SELECT * FROM knowledge_feedback_candidates WHERE id = ?",
                    (candidate_id,),
                ).fetchone()
                if not row:
                    return jsonify({"code": 404, "msg": "反哺候选不存在", "data": None}), 404
                if row["status"] != "pending":
                    return jsonify({"code": 409, "msg": "该候选已经审核", "data": showcase_network.public_feedback_candidate(row)}), 409
                document_id = None
                if decision == "approved":
                    evidence = showcase_network.public_feedback_candidate(row)["evidence"]
                    source_lines = [
                        f"- {str(item.get('title') or item.get('source') or '来源')}："
                        f"{str(item.get('citation') or item.get('url') or item.get('excerpt') or '')}"
                        for item in evidence
                    ]
                    document_text = "\n".join(
                        [
                            f"# {row['title']}",
                            "",
                            str(row["content"]),
                            "",
                            "## 可追溯来源",
                            *source_lines,
                            "",
                            f"来源运行：{row['run_id'] or '用户提交'}",
                            f"审核时间：{timestamp}",
                        ]
                    )
                    document = private_knowledge_service.add_knowledge_document(
                        conn,
                        int(row["user_id"]),
                        int(row["collection_id"]),
                        filename=f"knowledge-feedback-{candidate_id}.md",
                        content=document_text.encode("utf-8"),
                        mime_type="text/markdown",
                        timestamp=timestamp,
                    )
                    document_id = int(document["id"])
                conn.execute(
                    """
                    UPDATE knowledge_feedback_candidates
                    SET status = ?, review_note = ?, reviewed_by = ?, reviewed_at = ?,
                        approved_document_id = ?, updated_at = ? WHERE id = ?
                    """,
                    (
                        decision,
                        review_note,
                        int(reviewer["id"]),
                        timestamp,
                        document_id,
                        timestamp,
                        candidate_id,
                    ),
                )
                updated = conn.execute(
                    "SELECT * FROM knowledge_feedback_candidates WHERE id = ?",
                    (candidate_id,),
                ).fetchone()
        except Exception as exc:
            return private_error_response(exc)
        message = "审核完成，内容已入库" if decision == "approved" else "候选已驳回"
        return jsonify({"code": 0, "msg": message, "data": showcase_network.public_feedback_candidate(updated)})

    return blueprint
