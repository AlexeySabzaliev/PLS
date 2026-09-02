"""Тесты накладных и импорта с охраны."""

def test_save_vehicle_with_waybills(auth_client, client):
    auth_client("transport@test.local", "test")
    payload = {
        "warehouse_id": 1,
        "contract_id": 1,
        "operation_date": "2026-08-03",
        "tractor_plate": "К111КК11",
        "operation_type_code": "inbound",
        "waybills": [
            {"waybill_number": "WB-1001", "mx_number": "MX-1001"},
            {"waybill_number": "WB-1002", "mx_number": "MX-1002"},
        ],
    }
    resp = client.post("/api/uss/transport/vehicles", json=payload)
    assert resp.status_code == 200

    resp2 = client.get("/api/uss/transport/shift?warehouse_id=1&date=2026-08-03")
    row = next(v for v in resp2.json["vehicles"] if v["tractor_plate"] == "К111КК11")
    assert len(row["waybills"]) == 2
    assert row["waybill_number"] == "WB-1001"
    assert row["mx1_number"] == "MX-1001"


def test_transport_shift_includes_vehicle_types(auth_client, client):
    auth_client("transport@test.local", "test")
    resp = client.get("/api/uss/transport/shift?warehouse_id=1&date=2026-08-01")
    assert resp.status_code == 200
    types = resp.json.get("vehicle_types") or []
    assert any(t["code"] == "truck" for t in types)


def test_sync_security_mock(auth_client, client, monkeypatch):
    monkeypatch.setenv("SECURITY_USE_MOCK", "1")
    auth_client("transport@test.local", "test")
    resp = client.post(
        "/api/uss/transport/sync-security",
        json={"warehouse_id": 1, "date": "2026-08-05"},
    )
    assert resp.status_code == 200
    assert resp.json["synced"] >= 1

    resp2 = client.get("/api/uss/transport/shift?warehouse_id=1&date=2026-08-05")
    security_rows = [v for v in resp2.json["vehicles"] if v.get("source") == "security"]
    assert len(security_rows) >= 1
