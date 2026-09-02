"""Конверсия операционных количеств в строки биллинга."""
from __future__ import annotations

from decimal import Decimal


def _d(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def billing_line_for_rate(tariff: dict) -> str:
    """Код строки, по чьей ставке считается сумма."""
    return (tariff.get("rate_line_code") or tariff.get("billing_line_code") or "").strip()


def billing_quantity_divisor(tariff: dict) -> Decimal:
    div = _d(tariff.get("quantity_divisor") or 1)
    return div if div > 0 else Decimal("1")


def operational_to_billing_quantity(tariff: dict, operational_qty: Decimal) -> tuple[str, Decimal]:
    """Операционное кол-во → (код строки биллинга, кол-во для тарифа)."""
    bill_code = billing_line_for_rate(tariff)
    if not bill_code:
        return "", Decimal("0")
    return bill_code, operational_qty / billing_quantity_divisor(tariff)
