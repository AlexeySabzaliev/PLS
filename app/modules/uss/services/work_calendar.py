"""Рабочий календарь склада: пятидневка (пн–пт), без сб/вс."""
from __future__ import annotations

import calendar
from datetime import date, timedelta


def is_workday(on_date: date) -> bool:
    """Будний день (пн–пт)."""
    return on_date.weekday() < 5


def month_bounds(year: int, month: int) -> tuple[date, date]:
    last = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last)


def workdays_in_range(start: date, end: date) -> int:
    if start > end:
        return 0
    count = 0
    cursor = start
    while cursor <= end:
        if is_workday(cursor):
            count += 1
        cursor += timedelta(days=1)
    return count


def workdays_in_month(year: int, month: int) -> int:
    start, end = month_bounds(year, month)
    return workdays_in_range(start, end)


def clip_range_to_month(
    range_start: date,
    range_end: date | None,
    year: int,
    month: int,
) -> tuple[date, date] | None:
    period_start, period_end = month_bounds(year, month)
    start = max(range_start, period_start)
    end = min(range_end if range_end is not None else period_end, period_end)
    if start > end:
        return None
    return start, end
