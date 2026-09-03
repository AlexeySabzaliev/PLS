"""Блокировка закрытых биллинговых периодов (порт из Billings)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from app.db import db
from app.modules.billing.models import BillingPeriod, PERIOD_STATUSES

LOCKED_FOR_OPS = frozenset({"under_review", "confirmed", "invoiced"})
LOCKED_FOR_RECALC = frozenset({"under_review", "confirmed", "invoiced"})

STATUS_LABELS = {
    "draft": "Открыт",
    "under_review": "На согласовании",
    "confirmed": "Закрыт",
    "invoiced": "Счёт выставлен",
}


class PeriodLockedError(ValueError):
    """Период закрыт для изменений."""


def get_period(contract_id: int, year: int, month: int) -> BillingPeriod | None:
    return BillingPeriod.query.filter_by(
        contract_id=contract_id,
        period_year=year,
        period_month=month,
    ).first()


def period_for_date(contract_id: int, on_date: date) -> BillingPeriod | None:
    return get_period(contract_id, on_date.year, on_date.month)


def period_status_dict(period: BillingPeriod | None) -> dict:
    if not period:
        return {
            "status": "draft",
            "label": STATUS_LABELS["draft"],
            "locked": False,
            "total_ex_vat": None,
            "locked_at": None,
        }
    locked = period.status in LOCKED_FOR_OPS
    return {
        "status": period.status,
        "label": STATUS_LABELS.get(period.status, period.status),
        "locked": locked,
        "total_ex_vat": float(period.total_ex_vat) if period.total_ex_vat is not None else None,
        "locked_at": period.locked_at.isoformat() if period.locked_at else None,
    }


def periods_status_for_contracts(
    contract_ids: list[int],
    year: int,
    month: int,
) -> dict[int, dict]:
    if not contract_ids:
        return {}
    rows = BillingPeriod.query.filter(
        BillingPeriod.contract_id.in_(contract_ids),
        BillingPeriod.period_year == year,
        BillingPeriod.period_month == month,
    ).all()
    by_id = {r.contract_id: r for r in rows}
    return {cid: period_status_dict(by_id.get(cid)) for cid in contract_ids}


def assert_operations_editable(user: dict | None, contract_id: int, on_date: date) -> None:
    """Операции/смены нельзя менять в закрытом периоде (кроме admin)."""
    if user and user.get("is_admin"):
        return
    period = period_for_date(contract_id, on_date)
    if period and period.status in LOCKED_FOR_OPS:
        raise PeriodLockedError(
            f"Период {on_date.month:02d}.{on_date.year} ({STATUS_LABELS.get(period.status, period.status)}) "
            "закрыт для операций"
        )


def assert_warehouse_date_editable(user: dict | None, warehouse_id: int, on_date: date) -> None:
    """Склад/УЗ: блок, если закрыт хотя бы один договор склада за месяц."""
    if user and user.get("is_admin"):
        return
    from app.modules.reference.models import Contract, ProductType

    contracts = (
        Contract.query.join(ProductType)
        .filter(
            Contract.warehouse_id == warehouse_id,
            Contract.status == "active",
            ProductType.code == "RESPONSIBLE_STORAGE",
        )
        .all()
    )
    for contract in contracts:
        assert_operations_editable(user, contract.id, on_date)


def assert_billing_calculable(
    user: dict | None,
    contract_id: int,
    year: int,
    month: int,
) -> BillingPeriod | None:
    period = get_period(contract_id, year, month)
    if not period:
        return None
    if user and user.get("is_admin"):
        return period
    if period.status in LOCKED_FOR_RECALC:
        raise PeriodLockedError(
            f"Период {month:02d}.{year} ({STATUS_LABELS.get(period.status, period.status)}) — "
            "пересчёт недоступен. Обратитесь к администратору."
        )
    return period


def lock_period(
    user: dict,
    contract_id: int,
    year: int,
    month: int,
    *,
    status: str = "confirmed",
    total_ex_vat: Decimal | float | None = None,
) -> dict:
    if status not in PERIOD_STATUSES or status == "draft":
        return {"error": "invalid_status"}
    period = get_period(contract_id, year, month)
    if not period:
        period = BillingPeriod(
            contract_id=contract_id,
            period_year=year,
            period_month=month,
        )
        db.session.add(period)
    period.status = status
    if total_ex_vat is not None:
        period.total_ex_vat = Decimal(str(total_ex_vat))
    period.locked_by = user.get("id")
    period.locked_at = datetime.utcnow()
    db.session.commit()
    return {"period": period_status_dict(period)}


def unlock_period(user: dict, contract_id: int, year: int, month: int) -> dict:
    if not user.get("is_admin"):
        return {"error": "forbidden"}
    period = get_period(contract_id, year, month)
    if not period:
        return {"period": period_status_dict(None)}
    period.status = "draft"
    period.locked_by = None
    period.locked_at = None
    db.session.commit()
    return {"period": period_status_dict(period)}


def upsert_period_total(
    contract_id: int,
    year: int,
    month: int,
    total_ex_vat: Decimal | float,
) -> BillingPeriod:
    """Сохранить итог расчёта (не закрывает период)."""
    period = get_period(contract_id, year, month)
    if not period:
        period = BillingPeriod(
            contract_id=contract_id,
            period_year=year,
            period_month=month,
            status="draft",
        )
        db.session.add(period)
    if period.status == "draft":
        period.total_ex_vat = Decimal(str(total_ex_vat))
    db.session.commit()
    return period
