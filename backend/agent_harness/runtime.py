"""Agent Harness combining orchestration, skills, MCP calls and policy metadata."""

from __future__ import annotations

from typing import Any, Callable

try:
    from agent_manifest import DEFAULT_AGENT_MANIFEST
    from common import setting_overrides
    from model_routing import resolve_model_routing
    from multi_agent_runtime import (
        XIAOZHI_ARCHITECTURE,
        XIAOZHI_MASTER_AGENT_ID,
        multi_agent_runtime_status,
        run_multi_agent_workflow,
    )
except ImportError:  # pragma: no cover
    from ..agent_manifest import DEFAULT_AGENT_MANIFEST
    from ..common import setting_overrides
    from ..model_routing import resolve_model_routing
    from ..multi_agent_runtime import (
        XIAOZHI_ARCHITECTURE,
        XIAOZHI_MASTER_AGENT_ID,
        multi_agent_runtime_status,
        run_multi_agent_workflow,
    )

from .mcp_gateway import MCPToolGateway
from .handlers import DEFAULT_HANDLER_REGISTRY, HandlerRegistry
from .registry import DEFAULT_SKILL_REGISTRY, SkillRegistry


SpecialistHandler = Callable[[dict[str, Any], Callable[[dict[str, Any]], None]], dict[str, Any]]


def resolve_model_runtime(runtime_settings: dict[str, str] | None = None) -> dict[str, Any]:
    return resolve_model_routing(runtime_settings)


class XiaoZhiAgentHarness:
    name = "XiaoZhi Agent Harness"
    version = DEFAULT_AGENT_MANIFEST.manifest_version

    def __init__(
        self,
        registry: SkillRegistry | None = None,
        handler_registry: HandlerRegistry | None = None,
    ):
        self.registry = registry or DEFAULT_SKILL_REGISTRY
        self.handler_registry = handler_registry or DEFAULT_HANDLER_REGISTRY
        self.mcp_gateway = MCPToolGateway(self.registry)

    def run(
        self,
        task_type: str,
        topic: str,
        payload: dict[str, Any],
        platform_context: dict[str, Any],
        specialist_handler: SpecialistHandler,
        *,
        user_id: int = 0,
        task_id: str = "",
        on_event=None,
        max_retries: int | None = None,
        runtime_settings: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        skill = self.registry.resolve(task_type)
        tool_calls: list[dict[str, Any]] = []

        def harness_specialist(arguments: dict[str, Any], progress) -> dict[str, Any]:
            progress(
                {
                    "agentId": "skill-registry-agent",
                    "stage": "skill_resolved",
                    "status": "complete",
                    "message": f"Skill Registry 已解析能力：{skill.name} v{skill.version}",
                    "progress": 3,
                    "skillId": skill.id,
                    "permissions": list(skill.permissions),
                    "riskLevel": skill.risk_level,
                }
            )
            return self.mcp_gateway.invoke(
                skill,
                arguments,
                lambda call_arguments, call_progress: self.handler_registry.invoke(
                    skill.handler_key,
                    specialist_handler,
                    call_arguments,
                    call_progress,
                ),
                progress,
                tool_calls,
            )

        requested_retries = skill.max_retries if max_retries is None else int(max_retries)
        effective_retries = max(0, min(skill.max_retries, requested_retries))
        with setting_overrides(runtime_settings):
            result = run_multi_agent_workflow(
                task_type,
                topic,
                payload,
                platform_context,
                harness_specialist,
                user_id=user_id,
                task_id=task_id,
                on_event=on_event,
                max_retries=effective_retries,
            )
        harness_trace = {
            "name": self.name,
            "version": self.version,
            "rootAgent": XIAOZHI_MASTER_AGENT_ID,
            "architecture": "agent-harness-supervisor-blackboard",
            "orchestrationCore": XIAOZHI_ARCHITECTURE,
            "skill": skill.public_dict(),
            "profileReportId": int(
                platform_context.get("profileReportId")
                or (platform_context.get("profile") or {}).get("id")
                or 0
            ),
            "policy": {
                "permissions": list(skill.permissions),
                "riskLevel": skill.risk_level,
                "timeoutSeconds": skill.timeout_seconds,
                "requiresReview": skill.requires_review,
                "maxRetries": effective_retries,
            },
            "modelRuntime": resolve_model_runtime(runtime_settings),
            "mcp": {
                **self.mcp_gateway.status(),
                "toolCalls": tool_calls,
            },
            "features": [
                "context_management",
                "skill_registry",
                "json_contract_validation",
                "mcp_tool_gateway",
                "shared_blackboard",
                "structured_handoffs",
                "policy_metadata",
                "quality_and_safety_review",
                "checkpoint_persistence",
                "observable_execution_trace",
                "modality_aware_model_routing",
                "vision_to_text_handoff",
                "document_text_extraction_handoff",
            ],
        }
        result["harness"] = harness_trace
        trace = result.get("orchestration")
        if isinstance(trace, dict):
            trace["architecture"] = harness_trace["architecture"]
            trace["harness"] = {
                "name": self.name,
                "version": self.version,
                "skillId": skill.id,
                "mcpServer": skill.mcp_server,
                "mcpTool": skill.mcp_tool,
                "riskLevel": skill.risk_level,
            }
            trace["mcpToolCalls"] = tool_calls
        return result

    def status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "rootAgent": XIAOZHI_MASTER_AGENT_ID,
            "architecture": "agent-harness-supervisor-blackboard",
            "skillRegistry": {
                "skillCount": len(self.registry.list_skills()),
                "skills": self.registry.list_skills(),
            },
            "mcpGateway": self.mcp_gateway.status(),
            "handlerRegistry": self.handler_registry.status(),
            "orchestration": multi_agent_runtime_status(),
        }


DEFAULT_AGENT_HARNESS = XiaoZhiAgentHarness()
