"""Накладные по строке ТС (несколько на одну машину)."""
from __future__ import annotations

from app.db import db
from app.modules.uss.models import VehicleOperation, VehicleWaybill


def _serialize_waybill(row: VehicleWaybill) -> dict:
    return {
        "id": row.id,
        "waybill_number": row.waybill_number or "",
        "mx_number": row.mx_number or "",
        "sort_order": row.sort_order,
    }


def load_waybills_for_operations(operation_ids: list[int]) -> dict[int, list[dict]]:
    if not operation_ids:
        return {}
    rows = (
        VehicleWaybill.query.filter(VehicleWaybill.vehicle_operation_id.in_(operation_ids))
        .order_by(VehicleWaybill.vehicle_operation_id, VehicleWaybill.sort_order, VehicleWaybill.id)
        .all()
    )
    out: dict[int, list[dict]] = {}
    for row in rows:
        out.setdefault(row.vehicle_operation_id, []).append(_serialize_waybill(row))
    return out


def waybills_from_legacy_row(row: VehicleOperation) -> list[dict]:
    """Одна накладная из денормализованных полей (до миграции / импорт Excel)."""
    wb = (row.waybill_number or "").strip()
    if not wb:
        return []
    op = (row.operation_type_code or "inbound").strip()
    mx = row.mx3_number if op == "outbound" else row.mx1_number
    return [{"waybill_number": wb, "mx_number": (mx or "").strip()}]


def replace_waybills(
    operation_id: int,
    waybills: list[dict],
    operation_type_code: str,
) -> list[dict]:
    """Заменить накладные строки и синхронизировать primary waybill/mx на vehicle_operations."""
    row = db.session.get(VehicleOperation, operation_id)
    if not row:
        return []

    VehicleWaybill.query.filter_by(vehicle_operation_id=operation_id).delete(synchronize_session=False)
    saved: list[dict] = []
    primary_waybill = None
    primary_mx1 = None
    primary_mx3 = None

    for idx, wb in enumerate(waybills or []):
        number = (wb.get("waybill_number") or "").strip() or None
        mx = (wb.get("mx_number") or "").strip() or None
        if not number and not mx:
            continue
        item = VehicleWaybill(
            vehicle_operation_id=operation_id,
            waybill_number=number,
            mx_number=mx,
            sort_order=idx,
        )
        db.session.add(item)
        db.session.flush()
        saved.append(_serialize_waybill(item))
        if primary_waybill is None and number:
            primary_waybill = number
            if operation_type_code == "inbound":
                primary_mx1 = mx
            else:
                primary_mx3 = mx

    row.waybill_number = primary_waybill
    row.mx1_number = primary_mx1
    row.mx3_number = primary_mx3
    return saved
