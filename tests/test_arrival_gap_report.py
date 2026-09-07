"""Отчёт отклонений «заявлено в охране vs приехало» — проверка формул по кодам."""
from datetime import date, datetime

from app.db import db
from app.modules.uss.models import VehicleOperation
from app.modules.uss.services.arrival_gap_report import build_arrival_gap_report


def _op(day: date, request_id: str, *, registered: bool = False,
        no_show: bool = False, processed: bool = False) -> VehicleOperation:
    return VehicleOperation(
        contract_id=1,
        warehouse_id=1,
        operation_date=day,
        operation_type_code="inbound",
        source="security",
        security_request_id=request_id,
        registered_at=datetime(2026, 9, 7, 9, 0) if registered else None,
        arrival_status="no_show" if no_show else "arrived",
        processed_at=datetime(2026, 9, 7, 18, 0) if processed else None,
    )


def test_arrival_gap_report_formulas(app):
    day = date(2026, 9, 7)
    with app.app_context():
        db.session.add_all([
            # Убытие зафиксировано → arrived (без processed)
            _op(day, "s1", registered=True),
            # Не приехала (no_show)
            _op(day, "s2", no_show=True),
            # Приехала и обработана → arrived + processed
            _op(day, "s3", registered=True, processed=True),
        ])
        db.session.commit()

        report = build_arrival_gap_report(1, day, day)
        assert report["status"] == "ok"
        assert report["planned_total"] == 3
        assert report["arrived_total"] == 2
        assert report["no_show_total"] == 1
        assert report["processed_total"] == 1
        # gap = planned - arrived
        assert report["gap_total"] == 1
        # confirmation_rate = processed / planned * 100
        assert report["confirmation_rate"] == round(100.0 / 3.0, 2)
        assert len(report["daily"]) == 1
        assert report["daily"][0]["gap"] == 1
        assert report["daily"][0]["planned"] == 3
        assert len(report["details"]) == 3

        # Строки-не-из-портала (source != security) не считаются.
        db.session.add(
            VehicleOperation(
                contract_id=1,
                warehouse_id=1,
                operation_date=day,
                operation_type_code="inbound",
                source="manual",
                registered_at=datetime(2026, 9, 7, 10, 0),
            )
        )
        db.session.commit()
        again = build_arrival_gap_report(1, day, day)
        assert again["planned_total"] == 3


def test_arrival_gap_report_unknown_warehouse(app):
    with app.app_context():
        report = build_arrival_gap_report(-1, date(2026, 9, 7), date(2026, 9, 7))
        assert report["error"] == "warehouse_not_found"