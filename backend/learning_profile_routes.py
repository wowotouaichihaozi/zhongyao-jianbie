"""Learning-profile, portrait, assessment, and profile-chat HTTP routes."""

from __future__ import annotations

from typing import Callable

from flask import Blueprint


class _DependencyProxy:
    def __init__(self, provider: Callable[[str], object]):
        self._provider = provider

    def __getattr__(self, name: str):
        return self._provider(name)


blueprint = Blueprint("learning_profile_api", __name__)
dependencies: _DependencyProxy


def create_learning_profile_blueprint(provider: Callable[[str], object]) -> Blueprint:
    global dependencies
    dependencies = _DependencyProxy(provider)
    return blueprint


@blueprint.post("/api/learning-profile/analyze")
def learning_profile_analyze():
    user = dependencies.g.get("current_user")
    if not user:
        return dependencies.jsonify({"code": 401, "msg": "未登录"}), 401
    payload = dependencies.request.get_json(silent=True) or {}
    with dependencies.auth_db() as conn:
        payload["learningEvidence"] = dependencies.learning_evidence_for_user(conn, int(user["id"]))
    context = dependencies.xiaozhi_latest_context(int(user["id"]))
    result = dependencies.xiaozhi_run_orchestrated(
        "profile_update",
        str(payload.get("chatBackground") or "更新学习画像"),
        payload,
        int(user["id"]),
        lambda managed_payload, _progress: dependencies.generate_profile_report(managed_payload),
        context=context,
        max_retries=0,
    )
    if result.get("source") not in {"llm", "llm-fallback", "fallback-rule"}:
        return dependencies.jsonify({
            "code": 502,
            "msg": "学习画像智能体调用失败",
            "error": result.get("error") or "agent did not return llm result",
        }), 502

    report = {
        "timestamp": dependencies.now_iso(),
        "scaleScores": payload.get("scaleScores"),
        "scaleTimestamp": payload.get("scaleTimestamp"),
        "chatBackground": payload.get("chatBackground"),
        "chatTimestamp": payload.get("chatTimestamp"),
        "chatStudentProfile": payload.get("chatStudentProfile") or {},
        "completedProfileDimensions": payload.get("completedProfileDimensions") or [],
        "missingProfileDimensions": payload.get("missingProfileDimensions") or [],
        "uploadFiles": payload.get("uploadFiles") or [],
        "uploadTimestamp": payload.get("uploadTimestamp"),
        "aiAnalysis": result,
    }
    with dependencies.auth_db() as conn:
        report, save_mode = dependencies.save_or_update_active_profile(
            conn,
            int(user["id"]),
            report,
            profile_name=str(payload.get("profileName") or ""),
            timestamp=report["timestamp"],
        )
    dependencies._schedule_profile_portrait_generation(int(user["id"]), int(report["id"]), force=True)
    learning_path_task = dependencies._schedule_profile_learning_path_generation(
        int(user["id"]),
        int(report["id"]),
    )
    if learning_path_task:
        report["learningPathTask"] = learning_path_task
    response = dependencies.jsonify(report)
    response.headers["X-Profile-Save-Mode"] = save_mode
    return response, 201 if save_mode == "created" else 200


@blueprint.post("/api/learning-profile/analyze-stream")
def learning_profile_analyze_stream():
    user = dependencies.g.get("current_user")
    if not user:
        return dependencies.jsonify({"code": 401, "msg": "未登录"}), 401
    user_id = int(user["id"])
    payload = dependencies.request.get_json(silent=True) or {}
    with dependencies.auth_db() as conn:
        payload["learningEvidence"] = dependencies.learning_evidence_for_user(conn, user_id)

    events: dependencies.queue.Queue[tuple[str, dict]] = dependencies.queue.Queue()
    runtime = dependencies.llm_runtime_for_user(user_id)
    stream_started = dependencies.time.perf_counter()

    def with_elapsed(event_payload: dict) -> dict:
        event_payload = dict(event_payload or {})
        event_payload.setdefault("elapsedMs", round((dependencies.time.perf_counter() - stream_started) * 1000))
        return event_payload

    def worker():
        try:
            events.put(("progress", with_elapsed({
                "agentId": "learner-context-agent",
                "agentName": dependencies.AGENT_CATALOG.get("learner-context-agent", {}).get("name") or "学习上下文智能体",
                "stage": "collect_data",
                "status": "complete",
                "progress": 6,
                "message": "正在读取量表、作业、对话和近期学习证据",
                "snapshot": {
                    "scaleScoreCount": len(payload.get("scaleScores") or []),
                    "uploadFileCount": len(payload.get("uploadFiles") or []),
                    "hasChatBackground": bool(payload.get("chatBackground")),
                    "completedProfileDimensionCount": len(payload.get("completedProfileDimensions") or []),
                    "missingProfileDimensionCount": len(payload.get("missingProfileDimensions") or []),
                    "evidenceKeys": sorted(str(key) for key in (payload.get("learningEvidence") or {}).keys())[:20],
                },
            })))
            events.put(("progress", with_elapsed({
                "agentId": dependencies.XIAOZHI_MASTER_AGENT_ID,
                "agentName": dependencies.AGENT_CATALOG.get(dependencies.XIAOZHI_MASTER_AGENT_ID, {}).get("name") or "嵌小智",
                "stage": "call_agent",
                "status": "running",
                "progress": 10,
                "message": "嵌小智正在编排学习画像分析与审核流程",
            })))
            result = dependencies.xiaozhi_run_orchestrated(
                "profile_update",
                str(payload.get("chatBackground") or "更新学习画像"),
                payload,
                user_id,
                lambda managed_payload, _progress: dependencies.generate_profile_report(managed_payload),
                context=dependencies.xiaozhi_latest_context(user_id),
                on_event=lambda event: events.put(("progress", with_elapsed(event))),
                max_retries=0,
            )
            events.put(("progress", with_elapsed({
                "agentId": "learning-profile-agent",
                "agentName": dependencies.AGENT_CATALOG.get("learning-profile-agent", {}).get("name") or "学习画像智能体",
                "stage": "agent_returned",
                "status": "complete",
                "progress": 92,
                "message": "学习画像智能体已返回结果，JSON 结构校验通过",
                "source": result.get("source"),
                "outputKeys": sorted(str(key) for key in result.keys())[:30],
            })))
            if result.get("source") not in {"llm", "llm-fallback", "fallback-rule"}:
                raise RuntimeError(result.get("error") or "学习画像智能体未返回有效模型结果")

            report = {
                "timestamp": dependencies.now_iso(),
                "scaleScores": payload.get("scaleScores"),
                "scaleTimestamp": payload.get("scaleTimestamp"),
                "chatBackground": payload.get("chatBackground"),
                "chatTimestamp": payload.get("chatTimestamp"),
                "chatStudentProfile": payload.get("chatStudentProfile") or {},
                "completedProfileDimensions": payload.get("completedProfileDimensions") or [],
                "missingProfileDimensions": payload.get("missingProfileDimensions") or [],
                "uploadFiles": payload.get("uploadFiles") or [],
                "uploadTimestamp": payload.get("uploadTimestamp"),
                "aiAnalysis": result,
            }
            events.put(("progress", with_elapsed({
                "agentId": "learning-profile-agent",
                "agentName": dependencies.AGENT_CATALOG.get("learning-profile-agent", {}).get("name") or "学习画像智能体",
                "stage": "save_report",
                "status": "running",
                "progress": 96,
                "message": "报告审核完成，正在保存画像和执行追踪记录",
            })))
            with dependencies.auth_db() as conn:
                report, save_mode = dependencies.save_or_update_active_profile(
                    conn,
                    user_id,
                    report,
                    profile_name=str(payload.get("profileName") or ""),
                    timestamp=report["timestamp"],
                )
            dependencies._schedule_profile_portrait_generation(user_id, int(report["id"]), force=True)
            learning_path_task = dependencies._schedule_profile_learning_path_generation(
                user_id,
                int(report["id"]),
            )
            events.put(("result", with_elapsed({
                "agentId": "learning-profile-agent",
                "agentName": dependencies.AGENT_CATALOG.get("learning-profile-agent", {}).get("name") or "学习画像智能体",
                "stage": "complete",
                "status": "complete",
                "progress": 100,
                "message": "画像报告已原位更新，人像与学习路径已进入后台队列"
                if save_mode == "updated"
                else "首份画像报告已通过审核并保存，人像与学习路径已进入后台队列",
                "reportId": int(report["id"]),
                "saveMode": save_mode,
                "learningPathTask": learning_path_task,
                "report": report,
            })))
        except Exception as exc:
            dependencies.app.logger.error("learning profile analyze stream failed: %s", type(exc).__name__)
            public_detail = dependencies.re.sub(
                r"(?i)((?:api[_-]?key|api[_-]?secret|authorization|password)\s*[:=]\s*)[^\s,;]+",
                r"\1***",
                dependencies.public_llm_error(exc),
            )[:1200]
            error_payload = {
                "agentId": "learning-profile-agent",
                "agentName": dependencies.AGENT_CATALOG.get("learning-profile-agent", {}).get("name") or "学习画像智能体",
                "stage": "error",
                "status": "failed",
                "progress": 100,
                "errorCode": "PROFILE_ANALYSIS_FAILED",
                "message": "画像分析流式生成失败",
                "detail": public_detail,
            }
            if isinstance(exc, dependencies.SkillContractError):
                error_payload["errorCode"] = "AGENT_CONTRACT_FAILED"
                error_payload["message"] = "学习画像结构化输出未通过 Skill 契约校验"
            elif isinstance(exc, dependencies.SkillReviewError):
                trace = exc.result.get("orchestration") if isinstance(exc.result.get("orchestration"), dict) else {}
                error_payload["errorCode"] = "AGENT_REVIEW_FAILED"
                error_payload["message"] = "学习画像未通过质量或安全审核"
                error_payload["runId"] = trace.get("runId") or ""
                error_payload["review"] = trace.get("review") or {}
            events.put(("error", with_elapsed(error_payload)))
        finally:
            events.put(("done", with_elapsed({
                "agentId": dependencies.XIAOZHI_MASTER_AGENT_ID,
                "agentName": dependencies.AGENT_CATALOG.get(dependencies.XIAOZHI_MASTER_AGENT_ID, {}).get("name") or "嵌小智",
                "stage": "done",
                "status": "complete",
                "progress": 100,
                "message": "画像分析流已结束",
            })))

    @dependencies.stream_with_context
    def generate_events():
        dependencies.threading.Thread(target=worker, daemon=True).start()
        yield dependencies._sse_event("start", with_elapsed({
            "agentId": dependencies.XIAOZHI_MASTER_AGENT_ID,
            "agentName": dependencies.AGENT_CATALOG.get(dependencies.XIAOZHI_MASTER_AGENT_ID, {}).get("name") or "嵌小智",
            "stage": "request_start",
            "status": "running",
            "progress": 0,
            "message": "嵌小智已接收学习画像生成任务",
            "modelRuntime": runtime,
            "snapshot": {
                "completedProfileDimensionCount": len(payload.get("completedProfileDimensions") or []),
                "missingProfileDimensionCount": len(payload.get("missingProfileDimensions") or []),
            },
        }))
        while True:
            try:
                event, event_payload = events.get(timeout=10)
            except dependencies.queue.Empty:
                yield dependencies._sse_event("heartbeat", with_elapsed({
                    "agentId": "learning-profile-agent",
                    "agentName": dependencies.AGENT_CATALOG.get("learning-profile-agent", {}).get("name") or "学习画像智能体",
                    "stage": "waiting",
                    "status": "running",
                    "message": "学习画像智能体仍在分析，请稍候",
                }))
                continue
            yield dependencies._sse_event(event, event_payload)
            if event == "done":
                break

    return dependencies.Response(
        generate_events(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


def _attach_profile_learning_path_statuses(
    conn: dependencies.sqlite3.Connection,
    user_id: int,
    profiles: list[dict],
) -> None:
    rows = conn.execute(
        """
        SELECT profile_report_id, config_json, updated_at
        FROM learning_path_profile_configs
        WHERE user_id = ?
        """,
        (int(user_id),),
    ).fetchall()
    configs: dict[int, tuple[dict, str]] = {}
    for row in rows:
        try:
            config = dependencies.normalize_learning_path_config(dependencies.json.loads(row["config_json"]))
        except (TypeError, dependencies.json.JSONDecodeError):
            continue
        configs[int(row["profile_report_id"])] = (config, str(row["updated_at"] or ""))

    legacy_row = conn.execute(
        "SELECT config_json, updated_at FROM user_learning_path_configs WHERE user_id = ?",
        (int(user_id),),
    ).fetchone()
    if legacy_row:
        try:
            legacy_config = dependencies.normalize_learning_path_config(dependencies.json.loads(legacy_row["config_json"]))
            legacy_profile_id = dependencies.learning_path_profile_report_id(legacy_config)
            if legacy_profile_id > 0 and legacy_profile_id not in configs:
                configs[legacy_profile_id] = (legacy_config, str(legacy_row["updated_at"] or ""))
        except (TypeError, dependencies.json.JSONDecodeError):
            pass

    for profile in profiles:
        profile_id = int(profile.get("id") or 0)
        config, updated_at = configs.get(profile_id, ({}, ""))
        weeks = config.get("weeks") if isinstance(config, dict) and isinstance(config.get("weeks"), list) else []
        visible_weeks = [
            week for week in weeks
            if isinstance(week, dict) and week.get("enabled") is not False and not week.get("placeholder")
        ]
        profile["learningPath"] = {
            "profileReportId": profile_id,
            "hasPath": bool(visible_weeks),
            "status": "ready" if visible_weeks else "not-generated",
            "weekCount": len(visible_weeks),
            "title": str((config.get("meta") or {}).get("title") or "个性化周学习计划") if config else "个性化周学习计划",
            "updatedAt": updated_at,
            "route": "/learning-path/stage/overview",
        }


@blueprint.get("/api/learning-profile/history")
def learning_profile_history():
    user = dependencies.g.get("current_user")
    if not user:
        return dependencies.jsonify({"code": 401, "msg": "未登录"}), 401
    with dependencies.auth_db() as conn:
        reports, state = dependencies.list_profiles_for_user(conn, int(user["id"]))
        _attach_profile_portrait_statuses(conn, int(user["id"]), reports)
        _attach_profile_learning_path_statuses(conn, int(user["id"]), reports)
    return dependencies.jsonify({"reports": reports, "activeReportId": state["activeReportId"], "state": state})


@blueprint.get("/api/learning-profile/profiles")
def learning_profile_profiles():
    user = dependencies.g.get("current_user")
    if not user:
        return dependencies.jsonify({"code": 401, "msg": "未登录"}), 401
    with dependencies.auth_db() as conn:
        profiles, state = dependencies.list_profiles_for_user(conn, int(user["id"]))
        _attach_profile_portrait_statuses(conn, int(user["id"]), profiles)
        _attach_profile_learning_path_statuses(conn, int(user["id"]), profiles)
    return dependencies.jsonify({
        "code": 0,
        "data": {
            "profiles": profiles,
            "activeReportId": state["activeReportId"],
            "state": state,
        },
    })


@blueprint.get("/api/learning-profile/profiles/<int:report_id>")
def learning_profile_profile_detail(report_id: int):
    user = dependencies.g.get("current_user")
    if not user:
        return dependencies.jsonify({"code": 401, "msg": "未登录"}), 401
    with dependencies.auth_db() as conn:
        profile = dependencies.get_profile_for_user(conn, int(user["id"]), report_id)
        if profile:
            _attach_profile_portrait_statuses(conn, int(user["id"]), [profile])
    if not profile:
        return dependencies.jsonify({"code": 404, "msg": "学习画像不存在"}), 404
    return dependencies.jsonify({"code": 0, "data": {"profile": profile}})


def _profile_portrait_metadata(report_id: int, source: str = "image2") -> dict:
    return {
        "reportId": int(report_id),
        "url": f"/api/learning-profile/profiles/{int(report_id)}/portrait",
        "source": str(source or "image2"),
        "status": "ready",
        "error": "",
    }


def _profile_portrait_status_payload(report_id: int, row: dependencies.sqlite3.Row | None) -> dict:
    status = str(row["status"] or "missing") if row and row["status"] else "missing"
    interrupted = bool(
        row
        and status == "generating"
        and _profile_portrait_job_is_stale(str(row["updated_at"] or ""))
    )
    if interrupted:
        status = "missing"
    ready = status == "ready" and int(row["image_size"] or 0) > 0 if row else False
    if status == "ready" and not ready:
        status = "missing"
    return {
        "reportId": int(report_id),
        "url": f"/api/learning-profile/profiles/{int(report_id)}/portrait" if ready else "",
        "source": str(row["source"] or "") if row else "",
        "status": "ready" if ready else status,
        "error": str(row["error"] or "")[:500] if row and status == "failed" else "",
        "updatedAt": str(row["updated_at"] or "") if row else "",
        "attemptCount": max(0, int(row["attempt_count"] or 0)) if row else 0,
        "persisted": bool(ready),
        "interrupted": interrupted,
    }


def _attach_profile_portrait_statuses(
    conn: dependencies.sqlite3.Connection,
    user_id: int,
    profiles: list[dict],
) -> None:
    if not profiles:
        return
    rows = conn.execute(
        """
        SELECT report_id, source, status, error, updated_at, attempt_count,
               LENGTH(image_blob) AS image_size
        FROM learning_profile_portraits
        WHERE user_id = ?
        """,
        (int(user_id),),
    ).fetchall()
    stored_by_report_id = {int(row["report_id"]): row for row in rows}
    for profile in profiles:
        report_id = int(profile.get("id") or 0)
        if report_id <= 0:
            continue
        profile["portrait"] = _profile_portrait_status_payload(
            report_id,
            stored_by_report_id.get(report_id),
        )


def _profile_portrait_record(
    conn: dependencies.sqlite3.Connection,
    user_id: int,
    report_id: int,
) -> tuple[dict, dependencies.sqlite3.Row | None]:
    profile = dependencies.get_profile_for_user(conn, int(user_id), int(report_id))
    if not profile:
        return {}, None
    row = conn.execute(
        """
        SELECT source, status, error, updated_at, generation_token, attempt_count,
               LENGTH(image_blob) AS image_size
        FROM learning_profile_portraits
        WHERE report_id = ? AND user_id = ?
        LIMIT 1
        """,
        (int(report_id), int(user_id)),
    ).fetchone()
    return profile, row


def _profile_portrait_job_is_stale(updated_at: str) -> bool:
    raw = str(updated_at or "").strip()
    if not raw:
        return True
    try:
        parsed = dependencies.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.astimezone()
        age = (dependencies.datetime.now().astimezone() - parsed.astimezone()).total_seconds()
        return age >= dependencies.PROFILE_PORTRAIT_STALE_SECONDS
    except (TypeError, ValueError, OverflowError):
        return True


def _save_profile_portrait_metadata(
    conn: dependencies.sqlite3.Connection,
    user_id: int,
    report_id: int,
    portrait: dict,
) -> dict:
    row = conn.execute(
        "SELECT report_json FROM learning_profile_reports WHERE id = ? AND user_id = ?",
        (int(report_id), int(user_id)),
    ).fetchone()
    if not row:
        raise LookupError("学习画像不存在")
    try:
        payload = dependencies.json.loads(str(row["report_json"] or "{}"))
    except (TypeError, ValueError, dependencies.json.JSONDecodeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    payload["portrait"] = dict(portrait)
    conn.execute(
        "UPDATE learning_profile_reports SET report_json = ? WHERE id = ? AND user_id = ?",
        (dependencies.json.dumps(payload, ensure_ascii=False), int(report_id), int(user_id)),
    )
    return dependencies.get_profile_for_user(conn, int(user_id), int(report_id))


def _profile_portrait_image_response(report_id: int):
    user = dependencies.g.get("current_user")
    if not user:
        return dependencies.jsonify({"code": 401, "msg": "未登录"}), 401
    with dependencies.auth_db() as conn:
        row = conn.execute(
            """
            SELECT p.image_blob, p.mime_type, p.status
            FROM learning_profile_reports r
            LEFT JOIN learning_profile_portraits p ON p.report_id = r.id AND p.user_id = r.user_id
            WHERE r.id = ? AND r.user_id = ?
            LIMIT 1
            """,
            (int(report_id), int(user["id"])),
        ).fetchone()
    if not row or row["status"] != "ready" or not row["image_blob"]:
        return dependencies.jsonify({"code": 404, "msg": "画像人像不存在"}), 404
    image_bytes = bytes(row["image_blob"])
    response = dependencies.Response(image_bytes, mimetype=str(row["mime_type"] or "image/png"))
    response.set_etag(dependencies.hashlib.sha256(image_bytes).hexdigest())
    response.cache_control.private = True
    response.cache_control.max_age = 86400
    return response.make_conditional(dependencies.request)


@blueprint.get("/api/learning-profile/profiles/<int:report_id>/portrait")
def learning_profile_portrait_file(report_id: int):
    return _profile_portrait_image_response(report_id)


@blueprint.get("/api/learning-profile/profiles/<int:report_id>/portrait/status")
def learning_profile_portrait_status(report_id: int):
    user = dependencies.g.get("current_user")
    if not user:
        return dependencies.jsonify({"code": 401, "msg": "未登录"}), 401
    with dependencies.auth_db() as conn:
        profile, stored = _profile_portrait_record(conn, int(user["id"]), report_id)
    if not profile:
        return dependencies.jsonify({"code": 404, "msg": "学习画像不存在"}), 404
    portrait = _profile_portrait_status_payload(report_id, stored)
    return dependencies.jsonify({"code": 0, "data": {"portrait": portrait}})


@blueprint.get("/api/learning-profile/portraits/<path:filename>")
def learning_profile_legacy_portrait_file(filename: str):
    match = dependencies.re.fullmatch(r"profile-(\d+)\.png", filename)
    if not match:
        return dependencies.jsonify({"code": 404, "msg": "画像人像不存在"}), 404
    return _profile_portrait_image_response(int(match.group(1)))


def _run_profile_portrait_generation(
    user_id: int,
    report_id: int,
    generation_token: str,
    force: bool,
) -> None:
    with dependencies.auth_db() as conn:
        profile, stored = _profile_portrait_record(conn, user_id, report_id)
    if (
        not profile
        or not stored
        or stored["status"] != "generating"
        or str(stored["generation_token"] or "") != generation_token
    ):
        return

    try:
        generated = dependencies.generate_profile_portrait(profile, report_id, force=force)
        image_bytes = generated.get("imageBytes") if isinstance(generated, dict) else None
        if not isinstance(image_bytes, (bytes, bytearray)) or not image_bytes:
            raise RuntimeError("画像人像生成结果缺少图片数据")
        mime_type = str(generated.get("mimeType") or "image/png")
        source = str(generated.get("source") or "image2")
    except Exception as exc:
        dependencies.app.logger.warning("learning profile portrait generation failed: %s", exc)
        with dependencies.auth_db() as conn:
            conn.execute(
                """
                UPDATE learning_profile_portraits
                SET image_blob = NULL, status = 'failed', error = ?, updated_at = ?
                WHERE report_id = ? AND user_id = ? AND generation_token = ?
                """,
                (str(exc)[:500], dependencies.now_iso(), int(report_id), int(user_id), generation_token),
            )
        return

    completed_at = dependencies.now_iso()
    with dependencies.auth_db() as conn:
        current_profile = dependencies.get_profile_for_user(conn, user_id, report_id)
        if not current_profile:
            return
        updated = conn.execute(
            """
            UPDATE learning_profile_portraits
            SET image_blob = ?, mime_type = ?, source = ?, status = 'ready',
                error = '', updated_at = ?
            WHERE report_id = ? AND user_id = ? AND generation_token = ?
            """,
            (
                dependencies.sqlite3.Binary(bytes(image_bytes)),
                mime_type,
                source,
                completed_at,
                int(report_id),
                int(user_id),
                generation_token,
            ),
        )
        if updated.rowcount:
            _save_profile_portrait_metadata(
                conn,
                user_id,
                report_id,
                _profile_portrait_metadata(report_id, source),
            )


def _queue_profile_portrait_generation(
    user_id: int,
    report_id: int,
    *,
    force: bool = False,
) -> tuple[dict, dict, bool]:
    generation_token = ""
    should_submit = False
    with dependencies.auth_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        profile, stored = _profile_portrait_record(conn, user_id, report_id)
        if not profile:
            raise LookupError("学习画像不存在")

        portrait = _profile_portrait_status_payload(report_id, stored)
        if portrait["status"] == "ready" and not force:
            return portrait, profile, False
        if (
            portrait["status"] == "generating"
            and stored
            and not _profile_portrait_job_is_stale(str(stored["updated_at"] or ""))
        ):
            return portrait, profile, False

        generation_token = dependencies.secrets.token_urlsafe(18)
        started_at = dependencies.now_iso()
        attempt_count = max(0, int(stored["attempt_count"] or 0)) + 1 if stored else 1
        conn.execute(
            """
            INSERT INTO learning_profile_portraits
                (report_id, user_id, image_blob, mime_type, source, status, error,
                 generation_token, attempt_count, created_at, updated_at)
            VALUES (?, ?, NULL, 'image/png', '', 'generating', '', ?, ?, ?, ?)
            ON CONFLICT(report_id) DO UPDATE SET
                user_id = excluded.user_id,
                image_blob = NULL,
                mime_type = excluded.mime_type,
                source = '',
                status = 'generating',
                error = '',
                generation_token = excluded.generation_token,
                attempt_count = excluded.attempt_count,
                updated_at = excluded.updated_at
            """,
            (
                int(report_id),
                int(user_id),
                generation_token,
                attempt_count,
                started_at,
                started_at,
            ),
        )
        should_submit = True
        portrait = {
            "reportId": int(report_id),
            "url": "",
            "source": "",
            "status": "generating",
            "error": "",
            "updatedAt": started_at,
            "attemptCount": attempt_count,
        }

    if should_submit:
        try:
            dependencies.PROFILE_PORTRAIT_EXECUTOR.submit(
                _run_profile_portrait_generation,
                int(user_id),
                int(report_id),
                generation_token,
                bool(force),
            )
        except Exception as exc:
            with dependencies.auth_db() as conn:
                conn.execute(
                    """
                    UPDATE learning_profile_portraits
                    SET status = 'failed', error = ?, updated_at = ?
                    WHERE report_id = ? AND user_id = ? AND generation_token = ?
                    """,
                    (str(exc)[:500], dependencies.now_iso(), int(report_id), int(user_id), generation_token),
                )
            raise
    return portrait, profile, should_submit


def _schedule_profile_portrait_generation(
    user_id: int,
    report_id: int,
    *,
    force: bool = False,
) -> None:
    if dependencies.app.config.get("TESTING") and not dependencies.app.config.get("PROFILE_PORTRAIT_BACKGROUND_IN_TESTS"):
        return
    try:
        _queue_profile_portrait_generation(user_id, report_id, force=force)
    except Exception:
        dependencies.app.logger.exception("could not schedule learning profile portrait generation")


@blueprint.post("/api/learning-profile/profiles/<int:report_id>/portrait")
def learning_profile_portrait_generate(report_id: int):
    user = dependencies.g.get("current_user")
    if not user:
        return dependencies.jsonify({"code": 401, "msg": "未登录"}), 401
    payload = dependencies.request.get_json(silent=True) or {}
    try:
        portrait, profile, started = _queue_profile_portrait_generation(
            int(user["id"]),
            report_id,
            force=bool(payload.get("force")),
        )
    except LookupError:
        return dependencies.jsonify({"code": 404, "msg": "学习画像不存在"}), 404
    except Exception as exc:
        dependencies.app.logger.exception("could not queue learning profile portrait generation")
        return dependencies.jsonify({"code": 500, "msg": "画像人像生成任务启动失败", "error": str(exc)[:300]}), 500

    if portrait["status"] == "ready" and profile.get("portrait") != portrait:
        with dependencies.auth_db() as conn:
            profile = _save_profile_portrait_metadata(conn, int(user["id"]), report_id, portrait)
    status_code = 202 if portrait["status"] == "generating" else 200
    return dependencies.jsonify({
        "code": 0,
        "data": {
            "portrait": portrait,
            "profile": profile,
            "started": bool(started),
        },
    }), status_code


@blueprint.get("/api/effect-assessment")
def effect_assessment_overview():
    user = dependencies.g.get("current_user")
    if not user:
        return dependencies.jsonify({"code": 401, "msg": "未登录"}), 401
    requested_profile_id = dependencies.request.args.get("profileId", type=int)
    with dependencies.auth_db() as conn:
        profile = dependencies.get_profile_for_user(conn, int(user["id"]), requested_profile_id) if requested_profile_id else dependencies.active_profile_for_user(conn, int(user["id"]))
        if not profile:
            return dependencies.jsonify({"code": 404, "msg": "请先完成学习画像"}), 404
        evidence = dependencies.learning_evidence_for_user(conn, int(user["id"]))
        history = dependencies._effect_assessment_records(conn, int(user["id"]), int(profile["id"]), limit=10)
    assessment = dependencies.effect_assessment_snapshot(profile, evidence)
    plan = assessment.get("pathAdjustmentPlan") or {}
    applied_record = dependencies._find_effect_assessment_plan_record(history, str(plan.get("planId") or ""))
    if applied_record and applied_record.get("status") == "applied":
        assessment["pathAdjustmentPlan"] = {
            **plan,
            "status": "applied",
            "appliedAt": applied_record.get("appliedAt") or (applied_record.get("pathAdjustment") or {}).get("appliedAt") or "",
            "assessmentId": applied_record.get("id"),
        }
    return dependencies.jsonify({
        "code": 0,
        "data": {
            "profile": profile,
            "evidence": evidence,
            "assessment": assessment,
            "history": history,
        },
    })


@blueprint.post("/api/effect-assessment/apply-adjustment")
def effect_assessment_apply_adjustment():
    user = dependencies.g.get("current_user")
    if not user:
        return dependencies.jsonify({"code": 401, "msg": "未登录"}), 401
    payload = dependencies.request.get_json(silent=True) or {}
    requested_profile_id = payload.get("profileId")
    try:
        requested_profile_id = int(requested_profile_id) if requested_profile_id else None
    except (TypeError, ValueError):
        return dependencies.jsonify({"code": 400, "msg": "画像 ID 无效"}), 400

    with dependencies.auth_db() as conn:
        profile = (
            dependencies.get_profile_for_user(conn, int(user["id"]), requested_profile_id)
            if requested_profile_id
            else dependencies.active_profile_for_user(conn, int(user["id"]))
        )
        if not profile:
            return dependencies.jsonify({"code": 404, "msg": "学习画像不存在"}), 404
        if not profile.get("isActive"):
            return dependencies.jsonify({"code": 409, "msg": "请先将该画像设为当前画像，再应用路径调整"}), 409
        evidence = dependencies.learning_evidence_for_user(conn, int(user["id"]))
        assessment = dependencies.effect_assessment_snapshot(profile, evidence)
        plan = assessment.get("pathAdjustmentPlan") or {}
        requested_plan_id = str(payload.get("planId") or "").strip()
        if requested_plan_id and requested_plan_id != str(plan.get("planId") or ""):
            return dependencies.jsonify({"code": 409, "msg": "学习证据已变化，请刷新评估后重新应用"}), 409
        if not plan.get("canApply"):
            return dependencies.jsonify({"code": 409, "msg": "当前没有可应用的路径调整任务"}), 409
        existing_records = dependencies._effect_assessment_records(conn, int(user["id"]), int(profile["id"]), limit=50)
        existing_record = dependencies._find_effect_assessment_plan_record(existing_records, str(plan.get("planId") or ""))
        if existing_record and existing_record.get("status") == "applied":
            return dependencies.jsonify({
                "code": 0,
                "msg": "该路径调整已应用",
                "data": {
                    "assessment": assessment,
                    "pathAdjustment": existing_record.get("pathAdjustment") or {},
                    "assessmentId": existing_record.get("id"),
                    "alreadyApplied": True,
                },
            })

    def apply_specialist(_managed_payload: dict, progress) -> dict:
        progress({"stage": "plan_path_adjustment", "status": "running", "progress": 55, "message": "正在校验评估建议与当前周学习路径"})
        path_adjustment = dependencies._effect_path_adjustment_preview(profile, assessment)
        progress({"stage": "path_adjustment_planned", "status": "complete", "progress": 100, "message": "路径调整方案已形成，等待总控质量与安全审核"})
        return {
            "message": "学习效果评估的路径调整方案已完成审核前规划。",
            "assessment": assessment,
            "scores": {
                "achievementRate": assessment.get("achievementRate"),
                "masteryRate": assessment.get("masteryRate"),
                "radarScores": assessment.get("radarScores"),
            },
            "summary": assessment.get("summary"),
            "recommendations": [
                str(item.get("acceptanceCriteria") or "")
                for item in (plan.get("tasks") or [])
                if isinstance(item, dict) and item.get("acceptanceCriteria")
            ],
            "adjustments": path_adjustment,
            "pathAdjustment": path_adjustment,
        }

    try:
        result = dependencies.xiaozhi_run_orchestrated(
            "effect_assessment",
            f"{profile.get('profileName') or '当前画像'}学习效果评估与路径调整",
            {
                "profileReportId": int(profile["id"]),
                "evidenceVersion": evidence.get("evidenceVersion"),
                "assessment": assessment,
                "pathAdjustmentPlan": plan,
                "action": "apply-path-adjustment",
            },
            int(user["id"]),
            apply_specialist,
            context=dependencies.xiaozhi_latest_context(int(user["id"])),
            max_retries=1,
        )
        run_id = str((result.get("orchestration") or {}).get("runId") or "")
        created_at = dependencies.now_iso()
        with dependencies.auth_db() as conn:
            path_adjustment = dependencies._apply_effect_path_adjustment(
                conn,
                int(user["id"]),
                profile,
                assessment,
            )
            stored_record = dependencies._find_effect_assessment_plan_record(
                dependencies._effect_assessment_records(conn, int(user["id"]), int(profile["id"]), limit=50),
                str(plan.get("planId") or ""),
            )
            if stored_record:
                assessment_id = int(stored_record["id"])
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO learning_effect_assessments
                        (user_id, profile_report_id, run_id, assessment_json, path_adjustment_json,
                         status, created_at, applied_at)
                    VALUES (?, ?, ?, ?, ?, 'applied', ?, ?)
                    """,
                    (
                        int(user["id"]),
                        int(profile["id"]),
                        run_id,
                        dependencies.json.dumps(assessment, ensure_ascii=False),
                        dependencies.json.dumps(path_adjustment, ensure_ascii=False),
                        created_at,
                        str(path_adjustment.get("appliedAt") or created_at),
                    ),
                )
                assessment_id = int(cursor.lastrowid)
        result["pathAdjustment"] = path_adjustment
        result["adjustments"] = path_adjustment
    except LookupError as exc:
        return dependencies.jsonify({"code": 409, "msg": str(exc)}), 409
    except ValueError as exc:
        return dependencies.jsonify({"code": 409, "msg": str(exc)}), 409
    except dependencies.SkillReviewError:
        raise
    except Exception as exc:
        dependencies.app.logger.exception("effect assessment path adjustment failed")
        return dependencies.jsonify({"code": 500, "msg": "路径调整应用失败", "error": str(exc)[:300]}), 500

    return dependencies.jsonify({
        "code": 0,
        "msg": "评估建议已应用到学习路径",
        "data": {
            "assessment": assessment,
            "pathAdjustment": path_adjustment,
            "assessmentId": assessment_id,
            "runId": run_id,
            "orchestration": result.get("orchestration") or {},
            "harness": result.get("harness") or {},
            "alreadyApplied": bool(path_adjustment.get("alreadyApplied")),
        },
    })


@blueprint.post("/api/learning-profile/profiles/<int:report_id>/activate")
def learning_profile_activate(report_id: int):
    user = dependencies.g.get("current_user")
    if not user:
        return dependencies.jsonify({"code": 401, "msg": "未登录"}), 401
    try:
        with dependencies.auth_db() as conn:
            profile = dependencies.activate_profile(conn, int(user["id"]), report_id, timestamp=dependencies.now_iso())
            path_switched = dependencies.mark_learning_path_profile_switch(conn, int(user["id"]), int(profile["id"]))
            selected_path = dependencies.read_learning_path_config(
                conn,
                int(user["id"]),
                profile_report_id=int(profile["id"]),
            )
            path_restored = bool(selected_path.get("weeks"))
    except LookupError as exc:
        return dependencies.jsonify({"code": 404, "msg": str(exc)}), 404
    except ValueError as exc:
        return dependencies.jsonify({"code": 400, "msg": str(exc)}), 400
    learning_path_task = None
    if not path_restored:
        learning_path_task = dependencies._schedule_profile_learning_path_generation(
            int(user["id"]),
            int(profile["id"]),
        )
    return dependencies.jsonify({
        "code": 0,
        "msg": "已切换当前学习画像",
        "data": {
            "profile": profile,
            "pathSwitched": path_switched,
            "pathRestored": path_restored,
            "pathStatus": "ready" if path_restored else "generating" if learning_path_task else "not-generated",
            "learningPathTask": learning_path_task,
            "pathMessage": (
                "已恢复该画像独立保存的学习路径"
                if path_restored
                else "该画像的独立学习路径已在后台开始生成"
                if learning_path_task
                else "该画像尚未生成路径，可进入学习路径重试"
            ),
        },
    })


@blueprint.post("/api/learning-profile/profiles/<int:report_id>/refresh")
def learning_profile_refresh(report_id: int):
    user = dependencies.g.get("current_user")
    if not user:
        return dependencies.jsonify({"code": 401, "msg": "未登录"}), 401
    payload = dependencies.request.get_json(silent=True) or {}
    with dependencies.auth_db() as conn:
        base_profile = dependencies.get_profile_for_user(conn, int(user["id"]), report_id)
        if not base_profile:
            return dependencies.jsonify({"code": 404, "msg": "学习画像不存在"}), 404
        learning_evidence = dependencies.learning_evidence_for_user(conn, int(user["id"]))

    refresh_payload = {
        **base_profile,
        "baseProfile": base_profile,
        "learningEvidence": learning_evidence,
        "refreshInstruction": "自动检索最新聊天、题库、实验、资源调用和学习路径完成情况，更新当前学习画像且保持画像 ID 不变",
    }
    context = dependencies.xiaozhi_latest_context(int(user["id"]))
    result = dependencies.xiaozhi_run_orchestrated(
        "profile_update",
        refresh_payload["refreshInstruction"],
        refresh_payload,
        int(user["id"]),
        lambda managed_payload, _progress: dependencies.generate_profile_report(managed_payload),
        context=context,
        max_retries=0,
    )
    if result.get("source") not in {"llm", "llm-fallback", "fallback-rule"}:
        return dependencies.jsonify({
            "code": 502,
            "msg": "学习画像智能体调用失败",
            "error": result.get("error") or "agent did not return llm result",
        }), 502

    report = {
        key: value
        for key, value in base_profile.items()
        if key not in {
            "id",
            "profileName",
            "version",
            "parentReportId",
            "createdAt",
            "updatedAt",
            "archived",
            "isActive",
            "_profileReportId",
            "_profileUpdatedAt",
        }
    }
    report.update(
        {
            "timestamp": dependencies.now_iso(),
            "aiAnalysis": result,
            "learningEvidence": learning_evidence,
            "refreshInstruction": refresh_payload["refreshInstruction"],
            "updatedBy": "automatic-learning-evidence",
            "effectAssessment": dependencies.effect_assessment_snapshot(base_profile, learning_evidence),
        }
    )
    with dependencies.auth_db() as conn:
        report = dependencies.update_profile_report(
            conn,
            int(user["id"]),
            report_id,
            report,
            timestamp=report["timestamp"],
        )
    dependencies._schedule_profile_portrait_generation(int(user["id"]), int(report["id"]), force=True)
    learning_path_task = dependencies._schedule_profile_learning_path_generation(
        int(user["id"]),
        int(report["id"]),
    )
    return dependencies.jsonify({
        "code": 0,
        "msg": "学习画像已根据最新学习证据更新",
        "data": {"profile": report, "learningPathTask": learning_path_task},
    })


@blueprint.patch("/api/learning-profile/profiles/<int:report_id>")
def learning_profile_rename(report_id: int):
    user = dependencies.g.get("current_user")
    if not user:
        return dependencies.jsonify({"code": 401, "msg": "未登录"}), 401
    payload = dependencies.request.get_json(silent=True) or {}
    try:
        with dependencies.auth_db() as conn:
            profile = dependencies.rename_profile(
                conn,
                int(user["id"]),
                report_id,
                str(payload.get("profileName") or payload.get("name") or ""),
                timestamp=dependencies.now_iso(),
            )
    except LookupError as exc:
        return dependencies.jsonify({"code": 404, "msg": str(exc)}), 404
    except ValueError as exc:
        return dependencies.jsonify({"code": 400, "msg": str(exc)}), 400
    return dependencies.jsonify({"code": 0, "msg": "画像名称已更新", "data": {"profile": profile}})


@blueprint.delete("/api/learning-profile/profiles/<int:report_id>")
def learning_profile_delete(report_id: int):
    user = dependencies.g.get("current_user")
    if not user:
        return dependencies.jsonify({"code": 401, "msg": "未登录"}), 401
    try:
        with dependencies.auth_db() as conn:
            result = dependencies.delete_profile(
                conn,
                int(user["id"]),
                report_id,
                timestamp=dependencies.now_iso(),
            )
    except LookupError as exc:
        return dependencies.jsonify({"code": 404, "msg": str(exc)}), 404
    return dependencies.jsonify({"code": 0, "msg": "学习画像已删除", "data": result})


@blueprint.post("/api/learning-profile/reset")
def learning_profile_reset():
    user = dependencies.g.get("current_user")
    if not user:
        return dependencies.jsonify({"code": 401, "msg": "未登录"}), 401
    timestamp = dependencies.now_iso()
    with dependencies.auth_db() as conn:
        historical_count = int(
            conn.execute(
                "SELECT COUNT(*) AS total FROM learning_profile_reports WHERE user_id = ?",
                (int(user["id"]),),
            ).fetchone()["total"]
        )
        state = dependencies.reset_profile_state(conn, int(user["id"]), timestamp=timestamp)
    dialogue_reset = {}
    try:
        dialogue_reset = dependencies.clear_persisted_profile_dialogue(str(user["id"]))
    except Exception as exc:
        dependencies.app.logger.warning("failed to clear persisted learning-profile draft: %s", exc)
    return dependencies.jsonify({
        "code": 0,
        "msg": "已重置当前画像，历史版本仍然保留",
        "data": {
            "activeReportId": None,
            "historicalCount": historical_count,
            "state": state,
            "dialogueReset": dialogue_reset,
        },
    })


@blueprint.post("/api/learning-profile/questionnaire")
def learning_profile_questionnaire_save():
    user = dependencies.g.get("current_user")
    if not user:
        return dependencies.jsonify({"code": 401, "msg": "未登录"}), 401
    payload = dependencies.request.get_json(silent=True) or {}
    title = str(payload.get("title") or "嵌入式学习画像量表问卷")
    section_statuses = payload.get("sectionStatuses") or {}
    missing_message = str(payload.get("missingMessage") or "暂时缺失该部分的数据")
    created_at = dependencies.now_iso()
    with dependencies.auth_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO learning_profile_questionnaires
                (user_id, title, section_statuses, questionnaire_data, missing_message, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user["id"],
                title,
                dependencies.json.dumps(section_statuses, ensure_ascii=False),
                dependencies.json.dumps(payload, ensure_ascii=False),
                missing_message,
                created_at,
            ),
        )
        record_id = cursor.lastrowid
    return dependencies.jsonify({"code": 0, "id": record_id, "msg": "问卷已保存", "created_at": created_at})


@blueprint.get("/api/learning-profile/sessions")
def learning_profile_sessions_list():
    user = dependencies.g.get("current_user")
    if not user:
        return dependencies.jsonify({"code": 401, "msg": "未登录"}), 401
    with dependencies.auth_db() as conn:
        sessions = dependencies.list_profile_sessions(conn, int(user["id"]))
    return dependencies.jsonify({"code": 0, "data": {"sessions": sessions}})


@blueprint.post("/api/learning-profile/sessions")
def learning_profile_session_create():
    user = dependencies.g.get("current_user")
    if not user:
        return dependencies.jsonify({"code": 401, "msg": "未登录"}), 401
    payload = dependencies.request.get_json(silent=True) or {}
    with dependencies.auth_db() as conn:
        session = dependencies.create_profile_session(conn, int(user["id"]), dependencies.now_iso(), str(payload.get("title") or ""))
    return dependencies.jsonify({"code": 0, "msg": "已创建新的学习画像会话", "data": {"session": session}}), 201


@blueprint.get("/api/learning-profile/sessions/<int:session_id>")
def learning_profile_session_detail(session_id: int):
    user = dependencies.g.get("current_user")
    if not user:
        return dependencies.jsonify({"code": 401, "msg": "未登录"}), 401
    with dependencies.auth_db() as conn:
        session = dependencies.get_profile_session(conn, int(user["id"]), session_id, include_messages=True)
    if not session:
        return dependencies.jsonify({"code": 404, "msg": "学习画像会话不存在"}), 404
    return dependencies.jsonify({"code": 0, "data": {"session": session}})


@blueprint.post("/api/learning-profile/sessions/<int:session_id>/messages")
def learning_profile_session_message(session_id: int):
    """Run exactly one profile-dialogue turn inside the selected isolated session."""
    user = dependencies.g.get("current_user")
    if not user:
        return dependencies.jsonify({"code": 401, "msg": "未登录"}), 401
    payload = dependencies.request.get_json(silent=True) or {}
    content = str(payload.get("content") or payload.get("message") or "").strip()
    public_attachments, attachment_rows = dependencies._resolve_multimodal_inputs(int(user["id"]), payload.get("attachments"))
    if not content and not attachment_rows:
        return dependencies.jsonify({"code": 400, "msg": "消息不能为空"}), 400
    display_content = content or "请分析我上传的学习材料。"
    agent_content = dependencies._message_with_multimodal_context(display_content, attachment_rows)
    timestamp = dependencies.now_iso()
    with dependencies.auth_db() as conn:
        session = dependencies.get_profile_session(conn, int(user["id"]), session_id, include_messages=True)
        if not session:
            return dependencies.jsonify({"code": 404, "msg": "学习画像会话不存在"}), 404
        if session.get("status") == "complete":
            return dependencies.jsonify({"code": 409, "msg": "此学习画像已完成，请新建画像或使用报告页的重新评估", "data": {"session": session}}), 409
        messages = []
        for item in session.get("messages", []):
            item_content = str(item.get("content") or "")
            item_attachments = item.get("metadata", {}).get("attachments") if isinstance(item.get("metadata"), dict) else []
            _, historical_rows = dependencies._resolve_multimodal_inputs(int(user["id"]), item_attachments)
            messages.append({
                "role": item["role"],
                "content": dependencies._message_with_multimodal_context(item_content, historical_rows),
            })
        messages.append({"role": "user", "content": agent_content})

    # The workflow receives only this session's transcript and dimensions.
    try:
        workflow = dependencies.xiaozhi_run_orchestrated(
            "learning_background",
            agent_content,
            {
                "messages": messages,
                "attachments": public_attachments,
                "profile": session.get("dimensions")
                if isinstance(session.get("dimensions"), dict)
                else {},
            },
            int(user["id"]),
            lambda managed_payload, _progress: dependencies.run_learning_profile_workflow(
                managed_payload.get("messages") or [],
                user_id=f"profile-session-{user['id']}-{session_id}",
                profile=managed_payload.get("profile")
                if isinstance(managed_payload.get("profile"), dict)
                else {},
            ),
            context=dependencies.xiaozhi_latest_context(int(user["id"])),
            max_retries=0,
        )
    except dependencies.LearningProfileModelUnavailable as exc:
        dependencies.app.logger.warning("learning-profile model unavailable: %s", exc)
        return dependencies.jsonify({
            "code": 503,
            "errorCode": "MODEL_UNAVAILABLE",
            "msg": "学习画像大模型不可用，请稍后重试。",
        }), 503
    reply = str(workflow.get("reply") or workflow.get("question") or "请继续补充你的学习情况。").strip()
    dimensions = workflow.get("studentProfile") if isinstance(workflow.get("studentProfile"), dict) else {}
    dimensions.pop("补充信息", None)
    dimensions.pop("琛ュ厖淇℃伅", None)
    complete = str(workflow.get("status") or "") == "complete" and not (workflow.get("missingProfileDimensions") or [])
    profile_analysis = None
    if complete:
        report_request = {
            "chatBackground": workflow.get("summary") or "",
            "chatTimestamp": dependencies.now_iso(),
            "chatStudentProfile": dimensions,
            "completedProfileDimensions": list(dimensions.keys()),
            "missingProfileDimensions": [],
            "profileSessionId": session_id,
        }
        profile_analysis = dependencies.xiaozhi_run_orchestrated(
            "profile_update",
            "基于十个已采集维度生成完整学习画像报告",
            report_request,
            int(user["id"]),
            lambda managed_payload, _progress: dependencies.generate_profile_report(managed_payload),
            context=dependencies.xiaozhi_latest_context(int(user["id"])),
            max_retries=0,
        )
        if profile_analysis.get("source") not in {"llm", "llm-fallback", "fallback-rule"}:
            complete = False
            workflow["status"] = "collecting"
            workflow["reply"] = "十个维度已收集，正在重试生成完整画像报告。请稍后在画像报告页查看。"
            workflow["question"] = workflow["reply"]
            workflow["reportError"] = profile_analysis.get("error") or "profile agent did not return a valid result"
    report = None
    with dependencies.auth_db() as conn:
        user_message_id = dependencies.add_profile_session_message(
            conn,
            int(user["id"]),
            session_id,
            "user",
            display_content,
            timestamp,
            {"attachments": public_attachments},
        )
        memory_source_key = f"{session_id}:{user_message_id}"
        assistant_timestamp = dependencies.now_iso()
        assistant_message_id = dependencies.add_profile_session_message(conn, int(user["id"]), session_id, "assistant", reply, assistant_timestamp, {
            "completeness": workflow.get("completeness"), "missingFields": workflow.get("missingProfileDimensions") or [],
        })
        dependencies.knowledge_growth.record_conversation_memory(
            conn,
            int(user["id"]),
            source_type="profile-dialogue",
            source_key=memory_source_key,
            session_id=str(session_id),
            route="/learning-profile/chat",
            user_message=display_content,
            assistant_message=reply,
            metadata={
                "assistantMessageId": assistant_message_id,
                "summary": workflow.get("summary") or "",
                "topic": next(iter(dimensions.keys()), "学习画像采集"),
                "dimensions": dimensions,
            },
            timestamp=assistant_timestamp,
        )
        if complete:
            report_payload = {
                "timestamp": dependencies.now_iso(),
                "chatBackground": workflow.get("summary") or "",
                "chatTimestamp": dependencies.now_iso(),
                "chatStudentProfile": dimensions,
                "completedProfileDimensions": list(dimensions.keys()),
                "missingProfileDimensions": [],
                "aiAnalysis": profile_analysis,
            }
            report, profile_save_mode = dependencies.save_or_update_active_profile(
                conn,
                int(user["id"]),
                report_payload,
                profile_name=str(session.get("title") or "学习画像"),
                timestamp=report_payload["timestamp"],
            )
        session = dependencies.update_profile_session(
            conn, int(user["id"]), session_id, dimensions=dimensions,
            status="complete" if complete else "collecting", timestamp=dependencies.now_iso(), report_id=int(report["id"]) if report else None,
        )
    learning_path_task = None
    if report:
        dependencies._schedule_profile_portrait_generation(int(user["id"]), int(report["id"]), force=True)
        learning_path_task = dependencies._schedule_profile_learning_path_generation(
            int(user["id"]),
            int(report["id"]),
        )
    return dependencies.jsonify({
        "code": 0,
        "data": {
            "session": session,
            "workflow": workflow,
            "report": report,
            "profileSaveMode": profile_save_mode if report else "",
            "learningPathTask": learning_path_task,
        },
    })


@blueprint.post("/api/learning-profile/sessions/<int:session_id>/messages-stream")
def learning_profile_session_message_stream(session_id: int):
    @dependencies.stream_with_context
    def generate_events():
        yield dependencies._sse_event("start", {
            "agent": "learning-background-dialogue-agent",
            "stage": "start",
            "message": "学习画像智能体已启动",
            "sessionId": session_id,
        })
        try:
            yield dependencies._sse_event("progress", {
                "agent": "learning-background-dialogue-agent",
                "stage": "call_agent",
                "message": "正在读取会话上下文并调用学习画像智能体",
                "sessionId": session_id,
            })
            raw_response = learning_profile_session_message(session_id)
            status_code = 200
            response = raw_response
            if isinstance(raw_response, tuple):
                response = raw_response[0]
                if len(raw_response) > 1:
                    try:
                        status_code = int(raw_response[1])
                    except (TypeError, ValueError):
                        status_code = 500
            payload = {}
            try:
                payload = dependencies.json.loads(response.get_data(as_text=True))
            except Exception:
                payload = {}
            if status_code >= 400:
                yield dependencies._sse_event("error", {
                    "agent": "learning-background-dialogue-agent",
                    "stage": "failed",
                    "message": payload.get("msg") or payload.get("message") or "学习画像智能体调用失败",
                    "data": payload.get("data") or {},
                    "errorCode": payload.get("errorCode") or "",
                })
                yield dependencies._sse_event("done", {
                    "agent": "learning-background-dialogue-agent",
                    "stage": "done",
                    "status": "failed",
                })
                return
            data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
            workflow = data.get("workflow") if isinstance(data.get("workflow"), dict) else {}
            reply = str(workflow.get("reply") or workflow.get("question") or "")
            if not reply.strip():
                yield dependencies._sse_event("error", {
                    "agent": "learning-background-dialogue-agent",
                    "stage": "empty_reply",
                    "message": "学习画像智能体未返回可显示内容",
                    "data": data,
                })
                yield dependencies._sse_event("done", {
                    "agent": "learning-background-dialogue-agent",
                    "stage": "done",
                    "status": "failed",
                })
                return
            yield dependencies._sse_event("progress", {
                "agent": "learning-background-dialogue-agent",
                "stage": "stream_reply",
                "message": "学习画像智能体已返回，正在流式输出",
                "source": workflow.get("source") or "",
                "status": workflow.get("status") or "",
                "completeness": workflow.get("completeness"),
                "missingFields": workflow.get("missingProfileDimensions") or [],
            })
            for index in range(0, len(reply), 4):
                yield dependencies._sse_event("delta", {
                    "agent": "learning-background-dialogue-agent",
                    "text": reply[index:index + 4],
                    "source": workflow.get("source") or "",
                })
                dependencies.time.sleep(0.04)
            yield dependencies._sse_event("result", {
                "agent": "learning-background-dialogue-agent",
                "stage": "complete",
                "message": "学习画像会话本轮输出完成",
                "data": data,
            })
            yield dependencies._sse_event("done", {
                "agent": "learning-background-dialogue-agent",
                "stage": "done",
                "message": "学习画像会话流已结束",
            })
        except Exception as exc:
            dependencies.app.logger.exception("learning profile session message stream failed")
            yield dependencies._sse_event("error", {
                "agent": "learning-background-dialogue-agent",
                "stage": "failed",
                "message": "学习画像智能体调用失败，请重试本轮对话。",
                "error": str(exc),
            })
            yield dependencies._sse_event("done", {
                "agent": "learning-background-dialogue-agent",
                "stage": "done",
                "status": "failed",
            })

    return dependencies.Response(generate_events(), mimetype="text/event-stream")
@blueprint.post("/api/learning-profile/background-chat")
def learning_profile_background_chat():
    user = dependencies.g.get("current_user")
    if not user:
        return dependencies.jsonify({"code": 401, "msg": "未登录"}), 401
    payload = dependencies.request.get_json(silent=True) or {}
    payload, _ = dependencies._apply_profile_multimodal_context(payload, int(user["id"]))
    payload["userId"] = (user["id"] if "id" in user.keys() else None) or payload.get("userId") or "current-user"
    try:
        result = dependencies.xiaozhi_run_orchestrated(
            "learning_background",
            str(payload.get("message") or (payload.get("messages") or [{}])[-1].get("content") or "继续采集学习背景"),
            payload,
            int(user["id"]),
            lambda managed_payload, _progress: dependencies.generate_background_chat(managed_payload),
            max_retries=0,
        )
    except dependencies.LearningProfileModelUnavailable as exc:
        dependencies.app.logger.warning("learning-profile model unavailable: %s", exc)
        return dependencies.jsonify({
            "code": 503,
            "errorCode": "MODEL_UNAVAILABLE",
            "msg": "学习画像大模型不可用，请稍后重试。",
        }), 503
    if result.get("source") not in {"llm", "llm-fallback", "fallback-rule"}:
        return dependencies.jsonify({
            "code": 503,
            "msg": "调用学习背景对话智能体失败",
            "data": result,
        }), 503
    return dependencies.jsonify({"code": 0, "msg": "ok", "data": result})


@blueprint.post("/api/learning-profile/background-chat/reset")
def learning_profile_background_chat_reset():
    user = dependencies.g.get("current_user")
    if not user:
        return dependencies.jsonify({"code": 401, "msg": "未登录"}), 401
    user_id = (user["id"] if "id" in user.keys() else None) or "current-user"
    result = dependencies.clear_persisted_profile_dialogue(str(user_id))
    return dependencies.jsonify({"code": 0, "msg": "ok", "data": result})


@blueprint.post("/api/learning-profile/background-chat-stream")
def learning_profile_background_chat_stream():
    user = dependencies.g.get("current_user")
    if not user:
        return dependencies.jsonify({"code": 401, "msg": "未登录"}), 401
    payload = dependencies.request.get_json(silent=True) or {}
    payload, _ = dependencies._apply_profile_multimodal_context(payload, int(user["id"]))
    payload["userId"] = (user["id"] if "id" in user.keys() else None) or payload.get("userId") or "current-user"

    @dependencies.stream_with_context
    def generate_events():
        yield dependencies._sse_event("start", {
            "agent": "learning-background-dialogue-agent",
            "stage": "start",
            "message": "学习背景对话智能体已启动",
        })
        try:
            messages = payload.get("messages") or []
            yield dependencies._sse_event("progress", {
                "agent": "learning-background-dialogue-agent",
                "stage": "read_context",
                "message": "正在读取当前多轮对话上下文",
                "turnCount": len(messages),
            })
            yield dependencies._sse_event("progress", {
                "agent": "learning-background-dialogue-agent",
                "stage": "call_agent",
                "message": "正在判断已采集字段并生成下一轮追问",
            })
            orchestration_events = []
            result = dependencies.xiaozhi_run_orchestrated(
                "learning_background",
                str((payload.get("messages") or [{}])[-1].get("content") or "继续采集学习背景"),
                payload,
                int(user["id"]),
                lambda managed_payload, _progress: dependencies.generate_background_chat(managed_payload),
                on_event=orchestration_events.append,
                max_retries=0,
            )
            for event in orchestration_events:
                yield dependencies._sse_event("progress", {
                    **event,
                    "agent": event.get("agentId"),
                })
            source = result.get("source") or "unknown"
            if source != "llm":
                yield dependencies._sse_event("error", {
                    "agent": "learning-background-dialogue-agent",
                    "stage": "llm_required",
                    "message": "学习背景对话必须调用 LLM，但当前大模型未返回可用结果",
                    "source": source,
                    "data": result,
                })
                return
            reply = str(result.get("reply") or result.get("question") or "")
            yield dependencies._sse_event("progress", {
                "agent": "learning-background-dialogue-agent",
                "stage": "stream_reply",
                "message": "智能体已生成回复，正在流式输出",
                "source": source,
                "status": result.get("status"),
                "completeness": result.get("completeness"),
                "missingFields": result.get("missingFields") or [],
            })
            chunk_size = 4
            for index in range(0, len(reply), chunk_size):
                yield dependencies._sse_event("delta", {
                    "agent": "learning-background-dialogue-agent",
                    "source": source,
                    "text": reply[index:index + chunk_size],
                })
                dependencies.time.sleep(0.04)
            yield dependencies._sse_event("result", {
                "agent": "learning-background-dialogue-agent",
                "stage": "complete",
                "message": "学习背景对话本轮输出完成",
                "source": source,
                "data": result,
            })
            yield dependencies._sse_event("done", {
                "agent": "learning-background-dialogue-agent",
                "stage": "done",
                "message": "学习背景对话流已结束",
            })
        except Exception as exc:
            dependencies.app.logger.exception("learning profile background chat stream failed")
            yield dependencies._sse_event("error", {
                "agent": "learning-background-dialogue-agent",
                "stage": "failed",
                "message": "学习背景对话智能体调用失败，请重试本轮对话。",
                "source": "error",
                "error": str(exc),
            })
            yield dependencies._sse_event("done", {
                "agent": "learning-background-dialogue-agent",
                "stage": "done",
                "status": "failed",
                "message": "学习背景对话流已失败结束",
            })

    return dependencies.Response(generate_events(), mimetype="text/event-stream")
