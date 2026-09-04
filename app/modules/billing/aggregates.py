"""Агрегация операционных данных для биллинга."""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from app.db import db
from app.modules.uss.models import OperationDailyTotal, VehicleOperation
from app.modules.uss.services.overtime import row_is_overtime
from app.modules.uss.services.warehouse_schedule import warehouse_work_day_end


def _d(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _parse_json_obj(raw) -> dict:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw) or {}
        except json.JSONDecodeError:
            return {}
    return {}


def sum_daily_totals_by_code(
    contract_id: int,
    period_start: date,
    period_end: date,
) -> dict[str, Decimal]:
    from flask import has_app_context

    if not has_app_context():
        return {}
    rows = (
        db.session.query(
            OperationDailyTotal.billing_line_code,
            db.func.sum(OperationDailyTotal.quantity),
        )
        .filter(
            OperationDailyTotal.contract_id == contract_id,
            OperationDailyTotal.report_date >= period_start,
            OperationDailyTotal.report_date <= period_end,
        )
        .group_by(OperationDailyTotal.billing_line_code)
        .all()
    )
    return {code: _d(qty) for code, qty in rows}


def sum_vehicle_report_quantities(
    operations: list[dict],
    period_start: date,
    period_end: date,
) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = {}
    for op in operations:
        od = op.get("operation_date")
        if isinstance(od, str):
            od = date.fromisoformat(od[:10])
        if not (period_start <= od <= period_end):
            continue
        for code, raw in _parse_json_obj(op.get("report_quantities")).items():
            if not code:
                continue
            totals[code] = totals.get(code, Decimal("0")) + _d(raw)
    return totals


def vehicle_operation_to_billing_dict(row: VehicleOperation, *, work_day_end=None) -> dict:
    """VehicleOperation → формат калькулятора Billings."""
    if work_day_end is None:
        work_day_end = warehouse_work_day_end(row.warehouse_id)
    rq = row.report_quantities or {}
    return {
        "operation_date": row.operation_date,
        "volume_document_m3": row.volume_document_m3,
        "extra_handling_m3": row.extra_handling_m3,
        "extra_document_set_qty": row.extra_document_set_qty,
        "billing_document_qty": row.billing_document_qty or 1,
        "inbound_manual_m3": rq.get("inbound_manual_m3", 0),
        "outbound_manual_m3": rq.get("outbound_manual_m3", 0),
        "inbound_mech_m3": rq.get("inbound_mech_m3", 0),
        "outbound_mech_m3": rq.get("outbound_mech_m3", 0),
        "report_quantities": rq,
        "departed_at": row.departed_at,
        "is_overtime": row_is_overtime(
            row.operation_date,
            departed_at=row.departed_at,
            work_day_end=work_day_end,
        ),
    }


def load_vehicle_operations(
    contract_id: int,
    warehouse_id: int,
    period_start: date,
    period_end: date,
) -> list[dict]:
    rows = (
        VehicleOperation.query.filter(
            VehicleOperation.contract_id == contract_id,
            VehicleOperation.warehouse_id == warehouse_id,
            VehicleOperation.operation_date >= period_start,
            VehicleOperation.operation_date <= period_end,
        )
        .order_by(VehicleOperation.operation_date, VehicleOperation.id)
        .all()
    )
    work_end = warehouse_work_day_end(warehouse_id)
    return [vehicle_operation_to_billing_dict(r, work_day_end=work_end) for r in rows]
