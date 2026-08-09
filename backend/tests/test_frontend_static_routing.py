from backend.app import FRONTEND_DIST_DIR, app


def test_ppt_root_serves_ohmyppt_app():
    response = app.test_client().get("/ppt/")

    assert response.status_code == 200
    assert b"<title>OhMyPPT</title>" in response.data
    assert "嵌智学航".encode() not in response.data


def test_ppt_asset_is_served_directly():
    asset = next((FRONTEND_DIST_DIR / "ppt" / "assets").glob("*.js"))
    response = app.test_client().get(f"/ppt/assets/{asset.name}")

    assert response.status_code == 200
    assert len(response.data) == asset.stat().st_size


def test_ppt_client_route_serves_ohmyppt_app():
    response = app.test_client().get("/ppt/editor/test-session")

    assert response.status_code == 200
    assert b"<title>OhMyPPT</title>" in response.data


def test_missing_ppt_asset_returns_404():
    response = app.test_client().get("/ppt/assets/not-built.js")

    assert response.status_code == 404
    assert response.is_json


def test_main_ppt_workbench_route_stays_in_main_app():
    response = app.test_client().get("/personalized-resources/ppt")

    assert response.status_code == 200
    assert "<title>嵌智学航</title>".encode() in response.data
    assert b"<title>OhMyPPT</title>" not in response.data
