"""Progressive learning-path generation and weekly resource orchestration services."""

from __future__ import annotations

from functools import wraps
from typing import Callable

try:
    from exam_evidence import learning_resource_completed, resource_sheet_ids, normalize_exam, has_answer
except ImportError:
    from .exam_evidence import learning_resource_completed, resource_sheet_ids, normalize_exam, has_answer


_DependencyProvider = Callable[[str], object]
_provider: _DependencyProvider | None = None


def configure(provider: _DependencyProvider) -> None:
    global _provider
    _provider = provider


def _sync_dependencies() -> None:
    if _provider is None:
        raise RuntimeError("learning_path_service has not been configured")
    namespace = globals()
    for name in DEPENDENCY_NAMES:
        try:
            namespace[name] = _provider(name)
        except (KeyError, AttributeError):
            continue

DEPENDENCY_NAMES = (
    'AUTH_DB_PATH',
    'LEARNING_PATH_CONFIG_WRITE_LOCKS',
    'LEARNING_PATH_CONFIG_WRITE_LOCKS_GUARD',
    'LEARNING_PATH_GENERATION_EXECUTOR',
    'LEARNING_PATH_REQUIRED_TASK_RESOURCE_TYPES',
    'LEARNING_PATH_RESOURCE_MAX_GENERATION_ATTEMPTS',
    'LEARNING_PATH_RESOURCE_MAX_PLANNING_ATTEMPTS',
    'LEARNING_PATH_RESOURCE_PLANNER_MAX_WORKERS',
    'LEARNING_PATH_RESOURCE_PLAN_VERSION',
    'LEARNING_PATH_STAGE_RESOURCE_LOCKS',
    'LEARNING_PATH_STAGE_RESOURCE_LOCKS_GUARD',
    'LEARNING_PATH_TASK_RESOURCE_ACTIONS',
    'LEARNING_PATH_WEEK_PREPARATION_EXECUTOR',
    'LearningProfileRequiredError',
    'QueueCapacityError',
    'SkillReviewError',
    'ThreadPoolExecutor',
    '_apply_learning_path_node_resource_plan',
    '_canonical_learning_path_task_resource',
    '_clean_number',
    '_clean_text',
    '_enforce_parallel_learning_path_resource_coverage',
    '_json_copy',
    '_learning_path_active_profile_id',
    '_learning_path_config_write_lock',
    '_learning_path_resource_attempt',
    '_learning_path_resource_cache_key',
    '_learning_path_resource_plan_nodes',
    '_learning_path_resource_planner_trace',
    '_learning_path_stage_has_required_resources',
    '_learning_path_stage_needs_resource_recovery',
    '_learning_path_stage_resource_lock',
    '_learning_path_stage_view_progress',
    '_learning_path_stream_error',
    '_learning_path_task_resource_route',
    '_learning_path_task_runtime_summary',
    '_learning_path_week_view_progress',
    '_materialize_learning_path_resource_node',
    '_parallel_dispatch_learning_path_resource_nodes',
    '_persist_learning_path_stage_update',
    '_plan_learning_path_resource_node',
    '_prepare_learning_path_generation',
    '_prepare_learning_path_week_resources_in_background',
    '_queue_learning_path_week_resource_preparation',
    '_read_profile_scoped_learning_path_config',
    '_reset_retryable_failed_stage_resources',
    '_run_learning_path_generation',
    '_run_profile_learning_path_generation_task',
    '_sanitize_learning_path_error_message',
    '_visible_learning_path_weeks',
    'active_profile_for_user',
    'app',
    'auth_db',
    'build_learning_profile_context',
    'default_learning_path_config',
    'enrich_learning_path_task_descriptions',
    'ensure_weekly_learning_path_resource_coverage',
    'get_profile_for_user',
    'hashlib',
    'json',
    'json_loads_safe',
    'learning_path_config_is_degraded',
    'learning_path_node_cache_from_row',
    'learning_path_profile_report_id',
    'learning_path_stage_resource_status',
    'normalize_learning_path_config',
    'now_iso',
    'plan_learning_path_stage_resources',
    'prepare_learning_path_stage_resources_for_user',
    'private_knowledge_service',
    're',
    'read_learning_path_config',
    'secrets',
    'threading',
    'time',
    'upsert_learning_path_node_cache',
    'write_learning_path_config',
    'xiaozhi_create_resource_agent_task',
    'xiaozhi_insert_event',
    'xiaozhi_latest_context',
    'xiaozhi_route_with_task',
    'xiaozhi_run_orchestrated',
    'xiaozhi_task_from_row',
    'xiaozhi_update_task',
)
EXPORTED_FUNCTIONS = (
    '_visible_learning_path_weeks',
    '_learning_path_stage_view_progress',
    '_learning_path_week_view_progress',
    '_annotate_learning_path_week_view_progress',
    '_read_profile_scoped_learning_path_config',
    '_run_profile_learning_path_generation_task',
    '_schedule_profile_learning_path_generation',
    '_learning_path_stage_resource_lock',
    '_learning_path_config_write_lock',
    '_learning_path_stage_has_required_resources',
    '_persist_learning_path_stage_update',
    '_learning_path_resource_attempt',
    '_learning_path_resource_plan_nodes',
    '_learning_path_resource_cache_key',
    '_learning_path_task_runtime_summary',
    '_learning_path_resource_planner_trace',
    '_apply_learning_path_node_resource_plan',
    '_apply_learning_path_stage_resource_plan',
    'learning_path_stage_resource_status',
    '_reset_retryable_failed_stage_resources',
    '_plan_learning_path_resource_node',
    '_enforce_parallel_learning_path_resource_coverage',
    '_materialize_learning_path_resource_node',
    '_parallel_dispatch_learning_path_resource_nodes',
    '_prepare_learning_path_week_resources_in_background',
    '_queue_learning_path_week_resource_preparation',
    '_learning_path_stage_needs_resource_recovery',
    'prepare_learning_path_stage_resources_for_user',
)

def _visible_learning_path_weeks(config: dict) -> list[dict]:
    weeks = config.get("weeks") if isinstance(config, dict) else []
    return [
        week
        for week in (weeks if isinstance(weeks, list) else [])
        if isinstance(week, dict)
        and week.get("enabled", True)
        and not week.get("placeholder", False)
    ]


def _learning_path_stage_view_progress(
    conn: sqlite3.Connection,
    user_id: int,
    config: dict,
    stage_id: str = "",
) -> dict:
    resolved_stage_id = str(stage_id or "")
    stage = (config.get("stages") or {}).get(resolved_stage_id)
    nodes = [
        node
        for node in ((stage or {}).get("nodes") or [])
        if isinstance(node, dict) and node.get("enabled", True)
    ]
    required = {
        str(node.get("cacheKey") or ""): str(node.get("id") or "")
        for node in nodes
        if str(node.get("cacheKey") or "")
    }
    if not nodes or len(required) != len(nodes):
        return {
            "stageId": resolved_stage_id,
            "allViewed": False,
            "viewedCount": 0,
            "taskCount": len(nodes),
            "missingNodeIds": [str(node.get("id") or "") for node in nodes],
        }
    placeholders = ",".join("?" for _ in required)
    rows = conn.execute(
        f"""
        SELECT cache_key, resource_type, payload_json
        FROM learning_path_node_caches
        WHERE user_id = ? AND cache_key IN ({placeholders})
        """,
        (int(user_id), *required.keys()),
    ).fetchall()
    expected_profile_id = learning_path_profile_report_id(config)
    viewed_keys = set()
    for row in rows:
        cache_key = str(row["cache_key"])
        payload = json_loads_safe(row["payload_json"], {}) or {}
        if not learning_resource_completed(row["resource_type"], payload):
            continue
        if str(payload.get("stageId") or "") != resolved_stage_id:
            continue
        if str(payload.get("nodeId") or "") != required.get(cache_key):
            continue
        if expected_profile_id > 0:
            try:
                payload_profile_id = int(payload.get("profileReportId") or 0)
            except (TypeError, ValueError):
                payload_profile_id = 0
            if payload_profile_id != expected_profile_id:
                continue
        viewed_keys.add(cache_key)
    missing_node_ids = [node_id for key, node_id in required.items() if key not in viewed_keys]
    return {
        "stageId": resolved_stage_id,
        "allViewed": not missing_node_ids and len(viewed_keys) == len(nodes),
        "viewedCount": len(viewed_keys),
        "taskCount": len(nodes),
        "missingNodeIds": missing_node_ids,
    }


def _learning_path_week_view_progress(
    conn: sqlite3.Connection,
    user_id: int,
    config: dict,
    stage_id: str = "",
) -> dict:
    visible_weeks = sorted(
        _visible_learning_path_weeks(config),
        key=lambda item: int(item.get("order") or 0),
    )
    latest_week = visible_weeks[-1] if visible_weeks else {}
    resolved_stage_id = str(stage_id or latest_week.get("id") or "")
    if not latest_week or resolved_stage_id != str(latest_week.get("id") or ""):
        return {
            "stageId": resolved_stage_id,
            "isLatestWeek": False,
            "allViewed": False,
            "viewedCount": 0,
            "taskCount": 0,
            "missingNodeIds": [],
        }
    return {
        **_learning_path_stage_view_progress(conn, user_id, config, resolved_stage_id),
        "isLatestWeek": True,
    }


def _annotate_learning_path_week_view_progress(
    conn: sqlite3.Connection,
    user_id: int,
    config: dict,
) -> dict:
    for week in _visible_learning_path_weeks(config):
        stage_id = str(week.get("id") or "")
        progress = _learning_path_stage_view_progress(conn, user_id, config, stage_id)
        task_count = max(0, int(progress.get("taskCount") or 0))
        viewed_count = max(0, min(task_count, int(progress.get("viewedCount") or 0)))
        progress_percent = round((viewed_count / task_count) * 100) if task_count else 0
        week["viewProgress"] = progress
        week["progressPercent"] = max(0, min(100, progress_percent))
    return config


def _read_profile_scoped_learning_path_config(
    conn: sqlite3.Connection,
    user_id: int,
    profile_report_id: int,
) -> dict:
    row = conn.execute(
        """
        SELECT config_json, updated_at
        FROM learning_path_profile_configs
        WHERE user_id = ? AND profile_report_id = ?
        LIMIT 1
        """,
        (int(user_id), int(profile_report_id)),
    ).fetchone()
    if not row:
        return default_learning_path_config()
    try:
        config = normalize_learning_path_config(json.loads(row["config_json"]))
    except (TypeError, ValueError, json.JSONDecodeError):
        return default_learning_path_config()
    config["updatedAt"] = str(row["updated_at"] or config.get("updatedAt") or "")
    config.setdefault("meta", {}).update({
        "profileReportId": int(profile_report_id),
        "pathStorageScope": "profile",
    })
    return config


def _run_profile_learning_path_generation_task(
    task_id: str,
    user_id: int,
    profile_report_id: int,
    total_weeks: int = 6,
    trigger: str = "profile_complete",
    source_week_id: str = "",
) -> None:
    total_weeks = max(4, min(8, int(total_weeks or 6)))
    is_view_advance = trigger == "week_tasks_viewed"
    base_result = {
        "profileReportId": int(profile_report_id),
        "progress": 1,
        "currentStage": "loading_profile",
        "completedWeeks": 0,
        "totalWeeks": total_weeks,
        "message": "本周任务已全部查看，正在规划下一周" if is_view_advance else "学习画像已完成，正在读取画像并规划学习路径",
        "trigger": trigger,
        "sourceWeekId": str(source_week_id or ""),
    }
    xiaozhi_update_task(task_id, status="running", result_json=base_result, error="")
    try:
        payload, context = _prepare_learning_path_generation(
            int(user_id),
            {
                "profileReportId": int(profile_report_id),
                "persist": True,
                "useLatestProfile": False,
                "useLLM": True,
                "prepareResources": False,
                "totalWeeks": total_weeks,
            },
        )
        with auth_db() as conn:
            current_config = _read_profile_scoped_learning_path_config(
                conn,
                int(user_id),
                int(profile_report_id),
            )
        if learning_path_profile_report_id(current_config) not in {0, int(profile_report_id)}:
            current_config = default_learning_path_config()

        if is_view_advance:
            with auth_db() as conn:
                view_progress = _learning_path_week_view_progress(
                    conn,
                    int(user_id),
                    current_config,
                    source_week_id,
                )
            if not view_progress.get("allViewed"):
                xiaozhi_update_task(
                    task_id,
                    status="complete",
                    result_json={
                        **base_result,
                        "progress": 100,
                        "currentStage": "waiting_for_week_views",
                        "message": "本周仍有未查看任务，未生成下一周",
                        "viewProgress": view_progress,
                    },
                    error="",
                )
                return

        completed_weeks = len(_visible_learning_path_weeks(current_config))
        week_number = completed_weeks + 1
        phase = "first-week" if week_number == 1 else "next-week"
        progress_result = {
            **base_result,
            "progress": 12,
            "currentStage": f"planning_week_{week_number}",
            "completedWeeks": completed_weeks,
            "message": f"学习路径智能体正在生成第 {week_number} 周任务",
        }
        xiaozhi_update_task(task_id, status="running", result_json=progress_result, error="")
        generation_payload = {
            **payload,
            "generationPhase": phase,
            "weekStart": week_number,
            "weekCount": 1,
            "totalWeeks": total_weeks,
            "prepareResources": False,
        }
        if _visible_learning_path_weeks(current_config):
            generation_payload["existingConfig"] = current_config
        generated = _run_learning_path_generation(
            int(user_id),
            generation_payload,
            context,
            task_id=task_id,
        )
        if not isinstance(generated.get("config"), dict):
            raise RuntimeError(f"第 {week_number} 周学习路径未返回可保存配置")
        current_config = generated["config"]
        completed_weeks = len(_visible_learning_path_weeks(current_config))
        xiaozhi_update_task(
            task_id,
            status="running",
            result_json={
                **base_result,
                "progress": 95,
                "currentStage": f"week_{week_number}_saved",
                "completedWeeks": completed_weeks,
                "message": f"第 {week_number} 周路径已保存",
            },
            error="",
        )

        with auth_db() as conn:
            active_profile_id = _learning_path_active_profile_id(conn, int(user_id))
        resources_queued = active_profile_id == int(profile_report_id)
        if resources_queued:
            generated_stage_ids = [
                str(week.get("id") or "")
                for week in _visible_learning_path_weeks(current_config)
                if int(week.get("order") or 0) == week_number
            ]
            _queue_learning_path_week_resource_preparation(
                int(user_id),
                current_config,
                stage_ids=generated_stage_ids,
            )

        final_result = {
            **base_result,
            "progress": 100,
            "currentStage": "complete",
            "completedWeeks": len(_visible_learning_path_weeks(current_config)),
            "message": f"第 {week_number} 周学习路径已在后台生成并保存",
            "resourcesQueued": resources_queued,
            "generationState": str((current_config.get("meta") or {}).get("generationState") or "partial"),
        }
        xiaozhi_update_task(task_id, status="complete", result_json=final_result, error="")
        xiaozhi_insert_event(
            int(user_id),
            "learning_path_background_complete",
            "/learning-path",
            f"画像对应第 {week_number} 周学习路径已生成",
            final_result,
        )
    except Exception as exc:
        error_payload = _learning_path_stream_error(exc)
        error_message = str(error_payload.get("message") or "学习路径后台生成失败")[:1000]
        xiaozhi_update_task(
            task_id,
            status="failed",
            result_json={
                **base_result,
                "progress": 100,
                "currentStage": "failed",
                "message": error_message,
                "errorCode": str(error_payload.get("errorCode") or "LEARNING_PATH_GENERATION_FAILED"),
            },
            error=error_message,
        )
        app.logger.exception(
            "profile learning path background generation failed user=%s profile=%s",
            user_id,
            profile_report_id,
        )


def _schedule_profile_learning_path_generation(
    user_id: int,
    profile_report_id: int,
    *,
    total_weeks: int = 6,
    trigger: str = "profile_complete",
    source_week_id: str = "",
) -> dict | None:
    user_id = int(user_id)
    profile_report_id = int(profile_report_id)
    total_weeks = max(4, min(8, int(total_weeks or 6)))
    timestamp = now_iso()
    with auth_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        profile = get_profile_for_user(conn, user_id, profile_report_id)
        if not profile or profile.get("archived"):
            return None
        saved_config = _read_profile_scoped_learning_path_config(
            conn,
            user_id,
            profile_report_id,
        )
        total_weeks = max(
            4,
            min(8, int((saved_config.get("meta") or {}).get("totalWeeks") or total_weeks)),
        )
        saved_weeks = _visible_learning_path_weeks(saved_config)
        if saved_weeks:
            if trigger != "week_tasks_viewed" or not source_week_id:
                return None
            view_progress = _learning_path_week_view_progress(
                conn,
                user_id,
                saved_config,
                source_week_id,
            )
            if not view_progress.get("allViewed") or len(saved_weeks) >= total_weeks:
                return None

        active_rows = conn.execute(
            """
            SELECT task_id, task_type, title, prompt, status, route, result_json,
                   error, created_at, updated_at
            FROM xiaozhi_tasks
            WHERE user_id = ? AND task_type = 'learning_path' AND status IN ('queued', 'running')
            ORDER BY id DESC
            """,
            (user_id,),
        ).fetchall()
        for row in active_rows:
            result = json_loads_safe(row["result_json"], {})
            if int(result.get("profileReportId") or 0) == profile_report_id:
                return xiaozhi_task_from_row(row)

        task_id = f"xz_{int(time.time() * 1000)}_{secrets.token_hex(4)}"
        route = xiaozhi_route_with_task("/learning-path", task_id)
        title = (
            f"{str(profile.get('profileName') or '学习画像')[:32]} · 下一周学习路径规划"
            if trigger == "week_tasks_viewed"
            else f"{str(profile.get('profileName') or '学习画像')[:32]} · 学习路径后台规划"
        )
        task_prompt = (
            f"{source_week_id} 的任务已全部查看，自动生成下一周个性化学习任务"
            if trigger == "week_tasks_viewed"
            else "根据刚完成的学习画像自动生成第一周个性化学习任务"
        )
        initial_result = {
            "profileReportId": profile_report_id,
            "progress": 0,
            "currentStage": "queued",
            "completedWeeks": len(saved_weeks),
            "totalWeeks": total_weeks,
            "message": "本周任务已全部查看，下一周规划已排队" if trigger == "week_tasks_viewed" else "画像已保存，学习路径后台任务已排队",
            "trigger": trigger,
            "sourceWeekId": str(source_week_id or ""),
        }
        conn.execute(
            """
            INSERT INTO xiaozhi_tasks
                (task_id, user_id, profile_report_id, task_type, title, prompt, status, route,
                 result_json, error, created_at, updated_at)
            VALUES (?, ?, ?, 'learning_path', ?, ?, 'queued', ?, ?, '', ?, ?)
            """,
            (
                task_id,
                user_id,
                profile_report_id,
                title,
                task_prompt,
                route,
                json.dumps(initial_result, ensure_ascii=False),
                timestamp,
                timestamp,
            ),
        )

    task = {
        "taskId": task_id,
        "taskType": "learning_path",
        "title": title,
        "prompt": task_prompt,
        "status": "queued",
        "route": route,
        "result": initial_result,
        "error": "",
        "createdAt": timestamp,
        "updatedAt": timestamp,
    }
    try:
        LEARNING_PATH_GENERATION_EXECUTOR.submit(
            _run_profile_learning_path_generation_task,
            task_id,
            user_id,
            profile_report_id,
            total_weeks,
            trigger,
            source_week_id,
        )
    except Exception as exc:
        error_message = _sanitize_learning_path_error_message(exc)[:1000]
        xiaozhi_update_task(task_id, status="failed", error=error_message)
        task["status"] = "failed"
        task["error"] = error_message
        return task
    xiaozhi_insert_event(
        user_id,
        "learning_path_background_queued",
        route,
        title,
        {"taskId": task_id, **initial_result},
    )
    return task


def _learning_path_stage_resource_lock(user_id: int, stage_id: str) -> threading.Lock:
    key = (int(user_id), str(stage_id))
    with LEARNING_PATH_STAGE_RESOURCE_LOCKS_GUARD:
        lock = LEARNING_PATH_STAGE_RESOURCE_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            LEARNING_PATH_STAGE_RESOURCE_LOCKS[key] = lock
        return lock


def _learning_path_config_write_lock(user_id: int) -> threading.Lock:
    key = int(user_id)
    with LEARNING_PATH_CONFIG_WRITE_LOCKS_GUARD:
        lock = LEARNING_PATH_CONFIG_WRITE_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            LEARNING_PATH_CONFIG_WRITE_LOCKS[key] = lock
        return lock


def _learning_path_stage_has_required_resources(stage: dict) -> bool:
    nodes = [node for node in (stage.get("nodes") or []) if isinstance(node, dict)]
    if len(nodes) < len(LEARNING_PATH_REQUIRED_TASK_RESOURCE_TYPES):
        return True
    required = set(LEARNING_PATH_REQUIRED_TASK_RESOURCE_TYPES)
    resource_types = {
        _canonical_learning_path_task_resource(node, index)
        for index, node in enumerate(nodes, start=1)
    }
    return required.issubset(resource_types)


def _persist_learning_path_stage_update(user_id: int, stage_id: str, stage: dict) -> dict:
    """Merge one concurrently prepared week into the latest saved path."""
    with _learning_path_config_write_lock(user_id):
        with auth_db() as conn:
            latest = read_learning_path_config(conn, int(user_id))
            stages = latest.get("stages") if isinstance(latest.get("stages"), dict) else {}
            if str(stage_id) not in stages:
                raise KeyError(stage_id)
            stages[str(stage_id)] = _json_copy(stage)
            latest["stages"] = stages
            all_current = bool(stages) and all(
                isinstance(item, dict)
                and item.get("resourcePlanVersion") == LEARNING_PATH_RESOURCE_PLAN_VERSION
                and _learning_path_stage_has_required_resources(item)
                for item in stages.values()
            )
            latest.setdefault("meta", {})["taskResourceModel"] = (
                LEARNING_PATH_RESOURCE_PLAN_VERSION if all_current else ""
            )
            return write_learning_path_config(conn, latest, int(user_id))


def _learning_path_resource_attempt(resource_task: dict, field: str, default: int = 0) -> int:
    try:
        return max(0, int(resource_task.get(field) or default))
    except (TypeError, ValueError):
        return max(0, int(default))


def _learning_path_resource_plan_nodes(nodes: list[dict]) -> list[dict]:
    fresh: list[dict] = []
    retryable: list[dict] = []
    for node in nodes:
        resource_task = node.get("resourceTask") if isinstance(node.get("resourceTask"), dict) else {}
        if str(resource_task.get("taskId") or ""):
            continue
        if str(resource_task.get("status") or "waiting") != "failed":
            fresh.append(node)
        elif (
            _learning_path_resource_attempt(resource_task, "attemptCount")
            < LEARNING_PATH_RESOURCE_MAX_PLANNING_ATTEMPTS
        ):
            retryable.append(node)
    return [*fresh, *retryable]


def _learning_path_resource_cache_key(
    stage_id: str,
    node_id: str,
    profile_id: int,
    resource_type: str,
    semantic_text: str = "",
) -> str:
    semantic_fingerprint = hashlib.sha256(str(semantic_text or "").encode("utf-8")).hexdigest()[:12]
    return re.sub(
        r"[^a-zA-Z0-9_.:-]+",
        "-",
        (
            f"{stage_id}-{node_id}-p{max(0, int(profile_id or 0))}-{resource_type}-"
            f"{semantic_fingerprint}-{LEARNING_PATH_RESOURCE_PLAN_VERSION}"
        ),
    ).strip("-")


def _learning_path_task_runtime_summary(task: dict) -> dict:
    result = task.get("result") if isinstance(task.get("result"), dict) else {}
    selected_resource = result.get("selectedResource") if isinstance(result.get("selectedResource"), dict) else {}
    selected_metadata = selected_resource.get("metadata") if isinstance(selected_resource.get("metadata"), dict) else {}
    quality = result.get("qualityEvaluation") if isinstance(result.get("qualityEvaluation"), dict) else {}
    if not quality:
        for key in ("questionGenerator", "ppt", "document", "animation", "tutor"):
            nested_result = result.get(key) if isinstance(result.get(key), dict) else {}
            nested_quality = nested_result.get("qualityEvaluation") if isinstance(nested_result.get("qualityEvaluation"), dict) else {}
            if nested_quality:
                quality = nested_quality
                break
    if not quality:
        quality = selected_resource.get("qualityEvaluation") if isinstance(selected_resource.get("qualityEvaluation"), dict) else {}
    if not quality:
        quality = selected_metadata.get("qualityEvaluation") if isinstance(selected_metadata.get("qualityEvaluation"), dict) else {}
    knowledge_sources = result.get("knowledgeSources") if isinstance(result.get("knowledgeSources"), list) else []
    if not knowledge_sources:
        knowledge_sources = selected_metadata.get("knowledgeSources") if isinstance(selected_metadata.get("knowledgeSources"), list) else []
    orchestration = result.get("orchestration") if isinstance(result.get("orchestration"), dict) else {}
    review = orchestration.get("review") if isinstance(orchestration.get("review"), dict) else {}
    if not quality and review:
        quality = review
    source_task_status = str(task.get("status") or "queued")
    quality_rejected = bool(
        source_task_status == "complete"
        and isinstance(quality, dict)
        and quality.get("passed") is False
    )
    task_status = "failed" if quality_rejected else source_task_status
    if task_status in {"queued", "running"}:
        harness_review_status = "running"
    elif task_status == "failed":
        harness_review_status = "failed"
    else:
        harness_review_status = "passed" if review.get("passed") else "needs-verification"
    return {
        "taskId": str(task.get("taskId") or ""),
        "status": task_status,
        "route": str(task.get("route") or ""),
        "progress": int(_clean_number(result.get("progress"), 0, 0, 100)),
        "message": str(result.get("message") or ""),
        "error": str(
            task.get("error")
            or ("资源质量评价未通过，已等待重新生成" if quality_rejected else "")
        ),
        "qualityScore": int(_clean_number(quality.get("score"), 0, 0, 100)),
        "qualityPassed": quality.get("passed") if isinstance(quality, dict) else None,
        "qualityRejected": quality_rejected,
        "sourceStatus": source_task_status,
        "citationCount": max(
            len(knowledge_sources),
            int(_clean_number(quality.get("citationCount"), 0, 0, 1000)),
        ),
        "harnessReviewStatus": harness_review_status,
        "runId": str(orchestration.get("runId") or ""),
    }


def _learning_path_resource_planner_trace(plan: dict, node_id: str = "") -> dict:
    return {
        "nodeId": node_id,
        "agent": str(plan.get("agent") or "learning-path-resource-router-agent"),
        "source": str(plan.get("source") or "profile-rule"),
        "grounded": bool(plan.get("grounded")),
        "knowledgeSources": plan.get("knowledgeSources") if isinstance(plan.get("knowledgeSources"), list) else [],
        "runId": str((plan.get("orchestration") or {}).get("runId") or "") if isinstance(plan.get("orchestration"), dict) else "",
        "skillId": str((plan.get("harness") or {}).get("skill", {}).get("id") or "") if isinstance(plan.get("harness"), dict) else "",
        "mcpTool": str((plan.get("harness") or {}).get("skill", {}).get("mcpTool") or "") if isinstance(plan.get("harness"), dict) else "",
        "error": str(plan.get("error") or ""),
        "updatedAt": now_iso(),
    }


def _apply_learning_path_node_resource_plan(
    config: dict,
    stage_id: str,
    node_id: str,
    planned: dict,
    plan: dict,
    profile_id: int,
) -> dict:
    stage = (config.get("stages") or {}).get(stage_id)
    if not isinstance(stage, dict):
        raise KeyError(stage_id)
    nodes = [node for node in (stage.get("nodes") or []) if isinstance(node, dict)]
    node = next((item for item in nodes if str(item.get("id") or "") == str(node_id)), None)
    if not node:
        raise KeyError(node_id)
    node_index = nodes.index(node) + 1
    merged_node = {**node, **planned}
    resource_type = _canonical_learning_path_task_resource(merged_node, node_index)
    params = _json_copy(planned.get("resourceParams")) if isinstance(planned.get("resourceParams"), dict) else {}
    semantic_text = json.dumps(
        {
            "stage": stage.get("focus") or stage.get("title") or "",
            "title": node.get("title") or "",
            "description": node.get("description") or node.get("desc") or "",
            "deliverable": node.get("deliverable") or "",
            "resourceType": resource_type,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    cache_key = _learning_path_resource_cache_key(
        stage_id,
        node_id,
        profile_id,
        resource_type,
        semantic_text,
    )
    params.update(
        {
            "source": "learning-path",
            "stageId": stage_id,
            "nodeId": node_id,
            "cacheKey": cache_key,
            "profileReportId": profile_id,
        }
    )
    if resource_type == "herb-model" and params.get("herbName"):
        node["title"] = f"药材模型辨识 · {params['herbName']}"
        node["description"] = (
            f"旋转观察{params['herbName']}三维模型，先独立判断药材名称，"
            "再核对药用部位与关键性状并完成辨识。"
        )
        node["deliverable"] = "药材辨识结果与三条性状依据"
    node.update(
        {
            "cacheKey": cache_key,
            "resourceType": resource_type,
            "resourceTypes": [resource_type],
            "resourceParams": params,
            "resourcePrompt": _clean_text(planned.get("resourcePrompt"), node.get("description") or node.get("title") or "生成学习资源"),
            "resourceSelectionReason": _clean_text(planned.get("resourceSelectionReason"), "根据当前激活学习画像自动选择资源智能体。"),
            "resourceSelectionSource": _clean_text(planned.get("resourceSelectionSource"), plan.get("source") or "profile-rule"),
            "actionText": LEARNING_PATH_TASK_RESOURCE_ACTIONS[resource_type],
            "actionRoute": _learning_path_task_resource_route(
                resource_type,
                stage.get("focus") or stage.get("title") or "中医学习任务",
                stage_id,
                node_id,
                cache_key,
                params,
            ),
            "resourceTask": {"status": "planning", "progress": 0},
        }
    )
    trace = _learning_path_resource_planner_trace(plan, str(node_id))
    stage["resourcePlanner"] = trace
    planner_runs = stage.get("resourcePlannerRuns") if isinstance(stage.get("resourcePlannerRuns"), list) else []
    if not trace["runId"] or all(str(item.get("runId") or "") != trace["runId"] for item in planner_runs if isinstance(item, dict)):
        planner_runs.append(trace)
    stage["resourcePlannerRuns"] = planner_runs[-20:]
    stage["resourceProfileReportId"] = int(profile_id or 0)
    return node


def _apply_learning_path_stage_resource_plan(
    config: dict,
    stage_id: str,
    plan: dict,
    profile_id: int,
) -> dict:
    stage = (config.get("stages") or {}).get(stage_id)
    if not isinstance(stage, dict):
        raise KeyError(stage_id)
    plan_tasks = [item for item in (plan.get("tasks") or []) if isinstance(item, dict)]
    for planned in plan_tasks:
        node_id = str(planned.get("id") or "")
        if node_id:
            _apply_learning_path_node_resource_plan(config, stage_id, node_id, planned, plan, profile_id)
    if _learning_path_stage_has_required_resources(stage):
        stage["resourcePlanVersion"] = LEARNING_PATH_RESOURCE_PLAN_VERSION
    stages = config.get("stages") if isinstance(config.get("stages"), dict) else {}
    if stages and all(
        isinstance(item, dict) and item.get("resourcePlanVersion") == LEARNING_PATH_RESOURCE_PLAN_VERSION
        for item in stages.values()
    ):
        config.setdefault("meta", {})["taskResourceModel"] = LEARNING_PATH_RESOURCE_PLAN_VERSION
    return stage


def learning_path_stage_resource_status(user_id: int, stage_id: str) -> dict:
    with auth_db() as conn:
        config = read_learning_path_config(conn, user_id)
        stage = (config.get("stages") or {}).get(stage_id)
        if not isinstance(stage, dict):
            raise KeyError(stage_id)
        stage_view = _json_copy(stage)
        cache_rows = conn.execute(
            "SELECT * FROM learning_path_node_caches WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        caches = {row["cache_key"]: learning_path_node_cache_from_row(row) for row in cache_rows}
        view_progress = _learning_path_week_view_progress(conn, user_id, config, stage_id)
        task_ids = []
        for node in stage_view.get("nodes") or []:
            cache = caches.get(str(node.get("cacheKey") or ""), {})
            resource_task = node.get("resourceTask") if isinstance(node.get("resourceTask"), dict) else {}
            task_id = str(resource_task.get("taskId") or cache.get("agentTaskId") or cache.get("taskId") or "")
            if task_id:
                task_ids.append(task_id)
        task_rows = []
        if task_ids:
            placeholders = ",".join("?" for _ in task_ids)
            task_rows = conn.execute(
                f"""
                SELECT task_id, task_type, title, prompt, status, route, result_json, error, created_at, updated_at
                FROM xiaozhi_tasks
                WHERE user_id = ? AND task_id IN ({placeholders})
                """,
                [user_id, *task_ids],
            ).fetchall()
        tasks_by_id = {row["task_id"]: xiaozhi_task_from_row(row) for row in task_rows}

    tasks = []
    pending = False
    needs_preparation_retry = False
    failed_errors: list[str] = []
    prepared_count = 0
    for node in stage_view.get("nodes") or []:
        cache_key = str(node.get("cacheKey") or "")
        cache = caches.get(cache_key, {})
        resource_task = node.get("resourceTask") if isinstance(node.get("resourceTask"), dict) else {}
        task_id = str(resource_task.get("taskId") or cache.get("agentTaskId") or cache.get("taskId") or "")
        task = tasks_by_id.get(task_id)
        if task:
            prepared_count += 1
            summary = _learning_path_task_runtime_summary(task)
            generation_attempt = _learning_path_resource_attempt(resource_task, "generationAttemptCount", 1)
            summary.update(
                {
                    "attemptCount": _learning_path_resource_attempt(resource_task, "attemptCount"),
                    "generationAttemptCount": generation_attempt,
                    "retryOfTaskId": str(resource_task.get("retryOfTaskId") or ""),
                }
            )
            node["resourceTask"] = summary
            node["actionRoute"] = summary["route"] or node.get("actionRoute") or ""
            tasks.append({"nodeId": str(node.get("id") or ""), "cacheKey": cache_key, **summary})
            pending = pending or summary["status"] in {"queued", "running"}
            if summary["status"] == "failed":
                failed_errors.append(summary.get("error") or "资源生成失败")
                needs_preparation_retry = (
                    needs_preparation_retry
                    or generation_attempt < LEARNING_PATH_RESOURCE_MAX_GENERATION_ATTEMPTS
                )
            if cache_key and (cache.get("status") != summary["status"] or cache.get("agentTaskId") != task_id):
                with auth_db() as conn:
                    upsert_learning_path_node_cache(
                        conn,
                        user_id,
                        cache_key,
                        {
                            **cache,
                            "status": summary["status"],
                            "resourceType": node.get("resourceType") or "",
                            "title": node.get("title") or "",
                            "route": summary["route"],
                            "agentTaskId": task_id,
                            "progress": summary["progress"],
                            "message": summary["message"],
                            "error": summary["error"],
                        },
                    )
        else:
            node.setdefault("resourceTask", {})
            if str(resource_task.get("status") or "") == "failed":
                failed_errors.append(str(resource_task.get("error") or "资源智能体编排失败"))
                needs_preparation_retry = (
                    needs_preparation_retry
                    or _learning_path_resource_attempt(resource_task, "attemptCount")
                    < LEARNING_PATH_RESOURCE_MAX_PLANNING_ATTEMPTS
                )

    total = len([node for node in (stage_view.get("nodes") or []) if isinstance(node, dict)])
    preparation = stage_view.get("resourcePreparation") if isinstance(stage_view.get("resourcePreparation"), dict) else {}
    orchestration_pending = str(preparation.get("status") or "") in {"initializing", "running"}
    pending = pending or orchestration_pending
    if failed_errors and not orchestration_pending:
        preparation.update({"status": "failed", "error": failed_errors[0]})
        stage_view["resourcePreparation"] = preparation
    return {
        "stage": stage_view,
        "tasks": tasks,
        "preparation": preparation,
        "preparedCount": prepared_count,
        "totalCount": total,
        "pending": pending,
        "needsPreparationRetry": needs_preparation_retry,
        "allPrepared": bool(total) and prepared_count == total,
        "allComplete": bool(total) and prepared_count == total and not orchestration_pending and all(task.get("status") == "complete" for task in tasks),
        "viewProgress": view_progress,
    }


def _reset_retryable_failed_stage_resources(
    conn: sqlite3.Connection,
    config: dict,
    stage: dict,
    user_id: int,
) -> bool:
    nodes = [item for item in (stage.get("nodes") or []) if isinstance(item, dict)]
    task_ids = [
        str((node.get("resourceTask") or {}).get("taskId") or "")
        for node in nodes
        if isinstance(node.get("resourceTask"), dict)
        and str((node.get("resourceTask") or {}).get("taskId") or "")
    ]
    if not task_ids:
        return False
    placeholders = ",".join("?" for _ in task_ids)
    rows = conn.execute(
        f"""
        SELECT task_id, task_type, title, prompt, status, route, result_json, error, created_at, updated_at
        FROM xiaozhi_tasks
        WHERE user_id = ? AND task_id IN ({placeholders})
        """,
        [int(user_id), *task_ids],
    ).fetchall()
    tasks_by_id = {row["task_id"]: xiaozhi_task_from_row(row) for row in rows}
    retryable_nodes: list[tuple[dict, str, dict, int]] = []
    terminal_errors: list[str] = []
    for node in nodes:
        resource_task = node.get("resourceTask") if isinstance(node.get("resourceTask"), dict) else {}
        task_id = str(resource_task.get("taskId") or "")
        task = tasks_by_id.get(task_id)
        if not task:
            continue
        summary = _learning_path_task_runtime_summary(task)
        if summary.get("status") != "failed":
            continue
        generation_attempt = _learning_path_resource_attempt(resource_task, "generationAttemptCount", 1)
        if generation_attempt < LEARNING_PATH_RESOURCE_MAX_GENERATION_ATTEMPTS:
            retryable_nodes.append((node, task_id, summary, generation_attempt + 1))
        else:
            terminal_errors.append(str(summary.get("error") or "资源生成失败"))

    first_node_id = str(retryable_nodes[0][0].get("id") or "") if retryable_nodes else ""
    for node, failed_task_id, summary, next_attempt in retryable_nodes:
        cache_key = str(node.get("cacheKey") or "")
        previous_resource_task = node.get("resourceTask") if isinstance(node.get("resourceTask"), dict) else {}
        last_error = str(summary.get("error") or "资源生成失败")
        node["resourceTask"] = {
            "status": "waiting",
            "progress": 0,
            "attemptCount": _learning_path_resource_attempt(previous_resource_task, "attemptCount"),
            "generationAttemptCount": next_attempt,
            "retryOfTaskId": failed_task_id,
            "lastError": last_error,
            "error": "资源生成未通过审核，正在自动重试",
        }
        node["actionRoute"] = ""
        if cache_key:
            cache_row = conn.execute(
                "SELECT * FROM learning_path_node_caches WHERE user_id = ? AND cache_key = ?",
                (int(user_id), cache_key),
            ).fetchone()
            cache = learning_path_node_cache_from_row(cache_row) if cache_row else {}
            upsert_learning_path_node_cache(
                conn,
                int(user_id),
                cache_key,
                {
                    **cache,
                    "status": "waiting",
                    "agentTaskId": "",
                    "taskId": "",
                    "route": "",
                    "error": "资源生成未通过审核，正在自动重试",
                    "failedTaskId": failed_task_id,
                    "lastError": last_error,
                    "generationAttemptCount": next_attempt,
                },
            )

    if not retryable_nodes and not terminal_errors:
        return False

    preparation = stage.get("resourcePreparation") if isinstance(stage.get("resourcePreparation"), dict) else {}
    prepared_count = sum(
        1
        for node in nodes
        if str((node.get("resourceTask") or {}).get("taskId") or "")
    )
    preparation.update(
        {
            "status": "running" if retryable_nodes else "failed",
            "plannedCount": prepared_count,
            "resolvedCount": prepared_count,
            "totalCount": len(nodes),
            "currentNodeId": first_node_id,
            "updatedAt": now_iso(),
            "error": "" if retryable_nodes else terminal_errors[0],
        }
    )
    stage["resourcePreparation"] = preparation
    return True


def _plan_learning_path_resource_node(
    user_id: int,
    stage_id: str,
    stage_snapshot: dict,
    node_snapshot: dict,
    profile: dict,
    profile_id: int,
    use_llm: bool,
    planning_attempt: int,
    previous_types: list[str],
    platform_context: dict,
) -> dict:
    node_id = str(node_snapshot.get("id") or "")
    single_stage = {
        **_json_copy(stage_snapshot),
        "nodes": [_json_copy(node_snapshot)],
        "previousResourceTypes": list(previous_types),
    }
    compact_stage = {
        "id": str(stage_snapshot.get("id") or stage_id),
        "weekLabel": str(stage_snapshot.get("weekLabel") or ""),
        "title": str(stage_snapshot.get("title") or ""),
        "focus": str(stage_snapshot.get("focus") or ""),
        "objective": str(stage_snapshot.get("objective") or ""),
        "previousResourceTypes": list(previous_types[-8:]),
        "parallelBatchNodeIds": [
            str(node.get("id") or "")
            for node in (stage_snapshot.get("nodes") or [])
            if isinstance(node, dict) and str(node.get("id") or "")
        ],
        "nodes": [
            {
                key: node_snapshot.get(key)
                for key in ("id", "title", "description", "deliverable", "state", "order")
                if node_snapshot.get(key) not in (None, "")
            }
        ],
    }
    planner_payload = {
        "profileReportId": profile_id,
        "profileContext": build_learning_profile_context(profile),
        "stage": compact_stage,
        "useLLM": use_llm,
        "action": "route-one-stage-resource",
        "nodeId": node_id,
        "attemptCount": planning_attempt,
        "parallelPlanning": True,
    }

    def plan_single_resource(managed_payload: dict, _progress) -> dict:
        planned_result = plan_learning_path_stage_resources(
            {
                **managed_payload,
                "profile": profile,
                "stage": single_stage,
                "useLLM": use_llm,
            }
        )
        if not isinstance(planned_result, dict):
            raise RuntimeError("资源路由智能体未返回结构化计划")
        return {
            **planned_result,
            "message": "当前学习任务的资源智能体编排已完成。",
            "stageDetail": planned_result,
        }

    with private_knowledge_service.private_knowledge_scope(user_id, AUTH_DB_PATH):
        try:
            planner = xiaozhi_run_orchestrated(
                "learning_path_stage",
                f"{stage_snapshot.get('weekLabel') or '本周'}任务 {node_id} 资源智能体编排",
                planner_payload,
                user_id,
                plan_single_resource,
                context=_json_copy(platform_context),
                max_retries=1,
            )
        except SkillReviewError as review_error:
            review_result = review_error.result if isinstance(review_error.result, dict) else {}
            reviewed_detail = review_result.get("stageDetail") if isinstance(review_result.get("stageDetail"), dict) else {}
            candidate_plan = reviewed_detail if isinstance(reviewed_detail.get("tasks"), list) else review_result
            if not isinstance(candidate_plan.get("tasks"), list) or not candidate_plan["tasks"]:
                raise
            planner = {
                **candidate_plan,
                "message": "资源路由已生成，但质量审核提示需要人工核验；系统保留可打开资源入口。",
                "source": str(candidate_plan.get("source") or "review-tolerant"),
                "reviewWarning": str(review_error),
                "orchestration": review_result.get("orchestration") if isinstance(review_result.get("orchestration"), dict) else {},
                "harness": review_result.get("harness") if isinstance(review_result.get("harness"), dict) else {},
            }

    planned_tasks = [item for item in (planner.get("tasks") or []) if isinstance(item, dict)]
    if not planned_tasks:
        raise RuntimeError("资源路由智能体未返回当前任务计划")
    planned = next((item for item in planned_tasks if str(item.get("id") or "") == node_id), planned_tasks[0])
    return {"nodeId": node_id, "planner": planner, "planned": planned}


def _enforce_parallel_learning_path_resource_coverage(
    stage: dict,
    planning_states: list[dict],
    planning_results: dict[str, dict],
    profile: dict,
) -> None:
    """Reconcile independently planned nodes into one complete weekly resource set."""
    nodes = [node for node in (stage.get("nodes") or []) if isinstance(node, dict)]
    planning_node_ids = {str(state.get("nodeId") or "") for state in planning_states}
    existing_resource_types = [
        _canonical_learning_path_task_resource(node, index)
        for index, node in enumerate(nodes, start=1)
        if str(node.get("id") or "") not in planning_node_ids
        and str((node.get("resourceTask") or {}).get("taskId") or "")
    ]
    planned_tasks: list[dict] = []
    planned_nodes: list[dict] = []
    for state in planning_states:
        node_id = str(state.get("nodeId") or "")
        outcome = planning_results.get(node_id) or {}
        if str(outcome.get("error") or ""):
            continue
        plan_result = outcome.get("result") if isinstance(outcome.get("result"), dict) else {}
        planned = plan_result.get("planned") if isinstance(plan_result.get("planned"), dict) else {}
        if not planned:
            continue
        node = next((item for item in nodes if str(item.get("id") or "") == node_id), {})
        planned_tasks.append({**planned, "id": node_id})
        planned_nodes.append(node)

    covered_tasks = ensure_weekly_learning_path_resource_coverage(
        planned_tasks,
        planned_nodes,
        profile_context=build_learning_profile_context(profile),
        topic=str(stage.get("focus") or stage.get("goal") or stage.get("title") or "中医学习任务"),
        stage_id=str(stage.get("id") or ""),
        existing_resource_types=existing_resource_types,
    )
    covered_by_id = {
        str(task.get("id") or ""): task
        for task in covered_tasks
        if str(task.get("id") or "")
    }
    for node_id, covered in covered_by_id.items():
        outcome = planning_results.get(node_id) or {}
        plan_result = outcome.get("result") if isinstance(outcome.get("result"), dict) else {}
        plan_result["planned"] = covered
        outcome["result"] = plan_result
        planning_results[node_id] = outcome


def _materialize_learning_path_resource_node(
    config: dict,
    stage_id: str,
    user_id: int,
    profile_id: int,
    plan_result: dict,
    planning_state: dict,
) -> dict:
    node_id = str(plan_result.get("nodeId") or "")
    planner = plan_result.get("planner") if isinstance(plan_result.get("planner"), dict) else {}
    planned = plan_result.get("planned") if isinstance(plan_result.get("planned"), dict) else {}
    planning_attempt = int(planning_state.get("planningAttempt") or 1)
    generation_attempt = int(planning_state.get("generationAttempt") or 1)
    retry_of_task_id = str(planning_state.get("retryOfTaskId") or "")
    previous_error = str(planning_state.get("previousError") or "")

    node = _apply_learning_path_node_resource_plan(
        config,
        stage_id,
        node_id,
        planned,
        planner,
        profile_id,
    )
    node["resourceTask"].update(
        {
            "attemptCount": planning_attempt,
            "generationAttemptCount": generation_attempt,
            "retryOfTaskId": retry_of_task_id,
            "lastError": previous_error,
        }
    )
    stage = (config.get("stages") or {}).get(stage_id) or {}
    cache_key = str(node.get("cacheKey") or "")
    with auth_db() as conn:
        cache_row = conn.execute(
            "SELECT * FROM learning_path_node_caches WHERE user_id = ? AND cache_key = ?",
            (user_id, cache_key),
        ).fetchone()
        cache = learning_path_node_cache_from_row(cache_row) if cache_row else {}
        resource_task = node.get("resourceTask") if isinstance(node.get("resourceTask"), dict) else {}
        task_id = str(resource_task.get("taskId") or cache.get("agentTaskId") or cache.get("taskId") or "")
        task_row = conn.execute(
            """
            SELECT task_id, task_type, title, prompt, status, route, result_json, error, created_at, updated_at
            FROM xiaozhi_tasks WHERE user_id = ? AND task_id = ? LIMIT 1
            """,
            (user_id, task_id),
        ).fetchone() if task_id else None

    if task_row:
        task = xiaozhi_task_from_row(task_row)
    else:
        params = _json_copy(node.get("resourceParams")) if isinstance(node.get("resourceParams"), dict) else {}
        params.update(
            {
                "source": "learning-path",
                "stageId": stage_id,
                "nodeId": node_id,
                "cacheKey": cache_key,
                "profileReportId": profile_id,
            }
        )
        if str(node.get("resourceType") or "") == "generated_video":
            # Path planning only adds the entry; the user must explicitly start media generation.
            params["deferred"] = True
        task = xiaozhi_create_resource_agent_task(
            user_id,
            str(node.get("resourceType") or ""),
            str(params.get("topic") or stage.get("focus") or stage.get("title") or node.get("title") or "中医学习任务"),
            params,
            title=f"{stage.get('weekLabel') or '本周'} · {node.get('title') or '学习任务'}",
            prompt=str(node.get("resourcePrompt") or node.get("description") or node.get("title") or "生成学习资源"),
        )
        task_id = task["taskId"]

    summary = _learning_path_task_runtime_summary(task)
    summary.update(
        {
            "attemptCount": planning_attempt,
            "generationAttemptCount": generation_attempt,
            "retryOfTaskId": retry_of_task_id,
            "lastError": previous_error,
        }
    )
    node["resourceTask"] = summary
    node["actionRoute"] = summary["route"] or node.get("actionRoute") or ""
    with auth_db() as conn:
        upsert_learning_path_node_cache(
            conn,
            user_id,
            cache_key,
            {
                **cache,
                "status": summary["status"],
                "resourceType": node.get("resourceType") or "",
                "title": node.get("title") or "",
                "route": summary["route"],
                "agentTaskId": task_id,
                "resourceParams": node.get("resourceParams") or {},
                "resourcePrompt": node.get("resourcePrompt") or "",
                "profileReportId": profile_id,
                "progress": summary["progress"],
                "attemptCount": planning_attempt,
                "generationAttemptCount": generation_attempt,
                "retryOfTaskId": retry_of_task_id,
            },
        )
    return node


def _parallel_dispatch_learning_path_resource_nodes(
    config: dict,
    stage_id: str,
    user_id: int,
    profile: dict,
    profile_id: int,
) -> dict:
    """Create every task entry first, then let the shared executors generate in parallel."""
    stage = (config.get("stages") or {}).get(stage_id)
    if not isinstance(stage, dict):
        raise KeyError(stage_id)
    nodes = [node for node in (stage.get("nodes") or []) if isinstance(node, dict)]
    candidates = _learning_path_resource_plan_nodes(nodes)
    if not candidates:
        status = learning_path_stage_resource_status(user_id, stage_id)
        status.update(
            {
                "dispatchMode": "parallel",
                "profileReportId": profile_id,
                "submittedCount": 0,
                "allEntrypointsReady": bool(nodes) and all(
                    str((node.get("resourceTask") or {}).get("taskId") or "")
                    for node in nodes
                ),
            }
        )
        return status

    node_indexes = {
        str(node.get("id") or ""): index
        for index, node in enumerate(nodes, start=1)
    }
    candidate_ids = {str(node.get("id") or "") for node in candidates}
    existing_resource_types = [
        _canonical_learning_path_task_resource(node, index)
        for index, node in enumerate(nodes, start=1)
        if str(node.get("id") or "") not in candidate_ids
        and str((node.get("resourceTask") or {}).get("taskId") or "")
    ]
    direct_tasks: list[dict] = []
    planning_states: list[dict] = []
    for candidate in candidates:
        node_id = str(candidate.get("id") or "")
        node_index = node_indexes.get(node_id, len(direct_tasks) + 1)
        resource_type = _canonical_learning_path_task_resource(candidate, node_index)
        params = _json_copy(candidate.get("resourceParams")) if isinstance(candidate.get("resourceParams"), dict) else {}
        params.setdefault(
            "topic",
            str(candidate.get("title") or stage.get("focus") or stage.get("title") or "中医学习任务"),
        )
        direct_tasks.append(
            {
                "id": node_id,
                "title": str(candidate.get("title") or "学习任务"),
                "resourceType": resource_type,
                "resourceParams": params,
                "resourcePrompt": _clean_text(
                    candidate.get("resourcePrompt"),
                    candidate.get("description") or candidate.get("title") or "生成学习资源",
                ),
                "resourceSelectionReason": _clean_text(
                    candidate.get("resourceSelectionReason"),
                    "直接使用学习路径智能体已经生成的资源参数并提交后台生成。",
                ),
                "resourceSelectionSource": _clean_text(
                    candidate.get("resourceSelectionSource"),
                    "learning-path-direct-dispatch",
                ),
            }
        )
        previous_task = candidate.get("resourceTask") if isinstance(candidate.get("resourceTask"), dict) else {}
        planning_states.append(
            {
                "nodeId": node_id,
                "planningAttempt": _learning_path_resource_attempt(previous_task, "attemptCount") + 1,
                "generationAttempt": _learning_path_resource_attempt(previous_task, "generationAttemptCount", 1),
                "retryOfTaskId": str(previous_task.get("retryOfTaskId") or ""),
                "previousError": str(previous_task.get("lastError") or previous_task.get("error") or ""),
            }
        )
        candidate["resourceTask"] = {
            "status": "planning",
            "progress": 0,
            "attemptCount": planning_states[-1]["planningAttempt"],
            "generationAttemptCount": planning_states[-1]["generationAttempt"],
            "retryOfTaskId": planning_states[-1]["retryOfTaskId"],
            "lastError": planning_states[-1]["previousError"],
        }

    covered_tasks = ensure_weekly_learning_path_resource_coverage(
        direct_tasks,
        candidates,
        profile_context=build_learning_profile_context(profile),
        topic=str(stage.get("focus") or stage.get("goal") or stage.get("title") or "中医学习任务"),
        existing_resource_types=existing_resource_types,
    )
    covered_by_id = {
        str(task.get("id") or ""): task
        for task in covered_tasks
        if isinstance(task, dict) and str(task.get("id") or "")
    }
    active_node_ids = [state["nodeId"] for state in planning_states]
    preparation = stage.get("resourcePreparation") if isinstance(stage.get("resourcePreparation"), dict) else {}
    preparation.update(
        {
            "version": LEARNING_PATH_RESOURCE_PLAN_VERSION,
            "status": "running",
            "profileReportId": profile_id,
            "currentNodeId": active_node_ids[0] if active_node_ids else "",
            "activeNodeIds": active_node_ids,
            "totalCount": len(nodes),
            "updatedAt": now_iso(),
            "error": "",
            "dispatchMode": "parallel",
        }
    )
    stage["resourcePreparation"] = preparation
    config = _persist_learning_path_stage_update(user_id, stage_id, stage)

    dispatch_traces: list[dict] = []
    for state in planning_states:
        node_id = state["nodeId"]
        planned = covered_by_id.get(node_id) or next(
            (task for task in direct_tasks if str(task.get("id") or "") == node_id),
            {},
        )
        current_stage = (config.get("stages") or {}).get(stage_id) or stage
        current_node = next(
            (
                node
                for node in (current_stage.get("nodes") or [])
                if isinstance(node, dict) and str(node.get("id") or "") == node_id
            ),
            {},
        )
        knowledge_sources = (
            current_node.get("knowledgeSources")
            if isinstance(current_node.get("knowledgeSources"), list)
            else []
        )
        dispatcher = {
            "agent": "learning-path-resource-dispatcher",
            "source": "learning-path-direct-dispatch",
            "grounded": bool(knowledge_sources),
            "knowledgeSources": knowledge_sources,
            "message": "已复用学习路径参数并提交后台并行生成。",
        }
        dispatch_traces.append(dispatcher)
        try:
            _materialize_learning_path_resource_node(
                config,
                stage_id,
                user_id,
                profile_id,
                {"nodeId": node_id, "planner": dispatcher, "planned": planned},
                state,
            )
        except Exception as exc:
            current_stage = (config.get("stages") or {}).get(stage_id) or stage
            current_node = next(
                (
                    node
                    for node in (current_stage.get("nodes") or [])
                    if isinstance(node, dict) and str(node.get("id") or "") == node_id
                ),
                None,
            )
            if current_node is not None:
                error_message = str(exc) or "当前任务后台派发失败"
                current_node["resourceTask"] = {
                    "status": "failed",
                    "progress": 100,
                    "error": error_message,
                    "lastError": error_message,
                    "attemptCount": int(state["planningAttempt"]),
                    "generationAttemptCount": int(state["generationAttempt"]),
                    "retryOfTaskId": str(state["retryOfTaskId"]),
                    "retryable": int(state["planningAttempt"]) < LEARNING_PATH_RESOURCE_MAX_PLANNING_ATTEMPTS,
                }

    stage = (config.get("stages") or {}).get(stage_id) or stage
    nodes = [node for node in (stage.get("nodes") or []) if isinstance(node, dict)]
    task_count = sum(
        1
        for node in nodes
        if str((node.get("resourceTask") or {}).get("taskId") or "")
    )
    failed_nodes = [
        node
        for node in nodes
        if not str((node.get("resourceTask") or {}).get("taskId") or "")
        and str((node.get("resourceTask") or {}).get("status") or "") == "failed"
    ]
    failed_node = failed_nodes[0] if failed_nodes else None
    error_message = str((failed_node.get("resourceTask") or {}).get("error") or "") if failed_node else ""
    preparation = stage.get("resourcePreparation") if isinstance(stage.get("resourcePreparation"), dict) else {}
    preparation.update(
        {
            "status": "failed" if failed_node else "complete",
            "plannedCount": task_count,
            "resolvedCount": task_count + len(failed_nodes),
            "totalCount": len(nodes),
            "currentNodeId": "",
            "activeNodeIds": [],
            "updatedAt": now_iso(),
            "error": error_message,
            "dispatchMode": "parallel",
        }
    )
    stage["resourcePreparation"] = preparation
    if not failed_node and _learning_path_stage_has_required_resources(stage):
        stage["resourcePlanVersion"] = LEARNING_PATH_RESOURCE_PLAN_VERSION
    stage["resourceProfileReportId"] = profile_id
    _persist_learning_path_stage_update(user_id, stage_id, stage)

    status = learning_path_stage_resource_status(user_id, stage_id)
    status.update(
        {
            "dispatchMode": "parallel",
            "profileReportId": profile_id,
            "submittedCount": len(planning_states),
            "allEntrypointsReady": bool(nodes) and task_count == len(nodes),
            "planners": dispatch_traces,
        }
    )
    return status


def _prepare_learning_path_week_resources_in_background(user_id: int, stage_id: str) -> None:
    """Plan a saved week without tying resource generation to the browser view."""
    try:
        prepare_learning_path_stage_resources_for_user(
            int(user_id),
            str(stage_id),
            use_llm=True,
            advance=False,
            parallel_dispatch=True,
        )
    except Exception:
        app.logger.exception(
            "learning path background resource preparation failed for user=%s stage=%s",
            user_id,
            stage_id,
        )


def _queue_learning_path_week_resource_preparation(
    user_id: int,
    config: dict,
    *,
    stage_ids: list[str] | None = None,
    only_incomplete: bool = False,
    max_stages: int = 0,
) -> int:
    """Start non-video weekly resources as soon as their path tasks are saved."""
    stages = config.get("stages") if isinstance(config.get("stages"), dict) else {}
    weeks = config.get("weeks") if isinstance(config.get("weeks"), list) else []
    restrict_to_requested = stage_ids is not None
    requested_stage_ids = {str(stage_id) for stage_id in (stage_ids or []) if str(stage_id)}
    resolved_stage_ids = [
        str(week.get("id") or "")
        for week in weeks
        if isinstance(week, dict)
        and week.get("enabled", True)
        and not week.get("placeholder", False)
        and str(week.get("id") or "") in stages
        and (not restrict_to_requested or str(week.get("id") or "") in requested_stage_ids)
        and (
            not only_incomplete
            or _learning_path_stage_needs_resource_recovery(stages[str(week.get("id") or "")])
        )
    ]
    if not resolved_stage_ids and not restrict_to_requested and not only_incomplete:
        resolved_stage_ids = [str(stage_id) for stage_id in stages if str(stage_id)]
    resolved_stage_ids = list(dict.fromkeys(resolved_stage_ids))
    if int(max_stages or 0) > 0:
        resolved_stage_ids = resolved_stage_ids[:int(max_stages)]
    submitted = 0
    for stage_id in resolved_stage_ids:
        try:
            LEARNING_PATH_WEEK_PREPARATION_EXECUTOR.submit(
                _prepare_learning_path_week_resources_in_background,
                int(user_id),
                stage_id,
            )
            submitted += 1
        except QueueCapacityError:
            app.logger.warning(
                "learning path preparation queue full user=%s stage=%s",
                user_id,
                stage_id,
            )
            break
    return submitted


def _learning_path_stage_needs_resource_recovery(stage: dict) -> bool:
    nodes = [node for node in (stage.get("nodes") or []) if isinstance(node, dict) and node.get("enabled", True)]
    if not nodes:
        return False
    preparation = stage.get("resourcePreparation") if isinstance(stage.get("resourcePreparation"), dict) else {}
    if str(preparation.get("status") or "") in {"running", "initializing", "failed"}:
        return True
    for node in nodes:
        task = node.get("resourceTask") if isinstance(node.get("resourceTask"), dict) else {}
        status = str(task.get("status") or "")
        route = str(task.get("route") or node.get("actionRoute") or "")
        if not str(task.get("taskId") or "") or "xzTask=" not in route:
            return True
        if status in {"planning", "queued", "running", "failed"}:
            return True
    return False


def prepare_learning_path_stage_resources_for_user(
    user_id: int,
    stage_id: str,
    *,
    use_llm: bool = True,
    advance: bool = True,
    parallel_dispatch: bool = False,
) -> dict:
    lock = _learning_path_stage_resource_lock(user_id, stage_id)
    with lock:
        with auth_db() as conn:
            config = read_learning_path_config(conn, user_id)
            stage = (config.get("stages") or {}).get(stage_id)
            if not isinstance(stage, dict):
                raise KeyError(stage_id)
            profile = active_profile_for_user(conn, user_id) or {}
            if not profile:
                raise LearningProfileRequiredError(
                    "当前没有激活画像，暂不能为学习路径编排个性化资源。请先完成十个维度的画像采集。"
                )
            if learning_path_config_is_degraded(config):
                raise LearningProfileRequiredError(
                    "当前学习路径是未通过模型审核的降级结果，暂不能编排资源。请先重新生成个性化学习路径。"
                )

        profile_id = int(profile.get("id") or profile.get("_profileReportId") or 0)
        if enrich_learning_path_task_descriptions(stage, profile):
            config = _persist_learning_path_stage_update(user_id, stage_id, stage)
            stage = (config.get("stages") or {}).get(stage_id) or stage

        nodes = [item for item in (stage.get("nodes") or []) if isinstance(item, dict)]
        preparation = stage.get("resourcePreparation") if isinstance(stage.get("resourcePreparation"), dict) else {}
        effective_stage_plan_version = str(
            stage.get("resourcePlanVersion") or preparation.get("version") or ""
        )
        existing_task_count = sum(
            1
            for node in nodes
            if str((node.get("resourceTask") or {}).get("taskId") or "")
        )
        declared_profile_id = int(
            stage.get("resourceProfileReportId")
            or preparation.get("profileReportId")
            or 0
        )
        can_adopt_existing_parallel_tasks = bool(
            parallel_dispatch
            and existing_task_count
            and declared_profile_id in {0, profile_id}
            and _learning_path_stage_has_required_resources(stage)
        )
        needs_initialization = (
            effective_stage_plan_version != LEARNING_PATH_RESOURCE_PLAN_VERSION
            or preparation.get("version") != LEARNING_PATH_RESOURCE_PLAN_VERSION
            or int(preparation.get("profileReportId") or 0) != profile_id
            or not _learning_path_stage_has_required_resources(stage)
        )
        if can_adopt_existing_parallel_tasks:
            preparation.update(
                {
                    "version": LEARNING_PATH_RESOURCE_PLAN_VERSION,
                    "profileReportId": profile_id,
                    "plannedCount": existing_task_count,
                    "resolvedCount": existing_task_count,
                    "totalCount": len(nodes),
                    "updatedAt": now_iso(),
                    "dispatchMode": "parallel",
                }
            )
            stage["resourcePlanVersion"] = LEARNING_PATH_RESOURCE_PLAN_VERSION
            stage["resourceProfileReportId"] = profile_id
            stage["resourcePreparation"] = preparation
            config = _persist_learning_path_stage_update(user_id, stage_id, stage)
            stage = (config.get("stages") or {}).get(stage_id) or stage
            needs_initialization = False
        if needs_initialization:
            timestamp = now_iso()
            for node in nodes:
                node["resourceTask"] = {"status": "waiting", "progress": 0}
                node["cacheKey"] = ""
                node["actionRoute"] = ""
            stage["resourcePlanVersion"] = ""
            stage["resourceProfileReportId"] = profile_id
            stage["resourcePlanner"] = {}
            stage["resourcePlannerRuns"] = []
            stage["resourcePreparation"] = {
                "version": LEARNING_PATH_RESOURCE_PLAN_VERSION,
                "status": "running",
                "profileReportId": profile_id,
                "plannedCount": 0,
                "resolvedCount": 0,
                "totalCount": len(nodes),
                "currentNodeId": str(nodes[0].get("id") or "") if nodes else "",
                "activeNodeIds": [],
                "startedAt": timestamp,
                "updatedAt": timestamp,
                "error": "",
            }
            config = _persist_learning_path_stage_update(user_id, stage_id, stage)
            stage = (config.get("stages") or {}).get(stage_id) or stage
        else:
            with auth_db() as conn:
                reset_failed = _reset_retryable_failed_stage_resources(
                    conn,
                    config,
                    stage,
                    user_id,
                )
            if reset_failed:
                config = _persist_learning_path_stage_update(user_id, stage_id, stage)
                stage = (config.get("stages") or {}).get(stage_id) or stage

        nodes = [item for item in (stage.get("nodes") or []) if isinstance(item, dict)]
        candidates = _learning_path_resource_plan_nodes(nodes)
        preparation = stage.get("resourcePreparation") if isinstance(stage.get("resourcePreparation"), dict) else {}
        if candidates and str(preparation.get("status") or "") not in {"initializing", "running"}:
            preparation.update(
                {
                    "status": "running",
                    "currentNodeId": str(candidates[0].get("id") or ""),
                    "activeNodeIds": [],
                    "updatedAt": now_iso(),
                    "error": "",
                }
            )
            stage["resourcePreparation"] = preparation
            config = _persist_learning_path_stage_update(user_id, stage_id, stage)
            stage = (config.get("stages") or {}).get(stage_id) or stage

        if parallel_dispatch:
            return _parallel_dispatch_learning_path_resource_nodes(
                config,
                stage_id,
                user_id,
                profile,
                profile_id,
            )

        if not advance:
            status = learning_path_stage_resource_status(user_id, stage_id)
            status["profileReportId"] = profile_id
            return status

        nodes = [item for item in (stage.get("nodes") or []) if isinstance(item, dict)]
        candidates = _learning_path_resource_plan_nodes(nodes)
        if not candidates:
            preparation = stage.get("resourcePreparation") if isinstance(stage.get("resourcePreparation"), dict) else {}
            coverage_complete = _learning_path_stage_has_required_resources(stage)
            terminal_error = next(
                (
                    str((node.get("resourceTask") or {}).get("error") or "资源智能体编排失败")
                    for node in nodes
                    if str((node.get("resourceTask") or {}).get("status") or "") == "failed"
                ),
                "",
            )
            if not terminal_error and not coverage_complete:
                terminal_error = "本周资源编排未覆盖全部七类资源，将自动重新编排。"
            stage["resourcePlanVersion"] = (
                LEARNING_PATH_RESOURCE_PLAN_VERSION if not terminal_error else ""
            )
            preparation.update(
                {
                    "status": "failed" if terminal_error else "complete",
                    "currentNodeId": "",
                    "activeNodeIds": [],
                    "updatedAt": now_iso(),
                    "error": terminal_error,
                }
            )
            stage["resourcePreparation"] = preparation
            _persist_learning_path_stage_update(user_id, stage_id, stage)
            status = learning_path_stage_resource_status(user_id, stage_id)
            status["profileReportId"] = profile_id
            return status

        planning_states: list[dict] = []
        for candidate in candidates:
            node_id = str(candidate.get("id") or "")
            previous_resource_task = (
                candidate.get("resourceTask")
                if isinstance(candidate.get("resourceTask"), dict)
                else {}
            )
            planning_attempt = _learning_path_resource_attempt(previous_resource_task, "attemptCount") + 1
            generation_attempt = _learning_path_resource_attempt(
                previous_resource_task,
                "generationAttemptCount",
                1,
            )
            previous_error = str(
                previous_resource_task.get("lastError")
                or previous_resource_task.get("error")
                or ""
            )
            retry_of_task_id = str(previous_resource_task.get("retryOfTaskId") or "")
            candidate["resourceTask"] = {
                "status": "planning",
                "progress": 0,
                "attemptCount": planning_attempt,
                "generationAttemptCount": generation_attempt,
                "retryOfTaskId": retry_of_task_id,
                "lastError": previous_error,
            }
            planning_states.append(
                {
                    "nodeId": node_id,
                    "planningAttempt": planning_attempt,
                    "generationAttempt": generation_attempt,
                    "retryOfTaskId": retry_of_task_id,
                    "previousError": previous_error,
                }
            )

        active_node_ids = [state["nodeId"] for state in planning_states]
        preparation = stage.get("resourcePreparation") if isinstance(stage.get("resourcePreparation"), dict) else {}
        preparation.update(
            {
                "status": "running",
                "currentNodeId": active_node_ids[0] if active_node_ids else "",
                "activeNodeIds": active_node_ids,
                "updatedAt": now_iso(),
                "error": "",
            }
        )
        stage["resourcePreparation"] = preparation
        config = _persist_learning_path_stage_update(user_id, stage_id, stage)

        stage = (config.get("stages") or {}).get(stage_id) or stage
        stage_snapshot = _json_copy(stage)
        persisted_nodes = {
            str(node.get("id") or ""): node
            for node in (stage.get("nodes") or [])
            if isinstance(node, dict)
        }
        previous_types = [
            str(node.get("resourceType") or "")
            for node in (stage.get("nodes") or [])
            if isinstance(node, dict)
            and str((node.get("resourceTask") or {}).get("taskId") or "")
            and str(node.get("resourceType") or "")
        ]
        platform_context = xiaozhi_latest_context(user_id)
        planning_results: dict[str, dict] = {}
        max_workers = min(
            LEARNING_PATH_RESOURCE_PLANNER_MAX_WORKERS,
            max(1, len(planning_states)),
        )
        with ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="learning-path-resource-planner",
        ) as executor:
            futures = []
            for state in planning_states:
                node_snapshot = _json_copy(persisted_nodes.get(state["nodeId"]) or {})
                future = executor.submit(
                    _plan_learning_path_resource_node,
                    user_id,
                    stage_id,
                    stage_snapshot,
                    node_snapshot,
                    _json_copy(profile),
                    profile_id,
                    use_llm,
                    int(state["planningAttempt"]),
                    list(previous_types),
                    platform_context,
                )
                futures.append((state, future))

            for state, future in futures:
                try:
                    planning_results[state["nodeId"]] = {
                        "result": future.result(),
                        "error": "",
                    }
                except Exception as exc:
                    planning_results[state["nodeId"]] = {
                        "result": {},
                        "error": str(exc) or "当前任务资源编排失败",
                    }

        # Each node is routed independently for latency. Reconcile the complete
        # batch before creating any resource task so the weekly invariant cannot
        # be lost to duplicate model choices.
        _enforce_parallel_learning_path_resource_coverage(
            stage,
            planning_states,
            planning_results,
            profile,
        )

        planners: list[dict] = []
        for state in planning_states:
            node_id = state["nodeId"]
            outcome = planning_results.get(node_id) or {}
            step_error = str(outcome.get("error") or "")
            if not step_error:
                plan_result = outcome.get("result") if isinstance(outcome.get("result"), dict) else {}
                planner = plan_result.get("planner") if isinstance(plan_result.get("planner"), dict) else {}
                if planner:
                    planners.append(planner)
                try:
                    _materialize_learning_path_resource_node(
                        config,
                        stage_id,
                        user_id,
                        profile_id,
                        plan_result,
                        state,
                    )
                    continue
                except Exception as exc:
                    step_error = str(exc) or "当前任务资源创建失败"

            stage = (config.get("stages") or {}).get(stage_id) or stage
            node = next(
                (
                    item
                    for item in (stage.get("nodes") or [])
                    if isinstance(item, dict) and str(item.get("id") or "") == node_id
                ),
                None,
            )
            if node is not None:
                planning_attempt = int(state["planningAttempt"])
                node["resourceTask"] = {
                    "status": "failed",
                    "progress": 100,
                    "error": step_error,
                    "lastError": step_error,
                    "attemptCount": planning_attempt,
                    "generationAttemptCount": int(state["generationAttempt"]),
                    "retryOfTaskId": str(state["retryOfTaskId"]),
                    "retryable": planning_attempt < LEARNING_PATH_RESOURCE_MAX_PLANNING_ATTEMPTS,
                }

        stage = (config.get("stages") or {}).get(stage_id) or stage
        nodes = [item for item in (stage.get("nodes") or []) if isinstance(item, dict)]
        planned_count = sum(
            1
            for node in nodes
            if str((node.get("resourceTask") or {}).get("taskId") or "")
        )
        resolved_count = sum(
            1
            for node in nodes
            if str((node.get("resourceTask") or {}).get("taskId") or "")
            or str((node.get("resourceTask") or {}).get("status") or "") == "failed"
        )
        next_candidates = _learning_path_resource_plan_nodes(nodes)
        terminal_planning_error = next(
            (
                str((node.get("resourceTask") or {}).get("error") or "资源智能体编排失败")
                for node in nodes
                if not str((node.get("resourceTask") or {}).get("taskId") or "")
                and str((node.get("resourceTask") or {}).get("status") or "") == "failed"
                and _learning_path_resource_attempt(node.get("resourceTask") or {}, "attemptCount")
                >= LEARNING_PATH_RESOURCE_MAX_PLANNING_ATTEMPTS
            ),
            "",
        )
        coverage_complete = _learning_path_stage_has_required_resources(stage)
        if not next_candidates and not terminal_planning_error and not coverage_complete:
            terminal_planning_error = "本周资源编排未覆盖全部七类资源，将自动重新编排。"
        preparation_status = (
            "running"
            if next_candidates
            else ("failed" if terminal_planning_error else "complete")
        )
        preparation = stage.get("resourcePreparation") if isinstance(stage.get("resourcePreparation"), dict) else {}
        preparation.update(
            {
                "status": preparation_status,
                "plannedCount": planned_count,
                "resolvedCount": resolved_count,
                "totalCount": len(nodes),
                "currentNodeId": str(next_candidates[0].get("id") or "") if next_candidates else "",
                "activeNodeIds": [],
                "updatedAt": now_iso(),
                "error": terminal_planning_error if preparation_status == "failed" else "",
            }
        )
        stage["resourcePreparation"] = preparation
        if preparation_status == "complete":
            stage["resourcePlanVersion"] = LEARNING_PATH_RESOURCE_PLAN_VERSION
        elif preparation_status == "failed":
            stage["resourcePlanVersion"] = ""
        _persist_learning_path_stage_update(user_id, stage_id, stage)

        status = learning_path_stage_resource_status(user_id, stage_id)
        status["planner"] = planners[-1] if planners else {}
        status["planners"] = planners
        status["profileReportId"] = profile_id
        return status


def _bind_service_function(function):
    @wraps(function)
    def bound(*args, **kwargs):
        _sync_dependencies()
        return function(*args, **kwargs)

    return bound


for _function_name in EXPORTED_FUNCTIONS:
    globals()[_function_name] = _bind_service_function(globals()[_function_name])

del _function_name
