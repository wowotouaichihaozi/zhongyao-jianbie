"""MCP-style tool gateway and invocation trace for local platform skills."""

from __future__ import annotations

import time
import uuid
from typing import Any, Callable

from .registry import SkillRegistry, SkillSpec, validate_json_contract


ProgressCallback = Callable[[dict[str, Any]], None]
ToolHandler = Callable[[dict[str, Any], ProgressCallback], dict[str, Any]]


class MCPToolGateway:
    protocol_version = "2025-06-18"

    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    def list_tools(self) -> list[dict[str, Any]]:
        tools = []
        for skill in self.registry.list_skills():
            tools.append(
                {
                    "name": skill["mcpTool"],
                    "title": skill["name"],
                    "description": skill["description"],
                    "inputSchema": skill["inputSchema"],
                    "outputSchema": skill["outputSchema"],
                    "annotations": {
                        "readOnlyHint": not any(
                            permission.endswith(":write")
                            for permission in skill["permissions"]
                        ),
                        "destructiveHint": False,
                        "idempotentHint": skill["taskType"]
                        in {"video", "mindmap", "smart_tutor", "effect_assessment"},
                    },
                    "_meta": {
                        "server": skill["mcpServer"],
                        "skillId": skill["id"],
                        "agentId": skill["agentId"],
                        "version": skill["version"],
                        "riskLevel": skill["riskLevel"],
                        "timeoutSeconds": skill["timeoutSeconds"],
                    },
                }
            )
        return tools

    def list_resources(self) -> list[dict[str, Any]]:
        return [
            {
                "uri": "learner://profile/current",
                "name": "当前学习画像",
                "description": "当前用户最近一次学习画像和画像证据。",
                "mimeType": "application/json",
            },
            {
                "uri": "learner://evidence/recent",
                "name": "近期学习证据",
                "description": "近期答题、实验、面试和学习行为证据。",
                "mimeType": "application/json",
            },
            {
                "uri": "xiaozhi://orchestration/recent",
                "name": "岐小智近期执行链",
                "description": "近期 Harness 运行、交接、审核和反馈记录。",
                "mimeType": "application/json",
            },
            {
                "uri": "course://knowledge/catalog",
                "name": "课程知识库目录",
                "description": "本地课程知识库及可追溯资料目录。",
                "mimeType": "application/json",
            },
            {
                "uri": "learner://knowledge/private",
                "name": "当前用户私有知识库",
                "description": "当前用户创建的知识库、激活状态和文档索引统计。",
                "mimeType": "application/json",
            },
        ]

    def validate_input(self, skill: SkillSpec, arguments: dict[str, Any]) -> None:
        validate_json_contract(arguments, skill.input_schema, path="$input")

    def validate_output(self, skill: SkillSpec, result: dict[str, Any]) -> None:
        validate_json_contract(result, skill.output_schema, path="$output")

    def list_prompts(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "xiaozhi-grounded-task",
                "description": "使用画像、知识库和结构化审核执行学习任务。",
                "arguments": [
                    {"name": "taskType", "description": "Skill task type", "required": True},
                    {"name": "topic", "description": "Task topic", "required": True},
                ],
            },
            {
                "name": "xiaozhi-effect-loop",
                "description": "根据学习效果证据生成评估和路径调整建议。",
                "arguments": [
                    {"name": "topic", "description": "Assessment topic", "required": False},
                ],
            },
        ]

    def invoke(
        self,
        skill: SkillSpec,
        arguments: dict[str, Any],
        handler: ToolHandler,
        progress: ProgressCallback,
        calls: list[dict[str, Any]],
    ) -> dict[str, Any]:
        call = {
            "callId": f"mcp_{uuid.uuid4().hex[:12]}",
            "server": skill.mcp_server,
            "tool": skill.mcp_tool,
            "skillId": skill.id,
            "agentId": skill.agent_id,
            "status": "running",
            "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "completedAt": "",
            "elapsedMs": 0,
            "argumentKeys": sorted(str(key) for key in arguments.keys())[:50],
            "resultKeys": [],
            "error": "",
            "contract": {
                "input": "pending",
                "output": "pending",
                "version": skill.version,
            },
        }
        calls.append(call)
        progress(
            {
                "agentId": "mcp-tool-gateway",
                "stage": "mcp_tool_start",
                "status": "running",
                "message": f"通过 {skill.mcp_server} 调用 {skill.mcp_tool}",
                "progress": 8,
                "callId": call["callId"],
                "skillId": skill.id,
            }
        )
        started = time.perf_counter()
        try:
            self.validate_input(skill, arguments)
            call["contract"]["input"] = "passed"
            progress(
                {
                    "agentId": "skill-registry-agent",
                    "stage": "skill_input_validated",
                    "status": "complete",
                    "message": f"Skill 输入契约校验通过：{skill.id}",
                    "progress": 12,
                    "skillId": skill.id,
                }
            )
            result = handler(arguments, progress)
            if not isinstance(result, dict):
                result = {"result": result}
            self.validate_output(skill, result)
            call["contract"]["output"] = "passed"
            progress(
                {
                    "agentId": "skill-registry-agent",
                    "stage": "skill_output_validated",
                    "status": "complete",
                    "message": f"Skill 输出契约校验通过：{skill.id}",
                    "progress": 96,
                    "skillId": skill.id,
                }
            )
            call["status"] = "complete"
            call["resultKeys"] = list(result.keys())[:50]
            return result
        except Exception as exc:
            call["status"] = "failed"
            call["error"] = str(exc)[:1000]
            if call["contract"]["input"] == "pending":
                call["contract"]["input"] = "failed"
            elif call["contract"]["output"] == "pending":
                call["contract"]["output"] = "failed"
            raise
        finally:
            call["elapsedMs"] = round((time.perf_counter() - started) * 1000)
            call["completedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
            progress(
                {
                    "agentId": "mcp-tool-gateway",
                    "stage": "mcp_tool_complete",
                    "status": call["status"],
                    "message": f"MCP 工具调用{('完成' if call['status'] == 'complete' else '失败')}：{skill.mcp_tool}",
                    "progress": 100,
                    "callId": call["callId"],
                    "elapsedMs": call["elapsedMs"],
                }
            )

    def status(self) -> dict[str, Any]:
        return {
            "name": "xiaozhi-mcp-tool-gateway",
            "protocol": "Model Context Protocol",
            "protocolVersion": self.protocol_version,
            "transport": "in-process with JSON-RPC HTTP adapter",
            "servers": sorted({skill["mcpServer"] for skill in self.registry.list_skills()}),
            "toolCount": len(self.list_tools()),
            "resourceCount": len(self.list_resources()),
            "promptCount": len(self.list_prompts()),
        }
