"""Тарифы договора для расчёта биллинга."""
from __future__ import annotations

from datetime import date

from app.db import db
from app.modules.reference.models import ContractAmendment, TariffRule, UnitOfMeasure
from app.modules.uss.services.tariff_codes import formula_for_code, infer_billing_line_code, is_placeholder_code
from app.modules.uss.services.tariff_quantity import apply_tariff_defaults


def tariffs_for_billing_period(
    contract_id: int,
    period_start: date,
    period_end: date,
) -> list[dict]:
    """Все тарифы из активных ДС за период."""
    amendments = ContractAmendment.query.filter(
        ContractAmendment.contract_id == contract_id,
        ContractAmendment.status == "active",
        ContractAmendment.effective_from <= period_end,
        db.or_(
            ContractAmendment.effective_to.is_(None),
            ContractAmendment.effective_to >= period_start,
        ),
    ).all()
    am_ids = [a.id for a in amendments]
    if not am_ids:
        return []

    rows = (
        TariffRule.query.filter(
            TariffRule.contract_id == contract_id,
            TariffRule.amendment_id.in_(am_ids),
            TariffRule.valid_from <= period_end,
            db.or_(TariffRule.valid_to.is_(None), TariffRule.valid_to >= period_start),
        )
        .order_by(TariffRule.valid_from.desc(), TariffRule.sort_order, TariffRule.id)
        .all()
    )
    unit_ids = {r.unit_id for r in rows if r.unit_id}
    units = {
        u.id: u.code for u in UnitOfMeasure.query.filter(UnitOfMeasure.id.in_(unit_ids)).all()
    } if unit_ids else {}

    out: list[dict] = []
    seen: set[str] = set()
    for row in rows:
        code = row.billing_line_code
        if is_placeholder_code(code):
            code = infer_billing_line_code(row.name or "", code)
        if code in seen:
            continue
        seen.add(code)
        item = apply_tariff_defaults({
            "id": row.id,
            "billing_line_code": code,
            "name": row.name,
            "report_role": row.report_role,
            "report_scope": row.report_scope,
            "quantity_source": row.quantity_source,
            "rate_line_code": row.rate_line_code,
            "quantity_divisor": float(row.quantity_divisor or 1),
            "is_custom": row.is_custom,
            "price_agreed": row.price_agreed,
            "sort_order": row.sort_order or 0,
            "valid_from": row.valid_from,
            "valid_to": row.valid_to,
            "rate_ex_vat": row.rate_ex_vat,
            "formula": row.formula or formula_for_code(code),
            "unit_code": units.get(row.unit_id),
        })
        out.append(item)
    return out
