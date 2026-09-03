"""Применение разобранного DOCX к записи ДС и ставкам."""
from __future__ import annotations

from decimal import Decimal

from app.db import db
from app.modules.reference.amendment_docx_import import ParsedAmendment
from app.modules.reference.models import ContractAmendment, TariffRule, UnitOfMeasure
from app.modules.uss.services.tariff_codes import formula_for_code, is_standard_catalog_tariff
from app.modules.uss.services.tariff_quantity import apply_tariff_defaults


def _unit_id_by_code() -> dict[str, int]:
    return {u.code: u.id for u in UnitOfMeasure.query.all()}


def apply_parsed_to_amendment(
    amendment: ContractAmendment,
    parsed: ParsedAmendment,
    *,
    replace_tariffs: bool = True,
) -> dict:
    """Обновить поля ДС и создать строки tariff_rules из разбора DOCX."""
    valid_from = parsed.effective_from or amendment.effective_from
    valid_to = parsed.effective_to or amendment.effective_to

    if parsed.number:
        amendment.number = parsed.number
    if parsed.effective_from:
        amendment.effective_from = parsed.effective_from
    if parsed.effective_to is not None:
        amendment.effective_to = parsed.effective_to

    tariffs_created = 0
    if replace_tariffs and parsed.tariffs:
        TariffRule.query.filter_by(amendment_id=amendment.id).delete()
        unit_map = _unit_id_by_code()

        for t in parsed.tariffs:
            defaults = apply_tariff_defaults({
                "billing_line_code": t.billing_line_code,
                "name": t.name,
                "formula": t.formula,
            })
            code = defaults["billing_line_code"]
            unit_code = t.unit_code or defaults.get("unit_code")
            unit_id = unit_map.get(unit_code) if unit_code else None

            rule = TariffRule(
                contract_id=amendment.contract_id,
                amendment_id=amendment.id,
                billing_line_code=code,
                name=t.name,
                unit_id=unit_id,
                report_role=defaults.get("report_role"),
                report_scope=defaults.get("report_scope"),
                quantity_source=defaults.get("quantity_source"),
                rate_line_code=defaults.get("rate_line_code") or code,
                is_custom=not is_standard_catalog_tariff(code),
                price_agreed=True,
                sort_order=t.sort_order,
                valid_from=valid_from,
                valid_to=valid_to,
                rate_ex_vat=Decimal(t.rate),
                formula=t.formula or formula_for_code(code),
            )
            db.session.add(rule)
            tariffs_created += 1

    db.session.flush()
    return {
        "tariffs_created": tariffs_created,
        "warnings": list(parsed.warnings),
    }
