"""Тесты заглушек разделов и dev-флагов."""
from __future__ import annotations

import importlib

from app.modules.uss.services import security_intranet


def test_uznt_stub_requires_auth(client):
    resp = client.get("/uznt/requests")
    assert resp.status_code == 302
    assert "/" in resp.headers.get("Location", "")


def test_uznt_stub_for_transport(auth_client, client):
    auth_client("transport@test.local", "test")
    resp = client.get("/uznt/requests")
    assert resp.status_code == 200
    assert "заявки" in resp.get_data(as_text=True).lower()


def test_uss_reports_hub_admin(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.get("/uss/reports")
    assert resp.status_code == 200
    assert "отчёты" in resp.get_data(as_text=True).lower()
    assert "ФОТ" in resp.get_data(as_text=True)


def test_security_portal_stub_alias(monkeypatch):
    monkeypatch.delenv("SECURITY_USE_MOCK", raising=False)
    monkeypatch.setenv("SECURITY_PORTAL_STUB", "1")
    importlib.reload(security_intranet)
    try:
        assert security_intranet._use_mock() is True
    finally:
        importlib.reload(security_intranet)


def test_pls_sso_stub_config(monkeypatch):
    monkeypatch.setenv("PLS_SSO_STUB", "1")
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("SSO_DEV_IDENTITY", raising=False)
    cfg = importlib.import_module("app.config")
    importlib.reload(cfg)
    try:
        assert cfg.Config.SSO_ENABLED is True
        assert cfg.Config.SSO_DEV_IDENTITY
    finally:
        monkeypatch.delenv("PLS_SSO_STUB", raising=False)
        importlib.reload(cfg)


def test_maintenance_api(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.post(
        "/api/maintenance",
        json={
            "target_type": "section",
            "target_key": "billing",
            "message": "Техработы",
            "is_active": True,
        },
    )
    assert resp.status_code == 200
    auth_client("transport@test.local", "test")
    resp2 = client.get("/api/auth/me")
    assert resp2.status_code == 200
    assert resp2.json["maintenance"]["sections"].get("billing") == "Техработы"
