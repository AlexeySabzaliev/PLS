"""Складская смена: только operation_daily_totals (без ТС)."""
from __future__ import annotations

from datetime import date

from app.modules.reference.models import Contract, ProductType
from app.modules.uss.services.operation_daily_totals import list_daily_totals, upsert_daily_totals
from app.modules.uss.services.report_schema import schema_for_contract_role

REPORT_ROLE = "warehouse_logistics"


def list_warehouse_shift(user: dict, warehouse_id: int, day: date) -> dict:
    wh_ids = user.get("warehouse_ids") or []
    if warehouse_id not in wh_ids and not user.get("is_admin"):
        return {"error": "forbidden"}
    contracts = (
        Contract.query.join(ProductType)
        .filter(
            Contract.warehouse_id == warehouse_id,
            Contract.status == "active",
            ProductType.code == "RESPONSIBLE_STORAGE",
        )
        .all()
    )
    totals_by_contract = {
        c.id: list_daily_totals(c.id, warehouse_id, day) for c in contracts
    }
    schemas = {
        str(c.id): schema_for_contract_role(c.id, day, REPORT_ROLE) for c in contracts
    }
    return {
        "warehouse_id": warehouse_id,
        "report_date": day.isoformat(),
        "report_role": REPORT_ROLE,
        "contracts": [{"id": c.id, "number": c.number} for c in contracts],
        "schemas": schemas,
        "daily_totals": {str(k): v for k, v in totals_by_contract.items()},
    }


def save_warehouse_shift(user: dict, payload: dict) -> dict:
    wh_id = payload.get("warehouse_id")
    wh_ids = user.get("warehouse_ids") or []
    if wh_id not in wh_ids and not user.get("is_admin"):
        return {"error": "forbidden"}
    report_date = date.fromisoformat(str(payload["report_date"])[:10])
    saved = upsert_daily_totals(
        payload["contract_id"],
        wh_id,
        report_date,
        payload.get("entries") or [],
    )
    return {"saved": saved}
