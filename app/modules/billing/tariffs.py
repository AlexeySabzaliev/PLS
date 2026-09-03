"""Тарифы договора для расчёта биллинга."""
from __future__ import annotations

from datetime import date

from app.db import db
from app.modules.reference.amendment_scope import allowed_amendment_statuses
from app.modules.reference.models import ContractAmendment, TariffRule, UnitOfMeasure
from app.modules.uss.services.tariff_codes import formula_for_code, infer_billing_line_code, is_placeholder_code
from app.modules.uss.services.tariff_quantity import apply_tariff_defaults


def _period_label(period_start: date, period_end: date) -> str:
    if period_start.year == period_end.year and period_start.month == period_end.month:
        return f"{period_start.month:02d}.{period_start.year}"
    return f"{period_start.isoformat()}–{period_end.isoformat()}"


def _amendment_overlaps_period(amendment: ContractAmendment, period_start: date, period_end: date) -> bool:
    if amendment.effective_from > period_end:
        return False
    if amendment.effective_to is not None and amendment.effective_to < period_start:
        return False
    return True


def _tariff_overlaps_period(rule: TariffRule, period_start: date, period_end: date) -> bool:
    if rule.valid_from > period_end:
        return False
    if rule.valid_to is not None and rule.valid_to < period_start:
        return False
    return True


def _amendments_for_period(
    contract_id: int,
    period_start: date,
    period_end: date,
    *,
    statuses: list[str] | None = None,
) -> list[ContractAmendment]:
    query = ContractAmendment.query.filter(
        ContractAmendment.contract_id == contract_id,
        ContractAmendment.effective_from <= period_end,
        db.or_(
            ContractAmendment.effective_to.is_(None),
            ContractAmendment.effective_to >= period_start,
        ),
    )
    if statuses is not None:
        query = query.filter(ContractAmendment.status.in_(statuses))
    return query.order_by(ContractAmendment.effective_from.desc(), ContractAmendment.id).all()


def _tariff_rows_for_amendments(
    contract_id: int,
    amendment_ids: list[int],
    period_start: date,
    period_end: date,
) -> list[TariffRule]:
    if not amendment_ids:
        return []
    return (
        TariffRule.query.filter(
            TariffRule.contract_id == contract_id,
            TariffRule.amendment_id.in_(amendment_ids),
            TariffRule.valid_from <= period_end,
            db.or_(TariffRule.valid_to.is_(None), TariffRule.valid_to >= period_start),
        )
        .order_by(TariffRule.valid_from.desc(), TariffRule.sort_order, TariffRule.id)
        .all()
    )


def _serialize_tariff_rows(rows: list[TariffRule]) -> list[dict]:
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


def diagnose_tariffs_for_billing_period(
    contract_id: int,
    period_start: date,
    period_end: date,
) -> dict | None:
    """Причина отсутствия ставок для биллинга (None — ставки найдены)."""
    period = _period_label(period_start, period_end)
    allowed_statuses = allowed_amendment_statuses()

    all_amendments = ContractAmendment.query.filter_by(contract_id=contract_id).all()
    if not all_amendments:
        return {
            "error": "no_amendments",
            "message": (
                "К договору не привязано ни одного ДС — загрузите доп. соглашение "
                "со ставками в справочнике."
            ),
        }

    overlapping = [a for a in all_amendments if _amendment_overlaps_period(a, period_start, period_end)]
    if not overlapping:
        numbers = ", ".join(a.number for a in all_amendments[:3])
        return {
            "error": "amendment_dates",
            "message": (
                f"Нет ДС, действующих в периоде {period}. "
                f"Проверьте даты начала и окончания ДС ({numbers})."
            ),
        }

    allowed = [a for a in overlapping if a.status in allowed_statuses]
    if not allowed:
        draft_numbers = ", ".join(a.number for a in overlapping if a.status == "draft")
        if draft_numbers:
            return {
                "error": "amendment_draft",
                "message": (
                    f"ДС {draft_numbers} в статусе «черновик» — активируйте его "
                    f"(status = active) перед расчётом биллинга."
                ),
            }
        numbers = ", ".join(a.number for a in overlapping[:3])
        return {
            "error": "amendment_status",
            "message": (
                f"ДС {numbers} не в статусе «активно» — активируйте ДС перед расчётом."
            ),
        }

    am_ids = [a.id for a in allowed]
    tariff_rows = _tariff_rows_for_amendments(contract_id, am_ids, period_start, period_end)
    if tariff_rows:
        return None

    any_tariffs = TariffRule.query.filter(
        TariffRule.contract_id == contract_id,
        TariffRule.amendment_id.in_(am_ids),
    ).count()
    if not any_tariffs:
        numbers = ", ".join(a.number for a in allowed[:3])
        return {
            "error": "no_tariff_rules",
            "message": (
                f"В действующих ДС ({numbers}) нет ставок — загрузите файл Word "
                "или добавьте строки тарифов."
            ),
        }

    numbers = ", ".join(a.number for a in allowed[:3])
    return {
        "error": "tariff_dates",
        "message": (
            f"Ставки в ДС {numbers} есть, но ни одна не действует в периоде {period}. "
            "Проверьте даты valid_from и valid_to."
        ),
    }


def tariffs_for_billing_period(
    contract_id: int,
    period_start: date,
    period_end: date,
) -> list[dict]:
    """Все тарифы из действующих ДС за период."""
    amendments = _amendments_for_period(
        contract_id,
        period_start,
        period_end,
        statuses=allowed_amendment_statuses(),
    )
    rows = _tariff_rows_for_amendments(contract_id, [a.id for a in amendments], period_start, period_end)
    return _serialize_tariff_rows(rows)
