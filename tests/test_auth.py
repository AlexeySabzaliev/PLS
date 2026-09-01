"""Тесты SSO и прав."""
from app.core.permissions import user_has_uss_section
from app.core.sso import normalize_identity


def test_normalize_domain_login():
    email, local = normalize_identity("BSH\\ivanov")
    assert email.endswith("@bsh-ru.ru")
    assert local == "ivanov"


def test_normalize_email():
    email, local = normalize_identity("User@Example.COM")
    assert email == "user@example.com"
    assert local == "user"


def test_transport_has_uss_section():
    user = {"role_codes": ["transport_logistics"], "is_admin": False}
    assert user_has_uss_section(user, "uss_ops_transport")
    assert not user_has_uss_section(user, "uss_ops_warehouse")


def test_admin_has_all():
    user = {"role_codes": [], "is_admin": True}
    assert user_has_uss_section(user, "uss_billing")


def test_login_and_me(client, auth_client):
    auth_client("admin@test.local", "admin")
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json["email"] == "admin@test.local"
