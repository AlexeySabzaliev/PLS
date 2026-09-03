"""Сверхурочная работа ТС: по факту убытия после конца смены склада или в выходной."""
from __future__ import annotations

from datetime import date, datetime, time

from app.modules.uss.services.warehouse_schedule import DEFAULT_WORK_DAY_END

WORKDAY_END = DEFAULT_WORK_DAY_END


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


def is_overtime_end(op_date: date, end_time, *, work_day_end: time | None = None) -> bool:
    """Сверхурочно, если убытие после конца смены в будни или любое убытие в выходной."""
    end = _parse_time(end_time)
    if not end:
        return False
    if op_date.weekday() >= 5:
        return True
    limit = work_day_end or WORKDAY_END
    return end > limit


def transport_is_overtime(
    op_date: date,
    departed_at,
    *,
    warehouse_id: int | None = None,
    work_day_end: time | None = None,
) -> bool:
    if work_day_end is None and warehouse_id is not None:
        from app.modules.uss.services.warehouse_schedule import warehouse_work_day_end

        work_day_end = warehouse_work_day_end(warehouse_id)
    return is_overtime_end(op_date, departed_at, work_day_end=work_day_end)


def row_is_overtime(
    op_date: date,
    *,
    departed_at=None,
    prr_finished_at=None,
    warehouse_id: int | None = None,
    work_day_end: time | None = None,
) -> bool:
    return transport_is_overtime(
        op_date,
        departed_at,
        warehouse_id=warehouse_id,
        work_day_end=work_day_end,
    )
