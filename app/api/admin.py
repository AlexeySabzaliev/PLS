"""API администрирования."""
from __future__ import annotations

from flask import Blueprint, g, request

from app.core.auth import login_required
from app.core.sso_access import (
    approve_sso_request,
    dismiss_sso_request,
    list_pending_sso_requests,
    pending_sso_count,
)

bp = Blueprint("admin_api", __name__, url_prefix="/api/admin")


def _require_admin():
    if not g.user or not g.user.get("is_admin"):
        return {"error": "forbidden"}, 403
    return None


@bp.get("/sso-requests")
@login_required
def get_sso_requests():
    err = _require_admin()
    if err:
        return err
    return {
        "pending_count": pending_sso_count(),
        "items": list_pending_sso_requests(),
    }


@bp.post("/sso-requests/<int:request_id>/approve")
@login_required
def post_sso_approve(request_id: int):
    err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    result = approve_sso_request(request_id, g.user["id"], note=data.get("note"))
    if result.get("error"):
        return result, 404
    return result


@bp.post("/sso-requests/<int:request_id>/dismiss")
@login_required
def post_sso_dismiss(request_id: int):
    err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    result = dismiss_sso_request(request_id, g.user["id"], note=data.get("note"))
    if result.get("error"):
        return result, 404
    return result
