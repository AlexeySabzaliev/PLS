"""Тесты CRUD УЗнТ «заявки на перевозку» (/api/uznt/requests)."""
import pytest

from app.core.auth import hash_password
from app.db import db
from app.modules.reference.models import Role, User, UserRole


def _make_warehouse_user(client):
    """Пользователь без доступа к разделу заявок УЗнТ (только склад УСС)."""
    role = Role.query.filter_by(code="warehouse_logistics").first()
    user = User(
        email="warehouse@test.local",
        full_name="Складской логист",
        password_hash=hash_password("test"),
        is_active=True,
        is_admin=False,
    )
    db.session.add(user)
    db.session.flush()
    db.session.add(UserRole(user_id=user.id, role_id=role.id))
    db.session.commit()
    resp = client.post("/api/auth/login", json={"email": "warehouse@test.local", "password": "test"})
    assert resp.status_code == 200
    return client


def _payload():
    return {
        "request_date": "2026-09-10",
        "client_id": 1,
        "warehouse_id": 1,
        "from_location": "Стрельна",
        "to_location": "Софьино",
        "cargo_name": "Бойлерные материалы",
        "cargo_volume_m3": 12.5,
        "cargo_weight_t": 3.2,
        "quantity": 1,
        "unit": "pcs",
        "trucks_count": 2,
        "price": 15000,
        "priority": "high",
        "notes": "Доставить до обеда",
    }


def test_uznt_requests_crud_flow(auth_client, client):
    auth_client("transport@test.local", "test")

    empty = client.get("/api/uznt/requests").json
    assert empty["items"] == []
    assert empty["statuses"]

    created = client.post("/api/uznt/requests", json=_payload())
    assert created.status_code == 201
    body = created.json
    rid = body["id"]
    assert body["number"].startswith("UZNT-")
    assert body["client_name"] == "Аристон"
    assert body["warehouse_name"] in ("СПб-1", "Софьино")
    assert body["cargo_name"] == "Бойлерные материалы"
    assert body["trucks_count"] == 2
    assert body["priority"] == "high"
    assert body["status"] == "new"
    assert body["status_label"]

    fetched = client.get(f"/api/uznt/requests/{rid}").json
    assert fetched["id"] == rid
    assert fetched["cargo_volume_m3"] == 12.5

    listed = client.get("/api/uznt/requests").json
    assert listed["total"] == 1
    assert listed["items"][0]["number"] == body["number"]

    updated = client.put(
        f"/api/uznt/requests/{rid}",
        json={"status": "delivered", "price": 17200},
    )
    assert updated.status_code == 200
    assert updated.json["status"] == "delivered"
    assert updated.json["price"] == 17200.0
    # Частичное обновление не сбрасывает остальные поля.
    assert updated.json["cargo_name"] == "Бойлерные материалы"

    deleted = client.delete(f"/api/uznt/requests/{rid}")
    assert deleted.status_code == 200
    assert deleted.json["deleted_id"] == rid

    gone = client.get(f"/api/uznt/requests/{rid}")
    assert gone.status_code == 404


def test_uznt_request_validation(auth_client, client):
    auth_client("transport@test.local", "test")

    bad = client.post("/api/uznt/requests", json={"client_id": 1})
    assert bad.status_code == 422
    assert "request_date" in bad.json["errors"]

    bad_status = client.post(
        "/api/uznt/requests",
        json={**_payload(), "status": "bogus"},
    )
    assert bad_status.status_code == 422
    assert "status" in bad_status.json["errors"]

    unknown_client = client.post(
        "/api/uznt/requests",
        json={**_payload(), "client_id": 9999},
    )
    assert unknown_client.status_code == 422
    assert "client_id" in unknown_client.json["errors"]


def test_uznt_number_uniqueness(auth_client, client):
    auth_client("transport@test.local", "test")
    body = _payload()
    body["number"] = "UZNT-TEST-0001"
    first = client.post("/api/uznt/requests", json=body)
    assert first.status_code == 201

    dup = client.post("/api/uznt/requests", json=body)
    assert dup.status_code == 422
    assert "number" in dup.json["errors"]


def test_uznt_requests_permissions(client):
    _make_warehouse_user(client)
    # Просмотр/правка недоступны роли без секции заявок.
    assert client.get("/api/uznt/requests").status_code == 403
    assert client.post("/api/uznt/requests", json=_payload()).status_code == 403


def test_uznt_requests_meta(auth_client, client):
    auth_client("transport@test.local", "test")
    meta = client.get("/api/uznt/meta")
    assert meta.status_code == 200
    body = meta.json
    assert any(c["name"] == "Аристон" for c in body["clients"])
    assert body["warehouses"]
    assert body["units"]
    assert body["priorities"]


def test_uznt_requests_page(auth_client, client):
    auth_client("transport@test.local", "test")
    resp = client.get("/uznt/requests")
    assert resp.status_code == 200
    assert "Заявки на перевозку".encode("utf-8") in resp.data


def test_uznt_requests_as_admin(auth_client, client):
    auth_client("admin@test.local", "admin")
    empty = client.get("/api/uznt/requests")
    assert empty.status_code == 200
    created = client.post("/api/uznt/requests", json=_payload())
    assert created.status_code == 201