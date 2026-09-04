"""Саморегистрация пользователей."""
from app.core.permissions import user_is_reports_only
from app.modules.reference.models import User


def test_register_creates_reports_viewer(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "email": "viewer@bsh-ru.ru",
            "full_name": "Тест Просмотр",
            "password": "Viewer123",
            "confirm_password": "Viewer123",
        },
    )
    assert resp.status_code == 200
    data = resp.json
    assert data["ok"] is True
    assert data["user"]["email"] == "viewer@bsh-ru.ru"
    assert "reports_viewer" in data["user"]["role_codes"]
    assert user_is_reports_only(data["user"])

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json["email"] == "viewer@bsh-ru.ru"


def test_register_duplicate_email(client):
    payload = {
        "email": "dup@bsh-ru.ru",
        "password": "Duppass12",
        "confirm_password": "Duppass12",
    }
    assert client.post("/api/auth/register", json=payload).status_code == 200
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 409
    assert resp.json["error"] == "duplicate_email"


def test_register_password_mismatch(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "email": "mismatch@bsh-ru.ru",
            "password": "Goodpass12",
            "confirm_password": "Otherpass12",
        },
    )
    assert resp.status_code == 400
    assert resp.json["error"] == "mismatch"


def test_register_policy(client):
    resp = client.get("/api/auth/register-policy")
    assert resp.status_code == 200
    assert resp.json["enabled"] is True
    assert resp.json["default_role"] == "reports_viewer"


def test_admin_cannot_create_user_via_api(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.post(
        "/api/admin/users",
        json={"email": "blocked@bsh-ru.ru", "role_codes": ["transport_logistics"]},
    )
    assert resp.status_code == 403
    assert resp.json["error"] == "registration_only"


def test_admin_can_promote_registered_user(auth_client, client, app):
    client.post(
        "/api/auth/register",
        json={
            "email": "promote@bsh-ru.ru",
            "password": "Promote123",
            "confirm_password": "Promote123",
        },
    )
    client.post("/api/auth/logout")

    auth_client("admin@test.local", "admin")
    with app.app_context():
        user = User.query.filter_by(email="promote@bsh-ru.ru").first()
        assert user is not None

    resp = client.put(
        f"/api/admin/users/{user.id}",
        json={"role_codes": ["transport_logistics"]},
    )
    assert resp.status_code == 200
    assert "transport_logistics" in resp.json["user"]["role_codes"]
