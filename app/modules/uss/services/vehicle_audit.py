"""Журнал изменений строк ТС."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.db import db
from app.modules.uss.models import VehicleOperation, VehicleOperationAuditLog


def _user_label(user: dict | None) -> str | None:
    if not user:
        return None
    return (user.get("full_name") or "").strip() or user.get("email")


def _serialize_row_snapshot(row: VehicleOperation) -> dict[str, Any]:
    return {
        "id": row.id,
        "contract_id": row.contract_id,
        "warehouse_id": row.warehouse_id,
        "operation_date": row.operation_date.isoformat() if row.operation_date else None,
        "tractor_plate": row.tractor_plate,
        "trailer_plate": row.trailer_plate,
        "operation_type_code": row.operation_type_code,
        "arrival_status": row.arrival_status,
        "registered_at": row.registered_at.isoformat() if row.registered_at else None,
        "departed_at": row.departed_at.isoformat() if row.departed_at else None,
        "processed_by": row.processed_by,
        "processed_at": row.processed_at.isoformat() if row.processed_at else None,
        "source": row.source,
        "security_request_id": row.security_request_id,
        "report_quantities": dict(row.report_quantities or {}),
    }


def _diff(before: dict[str, Any] | None, after: dict[str, Any]) -> dict[str, dict[str, Any]]:
    before = before or {}
    changes: dict[str, dict[str, Any]] = {}
    keys = set(before) | set(after)
    for key in keys:
        old = before.get(key)
        new = after.get(key)
        if old != new:
            changes[key] = {"old": old, "new": new}
    return changes


def log_vehicle_change(
    row: VehicleOperation,
    *,
    user: dict | None,
    action: str,
    before: dict[str, Any] | None = None,
) -> None:
    after = _serialize_row_snapshot(row)
    entry = VehicleOperationAuditLog(
        vehicle_operation_id=row.id,
        user_id=user.get("id") if user else None,
        user_name=_user_label(user),
        action=action,
        changes=_diff(before, after) if before is not None else None,
        snapshot=after,
    )
    db.session.add(entry)


def list_vehicle_audit(vehicle_id: int, *, limit: int = 50) -> list[dict]:
    rows = (
        VehicleOperationAuditLog.query.filter_by(vehicle_operation_id=vehicle_id)
        .order_by(VehicleOperationAuditLog.created_at.desc(), VehicleOperationAuditLog.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "action": r.action,
            "action_label": ACTION_LABELS.get(r.action, r.action),
            "user_name": r.user_name,
            "changes": r.changes,
            "changes_display": format_changes_for_ui(r.changes),
            "summary": action_summary(r.action, r.snapshot),
            "snapshot": r.snapshot,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


ACTION_LABELS = {
    "create": "Создание",
    "update": "Изменение",
    "complete": "Обработка завершена",
    "no_show": "Не прибыл",
    "sync_security": "Загрузка с охраны",
    "reopen": "Снята отметка обработки",
}

FIELD_LABELS = {
    "tractor_plate": "Тягач",
    "trailer_plate": "Прицеп",
    "operation_type_code": "Операция",
    "arrival_status": "Статус приезда",
    "registered_at": "Прибытие",
    "departed_at": "Убытие",
    "handling_type_code": "Тип обработки",
    "volume_document_m3": "Объём по документам, м³",
    "seal_number": "Пломба",
    "torg2_number": "ТОРГ-2",
    "vehicle_type_id": "Тип ТС",
    "extra_document_set_qty": "Комплект документов",
    "source": "Источник",
    "report_quantities": "Тарифные поля",
}

OPERATION_LABELS = {"inbound": "Приём", "outbound": "Отгрузка"}
ARRIVAL_LABELS = {"expected": "Ожидается", "arrived": "Прибыл", "no_show": "Не прибыл"}
HANDLING_LABELS = {"manual": "Ручная", "mechanized": "Механизированная"}


def _empty_label(value: Any) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _format_scalar(key: str, value: Any) -> str:
    if value is None or value == "":
        return "—"
    if key == "operation_type_code":
        return OPERATION_LABELS.get(str(value), str(value))
    if key == "arrival_status":
        return ARRIVAL_LABELS.get(str(value), str(value))
    if key == "handling_type_code":
        return HANDLING_LABELS.get(str(value), str(value))
    if key in ("registered_at", "departed_at", "processed_at", "operation_date") and isinstance(value, str):
        return value.replace("T", " ")[:16]
    if isinstance(value, dict):
        if not value:
            return "пусто"
        return "; ".join(f"{k}: {v}" for k, v in sorted(value.items()))
    return str(value)


def _expand_report_quantities(old: Any, new: Any) -> list[dict[str, str]]:
    old_map = dict(old or {})
    new_map = dict(new or {})
    rows: list[dict[str, str]] = []
    for code in sorted(set(old_map) | set(new_map)):
        ov = old_map.get(code)
        nv = new_map.get(code)
        if ov != nv:
            rows.append({
                "field": code,
                "label": code,
                "old": _empty_label(ov),
                "new": _empty_label(nv),
            })
    return rows


def format_changes_for_ui(changes: dict[str, dict[str, Any]] | None) -> list[dict[str, str]]:
    """Человекочитаемый список изменений для UI."""
    if not changes:
        return []
    items: list[dict[str, str]] = []
    for key, pair in changes.items():
        old = pair.get("old")
        new = pair.get("new")
        if key == "report_quantities":
            items.extend(_expand_report_quantities(old, new))
            continue
        if old == new:
            continue
        items.append({
            "field": key,
            "label": FIELD_LABELS.get(key, key),
            "old": _format_scalar(key, old),
            "new": _format_scalar(key, new),
        })
    return items


def action_summary(action: str, snapshot: dict[str, Any] | None) -> str | None:
    snap = snapshot or {}
    if action == "create":
        plate = snap.get("tractor_plate") or "без номера"
        op = OPERATION_LABELS.get(snap.get("operation_type_code") or "", "—")
        return f"Создана строка: {plate}, {op}"
    if action == "no_show":
        return "ТС отмечено как не прибывшее"
    if action == "complete":
        return "Строка полностью заполнена и обработана"
    if action == "sync_security":
        plate = snap.get("tractor_plate") or "без номера"
        return f"Загружено с охраны: {plate}"
    if action == "reopen":
        return "Снята отметка об обработке — требуется дозаполнение"
    return None
