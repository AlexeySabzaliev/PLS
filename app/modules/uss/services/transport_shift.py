"""Ежесменный отчёт транспортной логистики: vehicle_operations + суточные допы."""
from __future__ import annotations

from datetime import date, datetime

from app.db import db
from app.modules.billing.period_lock import (
    PeriodLockedError,
    assert_operations_editable,
    periods_status_for_contracts,
)
from app.modules.reference.models import Client, Contract, ProductType, User, VehicleType, Warehouse
from app.modules.uss.services.shift_contracts import (
    contracts_for_transport_shift,
    serialize_primary_shift_blocks,
    shift_date_bounds,
)
from app.modules.uss.models import VehicleOperation
from app.modules.uss.services.operation_daily_totals import list_daily_totals, upsert_daily_totals
from app.modules.uss.services.report_schema import schema_for_contract_role
from app.modules.uss.services.security_intranet import (
    _use_mock,
    fetch_all_for_warehouse,
    fetch_vehicle_requests,
    is_demo_security_vehicle,
    purge_demo_security_vehicles,
    security_status,
)
from app.modules.uss.services.security_session import security_refresh_hint
from app.modules.uss.services.shift_handling import sync_handling_m3_updates
from app.modules.uss.services.transport_waybills import (
    load_waybills_for_operations,
    replace_waybills,
    waybills_from_legacy_row,
)
from app.modules.uss.services.overtime import row_is_overtime
from app.modules.uss.services.vehicle_audit import (
    ACTION_LABELS,
    _serialize_row_snapshot,
    list_vehicle_audit,
    log_vehicle_change,
)
from app.modules.uss.services.vehicle_validation import (
    ARRIVAL_NO_SHOW,
    is_row_complete,
    missing_required_fields,
    row_field_values,
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


def _processed_by_name(user_id: int | None) -> str | None:
    if not user_id:
        return None
    user = db.session.get(User, user_id)
    if not user:
        return None
    return (user.full_name or "").strip() or user.email


def _apply_completion_state(row: VehicleOperation, values: dict, user: dict | None) -> str:
    """Обновить processed_by/at по заполненности. Возвращает action для журнала."""
    was_complete = bool(row.processed_at)
    if values.get("arrival_status") == ARRIVAL_NO_SHOW:
        if not row.processed_at:
            row.processed_by = user.get("id") if user else None
            row.processed_at = datetime.utcnow()
            return "no_show"
        return "update"
    if is_row_complete(values):
        if not row.processed_at:
            row.processed_by = user.get("id") if user else None
            row.processed_at = datetime.utcnow()
            return "complete"
        return "update"
    if row.processed_at:
        row.processed_by = None
        row.processed_at = None
        return "reopen"
    return "update"


def _serialize_vehicle(row: VehicleOperation, waybills_map: dict[int, list[dict]]) -> dict:
    tractor = row.tractor_plate
    trailer = row.trailer_plate
    if not tractor and row.plate_number:
        tractor, trailer = parse_vehicle_plates(row.plate_number)
    op_type, handling = _legacy_fix_operation_handling(row)
    rq = dict(row.report_quantities or {})
    waybills = waybills_map.get(row.id) or waybills_from_legacy_row(row)
    vt = db.session.get(VehicleType, row.vehicle_type_id) if row.vehicle_type_id else None
    values = row_field_values(row)
    missing = missing_required_fields(values)
    complete = is_row_complete(values)
    return {
        "id": row.id,
        "contract_id": row.contract_id,
        "source": row.source or "manual",
        "arrival_status": row.arrival_status or "expected",
        "is_complete": complete,
        "missing_fields": missing,
        "processed_by": row.processed_by,
        "processed_by_name": _processed_by_name(row.processed_by),
        "processed_at": row.processed_at.isoformat() if row.processed_at else None,
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
        "is_overtime": row_is_overtime(
            row.operation_date,
            departed_at=row.departed_at,
            warehouse_id=row.warehouse_id,
        ),
        "report_quantities": rq,
    }


def _dedupe_vehicle_rows(vehicles: list[VehicleOperation]) -> list[VehicleOperation]:
    """Скрыть дубликаты импорта: одна строка на security_request_id или пару тягач/прицеп."""
    kept: dict[tuple, VehicleOperation] = {}
    for row in sorted(vehicles, key=lambda v: v.id, reverse=True):
        key = (
            row.contract_id,
            (row.security_request_id or "").strip(),
            (row.tractor_plate or "").strip(),
            (row.trailer_plate or "").strip(),
            (row.plate_number or "").strip(),
        )
        if key in kept:
            continue
        kept[key] = row
    return sorted(kept.values(), key=lambda v: v.id)


def list_transport_shift(user: dict, warehouse_id: int, day: date) -> dict:
    wh_ids = user.get("warehouse_ids") or []
    if warehouse_id not in wh_ids and not user.get("is_admin"):
        return {"error": "forbidden"}
    contracts = contracts_for_transport_shift(warehouse_id, day)
    blocks = serialize_primary_shift_blocks(contracts, day)
    vehicles = _dedupe_vehicle_rows(
        VehicleOperation.query.filter_by(
            warehouse_id=warehouse_id,
            operation_date=day,
        ).order_by(VehicleOperation.id).all()
    )
    if not _use_mock():
        vehicles = [
            v for v in vehicles
            if not is_demo_security_vehicle(
                security_request_id=v.security_request_id,
                tractor_plate=v.tractor_plate,
                plate_number=v.plate_number,
            )
        ]
    wb_map = load_waybills_for_operations([v.id for v in vehicles])
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
    contract_ids = list({b["contract_id"] for b in blocks})
    daily_totals = {
        str(cid): list_daily_totals(cid, warehouse_id, day) for cid in contract_ids
    }
    period_locks = periods_status_for_contracts(contract_ids, day.year, day.month)
    min_date, max_date = shift_date_bounds()
    wh = db.session.get(Warehouse, warehouse_id) if warehouse_id else None
    return {
        "warehouse_id": warehouse_id,
        "operation_date": day.isoformat(),
        "report_role": REPORT_ROLE,
        "contracts": blocks,
        "today": date.today().isoformat(),
        "min_date": min_date,
        "max_date": max_date,
        "schemas": schemas,
        "daily_totals": daily_totals,
        "period_locks": {str(k): v for k, v in period_locks.items()},
        "vehicle_types": _list_vehicle_types(),
        "security": security_status(),
        "security_visit_place": wh.security_visit_place if wh else None,
        "vehicles": [_serialize_vehicle(v, wb_map) for v in vehicles],
    }


def save_vehicle_row(user: dict, payload: dict) -> dict:
    wh_id = payload.get("warehouse_id")
    wh_ids = user.get("warehouse_ids") or []
    if wh_id not in wh_ids and not user.get("is_admin"):
        return {"error": "forbidden"}
    op_date = date.fromisoformat(str(payload["operation_date"])[:10])
    try:
        assert_operations_editable(user, int(payload["contract_id"]), op_date)
    except PeriodLockedError as exc:
        return {"error": "period_locked", "message": str(exc)}
    row_id = payload.get("id")
    before_snapshot = None
    if row_id:
        row = db.session.get(VehicleOperation, row_id)
        if not row:
            return {"error": "not_found"}
        before_snapshot = _serialize_row_snapshot(row)
    else:
        row = VehicleOperation(
            contract_id=payload["contract_id"],
            warehouse_id=wh_id,
            operation_date=op_date,
            source="manual",
            arrival_status="expected",
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

    if "arrival_status" in payload and payload["arrival_status"] != ARRIVAL_NO_SHOW:
        row.arrival_status = payload["arrival_status"]

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

    values = row_field_values(row)
    audit_action = _apply_completion_state(row, values, user)
    if before_snapshot is None:
        audit_action = "create"
    log_vehicle_change(row, user=user, action=audit_action, before=before_snapshot)

    db.session.commit()
    wb_map = load_waybills_for_operations([row.id])
    return {"id": row.id, "saved": True, "vehicle": _serialize_vehicle(row, wb_map)}


def mark_vehicle_no_show(user: dict, vehicle_id: int) -> dict:
    row = db.session.get(VehicleOperation, vehicle_id)
    if not row:
        return {"error": "not_found"}
    wh_ids = user.get("warehouse_ids") or []
    if row.warehouse_id not in wh_ids and not user.get("is_admin"):
        return {"error": "forbidden"}
    try:
        assert_operations_editable(user, row.contract_id, row.operation_date)
    except PeriodLockedError as exc:
        return {"error": "period_locked", "message": str(exc)}
    before = _serialize_row_snapshot(row)
    row.arrival_status = ARRIVAL_NO_SHOW
    row.processed_by = user.get("id")
    row.processed_at = datetime.utcnow()
    log_vehicle_change(row, user=user, action="no_show", before=before)
    db.session.commit()
    wb_map = load_waybills_for_operations([row.id])
    return {"ok": True, "vehicle": _serialize_vehicle(row, wb_map)}


def get_vehicle_audit_log(user: dict, vehicle_id: int) -> dict:
    row = db.session.get(VehicleOperation, vehicle_id)
    if not row:
        return {"error": "not_found"}
    wh_ids = user.get("warehouse_ids") or []
    if row.warehouse_id not in wh_ids and not user.get("is_admin"):
        return {"error": "forbidden"}
    items = list_vehicle_audit(vehicle_id)
    for item in items:
        item["action_label"] = ACTION_LABELS.get(item["action"], item["action"])
    return {"items": items, "action_labels": ACTION_LABELS}


def save_transport_daily(user: dict, payload: dict) -> dict:
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
        arrival_status="expected",
    )
    db.session.add(row)
    db.session.flush()
    log_vehicle_change(row, user=None, action="sync_security", before=None)
    return row.id


def sync_transport_security(user: dict, warehouse_id: int, day: date) -> dict:
    wh_ids = user.get("warehouse_ids") or []
    if warehouse_id not in wh_ids and not user.get("is_admin"):
        return {"error": "forbidden", "message": "Нет доступа к этому складу"}

    contracts = contracts_for_transport_shift(warehouse_id, day)
    if not contracts:
        return {
            "synced": 0,
            "source": "none",
            "details": [],
            "message": "Нет активных договоров ОХ на складе — синхронизация с охраной невозможна",
            "security": security_status(),
        }

    wh = db.session.get(Warehouse, warehouse_id)
    visit_place = wh.security_visit_place if wh else None
    purged_demo = 0
    if not _use_mock():
        purged_demo = purge_demo_security_vehicles(warehouse_id, day)
    prefetched, fetch_source = fetch_all_for_warehouse(visit_place, day)
    sources: set[str] = {fetch_source}
    total = 0
    details = []
    warnings: list[str] = []
    parse_stats: dict = {}

    if not visit_place and fetch_source not in ("mock", "stub", "mock_fallback"):
        warnings.append(
            "Не задано «Место визита СБ» у склада — в портале может быть слишком много заявок "
            "или фильтр не сработает. Укажите значение в справочнике «Склады»."
        )

    assigned_requests: set[str] = set()
    for contract in contracts:
        client = db.session.get(Client, contract.client_id)
        contract_stats: dict = {}
        rows, source = fetch_vehicle_requests(
            client_name=client.name if client else "",
            security_name=client.security_name if client else None,
            visit_place=visit_place,
            day=day,
            prefetched=prefetched,
            fetch_source=fetch_source,
            stats=contract_stats,
        )
        sources.add(source)
        details.append({
            "contract_id": contract.id,
            "client_name": client.name if client else None,
            "synced": len(rows),
            "source": source,
        })
        # #endregion
        skipped = contract_stats.get("skipped_no_plate", 0)
        if skipped:
            parse_stats[str(contract.id)] = contract_stats
            samples = contract_stats.get("skipped_samples") or []
            sample_txt = "; ".join(samples[:3])
            warnings.append(
                f"Клиент «{client.name if client else contract.id}»: {skipped} заявок без "
                f"распознанного госномера"
                + (f" (например: {sample_txt})" if sample_txt else "")
            )
        for item in rows:
            if not _use_mock() and (
                is_demo_security_vehicle(security_request_id=item.request_id, tractor_plate=item.vehicle_number)
            ):
                continue
            if item.request_id in assigned_requests:
                continue
            _upsert_security_vehicle(
                contract_id=contract.id,
                warehouse_id=warehouse_id,
                day=day,
                security_request_id=item.request_id,
                vehicle_number=item.vehicle_number,
            )
            assigned_requests.add(item.request_id)
            total += 1
        details.append({
            "contract_id": contract.id,
            "client_name": client.name if client else "",
            "fetched": len(rows),
            "skipped_no_plate": skipped,
        })

    db.session.commit()

    message = None
    if total == 0:
        if "unauthorized" in sources or "no_auth" in sources:
            message = security_refresh_hint()
        elif "stub" in sources:
            message = "Режим заглушки SECURITY_PORTAL_STUB — демо-заявки без портала."
        else:
            message = (
                f"Заявок в портале: {len(prefetched)}, подходящих по клиенту и складу: 0. "
                "Проверьте имя клиента и «Место визита СБ» у склада."
            )
    elif "live" in sources or "live+cache" in sources:
        if total == 0:
            message = (
                f"Заявок в портале: {len(prefetched)}, подходящих по клиенту и складу: 0. "
                "Проверьте имя клиента и «Место визита СБ» у склада."
            )
        elif "live+cache" in sources:
            message = "Данные загружены с портала и сохранены в локальный кэш для тестов."
    elif "mock_fallback" in sources or "stub" in sources:
        message = "Загружены демо-данные охраны (портал недоступен или включена заглушка)."

    return {
        "synced": total,
        "source": ",".join(sorted(sources)),
        "raw_rows": len(prefetched),
        "purged_demo": purged_demo,
        "details": details,
        "warnings": warnings,
        "parse_stats": parse_stats,
        "message": message,
        "security": security_status(),
    }
