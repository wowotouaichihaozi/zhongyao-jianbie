import base64
import binascii
import io
import hashlib
import hmac
import json
import os
import queue
import re
import secrets
import shutil
import smtplib
import sqlite3
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from email.message import EmailMessage
from functools import wraps
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse

import bcrypt
import requests
from dotenv import load_dotenv
from flask import Flask, Response, g, jsonify, request, send_file, stream_with_context
from flask_cors import CORS

try:
    from system_monitor import SystemMonitor
    from runtime_control import QueueCapacityError, create_platform_executors, runtime_health_snapshot
    from resource_task_admission import RESOURCE_TASK_ADMISSION
    from auth_service import AuthService, AuthSettings
    from auth_routes import AuthRouteDependencies, create_auth_blueprint
    from xiaozhi_api_routes import (
        create_xiaozhi_api_blueprint,
        xiaozhi_execute_profile_management,
    )
    from learning_profile_routes import (
        _attach_profile_learning_path_statuses,
        _schedule_profile_portrait_generation,
        create_learning_profile_blueprint,
    )
    from question_routes import (
        _ppt_task_meta,
        _ppt_task_snapshot,
        _question_task_snapshot,
        _safe_progress,
        _sse_event,
        _update_ppt_task,
        create_question_blueprint,
    )
    from multimodal_routes import (
        _apply_profile_multimodal_context,
        _message_with_multimodal_context,
        _resolve_multimodal_inputs,
        create_multimodal_blueprint,
    )
    from avatar_routes import avatar_bp
    from knowledge_routes import KnowledgeRouteDependencies, create_knowledge_blueprint
    from interview_routes import InterviewRouteDependencies, create_interview_blueprint
    from domain_errors import LearningProfileRequiredError
    from learning_path_state import (
        LEARNING_PATH_REQUIRED_TASK_RESOURCE_TYPES,
        LEARNING_PATH_RESOURCE_ROUTE_TYPES,
        LEARNING_PATH_TASK_RESOURCE_ACTIONS,
        LEARNING_PATH_TASK_RESOURCE_ALIASES,
        _apply_effect_path_adjustment,
        _canonical_learning_path_task_resource,
        _clean_number,
        _clean_text,
        _effect_assessment_records,
        _effect_path_adjustment_preview,
        _ensure_learning_path_task_resource_coverage,
        _find_effect_assessment_plan_record,
        _json_copy,
        _learning_path_active_profile_id,
        _learning_path_task_resource_route,
        _optional_bool,
        annotate_learning_path_personalization,
        build_default_stage_nodes,
        build_week_one_embedded_nodes,
        default_learning_path_config,
        effect_assessment_snapshot,
        json_loads_safe,
        latest_learning_profile_for_user,
        learning_evidence_for_user,
        learning_path_config_is_degraded,
        learning_path_node_cache_from_row,
        learning_path_profile_report_id,
        learning_resource_visit,
        list_learning_feedback_records,
        mark_learning_path_profile_switch,
        migrate_user_learning_path_configs,
        normalize_learning_path_config,
        normalize_learning_path_node_cache,
        normalize_learning_weak_point,
        normalize_learning_feedback_cache_key,
        parse_json_safely,
        read_learning_path_config,
        record_learning_feedback,
        seed_learning_path_config,
        upsert_learning_path_node_cache,
        utc_timestamp,
        write_learning_path_config,
    )
except ImportError:  # pragma: no cover - package import fallback
    from .system_monitor import SystemMonitor
    from .runtime_control import QueueCapacityError, create_platform_executors, runtime_health_snapshot
    from .resource_task_admission import RESOURCE_TASK_ADMISSION
    from .auth_service import AuthService, AuthSettings
    from .auth_routes import AuthRouteDependencies, create_auth_blueprint
    from .xiaozhi_api_routes import (
        create_xiaozhi_api_blueprint,
        xiaozhi_execute_profile_management,
    )
    from .learning_profile_routes import (
        _attach_profile_learning_path_statuses,
        _schedule_profile_portrait_generation,
        create_learning_profile_blueprint,
    )
    from .question_routes import (
        _ppt_task_meta,
        _ppt_task_snapshot,
        _question_task_snapshot,
        _safe_progress,
        _sse_event,
        _update_ppt_task,
        create_question_blueprint,
    )
    from .multimodal_routes import (
        _apply_profile_multimodal_context,
        _message_with_multimodal_context,
        _resolve_multimodal_inputs,
        create_multimodal_blueprint,
    )
    from .avatar_routes import avatar_bp
    from .knowledge_routes import KnowledgeRouteDependencies, create_knowledge_blueprint
    from .interview_routes import InterviewRouteDependencies, create_interview_blueprint
    from .domain_errors import LearningProfileRequiredError
    from .learning_path_state import (
        LEARNING_PATH_REQUIRED_TASK_RESOURCE_TYPES,
        LEARNING_PATH_RESOURCE_ROUTE_TYPES,
        LEARNING_PATH_TASK_RESOURCE_ACTIONS,
        LEARNING_PATH_TASK_RESOURCE_ALIASES,
        _apply_effect_path_adjustment,
        _canonical_learning_path_task_resource,
        _clean_number,
        _clean_text,
        _effect_assessment_records,
        _effect_path_adjustment_preview,
        _ensure_learning_path_task_resource_coverage,
        _find_effect_assessment_plan_record,
        _json_copy,
        _learning_path_active_profile_id,
        _learning_path_task_resource_route,
        _optional_bool,
        annotate_learning_path_personalization,
        build_default_stage_nodes,
        build_week_one_embedded_nodes,
        default_learning_path_config,
        effect_assessment_snapshot,
        json_loads_safe,
        latest_learning_profile_for_user,
        learning_evidence_for_user,
        learning_path_config_is_degraded,
        learning_path_node_cache_from_row,
        learning_path_profile_report_id,
        learning_resource_visit,
        list_learning_feedback_records,
        mark_learning_path_profile_switch,
        migrate_user_learning_path_configs,
        normalize_learning_path_config,
        normalize_learning_path_node_cache,
        normalize_learning_weak_point,
        normalize_learning_feedback_cache_key,
        parse_json_safely,
        read_learning_path_config,
        record_learning_feedback,
        seed_learning_path_config,
        upsert_learning_path_node_cache,
        utc_timestamp,
        write_learning_path_config,
    )

try:
    from video_generation import execute_generated_video_task, generate_generated_video_cover, media_file
except ImportError:  # pragma: no cover - package import fallback
    from .video_generation import execute_generated_video_task, generate_generated_video_cover, media_file

try:
    from herb_recognition import HerbRecognitionError, herb_ai_runtime_overrides, normalize_herb_analysis, recognize_herb_image, recognize_herb_image_with_deepseek, validate_recognized_herb_name
except ImportError:  # pragma: no cover - package import fallback
    from .herb_recognition import HerbRecognitionError, herb_ai_runtime_overrides, normalize_herb_analysis, recognize_herb_image, recognize_herb_image_with_deepseek, validate_recognized_herb_name

try:
    from resource_cover import render_resource_task_cover
except ImportError:  # pragma: no cover - package import fallback
    from .resource_cover import render_resource_task_cover

try:
    from api_config import setting_default
    from common import build_anthropic_messages_url, create_llm_headers, get_setting, now_iso, setting_overrides
    from database_schema import (
        init_auth_schema,
        recover_interrupted_learning_profile_portraits,
        recover_interrupted_xiaozhi_tasks,
    )
    from interview_runtime import (
        end_interview_session,
        get_interview_video_context,
        handle_interview_message,
        public_interview_profiles,
        save_interview_frame_analysis,
        start_interview_session,
    )
    from mimo_interview_client import (
        MimoInterviewConfigError,
        MimoInterviewError,
        analyze_interview_frame,
        generate_interview_followup,
        generate_interview_question,
    )
    from learning_agents import (
        LEARNING_PATH_REQUIRED_RESOURCE_TYPES,
        LEARNING_PATH_RESOURCE_PLAN_VERSION,
        build_learning_profile_context,
        call_llm_json,
        request_llm_audio_understanding,
        request_llm_image_understanding,
        request_llm_text,
        generate_background_chat,
        generate_learning_path,
        generate_learning_path_stage_detail,
        generate_personalized_resources,
        generate_profile_report,
        enrich_learning_path_task_descriptions,
        ensure_weekly_learning_path_resource_coverage,
        plan_learning_path_stage_resources,
        sanitize_learning_path_resource_params,
    )
    from learning_profile_workflow_agent import LearningProfileModelUnavailable, clear_persisted_profile_dialogue, run_learning_profile_workflow
    from learning_profile_sessions import add_message as add_profile_session_message, create_session as create_profile_session, get_session as get_profile_session, list_sessions as list_profile_sessions, update_session as update_profile_session
    from learning_profile_versions import (
        activate_profile,
        active_profile_for_user,
        create_profile_version,
        delete_profile,
        get_profile_for_user,
        list_profiles_for_user,
        profile_state_for_user,
        rename_profile,
        reset_profile_state,
        save_or_update_active_profile,
        update_profile_report,
    )
    from profile_portrait_service import generate_profile_portrait
    from profile_agent_context import ProfileAgentContextStore
    from learning_tutor import generate_learning_tutor
    from learning_document import generate_learning_document, get_learning_document, list_learning_documents, save_learning_document
    from learning_animation import generate_learning_animation
    from hermes_xiaozhi_agent import PLATFORM_TOOLS, hermes_xiaozhi_runtime_status, run_xiaozhi_hermes_agent
    from agent_harness import DEFAULT_AGENT_HARNESS
    from agent_harness.registry import SkillContractError
    from multi_agent_runtime import (
        AGENT_CATALOG,
        XIAOZHI_ARCHITECTURE,
        XIAOZHI_MASTER_AGENT_ID,
    )
    from model_routing import (
        DEFAULT_TEXT_MODEL_ID,
        DEFAULT_VISION_MODEL_ID,
        public_input_route,
        resolve_model_routing,
    )
    from course_knowledge import CACHE_PATH as COURSE_KNOWLEDGE_CACHE_PATH, retrieve_course_knowledge
    from herb_model_catalog import HERB_MODEL_REVISION, find_herb_model, public_herb_model_catalog, select_learning_path_herb
    import knowledge_growth
    import private_knowledge as private_knowledge_service
    import showcase_network
    from mcu_catalog import (
        get_mcu_experiment,
        mcu_catalog_payload,
        normalize_mcu_resource_params,
        normalize_mcu_route,
        recommend_mcu_experiments,
        validate_mcu_flash,
    )
    from ppt_h5 import generate_ppt_h5, ppt_h5_health
    from question_generator_runtime import StructuredContentError, generate_question_bank
    from question_generator_storage import (
        get_user_question_config,
        list_history,
        save_exam_result,
        save_question_sheet,
        save_user_question_config,
    )
    from resource_workflow import (
        evaluate_ppt_resource,
        evaluate_question_bank_resource,
        generate_resource_workflow,
    )
except ImportError:  # pragma: no cover - package-style import fallback
    from .api_config import setting_default
    from .common import build_anthropic_messages_url, create_llm_headers, get_setting, now_iso, setting_overrides
    from .database_schema import (
        init_auth_schema,
        recover_interrupted_learning_profile_portraits,
        recover_interrupted_xiaozhi_tasks,
    )
    from .interview_runtime import (
        end_interview_session,
        get_interview_video_context,
        handle_interview_message,
        public_interview_profiles,
        save_interview_frame_analysis,
        start_interview_session,
    )
    from .mimo_interview_client import (
        MimoInterviewConfigError,
        MimoInterviewError,
        analyze_interview_frame,
        generate_interview_followup,
        generate_interview_question,
    )
    from .learning_agents import (
        LEARNING_PATH_REQUIRED_RESOURCE_TYPES,
        LEARNING_PATH_RESOURCE_PLAN_VERSION,
        build_learning_profile_context,
        call_llm_json,
        request_llm_audio_understanding,
        request_llm_image_understanding,
        request_llm_text,
        generate_background_chat,
        generate_learning_path,
        generate_learning_path_stage_detail,
        generate_personalized_resources,
        generate_profile_report,
        enrich_learning_path_task_descriptions,
        ensure_weekly_learning_path_resource_coverage,
        plan_learning_path_stage_resources,
        sanitize_learning_path_resource_params,
    )
    from .learning_profile_workflow_agent import LearningProfileModelUnavailable, clear_persisted_profile_dialogue, run_learning_profile_workflow
    from .learning_profile_sessions import add_message as add_profile_session_message, create_session as create_profile_session, get_session as get_profile_session, list_sessions as list_profile_sessions, update_session as update_profile_session
    from .learning_profile_versions import (
        activate_profile,
        active_profile_for_user,
        create_profile_version,
        delete_profile,
        get_profile_for_user,
        list_profiles_for_user,
        profile_state_for_user,
        rename_profile,
        reset_profile_state,
        save_or_update_active_profile,
        update_profile_report,
    )
    from .profile_portrait_service import generate_profile_portrait
    from .profile_agent_context import ProfileAgentContextStore
    from .learning_tutor import generate_learning_tutor
    from .learning_document import generate_learning_document, get_learning_document, list_learning_documents, save_learning_document
    from .learning_animation import generate_learning_animation
    from .hermes_xiaozhi_agent import PLATFORM_TOOLS, hermes_xiaozhi_runtime_status, run_xiaozhi_hermes_agent
    from .agent_harness import DEFAULT_AGENT_HARNESS
    from .agent_harness.registry import SkillContractError
    from .multi_agent_runtime import (
        AGENT_CATALOG,
        XIAOZHI_ARCHITECTURE,
        XIAOZHI_MASTER_AGENT_ID,
    )
    from .model_routing import (
        DEFAULT_TEXT_MODEL_ID,
        DEFAULT_VISION_MODEL_ID,
        public_input_route,
        resolve_model_routing,
    )
    from .course_knowledge import CACHE_PATH as COURSE_KNOWLEDGE_CACHE_PATH, retrieve_course_knowledge
    from .herb_model_catalog import HERB_MODEL_REVISION, find_herb_model, public_herb_model_catalog, select_learning_path_herb
    from . import knowledge_growth
    from . import private_knowledge as private_knowledge_service
    from . import showcase_network
    from .mcu_catalog import (
        get_mcu_experiment,
        mcu_catalog_payload,
        normalize_mcu_resource_params,
        normalize_mcu_route,
        recommend_mcu_experiments,
        validate_mcu_flash,
    )
    from .ppt_h5 import generate_ppt_h5, ppt_h5_health
    from .question_generator_runtime import StructuredContentError, generate_question_bank
    from .question_generator_storage import (
        get_user_question_config,
        list_history,
        save_exam_result,
        save_question_sheet,
        save_user_question_config,
    )
    from .resource_workflow import (
        evaluate_ppt_resource,
        evaluate_question_bank_resource,
        generate_resource_workflow,
    )


# Always load the deployable backend configuration, independent of the shell cwd.
load_dotenv(Path(__file__).resolve().parent / ".env")

app = Flask(__name__)
app.register_blueprint(avatar_bp)
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST_DIR = BASE_DIR / 'frontend' / 'dist'
ADMIN_DIST_DIR = BASE_DIR / 'admin' / 'dist'
MOBILE_DIST_DIR = BASE_DIR / 'mobile' / 'dist'
DEFAULT_AVATAR = "/userlogo.png"
EXTRACT_CACHE_DIR = Path(__file__).resolve().parent / "data" / "extract_cache"
MULTIMODAL_INPUT_DIR = Path(__file__).resolve().parent / "data" / "multimodal_inputs"
RESOURCE_COVER_CACHE_DIR = Path(__file__).resolve().parent / "data" / "resource_covers"
AUTH_DB_PATH = Path(__file__).resolve().parent / "data" / "auth.sqlite3"
LLM_RESPONSE_TOKEN_BUDGET = 128000
SESSION_COOKIE_NAME = "fswy_session"
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
CODEX_PREVIEW_TOKEN = "codex-preview-token"
CODEX_PREVIEW_USERNAME = "codex-preview"
ADMIN_USERNAME = get_setting("ADMIN_USERNAME", setting_default("ADMIN_USERNAME", "admin123"))
ADMIN_PASSWORD = get_setting("ADMIN_PASSWORD", setting_default("ADMIN_PASSWORD", "admin123"))
SYSTEM_MONITOR = SystemMonitor(BASE_DIR)
APP_STARTED_AT = time.monotonic()
AUTH_LOCK_SECONDS = 10 * 60
VISION_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp", ".gif"}
AUDIO_INPUT_SUFFIXES = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus"}
VISION_EXTRACTION_CACHE_VERSION = "qwen3-vl-visual-evidence-v1"


class SkillReviewError(RuntimeError):
    """Raised when Harness review rejects a specialist result."""

    def __init__(self, result: dict):
        self.result = result if isinstance(result, dict) else {}
        trace = self.result.get("orchestration") if isinstance(self.result.get("orchestration"), dict) else {}
        review = trace.get("review") if isinstance(trace.get("review"), dict) else {}
        issues = [str(item) for item in (review.get("issues") or []) if str(item).strip()]
        super().__init__("；".join(issues[:5]) or "智能体产物未通过结构或安全审核")


def learning_profile_required_response(message: str = "当前没有激活画像，请先完成十个维度的画像采集并生成报告。"):
    return jsonify(
        {
            "code": 409,
            "errorCode": "ACTIVE_PROFILE_REQUIRED",
            "msg": message,
            "data": {
                "profileRequired": True,
                "requiredDimensions": 10,
                "actionRoute": "/learning-profile",
            },
        }
    ), 409


AUTH_MAX_FAILED_ATTEMPTS = 5
LOGIN_IP_WINDOW_SECONDS = 60
LOGIN_IP_MAX_ATTEMPTS = 20
REGISTER_IP_WINDOW_SECONDS = 60
REGISTER_IP_MAX_ATTEMPTS = 5
EMAIL_CODE_IP_WINDOW_SECONDS = 60
EMAIL_CODE_IP_MAX_ATTEMPTS = 3
EMAIL_CODE_TTL_SECONDS = 10 * 60

_ip_rate_lock = threading.Lock()
_ip_rate_buckets: dict[str, list[float]] = {}
_captcha_lock = threading.Lock()
_captchas: dict[str, dict] = {}
_email_code_lock = threading.Lock()
_email_codes: dict[str, dict] = {}


@app.get("/api-cover")
def proxy_video_cover():
    raw_url = request.args.get("url", "").strip()
    if not raw_url:
        return Response("Missing url", status=400)
    if not re.match(r"^https?://", raw_url, re.I):
        return Response("Unsupported image url", status=400)
    host = re.sub(r"^https?://", "", raw_url, flags=re.I).split("/", 1)[0].lower()
    allowed_hosts = ("hdslb.com", "bilibili.com", "biliimg.com")
    if not any(host == allowed or host.endswith(f".{allowed}") for allowed in allowed_hosts):
        return Response("Unsupported image host", status=400)
    try:
        upstream = requests.get(
            raw_url,
            headers={
                "Referer": "https://www.bilibili.com/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            },
            timeout=20,
        )
    except requests.RequestException as exc:
        return Response(str(exc), status=502)
    return Response(
        upstream.content,
        status=upstream.status_code,
        content_type=upstream.headers.get("content-type", "image/jpeg"),
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.route("/ppt-api/<path:subpath>", methods=["GET", "POST", "OPTIONS"])
def proxy_ohmyppt_api(subpath: str):
    """Expose the loopback-only OhMyPPT API through the unified local origin."""
    if subpath not in {"health", "generate"}:
        return jsonify({"detail": "OhMyPPT endpoint not found"}), 404
    if request.method == "OPTIONS":
        return Response(status=204)

    upstream_headers = {
        name: value
        for name, value in {
            "Accept": request.headers.get("Accept"),
            "Authorization": request.headers.get("Authorization"),
            "Content-Type": request.headers.get("Content-Type"),
            "Cookie": request.headers.get("Cookie"),
            "Origin": request.headers.get("Origin"),
        }.items()
        if value
    }
    try:
        upstream = requests.request(
            request.method,
            f"http://127.0.0.1:8765/api/{subpath}",
            params=request.args,
            data=request.get_data(cache=False) if request.method == "POST" else None,
            headers=upstream_headers,
            timeout=900 if subpath == "generate" else 10,
            proxies={"http": "", "https": ""},
        )
    except requests.RequestException as exc:
        return jsonify({"detail": f"OhMyPPT service unavailable: {str(exc)[:800]}"}), 502

    response_headers = {}
    content_type = upstream.headers.get("content-type")
    if content_type:
        response_headers["Content-Type"] = content_type
    return Response(upstream.content, status=upstream.status_code, headers=response_headers)


@app.get("/api-bili/<path:subpath>")
def proxy_bilibili(subpath: str):
    target_url = f"https://api.bilibili.com/{subpath}"
    try:
        upstream = requests.get(
            target_url,
            params=request.args,
            headers={
                "Referer": "https://search.bilibili.com",
                "Origin": "https://search.bilibili.com",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
                "Cookie": "buvid3=infoc",
            },
            timeout=30,
        )
    except requests.RequestException as exc:
        return jsonify({"error": str(exc)}), 502
    return Response(
        upstream.text,
        status=upstream.status_code,
        content_type=upstream.headers.get("content-type", "application/json"),
    )


@app.post("/api-mimo/<path:subpath>")
def proxy_mimo(subpath: str):
    # Compatibility for already-open mind-map tabs. Browser-supplied provider
    # credentials are deliberately ignored; all calls use the signed-in user's
    # server-side runtime settings.
    user = current_user_from_request()
    if not user:
        return jsonify({"error": {"message": "请先登录", "code": "AUTH_REQUIRED"}}), 401
    g.current_user = user
    payload = request.get_json(silent=True) or {}
    try:
        completion = run_user_llm_completion(int(user["id"]), payload)
    except ValueError as exc:
        return jsonify({"error": {"message": str(exc), "code": "INVALID_REQUEST"}}), 400
    except Exception as exc:
        return jsonify({"error": {"message": public_llm_error(exc), "code": "MODEL_REQUEST_FAILED"}}), 502

    text = completion["choices"][0]["message"]["content"]
    if bool(payload.get("stream")):
        def legacy_stream():
            yield f"data: {json.dumps({'type': 'content_block_delta', 'delta': {'type': 'text_delta', 'text': text}}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'message_stop'}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        return Response(legacy_stream(), content_type="text/event-stream; charset=utf-8")
    return jsonify({
        "id": completion["id"],
        "type": "message",
        "role": "assistant",
        "model": completion["model"],
        "content": [{"type": "text", "text": text}],
        "stop_reason": "end_turn",
        "usage": completion.get("usage") or {},
        "modelRuntime": completion["modelRuntime"],
        "deprecatedRoute": f"/api-mimo/{subpath}",
    })
_question_generation_lock = threading.Lock()
_question_generation_tasks: dict[int, dict] = {}
_ppt_generation_lock = threading.Lock()
_ppt_generation_tasks: dict[int, dict] = {}


frontend_origin = get_setting("FRONTEND_ORIGIN", setting_default("FRONTEND_ORIGIN"))
allowed_frontend_origins = {
    item.strip()
    for item in frontend_origin.split(",")
    if item.strip()
}
allowed_frontend_origins.update(
    {
        "http://localhost:5088",
        "http://127.0.0.1:5088",
        "http://115.190.162.173",
        "https://115.190.162.173",
        "http://120.26.3.150",
        "https://120.26.3.150",
        "https://lzhan.xyz",
        "https://www.lzhan.xyz",
        "https://localhost",
        "capacitor://localhost",
    }
)
CORS(app, resources={r"/api/*": {"origins": sorted(allowed_frontend_origins)}}, supports_credentials=True)


AUTH_SERVICE = AuthService(
    AuthSettings(
        database_path=lambda: AUTH_DB_PATH,
        default_avatar=DEFAULT_AVATAR,
        admin_username=ADMIN_USERNAME,
        admin_password=ADMIN_PASSWORD,
        session_cookie_name=SESSION_COOKIE_NAME,
        session_ttl_seconds=SESSION_TTL_SECONDS,
        preview_token=CODEX_PREVIEW_TOKEN,
        preview_username=CODEX_PREVIEW_USERNAME,
        email_code_ttl_seconds=EMAIL_CODE_TTL_SECONDS,
    ),
    timestamp=utc_timestamp,
)

# Compatibility exports keep existing route and extension call sites stable while
# authentication state and policy live in one owned service.
now_ts = AUTH_SERVICE.now_ts
auth_db = AUTH_SERVICE.connect
init_auth_db = AUTH_SERVICE.initialize_database
ensure_user_email_column = AUTH_SERVICE.ensure_user_email_column
password_hash = AUTH_SERVICE.password_hash
password_matches = AUTH_SERVICE.password_matches
seed_admin = AUTH_SERVICE.seed_admin
ensure_codex_preview_user = AUTH_SERVICE.ensure_preview_user


PLATFORM_EXECUTORS = create_platform_executors()
RESOURCE_AGENT_EXECUTOR = PLATFORM_EXECUTORS["resource"]
PPT_RESOURCE_EXECUTOR = PLATFORM_EXECUTORS["ppt"]
VIDEO_RESOURCE_EXECUTOR = PLATFORM_EXECUTORS["video"]
try:
    LEARNING_PATH_RESOURCE_PLANNER_MAX_WORKERS = max(
        1,
        min(8, int(os.getenv("LEARNING_PATH_RESOURCE_PLANNER_MAX_WORKERS", "4"))),
    )
except (TypeError, ValueError):
    LEARNING_PATH_RESOURCE_PLANNER_MAX_WORKERS = 4
LEARNING_PATH_GENERATION_EXECUTOR = PLATFORM_EXECUTORS["learningPath"]
LEARNING_PATH_WEEK_PREPARATION_EXECUTOR = PLATFORM_EXECUTORS["weekPreparation"]
_LEARNING_PATH_RESOURCE_RECOVERY_LOCK = threading.Lock()
_learning_path_resource_recovery_started = False
PROFILE_PORTRAIT_EXECUTOR = PLATFORM_EXECUTORS["profilePortrait"]
PROFILE_PORTRAIT_STALE_SECONDS = 8 * 60
LEARNING_PATH_STAGE_RESOURCE_LOCKS: dict[tuple[int, str], threading.Lock] = {}
LEARNING_PATH_STAGE_RESOURCE_LOCKS_GUARD = threading.Lock()
LEARNING_PATH_CONFIG_WRITE_LOCKS: dict[int, threading.Lock] = {}
LEARNING_PATH_CONFIG_WRITE_LOCKS_GUARD = threading.Lock()
LEARNING_PATH_NEXT_WEEK_LOCKS: dict[tuple[int, int], threading.Lock] = {}
LEARNING_PATH_NEXT_WEEK_LOCKS_GUARD = threading.Lock()
normalize_username = AUTH_SERVICE.normalize_username
normalize_email = AUTH_SERVICE.normalize_email
validate_username = AUTH_SERVICE.validate_username
validate_email = AUTH_SERVICE.validate_email
validate_login_identifier = AUTH_SERVICE.validate_login_identifier
validate_password = AUTH_SERVICE.validate_password
public_user = AUTH_SERVICE.public_user
auth_payload = AUTH_SERVICE.auth_payload
token_digest = AUTH_SERVICE.token_digest
client_ip = AUTH_SERVICE.client_ip
is_secure_request = AUTH_SERVICE.is_secure_request
set_session_cookie = AUTH_SERVICE.set_session_cookie
clear_session_cookie = AUTH_SERVICE.clear_session_cookie
create_session = AUTH_SERVICE.create_session
request_session_token = AUTH_SERVICE.request_session_token
is_local_preview_request = AUTH_SERVICE.is_local_preview_request
current_user_from_request = AUTH_SERVICE.current_user_from_request
revoke_current_session = AUTH_SERVICE.revoke_current_session
rate_limit_bucket = AUTH_SERVICE.rate_limit_bucket
get_login_failure_count = AUTH_SERVICE.get_login_failure_count
captcha_required = AUTH_SERVICE.captcha_required
create_captcha = AUTH_SERVICE.create_captcha
verify_captcha = AUTH_SERVICE.verify_captcha
email_code_digest = AUTH_SERVICE.email_code_digest
create_email_code = AUTH_SERVICE.create_email_code
verify_email_code = AUTH_SERVICE.verify_email_code
smtp_enabled = AUTH_SERVICE.smtp_enabled
send_email_code = AUTH_SERVICE.send_email_code
require_auth = AUTH_SERVICE.require_auth
admin_ok = AUTH_SERVICE.admin_ok
require_admin = AUTH_SERVICE.require_admin
require_super_admin = AUTH_SERVICE.require_super_admin
admin_user_info = AUTH_SERVICE.admin_user_info
rows_to_dicts = AUTH_SERVICE.rows_to_dicts
day_key = AUTH_SERVICE.day_key

init_auth_db()
app.register_blueprint(
    create_knowledge_blueprint(
        KnowledgeRouteDependencies(
            connection_factory=auth_db,
            database_path=lambda: AUTH_DB_PATH,
            knowledge_cache_path=COURSE_KNOWLEDGE_CACHE_PATH,
            now=now_iso,
        )
    )
)


@app.errorhandler(400)
def handle_bad_request(error: Exception):
    app.logger.info("request rejected as invalid: %s", error)
    return jsonify({"code": 400, "msg": "请求参数无效，请检查后重试"}), 400


@app.errorhandler(SkillReviewError)
def handle_skill_review_error(error: SkillReviewError):
    trace = error.result.get("orchestration") if isinstance(error.result.get("orchestration"), dict) else {}
    return jsonify(
        {
            "code": 422,
            "errorCode": "AGENT_REVIEW_FAILED",
            "msg": str(error),
            "data": {
                "runId": trace.get("runId") or "",
                "taskId": trace.get("taskId") or "",
                "review": trace.get("review") or {},
            },
        }
    ), 422


@app.errorhandler(SkillContractError)
def handle_skill_contract_error(error: SkillContractError):
    return jsonify(
        {
            "code": 422,
            "errorCode": "AGENT_CONTRACT_FAILED",
            "msg": "智能体结构化输出未通过 Skill 契约校验",
            "data": {"detail": str(error)[:1000]},
        }
    ), 422


@app.before_request
def ensure_api_auth():
    SYSTEM_MONITOR.start()
    if request.method == "OPTIONS":
        return None
    public_paths = {
        "/api/health",
        "/api/model-capabilities",
        "/api/auth/login",
        "/api/admin-auth/login",
        "/api/admin-auth/refreshToken",
        "/api/auth/register",
        "/api/auth/email-code",
        "/api/auth/captcha",
        "/api/auth/logout",
        "/api/ai-config",
        "/api/ppt-h5/health",
        "/api/ppt-h5/styles",
    }
    if request.path.startswith("/api/") and request.path not in public_paths:
        user = current_user_from_request()
        if not user:
            return jsonify({"code": 401, "msg": "请先登录"}), 401
        g.current_user = user
    return None


@app.before_request
def bind_private_knowledge_user_context():
    user = g.get("current_user")
    if not user:
        return None
    g.private_knowledge_context_token = private_knowledge_service.bind_private_knowledge_context(
        int(user["id"]),
        AUTH_DB_PATH,
    )
    return None


@app.teardown_request
def reset_private_knowledge_user_context(_error=None):
    token = getattr(g, "private_knowledge_context_token", None)
    if token is not None:
        private_knowledge_service.reset_private_knowledge_context(token)


@app.get("/api/health")
def health():
    payload, status_code = runtime_health_snapshot(
        db_path=AUTH_DB_PATH,
        connection_factory=auth_db,
        executors=PLATFORM_EXECUTORS,
        service="feishengwangying-backend-flask",
        started_at=APP_STARTED_AT,
        timestamp=now_iso(),
    )
    return jsonify(payload), status_code


@app.get("/api/model-capabilities")
def public_model_capabilities():
    """Expose effective model labels without provider URLs or credentials."""
    routing = resolve_model_routing().get("routing") or {}
    public_routing = {}
    for kind in ("text", "image", "audio"):
        route = routing.get(kind) or {}
        public_routing[kind] = {
            key: route.get(key)
            for key in ("provider", "modelName", "modelId", "input", "output")
            if route.get(key) not in (None, "")
        }
    return jsonify({"code": 0, "data": {"routing": public_routing}})


app.register_blueprint(
    create_auth_blueprint(
        AuthRouteDependencies(
            service=AUTH_SERVICE,
            timestamp=utc_timestamp,
            platform_tools=lambda: PLATFORM_TOOLS,
            parse_json=parse_json_safely,
            system_monitor=lambda: SYSTEM_MONITOR,
            default_avatar=DEFAULT_AVATAR,
            preview_username=CODEX_PREVIEW_USERNAME,
            auth_lock_seconds=AUTH_LOCK_SECONDS,
            auth_max_failed_attempts=AUTH_MAX_FAILED_ATTEMPTS,
            login_ip_limit=LOGIN_IP_MAX_ATTEMPTS,
            login_ip_window=LOGIN_IP_WINDOW_SECONDS,
            register_ip_limit=REGISTER_IP_MAX_ATTEMPTS,
            register_ip_window=REGISTER_IP_WINDOW_SECONDS,
            email_ip_limit=EMAIL_CODE_IP_MAX_ATTEMPTS,
            email_ip_window=EMAIL_CODE_IP_WINDOW_SECONDS,
        )
    )
)



def _multimodal_api_dependency(name: str):
    return globals()[name]


app.register_blueprint(create_multimodal_blueprint(_multimodal_api_dependency))


def _question_api_dependency(name: str):
    return globals()[name]


app.register_blueprint(create_question_blueprint(_question_api_dependency))


def _learning_profile_api_dependency(name: str):
    return globals()[name]


app.register_blueprint(create_learning_profile_blueprint(_learning_profile_api_dependency))


def _learning_path_background_task_status(
    conn: sqlite3.Connection,
    user_id: int,
    profile_report_id: int,
) -> dict:
    if int(profile_report_id or 0) <= 0:
        return {}
    rows = conn.execute(
        """
        SELECT task_id, status, route, result_json, error, created_at, updated_at
        FROM xiaozhi_tasks
        WHERE user_id = ? AND task_type = 'learning_path'
        ORDER BY id DESC
        LIMIT 30
        """,
        (int(user_id),),
    ).fetchall()
    for row in rows:
        result = json_loads_safe(row["result_json"], {})
        if int(result.get("profileReportId") or 0) != int(profile_report_id):
            continue
        return {
            "taskId": str(row["task_id"] or ""),
            "status": str(row["status"] or ""),
            "route": str(row["route"] or "/learning-path"),
            "progress": max(0, min(100, int(result.get("progress") or 0))),
            "currentStage": str(result.get("currentStage") or ""),
            "message": str(result.get("message") or ""),
            "completedWeeks": max(0, int(result.get("completedWeeks") or 0)),
            "totalWeeks": max(1, int(result.get("totalWeeks") or 6)),
            "profileReportId": int(profile_report_id),
            "error": str(row["error"] or "")[:500],
            "createdAt": str(row["created_at"] or ""),
            "updatedAt": str(row["updated_at"] or ""),
        }
    return {}


@app.get("/api/learning-path/config")
def learning_path_config_get():
    user = g.get("current_user")
    with auth_db() as conn:
        active_profile = active_profile_for_user(conn, int(user["id"])) if user else {}
        active_profile_id = int(active_profile.get("id") or active_profile.get("_profileReportId") or 0)
        config = read_learning_path_config(
            conn,
            int(user["id"]) if user else None,
            profile_report_id=active_profile_id or None,
        )
        if user:
            config = annotate_learning_path_personalization(config, active_profile)
            meta = config.setdefault("meta", {})
            path_profile_id = int(meta.get("profileReportId") or 0)
            refresh_recommended = bool(
                (active_profile_id > 0 and path_profile_id != active_profile_id)
                or meta.get("taskModel") != "dynamic-week-tasks-v2"
                or meta.get("taskResourceModel") != LEARNING_PATH_RESOURCE_PLAN_VERSION
            )
            has_saved_path = bool(config.get("weeks"))
            background_generation = _learning_path_background_task_status(
                conn,
                int(user["id"]),
                active_profile_id,
            )
            background_pending = background_generation.get("status") in {"queued", "running"}
            meta["persisted"] = has_saved_path
            meta["savedAt"] = str(config.get("updatedAt") or meta.get("savedAt") or "")
            meta["refreshRecommended"] = refresh_recommended if has_saved_path and active_profile_id > 0 else False
            meta["backgroundGeneration"] = background_generation
            # A stale saved path remains usable. Refresh suggestions must not turn a page reload
            # into an implicit, destructive regeneration.
            meta["needsRegeneration"] = (
                (not has_saved_path or meta.get("personalizationStatus") == "degraded")
                and active_profile_id > 0
                and not background_pending
            )
            config = _annotate_learning_path_week_view_progress(
                conn,
                int(user["id"]),
                config,
            )
    if _optional_bool(request.args.get("summary")) is True:
        config = {
            "version": config.get("version", 2),
            "meta": config.get("meta") or {},
            "weeks": config.get("weeks") or [],
            "stages": {},
            "updatedAt": config.get("updatedAt") or "",
        }
    return jsonify({"code": 0, "msg": "ok", "data": config})


@app.put("/api/learning-path/config")
def learning_path_config_save():
    user = g.get("current_user")
    payload = request.get_json(silent=True) or {}
    config = payload.get("config") if isinstance(payload.get("config"), dict) else payload
    with auth_db() as conn:
        saved_config = write_learning_path_config(conn, config, int(user["id"]) if user else None)
    return jsonify({"code": 0, "msg": "ok", "data": saved_config})


@app.get("/api/learning-path/stages/<stage_id>")
def learning_path_stage_get(stage_id: str):
    user = g.get("current_user")
    with auth_db() as conn:
        active_profile = active_profile_for_user(conn, int(user["id"])) if user else {}
        active_profile_id = int(active_profile.get("id") or active_profile.get("_profileReportId") or 0)
        config = read_learning_path_config(
            conn,
            int(user["id"]) if user else None,
            profile_report_id=active_profile_id or None,
        )
        if user:
            config = annotate_learning_path_personalization(config, active_profile)
    stage = (config.get("stages") or {}).get(stage_id)
    if not stage:
        return jsonify({"code": 404, "msg": "学习路径不存在", "data": None}), 404
    data = {"stage": stage, "meta": config.get("meta") or {}, "updatedAt": config.get("updatedAt") or ""}
    if _optional_bool(request.args.get("includeConfig")) is not False:
        data["config"] = config
    return jsonify({"code": 0, "msg": "ok", "data": data})


@app.post("/api/learning-path/stages/<stage_id>/prepare-resources")
def learning_path_stage_resources_prepare(stage_id: str):
    user = g.get("current_user")
    if not user:
        return jsonify({"code": 401, "msg": "未登录"}), 401
    payload = request.get_json(silent=True) or {}
    try:
        result = prepare_learning_path_stage_resources_for_user(
            int(user["id"]),
            stage_id,
            use_llm=payload.get("useLLM") is not False,
            advance=payload.get("advance") is not False,
            parallel_dispatch=payload.get("parallelDispatch") is True,
        )
    except KeyError:
        return jsonify({"code": 404, "msg": "学习路径周次不存在", "data": None}), 404
    except LearningProfileRequiredError as exc:
        return learning_profile_required_response(str(exc))
    except Exception as exc:
        app.logger.exception("learning path stage resource preparation failed")
        return jsonify({"code": 500, "msg": "本周资源智能体准备失败", "error": str(exc)}), 500
    status_code = 202 if result.get("pending") else 200
    message = (
        "本周资源任务已并行提交"
        if result.get("dispatchMode") == "parallel"
        else "本周资源智能体已准备"
    )
    return jsonify({"code": 0, "msg": message, "data": result}), status_code


@app.get("/api/learning-path/stages/<stage_id>/resource-tasks")
def learning_path_stage_resource_tasks_get(stage_id: str):
    user = g.get("current_user")
    if not user:
        return jsonify({"code": 401, "msg": "未登录"}), 401
    try:
        result = learning_path_stage_resource_status(int(user["id"]), stage_id)
    except KeyError:
        return jsonify({"code": 404, "msg": "学习路径周次不存在", "data": None}), 404
    return jsonify({"code": 0, "msg": "ok", "data": result})


@app.get("/api/learning-path/node-caches")
def learning_path_node_caches_get():
    user = g.get("current_user")
    user_id = int(user["id"])
    with auth_db() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM learning_path_node_caches
            WHERE user_id = ?
            ORDER BY updated_at DESC
            """,
            (user_id,),
        ).fetchall()
    caches = {row["cache_key"]: learning_path_node_cache_from_row(row) for row in rows}
    return jsonify({"code": 0, "msg": "ok", "data": {"caches": caches}})


@app.get("/api/learning-path/node-caches/<cache_key>")
def learning_path_node_cache_get(cache_key: str):
    user = g.get("current_user")
    user_id = int(user["id"])
    key = str(cache_key or "").strip()
    with auth_db() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM learning_path_node_caches
            WHERE user_id = ? AND cache_key = ?
            """,
            (user_id, key),
        ).fetchone()
    return jsonify({"code": 0, "msg": "ok", "data": {"entry": learning_path_node_cache_from_row(row) if row else None}})


@app.put("/api/learning-path/node-caches/<cache_key>")
def learning_path_node_cache_save(cache_key: str):
    user = g.get("current_user")
    user_id = int(user["id"])
    payload = request.get_json(silent=True) or {}
    entry = payload.get("entry") if isinstance(payload.get("entry"), dict) else payload
    try:
        with auth_db() as conn:
            saved = upsert_learning_path_node_cache(conn, user_id, cache_key, entry)
    except ValueError as exc:
        return jsonify({"code": 400, "msg": str(exc), "data": None}), 400
    next_week_task = None
    view_progress = None
    if saved.get("viewedAt") and saved.get("viewSource") == "learning-path-task-open":
        try:
            try:
                saved_profile_report_id = int(saved.get("profileReportId") or 0)
            except (TypeError, ValueError):
                saved_profile_report_id = 0
            with auth_db() as conn:
                active_profile_report_id = _learning_path_active_profile_id(conn, user_id)
                profile_report_id = saved_profile_report_id or active_profile_report_id
                scoped_config = _read_profile_scoped_learning_path_config(
                    conn,
                    user_id,
                    profile_report_id,
                ) if profile_report_id > 0 else {}
                view_progress = _learning_path_week_view_progress(
                    conn,
                    user_id,
                    scoped_config,
                    str(saved.get("stageId") or ""),
                )
            if profile_report_id > 0 and profile_report_id == active_profile_report_id:
                next_week_task = _schedule_profile_learning_path_generation(
                    user_id,
                    profile_report_id,
                    trigger="week_tasks_viewed",
                    source_week_id=str(saved.get("stageId") or ""),
                )
        except Exception:
            app.logger.exception("failed to schedule next week after task view user=%s", user_id)
    return jsonify({
        "code": 0,
        "msg": "ok",
        "data": {
            "entry": saved,
            "viewProgress": view_progress,
            "nextWeekTask": next_week_task,
        },
    })


def _prepare_learning_path_generation(user_id: int, raw_payload: dict) -> tuple[dict, dict]:
    payload = dict(raw_payload or {})
    generation_phase = str(payload.get("generationPhase") or "full").strip().lower()
    try:
        requested_profile_id = int(payload.get("profileReportId") or 0)
    except (TypeError, ValueError):
        requested_profile_id = 0
    with auth_db() as conn:
        profile = (
            get_profile_for_user(conn, int(user_id), requested_profile_id)
            if requested_profile_id > 0
            else latest_learning_profile_for_user(conn, int(user_id))
        )
        if not profile or profile.get("archived"):
            raise LearningProfileRequiredError(
                "当前没有激活画像，暂不能生成个性化学习路径。请先完成十个维度的画像采集。"
            )
        evidence = learning_evidence_for_user(conn, int(user_id))
        payload["profile"] = {
            **profile,
            "learningEvidence": evidence,
        }
        payload["profileReportId"] = int(profile.get("id") or requested_profile_id or 0)
    payload["generationPhase"] = generation_phase
    context = xiaozhi_latest_context(int(user_id))
    context["profile"] = payload["profile"]
    context["profileReportId"] = payload["profileReportId"]
    return payload, context


def _run_learning_path_generation(
    user_id: int,
    payload: dict,
    context: dict,
    *,
    task_id: str = "",
    on_event=None,
) -> dict:
    generation_phase = str(payload.get("generationPhase") or "full").strip().lower()
    result = xiaozhi_run_orchestrated(
        "learning_path",
        str(payload.get("topic") or payload.get("goal") or "生成个性化学习路径"),
        payload,
        int(user_id),
        lambda managed_payload, _progress: generate_learning_path(managed_payload),
        context=context,
        task_id=task_id,
        on_event=on_event,
        max_retries=1,
    )
    config = result.get("config") if isinstance(result, dict) else None
    try:
        profile_report_id = int(payload.get("profileReportId") or 0)
    except (TypeError, ValueError):
        profile_report_id = 0
    if isinstance(config, dict) and profile_report_id > 0:
        config.setdefault("meta", {})["profileReportId"] = profile_report_id
    with auth_db() as conn:
        if isinstance(config, dict) and payload.get("persist", True) is not False:
            result["config"] = write_learning_path_config(
                conn,
                config,
                int(user_id),
                profile_report_id=profile_report_id or None,
            )
    if (
        isinstance(result, dict)
        and isinstance(result.get("config"), dict)
        and payload.get("prepareResources", True) is not False
    ):
        generated_stage_ids = [
            str(week.get("id") or "")
            for week in _visible_learning_path_weeks(result["config"])
            if int(week.get("order") or 0) == int(payload.get("weekStart") or 1)
        ]
        _queue_learning_path_week_resource_preparation(
            int(user_id),
            result["config"],
            stage_ids=generated_stage_ids,
        )
    if isinstance(result, dict):
        saved_config = result.get("config") if isinstance(result.get("config"), dict) else config
        meta = saved_config.get("meta") if isinstance(saved_config, dict) and isinstance(saved_config.get("meta"), dict) else {}
        result["generation"] = {
            "phase": generation_phase,
            "weekStart": int(payload.get("weekStart") or 1),
            "weekCount": int(payload.get("weekCount") or 1),
            "totalWeeks": int(meta.get("totalWeeks") or payload.get("totalWeeks") or 6),
            "state": meta.get("generationState") or "complete",
        }
    return result


def _sanitize_learning_path_error_message(error: Exception | str) -> str:
    message = public_llm_error(error if isinstance(error, Exception) else RuntimeError(str(error)))
    return re.sub(
        r"(?i)((?:api[_-]?key|api[_-]?secret|authorization|password)\s*[:=]\s*)[^\s,;]+",
        r"\1***",
        message,
    )


def _learning_path_stream_error(error: Exception) -> dict:
    if isinstance(error, SkillReviewError):
        trace = error.result.get("orchestration") if isinstance(error.result.get("orchestration"), dict) else {}
        learning_path = error.result.get("learningPath") if isinstance(error.result.get("learningPath"), dict) else error.result
        payload = {
            "errorCode": "AGENT_REVIEW_FAILED",
            "message": str(error),
            "runId": trace.get("runId") or "",
            "review": trace.get("review") or {},
        }
        if isinstance(learning_path, dict) and learning_path.get("error"):
            payload["detail"] = _sanitize_learning_path_error_message(str(learning_path["error"]))
        return payload
    if isinstance(error, SkillContractError):
        return {
            "errorCode": "AGENT_CONTRACT_FAILED",
            "message": "智能体结构化输出未通过 Skill 契约校验",
            "detail": str(error)[:1000],
        }
    message = _sanitize_learning_path_error_message(error)
    return {
        "errorCode": "LEARNING_PATH_GENERATION_FAILED",
        "message": message or "学习路径生成失败",
    }


@app.post("/api/learning-path/generate")
def learning_path_generate():
    user = g.get("current_user")
    if not user:
        return jsonify({"code": 401, "msg": "未登录"}), 401
    try:
        payload, context = _prepare_learning_path_generation(
            int(user["id"]),
            request.get_json(silent=True) or {},
        )
    except LearningProfileRequiredError as exc:
        return learning_profile_required_response(str(exc))
    result = _run_learning_path_generation(int(user["id"]), payload, context)
    return jsonify({"code": 0, "msg": "ok", "data": result})


@app.post("/api/learning-path/generate-next-week")
def learning_path_generate_next_week():
    user = g.get("current_user")
    if not user:
        return jsonify({"code": 401, "msg": "未登录"}), 401
    user_id = int(user["id"])
    request_payload = request.get_json(silent=True) or {}
    try:
        requested_profile_id = int(request_payload.get("profileReportId") or 0)
    except (TypeError, ValueError):
        return jsonify({"code": 400, "msg": "profileReportId 必须是整数"}), 400
    with auth_db() as conn:
        profile_report_id = requested_profile_id or _learning_path_active_profile_id(conn, user_id)
        profile = get_profile_for_user(conn, user_id, profile_report_id) if profile_report_id else None
    if not profile or profile.get("archived"):
        return learning_profile_required_response("请先完成并激活学习画像")

    lock_key = (user_id, int(profile_report_id))
    with LEARNING_PATH_NEXT_WEEK_LOCKS_GUARD:
        generation_lock = LEARNING_PATH_NEXT_WEEK_LOCKS.setdefault(lock_key, threading.Lock())
    if not generation_lock.acquire(blocking=False):
        return jsonify({"code": 409, "msg": "下一周正在规划中，请稍后查看"}), 409

    try:
        with auth_db() as conn:
            existing_config = _read_profile_scoped_learning_path_config(
                conn,
                user_id,
                int(profile_report_id),
            )
        visible_weeks = _visible_learning_path_weeks(existing_config)
        if visible_weeks:
            latest_week = max(visible_weeks, key=lambda item: int(item.get("order") or 0))
            with auth_db() as conn:
                view_progress = _learning_path_week_view_progress(
                    conn,
                    user_id,
                    existing_config,
                    str(latest_week.get("id") or ""),
                )
            if not view_progress.get("allViewed"):
                return jsonify({
                    "code": 409,
                    "msg": "请先查看本周全部学习任务，再生成下一周",
                    "data": {"viewProgress": view_progress},
                }), 409
        next_week = max(
            [int(week.get("order") or 0) for week in visible_weeks] or [0]
        ) + 1
        try:
            requested_total = int(request_payload.get("totalWeeks") or 0)
        except (TypeError, ValueError):
            requested_total = 0
        total_weeks = max(
            4,
            min(
                8,
                requested_total
                or int((existing_config.get("meta") or {}).get("totalWeeks") or 6),
            ),
        )
        if next_week > total_weeks:
            return jsonify({
                "code": 409,
                "msg": "当前学习路径已完成全部周次规划",
                "data": {
                    "profileReportId": int(profile_report_id),
                    "completedWeeks": len(visible_weeks),
                    "totalWeeks": total_weeks,
                },
            }), 409
        generation_request = {
            "profileReportId": int(profile_report_id),
            "persist": True,
            "useLatestProfile": False,
            "useLLM": request_payload.get("useLLM") is not False,
            "prepareResources": request_payload.get("prepareResources") is not False,
            "generationPhase": "first-week" if next_week == 1 else "next-week",
            "weekStart": next_week,
            "weekCount": 1,
            "totalWeeks": total_weeks,
        }
        if visible_weeks:
            generation_request["existingConfig"] = existing_config
        payload, context = _prepare_learning_path_generation(user_id, generation_request)
        result = _run_learning_path_generation(user_id, payload, context)
        return jsonify({
            "code": 0,
            "msg": f"第 {next_week} 周学习路径已生成",
            "data": {
                **result,
                "generatedWeek": next_week,
                "profileReportId": int(profile_report_id),
            },
        })
    except LearningProfileRequiredError as exc:
        return learning_profile_required_response(str(exc))
    except Exception as exc:
        app.logger.exception(
            "next learning-path week generation failed user=%s profile=%s",
            user_id,
            profile_report_id,
        )
        error_payload = _learning_path_stream_error(exc)
        return jsonify({"code": 500, "msg": error_payload.get("message"), "error": error_payload}), 500
    finally:
        generation_lock.release()


@app.post("/api/learning-path/generate-stream")
def learning_path_generate_stream():
    user = g.get("current_user")
    if not user:
        return jsonify({"code": 401, "msg": "未登录"}), 401
    user_id = int(user["id"])
    try:
        payload, context = _prepare_learning_path_generation(
            user_id,
            request.get_json(silent=True) or {},
        )
    except LearningProfileRequiredError as exc:
        return learning_profile_required_response(str(exc))

    events: queue.Queue[tuple[str, dict]] = queue.Queue()
    runtime = llm_runtime_for_user(user_id)

    def worker():
        try:
            result = _run_learning_path_generation(
                user_id,
                payload,
                context,
                on_event=lambda event: events.put(("progress", event)),
            )
            events.put(("result", {
                "stage": "complete",
                "status": "complete",
                "progress": 100,
                "message": "学习路径已通过审核并保存",
                "result": result,
            }))
        except Exception as exc:
            app.logger.error("learning path generation stream failed: %s", type(exc).__name__)
            events.put(("error", {
                "stage": "error",
                "status": "failed",
                "progress": 100,
                **_learning_path_stream_error(exc),
            }))
        finally:
            events.put(("done", {
                "stage": "done",
                "message": "学习路径生成流已结束",
            }))

    @stream_with_context
    def generate_events():
        threading.Thread(target=worker, daemon=True).start()
        yield _sse_event("start", {
            "agentId": XIAOZHI_MASTER_AGENT_ID,
            "agentName": AGENT_CATALOG.get(XIAOZHI_MASTER_AGENT_ID, {}).get("name") or "嵌小智",
            "stage": "request_start",
            "status": "running",
            "progress": 0,
            "message": "嵌小智已接收学习路径生成任务",
            "generationPhase": payload.get("generationPhase"),
            "weekStart": int(payload.get("weekStart") or 1),
            "weekCount": int(payload.get("weekCount") or 1),
            "modelRuntime": runtime,
        })
        while True:
            try:
                event, event_payload = events.get(timeout=10)
            except queue.Empty:
                yield _sse_event("heartbeat", {
                    "stage": "waiting",
                    "status": "running",
                    "message": "智能体仍在生成，请稍候",
                })
                continue
            yield _sse_event(event, event_payload)
            if event == "done":
                break

    return Response(
        generate_events(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/learning-path/stage-detail")
def learning_path_stage_detail():
    user = g.get("current_user")
    if not user:
        return jsonify({"code": 401, "msg": "未登录"}), 401
    payload = request.get_json(silent=True) or {}
    with auth_db() as conn:
        active_profile = latest_learning_profile_for_user(conn, int(user["id"]))
        if not active_profile:
            return learning_profile_required_response(
                "当前没有激活画像，暂不能细化画像驱动的学习阶段。请先完成十个维度的画像采集。"
            )
        payload["profile"] = {
            **active_profile,
            "learningEvidence": learning_evidence_for_user(conn, int(user["id"])),
        }
    result = xiaozhi_run_orchestrated(
        "learning_path_stage",
        str((payload.get("stage") or {}).get("title") or payload.get("topic") or "细化学习阶段"),
        payload,
        int(user["id"]),
        lambda managed_payload, _progress: generate_learning_path_stage_detail(managed_payload),
        max_retries=1,
    )
    return jsonify(result)


@app.post("/api/personalized-resources/generate")
def personalized_resources_generate():
    user = g.get("current_user")
    if not user:
        return jsonify({"code": 401, "msg": "未登录"}), 401
    payload = request.get_json(silent=True) or {}
    with auth_db() as conn:
        active_profile = active_profile_for_user(conn, int(user["id"]))
        if not active_profile:
            return learning_profile_required_response(
                "当前没有激活画像，暂不能生成个性化资源包。请先完成十个维度的画像采集。"
            )
        payload["profile"] = {
            **active_profile,
            "learningEvidence": learning_evidence_for_user(conn, int(user["id"])),
        }
        rows = conn.execute(
            "SELECT id, experiment_id, experiment_name, passed, weak_points, run_data, created_at FROM mcu_experiments WHERE user_id = ? ORDER BY id DESC LIMIT 10",
            (user["id"],),
        ).fetchall()
    experiments = []
    for row in rows:
        experiments.append({
            "id": row[0],
            "experiment_id": row[1],
            "experiment_name": row[2],
            "passed": bool(row[3]),
            "weak_points": json.loads(row[4]) if row[4] else [],
            "run_data": json.loads(row[5]) if row[5] else {},
            "created_at": row[6],
        })
    def resource_package_specialist(managed_payload: dict, _progress) -> dict:
        workflow = generate_resource_workflow(
            managed_payload,
            mcu_experiments=experiments,
            user_id=int(user["id"]),
        )
        return {
            "message": "个性化资源包已生成。",
            "workflow": workflow,
            "selectedResource": (workflow.get("resources") or [None])[0]
            if isinstance(workflow, dict)
            else None,
        }

    result = xiaozhi_run_orchestrated(
        "personalized_resources",
        str((payload.get("request") or {}).get("topic") or payload.get("topic") or "生成个性化资源包"),
        payload,
        int(user["id"]),
        resource_package_specialist,
        context=xiaozhi_latest_context(int(user["id"])),
        max_retries=1,
    )
    return jsonify(result)


@app.post("/api/personalized-resources/agent-task")
def personalized_resource_agent_task():
    """Create background resource-generation tasks callable by platform agents."""
    user = g.get("current_user")
    if not user:
        return jsonify({"code": 401, "msg": "未登录"}), 401
    payload = request.get_json(silent=True) or {}
    raw_types = payload.get("resourceTypes")
    if not isinstance(raw_types, list):
        raw_types = [payload.get("resourceType") or payload.get("type")]
    task_types = []
    for raw_type in raw_types:
        task_type = normalize_resource_agent_type(raw_type)
        if task_type and task_type not in task_types:
            task_types.append(task_type)
    if not task_types:
        return jsonify({
            "code": 400,
            "msg": "resourceType 必须是 personalized_resources、question_bank、ppt、document、mindmap、video、animation、mcu、learning_feedback、profile_management 或 knowledge_base",
            "allowedTypes": sorted(RESOURCE_AGENT_ALLOWED_TYPES),
        }), 400
    if any(task_type in PROFILE_DRIVEN_TASK_TYPES for task_type in task_types):
        with auth_db() as conn:
            if not active_profile_for_user(conn, int(user["id"])):
                return learning_profile_required_response(
                    "当前没有激活画像，暂不能启动个性化资源智能体。请先完成十个维度的画像采集。"
                )

    base_params = payload.get("params") if isinstance(payload.get("params"), dict) else {}
    topic = _resource_agent_topic(payload.get("topic") or payload.get("prompt"), base_params)
    prompt = str(payload.get("prompt") or payload.get("userMessage") or topic).strip()
    created_tasks = []

    for task_type in task_types:
        type_params = dict(base_params)
        nested_params = base_params.get(task_type)
        if isinstance(nested_params, dict):
            type_params.update(nested_params)
        type_params.setdefault("topic", topic)
        task_topic = _resource_agent_topic(type_params.get("topic") or topic, type_params)
        if task_type == "generated_video":
            type_params["deferred"] = True
            type_params["prompt"] = prompt or task_topic
        title = str(payload.get("title") or f"{task_topic[:32]} · {XIAOZHI_RESOURCE_LABELS.get(task_type, '学习资源智能体')}")
        task = xiaozhi_create_resource_agent_task(
            int(user["id"]),
            task_type,
            task_topic,
            type_params,
            title=title,
            prompt=prompt or task_topic,
        )
        created_tasks.append(task)

    queue_rejected = bool(created_tasks) and all(
        str((task.get("result") or {}).get("errorCode") or "") == "RESOURCE_QUEUE_FULL"
        for task in created_tasks
    )
    return jsonify({
        "code": 503 if queue_rejected else 0,
        "msg": (
            "当前生成任务较多，请稍后重新提交"
            if queue_rejected
            else "资源任务已创建；AI 视频仅保存提示词，等待用户确认后启动"
            if "generated_video" in task_types
            else "资源智能体后台任务已启动"
        ),
        "data": {
            "tasks": created_tasks,
            "task": created_tasks[0] if created_tasks else None,
        },
    }), 503 if queue_rejected else 202


@app.get("/api/personalized-resources/generated-videos")
def generated_video_history():
    user, error_response = xiaozhi_current_user()
    if error_response:
        return error_response
    limit = max(1, min(100, request.args.get("limit", default=50, type=int) or 50))
    offset = max(0, request.args.get("offset", default=0, type=int) or 0)
    status = str(request.args.get("status") or "").strip().lower()
    if status == "waiting_for_user":
        status = "waiting"
    allowed_statuses = {"waiting", "queued", "running", "complete", "failed", "cancelled"}
    if status and status not in allowed_statuses:
        return jsonify({
            "code": 400,
            "msg": "status 必须是 waiting、queued、running、complete、failed 或 cancelled",
        }), 400

    clauses = ["user_id = ?", "task_type = 'generated_video'"]
    params: list[object] = [int(user["id"])]
    if status:
        clauses.append("status = ?")
        params.append(status)
    where_sql = " AND ".join(clauses)
    with auth_db() as conn:
        total = int(conn.execute(
            f"SELECT COUNT(*) FROM xiaozhi_tasks WHERE {where_sql}",
            params,
        ).fetchone()[0])
        rows = conn.execute(
            f"""
            SELECT task_id, task_type, title, prompt, status, route, result_json,
                   error, created_at, updated_at
            FROM xiaozhi_tasks
            WHERE {where_sql}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()
    tasks = [xiaozhi_task_from_row(row) for row in rows]
    return jsonify({
        "code": 0,
        "data": {
            "tasks": tasks,
            "total": total,
            "limit": limit,
            "offset": offset,
            "hasMore": offset + len(tasks) < total,
        },
    })


@app.get("/api/personalized-resources/generated-videos/<task_id>/file")
def generated_video_file(task_id: str):
    user, error_response = xiaozhi_current_user()
    if error_response:
        return error_response
    with auth_db() as conn:
        row = conn.execute("SELECT task_type, status FROM xiaozhi_tasks WHERE user_id = ? AND task_id = ? LIMIT 1", (int(user["id"]), str(task_id))).fetchone()
    if not row or row["task_type"] != "generated_video":
        return jsonify({"code": 404, "msg": "未找到视频任务"}), 404
    if row["status"] != "complete":
        return jsonify({"code": 409, "msg": "视频仍在生成中"}), 409
    path = media_file(int(user["id"]), task_id, "final.mp4")
    if not path.is_file():
        return jsonify({"code": 404, "msg": "视频文件不存在"}), 404
    return send_file(path, mimetype="video/mp4", conditional=True, as_attachment=False, download_name="learning-video.mp4")


@app.get("/api/personalized-resources/generated-videos/<task_id>/poster")
def generated_video_poster(task_id: str):
    user, error_response = xiaozhi_current_user()
    if error_response:
        return error_response
    with auth_db() as conn:
        row = conn.execute(
            """
            SELECT task.task_type, cover.image_blob, cover.mime_type, cover.status
            FROM xiaozhi_tasks AS task
            LEFT JOIN generated_video_covers AS cover ON cover.task_id = task.task_id
            WHERE task.user_id = ? AND task.task_id = ?
            LIMIT 1
            """,
            (int(user["id"]), str(task_id)),
        ).fetchone()
    if not row or row["task_type"] != "generated_video":
        return jsonify({"code": 404, "msg": "未找到视频任务"}), 404
    image_blob = bytes(row["image_blob"] or b"")
    if str(row["status"] or "") == "ready" and image_blob:
        response = send_file(
            io.BytesIO(image_blob),
            mimetype=str(row["mime_type"] or "image/jpeg"),
            conditional=False,
            as_attachment=False,
            download_name=f"{task_id}-poster",
            max_age=0,
        )
        response.headers["Cache-Control"] = "private, no-store"
        return response
    path = media_file(int(user["id"]), task_id, "poster.jpg")
    if not path.is_file():
        return jsonify({"code": 404, "msg": "视频封面尚未生成"}), 404
    return send_file(path, mimetype="image/jpeg", conditional=True, as_attachment=False)


@app.get("/api/personalized-resources/generated-videos/<task_id>/segments/<segment_id>/<kind>")
def generated_video_segment_file(task_id: str, segment_id: str, kind: str):
    user, error_response = xiaozhi_current_user()
    if error_response:
        return error_response
    with auth_db() as conn:
        row = conn.execute(
            "SELECT task_type FROM xiaozhi_tasks WHERE user_id = ? AND task_id = ? LIMIT 1",
            (int(user["id"]), str(task_id)),
        ).fetchone()
    if not row or row["task_type"] != "generated_video":
        return jsonify({"code": 404, "msg": "未找到视频任务"}), 404
    if not re.fullmatch(r"segment_[0-9]{2}", str(segment_id or "")):
        return jsonify({"code": 400, "msg": "无效的视频片段编号"}), 400
    targets = {
        "image": (f"images/{segment_id}.jpg", "image/jpeg"),
        "audio": (f"audio/{segment_id}.aac", "audio/aac"),
        "video": (f"segments/{segment_id}.mp4", "video/mp4"),
    }
    target = targets.get(str(kind or "").lower())
    if not target:
        return jsonify({"code": 400, "msg": "不支持的片段素材类型"}), 400
    path = media_file(int(user["id"]), task_id, target[0])
    if not path.is_file():
        return jsonify({"code": 404, "msg": "片段素材尚未生成"}), 404
    return send_file(path, mimetype=target[1], conditional=True, as_attachment=False)


@app.post("/api/personalized-resources/generated-videos/<task_id>/start")
def start_waiting_generated_video(task_id: str):
    user, error_response = xiaozhi_current_user()
    if error_response:
        return error_response
    payload = request.get_json(silent=True) or {}
    requested_params = payload.get("params") if isinstance(payload.get("params"), dict) else {}
    with auth_db() as conn:
        row = conn.execute(
            "SELECT * FROM xiaozhi_tasks WHERE user_id = ? AND task_id = ? LIMIT 1",
            (int(user["id"]), str(task_id)),
        ).fetchone()
        if not row or row["task_type"] != "generated_video":
            return jsonify({"code": 404, "msg": "未找到待确认的视频任务"}), 404
        if str(row["status"] or "") not in {"waiting", "waiting_for_user"}:
            current = xiaozhi_task_from_row(row)
            return jsonify({
                "code": 409,
                "msg": "该视频任务已经启动或结束",
                "data": {"task": current},
            }), 409

        stored_result = json_loads_safe(row["result_json"], {})
        stored_params = stored_result.get("params") if isinstance(stored_result.get("params"), dict) else {}
        params = {**stored_params, **requested_params}
        params.pop("deferred", None)
        try:
            requested_duration = int(params.get("duration") or 30)
        except (TypeError, ValueError):
            requested_duration = 30
        params["duration"] = max(20, min(60, requested_duration))
        params["style"] = str(params.get("style") or "二维科普动画")[:80]
        params["voice"] = str(params.get("voice") or "nova")[:40]
        params["resolution"] = str(params.get("resolution") or "720p")
        if params["resolution"] not in {"480p", "720p", "1080p"}:
            params["resolution"] = "720p"
        params["videoEngine"] = str(params.get("videoEngine") or "seedance_1_5_coze")
        if params["videoEngine"] not in {"seedance_1_5_coze", "seedance_2_mini", "seedance_2"}:
            params["videoEngine"] = "seedance_1_5_coze"

        topic = _resource_agent_topic(stored_result.get("topic") or row["prompt"] or row["title"], params)
        prompt = str(payload.get("prompt") or row["prompt"] or topic).strip()
        params["prompt"] = prompt[:1200]
        queued_result = {
            **stored_result,
            "message": "用户已确认视频参数，后台工作流即将启动",
            "topic": topic,
            "resourceType": "generated_video",
            "params": params,
            "progress": 0,
            "currentStage": "request",
            "engine": params["videoEngine"],
            "segments": [],
            "selectedResource": None,
        }
        updated = conn.execute(
            """
            UPDATE xiaozhi_tasks
            SET prompt = ?, status = 'queued', result_json = ?, error = '', updated_at = ?
            WHERE user_id = ? AND task_id = ? AND status IN ('waiting', 'waiting_for_user')
            """,
            (
                prompt,
                json.dumps(queued_result, ensure_ascii=False),
                now_iso(),
                int(user["id"]),
                str(task_id),
            ),
        )
        if int(updated.rowcount or 0) != 1:
            return jsonify({"code": 409, "msg": "视频任务状态已发生变化，请刷新后重试"}), 409
        refreshed = conn.execute(
            "SELECT * FROM xiaozhi_tasks WHERE user_id = ? AND task_id = ? LIMIT 1",
            (int(user["id"]), str(task_id)),
        ).fetchone()

    try:
        VIDEO_RESOURCE_EXECUTOR.submit(
            xiaozhi_run_resource_task,
            str(task_id),
            int(user["id"]),
            "generated_video",
            topic,
            params,
        )
    except QueueCapacityError:
        with auth_db() as conn:
            conn.execute(
                """
                UPDATE xiaozhi_tasks
                SET status = 'waiting', result_json = ?, error = ?, updated_at = ?
                WHERE user_id = ? AND task_id = ? AND status = 'queued'
                """,
                (
                    json.dumps({
                        **stored_result,
                        "message": "当前视频生成任务较多，参数已保留，请稍后再次确认",
                        "currentStage": "waiting_for_user",
                        "params": {**params, "deferred": True},
                    }, ensure_ascii=False),
                    "当前视频生成任务较多，请稍后再次确认",
                    now_iso(),
                    int(user["id"]),
                    str(task_id),
                ),
            )
        return jsonify({"code": 503, "msg": "当前视频生成任务较多，请稍后再次确认"}), 503
    task = xiaozhi_task_from_row(refreshed)
    return jsonify({
        "code": 0,
        "msg": "AI 视频工作流已启动",
        "data": {"task": task},
    }), 202

@app.get("/api/personalized-resources/mind-map/tasks")
def personalized_mindmap_tasks():
    """Return persisted mind-map tasks so generation survives page navigation."""
    user = g.get("current_user")
    if not user:
        return jsonify({"code": 401, "msg": "未登录"}), 401
    limit = max(1, min(60, request.args.get("limit", default=30, type=int) or 30))
    status = str(request.args.get("status") or "").strip().lower()
    allowed_statuses = {"queued", "running", "complete", "failed"}
    if status and status not in allowed_statuses:
        return jsonify({"code": 400, "msg": "status 必须是 queued、running、complete 或 failed"}), 400

    query = """
        SELECT task_id, task_type, title, prompt, status, route, result_json, error, created_at, updated_at
        FROM xiaozhi_tasks
        WHERE user_id = ? AND task_type = 'mindmap'
    """
    params: list[object] = [int(user["id"])]
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with auth_db() as conn:
        rows = conn.execute(query, params).fetchall()
    tasks = [xiaozhi_task_from_row(row) for row in rows]
    active_count = sum(1 for task in tasks if task.get("status") in {"queued", "running"})
    return jsonify({
        "code": 0,
        "data": {
            "tasks": tasks,
            "activeCount": active_count,
            "statusCounts": {
                task_status: sum(1 for task in tasks if task.get("status") == task_status)
                for task_status in ("queued", "running", "complete", "failed")
            },
        },
    })


@app.get("/api/personalized-resources/ppt/tasks")
def personalized_ppt_tasks():
    """Return persisted PPT jobs generated through the XiaoZhi/OhMyPPT pipeline."""
    user = g.get("current_user")
    if not user:
        return jsonify({"code": 401, "msg": "未登录"}), 401
    limit = max(1, min(60, request.args.get("limit", default=30, type=int) or 30))
    status = str(request.args.get("status") or "").strip().lower()
    allowed_statuses = {"queued", "running", "complete", "failed"}
    if status and status not in allowed_statuses:
        return jsonify({"code": 400, "msg": "status 必须是 queued、running、complete 或 failed"}), 400

    query = """
        SELECT task_id, task_type, title, prompt, status, route, result_json, error, created_at, updated_at
        FROM xiaozhi_tasks
        WHERE user_id = ? AND task_type = 'ppt'
    """
    params: list[object] = [int(user["id"])]
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with auth_db() as conn:
        rows = conn.execute(query, params).fetchall()
    tasks = [xiaozhi_task_from_row(row) for row in rows]
    active_count = sum(1 for task in tasks if task.get("status") in {"queued", "running"})
    return jsonify({
        "code": 0,
        "data": {
            "tasks": tasks,
            "activeCount": active_count,
            "statusCounts": {
                task_status: sum(1 for task in tasks if task.get("status") == task_status)
                for task_status in ("queued", "running", "complete", "failed")
            },
            "engine": "ohmyppt-fastapi",
        },
    })


@app.get("/api/learning-documents")
def learning_documents_list():
    user = g.get("current_user")
    if not user:
        return jsonify({"code": 401, "msg": "未登录"}), 401
    try:
        limit = max(1, min(int(request.args.get("limit") or 30), 100))
    except (TypeError, ValueError):
        limit = 30
    with auth_db() as conn:
        documents = list_learning_documents(conn, user_id=int(user["id"]), limit=limit)
    return jsonify({"code": 0, "data": {"documents": documents}})


@app.get("/api/learning-documents/<int:document_id>")
def learning_document_detail(document_id: int):
    user = g.get("current_user")
    if not user:
        return jsonify({"code": 401, "msg": "未登录"}), 401
    with auth_db() as conn:
        document = get_learning_document(conn, user_id=int(user["id"]), document_id=document_id)
    if not document:
        return jsonify({"code": 404, "msg": "课程讲义不存在"}), 404
    return jsonify({"code": 0, "data": {"document": document}})


def mcu_recommendation_bundle_for_user(user_id: int, payload: dict | None = None, limit: int = 5) -> dict:
    request_payload = dict(payload) if isinstance(payload, dict) else {}
    limit = max(1, min(int(limit or 5), 12))
    with auth_db() as conn:
        profile = latest_learning_profile_for_user(conn, int(user_id))
        rows = conn.execute(
            """
            SELECT experiment_id, experiment_name, passed, weak_points, created_at
            FROM mcu_experiments
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 60
            """,
            (int(user_id),),
        ).fetchall()
    history = [
        {
            "experiment_id": row["experiment_id"],
            "experiment_name": row["experiment_name"],
            "passed": bool(row["passed"]),
            "weak_points": json_loads_safe(row["weak_points"], []),
            "created_at": row["created_at"],
        }
        for row in rows
    ]
    return {
        "recommendations": recommend_mcu_experiments(
            request_payload,
            profile_context=profile,
            history=history,
            limit=limit,
        ),
        "profileBound": bool(profile),
        "historyCount": len(history),
    }


def resolve_mcu_agent_params_for_user(user_id: int, params: dict | None, topic: str = "") -> dict:
    raw_params = dict(params) if isinstance(params, dict) else {}
    requested_project = str(raw_params.get("projectId") or raw_params.get("project_id") or "").strip()
    auto_value = raw_params.get("autoRecommend")
    auto_recommend = (
        not requested_project
        if auto_value is None
        else auto_value is True or str(auto_value).strip().lower() in {"1", "true", "yes", "on"}
    )
    context = " ".join(
        str(value or "")
        for value in [
            topic,
            raw_params.get("topic"),
            raw_params.get("requirements"),
            raw_params.get("learningGoal"),
            raw_params.get("weakPoint"),
        ]
    )
    normalized = normalize_mcu_resource_params(raw_params, context)
    if raw_params.get("recommendationResolved") or not auto_recommend:
        normalized["autoRecommend"] = auto_recommend
        return normalized

    bundle = mcu_recommendation_bundle_for_user(
        int(user_id),
        {
            **normalized,
            "topic": context,
            "excludeCompleted": True,
        },
        limit=5,
    )
    recommendation = next(iter(bundle.get("recommendations") or []), None)
    if isinstance(recommendation, dict):
        detail = recommendation.get("recommendation") if isinstance(recommendation.get("recommendation"), dict) else {}
        normalized["board"] = str(recommendation.get("board") or normalized.get("board") or "arduino")
        normalized["projectId"] = str(recommendation.get("id") or normalized.get("projectId") or "")
        normalized["recommendationReason"] = str(detail.get("reason") or "按实验进阶顺序推荐")[:300]
        normalized["recommendationScore"] = int(detail.get("score") or 0)
    normalized["recommendationSource"] = (
        "profile-history"
        if bundle.get("profileBound") and bundle.get("historyCount")
        else ("active-profile" if bundle.get("profileBound") else "course-progression")
    )
    normalized["historyCount"] = int(bundle.get("historyCount") or 0)
    normalized["autoRecommend"] = True
    normalized["recommendationResolved"] = True
    return normalized


@app.get("/api/herb-models/catalog")
def herb_models_catalog_get():
    user = g.get("current_user")
    if not user:
        return jsonify({"code": 401, "msg": "未登录"}), 401
    items = public_herb_model_catalog()
    query_text = str(request.args.get("query") or "").strip().lower()
    if query_text:
        items = [
            item for item in items
            if query_text in " ".join(
                [item["name"], item["pinyin"], item["category"], item["medicinalPart"], *item["features"]]
            ).lower()
        ]
    return jsonify(
        {
            "code": 0,
            "data": {
                "revision": HERB_MODEL_REVISION,
                "count": len(items),
                "items": items,
                "usage": "历史三维模型兼容接口，当前嵌入式学习流程不再使用。",
            },
        }
    )


@app.get("/api/mcu/catalog")
def mcu_catalog_get():
    """Return the canonical MCU boards, pins, components, experiments, and sources."""
    user = g.get("current_user")
    if not user:
        return jsonify({"code": 401, "msg": "未登录"}), 401
    catalog = mcu_catalog_payload(
        board=request.args.get("board", ""),
        query=request.args.get("query", ""),
        difficulty=request.args.get("difficulty", ""),
        component=request.args.get("component", ""),
    )
    return jsonify({"code": 0, "data": catalog})


@app.post("/api/mcu/recommend")
@app.post("/api/mcu/recommendations")
def mcu_recommendations_post():
    """Recommend experiments from the active profile, weak points, and run history."""
    user = g.get("current_user")
    if not user:
        return jsonify({"code": 401, "msg": "未登录"}), 401
    payload = request.get_json(silent=True) or {}
    try:
        limit = max(1, min(int(payload.get("limit") or 5), 12))
    except (TypeError, ValueError):
        limit = 5
    return jsonify(
        {
            "code": 0,
            "data": mcu_recommendation_bundle_for_user(int(user["id"]), payload, limit),
        }
    )


@app.post("/api/mcu/flash")
def mcu_virtual_flash():
    """Validate source and wiring before a browser-side teaching simulation run."""
    user = g.get("current_user")
    if not user:
        return jsonify({"code": 401, "msg": "未登录"}), 401
    payload = request.get_json(silent=True) or {}
    result = validate_mcu_flash(payload)
    status = 200 if result.get("valid") else 422
    return jsonify(
        {
            "code": 0 if result.get("valid") else 422,
            "msg": "虚拟固件已通过检查" if result.get("valid") else "代码或接线检查未通过",
            "data": result,
        }
    ), status


@app.post("/api/mcu/save-experiment")
def mcu_save_experiment():
    """Save an MCU simulation result so learning-path / Q&A / assessment can read it."""
    user = g.get("current_user")
    if not user:
        return jsonify({"code": 401, "msg": "未登录"}), 401
    data = request.get_json(force=True, silent=True) or {}
    experiment_id = str(data.get("experiment_id") or data.get("experimentId") or "").strip()
    experiment = get_mcu_experiment(experiment_id)
    if not experiment:
        return jsonify({"code": 400, "msg": "实验编号不在受支持目录中"}), 400
    experiment_name = str(data.get("experiment_name") or data.get("experimentName") or experiment["title"]).strip()[:160]
    passed = 1 if data.get("passed") else 0
    weak_point_items = data.get("weak_points") if isinstance(data.get("weak_points"), list) else []
    weak_points = json.dumps([str(item)[:160] for item in weak_point_items[:20]], ensure_ascii=False)
    run_payload = data.get("run_data") if isinstance(data.get("run_data"), dict) else {}
    run_data = json.dumps(run_payload, ensure_ascii=False)
    if len(run_data.encode("utf-8")) > 20_000:
        return jsonify({"code": 413, "msg": "实验运行数据不能超过 20KB"}), 413
    created_at = now_iso()
    with auth_db() as conn:
        conn.execute(
            "INSERT INTO mcu_experiments (user_id, experiment_id, experiment_name, passed, weak_points, run_data, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user["id"], experiment_id, experiment_name, passed, weak_points, run_data, created_at),
        )
    return jsonify({"code": 0, "msg": "实验记录已保存"})


@app.get("/api/mcu/experiments")
def mcu_list_experiments():
    """Return recent MCU experiment records for the current user."""
    user = g.get("current_user")
    if not user:
        return jsonify({"code": 401, "msg": "未登录"}), 401
    limit = max(1, min(request.args.get("limit", 20, type=int) or 20, 100))
    with auth_db() as conn:
        rows = conn.execute(
            "SELECT id, experiment_id, experiment_name, passed, weak_points, run_data, created_at FROM mcu_experiments WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user["id"], limit),
        ).fetchall()
    items = []
    for r in rows:
        items.append({
            "id": r[0],
            "experiment_id": r[1],
            "experiment_name": r[2],
            "passed": bool(r[3]),
            "weak_points": json_loads_safe(r[4], []),
            "run_data": json_loads_safe(r[5], {}),
            "created_at": r[6],
        })
    return jsonify({"code": 0, "data": items})


PLATFORM_TOOLS.setdefault(
    "generated_video",
    {
        "agent": "personalized-resource-workflow",
        "label": "AI 视频生成智能体",
        "route": "/personalized-resources/video-generator",
        "description": "按需使用 Seedance 1.5 生成并由服务端自动剪辑讲解视频。",
        "skillId": "resource.generated-video.generate",
        "mcpServer": "resource-generation-mcp",
        "mcpTool": "resource.generated-video.generate",
        "handlerKey": "resource.generated_video.generate",
    },
)
XIAOZHI_RESOURCE_ROUTES = {tool_type: tool["route"] for tool_type, tool in PLATFORM_TOOLS.items()}
PROFILE_DRIVEN_TASK_TYPES = set(XIAOZHI_RESOURCE_ROUTES) - {
    "learning_background",
    "profile_update",
    "profile_management",
    "knowledge_base",
}

XIAOZHI_RESOURCE_LABELS = {
    tool_type: tool.get("label") or tool_type
    for tool_type, tool in PLATFORM_TOOLS.items()
}

XIAOZHI_MENTIONABLE_AGENTS = (
    {"id": XIAOZHI_MASTER_AGENT_ID, "name": "嵌小智总控智能体", "taskType": "", "aliases": ["嵌小智", "总控智能体"]},
    {"id": "learning-background-dialogue-agent", "name": "学习背景智能体", "taskType": "learning_background", "aliases": ["学习背景采集智能体"]},
    {"id": "learning-profile-agent", "name": "学习画像智能体", "taskType": "profile_update", "aliases": ["画像智能体"]},
    {"id": "learning-route-agent", "name": "学习路径智能体", "taskType": "learning_path", "aliases": ["学习路径规划智能体", "路径智能体"]},
    {"id": "learning-path-stage-agent", "name": "周任务规划智能体", "taskType": "learning_path_stage", "aliases": ["周任务智能体"]},
    {"id": "personalized-resource-workflow", "name": "个性化资源智能体", "taskType": "personalized_resources", "aliases": ["资源生成智能体", "资源智能体"]},
    {"id": "question-generator-workflow", "name": "题库生成智能体", "taskType": "question_bank", "aliases": ["题库智能体"]},
    {"id": "ppt-agent", "name": "PPT生成智能体", "taskType": "ppt", "aliases": ["PPT智能体", "ppt生成智能体"]},
    {"id": "learning-document-agent", "name": "课程讲义智能体", "taskType": "document", "aliases": ["讲义智能体"]},
    {"id": "mindmap-agent", "name": "思维导图智能体", "taskType": "mindmap", "aliases": ["导图智能体"]},
    {"id": "video-search-agent", "name": "视频检索智能体", "taskType": "video", "aliases": ["视频查找智能体"]},
    {"id": "generated-video-agent", "name": "AI视频生成智能体", "taskType": "generated_video", "aliases": ["AI视频智能体"]},
    {"id": "mcu-agent", "name": "单片机实验智能体", "taskType": "mcu", "aliases": ["MCU智能体", "实验智能体", "模拟器智能体"]},
    {"id": "interview-agent", "name": "学习访谈智能体", "taskType": "interview", "aliases": ["访谈智能体"]},
    {"id": "smart-tutor-agent", "name": "智能辅导智能体", "taskType": "smart_tutor", "aliases": ["辅导智能体"]},
    {"id": "learning-effect-assessment-agent", "name": "效果评估智能体", "taskType": "effect_assessment", "aliases": ["评估智能体"]},
    {"id": "learning-feedback-agent", "name": "学习反馈智能体", "taskType": "learning_feedback", "aliases": ["反馈智能体"]},
    {"id": "private-knowledge-agent", "name": "私有知识库智能体", "taskType": "knowledge_base", "aliases": ["知识库智能体", "知识检索智能体"]},
)

XIAOZHI_AGENT_PERSONAS = {
    XIAOZHI_MASTER_AGENT_ID: "负责汇总上下文、判断意图并协调平台智能体。",
    "learning-background-dialogue-agent": "负责通过自然对话了解学习经历、目标、基础、偏好与约束。",
    "learning-profile-agent": "负责解释十维学习画像、证据来源、能力特征与待补充信息。",
    "learning-route-agent": "负责依据画像规划阶段目标、周次节奏和平台能力闭环。",
    "learning-path-stage-agent": "负责把当前周目标拆成不同要求的具体任务和验收标准。",
    "personalized-resource-workflow": "负责协调知识检索、资源生成、审核和异步质量评分。",
    "question-generator-workflow": "负责嵌入式题目设计、难度分层、答案解析和错因诊断。",
    "ppt-agent": "负责嵌入式课程 PPT 的结构、逐页内容、讲解顺序和视觉表达。",
    "learning-document-agent": "负责基于可靠知识证据组织课程讲义、实验手册和复习材料。",
    "mindmap-agent": "负责梳理嵌入式概念层级、软硬件关系、调试链路和易混知识点。",
    "mcu-agent": "负责根据画像推荐合法实验预设，提供接线、代码、运行和调试入口。",
    "video-search-agent": "负责提炼检索关键词、筛选讲解视频并说明推荐依据。",
    "generated-video-agent": "负责设计 AI 讲解视频脚本、分镜、首图和生成参数；视频只在用户确认后生成。",
    "interview-agent": "负责开展学习访谈，通过追问获取可用于画像和路径调整的证据。",
    "smart-tutor-agent": "负责针对当前问题逐步启发、讲解和纠错，不直接替代用户完成学习。",
    "learning-effect-assessment-agent": "负责结合任务完成、测评和反馈分析学习效果及薄弱点。",
    "learning-feedback-agent": "负责记录资源体验、难度、完成结果并提炼后续调整信号。",
    "private-knowledge-agent": "负责拆分关键词，检索文档切块、QA 对、私有资料与知识图谱并说明证据来源。",
}


try:
    import learning_path_service as _learning_path_service
    import xiaozhi_service as _xiaozhi_service
except ImportError:  # pragma: no cover - package import fallback
    from . import learning_path_service as _learning_path_service
    from . import xiaozhi_service as _xiaozhi_service

def _bind_service_export(service_module, service_name, provider):
    service_function = getattr(service_module, service_name)

    @wraps(service_function)
    def app_bound_service(*args, **kwargs):
        service_module.configure(provider)
        return service_function(*args, **kwargs)

    return app_bound_service


_service_provider = lambda name: globals()[name]
_service_modules = (_learning_path_service, _xiaozhi_service)
for _service_module in _service_modules:
    for _service_name in _service_module.EXPORTED_FUNCTIONS:
        globals()[_service_name] = _bind_service_export(
            _service_module,
            _service_name,
            _service_provider,
        )
del _service_module, _service_modules, _service_name






RESOURCE_AGENT_TYPE_ALIASES = {
    "question-bank": "question_bank",
    "questionBank": "question_bank",
    "question": "question_bank",
    "quiz": "question_bank",
    "exam": "question_bank",
    "ppt_h5": "ppt",
    "presentation": "ppt",
    "handout": "document",
    "learning-document": "document",
    "learning_document": "document",
    "mind-map": "mindmap",
    "mind_map": "mindmap",
    "video-search": "video",
    "video-generator": "generated_video",
    "generated-video": "generated_video",
    "generated_video": "generated_video",
    "video_search": "video",
    "animated-lesson": "animation",
    "animated_lesson": "animation",
    "learning-animation": "animation",
    "learning_animation": "animation",
    "mcu-simulator": "mcu",
    "mcu_simulator": "mcu",
    "simulator": "mcu",
    "knowledge-base": "knowledge_base",
    "knowledge_base": "knowledge_base",
    "private-knowledge": "knowledge_base",
    "profile-management": "profile_management",
    "profile_management": "profile_management",
    "feedback": "learning_feedback",
    "learning-feedback": "learning_feedback",
    "learning_feedback": "learning_feedback",
    "resource-package": "personalized_resources",
    "resource_package": "personalized_resources",
    "resources": "personalized_resources",
}

RESOURCE_AGENT_ALLOWED_TYPES = {
    "personalized_resources",
    "question_bank",
    "ppt",
    "document",
    "mindmap",
    "video",
    "generated_video",
    "animation",
    "mcu",
    "knowledge_base",
    "profile_management",
    "learning_feedback",
}

XIAOZHI_TASK_COMMAND_MARKERS = (
    "生成",
    "制作",
    "创建",
    "准备",
    "查找",
    "搜索",
    "推荐",
    "打开",
    "启动",
    "进入",
    "运行",
    "规划",
    "细化",
    "评估",
    "开始",
    "调用",
    "采集",
    "补全",
    "更新",
    "刷新",
    "重置",
    "切换",
    "列出",
    "查看",
    "辅导",
    "答疑",
    "完成",
    "学完",
    "反馈",
    "巩固",
    "出题",
    "来一份",
    "出一套",
)
XIAOZHI_RESOURCE_CREATION_MARKERS = (
    "生成",
    "制作",
    "创建",
    "准备",
    "查找",
    "搜索",
    "推荐",
    "打开",
    "启动",
    "进入",
    "运行",
    "出题",
    "来一份",
    "出一套",
)
XIAOZHI_DIAGNOSTIC_MARKERS = (
    "为什么",
    "怎么理解",
    "哪里错",
    "失败",
    "报错",
    "不工作",
    "没反应",
    "不会",
    "不明白",
)










































































LEARNING_PATH_RESOURCE_MAX_PLANNING_ATTEMPTS = 2
LEARNING_PATH_RESOURCE_MAX_GENERATION_ATTEMPTS = 2


































def _recover_learning_path_resource_generation_after_restart() -> dict:
    """Fail interrupted workers, then requeue persisted active learning paths."""
    with auth_db() as conn:
        recovered_tasks = recover_interrupted_xiaozhi_tasks(conn)
        user_rows = conn.execute(
            """
            SELECT DISTINCT user_id FROM user_learning_path_configs
            UNION
            SELECT DISTINCT user_id FROM learning_path_profile_configs
            ORDER BY user_id
            """
        ).fetchall()

    queued_video_covers = _queue_waiting_generated_video_covers_after_restart()

    queued_users = 0
    queued_stages = 0
    for row in user_rows:
        user_id = int(row["user_id"])
        try:
            with auth_db() as conn:
                config = read_learning_path_config(conn, user_id)
            if not isinstance(config, dict) or learning_path_config_is_degraded(config):
                continue
            submitted = _queue_learning_path_week_resource_preparation(
                user_id,
                config,
                only_incomplete=True,
                max_stages=1,
            )
            if submitted:
                queued_users += 1
                queued_stages += submitted
        except Exception:
            app.logger.exception(
                "learning path startup resource recovery failed for user=%s",
                user_id,
            )

    result = {
        "recoveredTasks": recovered_tasks,
        "queuedUsers": queued_users,
        "queuedStages": queued_stages,
        "queuedVideoCovers": queued_video_covers,
    }
    if recovered_tasks or queued_stages or queued_video_covers:
        app.logger.warning(
            "Learning-path resource recovery finished: interrupted=%s users=%s stages=%s video-covers=%s",
            recovered_tasks,
            queued_users,
            queued_stages,
            queued_video_covers,
        )
    return result


def start_learning_path_resource_recovery() -> bool:
    """Start persisted learning-path resource recovery once per backend process."""
    global _learning_path_resource_recovery_started
    with _LEARNING_PATH_RESOURCE_RECOVERY_LOCK:
        if _learning_path_resource_recovery_started:
            return False
        try:
            _recover_learning_path_resource_generation_after_restart()
        except Exception:
            app.logger.exception("learning path startup resource recovery failed")
            return False
        _learning_path_resource_recovery_started = True
    return True


@app.before_request
def _ensure_learning_path_resource_recovery_started() -> None:
    if not app.config.get("TESTING"):
        start_learning_path_resource_recovery()


































@app.get("/api/llm/runtime")
def llm_runtime_get():
    user, error_response = xiaozhi_current_user()
    if error_response:
        return error_response
    return jsonify({"code": 0, "msg": "ok", "data": llm_runtime_for_user(int(user["id"]))})


@app.post("/api/llm/messages")
def llm_messages():
    user, error_response = xiaozhi_current_user()
    if error_response:
        return error_response
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": {"message": "请求体必须是 JSON 对象", "code": "INVALID_REQUEST"}}), 400
    try:
        return jsonify(run_user_llm_completion(int(user["id"]), payload))
    except ValueError as exc:
        return jsonify({"error": {"message": str(exc), "code": "INVALID_REQUEST"}}), 400
    except Exception as exc:
        app.logger.warning("[LLMGateway] request failed user=%s error=%s", user["id"], public_llm_error(exc))
        return jsonify({"error": {"message": public_llm_error(exc), "code": "MODEL_REQUEST_FAILED"}}), 502
























































XIAOZHI_LEARNING_PATH_CANDIDATE_FIELD = "_candidateLearningPathConfig"








def xiaozhi_latest_task_for_type(tasks: list[dict], task_type: str) -> dict | None:
    return next((item for item in tasks if item.get("taskType") == task_type), None)


def xiaozhi_tool_agent_status(tool_type: str, tasks: list[dict], context: dict, question_status: dict) -> tuple[str, str]:
    task = xiaozhi_latest_task_for_type(tasks, tool_type)
    if task:
        status = task.get("status") or "idle"
        result = task.get("result") if isinstance(task.get("result"), dict) else {}
        progress = result.get("progress")
        message = result.get("message") or result.get("currentStage") or ""
        if status == "failed":
            detail = task.get("error") or "最近一次 Hermes 调度任务失败"
        elif status == "complete":
            detail = message or ("最近任务已完成：" + (task.get("title") or task.get("taskId") or ""))
        elif progress is not None:
            detail = f"进度 {progress}%：" + (message or task.get("title") or task.get("taskId") or "")
        else:
            detail = "最近任务：" + (task.get("title") or task.get("taskId") or "")
        return status, detail

    if tool_type == "profile_update":
        return ("ready" if context.get("profile") else "idle", "最近画像报告：" + (context.get("profileCreatedAt") or "暂无"))
    if tool_type == "question_bank" and question_status:
        return (question_status.get("status") or "idle", question_status.get("payload", {}).get("message") or "等待生成任务")
    if tool_type == "interview":
        return "ready", "学习访谈问答、追问、视觉分析与评分接口可用"
    if tool_type == "learning_background":
        return "ready", "可继续采集学习背景并补全画像上下文"
    if tool_type == "learning_path":
        return "ready" if context.get("profile") or context.get("questionnaire") else "idle", "基于学习画像生成个性化路径"
    if tool_type == "learning_path_stage":
        return "ready" if context.get("profile") or context.get("questionnaire") else "idle", "基于路径阶段生成目标、资源与检查点"
    if tool_type == "mcu":
        return "unavailable", "旧实验模块已下线，历史记录仅保留兼容读取"
    return "ready", PLATFORM_TOOLS.get(tool_type, {}).get("description") or "Hermes 可调度平台智能体"


def _xiaozhi_api_dependency(name: str):
    return globals()[name]


app.register_blueprint(create_xiaozhi_api_blueprint(_xiaozhi_api_dependency))


@app.get("/api/ai-config")
def ai_config():
    """Return AI provider configuration for frontend display only (no secrets)."""
    base_url = get_setting("ANTHROPIC_BASE_URL", setting_default("ANTHROPIC_BASE_URL"))
    model = get_setting("ANTHROPIC_MODEL", setting_default("ANTHROPIC_MODEL"))
    auth_token = get_setting("ANTHROPIC_AUTH_TOKEN", setting_default("ANTHROPIC_AUTH_TOKEN"))
    return jsonify({
        "baseUrl": base_url or "https://maas-coding-api.cn-huabei-1.xf-yun.com/anthropic",
        "model": model or DEFAULT_TEXT_MODEL_ID,
        "hasToken": bool(auth_token),
    })


@app.post("/api/ai-proxy")
def ai_proxy():
    """Server-side proxy for Anthropic API calls — keeps auth token off the frontend."""
    import urllib.request
    import urllib.error

    payload = request.get_json(silent=True) or {}
    prompt = payload.get("prompt", "")
    max_tokens = max(LLM_RESPONSE_TOKEN_BUDGET, int(payload.get("max_tokens", LLM_RESPONSE_TOKEN_BUDGET)))
    system_prompt = payload.get("system", "")

    base_url = get_setting("ANTHROPIC_BASE_URL", setting_default("ANTHROPIC_BASE_URL")) or "https://maas-coding-api.cn-huabei-1.xf-yun.com/anthropic"
    model = get_setting("ANTHROPIC_MODEL", setting_default("ANTHROPIC_MODEL")) or DEFAULT_TEXT_MODEL_ID
    auth_token = get_setting("ANTHROPIC_AUTH_TOKEN", setting_default("ANTHROPIC_AUTH_TOKEN"))

    if not auth_token:
        return jsonify({"error": "AI API 未配置，请在后端配置 ANTHROPIC_AUTH_TOKEN"}), 503

    messages = payload.get("messages", [{"role": "user", "content": prompt}])
    body = {"model": model, "max_tokens": max_tokens, "messages": messages}
    if system_prompt:
        body["system"] = system_prompt

    req = urllib.request.Request(
        build_anthropic_messages_url(base_url),
        data=json.dumps(body).encode("utf-8"),
        headers=create_llm_headers(auth_token, anthropic=True),
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="ignore")
        return jsonify({"error": f"AI API 返回错误: {exc.code}", "detail": body_text}), 502
    except Exception as exc:
        return jsonify({"error": f"AI API 请求失败: {str(exc)}"}), 502

    return jsonify(result)


@app.post("/api/ai-proxy-stream")
def ai_proxy_stream():
    """Stream Anthropic text deltas as small SSE events for chat UIs."""
    import urllib.request
    import urllib.error

    payload = request.get_json(silent=True) or {}
    prompt = payload.get("prompt", "")
    max_tokens = max(LLM_RESPONSE_TOKEN_BUDGET, int(payload.get("max_tokens", LLM_RESPONSE_TOKEN_BUDGET)))
    system_prompt = payload.get("system", "")

    base_url = get_setting("ANTHROPIC_BASE_URL", setting_default("ANTHROPIC_BASE_URL")) or "https://maas-coding-api.cn-huabei-1.xf-yun.com/anthropic"
    model = get_setting("ANTHROPIC_MODEL", setting_default("ANTHROPIC_MODEL")) or DEFAULT_TEXT_MODEL_ID
    auth_token = get_setting("ANTHROPIC_AUTH_TOKEN", setting_default("ANTHROPIC_AUTH_TOKEN"))

    if not auth_token:
        return jsonify({"error": "AI API 未配置，请在后端配置 ANTHROPIC_AUTH_TOKEN"}), 503

    messages = payload.get("messages", [{"role": "user", "content": prompt}])
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
        "stream": True,
    }
    if system_prompt:
        body["system"] = system_prompt

    req = urllib.request.Request(
        build_anthropic_messages_url(base_url),
        data=json.dumps(body).encode("utf-8"),
        headers=create_llm_headers(auth_token, anthropic=True, stream=True),
        method="POST",
    )

    def emit(payload_obj):
      return f"data: {json.dumps(payload_obj, ensure_ascii=False)}\n\n"

    @stream_with_context
    def generate_events():
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8", errors="ignore").strip()
                    if not line.startswith("data:"):
                        continue
                    data_text = line[5:].strip()
                    if not data_text or data_text == "[DONE]":
                        continue
                    try:
                        event = json.loads(data_text)
                    except json.JSONDecodeError:
                        continue

                    if event.get("type") == "error":
                        yield emit({"type": "error", "error": event.get("error") or event})
                        return

                    delta = event.get("delta") or {}
                    text = delta.get("text")
                    if text:
                        yield emit({"type": "delta", "text": text})

                    if event.get("type") == "message_stop":
                        yield emit({"type": "done"})
                        return
                yield emit({"type": "done"})
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="ignore")
            yield emit({"type": "error", "error": f"AI API 返回错误: {exc.code}", "detail": body_text})
        except Exception as exc:
            yield emit({"type": "error", "error": f"AI API 请求失败: {str(exc)}"})

    return Response(generate_events(), mimetype="text/event-stream")


@app.get("/api/ppt-h5/health")
def ppt_h5_health_route():
    status = ppt_h5_health()
    return jsonify(status), (200 if status.get("ok") else 503)


def _json_list(value):
    if isinstance(value, list):
        return value
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (TypeError, json.JSONDecodeError):
        return []


@app.get("/api/ppt-h5/styles")
def ppt_h5_styles_route():
    db_path = BASE_DIR / "ppth5" / "ohmyppt.dev.db"
    if not db_path.exists():
        return jsonify({"items": []})

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            select id, style, style_name, description, category, aliases,
                   source, style_skill, style_case, created_at, updated_at
            from styles
            where coalesce(source, '') <> 'builtin'
            order by coalesce(updated_at, created_at, 0) desc, style_name asc
            """
        ).fetchall()
    except sqlite3.Error as exc:
        app.logger.exception("failed to read ppt h5 styles")
        return jsonify({"error": str(exc)}), 500
    finally:
        if conn is not None:
            conn.close()

    items = []
    for row in rows:
        style_key = row["style"] or row["id"]
        items.append(
            {
                "id": row["id"] or style_key,
                "styleKey": style_key,
                "label": row["style_name"] or style_key,
                "description": row["description"] or "",
                "aliases": _json_list(row["aliases"]),
                "category": row["category"] or "自定义",
                "source": row["source"] or "custom",
                "editable": True,
                "styleSkill": row["style_skill"] or "",
                "styleCase": row["style_case"] or "",
                "createdAt": row["created_at"] or 0,
                "updatedAt": row["updated_at"] or 0,
            }
        )
    return jsonify({"items": items})


@app.get("/api/ppt-h5/status")
def ppt_h5_status_route():
    user = g.get("current_user")
    if not user:
        return jsonify({"code": 401, "msg": "未登录"}), 401
    return jsonify(_ppt_task_snapshot(int(user["id"])))


@app.post("/api/ppt-h5/generate-background")
def ppt_h5_generate_background_route():
    user = g.get("current_user")
    if not user:
        return jsonify({"code": 401, "msg": "未登录"}), 401

    user_id = int(user["id"])
    current_task = _ppt_task_snapshot(user_id)
    if current_task.get("status") == "running":
        task_id = current_task.get("taskId") or current_task.get("payload", {}).get("taskId") or ""
        current_session_id = str(current_task.get("meta", {}).get("sessionId") or "").strip()
        current_route = (
            f"/ppt-generator/generating/{quote(current_session_id, safe='')}"
            if current_session_id
            else "/personalized-resources/ppt"
        )
        return jsonify({
            "code": 0,
            "data": {
                "task": {
                    "taskId": task_id,
                    "taskType": "ppt",
                    "title": current_task.get("meta", {}).get("title") or "PPT生成智能体",
                    "status": "running",
                    "route": xiaozhi_route_with_task(current_route, task_id),
                    "result": {
                        "message": current_task.get("payload", {}).get("message") or "PPT 正在生成中",
                        "progress": current_task.get("progress") or current_task.get("payload", {}).get("progress") or 0,
                        "logs": current_task.get("logs") or [],
                    },
                },
                "pptTask": current_task,
            },
        }), 202

    payload = request.get_json(silent=True) or {}
    session_id = str(payload.get("sessionId") or f"ppt_{int(time.time() * 1000)}").strip()
    topic = str(payload.get("topic") or "嵌入式学习课件").strip() or "嵌入式学习课件"
    user_message = str(payload.get("userMessage") or "").strip()
    try:
        page_count = max(1, min(20, int(payload.get("pageCount") or 5)))
    except (TypeError, ValueError):
        page_count = 5
    title = f"{topic[:32]} · PPT生成智能体"
    generation_route = f"/ppt-generator/generating/{quote(session_id, safe='')}"
    task_id = xiaozhi_create_task(user_id, "ppt", title, user_message or topic, generation_route)
    task_meta = _ppt_task_meta(task_id=task_id, session_id=session_id, topic=topic, page_count=page_count)
    task_logs: list[dict] = []

    def sync_xiaozhi_progress(stage_payload: dict, status: str = "running", result: dict | None = None, error: dict | None = None):
        progress = _safe_progress(stage_payload.get("progress"), 0)
        log_entry = {
            "time": utc_timestamp(),
            "stage": stage_payload.get("stage") or "progress",
            "message": stage_payload.get("message") or "",
            "progress": progress,
        }
        if not task_logs or task_logs[-1].get("stage") != log_entry["stage"] or task_logs[-1].get("message") != log_entry["message"]:
            task_logs.append(log_entry)
        task_result = {
            "message": stage_payload.get("message") or "",
            "topic": topic,
            "progress": progress,
            "currentStage": stage_payload.get("stage") or "",
            "logs": task_logs[-40:],
            "sessionId": session_id,
            "ohmyPptSessionId": session_id,
            "pageCount": page_count,
            "agentRuns": [
                {"name": "PPT任务规划智能体", "status": "complete" if progress >= 18 else "running", "detail": "解析主题、页数和风格约束"},
                {"name": "OhMyPPT生成智能体", "status": "complete" if progress >= 88 else ("running" if progress >= 18 else "queued"), "detail": "通过独立 FastAPI 引擎生成 H5 页面"},
                {"name": "页面审核智能体", "status": "complete" if progress >= 98 else ("running" if progress >= 88 else "queued"), "detail": "校验页数、HTML 安全与课件质量"},
            ],
            "engine": "ohmyppt-fastapi",
        }
        if result is not None:
            task_result["ppt"] = result
            task_result["message"] = stage_payload.get("message") or "PPT 已生成完成"
        if error is not None:
            task_result["error"] = error
        xiaozhi_update_task(task_id, status=status, result_json=task_result, error=(error or {}).get("details", ""))

    start_payload = {
        "stage": "start",
        "message": "PPT 后台生成任务已启动",
        "progress": 5,
        "taskId": task_id,
        "meta": task_meta,
    }
    sync_xiaozhi_progress(start_payload, status="running")
    _update_ppt_task(
        user_id,
        taskId=task_id,
        status="running",
        event="start",
        payload=start_payload,
        result=None,
        error=None,
        meta=task_meta,
        progress=5,
    )

    def worker():
        try:
            def on_orchestration_event(stage_payload: dict):
                stage_payload = {**stage_payload, "taskId": task_id, "meta": task_meta}
                sync_xiaozhi_progress(stage_payload, status="running")
                _update_ppt_task(
                    user_id,
                    status="running",
                    event="progress",
                    payload=stage_payload,
                )

            result = xiaozhi_generate_ppt_managed(
                {**payload, "sessionId": session_id, "topic": topic, "pageCount": page_count},
                user_id,
                task_id=task_id,
                on_event=on_orchestration_event,
            )
            result.setdefault("sessionId", session_id)
            result.setdefault("ohmyPptSessionId", session_id)
            result.setdefault("pageCount", page_count)
            result.setdefault("route", xiaozhi_route_with_task(generation_route, task_id))
            if isinstance(result.get("ppt"), dict):
                result["ppt"].setdefault("sessionId", session_id)
                result["ppt"].setdefault("pageCount", page_count)
                result["ppt"].setdefault("route", xiaozhi_route_with_task(generation_route, task_id))
            done_payload = {
                "stage": "complete",
                "message": f"PPT 已生成完成，共 {len(result.get('pages') or [])} 页",
                "progress": 100,
                "taskId": task_id,
                "meta": task_meta,
            }
            sync_xiaozhi_progress(done_payload, status="complete", result=result)
            _update_ppt_task(user_id, status="complete", event="result", payload=done_payload, result=result, error=None, progress=100)
        except Exception as exc:
            app.logger.exception("ppt h5 background generation failed")
            response = {"error": "PPT 生成失败", "details": str(exc)}
            error_payload = {
                "stage": "error",
                "message": str(exc) or "PPT 生成失败",
                "progress": 100,
                "taskId": task_id,
                "meta": task_meta,
                "response": response,
            }
            sync_xiaozhi_progress(error_payload, status="failed", error=response)
            _update_ppt_task(user_id, status="error", event="error", payload=error_payload, result=None, error=response, progress=100)

    threading.Thread(target=worker, daemon=True).start()
    snapshot = _ppt_task_snapshot(user_id)
    return jsonify({
        "code": 0,
        "data": {
            "task": {
                "taskId": task_id,
                "taskType": "ppt",
                "title": title,
                "prompt": user_message or topic,
                "status": "running",
                    "route": xiaozhi_route_with_task(generation_route, task_id),
                "result": {
                    "message": start_payload["message"],
                    "topic": topic,
                    "progress": 5,
                    "currentStage": "start",
                    "logs": task_logs[-40:],
                    "sessionId": session_id,
                    "ohmyPptSessionId": session_id,
                    "pageCount": page_count,
                    "engine": "ohmyppt-fastapi",
                },
                "error": "",
                "createdAt": task_meta["created_at"],
                "updatedAt": utc_timestamp(),
            },
            "pptTask": snapshot,
        },
    }), 202


@app.post("/api/ppt-h5/generate")
def ppt_h5_generate_route():
    user = g.get("current_user")
    if not user:
        return jsonify({"code": 401, "msg": "未登录"}), 401
    payload = request.get_json(silent=True) or {}
    payload.setdefault("sessionId", f"ppt_{int(time.time() * 1000)}_{secrets.token_hex(3)}")
    try:
        return jsonify(xiaozhi_generate_ppt_managed(payload, int(user["id"])))
    except Exception as exc:
        app.logger.exception("ppt h5 generation failed")
        return jsonify({"error": str(exc)}), 502


app.register_blueprint(
    create_interview_blueprint(
        InterviewRouteDependencies(
            run_orchestrated=xiaozhi_run_orchestrated,
            runtime_setting_overrides=xiaozhi_runtime_setting_overrides,
            llm_runtime=llm_runtime_for_user,
            public_llm_error=public_llm_error,
            skill_review_error=SkillReviewError,
            generate_question=lambda context: generate_interview_question(context),
            generate_followup=lambda context, answer: generate_interview_followup(context, answer),
            analyze_frame=lambda *args, **kwargs: analyze_interview_frame(*args, **kwargs),
        )
    )
)

@app.get("/admin")
@app.get("/admin/")
@app.get("/admin/<path:admin_path>")
def serve_single_port_admin(admin_path: str = ""):
    """Serve the compiled admin SPA at /admin/ from the unified API origin."""
    index_file = ADMIN_DIST_DIR / "index.html"
    if not index_file.is_file():
        return jsonify({"code": 503, "msg": "Admin build is missing. Run pnpm run build in admin."}), 503
    requested_file = (ADMIN_DIST_DIR / admin_path).resolve()
    if admin_path and ADMIN_DIST_DIR.resolve() in requested_file.parents and requested_file.is_file():
        return send_file(requested_file)
    if admin_path and Path(admin_path).suffix:
        return jsonify({"code": 404, "msg": "Admin static asset not found"}), 404
    return send_file(index_file)

@app.get("/")
@app.get("/<path:frontend_path>")
def serve_single_port_frontend(frontend_path: str = ""):
    """Serve the compiled SPA from the API origin without shadowing API routes."""
    if frontend_path.startswith(("api/", "ppt-api/")):
        return jsonify({"code": 404, "msg": "Not found"}), 404
    if frontend_path == "m" or frontend_path.startswith("m/"):
        mobile_root = MOBILE_DIST_DIR.resolve()
        mobile_index = mobile_root / "index.html"
        if not mobile_index.is_file():
            return jsonify({"code": 503, "msg": "Mobile frontend build is missing."}), 503
        mobile_path = frontend_path[2:].lstrip("/")
        requested_mobile_file = (mobile_root / mobile_path).resolve()
        if mobile_path and mobile_root in requested_mobile_file.parents and requested_mobile_file.is_file():
            return send_file(requested_mobile_file)
        if mobile_path and Path(mobile_path).suffix:
            return jsonify({"code": 404, "msg": "Mobile static asset not found"}), 404
        return send_file(mobile_index)
    index_file = FRONTEND_DIST_DIR / "index.html"
    if not index_file.is_file():
        return jsonify({"code": 503, "msg": "Frontend build is missing. Run npm run build in frontend."}), 503
    frontend_root = FRONTEND_DIST_DIR.resolve()
    requested_file = (frontend_root / frontend_path).resolve()
    is_inside_frontend = requested_file == frontend_root or frontend_root in requested_file.parents
    if frontend_path and is_inside_frontend and requested_file.is_file():
        return send_file(requested_file)
    if frontend_path and Path(frontend_path).suffix:
        return jsonify({"code": 404, "msg": "Static asset not found"}), 404
    if frontend_path == "ppt" or frontend_path.startswith("ppt/"):
        ppt_index_file = frontend_root / "ppt" / "index.html"
        if ppt_index_file.is_file():
            return send_file(ppt_index_file)
        return jsonify({"code": 503, "msg": "PPT frontend build is missing."}), 503
    return send_file(index_file)

@app.get("/api/<path:_path>")
@app.post("/api/<path:_path>")
@app.put("/api/<path:_path>")
@app.delete("/api/<path:_path>")
def disabled_api(_path: str):
    return jsonify({"code": 404, "msg": "该功能已删除"}), 404


if __name__ == "__main__":
    start_learning_path_resource_recovery()
    port = int(get_setting("PORT", "3000"))
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
