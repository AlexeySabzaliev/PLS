"""Тесты report_schema API и смен с schema в ответе."""
from datetime import date


def test_report_schema_warehouse(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.get(
        "/api/uss/report-schema?contract_id=1&role=warehouse_logistics&date=2026-01-15"
    )
    assert resp.status_code == 200
    codes = [x["billing_line_code"] for x in resp.json["period_inputs"]]
    assert "valve_gluing" in codes


def test_transport_shift_includes_schema(auth_client, client):
    auth_client("transport@test.local", "test")
    resp = client.get("/api/uss/transport/shift?warehouse_id=1&date=2026-01-15")
    assert resp.status_code == 200
    data = resp.json
    assert "schemas" in data
    assert "1" in data["schemas"]
    assert "vehicle_fixed_fields" in data["schemas"]["1"]


def test_warehouse_shift_no_vehicles(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.get("/api/uss/warehouse/shift?warehouse_id=1&date=2026-01-15")
    assert resp.status_code == 200
    data = resp.json
    assert "vehicles" not in data
    assert "schemas" in data
    assert "daily_totals" in data


def test_warehouse_save_daily(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.post(
        "/api/uss/warehouse/shift",
        json={
            "warehouse_id": 1,
            "contract_id": 1,
            "report_date": "2026-01-20",
            "entries": [{"billing_line_code": "valve_gluing", "quantity": 42}],
        },
    )
    assert resp.status_code == 200
    get_resp = client.get("/api/uss/warehouse/shift?warehouse_id=1&date=2026-01-20")
    totals = get_resp.json["daily_totals"]["1"]
    assert any(t["billing_line_code"] == "valve_gluing" and t["quantity"] == 42 for t in totals)


def test_inventory_shift_schema(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.get("/api/uss/inventory/shift?warehouse_id=1&date=2026-01-15")
    assert resp.status_code == 200
    data = resp.json
    assert "schemas" in data
    assert "contracts" in data
    assert "status" not in data


def test_inventory_save(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.post(
        "/api/uss/inventory/shift",
        json={
            "warehouse_id": 1,
            "report_date": "2026-02-01",
            "area_entries": {"storage_area_extra": 1500},
            "extra_entries": {},
        },
    )
    assert resp.status_code == 200
    get_resp = client.get("/api/uss/inventory/shift?warehouse_id=1&date=2026-02-01")
    assert get_resp.json["area_entries"].get("storage_area_extra") == 1500


def test_shift_context(auth_client, client):
    auth_client("transport@test.local", "test")
    resp = client.get("/api/uss/context?role=transport_logistics&date=2026-08-01")
    assert resp.status_code == 200
    data = resp.json
    assert data["warehouse_id"] == 1
    assert len(data["warehouses"]) >= 1
    assert len(data["contracts"]) >= 1
