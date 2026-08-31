"""Question generation, streaming progress, history, and scoring routes."""

from __future__ import annotations

from typing import Callable

from flask import Blueprint


class _DependencyProxy:
    def __init__(self, provider: Callable[[str], object]):
        self._provider = provider

    def __getattr__(self, name: str):
        return self._provider(name)


blueprint = Blueprint("question_generator_api", __name__)
dependencies: _DependencyProxy


def create_question_blueprint(provider: Callable[[str], object]) -> Blueprint:
    global dependencies
    dependencies = _DependencyProxy(provider)
    return blueprint


def _apply_question_scores(question_bank: dict, question_type_scores: dict[str, float]) -> None:
    questions = question_bank.get("questions") if isinstance(question_bank, dict) else []
    if not isinstance(questions, list):
        return

    total_score = 0.0
    for question in questions:
        if not isinstance(question, dict):
            continue
        question_type = str(question.get("type") or "")
        score = None
        for configured_type, configured_score in question_type_scores.items():
            if configured_type in question_type or question_type in configured_type:
                score = float(configured_score)
                break
        if score is None:
            try:
                score = float(question.get("score") or question.get("points") or question.get("full_score") or 0)
            except (TypeError, ValueError):
                score = 0.0
        question["score"] = round(score, 1)
        total_score += score

    question_bank["total_score"] = round(total_score, 1)


@blueprint.post("/api/question-generator/upload-generate")
def upload_and_generate():
    """Accept files + config, extract text, call questionGenerator, return structured bank."""
    files = dependencies.request.files.getlist("files")
    pasted_text = dependencies.request.form.get("pasted_text", "").strip()
    course_name = dependencies.request.form.get("course_name", "").strip()
    chapter_name = dependencies.request.form.get("chapter_name", "").strip()
    student_profile = dependencies.request.form.get("student_profile", "").strip()
    constraints = dependencies.request.form.get("constraints", "").strip()
    preferred_types_raw = dependencies.request.form.get("preferred_question_types", "[]")
    type_counts_raw = dependencies.request.form.get("question_type_counts", "{}")
    type_scores_raw = dependencies.request.form.get("question_type_scores", "{}")
    difficulty_ratios_raw = dependencies.request.form.get("difficulty_ratios", "{}")
    difficulty_locks_raw = dependencies.request.form.get("difficulty_locks", "{}")
    generation_options_raw = dependencies.request.form.get("generation_options", "{}")
    total_score_raw = dependencies.request.form.get("total_score", "0")
    question_count_raw = dependencies.request.form.get("question_count", "8")
    auto_distribute = dependencies.request.form.get("auto_distribute", "").strip().lower() in {"1", "true", "yes", "on"}
    force_real_agent = dependencies.request.form.get("force_real_agent", "").strip().lower() in {"1", "true", "yes", "on"}

    try:
        preferred_types = dependencies.json.loads(preferred_types_raw) if preferred_types_raw else []
    except dependencies.json.JSONDecodeError:
        preferred_types = []

    try:
        question_type_counts = dependencies.json.loads(type_counts_raw) if type_counts_raw else {}
    except dependencies.json.JSONDecodeError:
        question_type_counts = {}
    if not isinstance(question_type_counts, dict):
        question_type_counts = {}
    question_type_counts = {
        str(question_type): int(count)
        for question_type, count in question_type_counts.items()
        if str(question_type).strip()
        and isinstance(count, (int, float, str))
        and str(count).isdigit()
        and int(count) > 0
    }

    try:
        question_type_scores = dependencies.json.loads(type_scores_raw) if type_scores_raw else {}
    except dependencies.json.JSONDecodeError:
        question_type_scores = {}
    if not isinstance(question_type_scores, dict):
        question_type_scores = {}
    question_type_scores = {
        str(question_type): float(score)
        for question_type, score in question_type_scores.items()
        if str(question_type).strip()
        and isinstance(score, (int, float, str))
        and str(score).replace(".", "", 1).isdigit()
        and float(score) >= 0
    }

    try:
        question_count = int(question_count_raw)
    except (ValueError, TypeError):
        question_count = 8

    try:
        difficulty_ratios = dependencies.json.loads(difficulty_ratios_raw) if difficulty_ratios_raw else {}
    except dependencies.json.JSONDecodeError:
        difficulty_ratios = {}
    if not isinstance(difficulty_ratios, dict):
        difficulty_ratios = {}
    difficulty_ratios = {
        str(key): int(value)
        for key, value in difficulty_ratios.items()
        if str(key).strip() and isinstance(value, (int, float, str)) and str(value).replace(".", "", 1).isdigit()
    }

    try:
        difficulty_locks = dependencies.json.loads(difficulty_locks_raw) if difficulty_locks_raw else {}
    except dependencies.json.JSONDecodeError:
        difficulty_locks = {}
    if not isinstance(difficulty_locks, dict):
        difficulty_locks = {}

    try:
        generation_options = dependencies.json.loads(generation_options_raw) if generation_options_raw else {}
    except dependencies.json.JSONDecodeError:
        generation_options = {}
    if not isinstance(generation_options, dict):
        generation_options = {}
    generation_options = {
        "analysis": bool(generation_options.get("analysis", True)),
        "tags": bool(generation_options.get("tags", True)),
        "variants": bool(generation_options.get("variants", False)),
    }

    try:
        total_score = float(total_score_raw)
    except (ValueError, TypeError):
        total_score = 0

    extracted_parts = []
    for f in files:
        text = dependencies._extract_text_from_file(f)
        if text.strip():
            extracted_parts.append(text)

    if pasted_text:
        extracted_parts.append(pasted_text)

    resource_text = "\n\n".join(extracted_parts)
    if not resource_text.strip():
        uploaded_names = [f.filename for f in files if f.filename]
        return dependencies.jsonify({
            "error": "未能从上传文件中提取到有效文本，请粘贴文本或上传可复制文字的文档",
            "details": {
                "files": uploaded_names,
                "supported": "txt、md、pdf、docx、pptx、jpg、png、bmp；安装 LibreOffice 后支持 doc、ppt，安装 Tesseract 后支持图片 OCR",
            },
        }), 400

    if not course_name:
        course_name = "未指定课程"
    if not chapter_name:
        chapter_name = "未指定章节"

    source_mode = "question_sheet" if len(dependencies.re.findall(r"(?m)^\s*\d{1,3}\s*[\.、]\s*\S+", resource_text)) >= 3 else "material"
    qg_payload = {
        "student_profile": student_profile or "通用学生",
        "course_name": course_name,
        "target_topic": chapter_name,
        "learning_objectives": f"针对{course_name} - {chapter_name}生成练习题",
        "resource_plan_result": resource_text[:24000],
        "source_original_text": resource_text[:40000],
        "source_mode": source_mode,
        "preferred_question_types": preferred_types,
        "question_type_counts": question_type_counts,
        "question_type_scores": question_type_scores,
        "difficulty_ratios": difficulty_ratios,
        "difficulty_locks": difficulty_locks,
        "generation_options": generation_options,
        "total_score": total_score,
        "question_count": question_count,
        "auto_distribute": auto_distribute,
        "constraints": constraints,
        "force_real_agent": force_real_agent,
        "notes": "题型分值：" + "、".join(
            f"{question_type} 每题 {score:g} 分"
            for question_type, score in question_type_scores.items()
        ) + (f"；总分 {total_score:g} 分" if total_score else "")
        + f"；难度比例：简单 {difficulty_ratios.get('easy', 0)}%，中等 {difficulty_ratios.get('medium', 0)}%，困难 {difficulty_ratios.get('hard', 0)}%"
        + f"；生成选项：答案解析={'是' if generation_options.get('analysis') else '否'}，知识点标签={'是' if generation_options.get('tags') else '否'}，错题变式={'是' if generation_options.get('variants') else '否'}"
        + f"；生成策略：{'任务规划智能体自动分配题型数量' if auto_distribute else '手动配置题型数量'}",
    }

    try:
        data = dependencies.xiaozhi_generate_question_bank_managed(
            qg_payload,
            int(dependencies.user["id"]),
        )
    except dependencies.StructuredContentError as exc:
        response = {"error": str(exc)}
        if exc.result is not None:
            response["model"] = exc.result.get("model")
            response["raw_content"] = exc.result.get("content", "")
            response["debug"] = {
                "agent": "question-generator",
                "attempts": exc.result.get("debug_attempts", []),
            }
        return dependencies.jsonify(response), 502
    except ValueError as exc:
        return dependencies.jsonify({"error": str(exc)}), 400
    except Exception as exc:
        dependencies.app.logger.exception("question generator failed")
        return dependencies.jsonify({"error": "题库生成失败", "details": str(exc)}), 502

    data.setdefault("debug", {})
    data["debug"]["agent_input"] = qg_payload
    _apply_question_scores(data.get("question_bank", {}), question_type_scores)
    sheet = dependencies.save_question_sheet(data["question_bank"], user_id=int(dependencies.g.current_user["id"]))
    data["question_sheet"] = sheet
    data["question_sheet_id"] = sheet["id"]
    return dependencies.jsonify(data)


def _sse_event(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {dependencies.json.dumps(payload, ensure_ascii=False)}\n\n"


def _question_task_snapshot(user_id: int) -> dict:
    with dependencies._question_generation_lock:
        task = dependencies._question_generation_tasks.get(int(user_id))
        return dict(task) if task else {"status": "idle"}


def _update_question_task(user_id: int, **updates) -> dict:
    with dependencies._question_generation_lock:
        task = dict(dependencies._question_generation_tasks.get(int(user_id)) or {})
        task.update(updates)
        task["updated_at"] = dependencies.utc_timestamp()
        dependencies._question_generation_tasks[int(user_id)] = task
        return dict(task)


def _ppt_task_snapshot(user_id: int) -> dict:
    with dependencies._ppt_generation_lock:
        task = dependencies._ppt_generation_tasks.get(int(user_id))
        return dict(task) if task else {"status": "idle"}


def _ppt_task_meta(*, task_id: str, session_id: str, topic: str, page_count: int) -> dict:
    return {
        "taskId": task_id,
        "sessionId": session_id,
        "title": topic or "PPT 生成任务",
        "topic": topic,
        "pageCount": page_count,
        "created_at": dependencies.utc_timestamp(),
    }


def _safe_progress(value, default: int = 0) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(0, min(100, number))


def _update_ppt_task(user_id: int, **updates) -> dict:
    with dependencies._ppt_generation_lock:
        task = dict(dependencies._ppt_generation_tasks.get(int(user_id)) or {})
        payload = updates.get("payload") if isinstance(updates.get("payload"), dict) else None
        logs = list(task.get("logs") or [])
        if payload:
            progress = _safe_progress(payload.get("progress"), _safe_progress(updates.get("progress"), _safe_progress(task.get("progress"), 0)))
            log_entry = {
                "time": dependencies.utc_timestamp(),
                "stage": payload.get("stage") or updates.get("event") or "progress",
                "message": payload.get("message") or "",
                "progress": progress,
            }
            if not logs or logs[-1].get("stage") != log_entry["stage"] or logs[-1].get("message") != log_entry["message"]:
                logs.append(log_entry)
            updates.setdefault("progress", progress)
        task.update(updates)
        task["logs"] = logs[-40:]
        task["updated_at"] = dependencies.utc_timestamp()
        dependencies._ppt_generation_tasks[int(user_id)] = task
        return dict(task)


def _question_task_meta(
    *,
    task_id: str,
    course_name: str,
    chapter_name: str,
    question_count: int,
    preferred_types: list,
    auto_distribute: bool,
) -> dict:
    title_parts = [part for part in [course_name, chapter_name] if part and part != "未指定章节"]
    title = " - ".join(title_parts) or "题单生成任务"
    return {
        "taskId": task_id,
        "title": title,
        "course_name": course_name,
        "target_topic": chapter_name,
        "question_count": question_count,
        "preferred_question_types": preferred_types,
        "auto_distribute": auto_distribute,
        "created_at": dependencies.utc_timestamp(),
    }


@blueprint.get("/api/question-generator/status")
def question_generator_status():
    dependencies.user = dependencies.g.get("current_user")
    if not dependencies.user:
        return dependencies.jsonify({"code": 401, "msg": "未登录"}), 401
    return dependencies.jsonify(_question_task_snapshot(int(dependencies.user["id"])))


@blueprint.post("/api/question-generator/upload-generate-background")
def upload_and_generate_background():
    """Start question generation in a server-side background thread."""
    user_id = int(dependencies.g.current_user["id"])
    current_task = _question_task_snapshot(user_id)
    if current_task.get("status") == "running":
        return dependencies.jsonify(current_task), 202

    files = dependencies.request.files.getlist("files")
    pasted_text = dependencies.request.form.get("pasted_text", "").strip()
    course_name = dependencies.request.form.get("course_name", "").strip() or "未指定课程"
    chapter_name = dependencies.request.form.get("chapter_name", "").strip() or "未指定章节"
    student_profile = dependencies.request.form.get("student_profile", "").strip()
    constraints = dependencies.request.form.get("constraints", "").strip()
    preferred_types_raw = dependencies.request.form.get("preferred_question_types", "[]")
    type_counts_raw = dependencies.request.form.get("question_type_counts", "{}")
    type_scores_raw = dependencies.request.form.get("question_type_scores", "{}")
    difficulty_ratios_raw = dependencies.request.form.get("difficulty_ratios", "{}")
    difficulty_locks_raw = dependencies.request.form.get("difficulty_locks", "{}")
    generation_options_raw = dependencies.request.form.get("generation_options", "{}")
    total_score_raw = dependencies.request.form.get("total_score", "0")
    question_count_raw = dependencies.request.form.get("question_count", "8")
    auto_distribute = dependencies.request.form.get("auto_distribute", "").strip().lower() in {"1", "true", "yes", "on"}
    force_real_agent = dependencies.request.form.get("force_real_agent", "").strip().lower() in {"1", "true", "yes", "on"}

    try:
        preferred_types = dependencies.json.loads(preferred_types_raw) if preferred_types_raw else []
    except dependencies.json.JSONDecodeError:
        preferred_types = []
    try:
        raw_counts = dependencies.json.loads(type_counts_raw) if type_counts_raw else {}
    except dependencies.json.JSONDecodeError:
        raw_counts = {}
    question_type_counts = {
        str(question_type): int(count)
        for question_type, count in (raw_counts or {}).items()
        if str(question_type).strip()
        and isinstance(count, (int, float, str))
        and str(count).isdigit()
        and int(count) > 0
    }
    try:
        raw_scores = dependencies.json.loads(type_scores_raw) if type_scores_raw else {}
    except dependencies.json.JSONDecodeError:
        raw_scores = {}
    question_type_scores = {
        str(question_type): float(score)
        for question_type, score in (raw_scores or {}).items()
        if str(question_type).strip()
        and isinstance(score, (int, float, str))
        and str(score).replace(".", "", 1).isdigit()
        and float(score) >= 0
    }
    try:
        question_count = int(question_count_raw)
    except (ValueError, TypeError):
        question_count = 8
    try:
        difficulty_ratios = dependencies.json.loads(difficulty_ratios_raw) if difficulty_ratios_raw else {}
    except dependencies.json.JSONDecodeError:
        difficulty_ratios = {}
    if not isinstance(difficulty_ratios, dict):
        difficulty_ratios = {}
    difficulty_ratios = {
        str(key): int(value)
        for key, value in difficulty_ratios.items()
        if str(key).strip() and isinstance(value, (int, float, str)) and str(value).replace(".", "", 1).isdigit()
    }
    try:
        difficulty_locks = dependencies.json.loads(difficulty_locks_raw) if difficulty_locks_raw else {}
    except dependencies.json.JSONDecodeError:
        difficulty_locks = {}
    if not isinstance(difficulty_locks, dict):
        difficulty_locks = {}
    try:
        generation_options = dependencies.json.loads(generation_options_raw) if generation_options_raw else {}
    except dependencies.json.JSONDecodeError:
        generation_options = {}
    if not isinstance(generation_options, dict):
        generation_options = {}
    generation_options = {
        "analysis": bool(generation_options.get("analysis", True)),
        "tags": bool(generation_options.get("tags", True)),
        "variants": bool(generation_options.get("variants", False)),
    }
    try:
        total_score = float(total_score_raw)
    except (ValueError, TypeError):
        total_score = 0

    file_jobs = [
        {
            "index": index,
            "filename": f.filename or f"第 {index} 个文件",
            "raw": f.read(),
        }
        for index, f in enumerate(files, start=1)
    ]
    total_files = len(file_jobs)
    task_topic = " - ".join(part for part in [course_name, chapter_name] if part and part != "未指定章节") or "题单生成"
    task_id = dependencies.xiaozhi_create_task(
        user_id,
        "question_bank",
        f"{task_topic[:32]} · 题库生成智能体",
        constraints or task_topic,
        "/personalized-resources/question-bank",
    )
    task_meta = _question_task_meta(
        task_id=task_id,
        course_name=course_name,
        chapter_name=chapter_name,
        question_count=question_count,
        preferred_types=preferred_types,
        auto_distribute=auto_distribute,
    )
    xiaozhi_logs: list[dict] = []

    def sync_xiaozhi_question_task(
        stage_payload: dict,
        *,
        status: str = "running",
        result: dict | None = None,
        error: dict | None = None,
    ) -> None:
        stage = str(stage_payload.get("stage") or "progress")
        progress_defaults = {
            "start": 5,
            "extracting": 12,
            "agent_input": 22,
            "complete": 100,
            "error": 100,
        }
        progress = _safe_progress(stage_payload.get("progress"), progress_defaults.get(stage, 35))
        log_entry = {
            "time": dependencies.utc_timestamp(),
            "stage": stage,
            "message": str(stage_payload.get("message") or ""),
            "progress": progress,
        }
        if not xiaozhi_logs or xiaozhi_logs[-1].get("stage") != stage or xiaozhi_logs[-1].get("message") != log_entry["message"]:
            xiaozhi_logs.append(log_entry)
        task_result = {
            "message": log_entry["message"] or ("题库已生成完成" if status == "complete" else "嵌小智正在生成题库"),
            "topic": task_topic,
            "progress": progress,
            "currentStage": stage,
            "logs": xiaozhi_logs[-40:],
            "questionCount": question_count,
        }
        if isinstance(result, dict):
            task_result.update(result)
            task_result["progress"] = 100
            task_result["currentStage"] = "complete"
        if isinstance(error, dict):
            task_result["error"] = error
        dependencies.xiaozhi_update_task(
            task_id,
            status=status,
            result_json=task_result,
            error=str((error or {}).get("details") or (error or {}).get("error") or ""),
        )

    start_payload = {"stage": "start", "message": "后台生成任务已启动", "taskId": task_id, "meta": task_meta}
    sync_xiaozhi_question_task(start_payload)
    _update_question_task(user_id, taskId=task_id, status="running", event="start", payload=start_payload, result=None, error=None, meta=task_meta)

    def worker():
        try:
            progress_payload = {"stage": "extracting", "message": "正在提取上传资料并构造智能体输入 JSON", "taskId": task_id, "meta": task_meta}
            sync_xiaozhi_question_task(progress_payload)
            _update_question_task(user_id, status="running", event="progress", payload=progress_payload)
            extracted_parts = []
            for job in file_jobs:
                kind = dependencies._file_kind_label(job["filename"])
                start = {
                    "stage": "extract_file_start",
                    "message": f"正在解析{kind}：{job['index']}/{total_files} {job['filename']}",
                    "file": job["filename"],
                    "fileType": kind,
                    "index": job["index"],
                    "total": total_files,
                    "taskId": task_id,
                }
                _update_question_task(user_id, status="running", event="progress", payload=start)
                text, from_cache = dependencies._extract_text_with_cache(job["raw"], job["filename"])
                done = {
                    "stage": "extract_file_done",
                    "message": f"{kind} 解析完成：{job['index']}/{total_files} {job['filename']}，提取 {len(text.strip())} 个字符" + ("（缓存命中）" if from_cache else "") + "。",
                    "file": job["filename"],
                    "fileType": kind,
                    "index": job["index"],
                    "total": total_files,
                    "textLength": len(text.strip()),
                    "cached": from_cache,
                    "taskId": task_id,
                }
                _update_question_task(user_id, status="running", event="progress", payload=done)
                if text.strip():
                    extracted_parts.append(text)
            if pasted_text:
                extracted_parts.append(pasted_text)

            resource_text = "\n\n".join(extracted_parts)
            if not resource_text.strip():
                error_payload = {
                    "stage": "error",
                    "status": 400,
                    "response": {"error": "未能从上传文件中提取到有效文本，请粘贴文本或上传可复制文字的文档"},
                }
                sync_xiaozhi_question_task(error_payload, status="failed", error=error_payload["response"])
                _update_question_task(user_id, status="error", event="error", payload=error_payload, error=error_payload["response"])
                return

            source_mode = "question_sheet" if len(dependencies.re.findall(r"(?m)^\s*\d{1,3}\s*[\.、]\s*\S+", resource_text)) >= 3 else "material"
            qg_payload = {
                "student_profile": student_profile or "通用学生",
                "course_name": course_name,
                "target_topic": chapter_name,
                "learning_objectives": f"针对{course_name} - {chapter_name}生成练习题",
                "resource_plan_result": resource_text[:24000],
                "source_original_text": resource_text[:40000],
                "source_mode": source_mode,
                "preferred_question_types": preferred_types,
                "question_type_counts": question_type_counts,
                "question_type_scores": question_type_scores,
                "difficulty_ratios": difficulty_ratios,
                "difficulty_locks": difficulty_locks,
                "generation_options": generation_options,
                "total_score": total_score,
                "question_count": question_count,
                "auto_distribute": auto_distribute,
                "constraints": constraints,
                "force_real_agent": force_real_agent,
                "notes": "题型分值：" + "、".join(
                    f"{question_type} 每题 {score:g} 分"
                    for question_type, score in question_type_scores.items()
                ) + (f"；总分 {total_score:g} 分" if total_score else "")
                + f"；难度比例：简单 {difficulty_ratios.get('easy', 0)}%，中等 {difficulty_ratios.get('medium', 0)}%，困难 {difficulty_ratios.get('hard', 0)}%"
                + f"；生成选项：答案解析={'是' if generation_options.get('analysis') else '否'}，知识点标签={'是' if generation_options.get('tags') else '否'}，错题变式={'是' if generation_options.get('variants') else '否'}"
                + f"；生成策略：{'任务规划智能体自动分配题型数量' if auto_distribute else '手动配置题型数量'}",
            }
            agent_input_payload = {"stage": "agent_input", "payload": qg_payload, "taskId": task_id, "meta": task_meta}
            _update_question_task(user_id, status="running", event="agent_input", payload=agent_input_payload)

            def on_delta(piece: str, meta: dict | None = None):
                payload = {"stage": "model_delta", "content": piece[-2000:], "taskId": task_id}
                if meta:
                    payload.update(meta)
                _update_question_task(user_id, status="running", event="delta", payload=payload)

            def on_stage(payload: dict):
                sync_xiaozhi_question_task({**payload, "taskId": task_id})
                _update_question_task(user_id, status="running", event="progress", payload={**payload, "taskId": task_id})

            data = dependencies.xiaozhi_generate_question_bank_managed(
                qg_payload,
                user_id,
                task_id=task_id,
                on_delta=on_delta,
                on_stage=on_stage,
            )
            data.setdefault("debug", {})
            data["debug"]["agent_input"] = qg_payload
            _apply_question_scores(data.get("question_bank", {}), question_type_scores)
            sheet = dependencies.save_question_sheet(data["question_bank"], user_id=user_id)
            data["question_sheet"] = sheet
            data["question_sheet_id"] = sheet["id"]
            if isinstance(data.get("questionGenerator"), dict):
                data["questionGenerator"]["question_sheet"] = sheet
                data["questionGenerator"]["question_sheet_id"] = sheet["id"]
            result_payload = {"stage": "complete", "message": "完整 JSON 已生成，开始渲染题单", "result": data, "taskId": task_id, "meta": task_meta}
            sync_xiaozhi_question_task(result_payload, status="complete", result=data)
            _update_question_task(user_id, status="complete", event="result", payload=result_payload, result=data, error=None)
        except dependencies.StructuredContentError as exc:
            response = {"error": str(exc)}
            if exc.result is not None:
                response["model"] = exc.result.get("model")
                response["raw_content"] = exc.result.get("content", "")
                response["debug"] = {
                    "agent": "question-generator",
                    "attempts": exc.result.get("debug_attempts", []),
                }
            error_payload = {"stage": "error", "status": 502, "response": response, "taskId": task_id}
            sync_xiaozhi_question_task(error_payload, status="failed", error=response)
            _update_question_task(user_id, status="error", event="error", payload=error_payload, error=response)
        except ValueError as exc:
            error_payload = {"stage": "error", "status": 400, "response": {"error": str(exc)}, "taskId": task_id}
            sync_xiaozhi_question_task(error_payload, status="failed", error=error_payload["response"])
            _update_question_task(user_id, status="error", event="error", payload=error_payload, error=error_payload["response"])
        except Exception as exc:
            dependencies.app.logger.exception("question generator background failed")
            error_payload = {"stage": "error", "status": 502, "response": {"error": "题库生成失败", "details": str(exc)}, "taskId": task_id}
            sync_xiaozhi_question_task(error_payload, status="failed", error=error_payload["response"])
            _update_question_task(user_id, status="error", event="error", payload=error_payload, error=error_payload["response"])

    dependencies.threading.Thread(target=worker, daemon=True).start()
    return dependencies.jsonify(_question_task_snapshot(user_id)), 202


@blueprint.post("/api/question-generator/upload-generate-stream")
def upload_and_generate_stream():
    user_id = int(dependencies.g.current_user["id"])
    task_id = dependencies.secrets.token_urlsafe(12)
    files = dependencies.request.files.getlist("files")
    pasted_text = dependencies.request.form.get("pasted_text", "").strip()
    course_name = dependencies.request.form.get("course_name", "").strip() or "未指定课程"
    chapter_name = dependencies.request.form.get("chapter_name", "").strip() or "未指定章节"
    student_profile = dependencies.request.form.get("student_profile", "").strip()
    constraints = dependencies.request.form.get("constraints", "").strip()
    preferred_types_raw = dependencies.request.form.get("preferred_question_types", "[]")
    type_counts_raw = dependencies.request.form.get("question_type_counts", "{}")
    type_scores_raw = dependencies.request.form.get("question_type_scores", "{}")
    difficulty_ratios_raw = dependencies.request.form.get("difficulty_ratios", "{}")
    difficulty_locks_raw = dependencies.request.form.get("difficulty_locks", "{}")
    generation_options_raw = dependencies.request.form.get("generation_options", "{}")
    total_score_raw = dependencies.request.form.get("total_score", "0")
    question_count_raw = dependencies.request.form.get("question_count", "8")
    auto_distribute = dependencies.request.form.get("auto_distribute", "").strip().lower() in {"1", "true", "yes", "on"}
    force_real_agent = dependencies.request.form.get("force_real_agent", "").strip().lower() in {"1", "true", "yes", "on"}

    try:
        preferred_types = dependencies.json.loads(preferred_types_raw) if preferred_types_raw else []
    except dependencies.json.JSONDecodeError:
        preferred_types = []
    try:
        raw_counts = dependencies.json.loads(type_counts_raw) if type_counts_raw else {}
    except dependencies.json.JSONDecodeError:
        raw_counts = {}
    question_type_counts = {
        str(question_type): int(count)
        for question_type, count in (raw_counts or {}).items()
        if str(question_type).strip()
        and isinstance(count, (int, float, str))
        and str(count).isdigit()
        and int(count) > 0
    }
    try:
        raw_scores = dependencies.json.loads(type_scores_raw) if type_scores_raw else {}
    except dependencies.json.JSONDecodeError:
        raw_scores = {}
    question_type_scores = {
        str(question_type): float(score)
        for question_type, score in (raw_scores or {}).items()
        if str(question_type).strip()
        and isinstance(score, (int, float, str))
        and str(score).replace(".", "", 1).isdigit()
        and float(score) >= 0
    }
    try:
        question_count = int(question_count_raw)
    except (ValueError, TypeError):
        question_count = 8
    try:
        difficulty_ratios = dependencies.json.loads(difficulty_ratios_raw) if difficulty_ratios_raw else {}
    except dependencies.json.JSONDecodeError:
        difficulty_ratios = {}
    if not isinstance(difficulty_ratios, dict):
        difficulty_ratios = {}
    difficulty_ratios = {
        str(key): int(value)
        for key, value in difficulty_ratios.items()
        if str(key).strip() and isinstance(value, (int, float, str)) and str(value).replace(".", "", 1).isdigit()
    }
    try:
        difficulty_locks = dependencies.json.loads(difficulty_locks_raw) if difficulty_locks_raw else {}
    except dependencies.json.JSONDecodeError:
        difficulty_locks = {}
    if not isinstance(difficulty_locks, dict):
        difficulty_locks = {}
    try:
        generation_options = dependencies.json.loads(generation_options_raw) if generation_options_raw else {}
    except dependencies.json.JSONDecodeError:
        generation_options = {}
    if not isinstance(generation_options, dict):
        generation_options = {}
    generation_options = {
        "analysis": bool(generation_options.get("analysis", True)),
        "tags": bool(generation_options.get("tags", True)),
        "variants": bool(generation_options.get("variants", False)),
    }
    try:
        total_score = float(total_score_raw)
    except (ValueError, TypeError):
        total_score = 0

    task_meta = _question_task_meta(
        task_id=task_id,
        course_name=course_name,
        chapter_name=chapter_name,
        question_count=question_count,
        preferred_types=preferred_types,
        auto_distribute=auto_distribute,
    )

    file_jobs = [
        {
            "index": index,
            "filename": f.filename or f"第 {index} 个文件",
            "raw": f.read(),
        }
        for index, f in enumerate(files, start=1)
    ]
    total_files = len(file_jobs)

    @dependencies.stream_with_context
    def generate_events():
        start_payload = {"stage": "start", "message": "正在生成中，已收到生成请求", "taskId": task_id, "meta": task_meta}
        _update_question_task(user_id, taskId=task_id, status="running", event="start", payload=start_payload, result=None, error=None, meta=task_meta)
        yield _sse_event("start", start_payload)
        progress_payload = {"stage": "extracting", "message": "正在提取上传资料并构造智能体输入 JSON", "taskId": task_id, "meta": task_meta}
        _update_question_task(user_id, status="running", event="progress", payload=progress_payload)
        yield _sse_event("progress", progress_payload)

        extracted_parts = []

        if file_jobs:
            workers = min(3, len(file_jobs))
            extract_events: dependencies.queue.Queue[tuple[str, dict]] = dependencies.queue.Queue()

            def extract_job(job: dict) -> tuple[str, bool]:
                filename = job["filename"]
                kind = dependencies._file_kind_label(filename)
                cache_path = dependencies._extract_cache_path(job["raw"], filename)
                if cache_path.exists():
                    extract_events.put(("progress", {
                        "stage": "extract_cache_hit",
                        "message": f"{kind} \u5df2\u547d\u4e2d\u7f13\u5b58\uff1a{job['index']}/{total_files} {filename}\uff0c\u6b63\u5728\u8bfb\u53d6\u7f13\u5b58\u7ed3\u679c\u3002",
                        "file": filename,
                        "fileType": kind,
                        "index": job["index"],
                        "total": total_files,
                    }))
                else:
                    extract_events.put(("progress", {
                        "stage": "extract_file_start",
                        "message": f"\u6b63\u5728\u89e3\u6790{kind}\uff1a{job['index']}/{total_files} {filename}",
                        "file": filename,
                        "fileType": kind,
                        "index": job["index"],
                        "total": total_files,
                    }))
                text, from_cache = dependencies._extract_text_with_cache(job["raw"], filename)
                extract_events.put(("progress", {
                    "stage": "extract_file_done",
                    "message": (
                        f"{kind} \u89e3\u6790\u5b8c\u6210\uff1a{job['index']}/{total_files} {filename}\uff0c"
                        f"\u63d0\u53d6 {len(text.strip())} \u4e2a\u5b57\u7b26"
                        + ("\uff08\u7f13\u5b58\u547d\u4e2d\uff09" if from_cache else "")
                        + "\u3002"
                    ),
                    "file": filename,
                    "fileType": kind,
                    "index": job["index"],
                    "total": total_files,
                    "textLength": len(text.strip()),
                    "cached": from_cache,
                }))
                return text, from_cache

            with dependencies.ThreadPoolExecutor(max_workers=workers) as executor:
                future_map = {
                    executor.submit(extract_job, job): job
                    for job in file_jobs
                }
                pending = set(future_map)
                completed = 0
                while completed < len(future_map):
                    while True:
                        try:
                            event, payload = extract_events.get_nowait()
                        except dependencies.queue.Empty:
                            break
                        yield _sse_event(event, payload)

                    done_now = [future for future in pending if future.done()]
                    if not done_now:
                        try:
                            event, payload = extract_events.get(timeout=0.2)
                            yield _sse_event(event, payload)
                        except dependencies.queue.Empty:
                            pass
                        continue

                    for future in done_now:
                        pending.remove(future)
                        completed += 1
                        job = future_map[future]
                        while True:
                            try:
                                event, payload = extract_events.get_nowait()
                            except dependencies.queue.Empty:
                                break
                            yield _sse_event(event, payload)
                        try:
                            text, _from_cache = future.result()
                        except Exception as exc:
                            text = ""
                            yield _sse_event("progress", {
                                "stage": "extract_file_error",
                                "message": f"{dependencies._file_kind_label(job['filename'])} 解析失败：{job['index']}/{total_files} {job['filename']}，{exc}",
                                "file": job["filename"],
                                "fileType": dependencies._file_kind_label(job["filename"]),
                                "index": job["index"],
                                "total": total_files,
                            })
                        if text.strip():
                            extracted_parts.append(text)

                while True:
                    try:
                        event, payload = extract_events.get_nowait()
                    except dependencies.queue.Empty:
                        break
                    yield _sse_event(event, payload)
        if pasted_text:
            extracted_parts.append(pasted_text)
        resource_text = "\n\n".join(extracted_parts)
        if not resource_text.strip():
            yield _sse_event("error", {
                "stage": "error",
                "status": 400,
                "response": {"error": "未能从上传文件中提取到有效文本，请粘贴文本或上传可复制文字的文档"},
            })
            return

        source_mode = "question_sheet" if len(dependencies.re.findall(r"(?m)^\s*\d{1,3}\s*[\.、]\s*\S+", resource_text)) >= 3 else "material"
        qg_payload = {
            "student_profile": student_profile or "通用学生",
            "course_name": course_name,
            "target_topic": chapter_name,
            "learning_objectives": f"针对{course_name} - {chapter_name}生成练习题",
            "resource_plan_result": resource_text[:24000],
            "source_original_text": resource_text[:40000],
            "source_mode": source_mode,
            "preferred_question_types": preferred_types,
            "question_type_counts": question_type_counts,
            "question_type_scores": question_type_scores,
            "difficulty_ratios": difficulty_ratios,
            "difficulty_locks": difficulty_locks,
            "generation_options": generation_options,
            "total_score": total_score,
            "question_count": question_count,
            "auto_distribute": auto_distribute,
            "constraints": constraints,
            "force_real_agent": force_real_agent,
            "notes": "题型分值：" + "、".join(
                f"{question_type} 每题 {score:g} 分"
                for question_type, score in question_type_scores.items()
            ) + (f"；总分 {total_score:g} 分" if total_score else "")
            + f"；难度比例：简单 {difficulty_ratios.get('easy', 0)}%，中等 {difficulty_ratios.get('medium', 0)}%，困难 {difficulty_ratios.get('hard', 0)}%"
            + f"；生成选项：答案解析={'是' if generation_options.get('analysis') else '否'}，知识点标签={'是' if generation_options.get('tags') else '否'}，错题变式={'是' if generation_options.get('variants') else '否'}"
            + f"；生成策略：{'任务规划智能体自动分配题型数量' if auto_distribute else '手动配置题型数量'}",
        }
        agent_input_payload = {"stage": "agent_input", "payload": qg_payload, "taskId": task_id}
        _update_question_task(user_id, status="running", event="agent_input", payload=agent_input_payload)
        yield _sse_event("agent_input", agent_input_payload)

        events: dependencies.queue.Queue[tuple[str, dict]] = dependencies.queue.Queue()

        def worker():
            try:
                def on_delta(piece: str, meta: dict | None = None):
                    payload = {"stage": "model_delta", "content": piece}
                    if meta:
                        payload.update(meta)
                    _update_question_task(user_id, status="running", event="delta", payload={**payload, "content": piece[-2000:]})
                    events.put(("delta", payload))

                def on_stage(payload: dict):
                    _update_question_task(user_id, status="running", event="progress", payload=payload)
                    events.put(("progress", payload))

                data = dependencies.xiaozhi_generate_question_bank_managed(
                    qg_payload,
                    user_id,
                    task_id=task_id,
                    on_delta=on_delta,
                    on_stage=on_stage,
                )
                data.setdefault("debug", {})
                data["debug"]["agent_input"] = qg_payload
                _apply_question_scores(data.get("question_bank", {}), question_type_scores)
                sheet = dependencies.save_question_sheet(data["question_bank"], user_id=user_id)
                data["question_sheet"] = sheet
                data["question_sheet_id"] = sheet["id"]
                result_payload = {"stage": "complete", "message": "完整 JSON 已生成，开始渲染题单", "result": data}
                _update_question_task(user_id, status="complete", event="result", payload=result_payload, result=data, error=None)
                events.put(("result", result_payload))
            except dependencies.StructuredContentError as exc:
                response = {"error": str(exc)}
                if exc.result is not None:
                    response["model"] = exc.result.get("model")
                    response["raw_content"] = exc.result.get("content", "")
                    response["debug"] = {
                        "agent": "question-generator",
                        "attempts": exc.result.get("debug_attempts", []),
                    }
                error_payload = {"stage": "error", "status": 502, "response": response}
                _update_question_task(user_id, status="error", event="error", payload=error_payload, error=response)
                events.put(("error", error_payload))
            except ValueError as exc:
                error_payload = {"stage": "error", "status": 400, "response": {"error": str(exc)}}
                _update_question_task(user_id, status="error", event="error", payload=error_payload, error=error_payload["response"])
                events.put(("error", error_payload))
            except Exception as exc:
                dependencies.app.logger.exception("question generator stream failed")
                error_payload = {"stage": "error", "status": 502, "response": {"error": "题库生成失败", "details": str(exc)}}
                _update_question_task(user_id, status="error", event="error", payload=error_payload, error=error_payload["response"])
                events.put(("error", error_payload))
            finally:
                events.put(("done", {"stage": "done"}))

        dependencies.threading.Thread(target=worker, daemon=True).start()

        while True:
            event, payload = events.get()
            yield _sse_event(event, payload)
            if event == "done":
                break

    return dependencies.Response(generate_events(), mimetype="text/event-stream")


@blueprint.get("/api/question-generator/history")
def question_generator_history():
    dependencies.user = dependencies.g.get("current_user")
    history = dependencies.list_history(int(dependencies.user["id"])) if dependencies.user else {"question_sheets": [], "exam_results": []}
    if dependencies.user:
        task = _question_task_snapshot(int(dependencies.user["id"]))
        if task.get("status") == "running":
            history["active_task"] = task
    return dependencies.jsonify(history)


@blueprint.get("/api/question-generator/config")
def get_question_generator_config():
    user_id = int(dependencies.g.current_user["id"])
    result = dependencies.get_user_question_config(user_id)
    if not result:
        return dependencies.jsonify({"config": None})
    return dependencies.jsonify(result)


@blueprint.put("/api/question-generator/config")
def save_question_generator_config():
    user_id = int(dependencies.g.current_user["id"])
    payload = dependencies.request.get_json(silent=True) or {}
    result = dependencies.save_user_question_config(user_id, payload)
    return dependencies.jsonify(result)


@blueprint.post("/api/question-generator/exam-results")
def question_generator_exam_results():
    payload = dependencies.request.get_json(silent=True) or {}
    result = dependencies.save_exam_result(payload, user_id=int(dependencies.g.current_user["id"]))
    return dependencies.jsonify(result), 201


def _local_ai_score_item(item: dict) -> dict:
    question = item.get("question") or {}
    full_score = float(item.get("full_score") or item.get("score") or question.get("score") or question.get("points") or 0)
    user_answer = str(item.get("user_answer") or "").strip()
    standard_answer = str(item.get("answer") or question.get("answer") or "").strip()
    if not user_answer:
        score = 0.0
        comment = "未作答，无法给分。"
    else:
        normalized_user = dependencies.re.sub(r"\s+", "", user_answer).lower()
        normalized_standard = dependencies.re.sub(r"\s+", "", standard_answer).lower()
        if normalized_standard and (normalized_user == normalized_standard or normalized_user in normalized_standard or normalized_standard in normalized_user):
            score = full_score
            comment = "答案与参考答案高度一致，按满分处理。"
        elif normalized_standard and any(part and part in normalized_user for part in dependencies.re.split(r"[,，、;；。\s]+", normalized_standard)):
            score = round(full_score * 0.6, 1)
            comment = "答案命中部分关键内容，给予部分分。"
        else:
            score = round(full_score * 0.35, 1) if len(user_answer) >= 8 else 0.0
            comment = "答案有作答痕迹，但与参考答案匹配不足，建议人工复核。"
    return {
        "score": min(full_score, max(0.0, score)),
        "full_score": full_score,
        "comment": comment,
    }


def _clamp_ai_score(value, full_score: float) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = 0.0
    return round(min(full_score, max(0.0, score)), 1)


def _ai_score_exam_detail(payload: dict, detail: list[dict]) -> dict:
    items = []
    for idx, item in enumerate(detail):
        question = item.get("question") or {}
        full_score = float(item.get("full_score") or item.get("score") or question.get("score") or question.get("points") or 0)
        items.append({
            "ordinal": idx + 1,
            "question_number": item.get("question_number") or item.get("original_index") or idx + 1,
            "type": item.get("type") or question.get("type") or "",
            "stem": item.get("stem") or question.get("stem") or question.get("title") or question.get("question") or "",
            "options": question.get("options") or [],
            "reference_answer": item.get("answer") or question.get("answer") or "",
            "analysis": item.get("analysis") or question.get("analysis") or "",
            "user_answer": item.get("user_answer") or "",
            "full_score": full_score,
        })

    system = (
        "你是题库考试 AI 评分智能体。请根据题干、题型、用户答案、参考答案和解析进行复核评分。"
        "如果填空题、简答题没有参考答案，也要根据题干要求、关键词、逻辑完整度和表达准确性给出合理分数。"
        "只返回 JSON，不要输出 Markdown。"
    )
    prompt = f"""
考试标题: {payload.get("title") or "题库练习"}
原始总分: {payload.get("total_score")}

待复核题目 JSON:
{dependencies.json.dumps(items, ensure_ascii=False)}

请返回如下 JSON：
{{
  "items": [
    {{
      "ordinal": 1,
      "score": 0,
      "correct": false,
      "comment": "评分依据，说明是否因缺少标准答案而按语义评分",
      "reference_answer": "如果原题没有参考答案，可给出建议参考答案；否则原样返回"
    }}
  ],
  "summary": "本次 AI 复核评分总结"
}}
评分要求：
1. score 必须在 0 到 full_score 之间，可以给小数。
2. correct 表示该题是否达到 60% 得分阈值。
3. 填空题/简答题没有标准答案时，不要直接判 0 分，要按语义和完整度评分。
4. 客观题仍应严格匹配参考答案。
"""
    result = dependencies.call_llm_json(system, prompt, max_tokens=5200)
    scored_by_ordinal = {}
    for scored in result.get("items") or []:
        try:
            scored_by_ordinal[int(scored.get("ordinal"))] = scored
        except (TypeError, ValueError):
            continue

    scored_items = []
    total_score = 0.0
    full_score_total = 0.0
    for idx, item in enumerate(detail):
        question = item.get("question") or {}
        full_score = float(item.get("full_score") or item.get("score") or question.get("score") or question.get("points") or 0)
        full_score_total += full_score
        scored = scored_by_ordinal.get(idx + 1) or {}
        score = _clamp_ai_score(scored.get("score"), full_score)
        next_item = dict(item)
        next_item["ai_score"] = score
        next_item["score"] = score
        next_item["correct"] = bool(scored.get("correct")) if "correct" in scored else (score >= full_score * 0.6 if full_score else bool(item.get("correct")))
        next_item["ai_comment"] = str(scored.get("comment") or "AI 已完成复核评分。")
        if not str(next_item.get("answer") or "").strip() and scored.get("reference_answer"):
            next_item["answer"] = str(scored.get("reference_answer"))
        scored_items.append(next_item)
        total_score += score

    return {
        "score": round(total_score, 1),
        "total_score": round(full_score_total, 1),
        "correct_count": sum(1 for item in scored_items if item.get("correct")),
        "question_count": len(scored_items),
        "detail": scored_items,
        "aiSummary": result.get("summary") or "AI 智能体已完成复核评分。",
        "source": "anthropic_agent",
    }


@blueprint.post("/api/question-generator/ai-score")
def question_generator_ai_score():
    payload = dependencies.request.get_json(silent=True) or {}
    dependencies.user = dependencies.g.get("current_user")
    detail = payload.get("detail") or []
    if not isinstance(detail, list) or not detail:
        return dependencies.jsonify({"code": 400, "msg": "缺少待评分题目"}), 400

    try:
        def score_specialist(_managed_payload: dict, _progress) -> dict:
            score_result = _ai_score_exam_detail(payload, detail)
            score_result["scores"] = {
                "score": score_result.get("score"),
                "totalScore": score_result.get("total_score"),
                "correctCount": score_result.get("correct_count"),
                "questionCount": score_result.get("question_count"),
            }
            score_result["summary"] = score_result.get("aiSummary")
            score_result["recommendations"] = ["根据错题和低分题更新薄弱知识点，并调整下一阶段练习。"]
            score_result["adjustments"] = ["将低于 60% 得分的知识点加入学习路径复习任务。"]
            return score_result

        result = dependencies.xiaozhi_run_orchestrated(
            "effect_assessment",
            str(payload.get("title") or "题库考试效果评估"),
            payload,
            int(dependencies.user["id"]) if dependencies.user else 0,
            score_specialist,
            max_retries=0,
        )
        return dependencies.jsonify(result)
    except dependencies.SkillReviewError:
        raise
    except Exception as exc:
        print(f"[question-generator] AI score agent failed, fallback to local scoring: {exc}", flush=True)

    scored_items = []
    total_score = 0.0
    full_score = 0.0
    for item in detail:
        local = _local_ai_score_item(item)
        total_score += float(local["score"])
        full_score += float(local["full_score"])
        next_item = dict(item)
        next_item["ai_score"] = local["score"]
        next_item["score"] = local["score"]
        next_item["correct"] = local["score"] >= local["full_score"] * 0.6 if local["full_score"] else bool(item.get("correct"))
        next_item["ai_comment"] = local["comment"]
        scored_items.append(next_item)

    local_result = {
        "score": round(total_score, 1),
        "total_score": round(full_score, 1),
        "correct_count": sum(1 for item in scored_items if item.get("correct")),
        "question_count": len(scored_items),
        "detail": scored_items,
        "aiSummary": "已使用题库模块本地评分规则完成复评。",
        "source": "local",
        "scores": {
            "score": round(total_score, 1),
            "totalScore": round(full_score, 1),
            "correctCount": sum(1 for item in scored_items if item.get("correct")),
            "questionCount": len(scored_items),
        },
        "summary": "大模型复评暂不可用，嵌小智已使用本地规则完成基础效果评估。",
        "recommendations": ["恢复模型服务后再次执行语义复评。"],
        "adjustments": ["暂按客观得分更新薄弱点，不扩大推断范围。"],
    }
    try:
        local_result = dependencies.xiaozhi_run_orchestrated(
            "effect_assessment",
            str(payload.get("title") or "题库考试本地效果评估"),
            payload,
            int(dependencies.user["id"]) if dependencies.user else 0,
            lambda _managed_payload, _progress: local_result,
            max_retries=0,
        )
    except dependencies.SkillReviewError:
        raise
    except Exception as exc:
        dependencies.app.logger.exception("question generator local assessment harness failed")
        return dependencies.jsonify({"code": 500, "msg": "题库复评未能通过总控智能体", "error": str(exc)[:300]}), 500
    return dependencies.jsonify(local_result)


# ── MCU experiment persistence ───────────────────────────────────────────
