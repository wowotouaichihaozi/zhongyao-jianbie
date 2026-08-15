from __future__ import annotations

import base64
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

import profile_portrait_service as portrait_service


class _JsonResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class _BytesResponse(_JsonResponse):
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return self.payload


class ProfilePortraitServiceTests(unittest.TestCase):
    def test_generation_uses_relay_compatible_payload_and_returns_bytes(self) -> None:
        image_bytes = b"\x89PNG\r\n\x1a\n" + (b"portrait-service" * 200)
        response = _JsonResponse({"data": [{"b64_json": base64.b64encode(image_bytes).decode("ascii")}]})
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tempdir:
            with (
                patch.object(portrait_service, "PORTRAIT_DIR", Path(tempdir)),
                patch.dict(
                    portrait_service.os.environ,
                    {
                        "SEEDREAM_BASE_URL": "https://image.example/v1",
                        "SEEDREAM_API_KEY": "test-key",
                    },
                    clear=False,
                ),
                patch.object(portrait_service.urllib.request, "urlopen", return_value=response) as urlopen,
            ):
                generated = portrait_service.generate_profile_portrait(
                    {"aiAnalysis": {"learningStyle": "实践型"}},
                    701,
                )

        request = urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "seedream-4-5")
        self.assertEqual(payload["size"], "1:1")
        self.assertEqual(payload["resolution"], "2K")
        self.assertEqual(payload["watermark"], False)
        self.assertNotIn("background", payload)
        self.assertNotIn("output_format", payload)
        self.assertEqual(generated["imageBytes"], image_bytes)
        self.assertEqual(generated["mimeType"], "image/png")
        self.assertEqual(generated["source"], "image2")

    def test_async_task_response_is_polled_and_downloaded(self) -> None:
        image_bytes = b"\x89PNG\r\n\x1a\n" + (b"async-portrait" * 200)
        submitted = _JsonResponse({
            "code": 200,
            "data": [{"status": "submitted", "task_id": "task-profile-705"}],
        })
        completed = _JsonResponse({
            "code": 200,
            "data": {
                "id": "task-profile-705",
                "status": "completed",
                "result": {"images": [{"url": ["https://image.example/result.png"]}]},
            },
        })
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tempdir:
            with (
                patch.object(portrait_service, "PORTRAIT_DIR", Path(tempdir)),
                patch.dict(
                    portrait_service.os.environ,
                    {
                        "SEEDREAM_BASE_URL": "https://image.example/v1",
                        "SEEDREAM_API_KEY": "test-key",
                    },
                    clear=False,
                ),
                patch.object(
                    portrait_service.urllib.request,
                    "urlopen",
                    side_effect=[submitted, completed, _BytesResponse(image_bytes)],
                ) as urlopen,
            ):
                generated = portrait_service.generate_profile_portrait({}, 705)

        self.assertEqual(urlopen.call_count, 3)
        status_request = urlopen.call_args_list[1].args[0]
        self.assertEqual(status_request.full_url, "https://image.example/v1/tasks/task-profile-705")
        self.assertEqual(generated["imageBytes"], image_bytes)

    def test_http_error_keeps_safe_relay_detail(self) -> None:
        error_body = json.dumps({"error": {"message": "background is required"}}).encode("utf-8")
        http_error = urllib.error.HTTPError(
            "https://image.example/v1/images/generations",
            400,
            "Bad Request",
            {},
            io.BytesIO(error_body),
        )
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tempdir:
            with (
                patch.object(portrait_service, "PORTRAIT_DIR", Path(tempdir)),
                patch.dict(
                    portrait_service.os.environ,
                    {"SEEDREAM_BASE_URL": "https://image.example/v1", "SEEDREAM_API_KEY": "test-key"},
                    clear=False,
                ),
                patch.object(
                    portrait_service.urllib.request,
                    "urlopen",
                    side_effect=http_error,
                ) as urlopen,
            ):
                with self.assertRaisesRegex(RuntimeError, "HTTP 400: background is required"):
                    portrait_service.generate_profile_portrait({}, 702)

        self.assertEqual(urlopen.call_count, 1)

    def test_retryable_relay_timeout_is_retried_once(self) -> None:
        image_bytes = b"\x89PNG\r\n\x1a\n" + (b"retry-success" * 200)
        timeout_error = urllib.error.HTTPError(
            "https://image.example/v1/images/generations",
            524,
            "Timeout",
            {},
            io.BytesIO(b""),
        )
        response = _JsonResponse({"data": [{"b64_json": base64.b64encode(image_bytes).decode("ascii")}]})
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tempdir:
            with (
                patch.object(portrait_service, "PORTRAIT_DIR", Path(tempdir)),
                patch.dict(
                    portrait_service.os.environ,
                    {
                        "SEEDREAM_BASE_URL": "https://image.example/v1",
                        "SEEDREAM_API_KEY": "test-key",
                        "IMAGE2_MAX_ATTEMPTS": "2",
                    },
                    clear=False,
                ),
                patch.object(
                    portrait_service.urllib.request,
                    "urlopen",
                    side_effect=[timeout_error, response],
                ) as urlopen,
                patch.object(portrait_service.time, "sleep") as sleep,
            ):
                generated = portrait_service.generate_profile_portrait({}, 704)

        self.assertEqual(generated["imageBytes"], image_bytes)
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once_with(1)

    def test_force_regeneration_bypasses_existing_file_cache(self) -> None:
        cached_bytes = b"\x89PNG\r\n\x1a\n" + (b"cached-portrait" * 200)
        fresh_bytes = b"\x89PNG\r\n\x1a\n" + (b"fresh-portrait" * 200)
        response = _JsonResponse({"data": [{"b64_json": base64.b64encode(fresh_bytes).decode("ascii")}]})
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tempdir:
            portrait_dir = Path(tempdir)
            (portrait_dir / "profile-703.png").write_bytes(cached_bytes)
            with (
                patch.object(portrait_service, "PORTRAIT_DIR", portrait_dir),
                patch.dict(
                    portrait_service.os.environ,
                    {"SEEDREAM_BASE_URL": "https://image.example/v1", "SEEDREAM_API_KEY": "test-key"},
                    clear=False,
                ),
                patch.object(portrait_service.urllib.request, "urlopen", return_value=response) as urlopen,
            ):
                generated = portrait_service.generate_profile_portrait({}, 703, force=True)

        self.assertEqual(urlopen.call_count, 1)
        self.assertEqual(generated["imageBytes"], fresh_bytes)


if __name__ == "__main__":
    unittest.main()
