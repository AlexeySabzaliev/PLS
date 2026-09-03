"""Сверхурочная работа: пн–пт 9:00–17:30, иначе — сверхурочно."""
from __future__ import annotations

from datetime import date, datetime, time

WORKDAY_END = time(17, 30)


def _parse_time(value) -> time | None:
    if value is None:
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, datetime):
        return value.time()
    text = str(value).strip()
    if not text:
        return None
    if len(text) >= 5 and text[2] == ":":
        parts = text[:5].split(":")
        return time(int(parts[0]), int(parts[1]))
    return None


def compare_times(a, b) -> int | None:
    """Сравнение времён суток: -1 если a < b, 0 если равны, 1 если a > b, None если нет пары."""
    ta, tb = _parse_time(a), _parse_time(b)
    if not ta or not tb:
        return None
    if ta < tb:
        return -1
    if ta > tb:
        return 1
    return 0


def is_overtime_end(op_date: date, end_time) -> bool:
    """Сверхурочно, если окончание после 17:30 в будни или в выходной."""
    end = _parse_time(end_time)
    if not end:
        return False
    if op_date.weekday() >= 5:
        return True
    return end > WORKDAY_END


def transport_is_overtime(op_date: date, departed_at) -> bool:
    return is_overtime_end(op_date, departed_at)


def row_is_overtime(op_date: date, *, departed_at=None, prr_finished_at=None) -> bool:
    return transport_is_overtime(op_date, departed_at)
