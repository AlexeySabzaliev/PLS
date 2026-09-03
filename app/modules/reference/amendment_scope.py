"""Общая логика действия ДС на дату (смены УСС и биллинг)."""
from __future__ import annotations

import os
from datetime import date

from flask import has_app_context

from app.db import db
from app.modules.reference.models import ContractAmendment, TariffRule


def allowed_amendment_statuses() -> list[str]:
    """В dev-режиме допускаем черновики ДС без активации."""
    if has_app_context():
        from flask import current_app

        if current_app.config.get("TESTING"):
            return ["active"]
    if os.getenv("FLASK_ENV", "development").lower() == "production":
        return ["active"]
    return ["active", "draft"]


def _min_tariff_valid_from(amendment_id: int) -> date | None:
    return (
        db.session.query(db.func.min(TariffRule.valid_from))
        .filter(TariffRule.amendment_id == amendment_id)
        .scalar()
    )


def amendment_effective_from(amendment: ContractAmendment) -> date:
    """Дата начала ДС: effective_from, min(valid_from ставок) или дата создания."""
    tariff_min = _min_tariff_valid_from(amendment.id)
    stored = amendment.effective_from
    if tariff_min is not None and stored is not None:
        return min(stored, tariff_min)
    if stored is not None:
        return stored
    if tariff_min is not None:
        return tariff_min
    if amendment.created_at:
        return amendment.created_at.date()
    return date.today()


def amendment_effective_to(amendment: ContractAmendment) -> date | None:
    return amendment.effective_to


def amendment_active_on_date(amendment: ContractAmendment, day: date) -> bool:
    if amendment.status not in allowed_amendment_statuses():
        return False
    eff_from = amendment_effective_from(amendment)
    eff_to = amendment_effective_to(amendment)
    if eff_from > day:
        return False
    if eff_to is not None and eff_to < day:
        return False
    return True


def amendments_for_contract_on_date(contract_id: int, day: date) -> list[ContractAmendment]:
    rows = ContractAmendment.query.filter(
        ContractAmendment.contract_id == contract_id,
        ContractAmendment.status.in_(allowed_amendment_statuses()),
    ).all()
    active = [a for a in rows if amendment_active_on_date(a, day)]
    return sorted(active, key=lambda a: (amendment_effective_from(a), a.id))


def primary_amendment_for_contract_on_date(contract_id: int, day: date) -> ContractAmendment | None:
    """Одно ДС на дату: более позднее effective_from; «ДС-6» уступает «ДС-6/2024»."""
    active = amendments_for_contract_on_date(contract_id, day)
    if not active:
        return None
    if len(active) == 1:
        return active[0]

    def pick_key(a: ContractAmendment) -> tuple:
        eff = amendment_effective_from(a)
        # короткий дубль без года — ниже приоритет при том же сроке
        short_dup = 1 if a.number == "ДС-6" else 0
        return (eff.toordinal(), -short_dup, a.id)

    return max(active, key=pick_key)
