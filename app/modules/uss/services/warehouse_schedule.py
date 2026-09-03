"""График работы склада — для сверхурочных и биллинга."""
from __future__ import annotations

from datetime import time

from app.db import db
from app.modules.reference.models import Warehouse

DEFAULT_WORK_DAY_START = time(9, 0)
DEFAULT_WORK_DAY_END = time(17, 30)


def warehouse_shift_hours(warehouse_id: int | None) -> tuple[time, time]:
    """Начало и конец рабочего дня склада (пн–пт)."""
    if not warehouse_id:
        return DEFAULT_WORK_DAY_START, DEFAULT_WORK_DAY_END
    wh = db.session.get(Warehouse, warehouse_id)
    if not wh:
        return DEFAULT_WORK_DAY_START, DEFAULT_WORK_DAY_END
    start = wh.work_day_start or DEFAULT_WORK_DAY_START
    end = wh.work_day_end or DEFAULT_WORK_DAY_END
    return start, end


def warehouse_work_day_end(warehouse_id: int | None) -> time:
    return warehouse_shift_hours(warehouse_id)[1]
