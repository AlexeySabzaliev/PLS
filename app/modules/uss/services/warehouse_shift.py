"""Складская смена: только operation_daily_totals (без ТС)."""
from __future__ import annotations

from datetime import date

from app.modules.billing.period_lock import (
    PeriodLockedError,
    assert_operations_editable,
    periods_status_for_contracts,
)
from app.modules.uss.services.shift_contracts import (
    contracts_for_warehouse_shift,
    serialize_shift_blocks,
    shift_date_bounds,
)
from app.modules.uss.services.operation_daily_totals import list_daily_totals, upsert_daily_totals
from app.modules.uss.services.report_schema import schema_for_contract_role

REPORT_ROLE = "warehouse_logistics"


def list_warehouse_shift(user: dict, warehouse_id: int, day: date) -> dict:
    wh_ids = user.get("warehouse_ids") or []
    if warehouse_id not in wh_ids and not user.get("is_admin"):
        return {"error": "forbidden"}
    contracts = contracts_for_warehouse_shift(warehouse_id, day)
    blocks = serialize_shift_blocks(contracts, day)
    contract_ids = list({b["contract_id"] for b in blocks})
    totals_by_contract = {
        cid: list_daily_totals(cid, warehouse_id, day) for cid in contract_ids
    }
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
        "daily_totals": {str(k): v for k, v in totals_by_contract.items()},
        "period_locks": {str(k): v for k, v in period_locks.items()},
    }


def save_warehouse_shift(user: dict, payload: dict) -> dict:
    wh_id = payload.get("warehouse_id")
    wh_ids = user.get("warehouse_ids") or []
    if wh_id not in wh_ids and not user.get("is_admin"):
        return {"error": "forbidden"}
    report_date = date.fromisoformat(str(payload["report_date"])[:10])
    try:
        assert_operations_editable(user, int(payload["contract_id"]), report_date)
    except PeriodLockedError as exc:
        return {"error": "period_locked", "message": str(exc)}
    saved = upsert_daily_totals(
        payload["contract_id"],
        wh_id,
        report_date,
        payload.get("entries") or [],
    )
    return {"saved": saved}
