"""Тесты заглушек разделов и dev-флагов."""
from __future__ import annotations

import importlib

from app.modules.uss.services import security_intranet


def test_uznt_stub_requires_auth(client):
    # Реальный раздел заявок: страница отрисовывается (API отдаёт 401 без входа).
    resp = client.get("/uznt/requests")
    assert resp.status_code == 200
    api = client.get("/api/uznt/requests")
    assert api.status_code == 401


def test_uznt_stub_for_transport(auth_client, client):
    auth_client("transport@test.local", "test")
    resp = client.get("/uznt/requests")
    assert resp.status_code == 200
    assert "заявки" in resp.get_data(as_text=True).lower()


def test_uss_reports_hub_admin(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.get("/uss/reports", follow_redirects=True)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Транспортная логистика" in html
    assert "Справочники" in html
    assert "ПЛС" in html and "УСС" in html
    assert "Ежесменные отчёты" not in html


def test_uss_home_nav(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.get("/uss/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "pls-brand-sep" in html
    assert "Отчёты" in html
    assert "На главную" not in html
    assert "Ежесменные отчёты" not in html
    assert "операционного учёта" in html.lower()
    assert "uss-intro-list" in html
    assert "uss-intro-item-name" in html
    # ссылки только в шапке, не в карточках главной
    intro = html.split('class="uss-intro-grid"', 1)[1].split("</section>", 1)[0]
    assert "<a " not in intro


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


def test_section_maintenance_blocks_only_affected_section(auth_client, client):
    # Админ ставит заглушку только на УЗнТ-раздел «заявки».
    auth_client("admin@test.local", "admin")
    r = client.post(
        "/api/maintenance",
        json={
            "target_type": "section",
            "target_key": "requests_transport",
            "message": "Техработы УЗнТ",
            "is_active": True,
        },
    )
    assert r.status_code == 200

    # Сотрудник с доступом: заявка на перевозку заблокирована (503)…
    auth_client("transport@test.local", "test")
    resp = client.get("/uznt/requests")
    assert resp.status_code == 503
    assert "Техработы УЗнТ" in resp.get_data(as_text=True)

    # …но транспорт УСС работает — блокируется только затронутая часть.
    resp2 = client.get("/uss/transport")
    assert resp2.status_code == 200


def test_section_maintenance_admin_bypass(auth_client, client):
    auth_client("admin@test.local", "admin")
    client.post(
        "/api/maintenance",
        json={
            "target_type": "section",
            "target_key": "requests_transport",
            "message": "Техработы УЗнТ",
            "is_active": True,
        },
    )
    # Админ заглушкой не блокируется.
    resp = client.get("/uznt/requests")
    assert resp.status_code == 200


def test_section_maintenance_deactivate_restores_access(auth_client, client):
    auth_client("admin@test.local", "admin")
    client.post(
        "/api/maintenance",
        json={
            "target_type": "section",
            "target_key": "requests_transport",
            "message": "Техработы",
            "is_active": True,
        },
    )
    client.post(
        "/api/maintenance",
        json={
            "target_type": "section",
            "target_key": "requests_transport",
            "message": "Техработы",
            "is_active": False,
        },
    )
    auth_client("transport@test.local", "test")
    resp = client.get("/uznt/requests")
    assert resp.status_code == 200


def test_role_maintenance_blocks_entry_for_role(auth_client, client):
    auth_client("admin@test.local", "admin")
    r = client.post(
        "/api/maintenance",
        json={
            "target_type": "role",
            "target_key": "transport_logistics",
            "message": "Роль на техобслуживании",
            "is_active": True,
        },
    )
    assert r.status_code == 200
    # Сотрудник этой роли блокируются на входе в портал.
    auth_client("transport@test.local", "test")
    resp = client.get("/uss/")
    assert resp.status_code == 503
    assert "Роль на техобслуживании" in resp.get_data(as_text=True)
    # Админ — нет.
    auth_client("admin@test.local", "admin")
    resp2 = client.get("/uss/")
    assert resp2.status_code == 200


def test_maintenance_catalog_admin(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.get("/api/maintenance/catalog")
    assert resp.status_code == 200
    payload = resp.json
    assert payload["modules"]
    assert payload["sections"]
    assert payload["roles"]
    keys = {s["key"] for s in payload["sections"]}
    assert {"uss_home", "requests_transport", "ref_clients"} <= keys
    # Не-админ не получает реестр.
    auth_client("transport@test.local", "test")
    resp2 = client.get("/api/maintenance/catalog")
    assert resp2.status_code == 403
