"""Отчёт отклонений: заявлено в охране vs приехало фактически."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from app.db import db
from app.modules.reference.models import Warehouse
from app.modules.uss.models import VehicleOperation
from app.modules.uss.services.shift_day_confirm import is_day_confirmed


def _date_range(period_from: date, period_to: date):
    cur = period_from
    while cur <= period_to:
        yield cur
        cur += timedelta(days=1)


def build_arrival_gap_report(warehouse_id: int, period_from: date, period_to: date) -> dict:
    wh = db.session.get(Warehouse, warehouse_id)
    if not wh:
        return {"error": "warehouse_not_found"}

    rows = (
        VehicleOperation.query.filter(
            VehicleOperation.warehouse_id == warehouse_id,
            VehicleOperation.operation_date >= period_from,
            VehicleOperation.operation_date <= period_to,
            VehicleOperation.source == "security",
        )
        .order_by(VehicleOperation.operation_date, VehicleOperation.id)
        .all()
    )

    by_day = defaultdict(lambda: {"planned": 0, "arrived": 0, "no_show": 0, "processed": 0})
    details = []
    planned_total = arrived_total = no_show_total = processed_total = 0

    for row in rows:
        day = row.operation_date.isoformat()
        bucket = by_day[day]
        bucket["planned"] += 1
        planned_total += 1
        arrived = bool(row.registered_at) and row.arrival_status != "no_show"
        no_show = row.arrival_status == "no_show"
        processed = bool(row.processed_at)
        if arrived:
            bucket["arrived"] += 1
            arrived_total += 1
        if no_show:
            bucket["no_show"] += 1
            no_show_total += 1
        if processed:
            bucket["processed"] += 1
            processed_total += 1
        details.append({
            "date": day,
            "contract_id": row.contract_id,
            "operation_id": row.id,
            "security_request_id": row.security_request_id,
            "source": row.source,
            "arrival_status": row.arrival_status,
            "registered_at": row.registered_at.isoformat() if row.registered_at else None,
            "departed_at": row.departed_at.isoformat() if row.departed_at else None,
            "processed_at": row.processed_at.isoformat() if row.processed_at else None,
            "is_confirmed_day": is_day_confirmed(warehouse_id, row.operation_date),
            "is_arrived": arrived,
            "is_no_show": no_show,
        })

    daily = []
    for day in _date_range(period_from, period_to):
        day_key = day.isoformat()
        bucket = by_day[day_key]
        daily.append({
            "date": day_key,
            "is_confirmed_day": is_day_confirmed(warehouse_id, day),
            "planned": bucket["planned"],
            "arrived": bucket["arrived"],
            "no_show": bucket["no_show"],
            "processed": bucket["processed"],
            "gap": bucket["planned"] - bucket["arrived"],
        })

    return {
        "status": "ok",
        "warehouse_id": warehouse_id,
        "warehouse_code": wh.code,
        "warehouse_name": wh.name,
        "period_from": period_from.isoformat(),
        "period_to": period_to.isoformat(),
        "planned_total": planned_total,
        "arrived_total": arrived_total,
        "no_show_total": no_show_total,
        "processed_total": processed_total,
        "gap_total": planned_total - arrived_total,
        "confirmation_rate": round((processed_total / planned_total * 100.0), 2) if planned_total else 0.0,
        "daily": daily,
        "details": details,
    }
