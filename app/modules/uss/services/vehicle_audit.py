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
            "user_name": r.user_name,
            "changes": r.changes,
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
