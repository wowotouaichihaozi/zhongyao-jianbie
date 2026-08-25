from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import requests

try:
    from agent_manifest import PLATFORM_TOOLS
    from common import get_setting
    from learning_agents import extract_json
    from question_generator_runtime import (
        _anthropic_base_to_chat_url,
        get_mimo_api_key,
        get_mimo_model,
        resolve_mimo_api_url,
    )
except ImportError:  # pragma: no cover - package-style import fallback
    from .agent_manifest import PLATFORM_TOOLS
    from .common import get_setting
    from .learning_agents import extract_json
    from .question_generator_runtime import (
        _anthropic_base_to_chat_url,
        get_mimo_api_key,
        get_mimo_model,
        resolve_mimo_api_url,
    )


HERMES_XIAOZHI_AGENT_ID = "xiaozhi-companion-agent"
HERMES_XIAOZHI_AGENT_NAME = "XiaoZhi Companion Agent"
HERMES_RUNTIME = "hermes-agent"
HERMES_SOURCE = "hermes_agent"
DEFAULT_MODEL = "astron-code-latest"

ALLOWED_INTENTS = {"chat", "generate_resource", "update_profile", "profile_management"}
ALLOWED_PROFILE_ACTIONS = {"list", "activate", "refresh", "reset"}
ALLOWED_RESOURCE_TYPES = {"none", *PLATFORM_TOOLS.keys()}
RESOURCE_ALIASES = {
    "learning_profile": "profile_update",
    "profile": "profile_update",
    "resource": "personalized_resources",
    "resources": "personalized_resources",
    "quiz": "question_bank",
    "question": "question_bank",
    "questions": "question_bank",
    "exam": "question_bank",
    "ppt_h5": "ppt",
    "presentation": "ppt",
    "handout": "document",
    "learning_document": "document",
    "mind_map": "mindmap",
    "video_search": "video",
    "animated_lesson": "animation",
    "learning_animation": "animation",
    "animation_generate": "animation",
    "simulator": "mcu",
    "mcu_simulator": "mcu",
    "digital_human_interview": "interview",
    "ai_interview": "interview",
    "tutor": "smart_tutor",
    "smart_tutoring": "smart_tutor",
    "assessment": "effect_assessment",
    "learning_assessment": "effect_assessment",
    "feedback": "learning_feedback",
    "learning_feedback": "learning_feedback",
}

ACTION_SCHEMA = [
    {
        "name": "chat",
        "description": "Reply without creating a platform task.",
        "arguments": {"reply": "Short user-facing reply.", "suggestions": ["Up to 3 suggestions."]},
    },
    {
        "name": "create_learning_task",
        "description": "Create and dispatch a task to one platform agent.",
        "arguments": {
            "resourceType": "|".join(PLATFORM_TOOLS.keys()),
            "topic": "Task topic.",
            "reply": "Short user-facing reply.",
        },
    },
    {
        "name": "update_learning_profile",
        "description": "Dispatch the learner-profile agent.",
        "arguments": {"topic": "Profile update topic.", "reply": "Short user-facing reply."},
    },
    {
        "name": "manage_learning_profile",
        "description": "List, activate, refresh or reset immutable learner-profile versions.",
        "arguments": {
            "profileAction": "list|activate|refresh|reset",
            "targetQuery": "Profile name, version, date phrase or report id.",
            "reply": "Short user-facing reply.",
        },
    },
]


class HermesAgentError(RuntimeError):
    """Raised when the Hermes agent runtime cannot return usable JSON."""


@dataclass(frozen=True)
class HermesAgentConfig:
    agent_id: str
    agent_name: str
    api_url: str
    auth_token: str
    model: str

    @classmethod
    def from_settings(cls) -> "HermesAgentConfig":
        auth_token = get_setting("HERMES_AGENT_AUTH_TOKEN", "") or get_mimo_api_key({})
        model = get_setting("HERMES_AGENT_MODEL", "") or get_mimo_model({}) or DEFAULT_MODEL
        configured_api_url = get_setting("HERMES_AGENT_API_URL", "")
        configured_base_url = get_setting("HERMES_AGENT_BASE_URL", "")

        api_payload: dict[str, Any] = {}
        if configured_api_url:
            api_payload["api_url"] = configured_api_url
        elif configured_base_url:
            api_payload["api_url"] = _anthropic_base_to_chat_url(configured_base_url)
        api_url = resolve_mimo_api_url(auth_token, api_payload) if auth_token else ""

        return cls(
            agent_id=get_setting("HERMES_XIAOZHI_AGENT_ID", HERMES_XIAOZHI_AGENT_ID) or HERMES_XIAOZHI_AGENT_ID,
            agent_name=get_setting("HERMES_XIAOZHI_AGENT_NAME", HERMES_XIAOZHI_AGENT_NAME) or HERMES_XIAOZHI_AGENT_NAME,
            api_url=api_url,
            auth_token=auth_token,
            model=model,
        )


class HermesXiaoZhiAgent:
    """Hermes master-control agent backed by the shared XFYun MaaS API."""

    def __init__(self, config: HermesAgentConfig | None = None):
        self.config = config or HermesAgentConfig.from_settings()

    def invoke(self, message: str, context: dict[str, Any]) -> dict[str, Any]:
        if not self.config.api_url:
            raise HermesAgentError("Hermes MaaS API URL is not configured")
        if not self.config.auth_token:
            raise HermesAgentError("Hermes MaaS API key is not configured")

        parsed = self._call_mimo_chat(self._system_prompt(), self._user_prompt(message, context))
        result = self._normalize_result(parsed)
        result.update(
            {
                "agent": self.config.agent_id,
                "agentName": self.config.agent_name,
                "runtime": HERMES_RUNTIME,
                "source": HERMES_SOURCE,
                "provider": "xfyun-maas",
                "model": self.config.model,
                "apiUrl": self.config.api_url,
            }
        )
        return result

    def _call_mimo_chat(self, system: str, prompt: str) -> dict[str, Any]:
        body = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 900,
            "response_format": {"type": "json_object"},
        }
        try:
            response = requests.post(
                self.config.api_url,
                headers={
                    "api-key": self.config.auth_token,
                    "x-api-key": self.config.auth_token,
                    "Authorization": f"Bearer {self.config.auth_token}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=45,
            )
        except Exception as exc:  # pragma: no cover - network path
            raise HermesAgentError(f"Hermes MaaS request failed: {exc}") from exc

        if not response.ok:
            raise HermesAgentError(f"Hermes MaaS API failed: HTTP {response.status_code}; {response.text[:1000]}")
        try:
            data = response.json()
        except ValueError as exc:
            raise HermesAgentError(f"Hermes MaaS response is not JSON: {response.text[:1000]}") from exc

        text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content", "")
        if not str(text).strip():
            raise HermesAgentError("Hermes MaaS response is empty")
        try:
            return extract_json(str(text))
        except Exception as exc:
            raise HermesAgentError(f"Hermes MaaS response is not valid JSON: {exc}") from exc

    def _system_prompt(self) -> str:
        tool_list = [
            {
                "resourceType": key,
                "agent": value["agent"],
                "label": value["label"],
                "route": value["route"],
                "description": value["description"],
            }
            for key, value in PLATFORM_TOOLS.items()
        ]
        return f"""
You are {self.config.agent_name}, the Hermes master-control agent for an embedded-learning platform.
Your runtime is Hermes Agent Runtime. Your underlying LLM/API is the user-configured XFYun MaaS model through a compatible chat endpoint.

You can orchestrate these platform agents:
{json.dumps(tool_list, ensure_ascii=False)}

Action schema:
{json.dumps(ACTION_SCHEMA, ensure_ascii=False)}

Rules:
1. Output exactly one JSON object. Do not output Markdown or explanations.
2. intent must be one of: chat, generate_resource, update_profile, profile_management.
3. resourceType must be one of: none, {", ".join(PLATFORM_TOOLS.keys())}.
4. For requests to list, switch, activate, rename context, refresh or reset saved profile versions, use intent=profile_management and profileAction=list|activate|refresh|reset.
5. For requests to generate a first profile report, use intent=update_profile and resourceType=profile_update.
6. For requests to generate, start, search, recommend, evaluate, interview, plan, or open a platform agent, use intent=generate_resource and the most specific resourceType.
7. reply must be concise Simplified Chinese, 1-3 short sentences.
8. selectedAction must describe the selected Hermes action.
"""

    def _user_prompt(self, message: str, context: dict[str, Any]) -> str:
        return f"""
User message:
{message}

Platform context summary:
{json.dumps(context, ensure_ascii=False)[:5000]}

Return JSON in this shape:
{{
  "intent": "chat|generate_resource|update_profile|profile_management",
  "resourceType": "{'|'.join(['none', *PLATFORM_TOOLS.keys()])}",
  "profileAction": "list|activate|refresh|reset or empty string",
  "targetQuery": "profile name, version, date phrase, report id or empty string",
  "topic": "task topic or empty string",
  "reply": "short Simplified Chinese reply",
  "weakPointSummary": "weak-point summary inferred from context",
  "suggestions": ["up to 3 short suggestions"],
  "selectedAction": {{
    "name": "chat|create_learning_task|update_learning_profile|manage_learning_profile",
    "arguments": {{}}
  }}
}}
"""

    def _normalize_result(self, data: dict[str, Any]) -> dict[str, Any]:
        intent = data.get("intent") if data.get("intent") in ALLOWED_INTENTS else "chat"
        resource_type = str(data.get("resourceType") or "none").strip()
        resource_type = RESOURCE_ALIASES.get(resource_type, resource_type)
        if resource_type not in ALLOWED_RESOURCE_TYPES:
            resource_type = "none"
        if intent == "update_profile":
            resource_type = "profile_update"
        if intent in {"chat", "profile_management"}:
            resource_type = "none"
        profile_action = str(data.get("profileAction") or "").strip()
        if intent == "profile_management" and profile_action not in ALLOWED_PROFILE_ACTIONS:
            profile_action = "list"

        suggestions = data.get("suggestions")
        if not isinstance(suggestions, list):
            suggestions = []
        suggestions = [str(item).strip() for item in suggestions if str(item).strip()][:3]

        selected_action = data.get("selectedAction") if isinstance(data.get("selectedAction"), dict) else {}
        if not selected_action:
            action_name = "chat"
            if intent == "generate_resource":
                action_name = "create_learning_task"
            elif intent == "update_profile":
                action_name = "update_learning_profile"
            elif intent == "profile_management":
                action_name = "manage_learning_profile"
            selected_action = {
                "name": action_name,
                "arguments": {
                    "resourceType": resource_type,
                    "topic": str(data.get("topic") or "").strip(),
                    "profileAction": profile_action,
                    "targetQuery": str(data.get("targetQuery") or "").strip(),
                },
            }

        return {
            "intent": intent,
            "resourceType": resource_type,
            "profileAction": profile_action,
            "targetQuery": str(data.get("targetQuery") or "").strip(),
            "topic": str(data.get("topic") or "").strip(),
            "reply": str(data.get("reply") or "").strip(),
            "weakPointSummary": str(data.get("weakPointSummary") or "").strip(),
            "suggestions": suggestions,
            "selectedAction": selected_action,
        }


def run_xiaozhi_hermes_agent(message: str, context: dict[str, Any]) -> dict[str, Any]:
    return HermesXiaoZhiAgent().invoke(message, context)


def hermes_xiaozhi_runtime_status() -> dict[str, Any]:
    config = HermesAgentConfig.from_settings()
    return {
        "agentId": config.agent_id,
        "agentName": config.agent_name,
        "runtime": HERMES_RUNTIME,
        "source": HERMES_SOURCE,
        "provider": "xfyun-maas",
        "model": config.model,
        "apiUrl": config.api_url,
        "hasToken": bool(config.auth_token),
        "tools": [
            {
                "type": key,
                "agent": value["agent"],
                "label": value["label"],
                "route": value["route"],
                "description": value["description"],
            }
            for key, value in PLATFORM_TOOLS.items()
        ],
    }
