from __future__ import annotations

import base64
import json
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest

import video_generation


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.ok = True
        self.status_code = 200
        self.text = ""

    def json(self):
        return self._payload


def test_video_first_frame_uses_seedream_45_contract(monkeypatch):
    settings = {
        "SEEDREAM_BASE_URL": "https://api.apimart.ai/v1",
        "SEEDREAM_API_KEY": "test-key",
    }
    calls = []
    monkeypatch.setattr(
        video_generation,
        "_setting",
        lambda key, default="": settings.get(key, default),
    )

    def fake_post(url, *, headers, json, timeout):
        calls.append((url, headers, json, timeout))
        return FakeResponse({"data": [{"status": "submitted", "task_id": "task-frame-1"}]})

    monkeypatch.setattr(video_generation.requests, "post", fake_post)
    monkeypatch.setattr(
        video_generation,
        "_wait_media_task",
        lambda base_url, token, task_id: {
            "result": {"images": [{"url": ["https://media.example/frame.png"]}]}
        },
    )

    result = video_generation._create_image("GPIO lesson cover")

    assert result == "https://media.example/frame.png"
    assert calls[0][0] == "https://api.apimart.ai/v1/images/generations"
    assert calls[0][1]["Authorization"] == "Bearer test-key"
    assert calls[0][2] == {
        "model": "seedream-4-5",
        "prompt": "GPIO lesson cover",
        "size": "16:9",
        "resolution": "2K",
        "n": 1,
        "watermark": False,
    }


def test_waiting_video_cover_only_generates_and_downloads_one_image(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(video_generation, "ROOT", tmp_path)
    monkeypatch.setattr(video_generation, "_image_api_token", lambda: "image-key")
    monkeypatch.setattr(
        video_generation,
        "_create_image",
        lambda prompt: calls.append(("image", prompt)) or "https://media.example/cover.jpg",
    )

    def fake_download(url, destination):
        calls.append(("download", url, destination))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"poster")

    monkeypatch.setattr(video_generation, "_download", fake_download)
    result = video_generation.generate_generated_video_cover(
        "video-cover-1",
        101,
        "黄芪性状辨识",
        {"style": "本草图鉴"},
    )

    assert result["posterUrl"].endswith("/video-cover-1/poster")
    assert [call[0] for call in calls] == ["image", "download"]
    assert "黄芪性状辨识" in calls[0][1]
    assert video_generation.media_file(101, "video-cover-1", "poster.jpg").read_bytes() == b"poster"


def test_seedance_15_uses_dedicated_workflow_credentials(monkeypatch):
    settings = {
        "COZE_SEEDANCE_15_API_BASE_URL": "https://workflow.example/v1/",
        "COZE_SEEDANCE_15_API_TOKEN": "video-token",
        "COZE_SEEDANCE_15_WORKFLOW_ID": "workflow-15",
        "COZE_API_BASE_URL": "https://chat.example/v3/chat",
        "COZE_API_TOKEN": "chat-token",
    }
    calls = []

    monkeypatch.setattr(
        video_generation,
        "_setting",
        lambda key, default="": settings.get(key, default),
    )

    def fake_post(url, *, headers, json, timeout):
        calls.append(("post", url, headers, json, timeout))
        return FakeResponse({"data": {"execute_id": "execute-1"}})

    def fake_get(url, *, headers, timeout):
        calls.append(("get", url, headers, None, timeout))
        return FakeResponse(
            {
                "data": [
                    {
                        "execute_status": "SUCCESS",
                        "output": {"video_url": "https://media.example/final.mp4"},
                    }
                ]
            }
        )

    monkeypatch.setattr(video_generation.requests, "post", fake_post)
    monkeypatch.setattr(video_generation.requests, "get", fake_get)

    result = video_generation._create_seedance_15(
        "https://media.example/first-frame.png",
        "Explain GPIO interrupts",
    )

    assert result == "https://media.example/final.mp4"
    assert calls[0][1] == "https://workflow.example/v1/workflow/run"
    assert calls[1][1] == (
        "https://workflow.example/v1/workflows/workflow-15/"
        "run_histories/execute-1"
    )
    assert calls[0][2]["Authorization"] == "Bearer video-token"
    assert calls[1][2]["Authorization"] == "Bearer video-token"
    assert all("chat.example" not in call[1] for call in calls)
    assert calls[0][3]["parameters"] == {
        "img_head": "https://media.example/first-frame.png",
        "prompt": "Explain GPIO interrupts",
    }


def test_video_engine_and_default_model_contract():
    assert video_generation.DEFAULT_VIDEO_ENGINE == "seedance_1_5_coze"
    assert video_generation.SUPPORTED_VIDEO_ENGINES == {
        "seedance_1_5_coze",
        "seedance_2_mini",
        "seedance_2",
    }
    assert video_generation.VIDEO_ENGINE_MODELS["seedance_2_mini"] == (
        "doubao-seedance-2.0-mini"
    )
    assert video_generation.VIDEO_ENGINE_MODELS["seedance_2"] == (
        "doubao-seedance-2.0"
    )
    assert video_generation._video_engine({}) == "seedance_1_5_coze"
    assert video_generation._video_engine({"videoEngine": "unsupported"}) == (
        "seedance_1_5_coze"
    )


def test_xfyun_tts_signed_url_uses_hmac_authorization_without_secret():
    signed = video_generation._xfyun_tts_signed_url(
        "wss://cbm01.cn-huabei-1.xf-yun.com/v1/private/mcd9m97e6",
        "public-key",
        "private-secret",
        date="Sat, 15 Aug 2026 09:00:00 GMT",
    )
    query = parse_qs(urlsplit(signed).query)
    authorization = base64.b64decode(query["authorization"][0]).decode("utf-8")

    assert urlsplit(signed).scheme == "wss"
    assert query["host"] == ["cbm01.cn-huabei-1.xf-yun.com"]
    assert query["date"] == ["Sat, 15 Aug 2026 09:00:00 GMT"]
    assert 'api_key="public-key"' in authorization
    assert 'algorithm="hmac-sha256"' in authorization
    assert "private-secret" not in signed


def test_xfyun_tts_request_uses_authorized_voice_and_utf8_payload(monkeypatch):
    monkeypatch.setattr(video_generation, "_setting", lambda _key, default="": default)
    request = video_generation._xfyun_tts_request(
        "GPIO 中断实验",
        "app-id",
        "x6_lingxiaoxuan_pro",
    )

    assert request["header"] == {"app_id": "app-id", "status": 2}
    assert request["parameter"]["tts"]["vcn"] == "x6_lingxiaoxuan_pro"
    assert request["parameter"]["tts"]["audio"] == {
        "encoding": "lame",
        "sample_rate": 24000,
        "channels": 1,
        "bit_depth": 16,
        "frame_size": 0,
    }
    assert base64.b64decode(request["payload"]["text"]["text"]).decode("utf-8") == "GPIO 中断实验"


def test_xfyun_tts_collects_frames_and_converts_mp3_to_aac(monkeypatch, tmp_path):
    settings = {
        "XFYUN_TTS_APP_ID": "app-id",
        "XFYUN_TTS_API_KEY": "api-key",
        "XFYUN_TTS_API_SECRET": "api-secret",
        "XFYUN_TTS_VOICE": "x6_lingxiaoxuan_pro",
    }
    monkeypatch.setattr(video_generation, "_setting", lambda key, default="": settings.get(key, default))
    monkeypatch.setattr(video_generation, "_xfyun_tts_signed_url", lambda *_args, **_kwargs: "wss://signed.example/tts")
    sent = []

    class FakeSocket:
        frames = iter(
            [
                json.dumps({"header": {"code": 0}, "payload": {"audio": {"audio": base64.b64encode(b"mp3-1").decode(), "status": 1}}}),
                json.dumps({"header": {"code": 0}, "payload": {"audio": {"audio": base64.b64encode(b"mp3-2").decode(), "status": 2}}}),
            ]
        )

        def send(self, value):
            sent.append(json.loads(value))

        def recv(self, timeout=None):
            return next(self.frames)

        def close(self):
            sent.append("closed")

    monkeypatch.setattr(video_generation, "websocket_connect", lambda url, open_timeout, close_timeout: FakeSocket())

    destination = tmp_path / "segment.aac"

    def fake_run(command):
        assert (tmp_path / "segment.mp3").read_bytes() == b"mp3-1mp3-2"
        assert command[-1] == str(destination)
        destination.write_bytes(b"aac")

    monkeypatch.setattr(video_generation, "_run", fake_run)
    video_generation._create_xfyun_tts("测试配音", "nova", destination)

    assert destination.read_bytes() == b"aac"
    assert not (tmp_path / "segment.mp3").exists()
    assert sent[-1] == "closed"
    assert sent[0]["parameter"]["tts"]["vcn"] == "x6_lingxiaoxuan_pro"


def test_xfyun_tts_surfaces_business_error(monkeypatch, tmp_path):
    monkeypatch.setattr(
        video_generation,
        "_xfyun_tts_credentials",
        lambda: ("app-id", "api-key", "api-secret"),
    )
    monkeypatch.setattr(video_generation, "_xfyun_tts_signed_url", lambda *_args, **_kwargs: "wss://signed.example/tts")

    class FakeSocket:
        def send(self, _value):
            pass

        def recv(self, timeout=None):
            return json.dumps({"header": {"code": 10005, "message": "invalid parameter"}})

        def close(self):
            pass

    monkeypatch.setattr(video_generation, "websocket_connect", lambda *_args, **_kwargs: FakeSocket())

    with pytest.raises(video_generation.VideoGenerationError, match="10005"):
        video_generation._create_xfyun_tts("测试", "x6_lingxiaoxuan_pro", tmp_path / "segment.aac")


@pytest.mark.parametrize(
    "engine",
    ["seedance_1_5_coze", "seedance_2_mini", "seedance_2"],
)
def test_single_model_segment_is_expanded_to_requested_30_seconds(
    monkeypatch,
    engine,
):
    monkeypatch.setattr(
        video_generation,
        "call_llm_json",
        lambda *_args, **_kwargs: {
            "title": "GPIO 基础",
            "summary": "GPIO 课程讲解",
            "segments": [
                {
                    "id": "segment_01",
                    "title": "GPIO 架构",
                    "duration": 10,
                    "narration": "先认识 GPIO 的基础架构。",
                    "image_prompt": "GPIO architecture, no text",
                    "video_prompt": "Explain GPIO architecture, no text",
                }
            ],
        },
    )

    plan = video_generation._build_plan(
        "GPIO",
        {"duration": 30, "videoEngine": engine},
        {},
        [],
    )

    durations = [segment["duration"] for segment in plan["segments"]]
    assert sum(durations) == 30
    assert len(durations) >= 2
    assert all(5 <= duration <= 15 for duration in durations)
    if engine == "seedance_1_5_coze":
        assert durations == [10, 10, 10]


def test_seedance_2_preserves_valid_variable_segment_durations(monkeypatch):
    monkeypatch.setattr(
        video_generation,
        "call_llm_json",
        lambda *_args, **_kwargs: {
            "title": "中断课程",
            "summary": "分镜讲解",
            "segments": [
                {
                    "title": "入口",
                    "duration": 15,
                    "narration": "先识别中断入口。",
                    "image_prompt": "interrupt entry, no text",
                    "video_prompt": "show interrupt entry, no text",
                },
                {
                    "title": "处理",
                    "duration": 14,
                    "narration": "再观察中断处理流程。",
                    "image_prompt": "interrupt flow, no text",
                    "video_prompt": "show interrupt flow, no text",
                },
            ],
        },
    )

    plan = video_generation._build_plan(
        "中断",
        {"duration": 30, "videoEngine": "seedance_2"},
        {},
        [],
    )

    assert [segment["duration"] for segment in plan["segments"]] == [15, 14]
    assert plan["totalDuration"] == 29


@pytest.mark.parametrize(
    ("engine", "settings", "expected"),
    [
        (
            "seedance_2_mini",
            {
                "VIDEO_VIDEO_MODEL_MINI": "configured-mini",
                "VIDEO_VIDEO_MODEL": "legacy-mini",
            },
            "configured-mini",
        ),
        (
            "seedance_2_mini",
            {"VIDEO_VIDEO_MODEL": "legacy-mini"},
            "legacy-mini",
        ),
        ("seedance_2_mini", {}, "doubao-seedance-2.0-mini"),
        (
            "seedance_2",
            {"VIDEO_VIDEO_MODEL_FULL": "configured-full"},
            "configured-full",
        ),
        ("seedance_2", {}, "doubao-seedance-2.0"),
    ],
)
def test_seedance_2_model_setting_compatibility(
    monkeypatch,
    engine,
    settings,
    expected,
):
    monkeypatch.setattr(
        video_generation,
        "_setting",
        lambda key, default="": settings.get(key, default),
    )

    assert video_generation._seedance_2_model(engine) == expected


@pytest.mark.parametrize(
    ("resolution", "dimensions"),
    [
        ("480p", (854, 480)),
        ("720p", (1280, 720)),
        ("1080p", (1920, 1080)),
    ],
)
def test_video_resolution_contract(resolution, dimensions):
    params = video_generation._normalize_video_params(
        {
            "video_engine": "seedance_2",
            "videoResolution": resolution.upper(),
            "aspectRatio": "4:3",
        }
    )

    assert params["videoEngine"] == "seedance_2"
    assert params["resolution"] == resolution
    assert params["size"] == "16:9"
    assert video_generation.VIDEO_RESOLUTION_DIMENSIONS[resolution] == dimensions


def test_invalid_resolution_and_size_fall_back_to_defaults():
    params = video_generation._normalize_video_params(
        {"resolution": "2k", "size": "1:1"}
    )

    assert params["resolution"] == "720p"
    assert params["size"] == "16:9"


@pytest.mark.parametrize(
    ("engine", "settings", "missing_name"),
    [
        (
            "seedance_1_5_coze",
            {
                "VIDEO_IMAGE_API_KEY": "configured",
                "XFYUN_TTS_APP_ID": "configured",
                "XFYUN_TTS_API_KEY": "configured",
                "XFYUN_TTS_API_SECRET": "configured",
                "COZE_SEEDANCE_15_API_TOKEN": "configured",
            },
            "COZE_SEEDANCE_15_WORKFLOW_ID",
        ),
        (
            "seedance_2_mini",
            {
                "VIDEO_IMAGE_API_KEY": "configured",
                "XFYUN_TTS_APP_ID": "configured",
                "XFYUN_TTS_API_KEY": "configured",
                "XFYUN_TTS_API_SECRET": "configured",
            },
            "VIDEO_VIDEO_API_KEY",
        ),
        (
            "seedance_2",
            {
                "VIDEO_IMAGE_API_KEY": "configured",
                "XFYUN_TTS_APP_ID": "configured",
                "XFYUN_TTS_API_KEY": "configured",
                "XFYUN_TTS_API_SECRET": "configured",
            },
            "VIDEO_VIDEO_API_KEY",
        ),
    ],
)
def test_preflight_reports_missing_selected_engine_configuration(
    monkeypatch,
    engine,
    settings,
    missing_name,
):
    monkeypatch.setattr(
        video_generation,
        "_setting",
        lambda key, default="": settings.get(key, default),
    )

    with pytest.raises(video_generation.VideoGenerationError) as exc_info:
        video_generation._validate_video_configuration(engine)

    assert missing_name in str(exc_info.value)
    assert "configured" not in str(exc_info.value)


def test_execute_preflights_all_credentials_before_planning_or_first_image(
    monkeypatch,
):
    calls = []
    settings = {
        "VIDEO_IMAGE_API_KEY": "configured",
        "VIDEO_VIDEO_API_KEY": "configured",
    }
    monkeypatch.setattr(
        video_generation,
        "_setting",
        lambda key, default="": settings.get(key, default),
    )
    monkeypatch.setattr(
        video_generation,
        "_build_plan",
        lambda *_args: calls.append("planning"),
    )
    monkeypatch.setattr(
        video_generation,
        "_create_image",
        lambda *_args: calls.append("image"),
    )

    with pytest.raises(
        video_generation.VideoGenerationError,
        match="XFYUN_TTS_APP_ID",
    ):
        video_generation.execute_generated_video_task(
            "task-1",
            7,
            "Interrupts",
            {"videoEngine": "seedance_2", "resolution": "1080p"},
            {},
            [],
            lambda **_payload: None,
        )

    assert calls == []


@pytest.mark.parametrize(
    ("engine", "resolution", "expected_model"),
    [
        ("seedance_2_mini", "480p", "doubao-seedance-2.0-mini"),
        ("seedance_2", "1080p", "doubao-seedance-2.0"),
    ],
)
def test_seedance_2_api_uses_engine_model_and_dimensions(
    monkeypatch,
    engine,
    resolution,
    expected_model,
):
    requests_seen = []

    monkeypatch.setattr(
        video_generation,
        "_setting",
        lambda key, default="": {
            "VIDEO_MEDIA_BASE_URL": "https://media.example/v1",
        }.get(key, default),
    )
    monkeypatch.setattr(video_generation, "_headers", lambda _token: {})
    monkeypatch.setattr(
        video_generation,
        "_wait_media_task",
        lambda base_url, token, task_id: {
            "result": {"videos": [{"url": "https://media.example/result.mp4"}]}
        },
    )

    def fake_post(url, *, headers, json, timeout):
        requests_seen.append((url, headers, json, timeout))
        return FakeResponse({"data": [{"task_id": "video-task"}]})

    monkeypatch.setattr(video_generation.requests, "post", fake_post)

    result = video_generation._create_seedance_2_api(
        engine,
        "https://media.example/first-frame.png",
        "Explain an interrupt controller",
        resolution,
        "16:9",
        15,
    )

    assert result == "https://media.example/result.mp4"
    assert requests_seen[0][0] == "https://media.example/v1/videos/generations"
    assert requests_seen[0][2] == {
        "model": expected_model,
        "prompt": "Explain an interrupt controller",
        "image_urls": ["https://media.example/first-frame.png"],
        "duration": 15,
        "resolution": resolution,
        "size": "16:9",
        "generate_audio": False,
    }


def test_execute_explicitly_propagates_selected_engine_and_resolution(
    monkeypatch,
    tmp_path,
):
    generation_calls = []
    updates = []
    params = {
        "videoEngine": "seedance_2",
        "resolution": "1080p",
        "size": "16:9",
    }
    original_params = dict(params)
    plan = {
        "title": "Interrupts",
        "summary": "A focused explanation.",
        "segments": [
            {
                "id": "segment_01",
                "title": "Overview",
                "duration": 10,
                "narration": "先理解中断入口。",
                "image_prompt": "interrupt controller diagram, no text",
                "video_prompt": "explain interrupt flow, no text",
            }
        ],
    }

    monkeypatch.setattr(video_generation, "ROOT", tmp_path)
    monkeypatch.setattr(
        video_generation,
        "_validate_video_configuration",
        lambda _engine: None,
    )
    monkeypatch.setattr(video_generation, "_build_plan", lambda *args: plan)
    monkeypatch.setattr(
        video_generation,
        "_create_image",
        lambda _prompt: "https://media.example/frame.png",
    )
    monkeypatch.setattr(video_generation, "_download", lambda *_args: None)
    monkeypatch.setattr(video_generation, "_create_tts", lambda *_args: None)
    monkeypatch.setattr(
        video_generation,
        "_create_seedance_video",
        lambda *args: generation_calls.append(args)
        or "https://media.example/segment.mp4",
    )

    def fake_compose(directory, segments, progress, resolution):
        assert resolution == "1080p"
        return directory / "final.mp4", directory / "poster.jpg", 10

    monkeypatch.setattr(video_generation, "_compose", fake_compose)

    assert generation_calls == []
    result = video_generation.execute_generated_video_task(
        "task-1",
        7,
        "Interrupts",
        params,
        {},
        [],
        lambda **payload: updates.append(payload),
    )

    assert params == original_params
    assert generation_calls == [
        (
            "seedance_2",
            "https://media.example/frame.png",
            "explain interrupt flow, no text",
            "1080p",
            "16:9",
            10,
        )
    ]
    assert result["engine"] == "seedance_2"
    assert result["resolution"] == "1080p"
    assert result["selectedResource"]["metadata"]["resolution"] == "1080p"
    assert updates
    assert all(
        update["result_json"]["resolution"] == "1080p" for update in updates
    )


@pytest.mark.parametrize(
    ("resolution", "width", "height"),
    [
        ("480p", 854, 480),
        ("720p", 1280, 720),
        ("1080p", 1920, 1080),
    ],
)
def test_compose_normalizes_and_validates_requested_dimensions(
    monkeypatch,
    tmp_path,
    resolution,
    width,
    height,
):
    (tmp_path / "segments").mkdir()
    (tmp_path / "audio").mkdir()
    commands = []
    monkeypatch.setattr(video_generation, "_run", lambda command: commands.append(command))

    def fake_probe(*_args, **_kwargs):
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "format": {"duration": "10.0"},
                    "streams": [
                        {"codec_type": "video", "width": width, "height": height},
                        {"codec_type": "audio"},
                    ],
                }
            ),
        )

    monkeypatch.setattr(video_generation.subprocess, "run", fake_probe)

    video_generation._compose(
        tmp_path,
        [{"id": "segment_01", "narration": "中断控制器。"}],
        lambda *_args: None,
        resolution,
    )

    filter_index = commands[0].index("-filter_complex") + 1
    filter_complex = commands[0][filter_index]
    assert f"scale={width}:{height}" in filter_complex
    assert f"crop={width}:{height}" in filter_complex


def test_compose_uses_planned_segment_duration(monkeypatch, tmp_path):
    (tmp_path / "segments").mkdir()
    (tmp_path / "audio").mkdir()
    commands = []
    monkeypatch.setattr(video_generation, "_run", lambda command: commands.append(command))
    monkeypatch.setattr(
        video_generation.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "format": {"duration": "15.0"},
                    "streams": [
                        {"codec_type": "video", "width": 1280, "height": 720},
                        {"codec_type": "audio"},
                    ],
                }
            ),
        ),
    )

    _final, _poster, duration = video_generation._compose(
        tmp_path,
        [
            {
                "id": "segment_01",
                "duration": 15,
                "narration": "观察中断控制器的处理流程。",
            }
        ],
        lambda *_args: None,
        "720p",
    )

    filter_index = commands[0].index("-filter_complex") + 1
    filter_complex = commands[0][filter_index]
    subtitle = (tmp_path / "segments" / "segment_01.srt").read_text(
        encoding="utf-8"
    )
    assert "trim=duration=15" in filter_complex
    assert "atrim=duration=15" in filter_complex
    assert "00:00:15,000" in subtitle
    assert duration == 15


def test_compose_rejects_final_duration_that_misses_plan(monkeypatch, tmp_path):
    (tmp_path / "segments").mkdir()
    (tmp_path / "audio").mkdir()
    monkeypatch.setattr(video_generation, "_run", lambda _command: None)
    monkeypatch.setattr(
        video_generation.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "format": {"duration": "10.0"},
                    "streams": [
                        {"codec_type": "video", "width": 1280, "height": 720},
                        {"codec_type": "audio"},
                    ],
                }
            ),
        ),
    )

    with pytest.raises(video_generation.VideoGenerationError, match="规划时长 15 秒"):
        video_generation._compose(
            tmp_path,
            [
                {
                    "id": "segment_01",
                    "duration": 15,
                    "narration": "观察中断控制器的处理流程。",
                }
            ],
            lambda *_args: None,
            "720p",
        )
