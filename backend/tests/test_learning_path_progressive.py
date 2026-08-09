from backend import app as app_module
from backend import learning_agents
from backend.learning_agents import generate_learning_path, plan_learning_path_stage_resources
from urllib.parse import parse_qs, urlparse


def _profile():
    return {
        "studentProfile": {
            "学习目标": ["完成 STM32 智能车项目"],
            "薄弱知识点": ["GPIO 中断", "串口调试"],
            "资源形式偏好": ["视频", "实验", "思维导图"],
            "可投入时间": "每周 8 小时",
        }
    }


def test_learning_path_generates_first_week_before_remaining_weeks():
    first_result = generate_learning_path({
        "profile": _profile(),
        "useLLM": False,
        "weekStart": 1,
        "weekCount": 1,
        "totalWeeks": 6,
    })
    first_config = first_result["config"]

    assert len(first_config["weeks"]) == 1
    assert first_config["meta"]["generationState"] == "partial"
    assert first_config["meta"]["taskModel"] == "dynamic-week-tasks-v2"
    assert first_config["meta"]["taskResourceModel"] == learning_agents.LEARNING_PATH_RESOURCE_PLAN_VERSION

    first_stage_id = first_config["weeks"][0]["id"]
    first_nodes = first_config["stages"][first_stage_id]["nodes"]
    assert 7 <= len(first_nodes) <= 10
    assert all(node["resourceType"] in {"generated_video", "video", "animation", "document", "ppt", "mindmap", "question-bank", "mcu"} for node in first_nodes)
    assert {
        "generated_video", "question-bank", "ppt", "mindmap", "video", "mcu",
    }.issubset({node["resourceType"] for node in first_nodes})
    assert all(isinstance(node.get("resourceParams"), dict) and node["resourceParams"] for node in first_nodes)
    assert all(node.get("resourcePrompt") for node in first_nodes)
    assert all(node.get("resourceSelectionReason") for node in first_nodes)
    assert all(node["actionRoute"].startswith("/personalized-resources/") for node in first_nodes)
    assert all("/learning-profile" not in node["actionRoute"] for node in first_nodes)
    assert all(node.get("cacheKey") for node in first_nodes)
    mcu_nodes = [node for node in first_nodes if node["resourceType"] == "mcu"]
    assert all(node["resourceParams"]["board"] in {"arduino", "8051"} for node in mcu_nodes)
    assert all(
        node["resourceParams"]["projectId"]
        in {"uno-led-ready", "uno-button-ready", "uno-blank", "8051-led-ready", "8051-ram-ready", "8051-blank"}
        for node in mcu_nodes
    )

    current_config = first_config
    for week in range(2, 7):
        remaining_result = generate_learning_path({
            "profile": _profile(),
            "useLLM": False,
            "weekStart": week,
            "weekCount": 1,
            "totalWeeks": 6,
            "existingConfig": current_config,
        })
        current_config = remaining_result["config"]
        assert len(current_config["weeks"]) == week
    complete_config = current_config

    assert len(complete_config["weeks"]) == 6
    assert complete_config["meta"]["generationState"] == "complete"
    assert [week["weekLabel"] for week in complete_config["weeks"]] == [
        "第一周",
        "第二周",
        "第三周",
        "第四周",
        "第五周",
        "第六周",
    ]
    assert all(
        7 <= len(complete_config["stages"][week["id"]]["nodes"]) <= 10
        for week in complete_config["weeks"]
    )
    required_resource_types = {
        "generated_video", "question-bank", "ppt", "mindmap", "video", "mcu",
    }
    assert all(
        required_resource_types.issubset({
            node["resourceType"]
            for node in complete_config["stages"][week["id"]]["nodes"]
        })
        for week in complete_config["weeks"]
    )


def test_learning_path_persists_the_profile_report_basis():
    profile = _profile()
    profile["id"] = 42
    profile["updatedAt"] = "2026-07-12T18:00:00+08:00"
    profile["learningEvidence"] = {
        "evidenceVersion": "evidence-v42",
        "updatedAt": "2026-07-12T18:30:00+08:00",
    }

    result = generate_learning_path({
        "profile": profile,
        "useLLM": False,
        "weekStart": 1,
        "weekCount": 1,
        "totalWeeks": 1,
    })

    assert result["config"]["meta"]["profileReportId"] == 42
    assert result["config"]["meta"]["learningEvidenceVersion"] == "evidence-v42"
    assert all(
        stage["resourceProfileReportId"] == 42
        for stage in result["config"]["stages"].values()
    )


def test_profile_context_ignores_timestamps_routes_and_resource_history():
    profile = {
        "id": 39,
        "timestamp": "2026-07-12T19:49:44.926517+00:00",
        "updatedAt": "2026-07-12T19:49:44.926517+00:00",
        "chatStudentProfile": {
            "专业/课程背景": "STM32",
            "学习目标": ["完成课程设计"],
            "薄弱知识点": ["GPIO"],
            "易错点类型": ["外设配置理解偏差"],
            "学习风格/认知偏好": ["分步骤讲解", "项目实践驱动"],
            "资源形式偏好": ["PPT课件"],
            "可投入时间": "每周能投入6小时",
            "难度接受程度": "适中偏挑战",
        },
        "aiAnalysis": {
            "summary": "聚焦 GPIO 配置与调试。",
            "strengths": ["具备 STM32 基础"],
            "weaknesses": ["代码调试定位能力较弱"],
            "recommendations": ["建立系统化排查流程"],
        },
        "learningEvidence": {
            "targetStage": "week-1-gpio",
            "resourceCalls": [
                {
                    "title": "历史视频资源",
                    "type": "video",
                    "updatedAt": "2026-07-12T19:33:16.043420+00:00",
                }
            ],
        },
    }

    context = learning_agents.build_learning_profile_context(profile)

    assert context["goals"] == ["完成课程设计"]
    assert context["resourcePreferences"] == ["PPT课件"]
    assert context["timeBudget"] == "每周能投入6小时"
    assert context["difficulty"] == "适中偏挑战"
    assert "week-1-gpio" not in context["goals"]
    assert "驱动开发基础" not in context["topicKeywords"]
    assert all("2026-" not in item for item in context["resourcePreferences"])


def test_learning_path_prompt_excludes_raw_learning_history(monkeypatch):
    captured = {}

    def fake_llm(_system, prompt, **kwargs):
        captured["prompt"] = prompt
        captured["max_tokens"] = kwargs.get("max_tokens")
        return {
            "agent": "learning-path-planner-agent",
            "source": "llm",
            "title": "GPIO 个性化路径",
            "weakPoints": ["GPIO"],
            "profileBasis": {"summary": "每周 6 小时，优先补强 GPIO"},
            "weeks": [
                {
                    "title": "第一周：GPIO 基础",
                    "description": "按每周 6 小时完成 GPIO 概念、实验与测评闭环。",
                    "taskTitles": [f"GPIO 个性化任务 {index}" for index in range(1, 8)],
                }
            ],
            "nextAction": "开始第一周",
        }

    monkeypatch.setattr(learning_agents, "call_llm_json", fake_llm)
    profile = {
        "chatStudentProfile": {
            "专业/课程背景": "STM32",
            "学习目标": ["完成课程设计"],
            "薄弱知识点": ["GPIO"],
            "资源形式偏好": ["PPT课件"],
            "可投入时间": "每周 6 小时",
        },
        "learningEvidence": {
            "recentChats": [{"content": "HISTORICAL-CHAT" * 1000}],
            "resourceCalls": [{"title": "HISTORICAL-RESOURCE" * 1000}],
        },
    }

    result = generate_learning_path({
        "profile": profile,
        "useLLM": True,
        "weekStart": 1,
        "weekCount": 1,
        "totalWeeks": 1,
    })

    assert result["source"] == "llm"
    assert "每周 6 小时" in captured["prompt"]
    assert "learningEvidence" not in captured["prompt"]
    assert "HISTORICAL-CHAT" not in captured["prompt"]
    assert "HISTORICAL-RESOURCE" not in captured["prompt"]
    assert len(captured["prompt"]) < 30000
    assert captured["max_tokens"] == 3200
    assert result["phases"][0]["tasks"][0] == "GPIO 个性化任务 1"


def test_stage_detail_prompt_excludes_raw_history_and_requests_compact_resource_plan(monkeypatch):
    captured = {}

    def fake_llm(_system, prompt, **kwargs):
        captured["prompt"] = prompt
        captured["max_tokens"] = kwargs.get("max_tokens")
        return {
            "agent": "learning-path-stage-agent",
            "stageId": "week-1-gpio",
            "title": "第一周 GPIO 学习任务",
            "summary": "按概念、练习和实验完成 GPIO 学习闭环。",
            "profileBasis": {"summary": "优先补强 GPIO，采用图解与实验。"},
            "goals": ["解释 GPIO 模式", "完成按键输入实验"],
            "weeks": [
                {
                    "week": "第一周",
                    "focus": "GPIO 输入输出",
                    "tasks": [
                        {
                            "name": "GPIO 概念梳理",
                            "detail": "标出模式、寄存器和易错点。",
                            "deliverable": "一页结构化笔记",
                        }
                    ],
                }
            ],
            "resources": [
                {
                    "id": "week-1-gpio-01-mindmap",
                    "nodeId": "01",
                    "taskTitle": "GPIO 概念梳理",
                    "title": "GPIO 知识导图",
                    "description": "围绕当前薄弱点建立概念关系。",
                    "type": "mindmap",
                    "matchScore": 94,
                    "metadata": {"reason": "偏好图解资源"},
                },
                {
                    "id": "week-1-gpio-02-quiz",
                    "nodeId": "02",
                    "taskTitle": "GPIO 专项测评",
                    "title": "GPIO 配置题单",
                    "description": "检查模式与寄存器配置。",
                    "type": "quiz",
                    "matchScore": 91,
                    "metadata": {"reason": "验证薄弱点"},
                },
                {
                    "id": "week-1-gpio-03-simulator",
                    "nodeId": "03",
                    "taskTitle": "按键输入实验",
                    "title": "GPIO 输入仿真实验",
                    "description": "完成输入读取与现象记录。",
                    "type": "simulator",
                    "matchScore": 90,
                    "metadata": {"reason": "偏好实践"},
                },
                {
                    "id": "week-1-gpio-04-video",
                    "nodeId": "04",
                    "taskTitle": "示例跟做",
                    "title": "GPIO 示例视频",
                    "description": "按关键步骤完成示例跟做。",
                    "type": "video",
                    "matchScore": 86,
                    "metadata": {"reason": "辅助观察"},
                },
            ],
            "checkpoints": ["能解释推挽与开漏", "题单正确率达到 80%", "实验现象可复现"],
        }

    monkeypatch.setattr(learning_agents, "call_llm_json", fake_llm)
    profile = {
        "id": 42,
        "chatStudentProfile": {
            "学习目标": ["完成 GPIO 输入输出实验"],
            "薄弱知识点": ["GPIO 模式配置"],
            "资源形式偏好": ["思维导图", "实验"],
            "可投入时间": "每周 6 小时",
        },
        "learningEvidence": {
            "recentChats": [{"content": "STAGE-HISTORICAL-CHAT" * 1000}],
            "resourceCalls": [{"title": "STAGE-HISTORICAL-RESOURCE" * 1000}],
        },
    }
    stage = {
        "id": "week-1-gpio",
        "weekLabel": "第一周",
        "title": "第一周学习任务与资源",
        "focus": "GPIO 输入输出",
        "nodes": [
            {
                "id": "01",
                "title": "GPIO 概念梳理",
                "description": "梳理 GPIO 模式与寄存器关系。",
                "resourceType": "mindmap",
                "resourceTask": {"result": "STAGE-CACHED-RESOURCE" * 1000},
            }
        ],
    }

    result = learning_agents.generate_learning_path_stage_detail({
        "profile": profile,
        "stage": stage,
        "resources": [],
        "useLLM": True,
    })

    assert result["source"] == "llm"
    assert result["degraded"] is False
    assert "每周 6 小时" in captured["prompt"]
    assert "GPIO 模式配置" in captured["prompt"]
    assert "learningEvidence" not in captured["prompt"]
    assert "STAGE-HISTORICAL-CHAT" not in captured["prompt"]
    assert "STAGE-HISTORICAL-RESOURCE" not in captured["prompt"]
    assert "STAGE-CACHED-RESOURCE" not in captured["prompt"]
    assert "不要生成完整资源正文" in captured["prompt"]
    assert len(captured["prompt"]) < 30000
    assert captured["max_tokens"] == 2200
    assert len(result["resources"]) >= 4
    assert all(item.get("content") for item in result["resources"])


def test_chinese_only_week_title_uses_stable_nonduplicated_stage_id():
    config = learning_agents._build_learning_path_config(
        _profile(),
        planner_weeks=[
            {
                "title": "第二周：中断机制与事件处理",
                "description": "完成中断机制学习闭环。",
                "taskTitles": [f"中断任务 {index}" for index in range(1, 8)],
            }
        ],
        week_start=2,
        week_count=1,
        total_weeks=2,
    )

    assert config["weeks"][0]["id"] == "week-2"
    assert "week-2" in config["stages"]


def test_profile_preferences_change_resource_routing_without_a_fixed_sequence():
    hands_on = generate_learning_path({
        "profile": {
            "studentProfile": {
                "学习目标": ["完成开发板项目"],
                "薄弱知识点": ["中断调试"],
                "资源形式偏好": ["实验", "动手实践"],
            }
        },
        "useLLM": False,
        "weekStart": 1,
        "weekCount": 1,
        "totalWeeks": 1,
    })
    assessment_focused = generate_learning_path({
        "profile": {
            "studentProfile": {
                "学习目标": ["通过课程考试"],
                "薄弱知识点": ["概念辨析与错题"],
                "资源形式偏好": ["题库", "专项测评"],
            }
        },
        "useLLM": False,
        "weekStart": 1,
        "weekCount": 1,
        "totalWeeks": 1,
    })

    hands_on_stage = next(iter(hands_on["config"]["stages"].values()))
    assessment_stage = next(iter(assessment_focused["config"]["stages"].values()))
    hands_on_types = [node["resourceType"] for node in hands_on_stage["nodes"]]
    assessment_types = [node["resourceType"] for node in assessment_stage["nodes"]]

    assert hands_on_types != assessment_types
    assert hands_on_types.count("mcu") == learning_agents.LEARNING_PATH_RESOURCE_CONCENTRATION_LIMIT
    assert assessment_types.count("mcu") <= learning_agents.LEARNING_PATH_RESOURCE_CONCENTRATION_LIMIT
    assert assessment_types[0] == "question-bank"
    assert hands_on_types.index("mcu") < assessment_types.index("mcu")


def test_resource_semantic_guard_rejects_incompatible_agent_choices(monkeypatch):
    monkeypatch.setattr(
        learning_agents,
        "call_llm_json",
        lambda *_args, **_kwargs: {
            "tasks": [
                {"id": "01", "resourceType": "mcu"},
                {"id": "02", "resourceType": "mcu"},
                {"id": "03", "resourceType": "mcu"},
                {"id": "04", "resourceType": "mcu"},
            ]
        },
    )
    result = plan_learning_path_stage_resources({
        "profile": {
            "studentProfile": {
                "学习目标": ["完成开发板项目"],
                "薄弱知识点": ["GPIO 中断调试"],
                "资源形式偏好": ["实验", "动手实践"],
            }
        },
        "useLLM": True,
        "stage": {
            "focus": "GPIO 核心机制",
            "nodes": [
                {"id": "01", "title": "专项测评", "description": "完成配置陷阱测试卷"},
                {"id": "02", "title": "复盘迭代", "description": "整理典型错误并制作口诀表"},
                {"id": "03", "title": "概念建模", "description": "梳理寄存器结构框图"},
                {"id": "04", "title": "迁移挑战", "description": "完成任务并留下可复盘证据"},
            ],
        },
    })
    tasks = {item["id"]: item for item in result["tasks"]}

    assert tasks["01"]["resourceType"] == "question-bank"
    assert tasks["02"]["resourceType"] in {"mindmap", "ppt", "video"}
    assert tasks["03"]["resourceType"] in {"mindmap", "ppt", "video"}
    assert tasks["04"]["resourceType"] in {"mcu", "question-bank", "video"}
    assert tasks["01"]["resourceSelectionSource"] == "semantic-guard"
    assert tasks["02"]["resourceSelectionSource"] == "semantic-guard"


def test_weekly_resource_plan_always_includes_deferred_ai_video(monkeypatch):
    monkeypatch.setattr(learning_agents, "call_llm_json", lambda *_args, **_kwargs: {"tasks": []})

    result = plan_learning_path_stage_resources({
        "profile": _profile(),
        "useLLM": True,
        "stage": {
            "focus": "STM32 GPIO",
            "nodes": [
                {"id": f"{index:02d}", "title": f"Learning task {index}", "description": "Complete and verify the weekly learning objective."}
                for index in range(1, 7)
            ],
        },
    })

    tasks = result["tasks"]
    generated_video = next(task for task in tasks if task["resourceType"] == "generated_video")
    assert generated_video["resourceParams"]["duration"] == 30
    assert generated_video["resourceParams"]["resolution"] == "720p"
    assert "STM32 GPIO" in generated_video["resourceParams"]["prompt"]
    route = app_module._learning_path_task_resource_route(
        "generated_video",
        "STM32 GPIO",
        "week-1",
        generated_video["id"],
        "week-1-video",
        generated_video["resourceParams"],
    )
    query = parse_qs(urlparse(route).query)
    assert query["prompt"][0] == generated_video["resourceParams"]["prompt"]
    assert "autostart" not in query
    assert "videoEngine" not in query
    fallback_route = learning_agents._stage_resource_route(
        "generated_video",
        "STM32 GPIO",
        "week-1",
        generated_video["id"],
        params=generated_video["resourceParams"],
    )
    fallback_query = parse_qs(urlparse(fallback_route).query)
    assert fallback_query["prompt"][0] == generated_video["resourceParams"]["prompt"]
    assert "duration" not in fallback_query
    assert "style" not in fallback_query
    assert "voice" not in fallback_query
    assert "resolution" not in fallback_query
    assert "autostart" not in fallback_query
    assert "videoEngine" not in fallback_query
    assert {
        "generated_video", "question-bank", "ppt", "mindmap", "video", "mcu",
    }.issubset({task["resourceType"] for task in tasks})


def test_weekly_resource_plan_repairs_an_all_video_llm_response(monkeypatch):
    monkeypatch.setattr(
        learning_agents,
        "call_llm_json",
        lambda *_args, **_kwargs: {
            "tasks": [
                {
                    "id": f"{index:02d}",
                    "resourceType": "video",
                    "resourceParams": {"topic": "GPIO", "keyword": "GPIO tutorial"},
                    "resourcePrompt": "Find a GPIO tutorial",
                    "selectionReason": "Generic model response",
                }
                for index in range(1, 9)
            ]
        },
    )
    nodes = [
        {
            "id": f"{index:02d}",
            "title": f"Weekly learning task {index}",
            "description": "Complete a verifiable weekly learning task.",
        }
        for index in range(1, 9)
    ]

    result = plan_learning_path_stage_resources({
        "profile": _profile(),
        "useLLM": True,
        "stage": {"focus": "STM32 GPIO", "nodes": nodes},
    })

    required = {"generated_video", "question-bank", "ppt", "mindmap", "video", "mcu"}
    assert required.issubset({task["resourceType"] for task in result["tasks"]})
    generated_video = next(task for task in result["tasks"] if task["resourceType"] == "generated_video")
    assert generated_video["resourceSelectionSource"] == "weekly-resource-coverage"
    assert generated_video["resourceParams"]["prompt"]


def test_parallel_resource_planning_reconciles_six_types_before_materialization():
    nodes = [
        {
            "id": f"{index:02d}",
            "title": f"GPIO weekly task {index}",
            "description": "Complete and verify the GPIO learning objective.",
            "resourceType": "video",
            "resourceTask": {"status": "planning"},
        }
        for index in range(1, 9)
    ]
    stage = {"focus": "STM32 GPIO", "nodes": nodes}
    planning_states = [{"nodeId": node["id"]} for node in nodes]
    planning_results = {
        node["id"]: {
            "error": "",
            "result": {
                "nodeId": node["id"],
                "planner": {"source": "llm"},
                "planned": {
                    "id": node["id"],
                    "resourceType": "video",
                    "resourceParams": {"topic": "STM32 GPIO", "keyword": "GPIO tutorial"},
                },
            },
        }
        for node in nodes
    }

    app_module._enforce_parallel_learning_path_resource_coverage(
        stage,
        planning_states,
        planning_results,
        _profile(),
    )

    planned_types = {
        outcome["result"]["planned"]["resourceType"]
        for outcome in planning_results.values()
    }
    assert {"generated_video", "question-bank", "ppt", "mindmap", "video", "mcu"}.issubset(planned_types)


def test_saved_week_without_ai_video_is_repaired_before_resource_tasks_start():
    source_types = [
        "mindmap",
        "mindmap",
        "mcu",
        "mcu",
        "question-bank",
        "video",
        "ppt",
        "video",
    ]
    nodes = [
        {
            "id": f"{index:02d}",
            "title": f"GPIO 第一周任务 {index}",
            "description": "完成 GPIO 配置、验证与复盘并保留学习证据",
            "resourceType": resource_type,
            "resourceParams": {"topic": "GPIO 配置与硬件接线规范"},
            "resourceTask": {"status": "complete", "taskId": f"old-task-{index}"},
        }
        for index, resource_type in enumerate(source_types, start=1)
    ]

    repaired = app_module._ensure_learning_path_task_resource_coverage(
        nodes,
        "GPIO 配置与硬件接线规范",
        "week-1",
    )

    repaired_types = [node["resourceType"] for node in repaired]
    assert {
        "generated_video", "question-bank", "ppt", "mindmap", "video", "mcu",
    }.issubset(set(repaired_types))
    assert repaired_types.count("generated_video") == 1
    video_node = next(node for node in repaired if node["resourceType"] == "generated_video")
    assert video_node["resourceTask"] == {"status": "waiting", "progress": 0}
    route_query = parse_qs(urlparse(video_node["actionRoute"]).query)
    assert route_query["prompt"][0]
    assert "autostart" not in route_query
    assert "videoEngine" not in route_query


def test_saved_learning_path_queues_each_enabled_week_for_background_preparation(monkeypatch):
    submitted = []

    class FakeExecutor:
        def submit(self, callback, *args):
            submitted.append((callback, args))

    monkeypatch.setattr(app_module, "LEARNING_PATH_WEEK_PREPARATION_EXECUTOR", FakeExecutor())
    config = {
        "weeks": [
            {"id": "week-1", "enabled": True},
            {"id": "week-2", "enabled": True},
            {"id": "week-3", "enabled": False},
            {"id": "week-4", "enabled": True, "placeholder": True},
        ],
        "stages": {"week-1": {}, "week-2": {}, "week-3": {}, "week-4": {}},
    }

    app_module._queue_learning_path_week_resource_preparation(7, config)

    assert [args for _callback, args in submitted] == [(7, "week-1"), (7, "week-2")]


def test_resource_semantic_guard_rejects_mindmap_for_experiment_task(monkeypatch):
    monkeypatch.setattr(
        learning_agents,
        "call_llm_json",
        lambda *_args, **_kwargs: {
            "tasks": [
                {
                    "id": "02",
                    "resourceType": "mindmap",
                    "resourceParams": {"topic": "GPIO 输出控制实验"},
                }
            ]
        },
    )

    result = plan_learning_path_stage_resources({
        "profile": _profile(),
        "useLLM": True,
        "stage": {
            "focus": "GPIO 核心机制",
            "nodes": [
                {
                    "id": "02",
                    "title": "GPIO 输出控制实验",
                    "description": "配置推挽输出并在开发板记录 LED 与输出波形",
                }
            ],
        },
    })

    task = result["tasks"][0]
    assert task["resourceType"] in {"mcu", "video"}
    assert task["resourceSelectionSource"] == "semantic-guard"


def test_resource_semantic_guard_keeps_video_learning_task_on_video_agent(monkeypatch):
    monkeypatch.setattr(
        learning_agents,
        "call_llm_json",
        lambda *_args, **_kwargs: {
            "tasks": [
                {
                    "id": "09",
                    "resourceType": "document",
                    "resourceParams": {
                        "topic": "GPIO 配置笔记",
                        "requirements": "生成配置流程文档",
                    },
                    "resourcePrompt": "生成 GPIO 配置文档",
                    "selectionReason": "使用文档建立知识库",
                }
            ]
        },
    )

    result = plan_learning_path_stage_resources({
        "profile": _profile(),
        "useLLM": True,
        "stage": {
            "focus": "GPIO 核心机制",
            "nodes": [
                {
                    "id": "09",
                    "title": "视频学习：GPIO 配置实战演示",
                    "description": "观看 GPIO 配置实战视频并记录关键步骤",
                }
            ],
        },
    })

    task = result["tasks"][0]
    assert task["resourceType"] == "video"
    assert task["resourceSelectionSource"] == "semantic-guard"
    assert "改选查找学习视频" in task["resourceSelectionReason"]
    assert "keyword" in task["resourceParams"]
    assert "requirements" not in task["resourceParams"]
    assert "生成 GPIO 配置文档" not in task["resourcePrompt"]


def test_video_agent_params_drop_fields_owned_by_other_resource_agents(monkeypatch):
    monkeypatch.setattr(
        learning_agents,
        "call_llm_json",
        lambda *_args, **_kwargs: {
            "tasks": [
                {
                    "id": "09",
                    "resourceType": "video",
                    "resourceParams": {
                        "topic": "STM32 GPIO demo",
                        "keyword": "STM32 GPIO configuration video",
                        "keywords": ["GPIO mode", "register configuration"],
                        "duration": "15 minutes",
                        "requirements": "Generate a written handout",
                    },
                }
            ]
        },
    )

    result = plan_learning_path_stage_resources({
        "profile": _profile(),
        "useLLM": True,
        "stage": {
            "focus": "STM32 GPIO",
            "nodes": [
                {
                    "id": "09",
                    "title": "Video learning: GPIO configuration demo",
                    "description": "Watch a practical GPIO configuration demonstration.",
                }
            ],
        },
    })

    task = result["tasks"][0]
    assert task["resourceType"] == "video"
    assert task["resourceSelectionSource"] == "llm"
    assert task["resourceParams"]["keyword"] == "STM32 GPIO configuration video"
    assert task["resourceParams"]["duration"] == "15 minutes"
    assert "requirements" not in task["resourceParams"]


def test_legacy_placeholder_task_descriptions_are_enriched_without_overwriting_specific_content():
    stage = {
        "focus": "GPIO 核心概念与配置原理",
        "nodes": [
            {
                "id": "01",
                "title": "GPIO 工作原理思维导图构建",
                "description": "完成与 GPIO 核心概念与配置原理 相关的学习任务，并留下可复盘证据。",
            },
            {
                "id": "02",
                "title": "GPIO 输出控制实验",
                "description": "配置推挽输出并记录 LED 运行现象。",
            },
        ],
    }

    changed = learning_agents.enrich_learning_path_task_descriptions(stage, _profile())

    assert changed is True
    assert "思维导图" in stage["nodes"][0]["description"]
    assert "核心概念" in stage["nodes"][0]["description"]
    assert stage["nodes"][1]["description"] == "配置推挽输出并记录 LED 运行现象。"


def test_reviewing_experiment_evidence_does_not_create_another_experiment_task():
    allowed = learning_agents._task_allowed_resource_types(
        "复盘迭代",
        "整理本周错因、实验截图和代码片段，记录下一周需要继续追踪的问题。",
    )

    assert "mcu" not in allowed
    assert allowed == {"mindmap", "document", "ppt", "video", "animation"}


def test_resource_concentration_guard_keeps_profile_routing_diverse(monkeypatch):
    monkeypatch.setattr(
        learning_agents,
        "call_llm_json",
        lambda *_args, **_kwargs: {
            "tasks": [{"id": "06", "resourceType": "mindmap"}]
        },
    )
    result = plan_learning_path_stage_resources({
        "profile": _profile(),
        "useLLM": True,
        "stage": {
            "focus": "GPIO 核心机制",
            "previousResourceTypes": ["mindmap", "mindmap"],
            "nodes": [
                {
                    "id": "06",
                    "title": "复盘迭代",
                    "description": "整理本周错因和下一步行动",
                }
            ],
        },
    })

    task = result["tasks"][0]
    assert task["resourceType"] in {"document", "ppt", "video", "animation"}
    assert task["resourceSelectionSource"] == "concentration-guard"


def test_resource_coverage_guard_keeps_a_video_task_in_long_week(monkeypatch):
    monkeypatch.setattr(
        learning_agents,
        "call_llm_json",
        lambda *_args, **_kwargs: {
            "tasks": [{"id": "07", "resourceType": "ppt"}]
        },
    )
    result = plan_learning_path_stage_resources({
        "profile": _profile(),
        "useLLM": True,
        "stage": {
            "focus": "GPIO 核心机制",
            "previousResourceTypes": [
                "document",
                "mindmap",
                "mcu",
                "mcu",
                "question-bank",
                "mindmap",
            ],
            "nodes": [
                {
                    "id": "07",
                    "title": "调试证据归档",
                    "description": "整理调试过程、错误原因和下一步行动",
                }
            ],
        },
    })

    task = result["tasks"][0]
    assert task["resourceType"] == "video"
    assert task["resourceSelectionSource"] == "coverage-guard"
    assert "keyword" in task["resourceParams"]


def test_profile_router_hard_caps_strong_mcu_preference_when_video_is_compatible():
    resource_type, _reason = learning_agents._profile_routed_resource_type(
        {
            "resourcePreferences": ["实验", "动手实践", "开发板", "项目实操"],
            "learningStyle": "强实践型",
            "recommendations": ["继续完成开发板实验"],
            "weakPoints": ["GPIO 调试"],
            "goals": ["完成单片机项目"],
        },
        "实操验证",
        "跟随示例完成 GPIO 输出验证并观察现象",
        "提交运行记录",
        3,
        {"mcu", "video"},
        ["mcu", "mcu"],
    )

    assert resource_type == "video"


def test_animation_task_is_routed_to_animation_agent_with_ready_params(monkeypatch):
    monkeypatch.setattr(
        learning_agents,
        "call_llm_json",
        lambda *_args, **_kwargs: {
            "tasks": [
                {
                    "id": "03",
                    "resourceType": "animation",
                    "resourceParams": {
                        "topic": "STM32 外部中断响应流程",
                        "requirements": "动态展示 EXTI 触发、NVIC 响应和清除挂起位",
                    },
                }
            ]
        },
    )

    result = plan_learning_path_stage_resources({
        "profile": {
            "studentProfile": {
                "学习目标": ["理解 STM32 中断响应时序"],
                "薄弱知识点": ["EXTI 与 NVIC 状态迁移"],
                "资源形式偏好": ["动画微课", "动态可视化"],
            }
        },
        "useLLM": True,
        "stage": {
            "focus": "STM32 外部中断",
            "nodes": [
                {
                    "id": "03",
                    "title": "中断响应动画讲解",
                    "description": "用动画展示从边沿触发到 ISR 执行的时序流程",
                    "deliverable": "完成动画中的知识检查",
                }
            ],
        },
    })

    task = result["tasks"][0]
    assert task["resourceType"] == "animation"
    assert task["resourceSelectionSource"] == "llm"
    assert task["resourceParams"]["topic"] == "STM32 外部中断响应流程"
    assert "EXTI" in task["resourceParams"]["requirements"]
    assert learning_agents._learning_path_resource_action(task["resourceType"]) == "生成动画微课"


def test_profile_router_can_choose_animation_for_dynamic_process_learning():
    resource_type, reason = learning_agents._profile_routed_resource_type(
        {
            "resourcePreferences": ["动画微课", "动态可视化"],
            "learningStyle": "视觉过程型",
            "recommendations": ["用状态迁移动画理解中断响应"],
            "weakPoints": ["中断响应时序"],
            "goals": ["理解 EXTI 到 NVIC 的信号流程"],
        },
        "概念建模",
        "观察外部中断的状态迁移和信号变化",
        "完成流程复述",
        2,
        {"animation", "video", "document", "mindmap"},
        [],
    )

    assert resource_type == "animation"
    assert "动画" in reason or "动态" in reason


def test_animation_learning_path_route_opens_task_backed_animation_page():
    route = app_module._learning_path_task_resource_route(
        "animation",
        "STM32 外部中断",
        "week-2-interrupt",
        "03",
        "animation-cache-key",
        {
            "topic": "STM32 外部中断响应流程",
            "requirements": "动态展示 EXTI、NVIC 和 ISR 的状态迁移",
        },
    )

    assert route.startswith("/personalized-resources/animation?")
    assert "topic=STM32+%E5%A4%96%E9%83%A8%E4%B8%AD%E6%96%AD%E5%93%8D%E5%BA%94%E6%B5%81%E7%A8%8B" in route
    assert "stageId=week-2-interrupt" in route
    assert "nodeId=03" in route
    assert "cacheKey=animation-cache-key" in route
    assert "autostart=1" in route


def test_mcu_agent_output_is_mapped_to_a_supported_simulator_project(monkeypatch):
    monkeypatch.setattr(
        learning_agents,
        "call_llm_json",
        lambda *_args, **_kwargs: {
            "tasks": [
                {
                    "id": "04",
                    "resourceType": "mcu",
                    "resourceParams": {
                        "board": "STM32F103C8T6",
                        "projectId": "stm32-gpio-interrupt-lab",
                        "topic": "STM32 GPIO 按键中断验证",
                    },
                }
            ]
        },
    )

    result = plan_learning_path_stage_resources({
        "profile": _profile(),
        "useLLM": True,
        "stage": {
            "focus": "STM32 GPIO",
            "nodes": [
                {
                    "id": "04",
                    "title": "实操验证",
                    "description": "使用按键输入验证 GPIO 外部中断处理流程",
                }
            ],
        },
    })

    task = result["tasks"][0]
    assert task["resourceType"] == "mcu"
    assert task["resourceParams"]["board"] == "arduino"
    assert task["resourceParams"]["projectId"] == "uno-button-ready"
    assert task["resourceParams"]["requestedBoard"] == "STM32F103C8T6"
    assert task["resourceParams"]["requestedProjectId"] == "stm32-gpio-interrupt-lab"
