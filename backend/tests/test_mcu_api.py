from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from backend import app as app_module
from backend.database_schema import init_auth_schema


@pytest.fixture()
def mcu_client():
    tempdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    original_db_path = app_module.AUTH_DB_PATH
    app_module.AUTH_DB_PATH = Path(tempdir.name) / "mcu-api.sqlite3"
    app_module.app.config.update(TESTING=True)
    now = "2026-07-15T10:00:00+08:00"
    with app_module.auth_db() as conn:
        init_auth_schema(conn)
        conn.execute(
            """
            INSERT INTO users
                (id, username, display_name, password_hash, role, avatar_url, created_at, updated_at)
            VALUES (401, 'mcu-user', 'MCU User', ?, 'user', '/userlogo.png', ?, ?)
            """,
            (app_module.password_hash("password-1"), now, now),
        )
        cursor = conn.execute(
            """
            INSERT INTO learning_profile_reports
                (user_id, report_json, profile_name, version, created_at, updated_at, archived)
            VALUES (?, ?, '单片机学习画像', 1, ?, ?, 0)
            """,
            (
                401,
                json.dumps(
                    {
                        "learningGoals": ["掌握 PWM、GPIO 与 ADC"],
                        "weakPoints": ["PWM 占空比"],
                        "resourcePreferences": ["动手实验"],
                    },
                    ensure_ascii=False,
                ),
                now,
                now,
            ),
        )
        report_id = int(cursor.lastrowid)
        conn.execute(
            """
            INSERT INTO user_learning_profile_state
                (user_id, active_report_id, generation, reset_at, created_at, updated_at)
            VALUES (401, ?, 0, '', ?, ?)
            """,
            (report_id, now, now),
        )
        with app_module.app.test_request_context(
            "/api/mcu/catalog",
            headers={"User-Agent": "mcu-api-test"},
        ):
            token = app_module.create_session(conn, 401)

    try:
        yield app_module.app.test_client(), {"Authorization": f"Bearer {token}"}
    finally:
        app_module.AUTH_DB_PATH = original_db_path
        tempdir.cleanup()


def test_mcu_endpoints_require_authentication(mcu_client):
    client, _headers = mcu_client

    assert client.get("/api/mcu/catalog").status_code == 401
    assert client.post("/api/mcu/recommendations", json={}).status_code == 401
    assert client.post("/api/mcu/flash", json={}).status_code == 401
    assert client.post("/api/mcu/save-experiment", json={}).status_code == 401


def test_catalog_and_profile_recommendation_api(mcu_client):
    client, headers = mcu_client

    catalog_response = client.get("/api/mcu/catalog", headers=headers)
    recommendation_response = client.post(
        "/api/mcu/recommendations",
        headers=headers,
        json={"board": "arduino", "limit": 4},
    )

    assert catalog_response.status_code == 200
    catalog = catalog_response.get_json()["data"]
    assert catalog["counts"] == {"boards": 2, "components": 17, "experiments": 21}
    assert recommendation_response.status_code == 200
    recommendation_data = recommendation_response.get_json()["data"]
    assert recommendation_data["profileBound"] is True
    assert recommendation_data["recommendations"][0]["id"] == "uno-pwm-fade"
    assert all(item["board"] == "arduino" for item in recommendation_data["recommendations"])


def test_agent_auto_recommendation_uses_history_but_preserves_explicit_project(mcu_client):
    _client, _headers = mcu_client
    with app_module.auth_db() as conn:
        conn.execute(
            """
            INSERT INTO mcu_experiments
                (user_id, experiment_id, experiment_name, passed, weak_points, run_data, created_at)
            VALUES (401, 'uno-pwm-fade', 'PWM 呼吸灯', 1, '[]', '{}', '2026-07-15T10:02:00+08:00')
            """
        )

    automatic = app_module.resolve_mcu_agent_params_for_user(
        401,
        {"board": "arduino", "topic": "PWM 呼吸灯", "autoRecommend": True},
        "PWM 占空比实验",
    )
    explicit = app_module.resolve_mcu_agent_params_for_user(
        401,
        {"board": "arduino", "projectId": "uno-pwm-fade", "topic": "PWM 呼吸灯"},
        "打开指定实验",
    )

    assert automatic["board"] == "arduino"
    assert automatic["projectId"] != "uno-pwm-fade"
    assert automatic["recommendationSource"] == "profile-history"
    assert automatic["historyCount"] == 1
    assert automatic["recommendationResolved"] is True
    assert explicit["projectId"] == "uno-pwm-fade"
    assert explicit["autoRecommend"] is False


def test_flash_api_accepts_preset_and_rejects_invalid_pwm_pin(mcu_client):
    client, headers = mcu_client

    valid = client.post("/api/mcu/flash", headers=headers, json={"projectId": "uno-led-ready"})
    invalid = client.post(
        "/api/mcu/flash",
        headers=headers,
        json={
            "board": "arduino",
            "code": "void setup() { pinMode(2, OUTPUT); }\nvoid loop() { analogWrite(2, 128); }",
            "parts": [],
        },
    )

    assert valid.status_code == 200
    assert valid.get_json()["data"]["firmware"]["status"] == "ready"
    assert invalid.status_code == 422
    assert invalid.get_json()["data"]["firmware"]["status"] == "rejected"


def test_experiment_save_preserves_json_and_rejects_oversized_payload(mcu_client):
    client, headers = mcu_client

    saved = client.post(
        "/api/mcu/save-experiment",
        headers=headers,
        json={
            "experiment_id": "uno-led-ready",
            "passed": True,
            "run_data": {"firmwareId": "fw_test", "diagnostics": {"errors": [], "warnings": []}},
        },
    )
    oversized = client.post(
        "/api/mcu/save-experiment",
        headers=headers,
        json={
            "experiment_id": "uno-led-ready",
            "passed": True,
            "run_data": {"trace": "x" * 20_001},
        },
    )
    history = client.get("/api/mcu/experiments", headers=headers)

    assert saved.status_code == 200
    assert oversized.status_code == 413
    assert history.status_code == 200
    assert history.get_json()["data"][0]["run_data"]["firmwareId"] == "fw_test"


def test_history_tolerates_legacy_truncated_json(mcu_client):
    client, headers = mcu_client
    with app_module.auth_db() as conn:
        conn.execute(
            """
            INSERT INTO mcu_experiments
                (user_id, experiment_id, experiment_name, passed, weak_points, run_data, created_at)
            VALUES (401, 'uno-led-ready', 'legacy', 0, '[', '{\"truncated\":', '2026-07-15T10:01:00+08:00')
            """
        )

    history = client.get("/api/mcu/experiments?limit=1", headers=headers)

    assert history.status_code == 200
    item = history.get_json()["data"][0]
    assert item["weak_points"] == []
    assert item["run_data"] == {}
