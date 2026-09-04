"""Тесты аутентификации и прав."""
from app.core.permissions import user_has_uss_section, user_is_reports_only, user_can_edit
from app.core.passwords import validate_password


def test_validate_password_rules():
    ok, _ = validate_password("Secret12", email="user@bsh-ru.ru")
    assert ok


def test_transport_has_uss_section():
    user = {"role_codes": ["transport_logistics"], "is_admin": False}
    assert user_has_uss_section(user, "uss_ops_transport")
    assert not user_has_uss_section(user, "uss_ops_warehouse")


def test_reports_viewer_readonly():
    user = {"role_codes": ["reports_viewer"], "is_admin": False}
    assert user_has_uss_section(user, "uss_reports")
    assert user_is_reports_only(user)
    assert not user_can_edit(user)


def test_login_and_me(client, auth_client):
    auth_client("admin@test.local", "admin")
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json["email"] == "admin@test.local"
    assert "sso" not in resp.json
