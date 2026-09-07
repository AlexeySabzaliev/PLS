"""API заявок на перевозку (УЗнТ)."""
from __future__ import annotations

from flask import Blueprint, g, request

from app.core.auth import login_required
from app.modules.uznt.services import (
    can_view_requests,
    create_request,
    delete_request,
    get_request,
    list_requests,
    request_meta,
    update_request,
)

bp = Blueprint("uznt_api", __name__, url_prefix="/api/uznt")


def _api_result(result: dict, *, default_status: int = 400) -> tuple[dict, int]:
    if result.get("error") == "forbidden":
        return result, 403
    if result.get("error") == "not_found":
        return result, 404
    if result.get("error") == "validation":
        return result, 422
    if result.get("error"):
        return result, default_status
    return result, 200


@bp.get("/meta")
@login_required
def requests_meta():
    result = request_meta(g.user)
    body, status = _api_result(result)
    return body, status


@bp.get("/requests")
@login_required
def requests_list():
    if not can_view_requests(g.user):
        return {"error": "forbidden", "message": "Нет доступа к разделу «Заявки»"}, 403
    result = list_requests(
        g.user,
        status=request.args.get("status"),
        date_from=request.args.get("date_from"),
        date_to=request.args.get("date_to"),
        client_id=request.args.get("client_id", type=int),
        limit=request.args.get("limit", default=200, type=int),
    )
    body, status = _api_result(result)
    return body, status


@bp.get("/requests/<int:request_id>")
@login_required
def requests_get(request_id: int):
    if not can_view_requests(g.user):
        return {"error": "forbidden", "message": "Нет доступа к разделу «Заявки»"}, 403
    result = get_request(g.user, request_id)
    body, status = _api_result(result)
    return body, status


@bp.post("/requests")
@login_required
def requests_create():
    if not can_view_requests(g.user):
        return {"error": "forbidden", "message": "Нет доступа к разделу «Заявки»"}, 403
    result = create_request(g.user, request.get_json(silent=True) or {})
    body, status = _api_result(result)
    return body, (201 if status == 200 else status)


@bp.put("/requests/<int:request_id>")
@login_required
def requests_update(request_id: int):
    if not can_view_requests(g.user):
        return {"error": "forbidden", "message": "Нет доступа к разделу «Заявки»"}, 403
    result = update_request(g.user, request_id, request.get_json(silent=True) or {})
    body, status = _api_result(result)
    return body, status


@bp.delete("/requests/<int:request_id>")
@login_required
def requests_delete(request_id: int):
    if not can_view_requests(g.user):
        return {"error": "forbidden", "message": "Нет доступа к разделу «Заявки»"}, 403
    result = delete_request(g.user, request_id)
    body, status = _api_result(result)
    return body, status