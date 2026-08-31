"""Xiaozhi supervisor, model-runtime, task, and resource-agent orchestration services."""

from __future__ import annotations

from functools import wraps
from typing import Callable

_DependencyProvider = Callable[[str], object]
_provider: _DependencyProvider | None = None


def configure(provider: _DependencyProvider) -> None:
    global _provider
    _provider = provider


def _sync_dependencies() -> None:
    if _provider is None:
        raise RuntimeError("xiaozhi_service has not been configured")
    namespace = globals()
    for name in DEPENDENCY_NAMES:
        try:
            namespace[name] = _provider(name)
        except (KeyError, AttributeError):
            continue

DEPENDENCY_NAMES = (
    'AGENT_CATALOG',
    'AUTH_DB_PATH',
    'DEFAULT_AGENT_HARNESS',
    'DEFAULT_TEXT_MODEL_ID',
    'HERB_MODEL_REVISION',
    'LLM_RESPONSE_TOKEN_BUDGET',
    'LearningProfileRequiredError',
    'PPT_RESOURCE_EXECUTOR',
    'Path',
    'ProfileAgentContextStore',
    'QueueCapacityError',
    'RESOURCE_AGENT_ALLOWED_TYPES',
    'RESOURCE_AGENT_EXECUTOR',
    'RESOURCE_AGENT_TYPE_ALIASES',
    'RESOURCE_TASK_ADMISSION',
    'SkillReviewError',
    'VIDEO_RESOURCE_EXECUTOR',
    'XIAOZHI_AGENT_PERSONAS',
    'XIAOZHI_ARCHITECTURE',
    'XIAOZHI_DIAGNOSTIC_MARKERS',
    'XIAOZHI_LEARNING_PATH_CANDIDATE_FIELD',
    'XIAOZHI_MASTER_AGENT_ID',
    'XIAOZHI_MENTIONABLE_AGENTS',
    'XIAOZHI_RESOURCE_CREATION_MARKERS',
    'XIAOZHI_RESOURCE_LABELS',
    'XIAOZHI_RESOURCE_ROUTES',
    'XIAOZHI_TASK_COMMAND_MARKERS',
    '_activity_datetime',
    '_agent_runtime_allowed_host',
    '_agent_runtime_root',
    '_fail_resource_task_admission',
    '_generated_video_cover_mime_type',
    '_json_copy',
    '_learning_path_config_write_lock',
    '_llm_content_text',
    '_llm_json_contract_errors',
    '_llm_prompt_parts',
    '_orchestration_json',
    '_orchestration_output_json',
    '_persist_xiaozhi_reviewed_learning_path_candidate',
    '_resource_agent_route',
    '_resource_agent_topic',
    '_safe_progress',
    '_schedule_profile_learning_path_generation',
    '_schedule_profile_portrait_generation',
    '_upsert_generated_video_cover',
    '_xiaozhi_first_marker_position',
    '_xiaozhi_run_resource_task',
    '_xiaozhi_runtime_setting_overrides',
    'active_profile_for_user',
    'app',
    'auth_db',
    'call_llm_json',
    'create_profile_version',
    'datetime',
    'effect_assessment_snapshot',
    'evaluate_ppt_resource',
    'evaluate_question_bank_resource',
    'execute_generated_video_task',
    'find_herb_model',
    'g',
    'generate_background_chat',
    'generate_generated_video_cover',
    'generate_learning_animation',
    'generate_learning_document',
    'generate_learning_path',
    'generate_learning_path_stage_detail',
    'generate_learning_tutor',
    'generate_personalized_resources',
    'generate_ppt_h5',
    'generate_profile_report',
    'generate_question_bank',
    'generate_resource_workflow',
    'get_setting',
    'json',
    'json_loads_safe',
    'jsonify',
    'knowledge_growth',
    'learning_evidence_for_user',
    'learning_path_config_is_degraded',
    'learning_path_profile_report_id',
    'list_history',
    'llm_runtime_for_user',
    'media_file',
    'merge_xiaozhi_effect_assessment',
    'normalize_learning_path_config',
    'normalize_mcu_resource_params',
    'normalize_mcu_route',
    'normalize_resource_agent_type',
    'now_iso',
    'parse_qsl',
    'private_knowledge_service',
    'profile_state_for_user',
    'public_herb_model_catalog',
    'public_llm_error',
    'quote',
    're',
    'read_learning_path_config',
    'record_learning_feedback',
    'request_llm_text',
    'resolve_mcu_agent_params_for_user',
    'resolve_model_routing',
    'retrieve_course_knowledge',
    'run_xiaozhi_hermes_agent',
    'save_learning_document',
    'save_question_sheet',
    'secrets',
    'select_learning_path_herb',
    'setting_default',
    'setting_overrides',
    'sqlite3',
    'start_interview_session',
    'time',
    'update_profile_report',
    'urlencode',
    'urlparse',
    'urlunparse',
    'write_learning_path_config',
    'xiaozhi_active_profile_with_evidence',
    'xiaozhi_append_task_conversation',
    'xiaozhi_build_profile_payload',
    'xiaozhi_build_question_payload',
    'xiaozhi_create_task',
    'xiaozhi_detect_requested_resource_types',
    'xiaozhi_distribute_question_type_counts',
    'xiaozhi_effect_assessment_result',
    'xiaozhi_execute_profile_management',
    'xiaozhi_extract_explicit_topic',
    'xiaozhi_fallback_intent',
    'xiaozhi_generate_generated_video_cover',
    'xiaozhi_has_explicit_task_command',
    'xiaozhi_insert_event',
    'xiaozhi_is_diagnostic_query',
    'xiaozhi_latest_context',
    'xiaozhi_learning_feedback_fields',
    'xiaozhi_normalize_skill_output',
    'xiaozhi_persist_orchestration',
    'xiaozhi_private_knowledge_command',
    'xiaozhi_profile_text',
    'xiaozhi_profile_with_evidence',
    'xiaozhi_public_target_agent',
    'xiaozhi_resolve_learning_path_stage',
    'xiaozhi_route_with_task',
    'xiaozhi_run_orchestrated',
    'xiaozhi_run_platform_agent',
    'xiaozhi_run_resource_task',
    'xiaozhi_runtime_setting_overrides',
    'xiaozhi_runtime_settings_for_user',
    'xiaozhi_smart_tutor_result',
    'xiaozhi_task_from_row',
    'xiaozhi_update_task',
)
EXPORTED_FUNCTIONS = (
    'xiaozhi_public_target_agent',
    'xiaozhi_parse_agent_mention',
    'xiaozhi_agent_chat_reply',
    '_xiaozhi_first_marker_position',
    'xiaozhi_is_diagnostic_query',
    'xiaozhi_has_explicit_task_command',
    'normalize_resource_agent_type',
    'xiaozhi_detect_requested_resource_types',
    '_resource_agent_topic',
    '_resource_agent_route',
    'xiaozhi_route_with_task',
    'json_loads_safe',
    'xiaozhi_current_user',
    'xiaozhi_insert_event',
    '_activity_datetime',
    'record_learning_activity_pulse',
    'xiaozhi_insert_message',
    'xiaozhi_profile_agent_context',
    'xiaozhi_append_task_conversation',
    'xiaozhi_create_task',
    'xiaozhi_task_from_row',
    'xiaozhi_update_task',
    '_generated_video_cover_mime_type',
    '_upsert_generated_video_cover',
    'xiaozhi_generate_generated_video_cover',
    '_queue_waiting_generated_video_covers_after_restart',
    '_fail_resource_task_admission',
    'xiaozhi_create_resource_agent_task',
    'xiaozhi_latest_context',
    'xiaozhi_runtime_settings_for_user',
    '_agent_runtime_allowed_host',
    'validate_xiaozhi_runtime_settings',
    '_agent_runtime_root',
    '_xiaozhi_runtime_setting_overrides',
    'test_xiaozhi_runtime_connection',
    'xiaozhi_runtime_setting_overrides',
    '_llm_content_text',
    '_llm_prompt_parts',
    'llm_runtime_for_user',
    'public_llm_error',
    '_llm_json_contract_errors',
    'run_user_llm_completion',
    '_orchestration_json',
    '_orchestration_output_json',
    'xiaozhi_persist_orchestration',
    'xiaozhi_recent_orchestration_runs',
    'xiaozhi_normalize_skill_output',
    'xiaozhi_run_orchestrated',
    'xiaozhi_generate_question_bank_managed',
    'xiaozhi_generate_ppt_managed',
    'xiaozhi_smart_tutor_result',
    'xiaozhi_effect_assessment_result',
    'merge_xiaozhi_effect_assessment',
    'xiaozhi_private_knowledge_command',
    'xiaozhi_learning_feedback_fields',
    'xiaozhi_fallback_intent',
    'xiaozhi_extract_explicit_topic',
    'xiaozhi_detect_intent',
    'xiaozhi_build_card',
    'xiaozhi_feedback_target',
    'xiaozhi_smart_tutor_request',
    'xiaozhi_build_profile_payload',
    'xiaozhi_profile_text',
    'xiaozhi_profile_with_evidence',
    'xiaozhi_active_profile_with_evidence',
    'xiaozhi_build_question_payload',
    'xiaozhi_distribute_question_type_counts',
    'xiaozhi_resolve_learning_path_stage',
    'xiaozhi_run_platform_agent',
    '_persist_xiaozhi_reviewed_learning_path_candidate',
    'xiaozhi_run_resource_task',
    '_xiaozhi_run_resource_task',
)

def xiaozhi_public_target_agent(agent: dict | None = None) -> dict:
    resolved = agent or XIAOZHI_MENTIONABLE_AGENTS[0]
    return {
        "id": str(resolved.get("id") or XIAOZHI_MASTER_AGENT_ID),
        "name": str(resolved.get("name") or "岐小智"),
        "taskType": str(resolved.get("taskType") or ""),
        "actionable": True,
    }


def xiaozhi_parse_agent_mention(message: str) -> tuple[dict, str, bool]:
    text = str(message or "").strip()
    match = re.search(r"(^|\s)@([^\s，,：:]+)", text)
    if not match:
        return xiaozhi_public_target_agent(), text, False
    requested_name = str(match.group(2) or "").strip()
    normalized = requested_name.casefold()
    for agent in XIAOZHI_MENTIONABLE_AGENTS:
        names = [str(agent.get("name") or ""), *(agent.get("aliases") or [])]
        if normalized not in {name.casefold() for name in names if name}:
            continue
        clean_message = (text[:match.start()] + " " + text[match.end():]).strip()
        return xiaozhi_public_target_agent(agent), clean_message, True
    return xiaozhi_public_target_agent(), text, False


def xiaozhi_agent_chat_reply(
    user_id: int,
    target_agent: dict,
    message: str,
    context: dict,
    runtime_settings: dict[str, str] | None = None,
) -> str:
    agent_id = str(target_agent.get("id") or XIAOZHI_MASTER_AGENT_ID)
    agent_name = str(target_agent.get("name") or "岐小智")
    role = XIAOZHI_AGENT_PERSONAS.get(agent_id)
    if not role:
        raise RuntimeError(f"{agent_name}尚未配置专家对话角色")

    knowledge_context = ""
    citation_labels: list[str] = []
    try:
        retrieved = retrieve_course_knowledge(
            message,
            top_k=5,
            max_context_chars=6000,
            user_id=int(user_id),
            db_path=AUTH_DB_PATH,
        )
        knowledge_context = str(retrieved.get("context") or "").strip()
        citation_labels = [
            str(item.get("label") or item.get("id") or "").strip()
            for item in (retrieved.get("citations") or [])
            if isinstance(item, dict) and str(item.get("label") or item.get("id") or "").strip()
        ][:8]
    except Exception as exc:
        app.logger.warning("agent chat knowledge retrieval failed for %s: %s", agent_id, exc)

    active_profile = context.get("profile") if isinstance(context.get("profile"), dict) else {}
    recent_messages = context.get("recentMessages") if isinstance(context.get("recentMessages"), list) else []
    system = f"""
你是岐黄智境多智能体群聊中的“{agent_name}”。
你的唯一职责：{role}

要求：
1. 以该专家身份直接回答当前问题，不冒充岐小智，也不声称已经创建或完成任何任务。
2. 只有用户明确要求生成、创建、规划、搜索、评估或执行时，平台才会另行创建任务；本次是专家交流。
3. 回答使用简体中文，清楚、具体、简洁。需要用户补充信息时，只问最关键的问题。
4. 中医药事实优先依据提供的混合知识库内容；证据不足时明确说“当前知识库证据不足”，不要编造。
5. 不提供替代临床诊断或处方的结论。
""".strip()
    prompt = f"""
用户问题：
{message}

当前学习画像摘要：
{json.dumps(active_profile, ensure_ascii=False)[:3500] or "尚无激活画像"}

当前画像最近群聊：
{json.dumps(recent_messages[-6:], ensure_ascii=False)[:3000] or "暂无"}

混合知识库检索结果：
{knowledge_context[:6000] or "未检索到直接相关片段"}

可引用证据编号：{", ".join(citation_labels) or "无"}
""".strip()
    with setting_overrides(runtime_settings):
        reply = request_llm_text(
            system,
            prompt,
            max_tokens=1800,
            timeout=90,
            json_mode=False,
            allow_anthropic_fallback=False,
        )
    reply = str(reply or "").strip()
    if not reply:
        raise RuntimeError(f"{agent_name}未返回有效内容")
    return reply


def _xiaozhi_first_marker_position(text: str, markers: tuple[str, ...]) -> int:
    positions = [text.find(marker) for marker in markers if marker in text]
    return min(positions) if positions else -1


def xiaozhi_is_diagnostic_query(message: str) -> bool:
    text = str(message or "").lower()
    diagnostic_at = _xiaozhi_first_marker_position(text, XIAOZHI_DIAGNOSTIC_MARKERS)
    if diagnostic_at < 0:
        return False
    action_at = _xiaozhi_first_marker_position(text, XIAOZHI_RESOURCE_CREATION_MARKERS)
    return action_at < 0 or diagnostic_at <= action_at


def xiaozhi_has_explicit_task_command(message: str) -> bool:
    text = str(message or "").lower()
    return any(marker in text for marker in XIAOZHI_TASK_COMMAND_MARKERS)


def normalize_resource_agent_type(value: object) -> str:
    raw = str(value or "").strip()
    if raw in RESOURCE_AGENT_TYPE_ALIASES:
        raw = RESOURCE_AGENT_TYPE_ALIASES[raw]
    if raw in RESOURCE_AGENT_ALLOWED_TYPES:
        return raw
    return ""


def xiaozhi_detect_requested_resource_types(message: str) -> list[str]:
    text = str(message or "").lower()
    if xiaozhi_is_diagnostic_query(text):
        return []
    if any(keyword in text for keyword in ["五类资源", "全部资源", "资源包", "个性化资源包"]):
        return ["personalized_resources"]
    requested: list[str] = []
    checks = [
        ("herb_model", ["药材模型", "模型识别", "模型辨识", "药材识别", "药材辨识", "三维药材"]),
        ("generated_video", ["生成视频", "制作视频", "创建视频", "生成讲解视频", "制作讲解视频", "ai视频", "AI视频"]),
        ("document", ["课程讲义", "学习讲义", "讲义", "学习文档", "课程文档", "handout"]),
        ("ppt", ["ppt", "课件", "演示文稿"]),
        ("mindmap", ["思维导图", "导图", "mindmap", "mind map"]),
        ("animation", ["动画讲解", "动画微课", "h5动画", "h5 动画", "生成动画", "动态讲解"]),
        ("video", ["视频", "课程视频", "讲解视频", "视频检索"]),
        ("question_bank", ["题库", "练习题", "题单", "试卷", "考试"]),
        ("mcu", ["单片机实验", "模拟器", "仿真", "mcu", "实验资源"]),
    ]
    for task_type, keywords in checks:
        if any(keyword in text for keyword in keywords):
            requested.append(task_type)
    if "generated_video" in requested:
        requested = [item for item in requested if item != "video"]
    if "animation" in requested:
        requested = [item for item in requested if item != "video"]
    return list(dict.fromkeys(requested))


def _resource_agent_topic(topic: object, params: dict | None = None) -> str:
    params = params if isinstance(params, dict) else {}
    candidates = [
        topic,
        params.get("topic"),
        params.get("chapter"),
        params.get("keyword"),
        params.get("course"),
        params.get("title"),
    ]
    for candidate in candidates:
        text = str(candidate or "").strip()
        if text:
            return text[:80]
    return "中医学习资源"


def _resource_agent_route(task_type: str, topic: str, params: dict | None = None) -> str:
    params = params if isinstance(params, dict) else {}
    context_params = {
        key: params.get(key)
        for key in ["source", "stageId", "nodeId", "cacheKey", "profileReportId"]
        if params.get(key) is not None and str(params.get(key)).strip()
    }

    def query(route: str, values: dict) -> str:
        cleaned = {
            key: value
            for key, value in values.items()
            if value is not None and str(value).strip() != ""
        }
        if not cleaned:
            return route
        separator = "&" if "?" in route else "?"
        return f"{route}{separator}{urlencode(cleaned, doseq=True)}"

    if task_type == "question_bank":
        course = str(params.get("course") or params.get("courseName") or "中医系统").strip()
        chapter = str(params.get("chapter") or params.get("chapterName") or params.get("targetTopic") or topic).strip()
        count = params.get("count") or params.get("questionCount") or params.get("question_count") or 8
        return query(
            "/personalized-resources/question-bank",
            {"module": "generate", "course": course, "chapter": chapter, "count": count, "autostart": "1", **context_params},
        )
    if task_type == "ppt":
        page_count = params.get("pageCount") or params.get("pages") or params.get("page_count") or 6
        prompt = str(params.get("prompt") or params.get("userMessage") or topic).strip()
        session_id = str(params.get("sessionId") or "").strip()
        if session_id:
            return query(
                f"/ppt-generator/generating/{quote(session_id, safe='')}",
                {"topic": topic, "prompt": prompt, "pageCount": page_count, **context_params},
            )
        return query(
            "/personalized-resources/ppt",
            {"topic": topic, "prompt": prompt, "pageCount": page_count, "autostart": "1", **context_params},
        )
    if task_type == "document":
        requirements = str(params.get("requirements") or params.get("prompt") or "").strip()
        return query(
            "/personalized-resources/document",
            {"topic": topic, "requirements": requirements, "autostart": "1", **context_params},
        )
    if task_type == "mindmap":
        keyword = str(params.get("keyword") or topic).strip()
        return query("/personalized-resources/mind-map", {"topic": topic, "keyword": keyword, "autostart": "1", **context_params})
    if task_type == "video":
        keyword = str(params.get("keyword") or topic).strip()
        return query("/personalized-resources/video-search", {"keyword": keyword, "topic": topic, "autostart": "1", **context_params})
    if task_type == "generated_video":
        prompt = str(params.get("prompt") or topic).strip()
        return query("/personalized-resources/video-generator", {"topic": topic, "prompt": prompt, **context_params})
    if task_type == "animation":
        requirements = str(params.get("requirements") or params.get("prompt") or "").strip()
        return query(
            "/personalized-resources/animation",
            {"topic": topic, "requirements": requirements, "autostart": "1", **context_params},
        )
    if task_type == "herb_model":
        return query(
            "/personalized-resources/herb-model",
            {
                "herb": params.get("herbId") or "",
                "mode": params.get("challengeMode") or "identify",
                **context_params,
            },
        )
    if task_type == "mcu":
        params = normalize_mcu_resource_params(params, topic)
        board = str(params["board"])
        project_id = str(params["projectId"])
        return query(f"/personalized-resources/mcu-simulator/{quote(board)}/{quote(project_id)}", context_params)
    if task_type == "knowledge_base":
        return query(
            "/personalized-resources/knowledge-base",
            {
                "action": params.get("action") or params.get("knowledgeAction") or "",
                **context_params,
            },
        )
    return XIAOZHI_RESOURCE_ROUTES.get(task_type, "/personalized-resources")


def xiaozhi_route_with_task(route: str, task_id: str) -> str:
    route = str(route or "/personalized-resources")
    task_id = str(task_id or "")
    if not task_id:
        return route
    parsed = urlparse(route)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.pop("autostart", None)
    query["xzTask"] = task_id
    return urlunparse(parsed._replace(query=urlencode(query)))


def json_loads_safe(value, default):
    try:
        if value is None or value == "":
            return default
        return json.loads(value)
    except Exception:
        return default


def xiaozhi_current_user():
    user = g.get("current_user")
    if not user:
        return None, (jsonify({"code": 401, "msg": "请先登录"}), 401)
    return user, None


def xiaozhi_insert_event(user_id: int, event_type: str, route: str = "", title: str = "", payload=None) -> None:
    payload = payload if isinstance(payload, dict) else {}
    with auth_db() as conn:
        conn.execute(
            """
            INSERT INTO xiaozhi_events (user_id, event_type, route, title, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, event_type, route, title, json.dumps(payload, ensure_ascii=False), now_iso()),
        )


def _activity_datetime(value: object) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def record_learning_activity_pulse(conn: sqlite3.Connection, user_id: int, payload: dict) -> dict:
    session_id = str(payload.get("sessionId") or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,96}", session_id):
        raise ValueError("学习会话 ID 无效")
    action = str(payload.get("action") or "heartbeat").strip().lower()
    if action not in {"start", "heartbeat", "end"}:
        raise ValueError("学习会话动作无效")
    route = str(payload.get("route") or "")[:500]
    route_name = str(payload.get("routeName") or "")[:120]
    timestamp = now_iso()
    row = conn.execute(
        """
        SELECT id, last_seen_at, active_seconds, status, started_at, ended_at
        FROM learning_activity_sessions
        WHERE user_id = ? AND session_id = ?
        """,
        (int(user_id), session_id),
    ).fetchone()

    if row is None:
        status = "ended" if action == "end" else "active"
        cursor = conn.execute(
            """
            INSERT INTO learning_activity_sessions
                (session_id, user_id, route, route_name, started_at, last_seen_at,
                 active_seconds, status, ended_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
            ON CONFLICT(user_id, session_id) DO NOTHING
            """,
            (
                session_id,
                int(user_id),
                route,
                route_name,
                timestamp,
                timestamp,
                status,
                timestamp if status == "ended" else "",
                timestamp,
                timestamp,
            ),
        )
        if cursor.rowcount:
            return {
                "sessionId": session_id,
                "status": status,
                "activeSeconds": 0,
                "addedSeconds": 0,
                "route": route,
                "updatedAt": timestamp,
            }
        row = conn.execute(
            """
            SELECT id, last_seen_at, active_seconds, status, started_at, ended_at
            FROM learning_activity_sessions
            WHERE user_id = ? AND session_id = ?
            """,
            (int(user_id), session_id),
        ).fetchone()
        if row is None:
            raise RuntimeError("学习会话并发写入后无法读取")

    current_seconds = max(0, int(row["active_seconds"] or 0))
    if str(row["status"] or "active") == "ended":
        return {
            "sessionId": session_id,
            "status": "ended",
            "activeSeconds": current_seconds,
            "route": route,
            "updatedAt": str(row["ended_at"] or row["last_seen_at"] or timestamp),
        }

    previous_time = _activity_datetime(row["last_seen_at"])
    current_time = _activity_datetime(timestamp)
    elapsed_seconds = 0
    if action != "start" and previous_time and current_time:
        elapsed_seconds = max(0, min(45, int((current_time - previous_time).total_seconds())))
    active_seconds = current_seconds + elapsed_seconds
    status = "ended" if action == "end" else "active"
    ended_at = timestamp if status == "ended" else ""
    conn.execute(
        """
        UPDATE learning_activity_sessions
        SET route = ?, route_name = ?, last_seen_at = ?, active_seconds = ?,
            status = ?, ended_at = ?, updated_at = ?
        WHERE user_id = ? AND session_id = ?
        """,
        (
            route,
            route_name,
            timestamp,
            active_seconds,
            status,
            ended_at,
            timestamp,
            int(user_id),
            session_id,
        ),
    )
    return {
        "sessionId": session_id,
        "status": status,
        "activeSeconds": active_seconds,
        "addedSeconds": elapsed_seconds,
        "route": route,
        "updatedAt": timestamp,
    }


def xiaozhi_insert_message(
    user_id: int,
    role: str,
    content: str,
    intent=None,
    cards=None,
    *,
    profile_report_id: int = 0,
) -> int:
    with auth_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO xiaozhi_messages
                (user_id, profile_report_id, role, content, intent_json, cards_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                int(profile_report_id or 0),
                role,
                content,
                json.dumps(intent or {}, ensure_ascii=False),
                json.dumps(cards or [], ensure_ascii=False),
                now_iso(),
            ),
        )
        return int(cursor.lastrowid)


def xiaozhi_profile_agent_context(
    user_id: int,
    profile_report_id: int,
    *,
    backfill: bool = True,
) -> dict:
    store = ProfileAgentContextStore(AUTH_DB_PATH)
    conversation = store.context(int(user_id), int(profile_report_id))
    if (
        backfill
        and int(profile_report_id or 0) > 0
        and int(conversation.get("messageCount") or 0) == 0
    ):
        try:
            if store.backfill_from_orchestration(int(user_id), int(profile_report_id)):
                conversation = store.context(int(user_id), int(profile_report_id))
        except Exception as exc:
            app.logger.warning(
                "failed to backfill profile agent conversation user=%s profile=%s: %s",
                user_id,
                profile_report_id,
                exc,
            )
    return conversation


def xiaozhi_append_task_conversation(
    user_id: int,
    task_id: str,
    *,
    profile_report_id: int = 0,
    agent_id: str,
    agent_name: str,
    message_type: str,
    status: str,
    content: str,
    payload: dict | None = None,
    dedupe_suffix: str,
) -> dict | None:
    try:
        resolved_profile_report_id = int(profile_report_id or 0)
        if resolved_profile_report_id <= 0:
            context = xiaozhi_latest_context(int(user_id))
            resolved_profile_report_id = int(
                context.get("profileReportId")
                or (context.get("profile") or {}).get("id")
                or 0
            )
        if resolved_profile_report_id <= 0:
            return None
        details = dict(payload) if isinstance(payload, dict) else {}
        details["taskId"] = str(task_id or "")
        return ProfileAgentContextStore(AUTH_DB_PATH).append(
            int(user_id),
            resolved_profile_report_id,
            agent_id=agent_id,
            agent_name=agent_name,
            message_type=message_type,
            status=status,
            content=content,
            payload=details,
            task_id=str(task_id or ""),
            dedupe_key=f"task:{task_id}:{dedupe_suffix}",
        )
    except Exception as exc:
        app.logger.warning(
            "failed to append task lifecycle to profile group chat task=%s error=%s",
            task_id,
            exc,
        )
        return None


def xiaozhi_create_task(
    user_id: int,
    task_type: str,
    title: str,
    prompt: str,
    route: str,
    profile_report_id: int | None = None,
) -> str:
    task_id = f"xz_{int(time.time() * 1000)}_{secrets.token_hex(4)}"
    timestamp = now_iso()
    route = xiaozhi_route_with_task(route, task_id)
    with auth_db() as conn:
        resolved_profile_report_id = int(profile_report_id or 0)
        if profile_report_id is None:
            active_profile = active_profile_for_user(conn, int(user_id))
            resolved_profile_report_id = int(active_profile.get("id") or 0) if active_profile else 0
        conn.execute(
            """
            INSERT INTO xiaozhi_tasks
                (task_id, user_id, profile_report_id, task_type, title, prompt, status,
                 route, result_json, error, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'queued', ?, '{}', '', ?, ?)
            """,
            (
                task_id,
                user_id,
                resolved_profile_report_id,
                task_type,
                title,
                prompt,
                route,
                timestamp,
                timestamp,
            ),
        )
    return task_id


def xiaozhi_task_from_row(row) -> dict:
    keys = set(row.keys()) if hasattr(row, "keys") else set()
    result = json_loads_safe(row["result_json"], {})
    route = str(row["route"] or "")
    if row["task_type"] == "mcu":
        params = result.get("params") if isinstance(result.get("params"), dict) else {}
        route = normalize_mcu_route(
            route,
            params,
            " ".join([str(row["title"] or ""), str(result.get("topic") or "")]),
        )
    return {
        "taskId": row["task_id"],
        "profileReportId": int(row["profile_report_id"] or 0) if "profile_report_id" in keys else 0,
        "taskType": row["task_type"],
        "title": row["title"],
        "prompt": row["prompt"] if "prompt" in keys else "",
        "status": row["status"],
        "route": route,
        "result": result,
        "error": row["error"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


def xiaozhi_update_task(task_id: str, **fields) -> None:
    allowed = {"status", "route", "result_json", "error"}
    updates = []
    values = []
    for key, value in fields.items():
        if key not in allowed:
            continue
        updates.append(f"{key} = ?")
        if key == "result_json" and not isinstance(value, str):
            value = json.dumps(value or {}, ensure_ascii=False)
        values.append(value)
    updates.append("updated_at = ?")
    values.append(now_iso())
    values.append(task_id)
    with auth_db() as conn:
        conn.execute(f"UPDATE xiaozhi_tasks SET {', '.join(updates)} WHERE task_id = ?", values)


def _generated_video_cover_mime_type(image_bytes: bytes) -> str:
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def _upsert_generated_video_cover(
    conn: sqlite3.Connection,
    task_id: str,
    user_id: int,
    *,
    status: str,
    image_bytes: bytes | None = None,
    mime_type: str = "image/jpeg",
    model: str = "z-image-turbo",
    prompt: str = "",
    error: str = "",
) -> None:
    timestamp = now_iso()
    conn.execute(
        """
        INSERT INTO generated_video_covers
            (task_id, user_id, image_blob, mime_type, model, prompt, status, error, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(task_id) DO UPDATE SET
            user_id = excluded.user_id,
            image_blob = excluded.image_blob,
            mime_type = excluded.mime_type,
            model = excluded.model,
            prompt = excluded.prompt,
            status = excluded.status,
            error = excluded.error,
            updated_at = excluded.updated_at
        """,
        (
            str(task_id),
            int(user_id),
            sqlite3.Binary(image_bytes) if image_bytes else None,
            str(mime_type or "image/jpeg"),
            str(model or "z-image-turbo"),
            str(prompt or ""),
            str(status),
            str(error or "")[:1000],
            timestamp,
            timestamp,
        ),
    )


def xiaozhi_generate_generated_video_cover(
    task_id: str,
    user_id: int,
    topic: str,
    params: dict | None = None,
) -> None:
    """Generate a poster while leaving the full video task in its waiting state."""
    cover_result: dict = {}
    cover_error = ""
    with auth_db() as conn:
        task_row = conn.execute(
            "SELECT 1 FROM xiaozhi_tasks WHERE user_id = ? AND task_id = ? AND task_type = 'generated_video' LIMIT 1",
            (int(user_id), str(task_id)),
        ).fetchone()
        if not task_row:
            return
        _upsert_generated_video_cover(
            conn,
            str(task_id),
            int(user_id),
            status="generating",
        )
    xiaozhi_append_task_conversation(
        int(user_id),
        str(task_id),
        profile_report_id=(params or {}).get("profileReportId") or 0,
        agent_id="generated-video-agent",
        agent_name="AI 视频生成智能体",
        message_type="resource_progress",
        status="running",
        content="正在根据学习任务生成 AI 视频首图封面。",
        payload={
            "resourceType": "generated_video",
            "stage": "cover_generating",
            "progress": 10,
            "route": xiaozhi_route_with_task(
                _resource_agent_route("generated_video", str(topic), params or {}),
                str(task_id),
            ),
        },
        dedupe_suffix="cover:generating",
    )
    try:
        cover_result = generate_generated_video_cover(
            str(task_id),
            int(user_id),
            str(topic),
            params if isinstance(params, dict) else {},
        )
        image_path = Path(str(cover_result.get("imagePath") or media_file(int(user_id), str(task_id), "poster.jpg")))
        image_bytes = image_path.read_bytes() if image_path.is_file() else b""
        if not image_bytes:
            raise RuntimeError("AI 视频封面生成结果为空")
        mime_type = _generated_video_cover_mime_type(image_bytes)
        with auth_db() as conn:
            _upsert_generated_video_cover(
                conn,
                str(task_id),
                int(user_id),
                status="ready",
                image_bytes=image_bytes,
                mime_type=mime_type,
                model=str(cover_result.get("model") or "z-image-turbo"),
                prompt=str(cover_result.get("prompt") or ""),
            )
    except Exception as exc:
        cover_error = str(exc) or "AI 视频封面生成失败"
        with auth_db() as conn:
            _upsert_generated_video_cover(
                conn,
                str(task_id),
                int(user_id),
                status="failed",
                error=cover_error,
                model=str(cover_result.get("model") or "z-image-turbo"),
                prompt=str(cover_result.get("prompt") or ""),
            )

    with auth_db() as conn:
        row = conn.execute(
            "SELECT status, result_json FROM xiaozhi_tasks WHERE user_id = ? AND task_id = ? LIMIT 1",
            (int(user_id), str(task_id)),
        ).fetchone()
        if not row or str(row["status"] or "") not in {"waiting", "waiting_for_user"}:
            return
        current = json_loads_safe(row["result_json"], {})
        if not isinstance(current, dict):
            current = {}
        selected = current.get("selectedResource") if isinstance(current.get("selectedResource"), dict) else {}
        content = selected.get("content") if isinstance(selected.get("content"), dict) else {}
        metadata = selected.get("metadata") if isinstance(selected.get("metadata"), dict) else {}
        if cover_error:
            current.update({"coverStatus": "failed", "coverError": cover_error})
            metadata.update({"coverStatus": "failed"})
        else:
            poster_url = str(cover_result.get("posterUrl") or "")
            current.update({"coverStatus": "complete", "coverError": ""})
            content.update({"posterUrl": poster_url})
            metadata.update({"coverStatus": "complete", "posterUrl": poster_url})
        if selected:
            selected.update({"content": content, "metadata": metadata})
            current["selectedResource"] = selected
        conn.execute(
            """
            UPDATE xiaozhi_tasks
            SET result_json = ?, updated_at = ?
            WHERE user_id = ? AND task_id = ? AND status IN ('waiting', 'waiting_for_user')
            """,
            (
                json.dumps(current, ensure_ascii=False),
                now_iso(),
                int(user_id),
                str(task_id),
            ),
        )
    if cover_error:
        xiaozhi_append_task_conversation(
            int(user_id),
            str(task_id),
            profile_report_id=(params or {}).get("profileReportId") or 0,
            agent_id="generated-video-agent",
            agent_name="AI 视频生成智能体",
            message_type="resource_failed",
            status="failed",
            content=f"AI 视频首图封面生成失败：{cover_error}",
            payload={
                "resourceType": "generated_video",
                "stage": "cover_failed",
                "progress": 100,
                "error": cover_error,
            },
            dedupe_suffix="cover:failed",
        )
    else:
        xiaozhi_append_task_conversation(
            int(user_id),
            str(task_id),
            profile_report_id=(params or {}).get("profileReportId") or 0,
            agent_id="generated-video-agent",
            agent_name="AI 视频生成智能体",
            message_type="resource_ready",
            status="waiting",
            content="AI 视频首图封面已生成，完整视频等待用户手动确认。",
            payload={
                "resourceType": "generated_video",
                "stage": "waiting_for_user",
                "progress": 20,
                "route": xiaozhi_route_with_task(
                    _resource_agent_route("generated_video", str(topic), params or {}),
                    str(task_id),
                ),
                "posterUrl": str(cover_result.get("posterUrl") or ""),
            },
            dedupe_suffix="cover:ready",
        )


def _queue_waiting_generated_video_covers_after_restart() -> int:
    """Backfill cover-only jobs for persisted videos still awaiting confirmation."""
    pending: list[tuple[str, int, str, dict]] = []
    with auth_db() as conn:
        rows = conn.execute(
            """
            SELECT task.task_id, task.user_id, task.title, task.prompt, task.route,
                   task.result_json
            FROM xiaozhi_tasks AS task
            LEFT JOIN generated_video_covers AS cover ON cover.task_id = task.task_id
            WHERE task.task_type = 'generated_video'
              AND task.status IN ('waiting', 'waiting_for_user')
              AND (cover.status IS NULL OR cover.status != 'ready' OR cover.image_blob IS NULL)
            ORDER BY task.id
            """
        ).fetchall()
        for row in rows:
            task_id = str(row["task_id"])
            user_id = int(row["user_id"])
            current = json_loads_safe(row["result_json"], {})
            if not isinstance(current, dict):
                current = {}
            params = current.get("params") if isinstance(current.get("params"), dict) else {}
            topic = str(current.get("topic") or row["prompt"] or row["title"] or "中医药学习视频").strip()
            poster_url = f"/api/personalized-resources/generated-videos/{task_id}/poster"
            selected = current.get("selectedResource") if isinstance(current.get("selectedResource"), dict) else {}
            content = selected.get("content") if isinstance(selected.get("content"), dict) else {}
            metadata = selected.get("metadata") if isinstance(selected.get("metadata"), dict) else {}
            content.update({"posterUrl": poster_url, "videoUrl": str(content.get("videoUrl") or "")})
            metadata.update({
                "taskId": task_id,
                "generationState": "waiting_for_user",
                "coverStatus": "queued",
                "posterUrl": poster_url,
            })
            selected.update({
                "id": str(selected.get("id") or f"generated-video:{task_id}"),
                "type": "generated_video",
                "title": str(selected.get("title") or topic),
                "description": str(selected.get("description") or "首图封面自动生成，完整视频仅在手动确认后开始生成。"),
                "route": str(selected.get("route") or row["route"] or ""),
                "content": content,
                "metadata": metadata,
            })
            current.update({
                "message": "AI 视频首图正在生成；完整视频需在工作台手动确认后生成。",
                "topic": topic,
                "resourceType": "generated_video",
                "params": params,
                "currentStage": "waiting_for_user",
                "coverStatus": "queued",
                "coverError": "",
                "selectedResource": selected,
            })
            conn.execute(
                "UPDATE xiaozhi_tasks SET result_json = ?, updated_at = ? WHERE task_id = ?",
                (json.dumps(current, ensure_ascii=False), now_iso(), task_id),
            )
            _upsert_generated_video_cover(conn, task_id, user_id, status="queued")
            pending.append((task_id, user_id, topic, dict(params)))

    submitted = 0
    for task_id, user_id, topic, params in pending:
        try:
            VIDEO_RESOURCE_EXECUTOR.submit(
                xiaozhi_generate_generated_video_cover,
                task_id,
                user_id,
                topic,
                params,
            )
            submitted += 1
        except QueueCapacityError:
            app.logger.warning("video cover recovery queue full after %s submissions", submitted)
            break
    return submitted


def _fail_resource_task_admission(task: dict, initial_result: dict, executor_name: str) -> dict:
    message = "当前生成任务较多，请稍后重新提交"
    failed_result = {
        **initial_result,
        "message": message,
        "currentStage": "queue_full",
        "errorCode": "RESOURCE_QUEUE_FULL",
    }
    xiaozhi_update_task(
        str(task["taskId"]),
        status="failed",
        result_json=failed_result,
        error=message,
    )
    task.update({"status": "failed", "result": failed_result, "error": message})
    app.logger.warning(
        "resource task rejected because queue is full task=%s executor=%s",
        task["taskId"],
        executor_name,
    )
    return task


def xiaozhi_create_resource_agent_task(
    user_id: int,
    task_type: str,
    topic: str,
    params: dict | None = None,
    *,
    title: str = "",
    prompt: str = "",
) -> dict:
    params = dict(params) if isinstance(params, dict) else {}
    normalized_type = normalize_resource_agent_type(task_type)
    if not normalized_type:
        raise ValueError("unsupported resource agent type")
    task_topic = _resource_agent_topic(topic, params)
    if normalized_type == "mcu":
        params = resolve_mcu_agent_params_for_user(int(user_id), params, task_topic)
        task_topic = _resource_agent_topic(topic, params)
    if normalized_type == "herb_model":
        herb = find_herb_model(params.get("herbId"))
        if herb is None:
            herb = select_learning_path_herb(
                params.get("profileReportId") or 0,
                params.get("stageId") or "resource-library",
                params.get("nodeId") or secrets.token_hex(4),
            )
        params.update(
            {
                "herbId": herb["id"],
                "herbName": herb["name"],
                "challengeMode": "identify",
            }
        )
        task_topic = f"{herb['name']}药材模型辨识"
    task_title = str(title or f"{task_topic[:32]} · {XIAOZHI_RESOURCE_LABELS.get(normalized_type, '学习资源智能体')}")
    task_prompt = str(prompt or task_topic).strip()
    request_fingerprint = RESOURCE_TASK_ADMISSION.fingerprint(
        normalized_type,
        task_topic,
        task_prompt,
        params,
    )
    with RESOURCE_TASK_ADMISSION.creation_scope():
        is_learning_path_dispatch = str(params.get("source") or "") == "learning-path"
        if not is_learning_path_dispatch:
            active_row = RESOURCE_TASK_ADMISSION.find_active_row(
                auth_db,
                user_id=int(user_id),
                task_type=normalized_type,
                fingerprint=request_fingerprint,
                title=task_title,
                prompt=task_prompt,
                profile_report_id=int(params.get("profileReportId") or 0),
            )
            if active_row:
                active_task = xiaozhi_task_from_row(active_row)
                active_task["reused"] = True
                return active_task
        if normalized_type == "ppt" and not str(params.get("sessionId") or "").strip():
            cache_seed = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(params.get("cacheKey") or "").strip())[:96]
            params["sessionId"] = (
                f"ppt_{cache_seed}"
                if cache_seed
                else f"ppt_{int(time.time() * 1000)}_{secrets.token_hex(3)}"
            )
        route_to = _resource_agent_route(normalized_type, task_topic, params)
        task_id = xiaozhi_create_task(user_id, normalized_type, task_title, task_prompt, route_to)
    if normalized_type == "generated_video":
        params["deferred"] = True
        params.setdefault("prompt", task_prompt)
    timestamp = now_iso()
    initial_result = {
        "message": "资源智能体任务已创建，等待后台执行",
        "topic": task_topic,
        "resourceType": normalized_type,
        "params": params,
        "progress": 0,
        "requestFingerprint": request_fingerprint,
    }
    if normalized_type == "generated_video":
        poster_url = f"/api/personalized-resources/generated-videos/{task_id}/poster"
        initial_result.update(
            {
                "message": "AI 视频首图正在生成；完整视频需在工作台手动确认后生成。",
                "currentStage": "waiting_for_user",
                "coverStatus": "queued",
                "selectedResource": {
                    "id": f"generated-video:{task_id}",
                    "type": "generated_video",
                    "title": task_topic,
                    "description": "首图封面自动生成，完整视频仅在手动确认后开始生成。",
                    "route": xiaozhi_route_with_task(route_to, task_id),
                    "content": {
                        "posterUrl": poster_url,
                        "videoUrl": "",
                    },
                    "metadata": {
                        "taskId": task_id,
                        "generationState": "waiting_for_user",
                        "coverStatus": "queued",
                        "posterUrl": poster_url,
                        "profileReportId": params.get("profileReportId") or 0,
                    },
                },
            }
        )
    if normalized_type == "ppt":
        try:
            page_count = max(1, min(20, int(params.get("pageCount") or params.get("pages") or params.get("page_count") or 6)))
        except (TypeError, ValueError):
            page_count = 6
        session_id = str(params.get("sessionId") or "").strip()
        prompt_text = str(params.get("prompt") or params.get("userMessage") or task_prompt or task_topic).strip()
        task_route = xiaozhi_route_with_task(route_to, task_id)
        initial_result.update(
            {
                "message": "PPT生成智能体已接收参数，后台生成任务即将启动",
                "sessionId": session_id,
                "ohmyPptSessionId": session_id,
                "pageCount": page_count,
                "route": task_route,
                "engine": "ohmyppt-fastapi",
                "currentStage": "queued",
                "ppt": {
                    "status": "queued",
                    "sessionId": session_id,
                    "title": task_topic,
                    "topic": task_topic,
                    "pageCount": page_count,
                    "prompt": prompt_text,
                    "route": task_route,
                    "engine": {"id": "ohmyppt-fastapi"},
                    "pages": [],
                },
            }
        )
    xiaozhi_update_task(task_id, status="queued", result_json=initial_result)
    task = {
        "taskId": task_id,
        "taskType": normalized_type,
        "title": task_title,
        "prompt": task_prompt,
        "status": "queued",
        "route": xiaozhi_route_with_task(route_to, task_id),
        "result": initial_result,
        "error": "",
        "createdAt": timestamp,
        "updatedAt": timestamp,
    }
    xiaozhi_insert_event(
        user_id,
        "resource_agent_task_created",
        task["route"],
        task_title,
        {"taskId": task_id, "taskType": normalized_type, "topic": task_topic, "params": params},
    )
    if normalized_type == "herb_model":
        public_herb = next(
            item for item in public_herb_model_catalog() if item["id"] == params["herbId"]
        )
        completed_result = {
            **initial_result,
            "message": f"资源路由智能体已抽取{public_herb['name']}，药材模型辨识入口可直接学习。",
            "progress": 100,
            "route": task["route"],
            "selectedResource": {
                "id": f"herb-model:{public_herb['id']}",
                "type": "herb_model",
                "title": f"{public_herb['name']}药材模型辨识",
                "description": f"旋转观察{public_herb['name']}模型，通过性状要点完成辨识。",
                "route": task["route"],
                "content": public_herb,
                "metadata": {
                    "herbId": public_herb["id"],
                    "catalogRevision": HERB_MODEL_REVISION,
                    "selectionSource": "learning-path-resource-router-agent",
                    "profileReportId": params.get("profileReportId") or 0,
                },
            },
            "qualityEvaluation": {
                "passed": True,
                "score": 100,
                "reviewType": "curated-model-catalog",
            },
        }
        xiaozhi_update_task(task_id, status="complete", result_json=completed_result, route=task["route"])
        task.update({"status": "complete", "result": completed_result})
        return task
    executor = (
        VIDEO_RESOURCE_EXECUTOR
        if normalized_type == "generated_video"
        else (PPT_RESOURCE_EXECUTOR if normalized_type == "ppt" else RESOURCE_AGENT_EXECUTOR)
    )
    if normalized_type == "generated_video":
        xiaozhi_update_task(task_id, status="waiting", result_json=initial_result)
        task["status"] = "waiting"
        task["result"] = initial_result
        try:
            executor.submit(
                xiaozhi_generate_generated_video_cover,
                task_id,
                int(user_id),
                task_topic,
                params,
            )
        except QueueCapacityError as exc:
            return _fail_resource_task_admission(task, initial_result, exc.executor_name)
        return task
    try:
        executor.submit(
            xiaozhi_run_resource_task,
            task_id,
            user_id,
            normalized_type,
            task_topic,
            params,
        )
    except QueueCapacityError as exc:
        return _fail_resource_task_admission(task, initial_result, exc.executor_name)
    return task


def xiaozhi_latest_context(user_id: int, memory_query: str = "") -> dict:
    with auth_db() as conn:
        profile = active_profile_for_user(conn, int(user_id))
        active_profile_report_id = int(profile.get("id") or 0) if profile else 0
        profile_state = profile_state_for_user(conn, int(user_id))
        questionnaire_row = conn.execute(
            "SELECT questionnaire_data, created_at FROM learning_profile_questionnaires WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        experiments = conn.execute(
            """
            SELECT experiment_name, passed, weak_points, run_data, created_at
            FROM mcu_experiments WHERE user_id = ? ORDER BY id DESC LIMIT 8
            """,
            (user_id,),
        ).fetchall()
        events = conn.execute(
            """
            SELECT event_type, route, title, payload_json, created_at
            FROM xiaozhi_events WHERE user_id = ? ORDER BY id DESC LIMIT 20
            """,
            (user_id,),
        ).fetchall()
        if active_profile_report_id > 0:
            messages = conn.execute(
                """
                SELECT
                    CASE message.message_type
                        WHEN 'user_message' THEN 'user'
                        ELSE 'assistant'
                    END AS role,
                    message.content,
                    message.created_at
                FROM profile_agent_messages AS message
                JOIN profile_agent_conversations AS conversation
                  ON conversation.id = message.conversation_id
                WHERE conversation.user_id = ?
                  AND conversation.profile_report_id = ?
                  AND message.compacted = 0
                  AND message.message_type IN ('user_message', 'supervisor_reply')
                ORDER BY message.sequence DESC
                LIMIT 8
                """,
                (user_id, active_profile_report_id),
            ).fetchall()
            tasks = conn.execute(
                """
                SELECT task_id, task_type, title, status, route, result_json, error, created_at, updated_at
                FROM xiaozhi_tasks
                WHERE user_id = ? AND profile_report_id = ?
                ORDER BY id DESC LIMIT 10
                """,
                (user_id, active_profile_report_id),
            ).fetchall()
        else:
            messages = []
            tasks = []
        private_knowledge = private_knowledge_service.list_knowledge_collections(conn, int(user_id))
        learning_evidence = learning_evidence_for_user(conn, int(user_id))
        long_term_memories = knowledge_growth.relevant_memory_context(
            conn,
            int(user_id),
            memory_query,
            limit=10,
        )
    try:
        question_history = list_history(user_id)
    except Exception:
        question_history = {"question_sheets": [], "exam_results": []}

    return {
        "profile": profile,
        "profileReportId": int(profile.get("id") or 0) if profile else 0,
        "profileName": str(profile.get("profileName") or "") if profile else "",
        "profileVersion": int(profile.get("version") or 0) if profile else 0,
        "profileCreatedAt": str(profile.get("createdAt") or profile.get("timestamp") or "") if profile else "",
        "profileState": profile_state,
        "learningEvidence": learning_evidence,
        "longTermMemories": long_term_memories,
        "questionnaire": json_loads_safe(questionnaire_row["questionnaire_data"], {}) if questionnaire_row else {},
        "questionnaireCreatedAt": questionnaire_row["created_at"] if questionnaire_row else "",
        "mcuExperiments": [
            {
                "name": row["experiment_name"],
                "passed": bool(row["passed"]),
                "weakPoints": json_loads_safe(row["weak_points"], []),
                "createdAt": row["created_at"],
            }
            for row in experiments
        ],
        "recentEvents": [
            {
                "eventType": row["event_type"],
                "route": row["route"],
                "title": row["title"],
                "payload": json_loads_safe(row["payload_json"], {}),
                "createdAt": row["created_at"],
            }
            for row in events
        ],
        "recentMessages": [dict(row) for row in reversed(messages)],
        "recentTasks": [xiaozhi_task_from_row(row) for row in tasks],
        "questionSheets": [
            {
                "title": row.get("title"),
                "courseName": row.get("course_name"),
                "targetTopic": row.get("target_topic"),
                "questionCount": row.get("question_count"),
                "createdAt": row.get("created_at"),
            }
            for row in (question_history.get("question_sheets") or [])[:8]
        ],
        "examResults": [
            {
                "title": row.get("title"),
                "score": row.get("score"),
                "totalScore": row.get("total_score"),
                "correctCount": row.get("correct_count"),
                "questionCount": row.get("question_count"),
                "createdAt": row.get("created_at"),
            }
            for row in (question_history.get("exam_results") or [])[:8]
        ],
        "privateKnowledge": {
            "activeCollectionId": private_knowledge.get("activeCollectionId"),
            "stats": private_knowledge.get("stats") or {},
            "collections": [
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "isActive": item.get("isActive"),
                    "documentCount": item.get("documentCount"),
                    "chunkCount": item.get("chunkCount"),
                }
                for item in (private_knowledge.get("collections") or [])[:8]
            ],
        },
    }


def xiaozhi_runtime_settings_for_user(user_id: int) -> dict:
    with auth_db() as conn:
        row = conn.execute(
            """
            SELECT enabled, protocol, base_url, model, created_at, updated_at
            FROM user_agent_runtime_settings
            WHERE user_id = ?
            """,
            (int(user_id),),
        ).fetchone()
    if row:
        return {
            "enabled": bool(row["enabled"]),
            "protocol": row["protocol"] or "openai",
            "baseUrl": row["base_url"] or "",
            "model": row["model"] or DEFAULT_TEXT_MODEL_ID,
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
            "source": "user",
        }
    return {
        "enabled": False,
        "protocol": "openai",
        "baseUrl": get_setting("OPENAI_BASE_URL", setting_default("OPENAI_BASE_URL")),
        "model": get_setting("ANTHROPIC_MODEL", setting_default("ANTHROPIC_MODEL")) or DEFAULT_TEXT_MODEL_ID,
        "createdAt": "",
        "updatedAt": "",
        "source": "platform-default",
    }


def _agent_runtime_allowed_host(hostname: str) -> bool:
    configured = get_setting(
        "AGENT_RUNTIME_ALLOWED_HOSTS",
        "maas-coding-api.cn-huabei-1.xf-yun.com,localhost,127.0.0.1",
    )
    allowed_hosts = [item.strip().lower() for item in configured.split(",") if item.strip()]
    host = str(hostname or "").lower()
    return any(host == allowed or host.endswith(f".{allowed}") for allowed in allowed_hosts)


def validate_xiaozhi_runtime_settings(payload: dict) -> dict:
    enabled = bool(payload.get("enabled"))
    protocol = str(payload.get("protocol") or "openai").strip().lower()
    if protocol not in {"openai", "anthropic"}:
        raise ValueError("调用协议只能是讯飞 OpenAI 兼容接口或讯飞 Anthropic 兼容接口")
    base_url = str(payload.get("baseUrl") or payload.get("base_url") or "").strip().rstrip("/")
    model = str(payload.get("model") or DEFAULT_TEXT_MODEL_ID).strip()
    if not re.fullmatch(r"[A-Za-z0-9._:/-]{1,100}", model):
        raise ValueError("模型名只能包含字母、数字、点、下划线、斜杠、冒号和中划线")
    if enabled:
        parsed = urlparse(base_url)
        if parsed.scheme not in {"https", "http"} or not parsed.hostname:
            raise ValueError("请输入有效的 HTTP 或 HTTPS API 地址")
        if parsed.username or parsed.password or parsed.fragment:
            raise ValueError("API 地址不能包含账号、密码或 URL 片段")
        if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1"}:
            raise ValueError("非本地 API 地址必须使用 HTTPS")
        if not _agent_runtime_allowed_host(parsed.hostname):
            raise ValueError(f"当前地址域名不在安全白名单中：{parsed.hostname}")
    return {
        "enabled": enabled,
        "protocol": protocol,
        "baseUrl": base_url,
        "model": model,
    }


def _agent_runtime_root(base_url: str) -> str:
    value = str(base_url or "").strip().rstrip("/")
    for suffix in [
        "/v1/chat/completions",
        "/v2/chat/completions",
        "/chat/completions",
        "/anthropic/v1/messages",
        "/anthropic/messages",
        "/anthropic",
        "/v1/messages",
        "/messages",
        "/v2",
        "/v1",
    ]:
        if value.lower().endswith(suffix):
            return value[: -len(suffix)].rstrip("/")
    return value


def _xiaozhi_runtime_setting_overrides(settings: dict) -> dict[str, str]:
    if not settings.get("enabled"):
        return {}
    protocol = str(settings.get("protocol") or "openai")
    base_url = str(settings.get("baseUrl") or "")
    model = str(settings.get("model") or DEFAULT_TEXT_MODEL_ID)
    root = _agent_runtime_root(base_url)
    is_xfyun = "maas-coding-api.cn-huabei-1.xf-yun.com" in root
    return {
        "LLM_PROTOCOL": protocol,
        "OPENAI_BASE_URL": base_url if protocol == "openai" else (f"{root}/v2" if is_xfyun else f"{root}/v1"),
        "ANTHROPIC_BASE_URL": base_url if protocol == "anthropic" else (f"{root}/anthropic" if is_xfyun else root),
        "ANTHROPIC_MODEL": model,
    }


def test_xiaozhi_runtime_connection(settings: dict, *, timeout: int = 25) -> dict:
    started = time.perf_counter()
    with setting_overrides(_xiaozhi_runtime_setting_overrides(settings)):
        result = call_llm_json(
            "你是智能体运行配置测试助手，只输出 JSON。",
            '请返回 {"ok":true,"message":"连接成功"}。',
            max_tokens=800,
            repair=False,
            timeout=timeout,
        )
    if result.get("ok") is False:
        raise RuntimeError(str(result.get("message") or "模型未确认连接成功"))
    return {
        "ok": True,
        "message": str(result.get("message") or "连接成功"),
        "protocol": settings["protocol"] if settings.get("enabled") else "platform-default",
        "model": settings["model"] if settings.get("enabled") else get_setting("ANTHROPIC_MODEL"),
        "elapsedMs": round((time.perf_counter() - started) * 1000),
    }


def xiaozhi_runtime_setting_overrides(user_id: int) -> dict[str, str]:
    settings = xiaozhi_runtime_settings_for_user(int(user_id))
    if not settings.get("enabled"):
        return {}
    protocol = settings["protocol"]
    base_url = settings["baseUrl"]
    model = settings["model"]
    root = _agent_runtime_root(base_url)
    is_xfyun = "maas-coding-api.cn-huabei-1.xf-yun.com" in root
    if protocol == "openai":
        openai_base = base_url
        anthropic_base = f"{root}/anthropic" if is_xfyun else root
    else:
        anthropic_base = base_url
        openai_base = f"{root}/v2" if is_xfyun else f"{root}/v1"
    return {
        "LLM_PROTOCOL": protocol,
        "OPENAI_BASE_URL": openai_base,
        "ANTHROPIC_BASE_URL": anthropic_base,
        "ANTHROPIC_MODEL": model,
        "HERMES_AGENT_API_URL": "",
        "HERMES_AGENT_BASE_URL": base_url,
        "HERMES_AGENT_MODEL": model,
    }


def _llm_content_text(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = [_llm_content_text(item) for item in content]
        return "\n".join(part for part in parts if part).strip()
    if isinstance(content, dict):
        for key in ("text", "content", "value"):
            if key in content:
                return _llm_content_text(content.get(key))
        return ""
    if content is None:
        return ""
    return str(content).strip()


def _llm_prompt_parts(payload: dict) -> tuple[str, str]:
    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        raise ValueError("messages 必须是非空数组")
    if len(messages) > 40:
        raise ValueError("单次最多提交 40 条消息")

    system_parts: list[str] = []
    payload_system = _llm_content_text(payload.get("system"))
    if payload_system:
        system_parts.append(payload_system)
    dialogue_parts: list[str] = []
    role_labels = {"user": "用户", "assistant": "助手", "tool": "工具"}
    total_chars = 0
    context_window = int(resolve_model_routing().get("contextWindow") or 262144)
    max_input_chars = max(120000, min(1000000, context_window * 3))
    for message in messages:
        if not isinstance(message, dict):
            raise ValueError("每条消息必须是对象")
        role = str(message.get("role") or "user").strip().lower()
        if role not in {"system", "user", "assistant", "tool"}:
            raise ValueError(f"不支持的消息角色：{role}")
        content = _llm_content_text(message.get("content"))
        if not content:
            continue
        total_chars += len(content)
        if total_chars > max_input_chars:
            raise ValueError(
                f"消息内容过长，请缩短后重试（当前文本模型上下文上限 {context_window} tokens）"
            )
        if role == "system":
            system_parts.append(content)
        else:
            dialogue_parts.append(f"{role_labels[role]}：\n{content}")
    if not dialogue_parts:
        raise ValueError("至少需要一条非空用户消息")
    system = "\n\n".join(system_parts).strip() or "你是中药鉴别的学习资源生成助手。"
    prompt = "\n\n".join(dialogue_parts).strip()
    return system, prompt


def llm_runtime_for_user(user_id: int) -> dict:
    settings = xiaozhi_runtime_settings_for_user(int(user_id))
    overrides = xiaozhi_runtime_setting_overrides(int(user_id))
    runtime = resolve_model_routing(overrides)
    runtime["customized"] = bool(settings.get("enabled"))
    runtime["source"] = settings.get("source") or (
        "user" if settings.get("enabled") else "platform-default"
    )
    return runtime


def public_llm_error(error: Exception) -> str:
    message = str(error or "模型调用失败")
    for setting_name in ("ANTHROPIC_AUTH_TOKEN", "MIMO_API_KEY", "XIAOMI_API_KEY"):
        secret = get_setting(setting_name, "")
        if secret:
            message = message.replace(secret, "***")
    return message[:1200] or "模型调用失败"


def _llm_json_contract_errors(parsed: dict, response_format: dict, required_fields: list[str]) -> list[str]:
    errors = []
    for field in required_fields:
        value = parsed.get(field)
        empty_collection_is_valid = field == "commands"
        if (
            field not in parsed
            or value is None
            or value == ""
            or (not empty_collection_is_valid and value in ([], {}))
        ):
            errors.append(f"缺少非空字段 {field}")
    schema = str(response_format.get("schema") or "").strip().lower()
    if schema == "mindmap_markdown":
        markdown = parsed.get("markdown")
        if not isinstance(markdown, str):
            errors.append("markdown 必须是字符串")
            return errors
        cleaned = markdown.strip()
        if not re.search(r"(?m)^#\s+\S+", cleaned):
            errors.append("markdown 必须包含一个一级标题")
        branch_count = len(re.findall(r"(?m)^##\s+\S+", cleaned))
        if branch_count < 3:
            errors.append(f"markdown 至少需要 3 个二级分支，当前只有 {branch_count} 个")
        if len(cleaned) < 120:
            errors.append(f"markdown 内容过短，当前只有 {len(cleaned)} 个字符")
    elif schema == "mindmap_edit_commands":
        if not isinstance(parsed.get("message"), str) or not parsed.get("message", "").strip():
            errors.append("message 必须是非空字符串")
        commands = parsed.get("commands")
        if not isinstance(commands, list):
            errors.append("commands 必须是数组")
            return errors
        allowed_actions = {"add", "update", "delete", "update-settings", "contact-team"}
        for index, command in enumerate(commands[:100]):
            if not isinstance(command, dict):
                errors.append(f"commands[{index}] 必须是对象")
                continue
            action = str(command.get("action") or "").strip()
            if action not in allowed_actions:
                errors.append(f"commands[{index}].action 不受支持")
                continue
            if action in {"add", "update", "delete"} and not str(command.get("id") or "").strip():
                errors.append(f"commands[{index}] 缺少节点 id")
            if action in {"add", "update", "update-settings", "contact-team"} and not isinstance(command.get("data"), dict):
                errors.append(f"commands[{index}].data 必须是对象")
    return errors


def run_user_llm_completion(user_id: int, payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("请求体必须是 JSON 对象")
    system, prompt = _llm_prompt_parts(payload)
    try:
        max_tokens = int(payload.get("max_tokens") or payload.get("max_completion_tokens") or 2200)
    except (TypeError, ValueError):
        raise ValueError("max_tokens 必须是整数") from None
    max_tokens = max(LLM_RESPONSE_TOKEN_BUDGET, min(131072, max_tokens))
    try:
        timeout = int(payload.get("timeout") or 90)
    except (TypeError, ValueError):
        raise ValueError("timeout 必须是整数") from None
    timeout = max(10, min(120, timeout))
    response_format = payload.get("response_format") or payload.get("responseFormat") or {}
    json_mode = isinstance(response_format, dict) and response_format.get("type") == "json_object"
    required_fields: list[str] = []
    if json_mode and isinstance(response_format.get("required"), list):
        for field in response_format["required"][:12]:
            normalized = str(field or "").strip()
            if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", normalized):
                required_fields.append(normalized)
    overrides = xiaozhi_runtime_setting_overrides(int(user_id))
    runtime = llm_runtime_for_user(int(user_id))
    with setting_overrides(overrides):
        if json_mode:
            parsed = call_llm_json(system, prompt, max_tokens=max_tokens, repair=True, timeout=timeout)
            contract_errors = _llm_json_contract_errors(parsed, response_format, required_fields)
            if contract_errors:
                repair_prompt = f"""
原始任务：
{prompt}

上一次返回虽然是 JSON，但不符合输出契约：
{json.dumps(contract_errors, ensure_ascii=False)}

上一次返回：{json.dumps(parsed, ensure_ascii=False)[:12000]}

请重新完成原始任务，只输出一个合法 JSON 对象，确保以下字段都存在且内容非空：
{json.dumps(required_fields, ensure_ascii=False)}
若契约是思维导图，markdown 必须以一级标题开头，至少包含 3 行以 ## 开头的二级分支，
每个分支应有具体知识节点，markdown 总长度不得少于 120 个字符。
"""
                if str(response_format.get("schema") or "").strip().lower() == "mindmap_edit_commands":
                    repair_prompt += """
若契约是思维导图编辑，message 必须是非空字符串，commands 必须是数组；
commands 中每项只能使用 add、update、delete、update-settings、contact-team，
涉及节点的命令必须包含有效 id，需要修改内容的命令必须包含 data 对象。
"""
                parsed = call_llm_json(
                    f"{system}\n你正在修复不符合字段契约的 JSON 输出。",
                    repair_prompt,
                    max_tokens=max_tokens,
                    repair=True,
                    timeout=timeout,
                )
                contract_errors = _llm_json_contract_errors(parsed, response_format, required_fields)
                if contract_errors:
                    raise RuntimeError(f"模型 JSON 不符合输出契约：{'; '.join(contract_errors)}")
            content = json.dumps(parsed, ensure_ascii=False)
        else:
            content = request_llm_text(
                system,
                prompt,
                max_tokens=max_tokens,
                timeout=timeout,
                json_mode=False,
            )
    if not str(content or "").strip():
        raise RuntimeError("模型返回了空内容")
    return {
        "id": f"chatcmpl-{secrets.token_hex(12)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": runtime["model"],
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": str(content).strip()},
                "finish_reason": "stop",
            }
        ],
        "usage": {},
        "modelRuntime": runtime,
    }


def _orchestration_json(value, max_chars: int = 240000) -> str:
    try:
        text = json.dumps(value if value is not None else {}, ensure_ascii=False, default=str)
    except Exception:
        text = json.dumps({"value": str(value)}, ensure_ascii=False)
    if len(text) <= max_chars:
        return text
    return json.dumps(
        {
            "truncated": True,
            "originalChars": len(text),
            "preview": text[:max_chars],
        },
        ensure_ascii=False,
    )


def _orchestration_output_json(result: dict, max_chars: int = 240000) -> str:
    try:
        text = json.dumps(result, ensure_ascii=False, default=str)
    except Exception:
        return _orchestration_json(result, max_chars)
    if len(text) <= max_chars:
        return text

    trace = result.get("orchestration") if isinstance(result.get("orchestration"), dict) else {}
    compact_trace = dict(trace)
    compact_trace["handoffs"] = [
        {key: value for key, value in item.items() if key != "payload"}
        for item in trace.get("handoffs") or []
        if isinstance(item, dict)
    ]
    compact_trace["events"] = [
        {key: value for key, value in item.items() if key != "payload"}
        for item in trace.get("events") or []
        if isinstance(item, dict)
    ]
    compact_result = {
        "truncated": True,
        "originalChars": len(text),
        "orchestration": compact_trace,
        "harness": result.get("harness") if isinstance(result.get("harness"), dict) else {},
    }
    return _orchestration_json(compact_result, max_chars)


def xiaozhi_persist_orchestration(
    user_id: int,
    result: dict,
    *,
    task_type: str,
    topic: str,
    payload: dict | None = None,
    task_id: str = "",
) -> None:
    if int(user_id or 0) <= 0 or not isinstance(result, dict):
        return
    trace = result.get("orchestration")
    if not isinstance(trace, dict) or not trace.get("runId"):
        return
    run_id = str(trace["runId"])
    created_at = str((trace.get("events") or [{}])[0].get("time") or now_iso())
    updated_at = now_iso()
    review = trace.get("review") if isinstance(trace.get("review"), dict) else {}
    feedback = trace.get("feedback") if isinstance(trace.get("feedback"), dict) else {}
    harness = result.get("harness") if isinstance(result.get("harness"), dict) else {}
    skill = harness.get("skill") if isinstance(harness.get("skill"), dict) else {}
    mcp = harness.get("mcp") if isinstance(harness.get("mcp"), dict) else {}
    policy = harness.get("policy") if isinstance(harness.get("policy"), dict) else {}
    profile_report_id = int(
        harness.get("profileReportId")
        or trace.get("profileReportId")
        or (payload or {}).get("_profileReportId")
        or 0
    )
    with auth_db() as conn:
        conn.execute(
            """
            INSERT INTO agent_orchestration_runs
                (run_id, task_id, user_id, root_agent, task_type, topic, status, architecture,
                 harness_name, harness_version, skill_id, mcp_server, mcp_tool, policy_json,
                 profile_report_id, input_json, output_json, review_json, feedback_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                task_id = excluded.task_id,
                status = excluded.status,
                architecture = excluded.architecture,
                harness_name = excluded.harness_name,
                harness_version = excluded.harness_version,
                skill_id = excluded.skill_id,
                mcp_server = excluded.mcp_server,
                mcp_tool = excluded.mcp_tool,
                policy_json = excluded.policy_json,
                profile_report_id = excluded.profile_report_id,
                output_json = excluded.output_json,
                review_json = excluded.review_json,
                feedback_json = excluded.feedback_json,
                updated_at = excluded.updated_at
            """,
            (
                run_id,
                str(task_id or trace.get("taskId") or ""),
                int(user_id),
                str(trace.get("rootAgent") or XIAOZHI_MASTER_AGENT_ID),
                str(task_type or trace.get("taskType") or ""),
                str(topic or trace.get("topic") or "")[:240],
                str(trace.get("status") or "complete"),
                str(trace.get("architecture") or XIAOZHI_ARCHITECTURE),
                str(harness.get("name") or ""),
                str(harness.get("version") or ""),
                str(skill.get("id") or ""),
                str(skill.get("mcpServer") or ""),
                str(skill.get("mcpTool") or ""),
                _orchestration_json(policy),
                profile_report_id,
                _orchestration_json(payload or {}),
                _orchestration_output_json(result),
                _orchestration_json(review),
                _orchestration_json(feedback),
                created_at,
                updated_at,
            ),
        )
        conn.execute("DELETE FROM agent_orchestration_handoffs WHERE run_id = ?", (run_id,))
        conn.execute("DELETE FROM agent_orchestration_events WHERE run_id = ?", (run_id,))
        for handoff in trace.get("handoffs") or []:
            if not isinstance(handoff, dict):
                continue
            conn.execute(
                """
                INSERT INTO agent_orchestration_handoffs
                    (run_id, sequence, from_agent, to_agent, artifact_type, summary, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    int(handoff.get("sequence") or 0),
                    str(handoff.get("fromAgent") or ""),
                    str(handoff.get("toAgent") or ""),
                    str(handoff.get("artifactType") or ""),
                    str(handoff.get("summary") or "")[:500],
                    _orchestration_json(handoff.get("payload") or {}, 40000),
                    str(handoff.get("time") or updated_at),
                ),
            )
        for event in trace.get("events") or []:
            if not isinstance(event, dict):
                continue
            conn.execute(
                """
                INSERT INTO agent_orchestration_events
                    (run_id, sequence, agent_id, stage, status, message, progress, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    int(event.get("sequence") or 0),
                    str(event.get("agentId") or ""),
                    str(event.get("stage") or ""),
                    str(event.get("status") or ""),
                    str(event.get("message") or "")[:1000],
                    _safe_progress(event.get("progress"), 0),
                    _orchestration_json(event.get("payload") or {}, 40000),
                    str(event.get("time") or updated_at),
                ),
            )


def xiaozhi_recent_orchestration_runs(
    user_id: int,
    limit: int = 12,
    task_id: str = "",
    profile_report_id: int | None = None,
) -> list[dict]:
    limit = max(1, min(50, int(limit or 12)))
    where = "WHERE user_id = ?"
    values: list = [int(user_id)]
    if task_id:
        where += " AND task_id = ?"
        values.append(str(task_id))
    if profile_report_id is not None:
        where += " AND profile_report_id = ?"
        values.append(int(profile_report_id or 0))
    values.append(limit)
    with auth_db() as conn:
        rows = conn.execute(
            f"""
            SELECT run_id, task_id, root_agent, task_type, topic, status, architecture,
                   harness_name, harness_version, skill_id, mcp_server, mcp_tool, policy_json,
                   profile_report_id, output_json, review_json, feedback_json, created_at, updated_at,
                   (SELECT COUNT(*) FROM agent_orchestration_handoffs h WHERE h.run_id = r.run_id) AS handoff_count,
                   (SELECT COUNT(*) FROM agent_orchestration_events e WHERE e.run_id = r.run_id) AS event_count
            FROM agent_orchestration_runs r
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            values,
        ).fetchall()
    runs = []
    for row in rows:
        output = json_loads_safe(row["output_json"], {})
        trace = output.get("orchestration") if isinstance(output, dict) else {}
        trace_handoffs = trace.get("handoffs") if isinstance(trace, dict) else []
        trace_events = trace.get("events") if isinstance(trace, dict) else []
        runs.append(
            {
                "runId": row["run_id"],
                "taskId": row["task_id"],
                "rootAgent": row["root_agent"],
                "taskType": row["task_type"],
                "topic": row["topic"],
                "profileReportId": int(row["profile_report_id"] or 0),
                "status": row["status"],
                "architecture": row["architecture"],
                "harness": {
                    "name": row["harness_name"],
                    "version": row["harness_version"],
                    "skillId": row["skill_id"],
                    "mcpServer": row["mcp_server"],
                    "mcpTool": row["mcp_tool"],
                    "policy": json_loads_safe(row["policy_json"], {}),
                },
                "review": json_loads_safe(row["review_json"], {}),
                "feedback": json_loads_safe(row["feedback_json"], {}),
                "agentRuns": trace.get("agentRuns") if isinstance(trace, dict) else [],
                "handoffs": [
                    {
                        "sequence": int(item.get("sequence") or index + 1),
                        "time": str(item.get("time") or ""),
                        "fromAgent": str(item.get("fromAgent") or ""),
                        "fromAgentName": str(item.get("fromAgentName") or ""),
                        "toAgent": str(item.get("toAgent") or ""),
                        "toAgentName": str(item.get("toAgentName") or ""),
                        "artifactType": str(item.get("artifactType") or ""),
                        "summary": str(item.get("summary") or "")[:300],
                    }
                    for index, item in enumerate(trace_handoffs or [])
                    if isinstance(item, dict)
                ],
                "events": [
                    {
                        "sequence": int(item.get("sequence") or index + 1),
                        "time": str(item.get("time") or ""),
                        "agentId": str(item.get("agentId") or ""),
                        "agentName": str(item.get("agentName") or ""),
                        "stage": str(item.get("stage") or ""),
                        "status": str(item.get("status") or ""),
                        "message": str(item.get("message") or "")[:300],
                        "progress": _safe_progress(item.get("progress"), 0),
                    }
                    for index, item in enumerate(trace_events or [])
                    if isinstance(item, dict)
                ],
                "handoffCount": row["handoff_count"],
                "eventCount": row["event_count"],
                "createdAt": row["created_at"],
                "updatedAt": row["updated_at"],
            }
        )
    return runs


def xiaozhi_normalize_skill_output(task_type: str, topic: str, output) -> dict:
    """Preserve domain fields while adding the manifest-declared Skill envelope."""

    raw = dict(output) if isinstance(output, dict) else {"result": output}
    normalized = dict(raw)
    message = next(
        (
            str(raw.get(key) or "").strip()
            for key in ("message", "reply", "answer", "summary", "question")
            if str(raw.get(key) or "").strip()
        ),
        "",
    )
    normalized["message"] = message or f"{str(topic or '学习任务').strip()}已完成。"

    if task_type == "learning_background":
        normalized.setdefault("dialogue", raw)
    elif task_type == "profile_update":
        normalized.setdefault(
            "report",
            raw if isinstance(raw.get("aiAnalysis"), dict) else {"aiAnalysis": raw},
        )
    elif task_type == "profile_management":
        normalized.setdefault("profileManagement", raw)
    elif task_type == "learning_path":
        normalized.setdefault("learningPath", raw)
    elif task_type == "learning_path_stage":
        normalized.setdefault("stageDetail", raw)
    elif task_type == "personalized_resources":
        normalized.setdefault("workflow", raw)
    elif task_type == "question_bank":
        normalized.setdefault("questionGenerator", raw)
    elif task_type == "ppt":
        normalized.setdefault("ppt", raw)
    elif task_type in {"mindmap", "video", "mcu"}:
        workflow = raw.get("workflow") if isinstance(raw.get("workflow"), dict) else raw
        normalized.setdefault("workflow", workflow)
        resources = workflow.get("resources") if isinstance(workflow.get("resources"), list) else []
        aliases = {"mindmap": "mindmap", "video": "video", "mcu": "simulator"}
        selected = next(
            (
                item
                for item in resources
                if isinstance(item, dict) and str(item.get("type") or "") == aliases[task_type]
            ),
            {},
        )
        normalized.setdefault("selectedResource", selected)
    elif task_type == "interview":
        normalized.setdefault("interview", raw)
    elif task_type == "smart_tutor":
        normalized.setdefault("tutor", raw)
        normalized.setdefault("answer", str(raw.get("answer") or raw.get("explanation") or "").strip())
    elif task_type == "effect_assessment":
        normalized.setdefault("assessment", raw)
    elif task_type == "learning_feedback":
        normalized.setdefault("feedback", raw)
    elif task_type == "knowledge_base":
        normalized.setdefault("knowledgeBase", raw)

    return normalized


def xiaozhi_run_orchestrated(
    task_type: str,
    topic: str,
    payload: dict,
    user_id: int,
    specialist_handler,
    *,
    context: dict | None = None,
    task_id: str = "",
    on_event=None,
    max_retries: int = 0,
) -> dict:
    managed_payload = dict(payload or {})
    managed_payload["_xiaozhi_managed"] = True
    platform_context = dict(
        context if isinstance(context, dict) else xiaozhi_latest_context(int(user_id))
    )
    with auth_db() as conn:
        platform_context["longTermMemories"] = knowledge_growth.relevant_memory_context(
            conn,
            int(user_id),
            f"{topic} {task_type}",
            limit=10,
        )
    profile_report_id = int(
        platform_context.get("profileReportId")
        or (platform_context.get("profile") or {}).get("id")
        or 0
    )
    managed_payload["_profileReportId"] = profile_report_id
    profile_context_store = ProfileAgentContextStore(AUTH_DB_PATH)
    if profile_report_id > 0:
        try:
            platform_context["agentConversation"] = profile_context_store.context(
                int(user_id),
                profile_report_id,
            )
        except Exception as exc:
            app.logger.warning(
                "[ProfileAgentContext] load failed user=%s profile=%s error=%s",
                user_id,
                profile_report_id,
                exc,
            )

    def shared_conversation_event(event: dict) -> None:
        if profile_report_id > 0 and isinstance(event, dict):
            try:
                profile_context_store.append_event(
                    int(user_id),
                    profile_report_id,
                    event,
                    task_id=task_id,
                )
            except Exception as exc:
                app.logger.warning(
                    "[ProfileAgentContext] append event failed user=%s profile=%s error=%s",
                    user_id,
                    profile_report_id,
                    exc,
                )
        if callable(on_event):
            on_event(event)

    def contract_specialist(arguments: dict, progress) -> dict:
        return xiaozhi_normalize_skill_output(
            task_type,
            topic,
            specialist_handler(arguments, progress),
        )

    result = DEFAULT_AGENT_HARNESS.run(
        task_type,
        topic,
        managed_payload,
        platform_context,
        contract_specialist,
        user_id=int(user_id),
        task_id=task_id,
        on_event=shared_conversation_event,
        max_retries=max_retries,
        runtime_settings=xiaozhi_runtime_setting_overrides(int(user_id)),
    )
    if isinstance(result.get("harness"), dict):
        result["harness"]["profileReportId"] = profile_report_id
    if isinstance(result.get("orchestration"), dict):
        result["orchestration"]["profileReportId"] = profile_report_id
    xiaozhi_persist_orchestration(
        int(user_id),
        result,
        task_type=task_type,
        topic=topic,
        payload=managed_payload,
        task_id=task_id,
    )
    if profile_report_id > 0:
        try:
            profile_context_store.record_trace(
                int(user_id),
                profile_report_id,
                result,
                task_id=task_id,
            )
            conversation_context = profile_context_store.context(
                int(user_id),
                profile_report_id,
            )
            result["agentConversation"] = conversation_context
            if isinstance(result.get("harness"), dict):
                result["harness"]["sharedConversation"] = {
                    "conversationId": conversation_context.get("conversationId"),
                    "profileReportId": profile_report_id,
                    "messageCount": conversation_context.get("messageCount"),
                    "summaryVersion": conversation_context.get("summaryVersion"),
                    "automaticCompaction": True,
                }
            if isinstance(result.get("orchestration"), dict):
                result["orchestration"]["conversationId"] = conversation_context.get("conversationId")
        except Exception as exc:
            app.logger.warning(
                "[ProfileAgentContext] finalize failed user=%s profile=%s error=%s",
                user_id,
                profile_report_id,
                exc,
            )
    trace = result.get("orchestration") if isinstance(result.get("orchestration"), dict) else {}
    if str(trace.get("status") or "") != "complete":
        raise SkillReviewError(result)
    return result


def xiaozhi_generate_question_bank_managed(
    qg_payload: dict,
    user_id: int,
    *,
    task_id: str = "",
    on_delta=None,
    on_stage=None,
) -> dict:
    topic = str(qg_payload.get("target_topic") or qg_payload.get("course_name") or "中医题库").strip()

    def specialist(managed_payload: dict, progress) -> dict:
        def stage_bridge(event: dict):
            progress(event)
            if callable(on_stage):
                on_stage(event)

        generated = generate_question_bank(managed_payload, on_delta=on_delta, on_stage=stage_bridge)
        question_bank = generated.get("question_bank") if isinstance(generated.get("question_bank"), dict) else {}
        knowledge_sources = generated.get("knowledgeSources") if isinstance(generated.get("knowledgeSources"), list) else []
        if not knowledge_sources and isinstance(question_bank.get("knowledge_sources"), list):
            knowledge_sources = question_bank["knowledge_sources"]
        generated["qualityEvaluation"] = evaluate_question_bank_resource(
            question_bank,
            expected_count=int(
                managed_payload.get("question_count")
                or len(question_bank.get("questions") or [])
                or 1
            ),
            citations=knowledge_sources,
        )
        return generated

    return xiaozhi_run_orchestrated(
        "question_bank",
        topic,
        qg_payload,
        user_id,
        specialist,
        task_id=task_id,
        max_retries=0,
    )


def xiaozhi_generate_ppt_managed(
    payload: dict,
    user_id: int,
    *,
    task_id: str = "",
    on_event=None,
) -> dict:
    topic = str(payload.get("topic") or "中医学习课件").strip()

    def specialist(managed_payload: dict, progress) -> dict:
        generated = generate_ppt_h5(managed_payload, on_stage=progress)
        knowledge_sources = generated.get("knowledgeSources") if isinstance(generated.get("knowledgeSources"), list) else []
        generated["qualityEvaluation"] = evaluate_ppt_resource(
            generated,
            expected_page_count=int(managed_payload.get("pageCount") or len(generated.get("pages") or []) or 1),
            citations=knowledge_sources,
        )
        return generated

    return xiaozhi_run_orchestrated(
        "ppt",
        topic,
        payload,
        user_id,
        specialist,
        task_id=task_id,
        on_event=on_event,
        max_retries=1,
    )


def xiaozhi_smart_tutor_result(payload: dict) -> dict:
    return generate_learning_tutor(payload)


def xiaozhi_effect_assessment_result(payload: dict) -> dict:
    system = """
你是嵌小智调度的学习效果评估子智能体。
根据答题、考试、医案练习、面试和资源使用证据做诊断，禁止凭空编造数据。
只输出 JSON，字段为 scores、summary、strengths、weaknesses、recommendations、adjustments、evidenceUsed。
"""
    prompt = f"""
本次评估请求：{json.dumps(payload, ensure_ascii=False)[:12000]}
请给出多维度分数、证据化总结，以及对学习画像和学习路径的动态调整建议。
"""
    result = call_llm_json(system, prompt, max_tokens=3000)
    result.setdefault("agent", "learning-effect-assessment-agent")
    result.setdefault("source", "llm")
    return result


def merge_xiaozhi_effect_assessment(snapshot: dict, narrative: dict | None = None) -> dict:
    """Keep evidence-derived metrics authoritative while retaining the LLM diagnosis."""
    snapshot = dict(snapshot) if isinstance(snapshot, dict) else {}
    narrative = dict(narrative) if isinstance(narrative, dict) else {}
    plan = snapshot.get("pathAdjustmentPlan") if isinstance(snapshot.get("pathAdjustmentPlan"), dict) else {}
    plan_tasks = plan.get("tasks") if isinstance(plan.get("tasks"), list) else []
    recommendations = narrative.get("recommendations") if isinstance(narrative.get("recommendations"), list) else []
    if not recommendations:
        recommendations = [
            str(item.get("acceptanceCriteria") or "").strip()
            for item in plan_tasks
            if isinstance(item, dict) and str(item.get("acceptanceCriteria") or "").strip()
        ]
    adjustments = narrative.get("adjustments") if isinstance(narrative.get("adjustments"), list) else []
    if not adjustments and plan.get("reason"):
        adjustments = [str(plan["reason"])]
    scores = dict(narrative.get("scores")) if isinstance(narrative.get("scores"), dict) else {}
    scores.update(
        {
            "achievementRate": snapshot.get("achievementRate"),
            "masteryRate": snapshot.get("masteryRate"),
            "radarScores": snapshot.get("radarScores") or [],
        }
    )
    return {
        **narrative,
        **snapshot,
        "agent": "learning-effect-assessment-agent",
        "source": str(narrative.get("source") or "deterministic-evidence"),
        "summary": str(narrative.get("summary") or snapshot.get("summary") or "学习效果评估已完成。"),
        "strengths": narrative.get("strengths") if isinstance(narrative.get("strengths"), list) else [],
        "weaknesses": narrative.get("weaknesses") if isinstance(narrative.get("weaknesses"), list) else list(snapshot.get("weakPoints") or []),
        "recommendations": recommendations,
        "adjustments": adjustments,
        "scores": scores,
        "narrativeAssessment": narrative,
    }


def xiaozhi_private_knowledge_command(message: object, params: dict | None = None) -> dict:
    params = params if isinstance(params, dict) else {}
    text = str(message or "").strip()
    lowered = text.lower()
    explicit_action = str(params.get("action") or params.get("knowledgeAction") or "").strip().lower()
    action_aliases = {
        "catalog": "list",
        "open": "list",
        "status": "list",
        "create": "create",
        "activate": "activate",
        "switch": "activate",
        "search": "search",
        "retrieve": "search",
        "add_text": "add_text",
    }
    action = action_aliases.get(explicit_action, explicit_action)
    if action not in {"list", "create", "activate", "search", "add_text"}:
        mentions_knowledge = any(word in lowered for word in ["知识库", "资料库"])
        if mentions_knowledge and any(word in lowered for word in ["创建", "新建"]):
            action = "create"
        elif mentions_knowledge and any(word in lowered for word in ["切换", "启用", "设为当前", "使用"]):
            action = "activate"
        elif mentions_knowledge and any(word in lowered for word in ["检索", "搜索", "查询", "查找"]):
            action = "search"
        else:
            action = "list"

    collection_name = str(params.get("collectionName") or params.get("name") or "").strip()
    if not collection_name and action == "create":
        match = re.search(
            r"(?:创建|新建)(?:一个|一份|名为|叫做|叫)?\s*[“\"']?(.{1,40}?)[”\"']?\s*(?:知识库|资料库)",
            text,
            flags=re.I,
        )
        if match:
            collection_name = match.group(1).strip(" ，。,.、\"'“”")
        if collection_name in {"一个", "一份"}:
            collection_name = ""
    if not collection_name and action == "activate":
        match = re.search(
            r"(?:切换到?|启用|使用|设为当前)\s*[“\"']?(.{1,40}?)[”\"']?\s*(?:知识库|资料库)",
            text,
            flags=re.I,
        )
        if match:
            collection_name = match.group(1).strip(" ，。,.、\"'“”")

    query = str(params.get("query") or params.get("topic") or "").strip()
    if not query and action == "search":
        query = re.sub(r"(?:帮我|请|在)?(?:检索|搜索|查询|从)?(?:当前|我的)?(?:知识库|资料库)(?:里|中)?", "", text)
        query = query.strip(" ，。,.、")
    return {
        "action": action,
        "collectionName": collection_name[:80],
        "query": query[:300],
        "content": str(params.get("content") or "")[:200000],
        "filename": str(params.get("filename") or "xiaozhi-note.md")[:180],
    }


def xiaozhi_learning_feedback_fields(message: str) -> dict:
    text = str(message or "").strip().lower()
    if any(marker in text for marker in ["卡住", "阻塞", "无法继续", "做不了"]):
        outcome = "blocked"
    elif any(marker in text for marker in ["需要巩固", "还没掌握", "没看懂", "太难", "再复习", "不熟"]):
        outcome = "needs_review"
    else:
        outcome = "completed"
    difficulty = (
        "hard"
        if any(marker in text for marker in ["太难", "很难", "困难", "吃力", "没看懂"])
        else "easy"
        if any(marker in text for marker in ["很简单", "太简单", "容易"])
        else "appropriate"
    )
    helpful = None
    if any(marker in text for marker in ["没帮助", "无帮助", "没用"]):
        helpful = False
    elif any(marker in text for marker in ["有帮助", "有用", "讲清楚了"]):
        helpful = True
    return {
        "feedbackOutcome": outcome,
        "feedbackDifficulty": difficulty,
        "feedbackHelpful": helpful,
    }


def xiaozhi_fallback_intent(message: str) -> dict:
    text = (message or "").lower()
    if any(word in text for word in ["画像列表", "列出画像", "有哪些画像", "历史画像", "查看画像版本"]):
        return {
            "intent": "profile_management",
            "resourceType": "none",
            "profileAction": "list",
            "targetQuery": "",
            "topic": message,
            "reply": "我来读取你保留的学习画像版本。",
        }
    if any(word in text for word in ["重置画像", "清空当前画像", "重新开始画像", "从头评估"]):
        return {
            "intent": "profile_management",
            "resourceType": "none",
            "profileAction": "reset",
            "targetQuery": message,
            "topic": message,
            "reply": "我会保留历史画像，并清空当前激活状态和采集草稿。",
        }
    if any(word in text for word in ["切换到", "切换画像", "设为当前画像", "使用这个画像", "使用上个月的画像", "换成"]):
        return {
            "intent": "profile_management",
            "resourceType": "none",
            "profileAction": "activate",
            "targetQuery": message,
            "topic": message,
            "reply": "我来查找并切换到你指定的学习画像。",
        }
    if any(word in text for word in ["更新当前画像", "刷新画像", "根据最近考试更新画像", "基于最近", "画像更新"]):
        return {
            "intent": "profile_management",
            "resourceType": "none",
            "profileAction": "refresh",
            "targetQuery": message,
            "topic": message,
            "reply": "我会基于当前画像和最近学习证据更新同一份画像。",
        }
    knowledge_markers = [
        "我的知识库",
        "打开知识库",
        "查看知识库",
        "知识库列表",
        "创建知识库",
        "新建知识库",
        "切换知识库",
        "启用知识库",
        "设为当前知识库",
        "检索知识库",
        "搜索知识库",
        "查询知识库",
    ]
    has_knowledge_action = (
        any(word in text for word in ["知识库", "资料库"])
        and any(word in text for word in ["创建", "新建", "打开", "查看", "列出", "切换", "启用", "设为当前", "检索", "搜索", "查询"])
    )
    if any(word in text for word in knowledge_markers) or has_knowledge_action:
        command = xiaozhi_private_knowledge_command(message)
        replies = {
            "create": "我会调用私有知识库智能体创建知识库。",
            "activate": "我会查找并切换到指定知识库。",
            "search": "我会在当前私有知识库和内置课程资料中联合检索。",
            "list": "我会读取你的私有知识库目录和激活状态。",
        }
        return {
            "intent": "generate_resource",
            "resourceType": "knowledge_base",
            "knowledgeAction": command["action"],
            "collectionName": command["collectionName"],
            "knowledgeQuery": command["query"],
            "topic": message,
            "reply": replies.get(command["action"], replies["list"]),
        }
    feedback_markers = [
        "学完了",
        "已经学完",
        "完成学习",
        "任务完成",
        "需要巩固",
        "还没掌握",
        "学习反馈",
        "资源反馈",
        "这个资源有帮助",
        "这个资源没帮助",
    ]
    if any(marker in text for marker in feedback_markers):
        return {
            "intent": "generate_resource",
            "resourceType": "learning_feedback",
            "topic": message,
            "reply": "我会调用学习反馈智能体，把本次学习结果写入效果评估与路径证据。",
            **xiaozhi_learning_feedback_fields(message),
        }
    if xiaozhi_is_diagnostic_query(message):
        return {
            "intent": "generate_resource",
            "resourceType": "smart_tutor",
            "topic": message,
            "reply": "我会结合你的学习画像、实验记录和课程知识库定位问题，再分步引导你排查。",
        }
    if any(word in text for word in ["个性化资源", "五类资源", "全部资源", "资源包", "推荐资源"]):
        return {"intent": "generate_resource", "resourceType": "personalized_resources", "topic": message, "reply": "我会调用个性化资源工作流，为你准备一组匹配当前画像的资源。"}
    requested_types = xiaozhi_detect_requested_resource_types(message)
    if len(requested_types) > 1:
        labels = "、".join(XIAOZHI_RESOURCE_LABELS.get(item, item) for item in requested_types)
        return {
            "intent": "generate_resource",
            "resourceType": requested_types[0],
            "resourceTypes": requested_types,
            "topic": message,
            "reply": f"我会同时创建 {labels} 任务，每个资源都会在悬浮窗里保留小窗口预览。",
        }
    if any(word in text for word in ["阶段细化", "阶段详情", "阶段任务", "这一阶段"]):
        return {"intent": "generate_resource", "resourceType": "learning_path_stage", "topic": message, "reply": "我会调用阶段细化智能体，把当前阶段拆成目标、资源和检查点。"}
    if any(word in text for word in ["学习路径", "学习计划", "路线", "路径规划", "阶段计划"]):
        return {"intent": "generate_resource", "resourceType": "learning_path", "topic": message, "reply": "我会调用学习路径智能体，为你生成一条可执行的学习路线。"}
    if any(word in text for word in ["面试", "模拟面试", "ai面试", "数字人面试"]):
        return {"intent": "generate_resource", "resourceType": "interview", "topic": message, "reply": "我会启动数字人学习访谈，并生成进入访谈页面的卡片。"}
    if any(word in text for word in ["效果评估", "学习效果", "掌握情况", "评估一下", "学习诊断"]):
        return {"intent": "generate_resource", "resourceType": "effect_assessment", "topic": message, "reply": "我会汇总答题、实验和学习记录，生成学习效果评估与路径调整建议。"}
    if any(word in text for word in ["辅导", "答疑", "不会", "讲解一下", "怎么理解", "为什么"]):
        return {"intent": "generate_resource", "resourceType": "smart_tutor", "topic": message, "reply": "我会结合你的学习画像和课程知识库进行针对性辅导。"}
    if any(word in text for word in ["背景对话", "学习背景", "采集背景", "补充背景"]):
        return {"intent": "generate_resource", "resourceType": "learning_background", "topic": message, "reply": "我会调用学习背景对话智能体，帮你继续补全画像上下文。"}
    if any(word in text for word in ["课程讲义", "学习讲义", "讲义", "学习文档", "课程文档", "handout"]):
        return {"intent": "generate_resource", "resourceType": "document", "topic": message, "reply": "我会结合当前画像和课程知识库生成一份可追溯的个性化学习讲义。"}
    if any(word in text for word in ["ppt", "课件", "演示文稿"]):
        return {"intent": "generate_resource", "resourceType": "ppt", "topic": message, "reply": "我会先为你准备 PPT 课件任务，生成完成后可以从卡片进入。"}
    if any(word in text for word in ["思维导图", "导图", "mind"]):
        return {"intent": "generate_resource", "resourceType": "mindmap", "topic": message, "reply": "我会为你整理一份结构清晰的思维导图入口。"}
    if any(word in text for word in ["动画讲解", "动画微课", "h5动画", "h5 动画", "生成动画", "动态讲解"]):
        return {"intent": "generate_resource", "resourceType": "animation", "topic": message, "reply": "我会生成一份可播放的 H5 动画微课，并保留质量评估结果。"}
    if any(word in text for word in ["视频", "课程视频", "讲解"]):
        return {"intent": "generate_resource", "resourceType": "video", "topic": message, "reply": "我会帮你准备视频检索入口，方便继续筛选学习资源。"}
    if any(word in text for word in ["题库", "练习题", "出题", "试卷", "考试"]):
        return {"intent": "generate_resource", "resourceType": "question_bank", "topic": message, "reply": "我会为你准备题库生成入口，并保留后台任务状态。"}
    if any(word in text for word in ["单片机实验", "单片机模拟器", "模拟器", "仿真", "mcu", "实验资源"]):
        return {"intent": "generate_resource", "resourceType": "document", "topic": message, "reply": "旧实验模块已下线，我会改为生成中医医案辨析讲义。"}
    if any(word in text for word in ["画像", "重新评估", "更新评估", "更新报告"]):
        return {"intent": "update_profile", "resourceType": "profile_update", "topic": message, "reply": "我会调用学习画像智能体，在后台汇总现有对话和学习证据。"}
    return {"intent": "chat", "resourceType": "none", "topic": "", "reply": "我在。你可以告诉我最近学到哪一步，或者直接让我生成讲义、题库、PPT、思维导图和视频资源。"}


def xiaozhi_extract_explicit_topic(message: str, resource_type: str) -> str:
    text = str(message or "").strip()
    if not text:
        return ""
    direct = text
    direct = re.sub(r"^(帮我|请|给我|为我|我想|需要|麻烦你|帮忙)", "", direct).strip()
    direct = re.sub(r"^(生成|做|制作|准备|输出|整理|查找|搜索|推荐|找|出)", "", direct).strip()
    keyword_map = {
        "document": r"(课程讲义|学习讲义|讲义|学习文档|课程文档|handout)",
        "ppt": r"(ppt|PPT|课件|演示文稿)",
        "mindmap": r"(思维导图|导图|mindmap)",
        "animation": r"(动画讲解|动画微课|h5动画|h5 动画|动态讲解|动画)",
        "video": r"(视频|讲解|课程视频)",
        "question_bank": r"(题库|练习题|试卷|题单)",
        "mcu": r"(单片机实验|单片机模拟器|模拟器|仿真|mcu|实验资源)",
    }
    keyword = keyword_map.get(resource_type)
    if keyword and re.search(keyword, direct, flags=re.I):
        topic = re.split(keyword, direct, flags=re.I)[0]
        topic = topic.strip(" 的，。,.、")
        if 2 <= len(topic) <= 40:
            return topic
    patterns = {
        "document": [r"(?:生成|做|制作|准备|输出|整理)?(.{2,40}?)(?:的)?(?:课程讲义|学习讲义|讲义|学习文档|课程文档|handout)"],
        "ppt": [r"(?:生成|做|制作|准备|输出)?(.{2,40}?)(?:的)?(?:ppt|PPT|课件|演示文稿)"],
        "mindmap": [r"(?:生成|做|制作|整理)?(.{2,40}?)(?:的)?(?:思维导图|导图|mindmap)"],
        "animation": [r"(?:生成|做|制作|准备)?(.{2,40}?)(?:的)?(?:动画讲解|动画微课|h5动画|h5 动画|动态讲解|动画)"],
        "video": [r"(?:查找|搜索|推荐|找)?(.{2,40}?)(?:的)?(?:视频|讲解|课程视频)"],
        "question_bank": [r"(?:生成|出|制作)?(.{2,40}?)(?:的)?(?:题库|练习题|试卷|题单)"],
        "mcu": [r"(?:打开|启动|运行|推荐|准备)?(.{2,40}?)(?:的)?(?:单片机实验|单片机模拟器|模拟器|仿真|mcu|实验资源)"],
    }
    for pattern in patterns.get(resource_type, []):
        match = re.search(pattern, text, flags=re.I)
        if match:
            topic = re.sub(r"^(帮我|请|给我|为我|我想|需要)", "", match.group(1)).strip(" ，。,.、")
            if topic:
                return topic
    return ""


def xiaozhi_detect_intent(message: str, context: dict, runtime_settings: dict[str, str] | None = None) -> dict:
    try:
        data = None
        model_errors = []
        for attempt in range(2):
            try:
                with setting_overrides(runtime_settings):
                    data = run_xiaozhi_hermes_agent(message, context)
                break
            except Exception as exc:
                model_errors.append(str(exc))
                app.logger.warning(
                    "XiaoZhi supervisor model attempt %s/2 failed: %s",
                    attempt + 1,
                    public_llm_error(exc),
                )
        if not isinstance(data, dict):
            raise RuntimeError("; ".join(model_errors) or "XiaoZhi supervisor model returned no result")
        fallback = xiaozhi_fallback_intent(message)
        deterministic_fallback = bool(
            fallback.get("intent") != "chat"
            and (
                fallback.get("intent") == "profile_management"
                or fallback.get("resourceType") in {"knowledge_base", "learning_feedback"}
                or xiaozhi_has_explicit_task_command(message)
                or xiaozhi_is_diagnostic_query(message)
            )
        )
        intent = (
            fallback["intent"]
            if deterministic_fallback
            else data.get("intent")
            if data.get("intent") in {"chat", "generate_resource", "update_profile", "profile_management"}
            else fallback["intent"]
        )
        if fallback.get("intent") == "profile_management":
            intent = "profile_management"
        resource_type = (
            fallback["resourceType"]
            if deterministic_fallback
            else data.get("resourceType")
            if data.get("resourceType") in XIAOZHI_RESOURCE_ROUTES or data.get("resourceType") == "none"
            else fallback["resourceType"]
        )
        if intent == "profile_management":
            resource_type = "profile_management"
        if intent == "generate_resource" and resource_type in {"", "none"}:
            resource_type = fallback["resourceType"]
        if fallback.get("resourceType") in {"knowledge_base", "learning_feedback"}:
            intent = "generate_resource"
            resource_type = fallback["resourceType"]
        resource_types = []
        raw_resource_types = (
            fallback.get("resourceTypes")
            if deterministic_fallback
            else data.get("resourceTypes")
            if isinstance(data.get("resourceTypes"), list)
            else fallback.get("resourceTypes")
        )
        if isinstance(raw_resource_types, list):
            for raw_type in raw_resource_types:
                task_type = normalize_resource_agent_type(raw_type)
                if task_type and task_type not in resource_types:
                    resource_types.append(task_type)
        if resource_type != "learning_feedback":
            for task_type in xiaozhi_detect_requested_resource_types(message):
                if task_type not in resource_types:
                    resource_types.append(task_type)
        if not resource_types and resource_type in RESOURCE_AGENT_ALLOWED_TYPES:
            resource_types.append(resource_type)
        explicit_topic = xiaozhi_extract_explicit_topic(message, resource_type)
        resolved_topic = str(
            explicit_topic
            or (fallback.get("topic") if deterministic_fallback else data.get("topic"))
            or fallback.get("topic")
            or message
        ).strip()
        selected_action = data.get("selectedAction") if isinstance(data.get("selectedAction"), dict) else {}
        if deterministic_fallback:
            action_name = {
                "chat": "chat",
                "generate_resource": "create_learning_task",
                "update_profile": "update_learning_profile",
                "profile_management": "manage_learning_profile",
            }.get(intent, "chat")
            selected_action = {
                "name": action_name,
                "arguments": {
                    "resourceType": resource_type,
                    "topic": resolved_topic,
                    "profileAction": str(fallback.get("profileAction") or "").strip(),
                },
            }
        return {
            "intent": intent,
            "resourceType": resource_type,
            "resourceTypes": resource_types,
            "profileAction": str((fallback.get("profileAction") if deterministic_fallback else data.get("profileAction")) or fallback.get("profileAction") or "").strip(),
            "targetQuery": str((fallback.get("targetQuery") if deterministic_fallback else data.get("targetQuery")) or fallback.get("targetQuery") or "").strip(),
            "knowledgeAction": str((fallback.get("knowledgeAction") if deterministic_fallback else data.get("knowledgeAction")) or fallback.get("knowledgeAction") or "").strip(),
            "collectionName": str((fallback.get("collectionName") if deterministic_fallback else data.get("collectionName")) or fallback.get("collectionName") or "").strip(),
            "knowledgeQuery": str((fallback.get("knowledgeQuery") if deterministic_fallback else data.get("knowledgeQuery")) or fallback.get("knowledgeQuery") or "").strip(),
            "feedbackOutcome": str(fallback.get("feedbackOutcome") or "").strip(),
            "feedbackDifficulty": str(fallback.get("feedbackDifficulty") or "").strip(),
            "feedbackHelpful": fallback.get("feedbackHelpful"),
            "topic": resolved_topic,
            "reply": str((fallback.get("reply") if deterministic_fallback else data.get("reply") or (fallback["reply"] if intent != "chat" else ""))).strip(),
            "weakPointSummary": str(data.get("weakPointSummary") or "").strip(),
            "suggestions": data.get("suggestions") if isinstance(data.get("suggestions"), list) else [],
            "selectedAction": selected_action,
            "agent": data.get("agent") or "xiaozhi-companion-agent",
            "runtime": data.get("runtime") or "hermes-agent",
            "provider": data.get("provider") or "xfyun-maas",
            "model": data.get("model") or "",
            "source": data.get("source") or "hermes_agent",
            "routingSource": "deterministic" if deterministic_fallback else "model",
        }
    except Exception as exc:
        data = xiaozhi_fallback_intent(message)
        data.update({"weakPointSummary": "", "suggestions": [], "source": "fallback", "routingSource": "fallback", "error": str(exc)})
        return data


def xiaozhi_build_card(task_id: str, task_type: str, title: str, route: str, status: str = "queued", result=None) -> dict:
    route_with_task = xiaozhi_route_with_task(route, task_id)
    return {
        "taskId": task_id,
        "type": task_type,
        "title": title,
        "description": f"嵌小智已为你创建{XIAOZHI_RESOURCE_LABELS.get(task_type, '学习资源')}任务，点击进入对应页面继续查看。",
        "route": route_with_task,
        "status": status,
        "result": result or {},
    }


def xiaozhi_feedback_target(context: dict, current_route: str = "") -> dict:
    context = context if isinstance(context, dict) else {}
    tasks = [item for item in (context.get("recentTasks") or []) if isinstance(item, dict)]
    route_task_id = ""
    route_cache_key = ""
    try:
        route_query = dict(parse_qsl(urlparse(str(current_route or "")).query))
        route_task_id = route_query.get("xzTask", "")
        route_cache_key = route_query.get("cacheKey", "")
    except (TypeError, ValueError):
        route_task_id = ""
        route_cache_key = ""
    excluded_types = {
        "learning_feedback",
        "learning_background",
        "profile_update",
        "learning_path",
        "learning_path_stage",
        "effect_assessment",
        "knowledge_base",
    }
    target = next(
        (item for item in tasks if route_task_id and item.get("taskId") == route_task_id),
        None,
    )
    if not target:
        target = next(
            (
                item
                for item in tasks
                if item.get("status") == "complete"
                and str(item.get("taskType") or "") not in excluded_types
            ),
            None,
        )
    target = target or {}
    target_route = str(target.get("route") or "")
    target_cache_key = ""
    try:
        target_cache_key = dict(parse_qsl(urlparse(target_route).query)).get("cacheKey", "")
    except (TypeError, ValueError):
        target_cache_key = ""
    route_matches_target = bool(route_task_id and route_task_id == str(target.get("taskId") or ""))
    return {
        "taskId": str(target.get("taskId") or ""),
        "resourceType": str(target.get("taskType") or ""),
        "route": str(current_route if route_matches_target else (target_route or current_route)),
        "cacheKey": str(route_cache_key if route_matches_target else target_cache_key),
        "topic": str(target.get("title") or "当前学习资源"),
    }


def xiaozhi_smart_tutor_request(message: str, current_route: str = "") -> dict:
    conversation_context = str(message or "").strip()
    marker = "我的回答或追问："
    question = conversation_context.rsplit(marker, 1)[-1].strip() if marker in conversation_context else conversation_context
    previous_task_id = ""
    try:
        previous_task_id = str(
            dict(parse_qsl(urlparse(str(current_route or "")).query)).get("xzTask") or ""
        ).strip()
    except (TypeError, ValueError):
        previous_task_id = ""
    return {
        "question": question[:2000] or "继续上一轮智能辅导",
        "conversationContext": conversation_context[:12000],
        "previousTaskId": previous_task_id[:100],
    }


def xiaozhi_build_profile_payload(context: dict, topic: str, user_id: int) -> dict:
    active_profile = context.get("profile") if isinstance(context.get("profile"), dict) else {}
    questionnaire = context.get("questionnaire") if isinstance(context.get("questionnaire"), dict) else {}
    has_active_profile = bool(int(active_profile.get("id") or active_profile.get("_profileReportId") or 0))
    profile = dict(active_profile or questionnaire)
    if not has_active_profile:
        for key in ("id", "_profileReportId", "_profileUpdatedAt", "isActive"):
            profile.pop(key, None)
    with auth_db() as conn:
        learning_evidence = learning_evidence_for_user(conn, int(user_id))
    profile_dimensions = profile.get("chatStudentProfile") or profile.get("studentProfile") or {}
    if not isinstance(profile_dimensions, dict):
        profile_dimensions = {}
    completed_dimensions = profile.get("completedProfileDimensions") or list(profile_dimensions.keys())
    if not isinstance(completed_dimensions, list):
        completed_dimensions = []
    missing_dimensions = profile.get("missingProfileDimensions") or []
    if not isinstance(missing_dimensions, list):
        missing_dimensions = []
    return {
        **profile,
        "baseProfile": profile,
        "learningEvidence": learning_evidence,
        "chatBackground": str(profile.get("chatBackground") or topic or "").strip(),
        "chatStudentProfile": profile_dimensions,
        "completedProfileDimensions": completed_dimensions,
        "missingProfileDimensions": missing_dimensions,
        "initialProfile": not has_active_profile,
        "refreshInstruction": (
            "自动检索现有问卷、聊天记录、答题情况、实验情况、资源调用和学习路径完成情况，生成第一份学习画像。"
            if not has_active_profile
            else "自动检索最新聊天记录、答题情况、实验情况、资源调用和学习路径完成情况，在同一份画像上更新分析。"
        ),
        "request": str(topic or "").strip(),
    }


def xiaozhi_profile_text(context: dict) -> str:
    profile = context.get("profile") or {}
    questionnaire = context.get("questionnaire") or {}
    snapshot = {
        "profile": profile.get("aiAnalysis") or profile,
        "questionnaire": questionnaire,
        "mcuExperiments": context.get("mcuExperiments") or [],
        "questionSheets": context.get("questionSheets") or [],
        "examResults": context.get("examResults") or [],
    }
    text = json.dumps(snapshot, ensure_ascii=False)
    return text[:5000] if text.strip("{} ") else "通用中医学习者，正在补全学习画像。"


def xiaozhi_profile_with_evidence(context: dict) -> dict:
    profile = dict(context.get("profile") or context.get("questionnaire") or {})
    weak_points = [
        str(item).strip()
        for experiment in (context.get("mcuExperiments") or [])
        for item in (experiment.get("weakPoints") or [])
        if str(item).strip()
    ]
    existing_evidence = profile.get("learningEvidence") if isinstance(profile.get("learningEvidence"), dict) else {}
    platform_evidence = context.get("learningEvidence") if isinstance(context.get("learningEvidence"), dict) else {}
    profile["_profileReportId"] = int(
        profile.get("_profileReportId")
        or profile.get("id")
        or context.get("profileReportId")
        or 0
    )
    profile["_profileUpdatedAt"] = str(
        profile.get("_profileUpdatedAt")
        or profile.get("updatedAt")
        or profile.get("createdAt")
        or profile.get("timestamp")
        or context.get("profileCreatedAt")
        or ""
    )
    profile["learningEvidence"] = {
        **existing_evidence,
        **platform_evidence,
        "source": "xiaozhi-platform-context",
        "examResults": platform_evidence.get("examResults") or context.get("examResults") or [],
        "mcuExperiments": platform_evidence.get("mcuExperiments") or context.get("mcuExperiments") or [],
        "weakPoints": list(dict.fromkeys([
            *[str(item).strip() for item in (platform_evidence.get("weakPoints") or []) if str(item).strip()],
            *weak_points,
        ]))[:10],
    }
    return profile


def xiaozhi_active_profile_with_evidence(context: dict) -> dict:
    profile = xiaozhi_profile_with_evidence(context)
    if not int(profile.get("id") or profile.get("_profileReportId") or 0):
        raise LearningProfileRequiredError(
            "当前没有激活画像，请先通过学习画像对话完成十个维度的采集。"
        )
    return profile


def xiaozhi_build_question_payload(context: dict, topic: str) -> dict:
    profile_text = xiaozhi_profile_text(context)
    target_topic = (topic or "").strip(" ，。,.、") or "中医系统综合练习"
    source_parts = [
        f"用户通过嵌小智请求生成题库，主题：{target_topic}",
        f"学习画像上下文：{profile_text}",
    ]
    for sheet in (context.get("questionSheets") or [])[:3]:
        source_parts.append(f"历史题单：{sheet.get('title') or ''} / {sheet.get('targetTopic') or ''}")
    for item in (context.get("examResults") or [])[:3]:
        source_parts.append(f"近期考试：正确 {item.get('correctCount')} / {item.get('questionCount')}")
    return {
        "student_profile": profile_text,
        "course_name": "中医系统",
        "target_topic": target_topic,
        "learning_objectives": f"围绕 {target_topic} 生成可用于自测和复习的结构化题库。",
        "resource_plan_result": "\n".join(source_parts),
        "preferred_question_types": ["单选题", "判断题", "填空题", "简答题"],
        "question_type_counts": {"单选题": 2, "判断题": 2, "填空题": 2, "简答题": 2},
        "question_type_scores": {"单选题": 2, "判断题": 1, "填空题": 2, "简答题": 5},
        "question_count": 8,
        "constraints": "由 Hermes 总控智能体触发；必须返回完整 JSON，题目贴近中医学习场景。",
        "force_real_agent": True,
    }


def xiaozhi_distribute_question_type_counts(question_types: object, total: int) -> dict[str, int]:
    ordered_types = [
        str(question_type).strip()
        for question_type in (question_types if isinstance(question_types, list) else [])
        if str(question_type).strip()
    ]
    ordered_types = list(dict.fromkeys(ordered_types))
    if not ordered_types:
        ordered_types = ["单选题", "判断题", "填空题", "简答题"]
    total = max(1, min(50, int(total)))
    base, remainder = divmod(total, len(ordered_types))
    return {
        question_type: base + (1 if index < remainder else 0)
        for index, question_type in enumerate(ordered_types)
        if base + (1 if index < remainder else 0) > 0
    }


def xiaozhi_resolve_learning_path_stage(config: dict, topic: str, params: dict | None = None) -> dict:
    params = params if isinstance(params, dict) else {}
    weeks = [item for item in (config.get("weeks") or []) if isinstance(item, dict)]
    stages = config.get("stages") if isinstance(config.get("stages"), dict) else {}
    supplied_stage = params.get("stage") if isinstance(params.get("stage"), dict) else {}
    requested_id = str(
        params.get("stageId")
        or params.get("weekId")
        or supplied_stage.get("id")
        or ""
    ).strip()

    selected_week = None
    if requested_id:
        selected_week = next(
            (item for item in weeks if str(item.get("id") or "") == requested_id),
            None,
        )
        if requested_id not in stages and selected_week is None and not supplied_stage:
            raise LookupError(f"学习路径中不存在阶段 {requested_id}")

    topic_text = " ".join(str(topic or "").split())
    if selected_week is None and not requested_id:
        selected_week = next(
            (
                item for item in weeks
                if any(
                    marker and marker in topic_text
                    for marker in (
                        str(item.get("weekLabel") or ""),
                        str(item.get("title") or ""),
                        str(item.get("id") or ""),
                    )
                )
            ),
            None,
        )
    if selected_week is None and not requested_id:
        numeric_week = re.search(r"第\s*(\d{1,2})\s*周", topic_text)
        if numeric_week:
            expected_order = int(numeric_week.group(1))
            selected_week = next(
                (item for item in weeks if int(item.get("order") or 0) == expected_order),
                None,
            )
    if selected_week is None and not requested_id:
        selected_week = next(
            (
                item for item in weeks
                if str(item.get("status") or "").lower() in {"current", "active", "in-progress"}
            ),
            weeks[0] if weeks else None,
        )

    stage_id = requested_id or str((selected_week or {}).get("id") or supplied_stage.get("id") or "")
    stored_stage = stages.get(stage_id) if stage_id else None
    stage = _json_copy(stored_stage) if isinstance(stored_stage, dict) else _json_copy(supplied_stage)
    if not stage:
        return {}
    if selected_week:
        stage.setdefault("id", str(selected_week.get("id") or stage_id))
        stage.setdefault("weekLabel", str(selected_week.get("weekLabel") or ""))
        stage.setdefault("focus", str(selected_week.get("title") or ""))
        stage.setdefault("goal", str(selected_week.get("description") or ""))

    detail_type_map = {
        "question-bank": "quiz",
        "mcu": "simulator",
        "mindmap": "mindmap",
        "ppt": "ppt",
        "video": "video",
        "document": "document",
    }
    nodes = stage.get("nodes") if isinstance(stage.get("nodes"), list) else []
    stage["resourceTypes"] = list(dict.fromkeys(
        detail_type_map.get(str(item.get("resourceType") or ""), str(item.get("resourceType") or ""))
        for item in nodes
        if isinstance(item, dict) and str(item.get("resourceType") or "")
    ))
    return stage


def xiaozhi_run_platform_agent(task_type: str, topic: str, context: dict, user_id: int, on_stage=None, params: dict | None = None) -> dict:
    params = params if isinstance(params, dict) else {}
    task_type = normalize_resource_agent_type(task_type) or task_type
    topic = _resource_agent_topic(topic, params)
    if task_type == "mcu":
        params = resolve_mcu_agent_params_for_user(int(user_id), params, topic)
        topic = _resource_agent_topic(topic, params)
    route = _resource_agent_route(task_type, topic, params)
    result = {
        "topic": topic,
        "resourceType": task_type,
        "route": route,
        "params": params,
        "orchestrator": "xiaozhi-companion-agent",
        "runtime": "hermes-agent",
    }

    if task_type == "profile_management":
        fallback = xiaozhi_fallback_intent(topic)
        action = str(
            params.get("action")
            or params.get("profileAction")
            or fallback.get("profileAction")
            or "list"
        ).strip().lower()
        if action not in {"list", "activate", "reset"}:
            raise ValueError("画像管理 action 必须是 list、activate 或 reset")
        target_query = str(
            params.get("targetQuery")
            or params.get("target")
            or fallback.get("targetQuery")
            or topic
        ).strip()
        management = xiaozhi_execute_profile_management(int(user_id), action, target_query)
        if management.get("error"):
            raise LookupError(management.get("reply") or "画像管理动作未完成")
        result.update(
            {
                "message": management.get("reply") or "画像管理动作已完成。",
                "profileManagement": management,
                "route": "/learning-profile?menu=history",
            }
        )
        return result

    if task_type == "learning_feedback":
        feedback_payload = {
            **params,
            "taskId": str(params.get("sourceTaskId") or params.get("taskId") or "").strip(),
            "topic": str(params.get("feedbackTopic") or params.get("topic") or topic).strip(),
            "route": str(params.get("route") or "").strip(),
        }
        with auth_db() as conn:
            feedback = record_learning_feedback(conn, int(user_id), feedback_payload)
        messages = {
            "completed": "学习反馈已记录，本次任务已计入路径完成与效果评估。",
            "needs_review": "巩固需求已记录，效果评估会把该主题作为后续调整依据。",
            "blocked": "学习阻塞已记录，后续辅导与路径调整会优先处理该主题。",
        }
        result.update(
            {
                "message": messages.get(feedback.get("outcome"), "学习反馈已记录。"),
                "feedback": feedback,
                "route": "/effect-assessment?section=feedback",
            }
        )
        return result

    if task_type == "knowledge_base":
        command = xiaozhi_private_knowledge_command(topic, params)
        action = command["action"]
        message = "私有知识库目录已读取。"
        with auth_db() as conn:
            if action == "create":
                name = command["collectionName"] or "我的课程知识库"
                collection = private_knowledge_service.create_knowledge_collection(
                    conn,
                    int(user_id),
                    name,
                    str(params.get("description") or "由嵌小智创建的私有课程知识库"),
                    activate=True,
                    timestamp=now_iso(),
                )
                message = f"已创建并启用知识库“{collection['name']}”。"
            elif action == "activate":
                target = private_knowledge_service.find_knowledge_collection(
                    conn,
                    int(user_id),
                    command["collectionName"] or topic,
                )
                collection = private_knowledge_service.activate_knowledge_collection(
                    conn,
                    int(user_id),
                    int(target["id"]),
                    timestamp=now_iso(),
                )
                message = f"已切换到知识库“{collection['name']}”。"
            elif action == "add_text":
                catalog = private_knowledge_service.list_knowledge_collections(conn, int(user_id))
                active_id = int(params.get("collectionId") or catalog.get("activeCollectionId") or 0)
                if not active_id:
                    collection = private_knowledge_service.create_knowledge_collection(
                        conn,
                        int(user_id),
                        command["collectionName"] or "我的课程知识库",
                        "由嵌小智创建的私有课程知识库",
                        activate=True,
                        timestamp=now_iso(),
                    )
                    active_id = int(collection["id"])
                if not command["content"].strip():
                    raise private_knowledge_service.PrivateKnowledgeError("写入知识库的文本不能为空")
                document = private_knowledge_service.add_knowledge_document(
                    conn,
                    int(user_id),
                    active_id,
                    filename=command["filename"],
                    content=command["content"].encode("utf-8"),
                    mime_type="text/markdown",
                    timestamp=now_iso(),
                )
                message = f"已将“{document['filename']}”写入当前知识库。"
            catalog = private_knowledge_service.list_knowledge_collections(conn, int(user_id))

        if action == "search":
            search_query = command["query"] or topic
            knowledge_base = retrieve_course_knowledge(
                search_query,
                top_k=max(1, min(12, int(params.get("topK") or 6))),
                user_id=int(user_id),
                db_path=AUTH_DB_PATH,
            )
            message = f"知识库检索完成，命中 {len(knowledge_base.get('hits') or [])} 条可追溯片段。"
        else:
            knowledge_base = {"action": action, **catalog}
        result.update(
            {
                "message": message,
                "knowledgeBase": knowledge_base,
                "route": "/personalized-resources/knowledge-base",
            }
        )
        return result

    if task_type == "profile_update":
        xiaozhi_insert_event(
            user_id,
            "profile_update_requested",
            "/learning-profile",
            "嵌小智请求更新学习画像",
            {"topic": topic},
        )
        payload = xiaozhi_build_profile_payload(context, topic, int(user_id))
        base_profile = payload["baseProfile"]
        report_id = int(base_profile.get("id") or base_profile.get("_profileReportId") or 0)
        report_result = generate_profile_report(payload)
        if report_result.get("source") not in {"llm", "llm-fallback", "fallback-rule"}:
            raise RuntimeError(report_result.get("error") or "学习画像智能体未返回有效结果")
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
                "timestamp": now_iso(),
                "aiAnalysis": report_result,
                "learningEvidence": payload["learningEvidence"],
                "refreshInstruction": payload["refreshInstruction"],
                "updatedBy": "xiaozhi-learning-evidence",
                "effectAssessment": effect_assessment_snapshot(
                    base_profile,
                    payload["learningEvidence"],
                ),
            }
        )
        with auth_db() as conn:
            if report_id:
                report = update_profile_report(
                    conn,
                    int(user_id),
                    report_id,
                    report,
                    timestamp=report["timestamp"],
                )
                message = "嵌小智已根据最新学习证据更新当前画像。"
            else:
                report = create_profile_version(
                    conn,
                    int(user_id),
                    report,
                    profile_name=str(params.get("profileName") or base_profile.get("profileName") or "学习画像"),
                    start_new_profile=True,
                    timestamp=report["timestamp"],
                )
                message = "嵌小智已根据现有对话和学习证据生成第一份画像。"
        _schedule_profile_portrait_generation(int(user_id), int(report["id"]), force=True)
        learning_path_task = _schedule_profile_learning_path_generation(
            int(user_id),
            int(report["id"]),
        )
        if learning_path_task:
            message = f"{message} 对应学习路径已在后台开始生成。"
        result.update({
            "message": message,
            "reportId": report.get("id"),
            "report": report,
            "learningPathTask": learning_path_task,
        })
        return result

    if task_type == "learning_background":
        chat_result = generate_background_chat({"messages": [{"role": "user", "content": topic or "请继续采集我的学习背景"}]})
        result.update({"message": chat_result.get("reply") or chat_result.get("question") or "学习背景对话智能体已返回。", "dialogue": chat_result})
        return result

    if task_type == "learning_path":
        grounded_profile = xiaozhi_active_profile_with_evidence(context)
        path_result = generate_learning_path({"profile": grounded_profile})
        path_config = path_result.get("config") if isinstance(path_result, dict) else None
        if not isinstance(path_config, dict):
            raise RuntimeError("学习路径智能体未返回可保存的路径配置")
        profile_report_id = int(grounded_profile.get("id") or grounded_profile.get("_profileReportId") or 0)
        if profile_report_id > 0:
            path_config.setdefault("meta", {})["profileReportId"] = profile_report_id
        result.update({"message": "学习路径智能体已生成路径。", "learningPath": path_result})
        return result

    if task_type == "learning_path_stage":
        grounded_profile = xiaozhi_active_profile_with_evidence(context)
        grounded_profile_id = int(grounded_profile.get("id") or grounded_profile.get("_profileReportId") or 0)
        with auth_db() as conn:
            saved_row = conn.execute(
                "SELECT 1 FROM user_learning_path_configs WHERE user_id = ?",
                (int(user_id),),
            ).fetchone()
            saved_config = read_learning_path_config(conn, int(user_id)) if saved_row else {}
        stage = xiaozhi_resolve_learning_path_stage(saved_config, topic, params)
        path_origin = "persisted"
        path_result: dict = {}
        candidate_config: dict | None = None
        if not stage:
            path_result = generate_learning_path({"profile": grounded_profile})
            path_config = path_result.get("config") if isinstance(path_result, dict) else None
            if not isinstance(path_config, dict):
                raise RuntimeError("学习路径智能体未返回可细化的路径")
            saved_config = normalize_learning_path_config(path_config)
            if grounded_profile_id > 0:
                saved_config.setdefault("meta", {})["profileReportId"] = grounded_profile_id
            candidate_config = saved_config
            stage = xiaozhi_resolve_learning_path_stage(saved_config, topic, params)
            path_origin = "generated"
        if not stage:
            raise RuntimeError("当前学习路径中没有可细化的周任务")
        config_meta = saved_config.get("meta") if isinstance(saved_config.get("meta"), dict) else {}
        planner = saved_config.get("planner") if isinstance(saved_config.get("planner"), dict) else {}
        path_source = str(
            path_result.get("source")
            or config_meta.get("generationSource")
            or planner.get("source")
            or path_origin
        ).strip()
        generation_status = str(
            path_result.get("generationStatus")
            or config_meta.get("generationStatus")
            or ("fallback" if learning_path_config_is_degraded(saved_config) else "persisted")
        ).strip()
        path_degraded = (
            bool(path_result.get("degraded"))
            or learning_path_config_is_degraded(saved_config)
            or generation_status.lower() == "fallback"
            or path_source.lower() in {"fallback-rule", "profile-rule-agent"}
        )
        path_error = str(path_result.get("error") or config_meta.get("generationError") or "").strip()
        detail = generate_learning_path_stage_detail(
            {"profile": grounded_profile, "stage": stage, "resources": [], "useLLM": True}
        )
        stage_result = {
            "message": f"阶段细化智能体已生成{stage.get('weekLabel') or '当前周'}学习任务。",
            "learningPath": {
                "stageId": stage.get("id"),
                "profileReportId": learning_path_profile_report_id(saved_config) or grounded_profile_id,
                "savedPathUpdatedAt": saved_config.get("updatedAt") or "" if path_origin == "persisted" else "",
                "source": path_source,
                "pathSource": path_origin,
                "generationStatus": generation_status,
                "degraded": path_degraded,
                "error": path_error,
            },
            "stage": stage,
            "stageDetail": detail,
        }
        if isinstance(candidate_config, dict):
            stage_result["_candidateLearningPathConfig"] = candidate_config
        result.update(stage_result)
        return result

    if task_type == "question_bank":
        qg_payload = xiaozhi_build_question_payload(context, topic)
        if params:
            course = str(params.get("course") or params.get("courseName") or "").strip()
            chapter = str(params.get("chapter") or params.get("chapterName") or params.get("targetTopic") or "").strip()
            count = params.get("count") or params.get("questionCount") or params.get("question_count")
            constraints = str(params.get("constraints") or params.get("requirements") or "").strip()
            if course:
                qg_payload["course_name"] = course
            if chapter:
                qg_payload["target_topic"] = chapter
                qg_payload["learning_objectives"] = f"围绕 {chapter} 生成可用于自测和复习的结构化题库。"
            try:
                if count is not None:
                    requested_count = max(1, min(50, int(count)))
                    qg_payload["question_count"] = requested_count
                    qg_payload["question_type_counts"] = xiaozhi_distribute_question_type_counts(
                        qg_payload.get("preferred_question_types"),
                        requested_count,
                    )
            except (TypeError, ValueError):
                pass
            if constraints:
                qg_payload["constraints"] = constraints
        qg_result = generate_question_bank(qg_payload)
        question_bank = qg_result.get("question_bank") if isinstance(qg_result.get("question_bank"), dict) else {}
        knowledge_sources = question_bank.get("knowledge_sources") if isinstance(question_bank.get("knowledge_sources"), list) else []
        if not knowledge_sources:
            knowledge_sources = params.get("knowledgeSources") if isinstance(params.get("knowledgeSources"), list) else []
            if knowledge_sources:
                question_bank["knowledge_sources"] = knowledge_sources
        quality = evaluate_question_bank_resource(
            question_bank,
            expected_count=int(qg_payload.get("question_count") or len(question_bank.get("questions") or []) or 1),
            citations=knowledge_sources,
        )
        sheet = save_question_sheet(qg_result["question_bank"], user_id=user_id)
        qg_result["question_sheet"] = sheet
        qg_result["qualityEvaluation"] = quality
        result.update({
            "message": "题库生成工作流已完成。",
            "questionGenerator": qg_result,
            "sheet": sheet,
            "qualityEvaluation": quality,
            "knowledgeSources": knowledge_sources,
        })
        return result

    if task_type == "ppt":
        try:
            page_count = max(1, min(20, int(params.get("pageCount") or params.get("pages") or 6)))
        except (TypeError, ValueError):
            page_count = 6
        user_message = str(params.get("userMessage") or params.get("prompt") or topic).strip()
        session_id = str(params.get("sessionId") or "").strip() or f"ppt_{int(time.time() * 1000)}_{secrets.token_hex(3)}"
        ppt_result = generate_ppt_h5(
            {
                "sessionId": session_id,
                "topic": topic or "中医学习课件",
                "userMessage": user_message,
                "pageCount": page_count,
                "styleName": str(params.get("styleName") or "中药鉴别浅绿平台风"),
                "styleDescription": str(params.get("styleDescription") or "白底浅绿、干净明亮、模块化教育科技风。"),
                "styleSkill": str(params.get("styleSkill") or ""),
            },
            on_stage=on_stage,
        )
        knowledge_sources = ppt_result.get("knowledgeSources") if isinstance(ppt_result.get("knowledgeSources"), list) else []
        quality = evaluate_ppt_resource(
            ppt_result,
            expected_page_count=page_count,
            citations=knowledge_sources,
        )
        ppt_result["qualityEvaluation"] = quality
        route = _resource_agent_route(
            "ppt",
            topic or "中医学习课件",
            {**params, "sessionId": session_id, "pageCount": page_count, "prompt": user_message},
        )
        route_with_task = xiaozhi_route_with_task(route, str(params.get("taskId") or ""))
        result.update({
            "message": "PPT 生成智能体已完成 H5 课件。",
            "ppt": ppt_result,
            "sessionId": session_id,
            "ohmyPptSessionId": session_id,
            "pageCount": page_count,
            "route": route_with_task,
            "qualityEvaluation": quality,
            "knowledgeSources": knowledge_sources,
        })
        if isinstance(result.get("ppt"), dict):
            result["ppt"].setdefault("route", route_with_task)
        return result

    if task_type == "document":
        profile = xiaozhi_profile_with_evidence(context)
        generated = generate_learning_document(
            {
                "topic": topic,
                "requirements": params.get("requirements") or params.get("prompt") or "",
                "profile": profile,
                "knowledgeContext": params.get("knowledgeContext") or [],
                "knowledgeSources": params.get("knowledgeSources") or [],
            }
        )
        orchestration_context = params.get("orchestrationContext") if isinstance(params.get("orchestrationContext"), dict) else {}
        task_key = str(params.get("taskId") or f"document_{int(time.time() * 1000)}_{secrets.token_hex(3)}")
        with auth_db() as conn:
            stored_document = save_learning_document(
                conn,
                user_id=int(user_id),
                profile_report_id=int(profile.get("id") or profile.get("_profileReportId") or 0),
                task_id=task_key,
                run_id=str(orchestration_context.get("runId") or ""),
                topic=topic,
                generated=generated,
                timestamp=now_iso(),
            )
        result.update(
            {
                "message": "课程讲义生成智能体已完成可追溯学习文档。",
                **generated,
                "documentId": stored_document.get("id"),
                "documentRecord": stored_document,
                "route": f"/personalized-resources/document?documentId={stored_document.get('id')}",
            }
        )
        return result

    if task_type == "animation":
        generated = generate_learning_animation(
            {
                "topic": topic,
                "requirements": params.get("requirements") or params.get("prompt") or "",
                "profile": xiaozhi_profile_with_evidence(context),
                "knowledgeContext": params.get("knowledgeContext") or [],
                "knowledgeSources": params.get("knowledgeSources") or [],
            }
        )
        result.update(
            {
                "message": "H5 动画讲解智能体已生成可播放微课。",
                **generated,
            }
        )
        return result

    if task_type == "interview":
        interview_result = start_interview_session(
            user_id,
            {
                "topic": topic or "阴阳五行 / 四诊 / 八纲辨证",
                "direction": topic or "阴阳五行 / 四诊 / 八纲辨证",
                "difficulty": "medium",
                "difficultyLabel": "中等",
                "positionKey": "stm32_developer",
                "position": "中医基础理论学习者",
            },
        )
        result.update({"message": "数字人学习访谈已启动。", "interview": interview_result})
        return result

    if task_type == "smart_tutor":
        question = str(params.get("question") or topic).strip()[:2000] or topic
        conversation_context = str(params.get("conversationContext") or "").strip()[:12000]
        previous_task_id = str(params.get("previousTaskId") or "").strip()[:100]
        previous_task = next(
            (
                item
                for item in (context.get("recentTasks") or [])
                if isinstance(item, dict) and str(item.get("taskId") or "") == previous_task_id
            ),
            None,
        )
        if previous_task_id and not previous_task:
            with auth_db() as conn:
                previous_row = conn.execute(
                    """
                    SELECT task_id, task_type, title, prompt, status, route, result_json, error, created_at, updated_at
                    FROM xiaozhi_tasks
                    WHERE user_id = ? AND task_id = ?
                    LIMIT 1
                    """,
                    (int(user_id), previous_task_id),
                ).fetchone()
            previous_task = xiaozhi_task_from_row(previous_row) if previous_row else None
        previous_turn = {}
        if isinstance(previous_task, dict):
            previous_result = previous_task.get("result") if isinstance(previous_task.get("result"), dict) else {}
            previous_tutor = previous_result.get("tutor") if isinstance(previous_result.get("tutor"), dict) else {}
            previous_turn = {
                "taskId": str(previous_task.get("taskId") or ""),
                "title": str(previous_task.get("title") or "")[:200],
                "question": str(previous_tutor.get("question") or previous_task.get("prompt") or "")[:2000],
                "answer": str(previous_tutor.get("answer") or previous_result.get("answer") or "")[:5000],
                "socraticQuestions": (previous_tutor.get("socraticQuestions") or [])[:6],
                "followUp": str(previous_tutor.get("followUp") or "")[:1000],
            }
        tutor_result = xiaozhi_smart_tutor_result(
            {
                "question": question,
                "topic": topic,
                "profile": xiaozhi_profile_with_evidence(context),
                "xiaozhiContext": context,
                "knowledgeContext": params.get("knowledgeContext") or [],
                "knowledgeSources": params.get("knowledgeSources") or [],
                "conversationContext": conversation_context,
                "previousTaskId": previous_task_id,
                "previousTurn": previous_turn,
            }
        )
        result.update(
            {
                "message": tutor_result.get("answer") or tutor_result.get("explanation") or "智能辅导已完成。",
                "answer": tutor_result.get("answer") or tutor_result.get("explanation") or "",
                "tutor": tutor_result,
                "previousTaskId": previous_task_id,
            }
        )
        return result

    if task_type == "effect_assessment":
        profile = xiaozhi_profile_with_evidence(context)
        with auth_db() as conn:
            evidence = learning_evidence_for_user(conn, int(user_id))
        snapshot = effect_assessment_snapshot(profile, evidence)
        try:
            narrative = xiaozhi_effect_assessment_result(
                {
                    "request": topic,
                    "profile": profile,
                    "examResults": evidence.get("examResults") or [],
                    "mcuExperiments": evidence.get("mcuExperiments") or [],
                    "questionSheets": evidence.get("questionSheets") or [],
                    "resourceCalls": evidence.get("resourceCalls") or [],
                    "resourceVisits": evidence.get("resourceVisits") or [],
                    "activitySessions": evidence.get("activitySessions") or [],
                    "activeLearningSeconds": evidence.get("activeLearningSeconds") or 0,
                    "knowledgePointStats": evidence.get("knowledgePointStats") or [],
                    "deterministicAssessment": snapshot,
                    "params": params,
                }
            )
        except Exception:
            narrative = {
                "source": "deterministic-fallback",
                "summary": snapshot.get("summary"),
                "uncertainties": ["模型评估叙事未形成可解析 JSON，本次量化指标仍来自平台学习证据。"],
            }
        assessment_result = merge_xiaozhi_effect_assessment(snapshot, narrative)
        result.update(
            {
                "message": assessment_result.get("summary") or "学习效果评估已完成。",
                **assessment_result,
                "assessment": assessment_result,
            }
        )
        return result

    if task_type == "personalized_resources":
        grounded_profile = xiaozhi_profile_with_evidence(context)
        llm_resources = generate_personalized_resources(
            {
                "profile": grounded_profile,
                "route": context.get("learningPath") or {},
                "request": {"topic": topic, "resourceType": task_type},
            }
        )
        workflow = generate_resource_workflow(
            {
                "profile": grounded_profile,
                "route": {},
                "request": {"topic": topic, "resourceType": task_type},
            },
            mcu_experiments=context.get("mcuExperiments") or [],
            user_id=user_id,
        )
        result.update(
            {
                "message": "个性化资源多智能体工作流已完成。",
                "llmResources": llm_resources,
                "workflow": workflow,
                "selectedResource": (workflow.get("resources") or [None])[0] if isinstance(workflow, dict) else None,
            }
        )
        return result

    if task_type in {"mindmap", "video", "mcu"}:
        grounded_profile = xiaozhi_profile_with_evidence(context)
        workflow = generate_resource_workflow(
            {
                "profile": grounded_profile,
                "route": {},
                "request": {"topic": topic, "resourceType": task_type},
            },
            mcu_experiments=context.get("mcuExperiments") or [],
            user_id=user_id,
        )
        resources = workflow.get("resources") if isinstance(workflow, dict) else []
        aliases = {"mindmap": "mindmap", "video": "video", "mcu": "simulator"}
        selected = None
        for item in resources or []:
            if task_type == "personalized_resources" or item.get("type") == aliases.get(task_type):
                selected = item
                break
        selected_metadata = selected.get("metadata") if isinstance(selected, dict) and isinstance(selected.get("metadata"), dict) else {}
        quality = selected.get("qualityEvaluation") if isinstance(selected, dict) and isinstance(selected.get("qualityEvaluation"), dict) else {}
        knowledge_sources = selected_metadata.get("knowledgeSources") if isinstance(selected_metadata.get("knowledgeSources"), list) else []
        result.update({
            "message": "个性化资源工作流已完成。",
            "workflow": workflow,
            "selectedResource": selected,
            "qualityEvaluation": quality,
            "knowledgeSources": knowledge_sources,
        })
        return result

    raise ValueError(f"未知的小智任务类型: {task_type}")


def _persist_xiaozhi_reviewed_learning_path_candidate(
    task_type: str,
    user_id: int,
    result: dict,
) -> None:
    learning_path = result.get("learningPath") if isinstance(result.get("learningPath"), dict) else {}
    if task_type == "learning_path":
        candidate = learning_path.get("config") if isinstance(learning_path.get("config"), dict) else None
        if not isinstance(candidate, dict):
            raise RuntimeError("审核通过的学习路径缺少可保存配置")
    elif task_type == "learning_path_stage":
        candidate = result.pop(XIAOZHI_LEARNING_PATH_CANDIDATE_FIELD, None)
        if not isinstance(candidate, dict):
            return
    else:
        return

    trace = result.get("orchestration") if isinstance(result.get("orchestration"), dict) else {}
    harness = result.get("harness") if isinstance(result.get("harness"), dict) else {}
    profile_candidates = [
        learning_path_profile_report_id(candidate),
        learning_path.get("profileReportId"),
        trace.get("profileReportId"),
        harness.get("profileReportId"),
    ]
    profile_report_id = 0
    for value in profile_candidates:
        try:
            profile_report_id = int(value or 0)
        except (TypeError, ValueError):
            continue
        if profile_report_id > 0:
            break
    if profile_report_id <= 0:
        raise LearningProfileRequiredError("审核通过的学习路径缺少有效画像版本，未保存候选路径。")

    with _learning_path_config_write_lock(int(user_id)):
        with auth_db() as conn:
            profile_exists = conn.execute(
                "SELECT 1 FROM learning_profile_reports WHERE id = ? AND user_id = ? AND archived = 0",
                (profile_report_id, int(user_id)),
            ).fetchone()
            if not profile_exists:
                raise LearningProfileRequiredError("学习路径关联的画像版本已失效，未保存候选路径。")
            saved_config = write_learning_path_config(
                conn,
                candidate,
                int(user_id),
                profile_report_id=profile_report_id,
            )

    if task_type == "learning_path":
        learning_path["config"] = saved_config
        return
    learning_path.update(
        {
            "profileReportId": learning_path_profile_report_id(saved_config) or profile_report_id,
            "savedPathUpdatedAt": saved_config.get("updatedAt") or "",
            "persisted": True,
        }
    )


def xiaozhi_run_resource_task(task_id: str, user_id: int, task_type: str, topic: str, params: dict | None = None) -> None:
    with private_knowledge_service.private_knowledge_scope(int(user_id), AUTH_DB_PATH):
        _xiaozhi_run_resource_task(task_id, user_id, task_type, topic, params)


def _xiaozhi_run_resource_task(task_id: str, user_id: int, task_type: str, topic: str, params: dict | None = None) -> None:
    params = params if isinstance(params, dict) else {}
    if task_type == "generated_video":
        route = xiaozhi_route_with_task(
            _resource_agent_route(task_type, topic, params),
            task_id,
        )
        try:
            context = xiaozhi_latest_context(user_id)
            knowledge_payload = retrieve_course_knowledge(topic, top_k=6, user_id=int(user_id), db_path=AUTH_DB_PATH)
            knowledge_sources = knowledge_payload.get("citations") or [] if isinstance(knowledge_payload, dict) else []
            if not isinstance(knowledge_sources, list):
                knowledge_sources = []
            xiaozhi_append_task_conversation(
                int(user_id),
                task_id,
                profile_report_id=params.get("profileReportId") or 0,
                agent_id="knowledge-retrieval-agent",
                agent_name="知识检索智能体",
                message_type="knowledge_retrieval",
                status="complete",
                content=f"已为 AI 视频检索 {len(knowledge_sources)} 条知识依据，交给视频生成智能体。",
                payload={
                    "resourceType": "generated_video",
                    "stage": "knowledge_retrieval",
                    "progress": 5,
                    "route": route,
                    "citations": knowledge_sources,
                },
                dedupe_suffix="video:knowledge-retrieval",
            )

            def update_video_task(**fields) -> None:
                xiaozhi_update_task(task_id, **fields)
                state = fields.get("result_json") if isinstance(fields.get("result_json"), dict) else {}
                stage = str(state.get("currentStage") or "generating")
                progress = max(0, min(100, int(state.get("progress") or 0)))
                message = str(state.get("message") or "AI 视频生成进度已更新")
                xiaozhi_append_task_conversation(
                    int(user_id),
                    task_id,
                    profile_report_id=params.get("profileReportId") or 0,
                    agent_id="generated-video-agent",
                    agent_name="AI 视频生成智能体",
                    message_type="resource_progress",
                    status=str(fields.get("status") or "running"),
                    content=message,
                    payload={
                        "resourceType": "generated_video",
                        "stage": stage,
                        "progress": progress,
                        "route": route,
                    },
                    dedupe_suffix=f"video:{stage}:{progress}",
                )

            result = execute_generated_video_task(
                task_id,
                int(user_id),
                topic,
                params,
                context.get("profile") if isinstance(context.get("profile"), dict) else {},
                knowledge_sources,
                update_video_task,
            )
            xiaozhi_update_task(task_id, status="complete", result_json=result, route=route)
            xiaozhi_append_task_conversation(
                int(user_id),
                task_id,
                profile_report_id=params.get("profileReportId") or 0,
                agent_id="generated-video-agent",
                agent_name="AI 视频生成智能体",
                message_type="resource_complete",
                status="complete",
                content=str(result.get("message") or "AI 视频已生成完成。"),
                payload={
                    "resourceType": "generated_video",
                    "stage": "complete",
                    "progress": 100,
                    "route": route,
                    "knowledgeSources": knowledge_sources,
                    "selectedResource": result.get("selectedResource"),
                },
                dedupe_suffix="video:complete",
            )
        except Exception as exc:
            error_message = str(exc) or "AI 视频生成失败"
            xiaozhi_update_task(
                task_id,
                status="failed",
                result_json={
                    "message": error_message,
                    "topic": topic,
                    "progress": 100,
                    "currentStage": "error",
                    "engine": str(params.get("videoEngine") or "seedance_1_5_coze"),
                    "segments": [],
                    "selectedResource": None,
                    "logs": [{
                        "time": now_iso(),
                        "stage": "error",
                        "message": error_message,
                        "progress": 100,
                    }],
                },
                error=error_message,
            )
            xiaozhi_append_task_conversation(
                int(user_id),
                task_id,
                profile_report_id=params.get("profileReportId") or 0,
                agent_id="generated-video-agent",
                agent_name="AI 视频生成智能体",
                message_type="resource_failed",
                status="failed",
                content=f"AI 视频生成失败：{error_message}",
                payload={
                    "resourceType": "generated_video",
                    "stage": "error",
                    "progress": 100,
                    "route": route,
                    "error": error_message,
                },
                dedupe_suffix="video:failed",
            )
        return
    with auth_db() as conn:
        task_row = conn.execute(
            "SELECT result_json FROM xiaozhi_tasks WHERE task_id = ? LIMIT 1",
            (task_id,),
        ).fetchone()
    task_result_state = json_loads_safe(task_row["result_json"], {}) if task_row else {}
    if not isinstance(task_result_state, dict):
        task_result_state = {}
    logs: list[dict] = []
    agent_runs: dict[str, dict] = {}

    def merge_ppt_task_state(
        result: dict,
        *,
        status: str,
        stage: str,
        message: str,
        progress: int,
        error_message: str = "",
    ) -> dict:
        if task_type != "ppt":
            return result
        merged = {**task_result_state, **result}
        persisted_params = task_result_state.get("params") if isinstance(task_result_state.get("params"), dict) else {}
        merged_params = {**persisted_params, **params}
        try:
            page_count = max(
                1,
                min(
                    20,
                    int(
                        merged.get("pageCount")
                        or merged_params.get("pageCount")
                        or merged_params.get("pages")
                        or merged_params.get("page_count")
                        or 6
                    ),
                ),
            )
        except (TypeError, ValueError):
            page_count = 6
        current_ppt = task_result_state.get("ppt") if isinstance(task_result_state.get("ppt"), dict) else {}
        result_ppt = result.get("ppt") if isinstance(result.get("ppt"), dict) else {}
        session_id = str(
            result_ppt.get("sessionId")
            or current_ppt.get("sessionId")
            or merged.get("sessionId")
            or merged.get("ohmyPptSessionId")
            or merged_params.get("sessionId")
            or ""
        ).strip()
        route = str(
            merged.get("route")
            or current_ppt.get("route")
            or _resource_agent_route(
                "ppt",
                topic or "中医学习课件",
                {**merged_params, "sessionId": session_id, "pageCount": page_count},
            )
        )
        route = xiaozhi_route_with_task(route, task_id)
        merged_ppt = {
            **current_ppt,
            **result_ppt,
            "status": status,
            "sessionId": session_id,
            "title": str(result_ppt.get("title") or current_ppt.get("title") or topic),
            "topic": str(result_ppt.get("topic") or current_ppt.get("topic") or topic),
            "pageCount": page_count,
            "route": route,
            "progress": max(0, min(100, int(progress))),
            "currentStage": stage,
            "message": message,
            "error": error_message,
        }
        merged.update(
            {
                "message": message,
                "topic": topic,
                "resourceType": "ppt",
                "params": merged_params,
                "sessionId": session_id,
                "ohmyPptSessionId": session_id,
                "pageCount": page_count,
                "route": route,
                "progress": max(0, min(100, int(progress))),
                "currentStage": stage,
                "ppt": merged_ppt,
            }
        )
        return merged

    def push_progress(stage: str, message: str, progress: int, event: dict | None = None):
        nonlocal task_result_state
        log_entry = {"time": now_iso(), "stage": stage, "message": message, "progress": progress}
        if not logs or logs[-1].get("stage") != stage or logs[-1].get("message") != message:
            logs.append(log_entry)
        event = event if isinstance(event, dict) else {}
        agent_id = str(event.get("agentId") or "")
        if agent_id:
            event_status = str(event.get("status") or "running")
            agent_runs[agent_id] = {
                "id": agent_id,
                "name": event.get("agentName") or AGENT_CATALOG.get(agent_id, {}).get("name") or agent_id,
                "role": AGENT_CATALOG.get(agent_id, {}).get("role") or "specialist",
                "status": "failed"
                if event_status in {"failed", "error"}
                else ("warning" if event_status == "warning" else ("complete" if event_status in {"complete", "done"} else "running")),
                "detail": message,
                "progress": max(progress, int(agent_runs.get(agent_id, {}).get("progress") or 0)),
            }
        progress_value = max(0, min(100, int(progress)))
        progress_result = {
            **task_result_state,
            "message": message,
            "topic": topic,
            "progress": progress_value,
            "currentStage": stage,
            "logs": logs[-40:],
            "agentRuns": list(agent_runs.values()),
            "architecture": XIAOZHI_ARCHITECTURE,
            "rootAgent": XIAOZHI_MASTER_AGENT_ID,
        }
        progress_result = merge_ppt_task_state(
            progress_result,
            status="running",
            stage=stage,
            message=message,
            progress=progress_value,
        )
        task_result_state = progress_result
        xiaozhi_update_task(
            task_id,
            status="running",
            result_json=progress_result,
        )

    try:
        push_progress("start", "嵌小智已接管任务，正在准备上下文", 8)
        context = xiaozhi_latest_context(user_id)
        push_progress("context", "已读取学习画像、历史任务和实验记录", 14)

        def on_event(stage_payload: dict):
            push_progress(
                str(stage_payload.get("stage") or "progress"),
                str(stage_payload.get("message") or "智能体正在执行"),
                _safe_progress(stage_payload.get("progress"), 30),
                stage_payload,
            )

        def specialist(managed_payload: dict, specialist_progress) -> dict:
            managed_params = {
                **params,
                "taskId": task_id,
                "knowledgeContext": managed_payload.get("knowledgeContext") or [],
                "knowledgeSources": managed_payload.get("knowledgeSources") or [],
                "orchestrationContext": managed_payload.get("orchestrationContext") or {},
            }
            if task_type == "learning_feedback":
                managed_params["sourceTaskId"] = str(
                    params.get("sourceTaskId") or params.get("taskId") or ""
                ).strip()
            return xiaozhi_run_platform_agent(
                task_type,
                topic,
                context,
                user_id,
                on_stage=specialist_progress,
                params=managed_params,
            )

        retryable = task_type in {"learning_path", "learning_path_stage", "personalized_resources", "ppt", "document", "mindmap", "video", "animation", "mcu", "smart_tutor", "effect_assessment", "knowledge_base"}
        result = xiaozhi_run_orchestrated(
            task_type,
            topic,
            params,
            user_id,
            specialist,
            context=context,
            task_id=task_id,
            on_event=on_event,
            max_retries=1 if retryable else 0,
        )
        result.setdefault("topic", topic)
        result["progress"] = 100
        trace = result.get("orchestration") if isinstance(result.get("orchestration"), dict) else {}
        result["logs"] = [
            {
                "time": event.get("time") or now_iso(),
                "stage": event.get("stage") or "progress",
                "message": event.get("message") or "",
                "progress": event.get("progress") or 0,
            }
            for event in (trace.get("events") or [])[-40:]
            if isinstance(event, dict)
        ] or logs[-40:]
        result["agentRuns"] = trace.get("agentRuns") or list(agent_runs.values())
        route = result.get("route") or _resource_agent_route(task_type, topic, params)
        if str(trace.get("status") or "") != "complete":
            review = trace.get("review") if isinstance(trace.get("review"), dict) else {}
            issues = [str(item) for item in (review.get("issues") or []) if str(item).strip()]
            failure_message = "；".join(issues[:5]) or "智能体产物未通过结构或安全审核"
            result["currentStage"] = "quality_review_failed"
            result["qualityError"] = failure_message
            result.pop(XIAOZHI_LEARNING_PATH_CANDIDATE_FIELD, None)
            result = merge_ppt_task_state(
                result,
                status="failed",
                stage="quality_review_failed",
                message=failure_message,
                progress=100,
                error_message=failure_message,
            )
            xiaozhi_update_task(
                task_id,
                status="failed",
                result_json=result,
                error=failure_message,
                route=xiaozhi_route_with_task(route, task_id),
            )
            return
        _persist_xiaozhi_reviewed_learning_path_candidate(task_type, int(user_id), result)
        result = merge_ppt_task_state(
            result,
            status="complete",
            stage="complete",
            message=str(result.get("message") or "PPT 生成已完成"),
            progress=100,
        )
        xiaozhi_update_task(task_id, status="complete", result_json=result, route=xiaozhi_route_with_task(route, task_id))
    except SkillReviewError as exc:
        result = dict(exc.result)
        result.pop(XIAOZHI_LEARNING_PATH_CANDIDATE_FIELD, None)
        trace = result.get("orchestration") if isinstance(result.get("orchestration"), dict) else {}
        result.setdefault("topic", topic)
        result["progress"] = 100
        result["currentStage"] = "quality_review_failed"
        result["qualityError"] = str(exc)
        result["logs"] = [
            {
                "time": event.get("time") or now_iso(),
                "stage": event.get("stage") or "progress",
                "message": event.get("message") or "",
                "progress": event.get("progress") or 0,
            }
            for event in (trace.get("events") or [])[-40:]
            if isinstance(event, dict)
        ] or logs[-40:]
        result["agentRuns"] = trace.get("agentRuns") or list(agent_runs.values())
        route = result.get("route") or _resource_agent_route(task_type, topic, params)
        result = merge_ppt_task_state(
            result,
            status="failed",
            stage="quality_review_failed",
            message=str(exc),
            progress=100,
            error_message=str(exc),
        )
        xiaozhi_update_task(
            task_id,
            status="failed",
            result_json=result,
            error=str(exc),
            route=xiaozhi_route_with_task(route, task_id),
        )
    except Exception as exc:
        error_result = {
            "message": str(exc) or "任务执行失败",
            "topic": topic,
            "progress": 100,
            "currentStage": "error",
            "logs": logs[-40:] + [{"time": now_iso(), "stage": "error", "message": str(exc), "progress": 100}],
            "agentRuns": list(agent_runs.values()),
            "architecture": XIAOZHI_ARCHITECTURE,
            "rootAgent": XIAOZHI_MASTER_AGENT_ID,
        }
        error_result = merge_ppt_task_state(
            error_result,
            status="failed",
            stage="error",
            message=str(exc) or "PPT 生成失败",
            progress=100,
            error_message=str(exc),
        )
        update_fields = {"status": "failed", "result_json": error_result, "error": str(exc)}
        if task_type == "ppt" and str(error_result.get("route") or ""):
            update_fields["route"] = str(error_result["route"])
        xiaozhi_update_task(task_id, **update_fields)


def _bind_service_function(function):
    @wraps(function)
    def bound(*args, **kwargs):
        _sync_dependencies()
        return function(*args, **kwargs)

    return bound


for _function_name in EXPORTED_FUNCTIONS:
    globals()[_function_name] = _bind_service_function(globals()[_function_name])

del _function_name
