"""API биллинга."""
from __future__ import annotations

from datetime import date

from flask import Blueprint, g, request, send_file
import io

from app.core.auth import login_required, edit_required
from app.core.permissions import user_has_uss_section
from app.db import db
from app.modules.billing.calculator import BillingCalculator
from app.modules.billing.excel_export import build_billing_workbook
from app.modules.billing.period_lock import (
    PeriodLockedError,
    assert_billing_calculable,
    get_period,
    lock_period,
    period_status_dict,
    unlock_period,
    upsert_period_total,
)
from app.modules.reference.models import Contract, ProductType, Warehouse

bp = Blueprint("billing_api", __name__, url_prefix="/api/billing")

_FORBIDDEN = {"error": "forbidden", "message": "Нет доступа к разделу «Биллинг»"}
_NO_WAREHOUSES = {"error": "no_warehouses", "message": "Нет доступных складов для вашего пользователя"}


def _billing_warehouses():
    if g.user.get("is_admin"):
        return Warehouse.query.filter_by(is_active=True).order_by(Warehouse.code).all()
    wh_ids = g.user.get("warehouse_ids") or []
    return Warehouse.query.filter(Warehouse.id.in_(wh_ids), Warehouse.is_active.is_(True)).all()


@bp.get("/context")
@login_required
def billing_context():
    """Склады и договоры ОХ для UI расчёта биллинга."""
    if not user_has_uss_section(g.user, "uss_billing"):
        return _FORBIDDEN, 403

    wh_id = request.args.get("warehouse_id", type=int)
    warehouses = _billing_warehouses()
    if not warehouses:
        return _NO_WAREHOUSES, 403

    if wh_id is None:
        wh_id = warehouses[0].id
    elif not g.user.get("is_admin") and wh_id not in (g.user.get("warehouse_ids") or []):
        return {"error": "forbidden"}, 403

    contracts = (
        Contract.query.join(ProductType)
        .filter(
            Contract.warehouse_id == wh_id,
            Contract.status == "active",
            ProductType.code == "RESPONSIBLE_STORAGE",
        )
        .order_by(Contract.number)
        .all()
    )
    return {
        "warehouse_id": wh_id,
        "warehouses": [{"id": w.id, "code": w.code, "name": w.name} for w in warehouses],
        "contracts": [{"id": c.id, "number": c.number} for c in contracts],
        "is_admin": bool(g.user.get("is_admin")),
    }


@bp.get("/period")
@login_required
def billing_period_get():
    if not user_has_uss_section(g.user, "uss_billing"):
        return _FORBIDDEN, 403
    contract_id = request.args.get("contract_id", type=int)
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)
    if not contract_id or not year or not month:
        return {"error": "missing_params"}, 400
    period = get_period(contract_id, year, month)
    return {
        "contract_id": contract_id,
        "period_year": year,
        "period_month": month,
        **period_status_dict(period),
    }


@bp.post("/period/lock")
@login_required
@edit_required
def billing_period_lock():
    if not user_has_uss_section(g.user, "uss_billing"):
        return _FORBIDDEN, 403
    data = request.get_json(silent=True) or {}
    contract_id = data.get("contract_id")
    year = data.get("year")
    month = data.get("month")
    if not contract_id or not year or not month:
        return {"error": "missing_params"}, 400
    result = lock_period(
        g.user,
        int(contract_id),
        int(year),
        int(month),
        status=str(data.get("status") or "confirmed"),
        total_ex_vat=data.get("total_ex_vat"),
    )
    if result.get("error"):
        return result, 400
    return result


@bp.post("/period/unlock")
@login_required
@edit_required
def billing_period_unlock():
    if not user_has_uss_section(g.user, "uss_billing"):
        return _FORBIDDEN, 403
    data = request.get_json(silent=True) or {}
    contract_id = data.get("contract_id")
    year = data.get("year")
    month = data.get("month")
    if not contract_id or not year or not month:
        return {"error": "missing_params"}, 400
    result = unlock_period(g.user, int(contract_id), int(year), int(month))
    if result.get("error"):
        return result, 403
    return result


@bp.post("/calculate")
@login_required
@edit_required
def calculate():
    if not user_has_uss_section(g.user, "uss_billing"):
        return _FORBIDDEN, 403
    data = request.get_json(silent=True) or {}
    contract_id = data.get("contract_id")
    period_from = data.get("period_from")
    period_to = data.get("period_to")
    if not contract_id or not period_from or not period_to:
        return {"error": "missing_params", "message": "Укажите договор и период"}, 400

    pf = date.fromisoformat(str(period_from)[:10])
    pt = date.fromisoformat(str(period_to)[:10])
    year, month = pf.year, pf.month
    try:
        assert_billing_calculable(g.user, int(contract_id), year, month)
    except PeriodLockedError as exc:
        return {"error": "period_locked", "message": str(exc)}, 409

    calc = BillingCalculator(process_line_id=data.get("process_line_id"))
    result = calc.calculate_period(int(contract_id), pf, pt)
    if result.get("status") == "ok":
        upsert_period_total(int(contract_id), year, month, result["total_ex_vat"])
        result["period"] = period_status_dict(get_period(int(contract_id), year, month))
    return result


@bp.get("/export")
@login_required
def billing_export():
    """Экспорт расчёта биллинга в Excel."""
    if not user_has_uss_section(g.user, "uss_billing"):
        return _FORBIDDEN, 403

    contract_id = request.args.get("contract_id", type=int)
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)
    if not contract_id or not year or not month:
        return {"error": "missing_params", "message": "Укажите contract_id, year, month"}, 400

    contract = db.session.get(Contract, contract_id)
    if not contract:
        return {"error": "not_found", "message": "Договор не найден"}, 404
    if not g.user.get("is_admin") and contract.warehouse_id not in (g.user.get("warehouse_ids") or []):
        return {"error": "forbidden"}, 403

    try:
        data, filename = build_billing_workbook(contract_id, year, month)
    except ValueError as exc:
        code = str(exc)
        if code == "contract_not_found":
            return {"error": code, "message": "Договор не найден"}, 404
        return {"error": code, "message": "Не удалось сформировать отчёт"}, 400

    return send_file(
        io.BytesIO(data),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )
