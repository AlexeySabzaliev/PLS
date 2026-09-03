"""Тесты выбора договоров смены на дату."""
from datetime import date, timedelta


def test_shift_context_past_date(auth_client, client):
    auth_client("transport@test.local", "test")
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    resp = client.get(f"/api/uss/context?role=transport_logistics&date={yesterday}")
    assert resp.status_code == 200
    data = resp.json
    assert data["date"] == yesterday
    assert data["today"] == date.today().isoformat()
    assert data["min_date"] <= yesterday <= data["max_date"]


def test_transport_shift_yesterday(auth_client, client):
    auth_client("transport@test.local", "test")
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    resp = client.get(f"/api/uss/transport/shift?warehouse_id=1&date={yesterday}")
    assert resp.status_code == 200
    data = resp.json
    assert data["operation_date"] == yesterday
    assert "schemas" in data
    assert "vehicles" in data
    assert data["min_date"] <= yesterday <= data["max_date"]


def test_warehouse_shift_past_date(auth_client, client):
    auth_client("admin@test.local", "admin")
    past = (date.today() - timedelta(days=3)).isoformat()
    resp = client.get(f"/api/uss/warehouse/shift?warehouse_id=1&date={past}")
    assert resp.status_code == 200
    assert resp.json["report_date"] == past


def test_inventory_shift_past_date(auth_client, client):
    auth_client("admin@test.local", "admin")
    past = (date.today() - timedelta(days=5)).isoformat()
    resp = client.get(f"/api/uss/inventory/shift?warehouse_id=1&date={past}")
    assert resp.status_code == 200
    assert resp.json["report_date"] == past
