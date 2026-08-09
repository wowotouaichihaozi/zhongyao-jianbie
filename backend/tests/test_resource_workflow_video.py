from backend import resource_workflow


def test_search_videos_uses_metadata_rich_api_results_first(monkeypatch):
    monkeypatch.setattr(
        resource_workflow,
        "search_bilibili_api",
        lambda _query: [
            {
                "bvid": f"BV{index:010d}",
                "title": f"STM32 视频 {index}",
                "url": f"https://www.bilibili.com/video/BV{index:010d}",
                "embedUrl": f"https://player.bilibili.com/player.html?bvid=BV{index:010d}",
                "cover": f"https://i0.hdslb.com/{index}.jpg",
                "author": "课程作者",
                "duration": "10:00",
                "snippet": "UP主：课程作者",
            }
            for index in range(8)
        ],
    )
    monkeypatch.setattr(
        resource_workflow,
        "search_bilibili_web",
        lambda _query: (_ for _ in ()).throw(AssertionError("metadata-rich API results should not need HTML fallback")),
    )
    monkeypatch.setattr(
        resource_workflow,
        "search_bing_videos",
        lambda _query: (_ for _ in ()).throw(AssertionError("metadata-rich API results should not need Bing fallback")),
    )
    monkeypatch.setattr(
        resource_workflow,
        "fetch_bilibili_video_detail",
        lambda _bvid: (_ for _ in ()).throw(AssertionError("complete API metadata should not need detail requests")),
    )

    results = resource_workflow.search_videos("STM32 GPIO")

    assert len(results) == 8
    assert all(item["cover"].startswith("https://i0.hdslb.com/") for item in results)
    assert all(item["title"].startswith("STM32 视频") for item in results)


def test_search_videos_merges_richer_fallback_metadata(monkeypatch):
    monkeypatch.setattr(
        resource_workflow,
        "search_bilibili_api",
        lambda _query: [
            {
                "bvid": "BV0000000001",
                "title": "Bilibili 视频",
                "url": "https://www.bilibili.com/video/BV0000000001",
                "cover": "",
                "author": "",
                "duration": "",
            }
        ],
    )
    monkeypatch.setattr(
        resource_workflow,
        "search_bilibili_web",
        lambda _query: [
            {
                "bvid": "BV0000000001",
                "title": "GPIO 实验讲解",
                "url": "https://www.bilibili.com/video/BV0000000001",
                "embedUrl": "https://player.bilibili.com/player.html?bvid=BV0000000001",
                "cover": "https://i0.hdslb.com/gpio.jpg",
                "author": "实验课程",
                "duration": "08:20",
                "snippet": "UP主：实验课程",
            }
        ],
    )
    monkeypatch.setattr(resource_workflow, "search_bing_videos", lambda _query: [])
    monkeypatch.setattr(
        resource_workflow,
        "fetch_bilibili_video_detail",
        lambda _bvid: (_ for _ in ()).throw(AssertionError("merged search metadata should not need detail requests")),
    )

    results = resource_workflow.search_videos("GPIO 实验")

    assert results == [
        {
            "bvid": "BV0000000001",
            "title": "GPIO 实验讲解",
            "url": "https://www.bilibili.com/video/BV0000000001",
            "cover": "https://i0.hdslb.com/gpio.jpg",
            "author": "实验课程",
            "duration": "08:20",
            "embedUrl": "https://player.bilibili.com/player.html?bvid=BV0000000001",
            "snippet": "UP主：实验课程",
        }
    ]


def test_search_videos_enriches_bare_bvid_results(monkeypatch):
    monkeypatch.setattr(
        resource_workflow,
        "search_bilibili_api",
        lambda _query: [
            {
                "bvid": "BV0000000002",
                "title": "Bilibili 视频",
                "url": "https://www.bilibili.com/video/BV0000000002",
                "embedUrl": "https://player.bilibili.com/player.html?bvid=BV0000000002",
                "cover": "",
                "author": "",
                "duration": "",
                "snippet": "",
            }
        ],
    )
    monkeypatch.setattr(resource_workflow, "search_bilibili_web", lambda _query: [])
    monkeypatch.setattr(resource_workflow, "search_bing_videos", lambda _query: [])
    monkeypatch.setattr(
        resource_workflow,
        "fetch_bilibili_video_detail",
        lambda bvid: {
            "title": "定时器实验讲解",
            "cover": f"https://i0.hdslb.com/{bvid}.jpg",
            "author": "嵌入式课程",
            "duration": "12:30",
            "snippet": "UP主：嵌入式课程　时长：12:30",
        },
    )

    results = resource_workflow.search_videos("定时器")

    assert results[0]["title"] == "定时器实验讲解"
    assert results[0]["cover"] == "https://i0.hdslb.com/BV0000000002.jpg"
    assert results[0]["author"] == "嵌入式课程"
    assert results[0]["duration"] == "12:30"


def test_search_videos_prioritizes_target_platform_and_filters_conflicts(monkeypatch):
    candidates = [
        {
            "bvid": "BV0000000101",
            "title": "MSPM0 GPIO 快速入门",
            "url": "https://www.bilibili.com/video/BV0000000101",
            "cover": "https://i0.hdslb.com/mspm0.jpg",
            "author": "开发板课程",
            "duration": "10:00",
        },
        {
            "bvid": "BV0000000102",
            "title": "STM32 GPIO 工作模式详解",
            "url": "https://www.bilibili.com/video/BV0000000102",
            "cover": "https://i0.hdslb.com/stm32-gpio.jpg",
            "author": "嵌入式课程",
            "duration": "12:00",
        },
        {
            "bvid": "BV0000000103",
            "title": "STM32 HAL GPIO 调试方法",
            "url": "https://www.bilibili.com/video/BV0000000103",
            "cover": "https://i0.hdslb.com/stm32-debug.jpg",
            "author": "嵌入式课程",
            "duration": "15:00",
        },
        {
            "bvid": "BV0000000104",
            "title": "GPIO 调试检查清单",
            "url": "https://www.bilibili.com/video/BV0000000104",
            "cover": "https://i0.hdslb.com/gpio-debug.jpg",
            "author": "硬件课堂",
            "duration": "08:00",
        },
        {
            "bvid": "BV0000000105",
            "title": "POCIB 基础教程",
            "url": "https://www.bilibili.com/video/BV0000000105",
            "cover": "https://i0.hdslb.com/pocib.jpg",
            "author": "其他课程",
            "duration": "05:00",
        },
    ]
    monkeypatch.setattr(resource_workflow, "search_bilibili_api", lambda _query: candidates)
    monkeypatch.setattr(resource_workflow, "search_bilibili_web", lambda _query: [])
    monkeypatch.setattr(resource_workflow, "search_bing_videos", lambda _query: [])

    results = resource_workflow.search_videos("STM32 GPIO 调试 教程")

    assert [item["bvid"] for item in results] == [
        "BV0000000103",
        "BV0000000102",
        "BV0000000104",
    ]
    assert all("MSPM0" not in item["title"] for item in results)


def test_video_search_query_uses_profile_platform_and_requested_concepts():
    context = resource_workflow.ResourceContext(
        profile={"chatStudentProfile": {"专业/课程背景": "STM32 嵌入式系统"}},
        route={},
        question_sheets=[],
        mcu_experiments=[],
        knowledge={},
    )

    query = resource_workflow.build_video_search_query(
        ["第一周：GPIO基础与调试入门 · 调试证据归档", "GPIO"],
        context,
    )

    assert query.startswith("STM32")
    assert "GPIO" in query
    assert "调试" in query
    assert "定时器" not in query


def test_search_videos_keeps_platform_specific_results_when_enough_exist(monkeypatch):
    candidates = [
        {
            "bvid": f"BV00000002{index:02d}",
            "title": f"STM32 GPIO 调试教程 {index}",
            "url": f"https://www.bilibili.com/video/BV00000002{index:02d}",
            "cover": f"https://i0.hdslb.com/stm32-{index}.jpg",
            "author": "嵌入式课程",
            "duration": "10:00",
        }
        for index in range(1, 4)
    ] + [
        {
            "bvid": "BV0000000299",
            "title": "GPIO 调试检查清单",
            "url": "https://www.bilibili.com/video/BV0000000299",
            "cover": "https://i0.hdslb.com/generic.jpg",
            "author": "硬件课程",
            "duration": "08:00",
        }
    ]
    monkeypatch.setattr(resource_workflow, "search_bilibili_api", lambda _query: candidates)
    monkeypatch.setattr(resource_workflow, "search_bilibili_web", lambda _query: [])
    monkeypatch.setattr(resource_workflow, "search_bing_videos", lambda _query: [])

    results = resource_workflow.search_videos("STM32 GPIO 调试 教程")

    assert len(results) == 3
    assert all("STM32" in item["title"] for item in results)


def test_resource_workflow_exposes_quality_for_every_resource_type(monkeypatch):
    citations = [{"id": "KB1", "title": "GPIO 课程讲义", "section": 1}]
    monkeypatch.setattr(
        resource_workflow,
        "retrieve_course_knowledge",
        lambda *_args, **_kwargs: {
            "grounded": True,
            "citations": citations,
            "hits": [{"title": "GPIO 工作模式", "excerpt": "GPIO 可配置为输入和输出模式。", "citationId": "KB1"}],
            "stats": {"chunkCount": 1},
        },
    )
    monkeypatch.setattr(
        resource_workflow,
        "list_question_sheets",
        lambda _user_id: [
            {
                "id": 7,
                "title": "GPIO 专项题单",
                "course_name": "嵌入式系统",
                "target_topic": "GPIO",
                "question_count": 10,
                "question_bank": {"questions": [{"stem": "GPIO 是什么", "knowledge_point": "GPIO"}]},
            }
        ],
    )
    monkeypatch.setattr(
        resource_workflow,
        "search_videos",
        lambda _query: [
            {
                "bvid": f"BV{index:010d}",
                "title": f"GPIO 视频 {index}",
                "url": f"https://www.bilibili.com/video/BV{index:010d}",
                "cover": f"https://i0.hdslb.com/{index}.jpg",
            }
            for index in range(1, 6)
        ],
    )

    workflow = resource_workflow.generate_resource_workflow(
        {
            "profile": {"aiAnalysis": {"weaknesses": ["GPIO"]}},
            "request": {"topic": "GPIO"},
        },
        user_id=101,
    )

    resources = workflow["resources"]
    assert {item["type"] for item in resources} == {"document", "mindmap", "ppt", "video", "quiz", "simulator"}
    for item in resources:
        quality = item["qualityEvaluation"]
        assert quality == item["metadata"]["qualityEvaluation"]
        assert 0 <= quality["score"] <= 100
        assert quality["passed"] is True
        assert quality["reviewStatus"] in {"passed", "needs-verification"}


def test_single_mindmap_request_does_not_call_unrelated_video_agent(monkeypatch):
    monkeypatch.setattr(resource_workflow, "list_question_sheets", lambda _user_id: [])
    monkeypatch.setattr(
        resource_workflow,
        "retrieve_course_knowledge",
        lambda *_args, **_kwargs: {"grounded": False, "citations": [], "hits": [], "stats": {}},
    )
    monkeypatch.setattr(
        resource_workflow,
        "search_videos",
        lambda _query: (_ for _ in ()).throw(AssertionError("mindmap task must not invoke video search")),
    )

    workflow = resource_workflow.generate_resource_workflow(
        {
            "profile": {"aiAnalysis": {"weaknesses": ["GPIO"]}},
            "request": {"topic": "GPIO", "resourceType": "mindmap"},
        },
        user_id=101,
    )

    assert [item["type"] for item in workflow["resources"]] == ["mindmap"]
    assert workflow["planner"]["requestedResourceType"] == "mindmap"
    mindmap = workflow["resources"][0]
    assert mindmap["content"].startswith("# GPIO专项学习导图")
    assert len([line for line in mindmap["content"].splitlines() if line.startswith("## ")]) >= 4
    assert len([line for line in mindmap["content"].splitlines() if line.startswith("### ")]) >= 4
    assert mindmap["metadata"]["format"] == "mindmap-markdown"
    assert mindmap["metadata"]["renderer"] == "mind-map-wizard"


def test_generated_question_bank_and_ppt_receive_structural_quality_scores():
    questions = [
        {
            "id": f"Q{index}",
            "type": "单选题" if index % 2 else "判断题",
            "stem": f"题目 {index}",
            "answer": "A",
            "analysis": "依据配置与运行现象进行判断。",
        }
        for index in range(1, 7)
    ]
    question_quality = resource_workflow.evaluate_question_bank_resource(
        {"questions": questions},
        expected_count=6,
        citations=[{"id": "KB1"}],
    )
    ppt_quality = resource_workflow.evaluate_ppt_resource(
        {
            "pages": [
                {"title": f"第 {index} 页", "h": "<section>" + ("内容" * 30) + "</section>"}
                for index in range(1, 7)
            ]
        },
        expected_page_count=6,
        citations=[{"id": "KB1"}],
    )

    assert question_quality["passed"] is True
    assert question_quality["questionCount"] == 6
    assert ppt_quality["passed"] is True
    assert ppt_quality["pageCount"] == 6
