"""Закрытие дня по ролям."""
from __future__ import annotations

from datetime import date, datetime

from app.db import db
from app.modules.processes.templates import REPORT_ROLES
from app.modules.uss.models import ShiftDayConfirmation

ALL_ROLES = list(REPORT_ROLES)


def day_summary(warehouse_id: int, report_date: date) -> dict:
    rows = ShiftDayConfirmation.query.filter_by(
        warehouse_id=warehouse_id,
        report_date=report_date,
    ).all()
    confirmed = {r.report_role: r.confirmed_at.isoformat() if r.confirmed_at else None for r in rows}
    return {
        "warehouse_id": warehouse_id,
        "report_date": report_date.isoformat(),
        "roles": ALL_ROLES,
        "confirmed": confirmed,
        "fully_closed": all(role in confirmed for role in ALL_ROLES),
    }


def confirm_day(user: dict, warehouse_id: int, report_date: date, report_role: str) -> dict:
    if report_role not in REPORT_ROLES:
        return {"error": "invalid_role"}
    wh_ids = user.get("warehouse_ids") or []
    if warehouse_id not in wh_ids and not user.get("is_admin"):
        return {"error": "forbidden"}
    row = ShiftDayConfirmation.query.filter_by(
        warehouse_id=warehouse_id,
        report_date=report_date,
        report_role=report_role,
    ).first()
    if not row:
        row = ShiftDayConfirmation(
            warehouse_id=warehouse_id,
            report_date=report_date,
            report_role=report_role,
        )
        db.session.add(row)
    row.confirmed_by = user["id"]
    row.confirmed_at = datetime.utcnow()
    db.session.commit()
    return day_summary(warehouse_id, report_date)
