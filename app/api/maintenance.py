"""API заглушек разделов (admin + проверка)."""
from __future__ import annotations

from flask import Blueprint, g, request

from app.core.auth import login_required
from app.services.maintenance import (
    delete_maintenance,
    get_active_maintenance,
    maintenance_for_user,
    upsert_maintenance,
)

bp = Blueprint("maintenance_api", __name__, url_prefix="/api/maintenance")


def _require_admin():
    if not g.user or not g.user.get("is_admin"):
        return {"error": "forbidden"}, 403
    return None


@bp.get("/active")
@login_required
def active_maintenance():
    return maintenance_for_user(g.user)


@bp.get("")
@login_required
def list_all():
    err = _require_admin()
    if err:
        return err
    return get_active_maintenance()


@bp.post("")
@login_required
def upsert():
    err = _require_admin()
    if err:
        return err
    data = request.get_json(force=True) or {}
    target_type = data.get("target_type")
    target_key = (data.get("target_key") or "").strip()
    message = (data.get("message") or "").strip()
    is_active = bool(data.get("is_active", True))
    if target_type not in ("section", "role") or not target_key or not message:
        return {"error": "invalid_payload"}, 400
    row = upsert_maintenance(
        target_type=target_type,
        target_key=target_key,
        message=message,
        is_active=is_active,
        updated_by=g.user["id"],
    )
    return {
        "id": row.id,
        "target_type": row.target_type,
        "target_key": row.target_key,
        "message": row.message,
        "is_active": row.is_active,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@bp.delete("/<int:item_id>")
@login_required
def remove(item_id: int):
    err = _require_admin()
    if err:
        return err
    if not delete_maintenance(item_id):
        return {"error": "not_found"}, 404
    return {"ok": True}
