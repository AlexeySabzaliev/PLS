"""API биллинга."""
from __future__ import annotations

from datetime import date

from flask import Blueprint, g, request

from app.core.auth import login_required
from app.core.permissions import user_has_uss_section
from app.modules.billing.calculator import BillingCalculator
from app.modules.reference.models import Contract, ProductType, Warehouse

bp = Blueprint("billing_api", __name__, url_prefix="/api/billing")


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
        return {"error": "forbidden"}, 403

    wh_id = request.args.get("warehouse_id", type=int)
    warehouses = _billing_warehouses()
    if not warehouses:
        return {"error": "no_warehouses"}, 403

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
    }


@bp.post("/calculate")
@login_required
def calculate():
    if not user_has_uss_section(g.user, "uss_billing"):
        return {"error": "forbidden"}, 403
    data = request.get_json(silent=True) or {}
    contract_id = data.get("contract_id")
    period_from = data.get("period_from")
    period_to = data.get("period_to")
    if not contract_id or not period_from or not period_to:
        return {"error": "missing_params"}, 400
    calc = BillingCalculator(process_line_id=data.get("process_line_id"))
    result = calc.calculate_period(
        contract_id=int(contract_id),
        period_from=date.fromisoformat(str(period_from)[:10]),
        period_to=date.fromisoformat(str(period_to)[:10]),
    )
    return result
