from backend import app as app_module


def test_generated_video_runner_binds_task_id_to_progress_updates(monkeypatch):
    updates = []

    monkeypatch.setattr(app_module, "xiaozhi_latest_context", lambda _user_id: {"profile": {}})
    monkeypatch.setattr(
        app_module,
        "retrieve_course_knowledge",
        lambda *_args, **_kwargs: {"sources": []},
    )
    monkeypatch.setattr(
        app_module,
        "xiaozhi_update_task",
        lambda task_id, **fields: updates.append((task_id, fields)),
    )

    def execute_task(task_id, user_id, topic, params, profile, sources, update):
        assert (task_id, user_id, topic) == ("video-task-1", 7, "GPIO")
        assert params == {"videoEngine": "seedance_2"}
        assert profile == {}
        assert sources == []
        update(
            status="running",
            result_json={"progress": 8, "currentStage": "planning"},
        )
        return {"progress": 100, "currentStage": "complete"}

    monkeypatch.setattr(app_module, "execute_generated_video_task", execute_task)

    app_module._xiaozhi_run_resource_task(
        "video-task-1",
        7,
        "generated_video",
        "GPIO",
        {"videoEngine": "seedance_2"},
    )

    assert updates[0] == (
        "video-task-1",
        {
            "status": "running",
            "result_json": {"progress": 8, "currentStage": "planning"},
        },
    )
    assert updates[-1][0] == "video-task-1"
    assert updates[-1][1]["status"] == "complete"
    assert updates[-1][1]["result_json"]["progress"] == 100
