"""Отчёт ФОТ vs операционка."""
from datetime import date
from decimal import Decimal

from app.db import db
from app.modules.billing.operational_revenue import daily_operational_revenue_for_contract
from app.modules.uss.models import WarehouseStaffPosition, WarehouseStaffPositionVersion
from app.modules.uss.services.fot_efficiency import build_fot_report
from app.modules.uss.services.staff_positions import monthly_fot_total


def test_monthly_fot_total_empty():
    assert monthly_fot_total([]) == Decimal("0")


def test_monthly_fot_total_sums():
    positions = [{"monthly_rate": 50000, "headcount": 2}, {"monthly_rate": 80000, "headcount": 1}]
    assert monthly_fot_total(positions) == Decimal("180000")


def test_daily_operational_revenue_skips_storage():
    tariffs = [
        {
            "billing_line_code": "manual_m3",
            "rate_ex_vat": "100",
            "valid_from": date(2026, 7, 1),
            "valid_to": None,
            "formula": "rate_times_qty",
        },
        {
            "billing_line_code": "storage_area_fixed",
            "rate_ex_vat": "999",
            "valid_from": date(2026, 7, 1),
            "valid_to": None,
            "formula": "rate_times_days_times_qty",
        },
    ]
    operations = [{
        "operation_date": date(2026, 7, 10),
        "inbound_manual_m3": 1,
        "outbound_manual_m3": 0,
        "inbound_mech_m3": 0,
        "outbound_mech_m3": 0,
        "volume_document_m3": 1,
        "is_overtime": False,
    }]
    daily = daily_operational_revenue_for_contract(2026, 7, tariffs, operations, [])
    assert daily[date(2026, 7, 10)] == Decimal("100")


def test_fot_report_api_requires_auth(client):
    resp = client.get("/api/uss/reports/fot?warehouse_id=1&year=2026&month=8")
    assert resp.status_code in (401, 403)


def test_fot_report_api_admin(auth_client, client, app):
    auth_client("admin@test.local", "admin")
    resp = client.get("/api/uss/reports/fot?warehouse_id=1&year=2026&month=8")
    assert resp.status_code == 200
    data = resp.json
    assert data["warehouse_id"] == 1
    assert data["year"] == 2026
    assert data["month"] == 8
    assert "daily" in data
    assert "weekly" in data
    assert "monthly_ops_revenue" in data
    assert data.get("staff_missing") is True


def test_fot_report_with_staff(auth_client, client, app):
    auth_client("admin@test.local", "admin")
    with app.app_context():
        pos = WarehouseStaffPosition(
            warehouse_id=1,
            name="Кладовщик",
            monthly_rate=Decimal("100000"),
            headcount=2,
            is_active=True,
            sort_order=10,
        )
        db.session.add(pos)
        db.session.flush()
        db.session.add(WarehouseStaffPositionVersion(
            position_id=pos.id,
            warehouse_id=1,
            name="Кладовщик",
            monthly_rate=Decimal("100000"),
            headcount=2,
            valid_from=date(2026, 1, 1),
        ))
        db.session.commit()

    resp = client.get("/api/uss/reports/fot?warehouse_id=1&year=2026&month=8")
    assert resp.status_code == 200
    data = resp.json
    assert data["monthly_fot"] > 0
    assert not data.get("staff_missing")
    assert len(data["staff"]) >= 1


def test_fot_report_page_has_toolbar(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.get("/uss/reports/fot")
    text = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "Эффективность ОХ" in text
    assert 'id="toolbar"' in text
    assert "uss_fot.js" in text


def test_fot_report_page(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.get("/uss/reports/fot")
    assert resp.status_code == 200
    assert "Эффективность ОХ" in resp.get_data(as_text=True)


def test_reports_hub(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.get("/uss/reports", follow_redirects=True)
    assert resp.status_code == 200
    assert "Биллинг" in resp.get_data(as_text=True)
