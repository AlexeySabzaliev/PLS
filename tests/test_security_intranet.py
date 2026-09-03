"""Интеграция с порталом охраны."""


def test_demo_security_plate_detection():
    from app.modules.uss.services.security_intranet import (
        is_demo_security_plate,
        is_mock_security_request_id,
    )

    assert is_demo_security_plate("А000АА03")
    assert is_demo_security_plate("В111ВВ03")
    assert not is_demo_security_plate("К582ВЕ147")
    assert is_mock_security_request_id("mock-ariston-0309-1")


def test_sync_security_unauthorized_without_stub(auth_client, client, monkeypatch):
    """Без заглушки и без cookie — не подставлять демо-ТС."""
    import app.modules.uss.services.security_intranet as sec

    monkeypatch.delenv("SECURITY_PORTAL_STUB", raising=False)
    monkeypatch.delenv("SECURITY_USE_MOCK", raising=False)
    monkeypatch.setenv("SECURITY_AUTO_BROWSER_COOKIES", "0")
    monkeypatch.setattr(sec, "SECURITY_USE_LOCAL_DB", False)
    monkeypatch.setattr(sec, "SECURITY_LOCAL_FALLBACK", False)
    monkeypatch.setattr(sec, "get_authenticated_session", lambda *a, **k: None)
    auth_client("transport@test.local", "test")
    resp = client.post(
        "/api/uss/transport/sync-security",
        json={"warehouse_id": 1, "date": "2026-08-06"},
    )
    assert resp.status_code == 200
    data = resp.json
    assert data["synced"] == 0
    assert data.get("source", "") in ("no_auth", "unauthorized")
    assert data.get("message")


def test_shift_hides_demo_security_vehicles_without_stub(auth_client, client, app, monkeypatch):
    """Демо-ТС из заглушки не показываются, если SECURITY_PORTAL_STUB выключен."""
    monkeypatch.delenv("SECURITY_PORTAL_STUB", raising=False)
    monkeypatch.delenv("SECURITY_USE_MOCK", raising=False)

    with app.app_context():
        from datetime import date

        from app.db import db
        from app.modules.uss.models import VehicleOperation

        db.session.add(
            VehicleOperation(
                contract_id=1,
                warehouse_id=1,
                operation_date=date(2026, 9, 3),
                tractor_plate="А000АА03",
                plate_number="А000АА03",
                operation_type_code="inbound",
                source="security",
                security_request_id="mock-test-0309-1",
            )
        )
        db.session.commit()

    auth_client("transport@test.local", "test")
    resp = client.get("/api/uss/transport/shift?warehouse_id=1&date=2026-09-03")
    assert resp.status_code == 200
    plates = [v.get("tractor_plate") for v in resp.json["vehicles"]]
    assert "А000АА03" not in plates


def test_sync_purges_demo_security_vehicles_without_stub(auth_client, client, app, monkeypatch):
    monkeypatch.delenv("SECURITY_PORTAL_STUB", raising=False)
    monkeypatch.delenv("SECURITY_USE_MOCK", raising=False)
    monkeypatch.setenv("SECURITY_AUTO_BROWSER_COOKIES", "0")
    import app.modules.uss.services.security_intranet as sec

    monkeypatch.setattr(sec, "SECURITY_USE_LOCAL_DB", False)
    monkeypatch.setattr(sec, "SECURITY_LOCAL_FALLBACK", False)
    monkeypatch.setattr(sec, "get_authenticated_session", lambda *a, **k: None)

    with app.app_context():
        from datetime import date

        from app.db import db
        from app.modules.uss.models import VehicleOperation

        db.session.add(
            VehicleOperation(
                contract_id=1,
                warehouse_id=1,
                operation_date=date(2026, 9, 3),
                tractor_plate="В111ВВ03",
                plate_number="В111ВВ03",
                operation_type_code="inbound",
                source="security",
                security_request_id="mock-test-0309-2",
            )
        )
        db.session.commit()

    auth_client("transport@test.local", "test")
    resp = client.post(
        "/api/uss/transport/sync-security",
        json={"warehouse_id": 1, "date": "2026-09-03"},
    )
    assert resp.status_code == 200
    assert resp.json.get("purged_demo", 0) >= 1

    resp2 = client.get("/api/uss/transport/shift?warehouse_id=1&date=2026-09-03")
    plates = [v.get("tractor_plate") for v in resp2.json["vehicles"]]
    assert "В111ВВ03" not in plates


def test_sync_security_portal_stub(auth_client, client, monkeypatch):
    monkeypatch.setenv("SECURITY_PORTAL_STUB", "1")
    auth_client("transport@test.local", "test")
    resp = client.post(
        "/api/uss/transport/sync-security",
        json={"warehouse_id": 1, "date": "2026-08-06"},
    )
    assert resp.status_code == 200
    data = resp.json
    assert data["synced"] >= 2
    assert data["security"]["stub"] is True
    assert data.get("message")


def test_shift_includes_security_status(auth_client, client):
    auth_client("transport@test.local", "test")
    resp = client.get("/api/uss/transport/shift?warehouse_id=1&date=2026-08-01")
    assert resp.status_code == 200
    assert "security" in resp.json
    assert "security_visit_place" in resp.json


def test_live_api_params_review_scope():
    from datetime import date

    import app.modules.uss.services.security_intranet as sec

    params = sec._live_api_params("Склад ГП", date.today())
    assert params["scope"] == "review"
    assert params["approved"] == "approved"
    assert params["today"] == "1"
    assert params["visitPlace"] == "Склад ГП"


def test_resolve_security_cookie_rejects_bare_jwt(monkeypatch):
    import app.modules.uss.services.security_intranet as sec

    monkeypatch.setenv("SECURITY_API_COOKIE", "eyJ1c2Vy.test.signature")
    assert sec._resolve_security_cookie() == ""


def test_sync_security_after_oub_like_client(auth_client, client, app, monkeypatch):
    """E2E: клиент/склад как после import-from-billings — синх «С охраны» создаёт ТС."""
    monkeypatch.setenv("SECURITY_PORTAL_STUB", "1")
    with app.app_context():
        from app.db import db
        from app.modules.reference.models import Client, Contract, Warehouse

        wh = Warehouse.query.filter_by(code="spb1").first()
        assert wh is not None
        wh.security_visit_place = wh.security_visit_place or "Склад ГП"
        client_row = Client.query.first()
        assert client_row is not None
        client_row.name = 'ООО "Аристон Термо Рус"'
        contract = Contract.query.filter_by(warehouse_id=wh.id).first()
        assert contract is not None
        db.session.commit()
        wh_id = wh.id

    auth_client("transport@test.local", "test")
    resp = client.post(
        "/api/uss/transport/sync-security",
        json={"warehouse_id": wh_id, "date": "2026-08-06"},
    )
    assert resp.status_code == 200
    data = resp.json
    assert data["synced"] >= 2
    assert data["security"]["stub"] is True
    assert any(d.get("fetched", 0) >= 1 for d in data.get("details", []))
