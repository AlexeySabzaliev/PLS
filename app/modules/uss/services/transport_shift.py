"""Транспортная смена: vehicle_operations + суточные допы."""
from __future__ import annotations

from datetime import date, datetime

from app.db import db
from app.modules.reference.models import Contract, ProductType
from app.modules.uss.models import VehicleOperation
from app.modules.uss.services.operation_daily_totals import list_daily_totals, upsert_daily_totals
from app.modules.uss.services.report_schema import schema_for_contract_role

REPORT_ROLE = "transport_logistics"


def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def list_transport_shift(user: dict, warehouse_id: int, day: date) -> dict:
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
    vehicles = VehicleOperation.query.filter_by(
        warehouse_id=warehouse_id,
        operation_date=day,
    ).order_by(VehicleOperation.id).all()
    schemas = {
        str(c.id): schema_for_contract_role(c.id, day, REPORT_ROLE) for c in contracts
    }
    daily_totals = {
        str(c.id): list_daily_totals(c.id, warehouse_id, day) for c in contracts
    }
    return {
        "warehouse_id": warehouse_id,
        "operation_date": day.isoformat(),
        "report_role": REPORT_ROLE,
        "contracts": [{"id": c.id, "number": c.number, "client_id": c.client_id} for c in contracts],
        "schemas": schemas,
        "daily_totals": daily_totals,
        "vehicles": [
            {
                "id": v.id,
                "contract_id": v.contract_id,
                "plate_number": v.plate_number,
                "volume_document_m3": float(v.volume_document_m3 or 0),
                "handling_type_code": v.handling_type_code,
                "extra_handling_m3": float(v.extra_handling_m3 or 0),
                "extra_document_set_qty": v.extra_document_set_qty,
                "registered_at": v.registered_at.isoformat() if v.registered_at else None,
                "departed_at": v.departed_at.isoformat() if v.departed_at else None,
            }
            for v in vehicles
        ],
    }


def save_vehicle_row(user: dict, payload: dict) -> dict:
    wh_id = payload.get("warehouse_id")
    wh_ids = user.get("warehouse_ids") or []
    if wh_id not in wh_ids and not user.get("is_admin"):
        return {"error": "forbidden"}
    op_date = date.fromisoformat(str(payload["operation_date"])[:10])
    row_id = payload.get("id")
    if row_id:
        row = db.session.get(VehicleOperation, row_id)
        if not row:
            return {"error": "not_found"}
    else:
        row = VehicleOperation(
            contract_id=payload["contract_id"],
            warehouse_id=wh_id,
            operation_date=op_date,
        )
        db.session.add(row)
    row.plate_number = payload.get("plate_number")
    row.volume_document_m3 = payload.get("volume_document_m3")
    row.handling_type_code = payload.get("handling_type_code")
    row.extra_handling_m3 = payload.get("extra_handling_m3")
    row.extra_document_set_qty = payload.get("extra_document_set_qty")
    row.registered_at = _parse_dt(payload.get("registered_at"))
    row.departed_at = _parse_dt(payload.get("departed_at"))
    db.session.commit()
    return {"id": row.id, "saved": True}


def save_transport_daily(user: dict, payload: dict) -> dict:
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
