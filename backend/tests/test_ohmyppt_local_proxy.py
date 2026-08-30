from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("APP_SKIP_STARTUP_RECOVERY", "1")

app_module = importlib.import_module("app")


def test_local_ppt_generate_proxy_preserves_method_body_and_auth() -> None:
    upstream = Mock()
    upstream.status_code = 422
    upstream.content = b'{"detail":"validation error"}'
    upstream.headers = {"content-type": "application/json"}

    with patch.object(app_module.requests, "request", return_value=upstream) as request_mock:
        response = app_module.app.test_client().post(
            "/ppt-api/generate?trace=1",
            data=b'{"sessionId":"ppt-test"}',
            headers={
                "Authorization": "Bearer local-token",
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 422
    assert response.get_json() == {"detail": "validation error"}
    request_mock.assert_called_once()
    _, kwargs = request_mock.call_args
    assert request_mock.call_args.args == ("POST", "http://127.0.0.1:8765/api/generate")
    assert kwargs["params"].get("trace") == "1"
    assert kwargs["data"] == b'{"sessionId":"ppt-test"}'
    assert kwargs["headers"]["Authorization"] == "Bearer local-token"


def test_local_ppt_proxy_rejects_unknown_endpoint() -> None:
    response = app_module.app.test_client().get("/ppt-api/admin")
    assert response.status_code == 404
    assert response.get_json() == {"detail": "OhMyPPT endpoint not found"}
