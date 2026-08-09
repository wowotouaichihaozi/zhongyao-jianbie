from pathlib import Path

from api_config import setting_default


def test_default_admin_credentials_are_consistent() -> None:
    assert setting_default("ADMIN_USERNAME") == "admin123"
    assert setting_default("ADMIN_PASSWORD") == "admin123"


def test_admin_login_ui_uses_the_deployable_default_credentials() -> None:
    project_root = Path(__file__).resolve().parents[2]
    login_source = (project_root / "admin/src/views/_builtin/login/modules/pwd-login.vue").read_text(
        encoding="utf-8"
    )
    toggle_source = (project_root / "admin/src/views/function/toggle-auth/index.vue").read_text(
        encoding="utf-8"
    )
    route_guard_source = (project_root / "admin/src/router/guard/route.ts").read_text(encoding="utf-8")

    for source in (login_source, toggle_source):
        assert "userName: 'admin123'" in source
        assert "password: 'admin123'" in source
        assert "password: '123456'" not in source

    assert "getMainAdminLoginUrl" not in route_guard_source
    assert "window.location.origin}/login" not in route_guard_source
