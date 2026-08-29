"""Validated, configuration-driven XiaoZhi agent manifest."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_MANIFEST_PATH = Path(__file__).resolve().parent / "agent_manifests" / "xiaozhi_agents.json"
ALLOWED_RISK_LEVELS = {"low", "medium", "high"}
ALLOWED_PERMISSIONS = {
    "animation:write",
    "assessment:write",
    "camera:analyze",
    "dialogue:write",
    "document:write",
    "evidence:read",
    "experiment:launch",
    "experiment:read",
    "feedback:write",
    "interview:write",
    "knowledge:read",
    "knowledge:write",
    "mindmap:write",
    "network:search",
    "path:read",
    "path:write",
    "ppt:write",
    "profile:read",
    "profile:write",
    "question-bank:write",
    "resource:write",
    "video:write",
}


@dataclass(frozen=True)
class AgentManifest:
    path: Path
    manifest_version: str
    root_agent_id: str
    architecture: str
    agents: tuple[dict[str, Any], ...]
    skills: tuple[dict[str, Any], ...]

    def agent_catalog(self) -> dict[str, dict[str, Any]]:
        catalog: dict[str, dict[str, Any]] = {}
        for agent in self.agents:
            entry: dict[str, Any] = {
                "name": str(agent["name"]),
                "role": str(agent["role"]),
                "description": str(agent["description"]),
            }
            for key in (
                "modelId",
                "modelName",
                "contextWindow",
                "processor",
                "input",
                "output",
                "hidden",
                "hiddenReason",
            ):
                if key in agent:
                    entry[key] = agent[key]
            catalog[str(agent["id"])] = entry
        return catalog

    def task_policies(self) -> dict[str, dict[str, Any]]:
        return {
            str(skill["taskType"]): {
                "worker": str(skill["agentId"]),
                "knowledge": bool((skill.get("policy") or {}).get("knowledge")),
                "min_score": int((skill.get("policy") or {}).get("minScore") or 70),
            }
            for skill in self.skills
        }

    def platform_tools(self) -> dict[str, dict[str, str]]:
        return {
            str(skill["taskType"]): {
                "agent": str(skill["agentId"]),
                "label": str(skill["label"]),
                "route": str(skill["route"]),
                "description": str(skill["description"]),
                "skillId": str(skill["id"]),
                "mcpServer": str(skill["mcpServer"]),
                "mcpTool": str(skill["mcpTool"]),
                "handlerKey": str(skill["handlerKey"]),
            }
            for skill in self.skills
        }


def _required_text(item: dict[str, Any], key: str, owner: str) -> str:
    value = str(item.get(key) or "").strip()
    if not value:
        raise ValueError(f"{owner} is missing required field: {key}")
    return value


def load_agent_manifest(path: str | Path | None = None) -> AgentManifest:
    manifest_path = Path(path or DEFAULT_MANIFEST_PATH).resolve()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("agent manifest root must be an object")
    raw_agents = data.get("agents")
    raw_skills = data.get("skills")
    if not isinstance(raw_agents, list) or not isinstance(raw_skills, list):
        raise ValueError("agent manifest must contain agents and skills arrays")

    agents: list[dict[str, Any]] = []
    agent_ids: set[str] = set()
    for raw in raw_agents:
        if not isinstance(raw, dict):
            raise ValueError("each agent manifest entry must be an object")
        agent_id = _required_text(raw, "id", "agent")
        if agent_id in agent_ids:
            raise ValueError(f"duplicate agent id: {agent_id}")
        agent_ids.add(agent_id)
        for key in ("name", "role", "description"):
            _required_text(raw, key, f"agent {agent_id}")
        agents.append(dict(raw))

    root_agent_id = _required_text(data, "rootAgentId", "manifest")
    if root_agent_id not in agent_ids:
        raise ValueError(f"root agent is not registered: {root_agent_id}")

    skills: list[dict[str, Any]] = []
    skill_ids: set[str] = set()
    task_types: set[str] = set()
    mcp_tools: set[str] = set()
    for raw in raw_skills:
        if not isinstance(raw, dict):
            raise ValueError("each skill manifest entry must be an object")
        skill_id = _required_text(raw, "id", "skill")
        task_type = _required_text(raw, "taskType", f"skill {skill_id}")
        mcp_tool = _required_text(raw, "mcpTool", f"skill {skill_id}")
        if skill_id in skill_ids:
            raise ValueError(f"duplicate skill id: {skill_id}")
        if task_type in task_types:
            raise ValueError(f"duplicate skill task type: {task_type}")
        if mcp_tool in mcp_tools:
            raise ValueError(f"duplicate MCP tool name: {mcp_tool}")
        skill_ids.add(skill_id)
        task_types.add(task_type)
        mcp_tools.add(mcp_tool)
        for key in (
            "name",
            "agentId",
            "description",
            "label",
            "route",
            "mcpServer",
            "handlerKey",
            "version",
        ):
            _required_text(raw, key, f"skill {skill_id}")
        for schema_key in ("inputSchema", "outputSchema"):
            schema = raw.get(schema_key)
            if not isinstance(schema, dict) or schema.get("type") != "object":
                raise ValueError(
                    f"skill {skill_id} {schema_key} must be an explicit object schema"
                )
            required = schema.get("required") or []
            properties = schema.get("properties") or {}
            if not isinstance(required, list) or not isinstance(properties, dict):
                raise ValueError(f"skill {skill_id} has an invalid {schema_key}")
            unknown_required = sorted(set(map(str, required)) - set(map(str, properties)))
            if unknown_required:
                raise ValueError(
                    f"skill {skill_id} {schema_key} requires undefined properties: {unknown_required}"
                )
        if str(raw["agentId"]) not in agent_ids:
            raise ValueError(f"skill {skill_id} references unknown agent: {raw['agentId']}")
        if not str(raw["route"]).startswith("/"):
            raise ValueError(f"skill {skill_id} route must start with /")
        risk_level = str(raw.get("riskLevel") or "low")
        if risk_level not in ALLOWED_RISK_LEVELS:
            raise ValueError(f"skill {skill_id} has invalid risk level: {risk_level}")
        permissions = raw.get("permissions") or []
        if not isinstance(permissions, list):
            raise ValueError(f"skill {skill_id} permissions must be an array")
        illegal_permissions = sorted(set(map(str, permissions)) - ALLOWED_PERMISSIONS)
        if illegal_permissions:
            raise ValueError(f"skill {skill_id} has illegal permissions: {illegal_permissions}")
        timeout_seconds = int(raw.get("timeoutSeconds") or 0)
        max_retries = int(raw.get("maxRetries") or 0)
        if timeout_seconds <= 0 or timeout_seconds > 900:
            raise ValueError(f"skill {skill_id} timeout must be between 1 and 900 seconds")
        if max_retries < 0 or max_retries > 2:
            raise ValueError(f"skill {skill_id} maxRetries must be between 0 and 2")
        policy = raw.get("policy")
        if not isinstance(policy, dict) or not 0 <= int(policy.get("minScore") or -1) <= 100:
            raise ValueError(f"skill {skill_id} has an invalid policy")
        skills.append(dict(raw))

    return AgentManifest(
        path=manifest_path,
        manifest_version=_required_text(data, "manifestVersion", "manifest"),
        root_agent_id=root_agent_id,
        architecture=_required_text(data, "architecture", "manifest"),
        agents=tuple(agents),
        skills=tuple(skills),
    )


DEFAULT_AGENT_MANIFEST = load_agent_manifest()
XIAOZHI_MASTER_AGENT_ID = DEFAULT_AGENT_MANIFEST.root_agent_id
AGENT_CATALOG = DEFAULT_AGENT_MANIFEST.agent_catalog()
TASK_POLICIES = DEFAULT_AGENT_MANIFEST.task_policies()
PLATFORM_TOOLS = DEFAULT_AGENT_MANIFEST.platform_tools()
