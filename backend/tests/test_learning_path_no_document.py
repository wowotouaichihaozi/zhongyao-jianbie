from __future__ import annotations

from unittest.mock import patch

from backend import app as app_module
from backend import learning_agents


def _profile_context() -> dict:
    return {
        "goals": ["完成 STM32 综合项目"],
        "weakPoints": ["GPIO 中断与串口调试"],
        "resourcePreferences": ["课件", "导图"],
        "evidence": {"profileReportId": 9},
    }


def test_weekly_required_resources_exclude_course_documents() -> None:
    assert "document" not in learning_agents.LEARNING_PATH_RESOURCE_TYPES
    assert "document" not in learning_agents.LEARNING_PATH_REQUIRED_RESOURCE_TYPES
    assert set(learning_agents.LEARNING_PATH_REQUIRED_RESOURCE_TYPES) == {
        "mcu",
        "question-bank",
        "ppt",
        "mindmap",
        "video",
        "generated_video",
    }


def test_router_rewrites_model_document_choice_to_ppt() -> None:
    with patch.object(
        learning_agents,
        "call_llm_json",
        return_value={
            "tasks": [
                {
                    "id": "01",
                    "resourceType": "document",
                    "resourceParams": {"topic": "GPIO 中断"},
                    "resourcePrompt": "生成课程讲义",
                }
            ]
        },
    ):
        result = learning_agents.plan_learning_path_stage_resources(
            {
                "profile": _profile_context(),
                "stage": {
                    "id": "week-1",
                    "focus": "GPIO 中断",
                    "nodes": [
                        {
                            "id": "01",
                            "title": "中断机制梳理",
                            "description": "根据芯片手册完成中断流程判断。",
                        }
                    ],
                },
            }
        )

    assert result["tasks"][0]["resourceType"] == "ppt"
    assert "document" not in {task["resourceType"] for task in result["tasks"]}


def test_saved_legacy_document_node_is_migrated_without_reusing_old_task() -> None:
    raw = {
        "version": 2,
        "meta": {"totalWeeks": 1},
        "weeks": [
            {
                "id": "week-1",
                "order": 1,
                "weekLabel": "第一周",
                "title": "GPIO 基础",
                "description": "完成基础配置与验证",
                "status": "current",
                "enabled": True,
            }
        ],
        "stages": {
            "week-1": {
                "id": "week-1",
                "weekLabel": "第一周",
                "nodes": [
                    {
                        "id": "01",
                        "title": "课程讲义：GPIO 基础配置",
                        "description": "生成 GPIO 讲义并完成配置验证。",
                        "resourceType": "document",
                        "actionRoute": "/personalized-resources/document?task=old-document",
                        "resourceTask": {
                            "taskId": "old-document",
                            "status": "queued",
                            "route": "/personalized-resources/document?task=old-document",
                        },
                    }
                ],
            }
        },
    }

    node = app_module.normalize_learning_path_config(raw)["stages"]["week-1"]["nodes"][0]

    assert node["resourceType"] == "ppt"
    assert "讲义" not in node["title"]
    assert "讲义" not in node["description"]
    assert node["actionRoute"].startswith("/personalized-resources/ppt?")
    assert not node["resourceTask"].get("taskId")
    assert node["resourceSelectionSource"] == "legacy-document-migration"
