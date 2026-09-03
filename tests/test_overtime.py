"""Сверхурочная обработка ТС (паритет Billings)."""
from datetime import date, datetime

from app.modules.uss.services.overtime import is_overtime_end, row_is_overtime


def test_weekday_before_end_not_overtime():
    d = date(2026, 8, 3)  # понедельник
    assert is_overtime_end(d, "17:00") is False
    assert row_is_overtime(d, departed_at=datetime(2026, 8, 3, 17, 0)) is False


def test_weekday_after_end_is_overtime():
    d = date(2026, 8, 3)
    assert is_overtime_end(d, "18:00") is True
    assert row_is_overtime(d, departed_at=datetime(2026, 8, 3, 18, 30)) is True


def test_weekend_is_overtime():
    d = date(2026, 8, 2)  # воскресенье
    assert is_overtime_end(d, "10:00") is True


def test_custom_warehouse_end_time(app):
    from datetime import time as time_type

    from app.db import db
    from app.modules.reference.models import Warehouse
    from app.modules.uss.services.overtime import row_is_overtime

    d = date(2026, 8, 3)  # понедельник
    with app.app_context():
        wh = Warehouse(
            code="test_wh_ot",
            name="Test OT",
            work_day_start=time_type(8, 0),
            work_day_end=time_type(16, 0),
            is_active=True,
        )
        db.session.add(wh)
        db.session.commit()
        assert row_is_overtime(
            d,
            departed_at=datetime(2026, 8, 3, 16, 30),
            warehouse_id=wh.id,
        ) is True
        assert row_is_overtime(
            d,
            departed_at=datetime(2026, 8, 3, 15, 45),
            warehouse_id=wh.id,
        ) is False


def test_billing_dict_includes_overtime_flag(app):
    from app.db import db
    from app.modules.billing.aggregates import vehicle_operation_to_billing_dict
    from app.modules.uss.models import VehicleOperation

    with app.app_context():
        row = VehicleOperation(
            contract_id=1,
            warehouse_id=1,
            operation_date=date(2026, 8, 3),
            departed_at=datetime(2026, 8, 3, 19, 0),
            report_quantities={"inbound_manual_m3": 5},
        )
        db.session.add(row)
        db.session.commit()
        data = vehicle_operation_to_billing_dict(row)
        assert data["is_overtime"] is True
