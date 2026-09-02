"""Тесты листа ожидания SSO."""
from app.core.auth import attempt_sso_login
from app.core.sso_access import approve_sso_request, list_pending_sso_requests, record_sso_access_request
from app.modules.reference.models import SsoAccessRequest, User


def test_record_sso_access_request(app):
    with app.app_context():
        row = record_sso_access_request(r"BSH\new.user")
        assert row.email.endswith("@bsh-ru.ru")
        assert row.status == "pending"
        row2 = record_sso_access_request(r"BSH\new.user")
        assert row2.id == row.id
        assert row2.login_attempts == 2


def test_approve_sso_creates_user(app):
    with app.app_context():
        row = record_sso_access_request(r"BSH\pending.user")
        result = approve_sso_request(row.id, admin_user_id=1)
        assert result["ok"] is True
        assert result["user_created"] is True
        user = User.query.filter_by(email=row.email).first()
        assert user is not None
        assert user.is_active is True


def test_record_sso_on_failed_login(app, monkeypatch):
    import app.core.sso as sso_mod

    monkeypatch.setattr(sso_mod.Config, "SSO_ENABLED", True)
    monkeypatch.setattr(sso_mod.Config, "SSO_DEV_IDENTITY", r"BSH\ghost.user")
    with app.app_context():
        user = attempt_sso_login({})
        assert user is None
        assert SsoAccessRequest.query.filter_by(status="pending").count() >= 1


def test_admin_list_sso_requests(auth_client, client):
    with client.application.app_context():
        record_sso_access_request(r"BSH\list.me")
    auth_client("admin@test.local", "admin")
    resp = client.get("/api/admin/sso-requests")
    assert resp.status_code == 200
    assert resp.json["pending_count"] >= 1
    assert any(x["email"].startswith("list.me@") for x in resp.json["items"])
