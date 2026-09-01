"""Xiaozhi collaboration, MCP, history, and runtime-setting HTTP routes."""

from __future__ import annotations

from typing import Callable

from flask import Blueprint


class _DependencyProxy:
    def __init__(self, provider: Callable[[str], object]):
        self._provider = provider

    def __getattr__(self, name: str):
        return self._provider(name)


blueprint = Blueprint("xiaozhi_api", __name__)
dependencies: _DependencyProxy


def create_xiaozhi_api_blueprint(provider: Callable[[str], object]) -> Blueprint:
    global dependencies
    dependencies = _DependencyProxy(provider)
    return blueprint


@blueprint.post("/api/learning-activity/pulse")
def learning_activity_pulse():
    user, error_response = dependencies.xiaozhi_current_user()
    if error_response:
        return error_response
    payload = dependencies.request.get_json(silent=True) or {}
    try:
        with dependencies.auth_db() as conn:
            activity = dependencies.record_learning_activity_pulse(conn, int(user["id"]), payload)
    except ValueError as exc:
        return dependencies.jsonify({"code": 400, "msg": str(exc)}), 400
    return dependencies.jsonify({"code": 0, "data": {"activity": activity}})


@blueprint.post("/api/xiaozhi/events")
def xiaozhi_events():
    user, error_response = dependencies.xiaozhi_current_user()
    if error_response:
        return error_response
    payload = dependencies.request.get_json(silent=True) or {}
    dependencies.xiaozhi_insert_event(
        user["id"],
        str(payload.get("eventType") or "event")[:80],
        str(payload.get("route") or "")[:240],
        str(payload.get("title") or "")[:160],
        payload.get("payload") if isinstance(payload.get("payload"), dict) else {},
    )
    return dependencies.jsonify({"code": 0, "msg": "已记录"})


@blueprint.get("/api/xiaozhi/history")
def xiaozhi_history():
    user, error_response = dependencies.xiaozhi_current_user()
    if error_response:
        return error_response
    task_limit = max(1, min(100, dependencies.request.args.get("taskLimit", default=20, type=int) or 20))
    latest_context = dependencies.xiaozhi_latest_context(int(user["id"]))
    profile_report_id = int(
        latest_context.get("profileReportId")
        or (latest_context.get("profile") or {}).get("id")
        or 0
    )
    agent_conversation = dependencies.xiaozhi_profile_agent_context(
        int(user["id"]),
        profile_report_id,
    )
    task_rows = []
    if profile_report_id > 0:
        with dependencies.auth_db() as conn:
            task_rows = conn.execute(
                """
                SELECT task_id, task_type, title, prompt, status, route, result_json, error, created_at, updated_at
                FROM xiaozhi_tasks
                WHERE user_id = ? AND profile_report_id = ?
                ORDER BY id DESC LIMIT ?
                """,
                (user["id"], profile_report_id, task_limit),
            ).fetchall()
    with dependencies.auth_db() as conn:
        message_rows = conn.execute(
            """
            SELECT role, content, intent_json, cards_json, created_at
            FROM xiaozhi_messages
            WHERE user_id = ? AND profile_report_id = ?
            ORDER BY id DESC LIMIT 100
            """,
            (int(user["id"]), profile_report_id),
        ).fetchall()
    messages = []
    for row in reversed(message_rows):
        intent = dependencies.parse_json_safely(row["intent_json"], {})
        cards = dependencies.parse_json_safely(row["cards_json"], [])
        messages.append({
            "role": str(row["role"] or "assistant"),
            "content": str(row["content"] or ""),
            "intent": intent,
            "attachments": intent.get("attachments") if isinstance(intent.get("attachments"), list) else [],
            "cards": cards if isinstance(cards, list) else [],
            "targetAgent": intent.get("targetAgent") if isinstance(intent.get("targetAgent"), dict) else {},
            "createdAt": str(row["created_at"] or ""),
        })
    tasks = [dependencies.xiaozhi_task_from_row(row) for row in task_rows]
    orchestration_runs = dependencies.xiaozhi_recent_orchestration_runs(
        int(user["id"]),
        limit=20,
        profile_report_id=profile_report_id,
    )
    return dependencies.jsonify({
        "code": 0,
        "data": {
            "messages": messages,
            "tasks": tasks,
            "orchestrationRuns": orchestration_runs,
            "agentConversation": agent_conversation,
            "profileReportId": profile_report_id,
        },
    })


@blueprint.get("/api/xiaozhi/tasks/<task_id>")
def xiaozhi_task_detail(task_id: str):
    user, error_response = dependencies.xiaozhi_current_user()
    if error_response:
        return error_response
    with dependencies.auth_db() as conn:
        row = conn.execute(
            """
            SELECT task_id, profile_report_id, task_type, title, prompt, status, route,
                   result_json, error, created_at, updated_at
            FROM xiaozhi_tasks
            WHERE user_id = ? AND task_id = ?
            LIMIT 1
            """,
            (user["id"], task_id),
        ).fetchone()
        active_profile = dependencies.active_profile_for_user(conn, int(user["id"]))
    if not row:
        return dependencies.jsonify({"code": 404, "msg": "未找到嵌小智任务"}), 404
    return dependencies.jsonify({
        "code": 0,
        "data": {
            "task": dependencies.xiaozhi_task_from_row(row),
            "profileReportId": int(row["profile_report_id"] or 0),
            "activeProfileReportId": int(active_profile.get("id") or 0) if active_profile else 0,
            "orchestrationRuns": dependencies.xiaozhi_recent_orchestration_runs(
                int(user["id"]),
                limit=10,
                task_id=task_id,
            ),
        },
    })


@blueprint.get("/api/personalized-resources/task-covers/<task_id>.png")
def personalized_resource_task_cover(task_id: str):
    user, error_response = dependencies.xiaozhi_current_user()
    if error_response:
        return error_response
    with dependencies.auth_db() as conn:
        row = conn.execute(
            """
            SELECT task_id, profile_report_id, task_type, title, prompt, status, route,
                   result_json, error, created_at, updated_at
            FROM xiaozhi_tasks
            WHERE user_id = ? AND task_id = ?
            LIMIT 1
            """,
            (int(user["id"]), str(task_id or "")),
        ).fetchone()
    if not row:
        return dependencies.jsonify({"code": 404, "msg": "未找到资源任务"}), 404

    cover_path, fingerprint = dependencies.render_resource_task_cover(
        dependencies.xiaozhi_task_from_row(row),
        dependencies.RESOURCE_COVER_CACHE_DIR,
    )
    response = dependencies.send_file(
        cover_path,
        mimetype="image/png",
        conditional=True,
        etag=fingerprint,
        max_age=3600,
    )
    response.cache_control.public = False
    response.cache_control.private = True
    return response


def _parse_profile_datetime(value: object) -> dependencies.datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return dependencies.datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def xiaozhi_find_profile(profiles: list[dict], target_query: str) -> dict:
    if not profiles:
        return {}
    query = str(target_query or "").strip()
    lowered = query.lower()
    id_match = dependencies.re.search(r"(?:report\s*id|画像\s*(?:id|编号)|#)\s*[:：]?\s*(\d+)", query, flags=dependencies.re.I)
    if id_match:
        report_id = int(id_match.group(1))
        return next((item for item in profiles if int(item.get("id") or 0) == report_id), {})

    version_match = dependencies.re.search(r"(?:版本\s*|v)\s*(\d+)", lowered, flags=dependencies.re.I)
    if version_match:
        version = int(version_match.group(1))
        matched = [item for item in profiles if int(item.get("version") or 0) == version]
        if matched:
            return matched[0]

    if "上个月" in query:
        now = dependencies.datetime.now()
        month_start = dependencies.datetime(now.year, now.month, 1)
        previous_month_end = month_start - dependencies.timedelta(days=1)
        matched = [
            item
            for item in profiles
            if (
                (created := _parse_profile_datetime(item.get("createdAt") or item.get("timestamp")))
                and created.year == previous_month_end.year
                and created.month == previous_month_end.month
            )
        ]
        if matched:
            return matched[0]

    if any(word in query for word in ["上一份", "上一个", "之前的"]):
        active_index = next((index for index, item in enumerate(profiles) if item.get("isActive")), -1)
        if 0 <= active_index + 1 < len(profiles):
            return profiles[active_index + 1]
        if len(profiles) > 1:
            return profiles[1]
    if any(word in query for word in ["最新", "最近"]):
        return profiles[0]
    if any(word in query for word in ["最早", "第一份"]):
        return profiles[-1]

    for item in profiles:
        name = str(item.get("profileName") or "").strip()
        if name and name in query:
            return item
    return {}


def xiaozhi_execute_profile_management(user_id: int, action: str, target_query: str = "") -> dict:
    normalized_action = str(action or "").strip()
    with dependencies.auth_db() as conn:
        profiles, state = dependencies.list_profiles_for_user(conn, int(user_id))
        if normalized_action == "list":
            summary = "；".join(
                f"{item.get('profileName')} v{item.get('version')}{'（当前）' if item.get('isActive') else ''}"
                for item in profiles[:6]
            )
            return {
                "action": "list",
                "profiles": profiles,
                "activeReportId": state["activeReportId"],
                "reply": f"你目前保留了 {len(profiles)} 份画像。{summary or '还没有生成画像报告。'}",
            }
        if normalized_action == "activate":
            target = xiaozhi_find_profile(profiles, target_query)
            if not target:
                return {
                    "action": "activate",
                    "profiles": profiles,
                    "activeReportId": state["activeReportId"],
                    "reply": "我没有找到你指定的画像。可以说“列出画像”，或指定画像名称、版本号、报告 ID。",
                    "error": "profile_not_found",
                }
            profile = dependencies.activate_profile(conn, int(user_id), int(target["id"]), timestamp=dependencies.now_iso())
            return {
                "action": "activate",
                "profile": profile,
                "activeReportId": profile["id"],
                "reply": f"已切换到“{profile['profileName']}”v{profile['version']}，后续路径、资源和评估都会使用这份画像。",
            }
        if normalized_action == "reset":
            state = dependencies.reset_profile_state(conn, int(user_id), timestamp=dependencies.now_iso())
            historical_count = len(profiles)
        else:
            return {
                "action": normalized_action,
                "reply": "暂不支持这个画像管理动作。",
                "error": "unsupported_profile_action",
            }

    dialogue_reset = {}
    try:
        dialogue_reset = dependencies.clear_persisted_profile_dialogue(str(user_id))
    except Exception as exc:
        dependencies.app.logger.warning("failed to clear profile dialogue through XiaoZhi: %s", exc)
    return {
        "action": "reset",
        "activeReportId": None,
        "historicalCount": historical_count,
        "state": state,
        "dialogueReset": dialogue_reset,
        "reply": f"当前画像已重置，{historical_count} 份历史画像仍然保留。完成新一轮采集后，新报告会自动成为当前画像。",
    }


@blueprint.post("/api/xiaozhi/chat")
def xiaozhi_chat():
    user, error_response = dependencies.xiaozhi_current_user()
    if error_response:
        return error_response
    payload = dependencies.request.get_json(silent=True) or {}
    message = str(payload.get("message") or "").strip()
    public_attachments, attachment_rows = dependencies._resolve_multimodal_inputs(int(user["id"]), payload.get("attachments"))
    route = str(payload.get("route") or "")
    if not message and not attachment_rows:
        return dependencies.jsonify({"code": 400, "msg": "请输入内容"}), 400
    message = message or "请分析我上传的学习材料。"
    target_agent, routed_message, has_agent_mention = dependencies.xiaozhi_parse_agent_mention(message)
    if dependencies.re.search(r"(^|\s)@([^\s，,：:]+)", message) and not has_agent_mention:
        return dependencies.jsonify({"code": 400, "msg": "该智能体不可用，请从群聊的 @ 列表中选择"}), 400
    requested_profile_id = payload.get("profileReportId")
    context = dependencies.xiaozhi_latest_context(user["id"], memory_query=message)
    profile_report_id = int(
        context.get("profileReportId")
        or (context.get("profile") or {}).get("id")
        or 0
    )
    if requested_profile_id not in (None, ""):
        try:
            requested_profile_id = int(requested_profile_id)
        except (TypeError, ValueError):
            return dependencies.jsonify({"code": 400, "msg": "profileReportId 必须是整数"}), 400
        if requested_profile_id != profile_report_id:
            return dependencies.jsonify({
                "code": 409,
                "msg": "学习画像已切换，请在当前画像中重新发送",
                "data": {"profileReportId": profile_report_id},
            }), 409
    routed_message = routed_message or f"请根据当前画像执行{target_agent.get('name') or '学习任务'}的工作"
    agent_message = dependencies._message_with_multimodal_context(routed_message, attachment_rows)
    user_message_id = dependencies.xiaozhi_insert_message(
        user["id"],
        "user",
        message,
        intent={"attachments": public_attachments, "targetAgent": target_agent},
        profile_report_id=profile_report_id,
    )
    memory_source_key = str(user_message_id)
    with dependencies.auth_db() as conn:
        dependencies.knowledge_growth.record_conversation_memory(
            conn,
            int(user["id"]),
            source_type="xiaozhi",
            source_key=memory_source_key,
            route=route,
            user_message=message,
            metadata={"attachments": public_attachments},
            timestamp=dependencies.now_iso(),
        )
    dependencies.xiaozhi_insert_event(
        user["id"],
        "assistant_message",
        route,
        "用户向嵌小智提问",
        {"message": message, "attachmentIds": [item["id"] for item in public_attachments]},
    )
    if profile_report_id > 0:
        try:
            dependencies.ProfileAgentContextStore(dependencies.AUTH_DB_PATH).append(
                int(user["id"]),
                profile_report_id,
                agent_id="learner",
                agent_name=str(user["display_name"] or user["username"] or "学习者"),
                message_type="user_message",
                status="complete",
                content=message,
                payload={
                    "route": route,
                    "attachments": public_attachments,
                    "targetAgent": target_agent,
                },
                dedupe_key=f"chat:user:{user_message_id}",
            )
        except Exception as exc:
            dependencies.app.logger.warning("failed to append learner group-chat message: %s", exc)
    target_task_type = str(target_agent.get("taskType") or "")
    if has_agent_mention and target_task_type:
        if dependencies.xiaozhi_has_explicit_task_command(routed_message):
            intent = {
                "intent": "update_profile" if target_task_type == "profile_update" else "generate_resource",
                "resourceType": target_task_type,
                "resourceTypes": [target_task_type],
                "topic": routed_message,
                "reply": f"已由{target_agent['name']}接收任务，执行进度会继续写入当前画像群聊。",
                "source": "explicit-agent-mention",
                "routingSource": "agent-mention",
            }
        else:
            try:
                expert_reply = dependencies.xiaozhi_agent_chat_reply(
                    int(user["id"]),
                    target_agent,
                    routed_message,
                    context,
                    dependencies.xiaozhi_runtime_setting_overrides(int(user["id"])),
                )
            except Exception as exc:
                dependencies.app.logger.warning("named agent chat failed for %s: %s", target_agent.get("id"), exc)
                return dependencies.jsonify({
                    "code": 502,
                    "msg": f"{target_agent['name']}大模型不可用，请检查模型服务后重试",
                    "data": {
                        "targetAgent": target_agent,
                        "profileReportId": profile_report_id,
                        "error": dependencies.public_llm_error(exc),
                    },
                }), 502
            intent = {
                "intent": "chat",
                "resourceType": "none",
                "resourceTypes": [],
                "topic": routed_message,
                "reply": expert_reply,
                "source": "explicit-agent-conversation",
                "routingSource": "agent-mention",
            }
    else:
        intent = dependencies.xiaozhi_detect_intent(
            agent_message,
            context,
            dependencies.xiaozhi_runtime_setting_overrides(int(user["id"])),
        )
    intent["targetAgent"] = target_agent
    if intent.get("intent") == "chat" and intent.get("source") == "fallback":
        return dependencies.jsonify({
            "code": 502,
            "msg": "嵌小智智能体未返回可用回复，请检查模型服务后重试",
            "data": {"intent": intent},
        }), 502
    intent["attachments"] = public_attachments
    cards = []
    if intent["intent"] == "profile_management":
        profile_action = str(intent.get("profileAction") or "list")
        if profile_action == "refresh":
            active_report_id = int(context.get("profileReportId") or 0)
            title_topic = intent.get("topic") or message
            route_to = dependencies._resource_agent_route("profile_update", dependencies._resource_agent_topic(title_topic), {})
            title = f"{title_topic[:32]} · {dependencies.XIAOZHI_RESOURCE_LABELS.get('profile_update', '学习画像')}"
            task_id = dependencies.xiaozhi_create_task(user["id"], "profile_update", title, agent_message, route_to)
            cards.append(dependencies.xiaozhi_build_card(task_id, "profile_update", title, route_to))
            dependencies.threading.Thread(
                target=dependencies.xiaozhi_run_resource_task,
                args=(
                    task_id,
                    user["id"],
                    "profile_update",
                    title_topic,
                    {
                        "parentReportId": active_report_id,
                        "refreshInstruction": agent_message,
                        "attachmentIds": [item["id"] for item in public_attachments],
                        "initialProfile": not bool(active_report_id),
                    },
                ),
                daemon=True,
            ).start()
            intent["reply"] = (
                "我已汇总现有对话和学习证据，开始生成第一份画像。"
                if not active_report_id
                else "我已基于当前画像和最近学习证据启动更新；完成后仍保存到当前画像。"
            )
        else:
            title_topic = intent.get("topic") or message
            task_params = {
                "action": profile_action,
                "targetQuery": str(intent.get("targetQuery") or message),
                "attachmentIds": [item["id"] for item in public_attachments],
            }
            route_to = dependencies._resource_agent_route("profile_management", dependencies._resource_agent_topic(title_topic), task_params)
            title = f"{title_topic[:32]} · {dependencies.XIAOZHI_RESOURCE_LABELS.get('profile_management', '学习画像管理')}"
            task_id = dependencies.xiaozhi_create_task(user["id"], "profile_management", title, agent_message, route_to)
            cards.append(dependencies.xiaozhi_build_card(task_id, "profile_management", title, route_to))
            dependencies.threading.Thread(
                target=dependencies.xiaozhi_run_resource_task,
                args=(task_id, user["id"], "profile_management", title_topic, task_params),
                daemon=True,
            ).start()
            intent["reply"] = intent.get("reply") or "画像管理任务已交给嵌小智执行。"
    elif intent["intent"] in {"generate_resource", "update_profile"}:
        if intent["intent"] == "generate_resource" and isinstance(intent.get("resourceTypes"), list) and intent.get("resourceTypes"):
            task_types = [task_type for task_type in intent["resourceTypes"] if task_type in dependencies.XIAOZHI_RESOURCE_ROUTES]
        else:
            task_types = [intent["resourceType"] if intent["resourceType"] in dependencies.XIAOZHI_RESOURCE_ROUTES else "profile_update"]
        task_types = list(dict.fromkeys(task_types)) or ["profile_update"]
        if not int(context.get("profileReportId") or 0):
            blocked_types = [task_type for task_type in task_types if task_type in dependencies.PROFILE_DRIVEN_TASK_TYPES]
            task_types = [task_type for task_type in task_types if task_type not in dependencies.PROFILE_DRIVEN_TASK_TYPES]
            if blocked_types:
                guidance = "请先在学习画像中通过多轮对话补齐十个维度并生成报告。"
                intent["reply"] = (
                    f"当前没有激活画像，暂不能执行画像驱动的学习与资源任务。{guidance}"
                    if not task_types
                    else f"不依赖画像的任务已创建；其余个性化任务暂未执行。{guidance}"
                )
        title_topic = intent.get("topic") or message
        for task_type in task_types:
            task_params = {
                "attachmentIds": [item["id"] for item in public_attachments],
                "profileReportId": profile_report_id,
            }
            task_topic = title_topic
            if task_type == "knowledge_base":
                task_params = {
                    "action": intent.get("knowledgeAction") or "list",
                    "collectionName": intent.get("collectionName") or "",
                    "query": intent.get("knowledgeQuery") or "",
                }
            elif task_type == "learning_feedback":
                target = dependencies.xiaozhi_feedback_target(context, route)
                task_topic = target.get("topic") or "当前学习资源"
                task_params = {
                    **target,
                    "sourceTaskId": str(target.get("taskId") or "").strip(),
                    "outcome": intent.get("feedbackOutcome") or "completed",
                    "difficulty": intent.get("feedbackDifficulty") or "appropriate",
                    "helpful": intent.get("feedbackHelpful"),
                    "note": agent_message,
                }
                task_params.pop("taskId", None)
            elif task_type == "smart_tutor":
                task_params = dependencies.xiaozhi_smart_tutor_request(agent_message, route)
                task_params["attachmentIds"] = [item["id"] for item in public_attachments]
                task_topic = task_params["question"]
            if public_attachments:
                task_params["attachmentIds"] = [item["id"] for item in public_attachments]
            if task_type == "mcu":
                task_params = dependencies.resolve_mcu_agent_params_for_user(int(user["id"]), task_params, task_topic)
            if task_type == "generated_video":
                task = dependencies.xiaozhi_create_resource_agent_task(
                    int(user["id"]),
                    task_type,
                    task_topic,
                    task_params,
                    prompt=agent_message,
                )
                cards.append(
                    dependencies.xiaozhi_build_card(
                        str(task.get("taskId") or ""),
                        task_type,
                        str(task.get("title") or task_topic),
                        str(task.get("route") or ""),
                        status=str(task.get("status") or "queued"),
                        result=task.get("result") if isinstance(task.get("result"), dict) else {},
                    )
                )
                continue
            route_to = dependencies._resource_agent_route(task_type, dependencies._resource_agent_topic(task_topic), task_params)
            title = f"{task_topic[:32]} · {dependencies.XIAOZHI_RESOURCE_LABELS.get(task_type, '学习任务')}"
            task_id = dependencies.xiaozhi_create_task(user["id"], task_type, title, agent_message, route_to)
            cards.append(dependencies.xiaozhi_build_card(task_id, task_type, title, route_to))
            dependencies.threading.Thread(
                target=dependencies.xiaozhi_run_resource_task,
                args=(task_id, user["id"], task_type, task_topic, task_params),
                daemon=True,
            ).start()
        if len(cards) > 1 and "resourceTypes" in intent:
            intent["reply"] = intent.get("reply") or f"我已创建 {len(cards)} 个资源任务，会在悬浮窗里分别显示小窗口预览。"
    assistant_reply = intent.get("reply") or ""
    assistant_message_id = dependencies.xiaozhi_insert_message(
        user["id"],
        "assistant",
        assistant_reply,
        intent=intent,
        cards=cards,
        profile_report_id=profile_report_id,
    )
    agent_conversation = None
    if profile_report_id > 0:
        try:
            profile_store = dependencies.ProfileAgentContextStore(dependencies.AUTH_DB_PATH)
            if assistant_reply:
                profile_store.append(
                    int(user["id"]),
                    profile_report_id,
                    agent_id=str(target_agent.get("id") or dependencies.XIAOZHI_MASTER_AGENT_ID),
                    agent_name=str(target_agent.get("name") or "嵌小智"),
                    message_type="supervisor_reply",
                    status="complete",
                    content=assistant_reply,
                    payload={
                        "intent": intent.get("intent") or "chat",
                        "topic": intent.get("topic") or "",
                        "cards": cards,
                        "targetAgent": target_agent,
                    },
                    dedupe_key=f"chat:assistant:{assistant_message_id}",
                )
            for card in cards:
                card_task_id = str(card.get("taskId") or "")
                card_type = str(card.get("type") or "")
                card_title = str(card.get("title") or "学习资源任务")
                profile_store.append(
                    int(user["id"]),
                    profile_report_id,
                    agent_id=dependencies.XIAOZHI_MASTER_AGENT_ID,
                    agent_name="嵌小智总控智能体",
                    message_type="task_created",
                    status=str(card.get("status") or "queued"),
                    content=f"已派发{dependencies.XIAOZHI_RESOURCE_LABELS.get(card_type, '学习资源')}任务：{card_title}",
                    payload={
                        "taskId": card_task_id,
                        "resourceType": card_type,
                        "title": card_title,
                        "route": str(card.get("route") or ""),
                        "progress": 0,
                    },
                    task_id=card_task_id,
                    dedupe_key=f"chat:task-created:{card_task_id}",
                )
            agent_conversation = profile_store.context(int(user["id"]), profile_report_id)
        except Exception as exc:
            dependencies.app.logger.warning("failed to append supervisor group-chat reply: %s", exc)
    with dependencies.auth_db() as conn:
        dependencies.knowledge_growth.record_conversation_memory(
            conn,
            int(user["id"]),
            source_type="xiaozhi",
            source_key=memory_source_key,
            route=route,
            user_message=message,
            assistant_message=assistant_reply,
            metadata={
                "assistantMessageId": assistant_message_id,
                "intent": intent.get("intent") or "chat",
                "topic": intent.get("topic") or "",
                "resourceTypes": intent.get("resourceTypes") or [],
                "attachments": public_attachments,
            },
            timestamp=dependencies.now_iso(),
        )
    return dependencies.jsonify({
        "code": 0,
        "data": {
            "reply": intent.get("reply") or "",
            "intent": intent,
            "cards": cards,
            "attachments": public_attachments,
            "agentConversation": agent_conversation,
            "targetAgent": target_agent,
            "profileReportId": profile_report_id,
        },
    })


@blueprint.post("/api/xiaozhi/chat-stream")
def xiaozhi_chat_stream():
    @dependencies.stream_with_context
    def generate_events():
        yield dependencies._sse_event("start", {
            "agent": dependencies.XIAOZHI_MASTER_AGENT_ID,
            "stage": "start",
            "message": "嵌小智总控智能体已启动",
        })
        try:
            yield dependencies._sse_event("progress", {
                "agent": dependencies.XIAOZHI_MASTER_AGENT_ID,
                "stage": "route_intent",
                "message": "正在调用嵌小智智能体识别意图并调度任务",
            })
            raw_response = xiaozhi_chat()
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
                    "agent": dependencies.XIAOZHI_MASTER_AGENT_ID,
                    "stage": "failed",
                    "message": payload.get("msg") or payload.get("message") or "嵌小智智能体调用失败",
                    "data": payload.get("data") or {},
                })
                yield dependencies._sse_event("done", {
                    "agent": dependencies.XIAOZHI_MASTER_AGENT_ID,
                    "stage": "done",
                    "status": "failed",
                })
                return
            data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
            intent = data.get("intent") if isinstance(data.get("intent"), dict) else {}
            reply = str(data.get("reply") or "")
            if intent.get("intent") == "chat" and intent.get("source") == "fallback":
                yield dependencies._sse_event("error", {
                    "agent": dependencies.XIAOZHI_MASTER_AGENT_ID,
                    "stage": "llm_required",
                    "message": "嵌小智聊天必须调用真实智能体，已禁止本地兜底回复",
                    "data": intent,
                })
                yield dependencies._sse_event("done", {
                    "agent": dependencies.XIAOZHI_MASTER_AGENT_ID,
                    "stage": "done",
                    "status": "failed",
                })
                return
            yield dependencies._sse_event("progress", {
                "agent": dependencies.XIAOZHI_MASTER_AGENT_ID,
                "stage": "stream_reply",
                "message": "嵌小智智能体已返回，正在流式输出",
                "intent": intent.get("intent") or "",
                "source": intent.get("source") or "",
                "routingSource": intent.get("routingSource") or "",
            })
            for index in range(0, len(reply), 4):
                yield dependencies._sse_event("delta", {
                    "agent": dependencies.XIAOZHI_MASTER_AGENT_ID,
                    "text": reply[index:index + 4],
                    "source": intent.get("source") or "",
                })
                dependencies.time.sleep(0.035)
            yield dependencies._sse_event("result", {
                "agent": dependencies.XIAOZHI_MASTER_AGENT_ID,
                "stage": "complete",
                "message": "嵌小智本轮回复完成",
                "data": data,
            })
            yield dependencies._sse_event("done", {
                "agent": dependencies.XIAOZHI_MASTER_AGENT_ID,
                "stage": "done",
                "message": "嵌小智对话流已结束",
            })
        except Exception as exc:
            dependencies.app.logger.exception("xiaozhi chat stream failed")
            yield dependencies._sse_event("error", {
                "agent": dependencies.XIAOZHI_MASTER_AGENT_ID,
                "stage": "failed",
                "message": "嵌小智智能体调用失败，请检查模型服务后重试。",
                "error": str(exc),
            })
            yield dependencies._sse_event("done", {
                "agent": dependencies.XIAOZHI_MASTER_AGENT_ID,
                "stage": "done",
                "status": "failed",
            })

    return dependencies.Response(generate_events(), mimetype="text/event-stream")


@blueprint.post("/api/xiaozhi/tutor")
def xiaozhi_tutor():
    user, error_response = dependencies.xiaozhi_current_user()
    if error_response:
        return error_response
    payload = dependencies.request.get_json(silent=True) or {}
    question = str(payload.get("question") or payload.get("message") or "").strip()
    if not question:
        return dependencies.jsonify({"code": 400, "msg": "请输入需要辅导的问题"}), 400
    result = dependencies.xiaozhi_run_orchestrated(
        "smart_tutor",
        question,
        payload,
        int(user["id"]),
        lambda managed_payload, _progress: dependencies.xiaozhi_smart_tutor_result(managed_payload),
        max_retries=1,
    )
    return dependencies.jsonify({"code": 0, "msg": "ok", "data": result})


@blueprint.get("/api/learning-feedback")
def learning_feedback_list():
    user = dependencies.g.get("current_user")
    if not user:
        return dependencies.jsonify({"code": 401, "msg": "未登录"}), 401
    task_id = str(dependencies.request.args.get("taskId") or "").strip()
    cache_key = str(dependencies.request.args.get("cacheKey") or "").strip()
    try:
        limit = max(1, min(200, int(dependencies.request.args.get("limit") or 40)))
    except (TypeError, ValueError):
        limit = 40
    with dependencies.auth_db() as conn:
        feedbacks = dependencies.list_learning_feedback_records(
            conn,
            int(user["id"]),
            task_id=task_id,
            cache_key=cache_key,
            limit=limit,
        )
    return dependencies.jsonify({"code": 0, "data": {"feedbacks": feedbacks}})


@blueprint.post("/api/xiaozhi/feedback")
def xiaozhi_learning_feedback():
    user, error_response = dependencies.xiaozhi_current_user()
    if error_response:
        return error_response
    payload = dependencies.request.get_json(silent=True) or {}
    topic = str(payload.get("topic") or payload.get("title") or "当前学习资源").strip()
    payload["topic"] = topic
    payload["outcome"] = str(payload.get("outcome") or "completed").strip().lower()
    context = dependencies.xiaozhi_latest_context(int(user["id"]))
    try:
        result = dependencies.xiaozhi_run_orchestrated(
            "learning_feedback",
            topic,
            payload,
            int(user["id"]),
            lambda managed_payload, progress: dependencies.xiaozhi_run_platform_agent(
                "learning_feedback",
                topic,
                context,
                int(user["id"]),
                on_stage=progress,
                params=managed_payload,
            ),
            context=context,
            max_retries=0,
        )
    except dependencies.LearningProfileRequiredError as exc:
        return dependencies.jsonify({"code": 409, "msg": str(exc)}), 409
    except LookupError as exc:
        return dependencies.jsonify({"code": 404, "msg": str(exc)}), 404
    except ValueError as exc:
        return dependencies.jsonify({"code": 400, "msg": str(exc)}), 400
    return dependencies.jsonify({"code": 0, "msg": "学习反馈已记录", "data": result})


@blueprint.post("/api/xiaozhi/effect-assessment")
def xiaozhi_effect_assessment():
    user, error_response = dependencies.xiaozhi_current_user()
    if error_response:
        return error_response
    payload = dependencies.request.get_json(silent=True) or {}
    result = dependencies.xiaozhi_run_orchestrated(
        "effect_assessment",
        str(payload.get("topic") or payload.get("title") or "综合学习效果评估"),
        payload,
        int(user["id"]),
        lambda managed_payload, _progress: dependencies.xiaozhi_effect_assessment_result(managed_payload),
        max_retries=1,
    )
    return dependencies.jsonify({"code": 0, "msg": "ok", "data": result})


@blueprint.get("/api/xiaozhi/harness")
def xiaozhi_harness_status():
    user, error_response = dependencies.xiaozhi_current_user()
    if error_response:
        return error_response
    return dependencies.jsonify({
        "code": 0,
        "msg": "ok",
        "data": {
            **dependencies.DEFAULT_AGENT_HARNESS.status(),
            "modelRuntime": dependencies.llm_runtime_for_user(int(user["id"])),
            "recentRuns": dependencies.xiaozhi_recent_orchestration_runs(int(user["id"]), limit=12),
        },
    })


@blueprint.get("/api/xiaozhi/runtime-settings")
def xiaozhi_runtime_settings_get():
    user, error_response = dependencies.xiaozhi_current_user()
    if error_response:
        return error_response
    return dependencies.jsonify({
        "code": 0,
        "msg": "ok",
        "data": {
            "settings": dependencies.xiaozhi_runtime_settings_for_user(int(user["id"])),
            "protocols": [
                {"value": "openai", "label": "讯飞 OpenAI 兼容接口"},
                {"value": "anthropic", "label": "讯飞 Anthropic 兼容接口"},
            ],
            "allowedHosts": [
                item.strip()
                for item in dependencies.get_setting(
                    "AGENT_RUNTIME_ALLOWED_HOSTS",
                    "maas-coding-api.cn-huabei-1.xf-yun.com,api.deepseek.com,deepseek.com,localhost,127.0.0.1",
                ).split(",")
                if item.strip()
            ],
            "usesPlatformCredential": True,
        },
    })


@blueprint.put("/api/xiaozhi/runtime-settings")
def xiaozhi_runtime_settings_save():
    user, error_response = dependencies.xiaozhi_current_user()
    if error_response:
        return error_response
    payload = dependencies.request.get_json(silent=True) or {}
    try:
        settings = dependencies.validate_xiaozhi_runtime_settings(payload)
    except ValueError as exc:
        return dependencies.jsonify({"code": 400, "msg": str(exc)}), 400
    connection = None
    if settings["enabled"]:
        try:
            connection = dependencies.test_xiaozhi_runtime_connection(settings)
        except dependencies.SkillReviewError as exc:
            dependencies.app.logger.warning("runtime model connection review failed: %s", exc)
            return dependencies.jsonify({
                "code": 422,
                "msg": "模型连接未通过安全审核，配置未保存",
                "data": {"ok": False, "error": str(exc)[:1200]},
            }), 422
        except Exception as exc:
            return dependencies.jsonify({
                "code": 502,
                "msg": "模型连接测试失败，配置未保存",
                "data": {
                    "ok": False,
                    "error": str(exc)[:1200],
                },
            }), 502
    timestamp = dependencies.now_iso()
    with dependencies.auth_db() as conn:
        conn.execute(
            """
            INSERT INTO user_agent_runtime_settings
                (user_id, enabled, protocol, base_url, model, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                enabled = excluded.enabled,
                protocol = excluded.protocol,
                base_url = excluded.base_url,
                model = excluded.model,
                updated_at = excluded.updated_at
            """,
            (
                int(user["id"]),
                1 if settings["enabled"] else 0,
                settings["protocol"],
                settings["baseUrl"],
                settings["model"],
                timestamp,
                timestamp,
            ),
        )
    return dependencies.jsonify({
        "code": 0,
        "msg": "智能体运行配置已保存",
        "data": {
            "settings": dependencies.xiaozhi_runtime_settings_for_user(int(user["id"])),
            "connection": connection,
        },
    })


@blueprint.post("/api/xiaozhi/runtime-settings/test")
def xiaozhi_runtime_settings_test():
    user, error_response = dependencies.xiaozhi_current_user()
    if error_response:
        return error_response
    payload = dependencies.request.get_json(silent=True) or {}
    try:
        settings = dependencies.validate_xiaozhi_runtime_settings(payload)
    except ValueError as exc:
        return dependencies.jsonify({"code": 400, "msg": str(exc)}), 400
    try:
        result = dependencies.test_xiaozhi_runtime_connection(settings)
    except Exception as exc:
        return dependencies.jsonify({
            "code": 502,
            "msg": "模型连接测试失败",
            "data": {
                "ok": False,
                "error": str(exc)[:1200],
            },
        }), 502
    return dependencies.jsonify({
        "code": 0,
        "msg": "模型连接成功",
        "data": result,
    })


@blueprint.get("/api/xiaozhi/skills")
def xiaozhi_skills():
    user, error_response = dependencies.xiaozhi_current_user()
    if error_response:
        return error_response
    return dependencies.jsonify({
        "code": 0,
        "msg": "ok",
        "data": {
            "skills": dependencies.DEFAULT_AGENT_HARNESS.registry.list_skills(),
        },
    })


def _mcp_jsonrpc_result(request_id, result: dict):
    return dependencies.jsonify({"jsonrpc": "2.0", "id": request_id, "result": result})


def _mcp_jsonrpc_error(request_id, code: int, message: str, data=None):
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return dependencies.jsonify({"jsonrpc": "2.0", "id": request_id, "error": error})


@blueprint.get("/api/xiaozhi/mcp")
def xiaozhi_mcp_info():
    user, error_response = dependencies.xiaozhi_current_user()
    if error_response:
        return error_response
    return dependencies.jsonify({
        "code": 0,
        "msg": "ok",
        "data": {
            **dependencies.DEFAULT_AGENT_HARNESS.mcp_gateway.status(),
            "endpoint": "/api/xiaozhi/mcp",
            "methods": [
                "initialize",
                "ping",
                "tools/list",
                "tools/call",
                "resources/list",
                "resources/read",
                "prompts/list",
                "prompts/get",
            ],
        },
    })


@blueprint.post("/api/xiaozhi/mcp")
def xiaozhi_mcp_jsonrpc():
    user, error_response = dependencies.xiaozhi_current_user()
    if error_response:
        return error_response
    envelope = dependencies.request.get_json(silent=True) or {}
    request_id = envelope.get("id")
    method = str(envelope.get("method") or "").strip()
    params = envelope.get("params") if isinstance(envelope.get("params"), dict) else {}
    gateway = dependencies.DEFAULT_AGENT_HARNESS.mcp_gateway

    if envelope.get("jsonrpc") != "2.0":
        return _mcp_jsonrpc_error(request_id, -32600, "Invalid Request")
    if method == "notifications/initialized":
        return dependencies.Response(status=202)
    if method == "initialize":
        return _mcp_jsonrpc_result(
            request_id,
            {
                "protocolVersion": gateway.protocol_version,
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                    "prompts": {"listChanged": False},
                },
                "serverInfo": {
                    "name": "xiaozhi-agent-harness",
                    "title": "嵌小智 Agent Harness MCP Gateway",
                    "version": dependencies.DEFAULT_AGENT_HARNESS.version,
                },
                "instructions": "所有工具均由嵌小智总控调度，并经过共享黑板、质量审核和安全审核。",
            },
        )
    if method == "ping":
        return _mcp_jsonrpc_result(request_id, {})
    if method == "tools/list":
        return _mcp_jsonrpc_result(request_id, {"tools": gateway.list_tools()})
    if method == "resources/list":
        return _mcp_jsonrpc_result(request_id, {"resources": gateway.list_resources()})
    if method == "prompts/list":
        return _mcp_jsonrpc_result(request_id, {"prompts": gateway.list_prompts()})
    if method == "prompts/get":
        name = str(params.get("name") or "")
        arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
        if name not in {item["name"] for item in gateway.list_prompts()}:
            return _mcp_jsonrpc_error(request_id, -32602, f"Unknown prompt: {name}")
        return _mcp_jsonrpc_result(
            request_id,
            {
                "description": next(item["description"] for item in gateway.list_prompts() if item["name"] == name),
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": (
                                f"请由嵌小智总控执行 {arguments.get('taskType') or '学习任务'}，"
                                f"主题为：{arguments.get('topic') or '根据当前画像自动判断'}。"
                            ),
                        },
                    }
                ],
            },
        )
    if method == "resources/read":
        uri = str(params.get("uri") or "")
        context = dependencies.xiaozhi_latest_context(int(user["id"]))
        if uri == "learner://profile/current":
            value = context.get("profile") or context.get("questionnaire") or {}
        elif uri == "learner://evidence/recent":
            value = {
                "examResults": context.get("examResults") or [],
                "questionSheets": context.get("questionSheets") or [],
                "mcuExperiments": context.get("mcuExperiments") or [],
                "recentEvents": context.get("recentEvents") or [],
            }
        elif uri == "xiaozhi://orchestration/recent":
            value = dependencies.xiaozhi_recent_orchestration_runs(int(user["id"]), limit=20)
        elif uri == "course://knowledge/catalog":
            value = dependencies.retrieve_course_knowledge(
                "嵌入式基础 STM32 GPIO 串口中断 Linux驱动 RTOS 实验调试",
                top_k=12,
                user_id=int(user["id"]),
                db_path=dependencies.AUTH_DB_PATH,
            )
        elif uri == "learner://knowledge/private":
            with dependencies.auth_db() as conn:
                value = dependencies.private_knowledge_service.list_knowledge_collections(conn, int(user["id"]))
        else:
            return _mcp_jsonrpc_error(request_id, -32002, f"Resource not found: {uri}")
        return _mcp_jsonrpc_result(
            request_id,
            {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": dependencies._orchestration_json(value),
                    }
                ]
            },
        )
    if method == "tools/call":
        tool_name = str(params.get("name") or "")
        arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
        try:
            skill = dependencies.DEFAULT_AGENT_HARNESS.registry.resolve_tool(tool_name)
        except KeyError as exc:
            return _mcp_jsonrpc_error(request_id, -32602, str(exc))
        try:
            gateway.validate_input(skill, arguments)
        except dependencies.SkillContractError as exc:
            return _mcp_jsonrpc_error(
                request_id,
                -32602,
                "Invalid tool arguments",
                {"tool": tool_name, "contractError": str(exc)},
            )
        if skill.task_type in dependencies.PROFILE_DRIVEN_TASK_TYPES:
            with dependencies.auth_db() as conn:
                active_profile = dependencies.active_profile_for_user(conn, int(user["id"]))
            if not active_profile:
                return _mcp_jsonrpc_error(
                    request_id,
                    -32010,
                    "Active learning profile required",
                    {
                        "errorCode": "ACTIVE_PROFILE_REQUIRED",
                        "profileRequired": True,
                        "actionRoute": "/learning-profile",
                    },
                )
        topic = dependencies._resource_agent_topic(
            arguments.get("topic")
            or arguments.get("question")
            or arguments.get("message")
            or skill.name,
            arguments,
        )
        task_arguments = {**arguments, "topic": topic}
        if skill.task_type == "learning_feedback":
            task_arguments["sourceTaskId"] = str(arguments.get("taskId") or "").strip()
        if skill.task_type == "mcu":
            task_arguments = dependencies.resolve_mcu_agent_params_for_user(int(user["id"]), task_arguments, topic)
        route_to = dependencies._resource_agent_route(skill.task_type, topic, task_arguments)
        title = f"{topic[:32]} · {skill.name}"
        task_id = dependencies.xiaozhi_create_task(
            int(user["id"]),
            skill.task_type,
            title,
            str(arguments.get("prompt") or arguments.get("message") or topic),
            route_to,
        )
        dependencies.threading.Thread(
            target=dependencies.xiaozhi_run_resource_task,
            args=(task_id, int(user["id"]), skill.task_type, topic, task_arguments),
            daemon=True,
        ).start()
        task = dependencies.xiaozhi_build_card(task_id, skill.task_type, title, route_to)
        return _mcp_jsonrpc_result(
            request_id,
            {
                "content": [
                    {
                        "type": "text",
                        "text": f"嵌小智已通过 Skill {skill.id} 创建后台任务 {task_id}。",
                    }
                ],
                "structuredContent": {
                    "task": task,
                    "skill": skill.public_dict(),
                },
                "isError": False,
            },
        )
    return _mcp_jsonrpc_error(request_id, -32601, f"Method not found: {method}")


@blueprint.get("/api/xiaozhi/status")
def xiaozhi_status():
    user, error_response = dependencies.xiaozhi_current_user()
    if error_response:
        return error_response
    context = dependencies.xiaozhi_latest_context(user["id"])
    tasks = context.get("recentTasks") or []
    question_status = {}
    try:
        question_status = dependencies._question_task_snapshot(user["id"])
    except Exception:
        question_status = {}
    user_runtime_settings = dependencies.xiaozhi_runtime_settings_for_user(int(user["id"]))
    runtime_overrides = dependencies.xiaozhi_runtime_setting_overrides(int(user["id"]))
    with dependencies.setting_overrides(runtime_overrides):
        xiaozhi_runtime = dependencies.hermes_xiaozhi_runtime_status()
    orchestration_runtime = dependencies.DEFAULT_AGENT_HARNESS.status()
    profile_report_id = int(
        context.get("profileReportId")
        or (context.get("profile") or {}).get("id")
        or 0
    )
    recent_runs = dependencies.xiaozhi_recent_orchestration_runs(
        int(user["id"]),
        limit=12,
        profile_report_id=profile_report_id,
    )
    agent_conversation = dependencies.xiaozhi_profile_agent_context(
        int(user["id"]),
        profile_report_id,
    )
    latest_agent_runs: dict[str, dict] = {}
    latest_agent_context: dict[str, dict] = {}
    for orchestration_run in recent_runs:
        for agent_run in orchestration_run.get("agentRuns") or []:
            if not isinstance(agent_run, dict):
                continue
            agent_id = str(agent_run.get("id") or "").strip()
            if not agent_id or agent_id in latest_agent_runs:
                continue
            latest_agent_runs[agent_id] = agent_run
            latest_agent_context[agent_id] = orchestration_run

    master_run = latest_agent_runs.pop(dependencies.XIAOZHI_MASTER_AGENT_ID, {})
    master_context = latest_agent_context.get(dependencies.XIAOZHI_MASTER_AGENT_ID) or {}
    agents = [
        {
            "id": dependencies.XIAOZHI_MASTER_AGENT_ID,
            "name": "嵌小智总控智能体",
            "status": master_run.get("status") or ("ready" if xiaozhi_runtime.get("hasToken") else "idle"),
            "detail": master_run.get("detail") or (
                f"总控编排 / {xiaozhi_runtime.get('model') or dependencies.DEFAULT_TEXT_MODEL_ID} / "
                f"{'用户自定义 ' + user_runtime_settings.get('protocol', '') if user_runtime_settings.get('enabled') else '平台默认'}"
            ),
            "runtime": {
                **xiaozhi_runtime,
                "orchestration": orchestration_runtime,
            },
            "role": "supervisor",
            "source": "orchestration-run" if master_run else "runtime",
            "lastRunId": str(master_context.get("runId") or ""),
            "lastRunAt": str(master_context.get("updatedAt") or ""),
        },
    ]
    for agent_id, agent_run in latest_agent_runs.items():
        metadata = dependencies.AGENT_CATALOG.get(agent_id) or {}
        run_context = latest_agent_context.get(agent_id) or {}
        agents.append(
            {
                "id": agent_id,
                "name": str(agent_run.get("name") or metadata.get("name") or agent_id),
                "status": str(agent_run.get("status") or "complete"),
                "detail": str(agent_run.get("detail") or ""),
                "progress": dependencies._safe_progress(agent_run.get("progress"), 0),
                "eventCount": int(agent_run.get("eventCount") or 0),
                "role": metadata.get("role") or str(agent_run.get("role") or "specialist"),
                "hidden": bool(metadata.get("hidden")),
                "hiddenReason": str(metadata.get("hiddenReason") or ""),
                "source": "orchestration-run",
                "lastRunId": str(run_context.get("runId") or ""),
                "lastRunAt": str(run_context.get("updatedAt") or ""),
            }
        )
    return dependencies.jsonify({
        "code": 0,
        "data": {
            "agents": agents,
            "tasks": tasks,
            "context": context,
            "orchestrationRuns": recent_runs,
            "architecture": orchestration_runtime,
            "modelRuntime": user_runtime_settings,
            "agentConversation": agent_conversation,
            "profileReportId": profile_report_id,
        },
    })


@blueprint.get("/api/xiaozhi/profile-conversation")
def xiaozhi_profile_conversation():
    user, error_response = dependencies.xiaozhi_current_user()
    if error_response:
        return error_response
    try:
        requested_profile_id = int(dependencies.request.args.get("profileReportId") or 0)
    except (TypeError, ValueError):
        return dependencies.jsonify({"message": "profileReportId 必须是整数"}), 400
    if requested_profile_id <= 0:
        context = dependencies.xiaozhi_latest_context(int(user["id"]))
        requested_profile_id = int(
            context.get("profileReportId")
            or (context.get("profile") or {}).get("id")
            or 0
        )
    if requested_profile_id <= 0:
        return dependencies.jsonify({
            "code": 0,
            "data": dependencies.ProfileAgentContextStore.empty_context(),
        })
    with dependencies.auth_db() as conn:
        profile = dependencies.get_profile_for_user(conn, int(user["id"]), requested_profile_id)
    if not profile:
        return dependencies.jsonify({"message": "学习画像不存在"}), 404
    conversation = dependencies.xiaozhi_profile_agent_context(
        int(user["id"]),
        requested_profile_id,
    )
    return dependencies.jsonify({"code": 0, "data": conversation})
