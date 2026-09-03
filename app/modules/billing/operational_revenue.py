"""Выручка по операциям ответхранения (без хранения на площадях) по дням."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from app.modules.billing.storage_strategy import (
    _apply_formula,
    _d,
    _effective_rate,
    _iter_shift_code_qty,
    _month_bounds,
    _tariff_on,
)
from app.modules.uss.services.tariff_codes import AREA_LINE_CODES


def _parse_date(value) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _effective_handling_m3(operations: list[dict]) -> tuple[Decimal, Decimal]:
    """Ручная и мех. обработка; нераспределённый объём по документам → в механизированную."""
    manual_m3 = Decimal("0")
    mech_m3 = Decimal("0")
    for o in operations:
        manual = _d(o.get("inbound_manual_m3")) + _d(o.get("outbound_manual_m3"))
        mech = _d(o.get("inbound_mech_m3")) + _d(o.get("outbound_mech_m3"))
        volume = _d(o.get("volume_document_m3"))
        unallocated = max(volume - manual - mech, Decimal("0"))
        manual_m3 += manual
        mech_m3 += mech + unallocated
    return manual_m3, mech_m3


def _amount_for_metric(tariffs: list[dict], line_code: str, on_date: date, qty: Decimal) -> Decimal:
    if qty <= 0:
        return Decimal("0")
    tariff = _tariff_on(tariffs, line_code, on_date)
    if not tariff:
        return Decimal("0")
    rate = _effective_rate(tariff)
    formula = tariff.get("formula", "rate_times_qty")
    return _apply_formula(formula, rate, qty, None)


def daily_operational_revenue_for_contract(
    year: int,
    month: int,
    tariffs: list[dict],
    operations: list[dict],
    shifts: list[dict],
) -> dict[date, Decimal]:
    """Сумма по операционным строкам биллинга (без хранения) в разрезе календарных дней."""
    period_start, period_end = _month_bounds(year, month)
    daily: dict[date, Decimal] = {}
    cursor = period_start
    while cursor <= period_end:
        daily[cursor] = Decimal("0")
        cursor += timedelta(days=1)

    ops_by_date: dict[date, list[dict]] = {}
    for op in operations:
        ops_by_date.setdefault(_parse_date(op["operation_date"]), []).append(op)

    shifts_by_date: dict[date, list[dict]] = {}
    for shift in shifts:
        shifts_by_date.setdefault(_parse_date(shift["report_date"]), []).append(shift)

    for on_date in daily:
        day_ops = ops_by_date.get(on_date, [])
        day_shifts = shifts_by_date.get(on_date, [])

        if day_ops:
            manual_m3, mech_m3 = _effective_handling_m3(day_ops)
            vehicles = Decimal(len(day_ops))
            overtime_m3 = sum(
                _d(o.get("inbound_manual_m3")) + _d(o.get("outbound_manual_m3"))
                + _d(o.get("inbound_mech_m3")) + _d(o.get("outbound_mech_m3"))
                for o in day_ops if o.get("is_overtime")
            )
            daily[on_date] += _amount_for_metric(tariffs, "manual_m3", on_date, manual_m3)
            daily[on_date] += _amount_for_metric(tariffs, "mechanized_m3", on_date, mech_m3)
            daily[on_date] += _amount_for_metric(tariffs, "vehicle_docs", on_date, vehicles)
            daily[on_date] += _amount_for_metric(tariffs, "overtime_m3", on_date, overtime_m3)

        for shift in day_shifts:
            for code, qty in _iter_shift_code_qty(shift.get("extra_entries")):
                if code in AREA_LINE_CODES:
                    continue
                daily[on_date] += _amount_for_metric(tariffs, code, on_date, qty)

    return daily
