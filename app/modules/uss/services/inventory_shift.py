"""Управление запасами: shift_reports."""
from __future__ import annotations

from datetime import date

from app.db import db
from app.modules.billing.period_lock import (
    PeriodLockedError,
    assert_warehouse_date_editable,
    periods_status_for_contracts,
)
from app.modules.uss.services.shift_contracts import (
    contracts_for_inventory_shift,
    serialize_shift_blocks,
    shift_date_bounds,
)
from app.modules.uss.models import ShiftReport
from app.modules.uss.services.report_schema import schema_for_contract_role

REPORT_ROLE = "inventory_management"


def get_inventory_shift(user: dict, warehouse_id: int, day: date) -> dict:
    wh_ids = user.get("warehouse_ids") or []
    if warehouse_id not in wh_ids and not user.get("is_admin"):
        return {"error": "forbidden"}
    row = ShiftReport.query.filter_by(warehouse_id=warehouse_id, report_date=day).first()
    contracts = contracts_for_inventory_shift(warehouse_id, day)
    blocks = serialize_shift_blocks(contracts, day)
    contract_ids = list({b["contract_id"] for b in blocks})
    schemas: dict[str, dict] = {}
    for b in blocks:
        sch = schema_for_contract_role(
            b["contract_id"],
            day,
            REPORT_ROLE,
            amendment_id=b.get("amendment_id"),
        )
        schemas[b["block_key"]] = sch
        cid = str(b["contract_id"])
        if cid not in schemas:
            schemas[cid] = sch
    period_locks = periods_status_for_contracts(contract_ids, day.year, day.month)
    warehouse_locked = any(p.get("locked") for p in period_locks.values())
    min_date, max_date = shift_date_bounds()
    return {
        "warehouse_id": warehouse_id,
        "report_date": day.isoformat(),
        "report_role": REPORT_ROLE,
        "contracts": blocks,
        "today": date.today().isoformat(),
        "min_date": min_date,
        "max_date": max_date,
        "schemas": schemas,
        "area_entries": (row.area_entries if row else {}) or {},
        "extra_entries": (row.extra_entries if row else {}) or {},
        "period_locks": {str(k): v for k, v in period_locks.items()},
        "warehouse_locked": warehouse_locked,
    }


def save_inventory_shift(user: dict, payload: dict) -> dict:
    wh_id = payload.get("warehouse_id")
    wh_ids = user.get("warehouse_ids") or []
    if wh_id not in wh_ids and not user.get("is_admin"):
        return {"error": "forbidden"}
    report_date = date.fromisoformat(str(payload["report_date"])[:10])
    try:
        assert_warehouse_date_editable(user, wh_id, report_date)
    except PeriodLockedError as exc:
        return {"error": "period_locked", "message": str(exc)}
    row = ShiftReport.query.filter_by(warehouse_id=wh_id, report_date=report_date).first()
    if not row:
        row = ShiftReport(warehouse_id=wh_id, report_date=report_date)
        db.session.add(row)
    row.area_entries = payload.get("area_entries") or {}
    row.extra_entries = payload.get("extra_entries") or {}
    db.session.commit()
    return {"saved": True, "id": row.id}
