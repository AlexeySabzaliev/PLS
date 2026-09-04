"""Тесты восстановления пароля."""
from app.core.password_reset import (
    approve_password_reset,
    list_pending_password_resets,
    record_password_reset_request,
)
from app.modules.reference.models import PasswordResetRequest, User


def test_record_password_reset_request(app):
    with app.app_context():
        created, email = record_password_reset_request("admin@test.local", note="забыл")
        assert created is True
        assert email == "admin@test.local"
        row = PasswordResetRequest.query.filter_by(email="admin@test.local").first()
        assert row.status == "pending"
        created2, _ = record_password_reset_request("admin@test.local")
        assert created2 is True
        assert row.request_count == 2


def test_record_unknown_email(app):
    with app.app_context():
        created, _ = record_password_reset_request("nobody@test.local")
        assert created is False
        assert PasswordResetRequest.query.count() == 0


def test_password_reset_request_api(client, app):
    with app.app_context():
        record_password_reset_request("admin@test.local")
    resp = client.post(
        "/api/auth/password-reset/request",
        json={"email": "admin@test.local", "note": "help"},
    )
    assert resp.status_code == 200
    assert resp.json["ok"] is True


def test_approve_password_reset(auth_client, client, app):
    with app.app_context():
        record_password_reset_request("transport@test.local")
        row = PasswordResetRequest.query.filter_by(email="transport@test.local").first()
        rid = row.id
    auth_client("admin@test.local", "admin")
    resp = client.post(
        f"/api/admin/password-reset-requests/{rid}/approve",
        json={"password": "Newpass123"},
    )
    assert resp.status_code == 200
    client.post("/api/auth/logout")
    login = client.post("/api/auth/login", json={"email": "transport@test.local", "password": "Newpass123"})
    assert login.status_code == 200


def test_reopen_password_reset_after_approve(app):
    with app.app_context():
        record_password_reset_request("transport@test.local")
        row = PasswordResetRequest.query.filter_by(email="transport@test.local").first()
        admin = User.query.filter_by(email="admin@test.local").first()
        approve_password_reset(row.id, admin.id, new_password="Firstpass12")
        created, _ = record_password_reset_request("transport@test.local", note="снова")
        assert created is True
        row = PasswordResetRequest.query.filter_by(email="transport@test.local").first()
        assert row.status == "pending"
        assert row.request_count == 1


def test_admin_list_password_resets(auth_client, client, app):
    with app.app_context():
        record_password_reset_request("admin@test.local")
    auth_client("admin@test.local", "admin")
    resp = client.get("/api/admin/password-reset-requests")
    assert resp.status_code == 200
    assert resp.json["pending_count"] >= 1
