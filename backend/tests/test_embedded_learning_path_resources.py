from learning_agents import (
    LEARNING_PATH_RESOURCE_ACTIONS,
    LEARNING_PATH_RESOURCE_TYPES,
    generate_learning_path,
)


def test_every_embedded_learning_resource_has_an_action_label() -> None:
    assert LEARNING_PATH_RESOURCE_TYPES == set(LEARNING_PATH_RESOURCE_ACTIONS)
    assert "document" not in LEARNING_PATH_RESOURCE_TYPES


def test_embedded_fallback_path_can_route_all_week_tasks() -> None:
    result = generate_learning_path(
        {
            "profile": {
                "studentProfile": {
                    "学习目标": ["完成 STM32 综合项目"],
                    "薄弱知识点": ["GPIO 中断与串口调试"],
                    "资源形式偏好": ["分步骤讲解", "代码例程", "动手实验"],
                }
            },
            "useLLM": False,
            "weekStart": 1,
            "weekCount": 1,
            "totalWeeks": 6,
        }
    )

    config = result["config"]
    first_stage_id = config["weeks"][0]["id"]
    first_week_nodes = config["stages"][first_stage_id]["nodes"]
    assert first_week_nodes
    assert all(node["resourceType"] in LEARNING_PATH_RESOURCE_TYPES for node in first_week_nodes)
    assert all(node["resourceType"] != "document" for node in first_week_nodes)
