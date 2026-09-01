"""API биллинга (скелет)."""
from __future__ import annotations

from datetime import date

from flask import Blueprint, g, request

from app.core.auth import login_required
from app.core.permissions import user_has_uss_section
from app.modules.billing.calculator import BillingCalculator

bp = Blueprint("billing_api", __name__, url_prefix="/api/billing")


@bp.post("/calculate")
@login_required
def calculate():
    if not user_has_uss_section(g.user, "uss_billing"):
        return {"error": "forbidden"}, 403
    data = request.get_json(silent=True) or {}
    calc = BillingCalculator(process_line_id=data.get("process_line_id"))
    result = calc.calculate_period(
        contract_id=data["contract_id"],
        period_from=date.fromisoformat(data["period_from"]),
        period_to=date.fromisoformat(data["period_to"]),
    )
    return result
