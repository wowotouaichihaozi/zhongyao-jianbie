"""Versioned skill contracts loaded from the XiaoZhi agent manifest."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

try:
    from agent_manifest import DEFAULT_AGENT_MANIFEST, AgentManifest
except ImportError:  # pragma: no cover
    from ..agent_manifest import DEFAULT_AGENT_MANIFEST, AgentManifest


OBJECT_SCHEMA = {"type": "object", "additionalProperties": True}


class SkillContractError(ValueError):
    """Raised when a Skill input or output violates its JSON contract."""


def _matches_json_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    raise SkillContractError(f"unsupported JSON schema type: {expected}")


def validate_json_contract(value: Any, schema: dict[str, Any], *, path: str = "$") -> None:
    """Validate the JSON Schema subset used by the Skill manifest."""

    if not isinstance(schema, dict):
        raise SkillContractError(f"{path}: contract schema must be an object")
    if "enum" in schema and value not in schema["enum"]:
        raise SkillContractError(f"{path}: value is outside the allowed enum")

    expected = schema.get("type")
    expected_types = expected if isinstance(expected, list) else [expected] if expected else []
    if expected_types and not any(_matches_json_type(value, str(item)) for item in expected_types):
        type_label = " or ".join(map(str, expected_types))
        raise SkillContractError(f"{path}: expected {type_label}")

    if isinstance(value, dict):
        required = schema.get("required") or []
        for key in required:
            if str(key) not in value:
                raise SkillContractError(f"{path}.{key}: required property is missing")
        properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
        for key, child_schema in properties.items():
            if key in value:
                validate_json_contract(value[key], child_schema, path=f"{path}.{key}")
        if schema.get("additionalProperties") is False:
            unexpected = sorted(set(map(str, value)) - set(map(str, properties)))
            if unexpected:
                raise SkillContractError(f"{path}: unexpected properties: {unexpected}")

    if isinstance(value, list):
        minimum = int(schema.get("minItems") or 0)
        if len(value) < minimum:
            raise SkillContractError(f"{path}: expected at least {minimum} items")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                validate_json_contract(item, item_schema, path=f"{path}[{index}]")

    if isinstance(value, str):
        minimum = int(schema.get("minLength") or 0)
        if len(value.strip()) < minimum:
            raise SkillContractError(f"{path}: expected a non-empty string")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise SkillContractError(f"{path}: value is below the minimum")
        if "maximum" in schema and value > schema["maximum"]:
            raise SkillContractError(f"{path}: value exceeds the maximum")


@dataclass(frozen=True)
class SkillSpec:
    id: str
    name: str
    task_type: str
    agent_id: str
    description: str
    label: str
    route: str
    mcp_server: str
    mcp_tool: str
    handler_key: str
    permissions: tuple[str, ...] = ()
    risk_level: str = "low"
    timeout_seconds: int = 120
    max_retries: int = 0
    requires_review: bool = True
    knowledge_required: bool = False
    min_score: int = 70
    version: str = "1.0.0"
    input_schema: dict[str, Any] = field(default_factory=lambda: dict(OBJECT_SCHEMA))
    output_schema: dict[str, Any] = field(default_factory=lambda: dict(OBJECT_SCHEMA))

    def public_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.update(
            {
                "taskType": data.pop("task_type"),
                "agentId": data.pop("agent_id"),
                "mcpServer": data.pop("mcp_server"),
                "mcpTool": data.pop("mcp_tool"),
                "handlerKey": data.pop("handler_key"),
                "riskLevel": data.pop("risk_level"),
                "timeoutSeconds": data.pop("timeout_seconds"),
                "maxRetries": data.pop("max_retries"),
                "requiresReview": data.pop("requires_review"),
                "knowledgeRequired": data.pop("knowledge_required"),
                "minScore": data.pop("min_score"),
                "inputSchema": data.pop("input_schema"),
                "outputSchema": data.pop("output_schema"),
                "permissions": list(data.get("permissions") or []),
            }
        )
        return data


class SkillRegistry:
    def __init__(self, skills: list[SkillSpec] | None = None):
        self._by_id: dict[str, SkillSpec] = {}
        self._by_task_type: dict[str, SkillSpec] = {}
        self._by_tool: dict[str, SkillSpec] = {}
        for skill in skills or []:
            self.register(skill)

    def register(self, skill: SkillSpec) -> None:
        if skill.id in self._by_id:
            raise ValueError(f"duplicate skill id: {skill.id}")
        if skill.task_type in self._by_task_type:
            raise ValueError(f"duplicate skill task type: {skill.task_type}")
        if skill.mcp_tool in self._by_tool:
            raise ValueError(f"duplicate MCP tool name: {skill.mcp_tool}")
        self._by_id[skill.id] = skill
        self._by_task_type[skill.task_type] = skill
        self._by_tool[skill.mcp_tool] = skill

    def resolve(self, task_type: str) -> SkillSpec:
        skill = self._by_task_type.get(str(task_type or "").strip())
        if not skill:
            raise KeyError(f"skill is not registered for task type: {task_type}")
        return skill

    def resolve_tool(self, tool_name: str) -> SkillSpec:
        skill = self._by_tool.get(str(tool_name or "").strip())
        if not skill:
            raise KeyError(f"MCP tool is not registered: {tool_name}")
        return skill

    def list_specs(self) -> list[SkillSpec]:
        return list(self._by_task_type.values())

    def list_skills(self) -> list[dict[str, Any]]:
        return [skill.public_dict() for skill in self.list_specs()]


def skills_from_manifest(manifest: AgentManifest) -> list[SkillSpec]:
    skills: list[SkillSpec] = []
    for raw in manifest.skills:
        policy = raw.get("policy") if isinstance(raw.get("policy"), dict) else {}
        skills.append(
            SkillSpec(
                id=str(raw["id"]),
                name=str(raw["name"]),
                task_type=str(raw["taskType"]),
                agent_id=str(raw["agentId"]),
                description=str(raw["description"]),
                label=str(raw["label"]),
                route=str(raw["route"]),
                mcp_server=str(raw["mcpServer"]),
                mcp_tool=str(raw["mcpTool"]),
                handler_key=str(raw["handlerKey"]),
                permissions=tuple(map(str, raw.get("permissions") or [])),
                risk_level=str(raw.get("riskLevel") or "low"),
                timeout_seconds=int(raw.get("timeoutSeconds") or 120),
                max_retries=int(raw.get("maxRetries") or 0),
                requires_review=bool(raw.get("requiresReview", True)),
                knowledge_required=bool(policy.get("knowledge")),
                min_score=int(policy.get("minScore") or 70),
                version=str(raw.get("version") or "1.0.0"),
                input_schema=dict(raw.get("inputSchema") or OBJECT_SCHEMA),
                output_schema=dict(raw.get("outputSchema") or OBJECT_SCHEMA),
            )
        )
    return skills


DEFAULT_SKILLS = skills_from_manifest(DEFAULT_AGENT_MANIFEST)
DEFAULT_SKILL_REGISTRY = SkillRegistry(DEFAULT_SKILLS)
