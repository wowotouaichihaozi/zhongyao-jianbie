from __future__ import annotations

import argparse
import json
import time
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_xiaozhi_agent import PLATFORM_TOOLS, hermes_xiaozhi_runtime_status, run_xiaozhi_hermes_agent


DEFAULT_BACKEND_URL = "http://127.0.0.1:3000/api/health"
DEFAULT_FRONTEND_URL = "http://127.0.0.1:5088/"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_json(url: str, timeout: int = 10) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return {
            "status": response.status,
            "body": json.loads(response.read().decode("utf-8")),
        }


def fetch_text(url: str, timeout: int = 10) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept": "text/html"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        text = response.read().decode("utf-8", errors="replace")
        return {
            "status": response.status,
            "length": len(text),
            "hasSrcMain": "/src/main" in text,
        }


def run_check(args: argparse.Namespace, iteration: int) -> dict[str, Any]:
    record: dict[str, Any] = {
        "timestamp": utc_now(),
        "iteration": iteration,
        "ok": True,
        "checks": {},
        "errors": [],
    }

    try:
        runtime = hermes_xiaozhi_runtime_status()
        tools = runtime.get("tools") or []
        tool_types = [tool.get("type") for tool in tools]
        missing_labels = [tool.get("type") for tool in tools if not tool.get("label")]
        record["checks"]["hermesRuntime"] = {
            "runtime": runtime.get("runtime"),
            "source": runtime.get("source"),
            "provider": runtime.get("provider"),
            "model": runtime.get("model"),
            "hasToken": bool(runtime.get("hasToken")),
            "toolCount": len(tools),
            "toolTypes": tool_types,
            "missingLabels": missing_labels,
        }
        assert runtime.get("runtime") == "hermes-agent"
        assert runtime.get("provider") == "mimo"
        assert runtime.get("model") == "xsparkx2agent"
        assert len(tools) == len(PLATFORM_TOOLS)
        assert set(tool_types) == set(PLATFORM_TOOLS)
        assert not missing_labels
    except Exception as exc:
        record["ok"] = False
        record["errors"].append({"check": "hermesRuntime", "error": str(exc)})

    try:
        import app

        route_types = set(app.XIAOZHI_RESOURCE_ROUTES)
        label_types = set(app.XIAOZHI_RESOURCE_LABELS)
        record["checks"]["appRegistry"] = {
            "routeCount": len(route_types),
            "labelCount": len(label_types),
            "routeTypes": sorted(route_types),
        }
        assert route_types == set(PLATFORM_TOOLS)
        assert label_types == set(PLATFORM_TOOLS)
    except Exception as exc:
        record["ok"] = False
        record["errors"].append({"check": "appRegistry", "error": str(exc)})

    try:
        record["checks"]["taskDetailEndpoint"] = verify_task_detail_endpoint()
    except Exception as exc:
        record["ok"] = False
        record["errors"].append({"check": "taskDetailEndpoint", "error": str(exc)})

    try:
        record["checks"]["platformDispatch"] = verify_platform_dispatch()
    except Exception as exc:
        record["ok"] = False
        record["errors"].append({"check": "platformDispatch", "error": str(exc)})

    try:
        record["checks"]["backendHealth"] = fetch_json(args.backend_url)
        assert record["checks"]["backendHealth"]["status"] == 200
        assert record["checks"]["backendHealth"]["body"].get("ok") is True
    except Exception as exc:
        record["ok"] = False
        record["errors"].append({"check": "backendHealth", "error": str(exc)})

    try:
        record["checks"]["frontend"] = fetch_text(args.frontend_url)
        assert record["checks"]["frontend"]["status"] == 200
        assert record["checks"]["frontend"]["hasSrcMain"] is True
    except Exception as exc:
        record["ok"] = False
        record["errors"].append({"check": "frontend", "error": str(exc)})

    try:
        record["checks"]["frontendCardFlow"] = verify_frontend_card_flow()
    except Exception as exc:
        record["ok"] = False
        record["errors"].append({"check": "frontendCardFlow", "error": str(exc)})

    if args.live_mimo_on_start and iteration == 1:
        try:
            live = run_xiaozhi_hermes_agent(
                "\u8bf7\u4e3a\u6211\u751f\u6210 STM32 GPIO \u5b66\u4e60\u8def\u5f84",
                {"profile": {"level": "beginner"}, "mcuExperiments": [], "questionSheets": [], "examResults": []},
            )
            record["checks"]["liveMimoHermes"] = {
                "intent": live.get("intent"),
                "resourceType": live.get("resourceType"),
                "runtime": live.get("runtime"),
                "provider": live.get("provider"),
                "model": live.get("model"),
                "source": live.get("source"),
            }
            assert live.get("intent") == "generate_resource"
            assert live.get("resourceType") == "learning_path"
            assert live.get("runtime") == "hermes-agent"
            assert live.get("provider") == "mimo"
            assert live.get("model") == "xsparkx2agent"
        except Exception as exc:
            record["ok"] = False
            record["errors"].append({"check": "liveMimoHermes", "error": str(exc)})

    return record


def verify_task_detail_endpoint() -> dict[str, Any]:
    import app

    suffix = f"{int(time.time() * 1000)}_{iteration_safe_counter()}"
    username = f"soak_xz_{suffix}"
    other_username = f"soak_xz_other_{suffix}"
    task_id = f"xz_soak_{suffix}"
    created_ids: list[int] = []
    token = ""
    other_token = ""
    with app.app.test_request_context("/hermes-soak-session", headers={"User-Agent": "Hermes XiaoZhi Soak"}):
        with app.auth_db() as conn:
            timestamp = app.utc_timestamp()
            for name in [username, other_username]:
                conn.execute(
                    """
                    INSERT INTO users (username, email, display_name, password_hash, role, avatar_url, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 'user', ?, ?, ?)
                    """,
                    (
                        name,
                        f"{name}@example.test",
                        "Hermes Soak User",
                        app.password_hash("HermesSoak123!"),
                        app.DEFAULT_AVATAR,
                        timestamp,
                        timestamp,
                    ),
                )
                row = conn.execute("SELECT * FROM users WHERE username = ?", (name,)).fetchone()
                created_ids.append(int(row["id"]))
            token = app.create_session(conn, created_ids[0])
            other_token = app.create_session(conn, created_ids[1])
            conn.execute(
                """
                INSERT INTO xiaozhi_tasks (task_id, user_id, task_type, title, prompt, status, route, result_json, error, created_at, updated_at)
                VALUES (?, ?, 'ppt', 'UART · PPT 生成智能体', 'UART PPT', 'complete', '/personalized-resources/ppt', ?, '', ?, ?)
                """,
                (
                    task_id,
                    created_ids[0],
                    json.dumps({"message": "PPT 生成智能体已完成 H5 课件。", "topic": "UART"}, ensure_ascii=False),
                    timestamp,
                    timestamp,
                ),
            )

    try:
        client = app.app.test_client()
        owned = client.get(f"/api/xiaozhi/tasks/{task_id}", headers={"Authorization": f"Bearer {token}"})
        foreign = client.get(f"/api/xiaozhi/tasks/{task_id}", headers={"Authorization": f"Bearer {other_token}"})
        missing = client.get("/api/xiaozhi/tasks/no_such_task", headers={"Authorization": f"Bearer {token}"})
        owned_json = owned.get_json() or {}
        assert owned.status_code == 200
        assert owned_json.get("data", {}).get("task", {}).get("taskId") == task_id
        assert owned_json.get("data", {}).get("task", {}).get("result", {}).get("topic") == "UART"
        assert foreign.status_code == 404
        assert missing.status_code == 404
        return {
            "ownedStatus": owned.status_code,
            "foreignStatus": foreign.status_code,
            "missingStatus": missing.status_code,
            "taskType": owned_json.get("data", {}).get("task", {}).get("taskType"),
            "taskStatus": owned_json.get("data", {}).get("task", {}).get("status"),
        }
    finally:
        with app.auth_db() as conn:
            for user_id in created_ids:
                conn.execute("DELETE FROM xiaozhi_tasks WHERE user_id = ?", (user_id,))
                conn.execute("DELETE FROM xiaozhi_messages WHERE user_id = ?", (user_id,))
                conn.execute("DELETE FROM xiaozhi_events WHERE user_id = ?", (user_id,))
                conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
                conn.execute("DELETE FROM users WHERE id = ?", (user_id,))


def verify_platform_dispatch() -> dict[str, Any]:
    import app

    original = {
        "xiaozhi_insert_event": app.xiaozhi_insert_event,
        "auth_db": app.auth_db,
        "generate_profile_report": app.generate_profile_report,
        "generate_background_chat": app.generate_background_chat,
        "generate_learning_path": app.generate_learning_path,
        "generate_learning_path_stage_detail": app.generate_learning_path_stage_detail,
        "generate_personalized_resources": app.generate_personalized_resources,
        "generate_question_bank": app.generate_question_bank,
        "save_question_sheet": app.save_question_sheet,
        "generate_ppt_h5": app.generate_ppt_h5,
        "start_interview_session": app.start_interview_session,
        "generate_resource_workflow": app.generate_resource_workflow,
    }

    class Cursor:
        lastrowid = 101

    class FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, *args, **kwargs):
            return Cursor()

    try:
        app.xiaozhi_insert_event = lambda *args, **kwargs: None
        app.auth_db = lambda: FakeConn()
        app.generate_profile_report = lambda payload: {"source": "llm", "summary": "profile ok"}
        app.generate_background_chat = lambda payload: {"reply": "background ok"}
        app.generate_learning_path = lambda payload: {"phases": [{"id": "s1", "title": "stage"}]}
        app.generate_learning_path_stage_detail = lambda payload: {"stage": payload.get("stage"), "useLLM": payload.get("useLLM"), "tasks": []}
        app.generate_personalized_resources = lambda payload: {
            "agent": "personalized-resource-workflow",
            "source": "llm",
            "resources": [{"type": "ppt", "title": "llm"}],
        }
        app.generate_question_bank = lambda payload: {"question_bank": {"title": payload["target_topic"], "questions": []}}
        app.save_question_sheet = lambda question_bank: {"id": 22, "title": question_bank.get("title")}
        app.generate_ppt_h5 = lambda payload: {"slides": [{"title": payload.get("topic")}]}
        app.start_interview_session = lambda user_id, payload: {"sessionId": "iv-1", "topic": payload.get("topic")}
        app.generate_resource_workflow = lambda payload, mcu_experiments=None: {
            "resources": [{"type": "mindmap"}, {"type": "video"}, {"type": "simulator"}]
        }

        context = {
            "profile": {"aiAnalysis": {"level": "beginner"}},
            "questionnaire": {},
            "mcuExperiments": [],
            "questionSheets": [],
            "examResults": [],
        }
        dispatch: dict[str, list[str]] = {}
        for tool_type in sorted(app.XIAOZHI_RESOURCE_ROUTES):
            result = app.xiaozhi_run_platform_agent(tool_type, "STM32 GPIO", context, 1)
            assert result["resourceType"] == tool_type
            assert result["runtime"] == "hermes-agent"
            assert result["route"] == app.XIAOZHI_RESOURCE_ROUTES[tool_type]
            assert result.get("message")
            if tool_type == "learning_path_stage":
                assert result["stageDetail"]["useLLM"] is True
            if tool_type == "personalized_resources":
                assert result["llmResources"]["source"] == "llm"
                assert result["workflow"]["resources"]
            dispatch[tool_type] = sorted(result.keys())
        return {"dispatchCount": len(dispatch), "toolTypes": sorted(dispatch), "personalizedKeys": dispatch.get("personalized_resources", [])}
    finally:
        for name, value in original.items():
            setattr(app, name, value)


def verify_frontend_card_flow() -> dict[str, Any]:
    project_root = Path(__file__).resolve().parents[1]
    launcher_path = project_root / "frontend" / "src" / "components" / "FloatingLogoLauncher.vue"
    banner_path = project_root / "frontend" / "src" / "components" / "ResourceTaskStatusBanner.vue"
    api_path = project_root / "frontend" / "src" / "services" / "api.js"

    launcher = launcher_path.read_text(encoding="utf-8")
    banner = banner_path.read_text(encoding="utf-8")
    api = api_path.read_text(encoding="utf-8")

    required_launcher_tokens = [
        ':href="resolveRouteHref(card.route)"',
        'target="_blank"',
        'rel="noopener noreferrer"',
        '@click.prevent="goToCard(card)"',
        '@click.prevent="goToTask(task)"',
        "window.open('about:blank', '_blank')",
        "opened.location.replace(href)",
        "new URL(router.resolve(routeTarget).href, window.location.origin).href",
    ]
    missing_launcher_tokens = [token for token in required_launcher_tokens if token not in launcher]
    assert not missing_launcher_tokens, missing_launcher_tokens

    assert "getXiaoZhiTask(taskId.value)" in banner
    assert "getXiaoZhiStatus" in banner
    assert "/api/xiaozhi/tasks/" in api

    return {
        "launcherPath": str(launcher_path.relative_to(project_root)),
        "bannerPath": str(banner_path.relative_to(project_root)),
        "apiPath": str(api_path.relative_to(project_root)),
        "cardHref": True,
        "cardTargetBlank": True,
        "taskDetailApi": True,
        "popupOpen": True,
    }


_COUNTER = 0


def iteration_safe_counter() -> int:
    global _COUNTER
    _COUNTER += 1
    return _COUNTER


def append_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run long-lived XiaoZhi Hermes verification checks.")
    parser.add_argument("--duration-seconds", type=int, default=5 * 60 * 60)
    parser.add_argument("--interval-seconds", type=int, default=5 * 60)
    parser.add_argument("--backend-url", default=DEFAULT_BACKEND_URL)
    parser.add_argument("--frontend-url", default=DEFAULT_FRONTEND_URL)
    parser.add_argument("--log", default=str(Path("data") / "hermes_xiaozhi_soak.jsonl"))
    parser.add_argument("--live-mimo-on-start", action="store_true")
    args = parser.parse_args()

    log_path = Path(args.log)
    started = time.monotonic()
    iteration = 0
    exit_code = 0
    while True:
        iteration += 1
        record = run_check(args, iteration)
        append_record(log_path, record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
        if not record["ok"]:
            exit_code = 1
        elapsed = time.monotonic() - started
        if elapsed >= args.duration_seconds:
            break
        time.sleep(min(args.interval_seconds, max(0, args.duration_seconds - elapsed)))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
