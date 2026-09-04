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
    tariff_cols = [f for f in fields if f.get("tariff_input")]
    tariff_codes = [f["billing_line_code"] for f in tariff_cols]
    assert "extra_vehicle_docs_rf" in tariff_codes
    assert "elco_passports" in tariff_codes
    handling_idx = field_names.index("handling_type_code")
    reg_idx = field_names.index("registered_at")
    first_tariff_idx = field_names.index(tariff_cols[0]["field"])
    assert handling_idx < first_tariff_idx < reg_idx
    assert "extra_handling_m3" not in field_names
    schema_vehicle_codes = [t["billing_line_code"] for t in resp.json["schemas"]["1"]["vehicle_inputs"]]
    assert "extra_vehicle_docs_rf" in schema_vehicle_codes


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


def test_save_transport_daily(auth_client, client):
    auth_client("transport@test.local", "test")
    payload = {
        "warehouse_id": 1,
        "contract_id": 1,
        "report_date": "2026-08-04",
        "entries": [{"billing_line_code": "is_custom", "quantity": 3}],
    }
    resp = client.post("/api/uss/transport/daily", json=payload)
    assert resp.status_code == 200
    assert resp.json["saved"]

    shift = client.get("/api/uss/transport/shift?warehouse_id=1&date=2026-08-04").json
    totals = shift["daily_totals"].get("1") or []
    row = next(t for t in totals if t["billing_line_code"] == "is_custom")
    assert row["quantity"] == 3.0


def test_vehicle_overtime_in_shift_list(auth_client, client):
    auth_client("transport@test.local", "test")
    payload = {
        "warehouse_id": 1,
        "contract_id": 1,
        "operation_date": "2026-08-03",
        "tractor_plate": "О777ОО77",
        "operation_type_code": "inbound",
        "handling_type_code": "manual",
        "volume_document_m3": 10,
        "departed_at": "19:30",
    }
    resp = client.post("/api/uss/transport/vehicles", json=payload)
    assert resp.status_code == 200

    shift = client.get("/api/uss/transport/shift?warehouse_id=1&date=2026-08-03").json
    row = next(v for v in shift["vehicles"] if v["tractor_plate"] == "О777ОО77")
    assert row["is_overtime"] is True


def test_vehicle_complete_without_trailer(auth_client, client):
    auth_client("transport@test.local", "test")
    payload = {
        "warehouse_id": 1,
        "contract_id": 1,
        "operation_date": "2026-08-05",
        "tractor_plate": "B111BB11",
        "trailer_plate": None,
        "operation_type_code": "inbound",
        "registered_at": "08:00",
        "departed_at": "09:30",
    }
    resp = client.post("/api/uss/transport/vehicles", json=payload)
    assert resp.status_code == 200
    vehicle = resp.json["vehicle"]
    assert vehicle["is_complete"] is True
    assert vehicle["trailer_plate"] in (None, "")


def test_vehicle_no_show_and_audit(auth_client, client):
    auth_client("transport@test.local", "test")
    create = client.post("/api/uss/transport/vehicles", json={
        "warehouse_id": 1,
        "contract_id": 1,
        "operation_date": "2026-08-06",
        "tractor_plate": "C222CC22",
        "operation_type_code": "inbound",
    })
    assert create.status_code == 200
    vid = create.json["id"]

    no_show = client.post(f"/api/uss/transport/vehicles/{vid}/no-show", json={})
    assert no_show.status_code == 200
    assert no_show.json["vehicle"]["arrival_status"] == "no_show"
    assert no_show.json["vehicle"]["is_complete"] is True

    audit = client.get(f"/api/uss/transport/vehicles/{vid}/audit")
    assert audit.status_code == 200
    actions = [item["action"] for item in audit.json["items"]]
    assert "create" in actions
    assert "no_show" in actions
