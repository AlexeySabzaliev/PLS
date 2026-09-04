"""Пароли: политика, смена, админ."""
from app.core.auth import change_user_password, hash_password, login_user_password, set_user_password
from app.core.passwords import validate_password
from app.modules.reference.models import User


def test_password_policy(client):
    resp = client.get("/api/auth/password-policy")
    assert resp.status_code == 200
    assert resp.json["min_length"] >= 6


def test_validate_password_rules():
    ok, _ = validate_password("short1")
    assert not ok
    ok, _ = validate_password("nodigits")
    assert not ok
    ok, _ = validate_password("12345678")
    assert not ok
    ok, _ = validate_password("Secret12", email="user@bsh-ru.ru")
    assert ok


def test_change_password(auth_client, client, app):
    auth_client("admin@test.local", "admin")
    resp = client.post(
        "/api/auth/change-password",
        json={
            "current_password": "admin",
            "new_password": "Admin1234",
            "confirm_password": "Admin1234",
        },
    )
    assert resp.status_code == 200
    client.post("/api/auth/logout")
    ok, _ = login_user_password("admin@test.local", "Admin1234")
    assert ok is not None
    with app.app_context():
        user = User.query.filter_by(email="admin@test.local").first()
        user.password_hash = hash_password("admin")
        from app.db import db
        db.session.commit()


def test_change_password_wrong_current(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.post(
        "/api/auth/change-password",
        json={
            "current_password": "wrong",
            "new_password": "Admin1234",
            "confirm_password": "Admin1234",
        },
    )
    assert resp.status_code == 400
    assert resp.json["error"] == "invalid_current"


def test_set_password_first_time(app, client):
    with app.app_context():
        user = User(email="nopw@test.local", full_name="No PW", is_active=True)
        from app.db import db
        db.session.add(user)
        db.session.commit()
        uid = user.id
    login_resp = client.post("/api/auth/login", json={"email": "nopw@test.local", "password": "x"})
    assert login_resp.status_code == 401
    assert login_resp.json["error"] == "no_password"

    with client.session_transaction() as sess:
        sess["user_id"] = uid
    resp = client.post(
        "/api/auth/change-password",
        json={"new_password": "First1234", "confirm_password": "First1234"},
    )
    assert resp.status_code == 200
    client.post("/api/auth/logout")
    login2 = client.post("/api/auth/login", json={"email": "nopw@test.local", "password": "First1234"})
    assert login2.status_code == 200


def test_admin_set_user_password(auth_client, client, app):
    client.post(
        "/api/auth/register",
        json={
            "email": "pw.user@bsh-ru.ru",
            "full_name": "PW User",
            "password": "User1234",
            "confirm_password": "User1234",
        },
    )
    client.post("/api/auth/logout")
    with app.app_context():
        from app.modules.reference.models import User

        user = User.query.filter_by(email="pw.user@bsh-ru.ru").first()
        assert user is not None

    auth_client("admin@test.local", "admin")
    resp = client.post(
        f"/api/admin/users/{user.id}/password",
        json={"password": "AdminSet99"},
    )
    assert resp.status_code == 200
    client.post("/api/auth/logout")
    login = client.post("/api/auth/login", json={"email": "pw.user@bsh-ru.ru", "password": "AdminSet99"})
    assert login.status_code == 200


def test_profile_page(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.get("/profile")
    assert resp.status_code == 200
    assert "Профиль" in resp.get_data(as_text=True)
