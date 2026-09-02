"""Транспортная смена: vehicle_operations + суточные допы."""
from __future__ import annotations

from datetime import date, datetime

from app.db import db
from app.modules.reference.models import Client, Contract, ProductType, VehicleType, Warehouse
from app.modules.uss.models import VehicleOperation
from app.modules.uss.services.operation_daily_totals import list_daily_totals, upsert_daily_totals
from app.modules.uss.services.report_schema import schema_for_contract_role
from app.modules.uss.services.security_intranet import (
    fetch_all_for_warehouse,
    fetch_vehicle_requests,
    security_status,
)
from app.modules.uss.services.shift_handling import sync_handling_m3_updates
from app.modules.uss.services.transport_waybills import (
    load_waybills_for_operations,
    replace_waybills,
    waybills_from_legacy_row,
)
from app.modules.uss.services.vehicle_plates import combine_vehicle_plates, parse_vehicle_plates

REPORT_ROLE = "transport_logistics"

_VEHICLE_FIELDS = (
    "operation_type_code",
    "tractor_plate",
    "trailer_plate",
    "seal_number",
    "torg2_number",
    "volume_document_m3",
    "handling_type_code",
    "extra_handling_m3",
    "extra_document_set_qty",
    "vehicle_type_id",
)


def _list_vehicle_types() -> list[dict]:
    rows = VehicleType.query.order_by(VehicleType.sort_order, VehicleType.id).all()
    return [
        {
            "id": r.id,
            "code": r.code,
            "name": r.name,
            "dimensions_label": r.dimensions_label,
        }
        for r in rows
    ]


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


def _serialize_vehicle(row: VehicleOperation, waybills_map: dict[int, list[dict]]) -> dict:
    tractor = row.tractor_plate
    trailer = row.trailer_plate
    if not tractor and row.plate_number:
        tractor, trailer = parse_vehicle_plates(row.plate_number)
    op_type, handling = _legacy_fix_operation_handling(row)
    rq = dict(row.report_quantities or {})
    waybills = waybills_map.get(row.id) or waybills_from_legacy_row(row)
    vt = db.session.get(VehicleType, row.vehicle_type_id) if row.vehicle_type_id else None
    return {
        "id": row.id,
        "contract_id": row.contract_id,
        "source": row.source or "manual",
        "plate_number": row.plate_number or combine_vehicle_plates(tractor, trailer),
        "tractor_plate": tractor,
        "trailer_plate": trailer,
        "operation_type_code": op_type or "inbound",
        "vehicle_type_id": row.vehicle_type_id,
        "vehicle_type_name": vt.name if vt else None,
        "dimensions_label": vt.dimensions_label if vt else None,
        "waybills": waybills,
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
    wb_map = load_waybills_for_operations([v.id for v in vehicles])
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
        "vehicle_types": _list_vehicle_types(),
        "security": security_status(),
        "vehicles": [_serialize_vehicle(v, wb_map) for v in vehicles],
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
            source="manual",
        )
        db.session.add(row)

    for key in _VEHICLE_FIELDS:
        if key in payload:
            val = payload.get(key)
            if key == "handling_type_code":
                val = _normalize_handling(val) or None
            elif key == "operation_type_code":
                val = _normalize_operation_type(val) or "inbound"
            elif key == "vehicle_type_id":
                val = int(val) if val not in (None, "", 0, "0") else None
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

    db.session.flush()
    if "waybills" in payload:
        replace_waybills(row.id, payload.get("waybills") or [], row.operation_type_code or "inbound")

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


def _upsert_security_vehicle(
    *,
    contract_id: int,
    warehouse_id: int,
    day: date,
    security_request_id: str,
    vehicle_number: str,
) -> int:
    tractor, trailer = parse_vehicle_plates(vehicle_number)
    combined = combine_vehicle_plates(tractor, trailer) or vehicle_number
    existing = VehicleOperation.query.filter_by(
        contract_id=contract_id,
        operation_date=day,
        security_request_id=security_request_id,
    ).first()
    if existing:
        existing.plate_number = combined
        existing.tractor_plate = tractor
        existing.trailer_plate = trailer
        return existing.id
    row = VehicleOperation(
        contract_id=contract_id,
        warehouse_id=warehouse_id,
        operation_date=day,
        plate_number=combined,
        tractor_plate=tractor,
        trailer_plate=trailer,
        operation_type_code="inbound",
        source="security",
        security_request_id=security_request_id,
    )
    db.session.add(row)
    db.session.flush()
    return row.id


def sync_transport_security(user: dict, warehouse_id: int, day: date) -> dict:
    wh_ids = user.get("warehouse_ids") or []
    if warehouse_id not in wh_ids and not user.get("is_admin"):
        return {"error": "forbidden"}

    contracts = (
        Contract.query.join(Client).join(Warehouse)
        .filter(
            Contract.warehouse_id == warehouse_id,
            Contract.status == "active",
        )
        .all()
    )
    if not contracts:
        return {"synced": 0, "source": "none", "details": []}

    wh = db.session.get(Warehouse, warehouse_id)
    visit_place = wh.security_visit_place if wh else None
    prefetched, fetch_source = fetch_all_for_warehouse(visit_place, day)
    sources: set[str] = {fetch_source}
    total = 0
    details = []

    for contract in contracts:
        client = db.session.get(Client, contract.client_id)
        rows, source = fetch_vehicle_requests(
            client_name=client.name if client else "",
            security_name=client.security_name if client else None,
            visit_place=visit_place,
            day=day,
            prefetched=prefetched,
            fetch_source=fetch_source,
        )
        sources.add(source)
        for item in rows:
            _upsert_security_vehicle(
                contract_id=contract.id,
                warehouse_id=warehouse_id,
                day=day,
                security_request_id=item.request_id,
                vehicle_number=item.vehicle_number,
            )
            total += 1
        details.append({
            "contract_id": contract.id,
            "fetched": len(rows),
        })

    db.session.commit()
    return {
        "synced": total,
        "source": ",".join(sorted(sources)),
        "details": details,
        "security": security_status(),
    }
