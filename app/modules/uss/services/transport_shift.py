"""Транспортная смена: vehicle_operations + суточные допы."""
from __future__ import annotations

from datetime import date, datetime, time

from app.db import db
from app.modules.reference.models import Contract, ProductType
from app.modules.uss.models import VehicleOperation
from app.modules.uss.services.operation_daily_totals import list_daily_totals, upsert_daily_totals
from app.modules.uss.services.report_schema import schema_for_contract_role
from app.modules.uss.services.shift_handling import sync_handling_m3_updates
from app.modules.uss.services.vehicle_plates import combine_vehicle_plates, parse_vehicle_plates

REPORT_ROLE = "transport_logistics"

_VEHICLE_FIELDS = (
    "operation_type_code",
    "tractor_plate",
    "trailer_plate",
    "waybill_number",
    "mx1_number",
    "mx3_number",
    "seal_number",
    "torg2_number",
    "volume_document_m3",
    "handling_type_code",
    "extra_handling_m3",
    "extra_document_set_qty",
)


def _parse_time_on_date(op_date: date, value) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.replace(year=op_date.year, month=op_date.month, day=op_date.day)
    s = str(value).strip()
    if "T" in s:
        return _parse_time_on_date(op_date, datetime.fromisoformat(s.replace("Z", "+00:00")))
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.combine(op_date, datetime.strptime(s[:8], fmt).time())
        except ValueError:
            continue
    return None


def _time_to_str(value: datetime | None) -> str | None:
    if not value:
        return None
    return value.strftime("%H:%M")


def _normalize_operation_type(code: str | None) -> str | None:
    c = (code or "").strip().lower()
    if c in ("inbound", "outbound"):
        return c
    if "приём" in c or "прием" in c:
        return "inbound"
    if "отгруз" in c:
        return "outbound"
    return None


def _normalize_handling(code: str | None) -> str | None:
    c = (code or "").strip().lower()
    if c in ("manual", "mechanized"):
        return c
    if c in ("inbound", "outbound", ""):
        return None
    if "ручн" in c:
        return "manual"
    if "механ" in c:
        return "mechanized"
    return None


def _legacy_fix_operation_handling(row: VehicleOperation) -> tuple[str | None, str | None]:
    """Старые строки: inbound/outbound ошибочно в handling_type_code."""
    op = _normalize_operation_type(row.operation_type_code)
    handling = _normalize_handling(row.handling_type_code)
    if not op and handling is None:
        legacy = _normalize_operation_type(row.handling_type_code)
        if legacy:
            op = legacy
            rq = row.report_quantities or {}
            from app.modules.uss.services.shift_handling import infer_handling_from_volumes

            handling = _normalize_handling(
                infer_handling_from_volumes(
                    rq.get("inbound_manual_m3"),
                    rq.get("inbound_mech_m3"),
                    rq.get("outbound_manual_m3"),
                    rq.get("outbound_mech_m3"),
                )
            ) or None
    return op, handling


def _serialize_vehicle(row: VehicleOperation) -> dict:
    tractor = row.tractor_plate
    trailer = row.trailer_plate
    if not tractor and row.plate_number:
        tractor, trailer = parse_vehicle_plates(row.plate_number)
    op_type, handling = _legacy_fix_operation_handling(row)
    rq = dict(row.report_quantities or {})
    return {
        "id": row.id,
        "contract_id": row.contract_id,
        "plate_number": row.plate_number or combine_vehicle_plates(tractor, trailer),
        "tractor_plate": tractor,
        "trailer_plate": trailer,
        "operation_type_code": op_type or "inbound",
        "waybill_number": row.waybill_number,
        "mx1_number": row.mx1_number,
        "mx3_number": row.mx3_number,
        "seal_number": row.seal_number,
        "torg2_number": row.torg2_number,
        "volume_document_m3": float(row.volume_document_m3 or 0),
        "handling_type_code": handling or "",
        "extra_handling_m3": float(row.extra_handling_m3 or 0),
        "extra_document_set_qty": row.extra_document_set_qty,
        "registered_at": _time_to_str(row.registered_at),
        "departed_at": _time_to_str(row.departed_at),
        "report_quantities": rq,
    }


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
        "vehicles": [_serialize_vehicle(v) for v in vehicles],
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

    for key in _VEHICLE_FIELDS:
        if key in payload:
            val = payload.get(key)
            if key == "handling_type_code":
                val = _normalize_handling(val) or None
            elif key == "operation_type_code":
                val = _normalize_operation_type(val) or "inbound"
            elif key in ("extra_document_set_qty",) and val == "":
                val = None
            setattr(row, key, val)

    row.registered_at = _parse_time_on_date(op_date, payload.get("registered_at"))
    row.departed_at = _parse_time_on_date(op_date, payload.get("departed_at"))
    row.plate_number = combine_vehicle_plates(row.tractor_plate, row.trailer_plate)

    rq = dict(row.report_quantities or {})
    if isinstance(payload.get("report_quantities"), dict):
        for k, v in payload["report_quantities"].items():
            if v not in (None, ""):
                rq[str(k)] = float(v)
    merged = {
        "operation_type_code": row.operation_type_code or "inbound",
        "handling_type_code": row.handling_type_code or "",
        "volume_document_m3": float(row.volume_document_m3 or 0),
    }
    rq.update(sync_handling_m3_updates(merged))
    row.report_quantities = rq

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
