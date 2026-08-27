from pathlib import Path
from unittest.mock import patch

from backend import app as app_module
from backend import learning_agents
from backend.herb_model_catalog import (
    HERB_MODELS,
    find_herb_model,
    public_herb_model_catalog,
    select_learning_path_herb,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_herb_catalog_has_unique_complete_web_assets():
    catalog = public_herb_model_catalog()

    assert len(catalog) == 20
    assert len({item["id"] for item in catalog}) == len(catalog)
    assert len({item["name"] for item in catalog}) == len(catalog)
    for item in catalog:
        assert (PROJECT_ROOT / "img" / item["modelUrl"].lstrip("/")).is_file()
        assert item["materialTextures"]
        for texture_url in item["materialTextures"].values():
            assert (PROJECT_ROOT / "img" / texture_url.lstrip("/")).is_file()


def test_learning_path_herb_selection_is_stable_and_catalog_backed():
    first = select_learning_path_herb(17, "week-2", "04")
    second = select_learning_path_herb(17, "week-2", "04")

    assert first == second
    assert find_herb_model(first["id"])["name"] == first["name"]
    assert first["id"] in {item["id"] for item in HERB_MODELS}


def test_weekly_coverage_assigns_one_concrete_herb_model():
    nodes = [
        {
            "id": f"{index:02d}",
            "title": f"中医学习任务 {index}",
            "description": "完成学习记录并保留可复盘证据。",
        }
        for index in range(1, 9)
    ]
    tasks = [
        {
            "id": node["id"],
            "resourceType": "video",
            "resourceParams": {"topic": "八纲辨证", "keyword": "八纲辨证"},
        }
        for node in nodes
    ]

    covered = learning_agents.ensure_weekly_learning_path_resource_coverage(
        tasks,
        nodes,
        profile_context={"evidence": {"profileReportId": 17}},
        topic="八纲辨证与中药性状",
        stage_id="week-2",
    )

    herb_tasks = [task for task in covered if task["resourceType"] == "herb-model"]
    assert len(herb_tasks) == 1
    params = herb_tasks[0]["resourceParams"]
    selected = find_herb_model(params["herbId"])
    assert selected is not None
    assert params["herbName"] == selected["name"]
    assert params["challengeMode"] == "identify"


def test_legacy_short_week_is_not_rewritten_for_resource_coverage():
    nodes = [
        {"id": f"{index:02d}", "title": f"历史任务 {index}", "description": "完成学习记录。"}
        for index in range(1, 5)
    ]
    tasks = [
        {"id": node["id"], "resourceType": "document", "resourceParams": {"topic": "中医基础"}}
        for node in nodes
    ]

    covered = app_module._ensure_learning_path_task_resource_coverage(
        [{**node, **task} for node, task in zip(nodes, tasks)],
        "中医基础",
        "legacy-week",
    )

    assert [task["resourceType"] for task in covered] == ["document"] * 4


def test_profile_selected_herb_model_always_gets_concrete_catalog_params():
    node = {
        "id": "03",
        "title": "药材性状观察",
        "description": "旋转观察模型并完成药材辨识。",
    }
    covered = learning_agents.ensure_weekly_learning_path_resource_coverage(
        [
            {"id": "01", "resourceType": "document"},
            {"id": "02", "resourceType": "question-bank"},
            {"id": "03", "resourceType": "herb-model", "resourceParams": {}},
            {"id": "04", "resourceType": "ppt"},
            {"id": "05", "resourceType": "mindmap"},
            {"id": "06", "resourceType": "video"},
            {"id": "07", "resourceType": "generated_video"},
        ],
        [{"id": f"{index:02d}", **(node if index == 3 else {})} for index in range(1, 8)],
        profile_context={"evidence": {"profileReportId": 17}},
        topic="中药性状鉴别",
        stage_id="week-3",
    )

    herb_task = next(task for task in covered if task["resourceType"] == "herb-model")
    assert find_herb_model(herb_task["resourceParams"]["herbId"])["name"] == herb_task["resourceParams"]["herbName"]


def test_model_focused_profile_still_gets_exactly_one_herb_task_per_week():
    result = learning_agents.generate_learning_path(
        {
            "profile": {
                "id": 17,
                "studentProfile": {
                    "学习目标": ["掌握中药性状鉴别"],
                    "薄弱知识点": ["根及根茎类药材辨识"],
                    "资源形式偏好": ["三维模型", "题库"],
                },
            },
            "useLLM": False,
            "weekStart": 1,
            "weekCount": 1,
            "totalWeeks": 1,
        }
    )
    stage = next(iter(result["config"]["stages"].values()))
    herb_nodes = [node for node in stage["nodes"] if node["resourceType"] == "herb-model"]

    assert len(herb_nodes) == 1
    assert herb_nodes[0]["resourceParams"]["herbId"]
    assert "herb=" in herb_nodes[0]["actionRoute"]


def test_herb_model_resource_task_completes_without_model_runtime():
    with (
        patch.object(app_module, "xiaozhi_create_task", return_value="herb-task-1"),
        patch.object(app_module, "xiaozhi_update_task") as update_task,
        patch.object(app_module, "xiaozhi_insert_event"),
        patch.object(app_module.RESOURCE_AGENT_EXECUTOR, "submit") as submit,
    ):
        task = app_module.xiaozhi_create_resource_agent_task(
            101,
            "herb_model",
            "药材辨识",
            {
                "herbId": "ginseng",
                "stageId": "week-1",
                "nodeId": "03",
                "cacheKey": "week-1-03-herb-model",
                "profileReportId": 17,
            },
        )

    assert task["status"] == "complete"
    assert task["result"]["selectedResource"]["content"]["name"] == "人参"
    assert task["route"].startswith("/personalized-resources/herb-model?")
    assert "herb=ginseng" in task["route"]
    assert update_task.call_count == 2
    submit.assert_not_called()
