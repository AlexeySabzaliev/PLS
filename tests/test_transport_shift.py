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
        "tractor_plate": "A123BC78",
        "operation_type_code": "inbound",
        "handling_type_code": "manual",
        "volume_document_m3": 12.5,
    }
    resp = client.post("/api/uss/transport/vehicles", json=payload)
    assert resp.status_code == 200
    assert resp.json["saved"] is True

    resp2 = client.get("/api/uss/transport/shift?warehouse_id=1&date=2026-08-01")
    row = resp2.json["vehicles"][0]
    assert row["tractor_plate"] == "A123BC78"
    assert row["operation_type_code"] == "inbound"
    assert row["handling_type_code"] == "manual"
    assert row["report_quantities"]["inbound_manual_m3"] == 12.5


def test_transport_schema_has_operation_select(auth_client, client):
    auth_client("transport@test.local", "test")
    resp = client.get("/api/uss/transport/shift?warehouse_id=1&date=2026-08-01")
    fields = resp.json["schemas"]["1"]["vehicle_fixed_fields"]
    field_names = [f["field"] for f in fields]
    assert "waybill_numbers" in field_names
    assert "mx_numbers" in field_names
    assert "extra_document_set_qty" not in field_names
    op = next(f for f in fields if f["field"] == "operation_type_code")
    handling = next(f for f in fields if f["field"] == "handling_type_code")
    assert op["input_type"] == "select"
    assert handling["input_type"] == "select"
    assert any(c["value"] == "inbound" for c in op["choices"])
    assert any(c["value"] == "manual" for c in handling["choices"])
    tariff_codes = [t["billing_line_code"] for t in resp.json["schemas"]["1"]["vehicle_inputs"]]
    assert "extra_vehicle_docs_rf" in tariff_codes


def test_save_vehicle_report_quantities(auth_client, client):
    auth_client("transport@test.local", "test")
    payload = {
        "warehouse_id": 1,
        "contract_id": 1,
        "operation_date": "2026-08-02",
        "tractor_plate": "X999XX99",
        "report_quantities": {"extra_vehicle_docs_rf": 2, "elco_passports": 1},
    }
    resp = client.post("/api/uss/transport/vehicles", json=payload)
    assert resp.status_code == 200

    resp2 = client.get("/api/uss/transport/shift?warehouse_id=1&date=2026-08-02")
    row = next(v for v in resp2.json["vehicles"] if v["tractor_plate"] == "X999XX99")
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
