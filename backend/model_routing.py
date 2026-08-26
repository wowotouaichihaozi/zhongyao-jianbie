"""Central model-routing metadata for text and multimodal agent inputs."""

from __future__ import annotations

from typing import Any

try:
    from api_config import setting_default
    from common import get_setting
except ImportError:  # pragma: no cover - package-style import fallback
    from .api_config import setting_default
    from .common import get_setting


DEFAULT_TEXT_MODEL_ID = "astron-code-latest"
DEFAULT_VISION_MODEL_ID = "qwen3-vl-plus"
DEFAULT_AUDIO_MODEL_ID = "qwen3-omni-flash"
DEFAULT_CONTEXT_WINDOW = 262_144

MODEL_DISPLAY_NAMES = {
    DEFAULT_TEXT_MODEL_ID: "Spark X2 Flash",
    DEFAULT_VISION_MODEL_ID: "Qwen3-VL-Plus",
    DEFAULT_AUDIO_MODEL_ID: "Qwen3-Omni-Flash",
    "deepseek-v4-flash": "DeepSeek V4 Flash",
    "deepseek-v4-flash-vision-exp": "DeepSeek V4 Flash Vision",
}


def _positive_int(value: object, default: int) -> int:
    try:
        parsed = int(str(value or "").strip())
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def model_display_name(model_id: object) -> str:
    normalized = str(model_id or "").strip()
    return MODEL_DISPLAY_NAMES.get(normalized, normalized or "unknown")


def resolve_model_routing(runtime_settings: dict[str, str] | None = None) -> dict[str, Any]:
    """Return the effective text model and deterministic multimodal handoffs."""
    settings = runtime_settings or {}
    protocol = str(
        settings.get("LLM_PROTOCOL")
        or get_setting("LLM_PROTOCOL", "auto")
        or "auto"
    ).strip().lower()
    text_model = str(
        settings.get("ANTHROPIC_MODEL")
        or get_setting(
            "ANTHROPIC_MODEL",
            setting_default("ANTHROPIC_MODEL", DEFAULT_TEXT_MODEL_ID),
        )
        or DEFAULT_TEXT_MODEL_ID
    ).strip()
    text_context_window = _positive_int(
        settings.get("LLM_CONTEXT_WINDOW")
        or get_setting("LLM_CONTEXT_WINDOW", str(DEFAULT_CONTEXT_WINDOW)),
        DEFAULT_CONTEXT_WINDOW,
    )
    vision_model = str(
        settings.get("VISION_LLM_MODEL")
        or get_setting(
            "VISION_LLM_MODEL",
            setting_default("VISION_LLM_MODEL", DEFAULT_VISION_MODEL_ID),
        )
        or DEFAULT_VISION_MODEL_ID
    ).strip()
    vision_context_window = _positive_int(
        settings.get("VISION_LLM_CONTEXT_WINDOW")
        or get_setting("VISION_LLM_CONTEXT_WINDOW", str(DEFAULT_CONTEXT_WINDOW)),
        DEFAULT_CONTEXT_WINDOW,
    )
    audio_model = str(
        settings.get("AUDIO_LLM_MODEL")
        or get_setting(
            "AUDIO_LLM_MODEL",
            setting_default("AUDIO_LLM_MODEL", DEFAULT_AUDIO_MODEL_ID),
        )
        or DEFAULT_AUDIO_MODEL_ID
    ).strip()
    audio_context_window = _positive_int(
        settings.get("AUDIO_LLM_CONTEXT_WINDOW")
        or get_setting("AUDIO_LLM_CONTEXT_WINDOW", "32768"),
        32_768,
    )
    if protocol == "anthropic":
        base_url = settings.get("ANTHROPIC_BASE_URL") or get_setting("ANTHROPIC_BASE_URL", "")
    else:
        base_url = (
            settings.get("OPENAI_BASE_URL")
            or get_setting("OPENAI_BASE_URL", "")
            or settings.get("ANTHROPIC_BASE_URL")
            or get_setting("ANTHROPIC_BASE_URL", "")
        )

    text_target = {
        "agentId": "spark-text-reasoning-agent",
        "modelName": model_display_name(text_model),
        "modelId": text_model,
        "contextWindow": text_context_window,
        "input": ["text"],
    }
    return {
        "protocol": protocol,
        "baseUrl": str(base_url or "").strip(),
        "model": text_model,
        "modelName": model_display_name(text_model),
        "contextWindow": text_context_window,
        "customized": bool(runtime_settings),
        "routing": {
            "text": dict(text_target),
            "image": {
                "agentId": "qwen-multimodal-evidence-agent",
                "provider": "Alibaba Bailian",
                "modelName": model_display_name(vision_model),
                "modelId": vision_model,
                "contextWindow": vision_context_window,
                "input": ["image", "text"],
                "output": "grounded_visual_evidence_text",
                "handoffTo": dict(text_target),
            },
            "audio": {
                "agentId": "qwen-multimodal-evidence-agent",
                "provider": "Alibaba Bailian",
                "modelName": model_display_name(audio_model),
                "modelId": audio_model,
                "contextWindow": audio_context_window,
                "input": ["audio", "text"],
                "output": "grounded_audio_evidence_text",
                "handoffTo": dict(text_target),
            },
            "document": {
                "agentId": "document-text-extraction-agent",
                "processor": "local-structured-text-extraction",
                "input": ["document"],
                "output": "extracted_document_text",
                "handoffTo": dict(text_target),
            },
        },
    }


def public_input_route(media_kind: object) -> dict[str, Any]:
    routing = resolve_model_routing().get("routing") or {}
    kind = str(media_kind or "").strip().lower()
    if kind == "image":
        return dict(routing.get("image") or {})
    if kind == "audio":
        return dict(routing.get("audio") or {})
    if kind == "document":
        return dict(routing.get("document") or {})
    return {
        "agentId": "multimodal-input-router",
        "input": [kind or "file"],
        "output": "registered_learning_evidence",
        "handoffTo": dict(routing.get("text") or {}),
    }
