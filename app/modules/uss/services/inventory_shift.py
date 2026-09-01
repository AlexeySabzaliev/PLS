"""Управление запасами: shift_reports (заглушка)."""
from __future__ import annotations

from datetime import date

from app.db import db
from app.modules.uss.models import ShiftReport


def get_inventory_shift(user: dict, warehouse_id: int, day: date) -> dict:
    wh_ids = user.get("warehouse_ids") or []
    if warehouse_id not in wh_ids and not user.get("is_admin"):
        return {"error": "forbidden"}
    row = ShiftReport.query.filter_by(warehouse_id=warehouse_id, report_date=day).first()
    return {
        "warehouse_id": warehouse_id,
        "report_date": day.isoformat(),
        "area_entries": (row.area_entries if row else {}) or {},
        "extra_entries": (row.extra_entries if row else {}) or {},
        "status": "stub",
    }


def save_inventory_shift(user: dict, payload: dict) -> dict:
    wh_id = payload.get("warehouse_id")
    wh_ids = user.get("warehouse_ids") or []
    if wh_id not in wh_ids and not user.get("is_admin"):
        return {"error": "forbidden"}
    report_date = date.fromisoformat(str(payload["report_date"])[:10])
    row = ShiftReport.query.filter_by(warehouse_id=wh_id, report_date=report_date).first()
    if not row:
        row = ShiftReport(warehouse_id=wh_id, report_date=report_date)
        db.session.add(row)
    row.area_entries = payload.get("area_entries") or {}
    row.extra_entries = payload.get("extra_entries") or {}
    db.session.commit()
    return {"saved": True, "id": row.id}
