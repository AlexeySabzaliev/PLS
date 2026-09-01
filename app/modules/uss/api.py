"""API операций УСС."""
from __future__ import annotations

from datetime import date

from flask import Blueprint, g, request

from app.core.auth import login_required
from app.core.permissions import user_has_uss_section
from app.modules.uss.services.inventory_shift import get_inventory_shift, save_inventory_shift
from app.modules.uss.services.shift_day_confirm import confirm_day, day_summary
from app.modules.uss.services.transport_shift import list_transport_shift, save_transport_daily, save_vehicle_row
from app.modules.uss.services.warehouse_shift import list_warehouse_shift, save_warehouse_shift

bp = Blueprint("uss_api", __name__, url_prefix="/api/uss")


@bp.get("/transport/shift")
@login_required
def transport_shift_get():
    if not user_has_uss_section(g.user, "uss_ops_transport"):
        return {"error": "forbidden"}, 403
    wh = request.args.get("warehouse_id", type=int)
    day = date.fromisoformat(request.args.get("date", date.today().isoformat()))
    result = list_transport_shift(g.user, wh, day)
    if result.get("error"):
        return result, 403
    return result


@bp.post("/transport/vehicles")
@login_required
def transport_vehicle_save():
    if not user_has_uss_section(g.user, "uss_ops_transport"):
        return {"error": "forbidden"}, 403
    result = save_vehicle_row(g.user, request.get_json(silent=True) or {})
    if result.get("error"):
        return result, 400
    return result


@bp.post("/transport/daily")
@login_required
def transport_daily_save():
    if not user_has_uss_section(g.user, "uss_ops_transport"):
        return {"error": "forbidden"}, 403
    result = save_transport_daily(g.user, request.get_json(silent=True) or {})
    if result.get("error"):
        return result, 400
    return result


@bp.get("/warehouse/shift")
@login_required
def warehouse_shift_get():
    if not user_has_uss_section(g.user, "uss_ops_warehouse"):
        return {"error": "forbidden"}, 403
    wh = request.args.get("warehouse_id", type=int)
    day = date.fromisoformat(request.args.get("date", date.today().isoformat()))
    result = list_warehouse_shift(g.user, wh, day)
    if result.get("error"):
        return result, 403
    return result


@bp.post("/warehouse/shift")
@login_required
def warehouse_shift_save():
    if not user_has_uss_section(g.user, "uss_ops_warehouse"):
        return {"error": "forbidden"}, 403
    result = save_warehouse_shift(g.user, request.get_json(silent=True) or {})
    if result.get("error"):
        return result, 400
    return result


@bp.get("/inventory/shift")
@login_required
def inventory_shift_get():
    if not user_has_uss_section(g.user, "uss_ops_inventory"):
        return {"error": "forbidden"}, 403
    wh = request.args.get("warehouse_id", type=int)
    day = date.fromisoformat(request.args.get("date", date.today().isoformat()))
    result = get_inventory_shift(g.user, wh, day)
    if result.get("error"):
        return result, 403
    return result


@bp.post("/inventory/shift")
@login_required
def inventory_shift_post():
    if not user_has_uss_section(g.user, "uss_ops_inventory"):
        return {"error": "forbidden"}, 403
    result = save_inventory_shift(g.user, request.get_json(silent=True) or {})
    if result.get("error"):
        return result, 400
    return result


@bp.get("/day-summary")
@login_required
def get_day_summary():
    wh = request.args.get("warehouse_id", type=int)
    day = date.fromisoformat(request.args.get("date", date.today().isoformat()))
    return day_summary(wh, day)


@bp.post("/day-confirm")
@login_required
def post_day_confirm():
    data = request.get_json(silent=True) or {}
    wh = data.get("warehouse_id")
    day = date.fromisoformat(str(data.get("report_date", date.today().isoformat()))[:10])
    role = data.get("report_role")
    result = confirm_day(g.user, wh, day, role)
    if result.get("error"):
        return result, 400
    return result
