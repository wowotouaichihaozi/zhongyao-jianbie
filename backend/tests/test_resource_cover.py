from PIL import Image

from backend.resource_cover import COVER_SIZE, render_resource_task_cover


def _task(updated_at: str = "2026-08-30T12:00:00") -> dict:
    return {
        "taskId": "ppt_week-1-03",
        "taskType": "ppt",
        "title": "第一周：中药性味归经与功效辨析",
        "status": "complete",
        "updatedAt": updated_at,
        "result": {
            "slides": [
                {"title": "四气五味", "description": "掌握寒热温凉与辛甘酸苦咸"},
                {"title": "归经辨析", "description": "结合药物功效判断归经"},
            ]
        },
    }


def test_resource_cover_is_png_with_expected_size_and_reuses_cache(tmp_path):
    first_path, first_fingerprint = render_resource_task_cover(_task(), tmp_path)
    second_path, second_fingerprint = render_resource_task_cover(_task(), tmp_path)

    assert first_path == second_path
    assert first_fingerprint == second_fingerprint
    assert first_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(first_path) as image:
        assert image.size == COVER_SIZE
        assert image.format == "PNG"


def test_resource_cover_changes_when_task_is_updated(tmp_path):
    first_path, first_fingerprint = render_resource_task_cover(_task(), tmp_path)
    updated_path, updated_fingerprint = render_resource_task_cover(
        _task("2026-08-30T12:01:00"),
        tmp_path,
    )

    assert updated_path != first_path
    assert updated_fingerprint != first_fingerprint
    assert updated_path.exists()
