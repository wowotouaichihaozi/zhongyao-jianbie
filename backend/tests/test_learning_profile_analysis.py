from backend import learning_agents


def test_profile_report_derives_radar_from_model_dimension_scores(monkeypatch):
    model_result = {
        "learningStyle": "项目实践驱动型",
        "overallScore": 76,
        "dimensionScores": [
            {"name": name, "score": score}
            for name, score in zip(
                learning_agents.DIMENSIONS,
                [3.2, 3.8, 4.1, 3.5, 3.7, 3.0],
            )
        ],
        "strengths": ["实验验证能力较好"],
        "weaknesses": ["中断调试证据不足"],
        "recommendations": ["完成一次中断专项实验"],
        "summary": "模型已根据画像与学习证据完成分析。",
    }
    monkeypatch.setattr(learning_agents, "call_llm_json", lambda *_args, **_kwargs: model_result)

    report = learning_agents.generate_profile_report(
        {
            "scaleScores": [3, 3, 3, 3, 3, 3],
            "chatStudentProfile": {"学习目标": ["掌握 STM32 中断"]},
            "completedProfileDimensions": ["学习目标"],
        }
    )

    assert report["source"] == "llm"
    assert report["radarScores"] == [3.2, 3.8, 4.1, 3.5, 3.7, 3.0]
    assert [item["score"] for item in report["dimensionScores"]] == report["radarScores"]
    assert "error" not in report


def test_profile_report_normalizes_missing_non_core_summary(monkeypatch):
    model_result = {
        "learningStyle": "分步骤实践型",
        "overallScore": 72,
        "radarScores": [3.0, 3.4, 3.8, 3.1, 3.6, 2.9],
        "strengths": ["愿意动手验证"],
        "weaknesses": ["调试证据不足"],
        "recommendations": ["完成一次带记录的调试实验"],
    }
    monkeypatch.setattr(learning_agents, "call_llm_json", lambda *_args, **_kwargs: model_result)

    report = learning_agents.generate_profile_report(
        {
            "scaleScores": [3, 3, 3, 3, 3, 3],
            "chatStudentProfile": {"学习目标": ["掌握 STM32 调试"]},
        }
    )

    assert report["source"] == "llm"
    assert report["summary"] == "学习风格为分步骤实践型；当前优势集中在愿意动手验证；下一阶段优先补强调试证据不足。"
    assert "error" not in report
