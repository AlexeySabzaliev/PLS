"""Блокировка биллингового периода."""
from datetime import date

import pytest

from app.modules.billing.period_lock import lock_period, unlock_period
from app.modules.reference.models import User


def test_period_lock_blocks_vehicle_save(auth_client, client, app):
    auth_client("admin@test.local", "admin")
    client.post(
        "/api/uss/transport/vehicles",
        json={
            "warehouse_id": 1,
            "contract_id": 1,
            "operation_date": "2026-08-05",
            "tractor_plate": "LOCK01",
        },
    )
    with app.app_context():
        admin = User.query.filter_by(email="admin@test.local").first()
        lock_period({"id": admin.id, "is_admin": False}, contract_id=1, year=2026, month=8)
    auth_client("transport@test.local", "test")
    resp = client.post(
        "/api/uss/transport/vehicles",
        json={
            "warehouse_id": 1,
            "contract_id": 1,
            "operation_date": "2026-08-06",
            "tractor_plate": "BLOCKED",
        },
    )
    assert resp.status_code == 409
    assert resp.json["error"] == "period_locked"


def test_period_lock_admin_can_save(auth_client, client, app):
    with app.app_context():
        admin = User.query.filter_by(email="admin@test.local").first()
        lock_period({"id": admin.id, "is_admin": True}, contract_id=1, year=2026, month=8)
    auth_client("admin@test.local", "admin")
    resp = client.post(
        "/api/uss/transport/vehicles",
        json={
            "warehouse_id": 1,
            "contract_id": 1,
            "operation_date": "2026-08-07",
            "tractor_plate": "ADMINOK",
        },
    )
    assert resp.status_code == 200


def test_billing_period_lock_unlock_api(auth_client, client):
    auth_client("admin@test.local", "admin")
    lock = client.post(
        "/api/billing/period/lock",
        json={"contract_id": 1, "year": 2026, "month": 8, "total_ex_vat": 1000},
    )
    assert lock.status_code == 200
    assert lock.json["period"]["locked"] is True

    get = client.get("/api/billing/period?contract_id=1&year=2026&month=8")
    assert get.json["status"] == "confirmed"

    unlock = client.post(
        "/api/billing/period/unlock",
        json={"contract_id": 1, "year": 2026, "month": 8},
    )
    assert unlock.status_code == 200
    assert unlock.json["period"]["locked"] is False


def test_transport_shift_includes_period_locks(auth_client, client):
    auth_client("transport@test.local", "test")
    resp = client.get("/api/uss/transport/shift?warehouse_id=1&date=2026-08-01")
    assert resp.status_code == 200
    assert "period_locks" in resp.json
    assert "1" in resp.json["period_locks"]
