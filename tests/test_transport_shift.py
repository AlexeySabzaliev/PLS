"""Базовые тесты транспортной смены."""
from datetime import date


def test_transport_shift_list(auth_client, client):
    auth_client("transport@test.local", "test")
    resp = client.get("/api/uss/transport/shift?warehouse_id=1&date=2026-08-01")
    assert resp.status_code == 200
    data = resp.json
    assert data["warehouse_id"] == 1
    assert "vehicles" in data


def test_save_vehicle_row(auth_client, client):
    auth_client("transport@test.local", "test")
    payload = {
        "warehouse_id": 1,
        "contract_id": 1,
        "operation_date": "2026-08-01",
        "plate_number": "A123BC78",
        "volume_document_m3": 12.5,
        "handling_type_code": "manual",
    }
    resp = client.post("/api/uss/transport/vehicles", json=payload)
    assert resp.status_code == 200
    assert resp.json["saved"] is True

    resp2 = client.get("/api/uss/transport/shift?warehouse_id=1&date=2026-08-01")
    assert len(resp2.json["vehicles"]) == 1
    assert resp2.json["vehicles"][0]["plate_number"] == "A123BC78"


def test_save_vehicle_report_quantities(auth_client, client):
    auth_client("transport@test.local", "test")
    payload = {
        "warehouse_id": 1,
        "contract_id": 1,
        "operation_date": "2026-08-02",
        "plate_number": "X999XX99",
        "report_quantities": {"extra_vehicle_docs_rf": 2, "elco_passports": 1},
    }
    resp = client.post("/api/uss/transport/vehicles", json=payload)
    assert resp.status_code == 200

    resp2 = client.get("/api/uss/transport/shift?warehouse_id=1&date=2026-08-02")
    row = next(v for v in resp2.json["vehicles"] if v["plate_number"] == "X999XX99")
    assert row["report_quantities"]["extra_vehicle_docs_rf"] == 2
    assert row["report_quantities"]["elco_passports"] == 1


def test_day_confirm(auth_client, client):
    auth_client("transport@test.local", "test")
    resp = client.post(
        "/api/uss/day-confirm",
        json={
            "warehouse_id": 1,
            "report_date": "2026-08-01",
            "report_role": "transport_logistics",
        },
    )
    assert resp.status_code == 200
    assert "transport_logistics" in resp.json["confirmed"]
