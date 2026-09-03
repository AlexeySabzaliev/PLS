"""API операций УСС."""
from __future__ import annotations

from datetime import date

from flask import Blueprint, g, request

from app.core.auth import login_required
from app.core.permissions import user_has_uss_section
from app.db import db
from app.modules.reference.models import Warehouse
from app.modules.uss.services.fot_efficiency import build_fot_report
from app.modules.uss.services.inventory_shift import get_inventory_shift, save_inventory_shift
from app.modules.uss.services.report_schema import schema_for_contract_role
from app.modules.uss.services.shift_day_confirm import confirm_day, day_summary
from app.modules.uss.services.transport_shift import (
    list_transport_shift,
    save_transport_daily,
    save_vehicle_row,
    sync_transport_security,
)
from app.modules.uss.services.security_intranet import security_status
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


def _api_result(result: dict, *, default_status: int = 400) -> tuple[dict, int]:
    if result.get("error") == "period_locked":
        return result, 409
    if result.get("error"):
        return result, default_status
    return result, 200


@bp.post("/transport/vehicles")
@login_required
def transport_vehicle_save():
    if not user_has_uss_section(g.user, "uss_ops_transport"):
        return {"error": "forbidden"}, 403
    result = save_vehicle_row(g.user, request.get_json(silent=True) or {})
    body, status = _api_result(result)
    return body, status


@bp.post("/transport/daily")
@login_required
def transport_daily_save():
    if not user_has_uss_section(g.user, "uss_ops_transport"):
        return {"error": "forbidden"}, 403
    result = save_transport_daily(g.user, request.get_json(silent=True) or {})
    body, status = _api_result(result)
    return body, status


@bp.post("/transport/sync-security")
@login_required
def transport_sync_security():
    if not user_has_uss_section(g.user, "uss_ops_transport"):
        return {"error": "forbidden"}, 403
    data = request.get_json(silent=True) or {}
    wh = data.get("warehouse_id") or request.args.get("warehouse_id", type=int)
    day = date.fromisoformat(str(data.get("date") or request.args.get("date", date.today().isoformat()))[:10])
    result = sync_transport_security(g.user, wh, day)
    if result.get("error"):
        return result, 403
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
    body, status = _api_result(result)
    return body, status


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
    body, status = _api_result(result)
    return body, status


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
    body, status = _api_result(result)
    return body, status


@bp.get("/report-schema")
@login_required
def get_report_schema():
    """Схема полей по договору и роли (из tariff_rules)."""
    contract_id = request.args.get("contract_id", type=int)
    amendment_id = request.args.get("amendment_id", type=int)
    role = request.args.get("role", "transport_logistics")
    on_date = date.fromisoformat(request.args.get("date", date.today().isoformat()))
    if not contract_id:
        return {"error": "contract_id_required"}, 400
    if role == "transport_logistics" and not user_has_uss_section(g.user, "uss_ops_transport"):
        return {"error": "forbidden"}, 403
    if role == "warehouse_logistics" and not user_has_uss_section(g.user, "uss_ops_warehouse"):
        return {"error": "forbidden"}, 403
    if role == "inventory_management" and not user_has_uss_section(g.user, "uss_ops_inventory"):
        return {"error": "forbidden"}, 403
    return schema_for_contract_role(contract_id, on_date, role, amendment_id=amendment_id)


@bp.get("/context")
@login_required
def shift_context():
    """Склады и договоры для UI смен."""
    from app.modules.reference.models import Warehouse
    from app.modules.uss.services.shift_contracts import (
        contracts_for_inventory_shift,
        contracts_for_transport_shift,
        contracts_for_warehouse_shift,
        serialize_contracts,
        shift_date_bounds,
    )

    role = request.args.get("role", "transport_logistics")
    wh_id = request.args.get("warehouse_id", type=int)
    day = date.fromisoformat(request.args.get("date", date.today().isoformat()))

    if g.user.get("is_admin"):
        warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.code).all()
    else:
        wh_ids = g.user.get("warehouse_ids") or []
        warehouses = Warehouse.query.filter(Warehouse.id.in_(wh_ids), Warehouse.is_active.is_(True)).all()

    if not warehouses:
        return {"error": "no_warehouses"}, 403

    if wh_id is None:
        wh_id = warehouses[0].id
    elif not g.user.get("is_admin") and wh_id not in (g.user.get("warehouse_ids") or []):
        return {"error": "forbidden"}, 403

    if role == "warehouse_logistics":
        contracts = contracts_for_warehouse_shift(wh_id, day)
    elif role == "inventory_management":
        contracts = contracts_for_inventory_shift(wh_id, day)
    else:
        contracts = contracts_for_transport_shift(wh_id, day)
    wh = db.session.get(Warehouse, wh_id)
    min_date, max_date = shift_date_bounds()
    return {
        "role": role,
        "date": day.isoformat(),
        "today": date.today().isoformat(),
        "min_date": min_date,
        "max_date": max_date,
        "warehouse_id": wh_id,
        "warehouses": [{"id": w.id, "code": w.code, "name": w.name} for w in warehouses],
        "contracts": serialize_contracts(contracts, day),
        "security": security_status(),
        "security_visit_place": wh.security_visit_place if wh else None,
    }


def _report_warehouses():
    if g.user.get("is_admin"):
        return Warehouse.query.filter_by(is_active=True).order_by(Warehouse.code).all()
    wh_ids = g.user.get("warehouse_ids") or []
    return Warehouse.query.filter(Warehouse.id.in_(wh_ids), Warehouse.is_active.is_(True)).all()


def _can_access_warehouse(warehouse_id: int) -> bool:
    if g.user.get("is_admin"):
        return True
    return warehouse_id in (g.user.get("warehouse_ids") or [])


@bp.get("/reports/fot")
@login_required
def fot_report():
    """Отчёт ФОТ vs операционка по складу и месяцу."""
    if not user_has_uss_section(g.user, "uss_reports"):
        return {"error": "forbidden"}, 403

    warehouse_id = request.args.get("warehouse_id", type=int)
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)
    if not warehouse_id or not year or not month:
        return {"error": "missing_params", "message": "warehouse_id, year и month обязательны"}, 400
    if month < 1 or month > 12:
        return {"error": "invalid_month"}, 400
    if not _can_access_warehouse(warehouse_id):
        return {"error": "forbidden"}, 403

    warehouses = _report_warehouses()
    if not warehouses:
        return {"error": "no_warehouses"}, 403

    contract_id = request.args.get("contract_id", type=int)
    report = build_fot_report(warehouse_id, year, month, contract_id=contract_id)
    report["warehouses"] = [{"id": w.id, "code": w.code, "name": w.name} for w in warehouses]
    return report
