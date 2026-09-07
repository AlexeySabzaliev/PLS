"""CRUD заявок на перевозку (УЗнТ).

Раздел прав: `user_has_request_section(user, "requests_transport")` —
просмотр и редактирование; `requests_view_all` — только просмотр.
Админ проходит любую проверку (`permissions._has_section`).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from app.db import db
from app.modules.reference.models import Client, UnitOfMeasure, User, VehicleType, Warehouse
from app.modules.uznt.models import (
    TRANSPORT_REQUEST_PRIORITIES,
    TRANSPORT_REQUEST_PRIORITY_LABELS,
    TRANSPORT_REQUEST_STATUSES,
    TRANSPORT_REQUEST_STATUS_LABELS,
    TransportRequest,
)

# Поля, принимаемые при создании/обновлении.
_EDITABLE_FIELDS = (
    "number",
    "request_date",
    "client_id",
    "warehouse_id",
    "from_location",
    "to_location",
    "cargo_name",
    "cargo_volume_m3",
    "cargo_weight_t",
    "quantity",
    "unit",
    "vehicle_type_id",
    "trucks_count",
    "price",
    "status",
    "priority",
    "notes",
)


def can_view_requests(user: dict | None) -> bool:
    from app.core.permissions import user_has_request_section

    if not user:
        return False
    if user.get("is_admin"):
        return True
    return (
        user_has_request_section(user, "requests_transport")
        or user_has_request_section(user, "requests_view_all")
    )


def can_edit_requests(user: dict | None) -> bool:
    from app.core.permissions import user_has_request_section

    if not user:
        return False
    if user.get("is_admin"):
        return True
    return user_has_request_section(user, "requests_transport")


def _num(value) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _flt(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _serialize(row: TransportRequest) -> dict[str, Any]:
    client = db.session.get(Client, row.client_id) if row.client_id else None
    wh = db.session.get(Warehouse, row.warehouse_id) if row.warehouse_id else None
    vt = db.session.get(VehicleType, row.vehicle_type_id) if row.vehicle_type_id else None
    unit = (
        UnitOfMeasure.query.filter_by(code=row.unit).first() if row.unit else None
    )
    created_by = db.session.get(User, row.created_by) if row.created_by else None
    return {
        "id": row.id,
        "number": row.number,
        "request_date": row.request_date.isoformat() if row.request_date else None,
        "client_id": row.client_id,
        "client_name": client.name if client else None,
        "warehouse_id": row.warehouse_id,
        "warehouse_name": wh.name if wh else None,
        "from_location": row.from_location,
        "to_location": row.to_location,
        "cargo_name": row.cargo_name,
        "cargo_volume_m3": _flt(row.cargo_volume_m3),
        "cargo_weight_t": _flt(row.cargo_weight_t),
        "quantity": _flt(row.quantity),
        "unit": row.unit,
        "unit_label": unit.name if unit else None,
        "vehicle_type_id": row.vehicle_type_id,
        "vehicle_type_name": vt.name if vt else None,
        "trucks_count": row.trucks_count,
        "price": _flt(row.price),
        "status": row.status,
        "status_label": TRANSPORT_REQUEST_STATUS_LABELS.get(row.status, row.status),
        "priority": row.priority,
        "priority_label": TRANSPORT_REQUEST_PRIORITY_LABELS.get(row.priority, row.priority),
        "notes": row.notes,
        "created_by": row.created_by,
        "created_by_name": (created_by.full_name if created_by else None),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
def _next_number(request_date: date) -> str:
    """Автогенерация номера: UZNT-YYYYMMDD-NNNN (01..)."""
    prefix = f'UZNT-{request_date.strftime("%Y%m%d")}-'
    last = (
        TransportRequest.query.filter(TransportRequest.number.like(prefix + "%"))
        .order_by(TransportRequest.number.desc())
        .first()
    )
    seq = 1
    if last and last.number:
        try:
            seq = int(last.number.rsplit("-", 1)[-1]) + 1
        except ValueError:
            seq = 1
    return f"{prefix}{seq:04d}"


def _validate_payload(payload: dict) -> dict[str, str] | None:
    """Базовые проверки. Возвращает {field: message} при ошибке."""
    errors: dict[str, str] = {}

    if "request_date" not in payload or not payload.get("request_date"):
        errors["request_date"] = "Дата заявки обязательна"
    else:
        try:
            parsed = date.fromisoformat(str(payload["request_date"]))
        except ValueError:
            errors["request_date"] = "Неверный формат даты (нужен ГГГГ-ММ-ДД)"
        else:
            payload["request_date"] = parsed

    if payload.get("client_id") is None:
        errors["client_id"] = "Клиент обязателен"
    elif db.session.get(Client, payload["client_id"]) is None:
        errors["client_id"] = "Клиент не найден"

    if payload.get("warehouse_id") is None:
        errors["warehouse_id"] = "Площадка обязательна"
    elif db.session.get(Warehouse, payload["warehouse_id"]) is None:
        errors["warehouse_id"] = "Площадка не найдена"

    status = payload.get("status")
    if status is not None and status not in TRANSPORT_REQUEST_STATUSES:
        errors["status"] = f"Недопустимый статус «{status}»"
    priority = payload.get("priority")
    if priority is not None and priority not in TRANSPORT_REQUEST_PRIORITIES:
        errors["priority"] = f"Недопустимый приоритет «{priority}»"

    if payload.get("vehicle_type_id") is not None and db.session.get(
        VehicleType, payload["vehicle_type_id"]
    ) is None:
        errors["vehicle_type_id"] = "Тип ТС не найден"

    trucks = payload.get("trucks_count")
    if trucks is not None:
        try:
            if int(trucks) < 1:
                errors["trucks_count"] = "Число машин должно быть ≥ 1"
        except (TypeError, ValueError):
            errors["trucks_count"] = "Число машин — целое число"

    return errors or None


def _apply_payload(row: TransportRequest, payload: dict) -> None:
    for field in _EDITABLE_FIELDS:
        if field not in payload:
            continue
        value = payload[field]
        if field in ("cargo_volume_m3", "cargo_weight_t", "quantity", "price"):
            row.__setattr__(field, _num(value))
        elif field == "request_date":
            row.request_date = payload[field]
        elif field in ("client_id", "warehouse_id", "vehicle_type_id", "trucks_count"):
            if value is not None:
                row.__setattr__(field, int(value))
        else:
            row.__setattr__(field, value if value != "" else None)
def list_requests(
    user: dict,
    *,
    status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    client_id: int | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    if not can_view_requests(user):
        return {"error": "forbidden", "message": "Нет доступа к разделу «Заявки»"}

    q = TransportRequest.query

    if status:
        q = q.filter(TransportRequest.status == status)
    if client_id:
        q = q.filter(TransportRequest.client_id == client_id)
    if date_from:
        try:
            q = q.filter(TransportRequest.request_date >= date.fromisoformat(date_from))
        except ValueError:
            return {"error": "invalid_date", "message": "date_from: нужен формат ГГГГ-ММ-ДД"}
    if date_to:
        try:
            q = q.filter(TransportRequest.request_date <= date.fromisoformat(date_to))
        except ValueError:
            return {"error": "invalid_date", "message": "date_to: нужен формат ГГГГ-ММ-ДД"}

    rows = q.order_by(TransportRequest.request_date.desc(), TransportRequest.id.desc()).limit(
        max(1, min(int(limit), 1000))
    ).all()

    return {
        "items": [_serialize(r) for r in rows],
        "total": len(rows),
        "statuses": [
            {"code": s, "label": TRANSPORT_REQUEST_STATUS_LABELS.get(s, s)}
            for s in TRANSPORT_REQUEST_STATUSES
        ],
    }


def get_request(user: dict, request_id: int) -> dict[str, Any]:
    if not can_view_requests(user):
        return {"error": "forbidden", "message": "Нет доступа к разделу «Заявки»"}
    row = db.session.get(TransportRequest, request_id)
    if not row:
        return {"error": "not_found", "message": "Заявка не найдена"}
    return _serialize(row)


def create_request(user: dict, payload: dict) -> dict[str, Any]:
    if not can_edit_requests(user):
        return {"error": "forbidden", "message": "Нет прав на создание заявок"}
    payload = dict(payload or {})

    if payload.get("quantity") is None:
        payload["quantity"] = 1
    if not payload.get("unit"):
        payload["unit"] = "pcs"
    if not payload.get("status"):
        payload["status"] = "new"
    if not payload.get("priority"):
        payload["priority"] = "normal"
    if payload.get("trucks_count") is None:
        payload["trucks_count"] = 1

    errors = _validate_payload(payload)
    if errors:
        return {"error": "validation", "errors": errors}

    request_date: date = payload["request_date"]
    number = (payload.get("number") or "").strip()
    if number:
        dup = TransportRequest.query.filter_by(number=number).first()
        if dup:
            return {"error": "validation", "errors": {"number": "Такой номер уже существует"}}
    else:
        number = _next_number(request_date)

    row = TransportRequest(
        number=number,
        request_date=request_date,
        client_id=int(payload["client_id"]),
        warehouse_id=int(payload["warehouse_id"]),
        status=payload["status"],
        priority=payload["priority"],
        unit=payload["unit"],
        quantity=payload["quantity"],
        trucks_count=payload["trucks_count"],
        created_by=user.get("id"),
        updated_by=user.get("id"),
    )
    db.session.add(row)
    db.session.flush()
    _apply_payload(row, payload)
    db.session.commit()
    return _serialize(row)


def update_request(user: dict, request_id: int, payload: dict) -> dict[str, Any]:
    if not can_edit_requests(user):
        return {"error": "forbidden", "message": "Нет прав на изменение заявок"}
    row = db.session.get(TransportRequest, request_id)
    if not row:
        return {"error": "not_found", "message": "Заявка не найдена"}
    payload = dict(payload or {})

    merged = {field: getattr(row, field) for field in _EDITABLE_FIELDS}
    for field in _EDITABLE_FIELDS:
        if field in payload:
            merged[field] = payload[field]
    if merged.get("quantity") is None:
        merged["quantity"] = 1
    if merged.get("trucks_count") is None:
        merged["trucks_count"] = 1

    errors = _validate_payload(merged)
    if errors:
        return {"error": "validation", "errors": errors}

    number = (merged.get("number") or "").strip()
    if number and number != row.number:
        dup = TransportRequest.query.filter(
            TransportRequest.number == number, TransportRequest.id != request_id
        ).first()
        if dup:
            return {"error": "validation", "errors": {"number": "Такой номер уже существует"}}
        row.number = number

    row.client_id = int(merged["client_id"])
    row.warehouse_id = int(merged["warehouse_id"])
    _apply_payload(row, merged)
    row.updated_by = user.get("id")
    db.session.commit()
    return _serialize(row)


def delete_request(user: dict, request_id: int) -> dict[str, Any]:
    if not can_edit_requests(user):
        return {"error": "forbidden", "message": "Нет прав на удаление заявок"}
    row = db.session.get(TransportRequest, request_id)
    if not row:
        return {"error": "not_found", "message": "Заявка не найдена"}
    serialized = _serialize(row)
    db.session.delete(row)
    db.session.commit()
    return {"deleted_id": request_id, "number": serialized["number"]}
def request_meta(user: dict) -> dict[str, Any]:
    """Справочные списки для формы заявки (без раздела «Справочники»)."""
    if not can_view_requests(user):
        return {"error": "forbidden", "message": "Нет доступа к разделу «Заявки»"}

    def _pick(rows, name_attr="name"):
        return [{"id": r.id, "name": getattr(r, name_attr)} for r in rows]

    clients = Client.query.filter_by(is_active=True).order_by(Client.name).all()
    warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.name).all()
    vehicle_types = VehicleType.query.order_by(VehicleType.sort_order, VehicleType.id).all()
    units = UnitOfMeasure.query.filter_by(is_active=True).order_by(UnitOfMeasure.name).all()

    return {
        "clients": _pick(clients),
        "warehouses": _pick(warehouses),
        "vehicle_types": [
            {
                "id": v.id,
                "name": v.name,
                "dimensions_label": v.dimensions_label,
            }
            for v in vehicle_types
        ],
        "units": [{"code": u.code, "name": u.name} for u in units],
        "priorities": [
            {"code": c, "label": TRANSPORT_REQUEST_PRIORITY_LABELS.get(c, c)}
            for c in TRANSPORT_REQUEST_PRIORITIES
        ],
    }