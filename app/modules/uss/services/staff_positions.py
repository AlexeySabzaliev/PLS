"""Справочник штатных позиций (ФОТ) по складу с историей ставок."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from app.db import db
from app.modules.uss.models import WarehouseStaffPosition, WarehouseStaffPositionVersion
from app.modules.uss.services.work_calendar import clip_range_to_month, is_workday, workdays_in_range


def _d(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _version_active_on(valid_from: date, valid_to: date | None, on_date: date) -> bool:
    if on_date < valid_from:
        return False
    if valid_to is not None and on_date > valid_to:
        return False
    return True


def list_versions_for_period(
    warehouse_id: int,
    period_start: date,
    period_end: date,
) -> list[dict]:
    rows = (
        WarehouseStaffPositionVersion.query.filter(
            WarehouseStaffPositionVersion.warehouse_id == warehouse_id,
            WarehouseStaffPositionVersion.valid_from <= period_end,
            db.or_(
                WarehouseStaffPositionVersion.valid_to.is_(None),
                WarehouseStaffPositionVersion.valid_to >= period_start,
            ),
        )
        .order_by(
            WarehouseStaffPositionVersion.valid_from,
            WarehouseStaffPositionVersion.position_id,
            WarehouseStaffPositionVersion.id,
        )
        .all()
    )
    return [
        {
            "id": r.id,
            "position_id": r.position_id,
            "warehouse_id": r.warehouse_id,
            "name": r.name,
            "monthly_rate": r.monthly_rate,
            "headcount": r.headcount,
            "valid_from": r.valid_from,
            "valid_to": r.valid_to,
        }
        for r in rows
    ]


def daily_fot_for_date(
    warehouse_id: int,
    on_date: date,
    calendar_days: int,
) -> Decimal:
    """
    Дневной ФОТ на рабочий день (пн–пт): (оклад × штат) / рабочие дни сегмента в месяце.
    В сб/вс — 0. calendar_days оставлен для совместимости вызовов.
    """
    del calendar_days
    if not is_workday(on_date):
        return Decimal("0")

    year, month = on_date.year, on_date.month
    versions = (
        WarehouseStaffPositionVersion.query.filter(
            WarehouseStaffPositionVersion.warehouse_id == warehouse_id,
            WarehouseStaffPositionVersion.valid_from <= on_date,
            db.or_(
                WarehouseStaffPositionVersion.valid_to.is_(None),
                WarehouseStaffPositionVersion.valid_to >= on_date,
            ),
        )
        .all()
    )
    daily = Decimal("0")
    for row in versions:
        if not _version_active_on(row.valid_from, row.valid_to, on_date):
            continue
        clipped = clip_range_to_month(row.valid_from, row.valid_to, year, month)
        if not clipped:
            continue
        seg_start, seg_end = clipped
        if on_date < seg_start or on_date > seg_end:
            continue
        wd = workdays_in_range(seg_start, seg_end)
        if wd <= 0:
            continue
        daily += _d(row.monthly_rate) * Decimal(int(row.headcount or 0)) / Decimal(wd)
    return daily


def monthly_fot_total_for_period(warehouse_id: int, year: int, month: int) -> Decimal:
    import calendar

    cal_days = calendar.monthrange(year, month)[1]
    period_start = date(year, month, 1)
    total = Decimal("0")
    for i in range(cal_days):
        on_date = period_start + timedelta(days=i)
        total += daily_fot_for_date(warehouse_id, on_date, cal_days)
    return total


def monthly_fot_total(positions: list[dict]) -> Decimal:
    """Сумма по текущему справочнику (без истории) — для простых тестов."""
    total = Decimal("0")
    for p in positions:
        total += _d(p.get("monthly_rate")) * Decimal(int(p.get("headcount") or 0))
    return total


def _open_version(position_id: int) -> WarehouseStaffPositionVersion | None:
    return (
        WarehouseStaffPositionVersion.query.filter_by(position_id=position_id, valid_to=None)
        .order_by(WarehouseStaffPositionVersion.valid_from.desc())
        .first()
    )


def list_position_versions(position_id: int) -> list[dict]:
    rows = (
        WarehouseStaffPositionVersion.query.filter_by(position_id=position_id)
        .order_by(WarehouseStaffPositionVersion.valid_from.desc(), WarehouseStaffPositionVersion.id.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "position_id": r.position_id,
            "name": r.name,
            "monthly_rate": float(_d(r.monthly_rate)),
            "headcount": int(r.headcount or 0),
            "valid_from": r.valid_from.isoformat(),
            "valid_to": r.valid_to.isoformat() if r.valid_to else None,
        }
        for r in rows
    ]


def list_staff_positions(warehouse_id: int, *, active_only: bool = True) -> list[dict]:
    q = WarehouseStaffPosition.query.filter_by(warehouse_id=warehouse_id)
    if active_only:
        q = q.filter_by(is_active=True)
    rows = q.order_by(WarehouseStaffPosition.sort_order, WarehouseStaffPosition.name).all()
    out = []
    for row in rows:
        rate = _d(row.monthly_rate)
        hc = int(row.headcount or 0)
        open_v = _open_version(row.id)
        effective_from = open_v.valid_from.isoformat() if open_v else None
        out.append({
            "id": row.id,
            "warehouse_id": row.warehouse_id,
            "name": row.name,
            "monthly_rate": float(rate),
            "headcount": hc,
            "monthly_total": float(rate * hc),
            "is_active": row.is_active,
            "sort_order": row.sort_order,
            "effective_from": effective_from,
            "version_id": open_v.id if open_v else None,
        })
    return out


def _close_open_version(position_id: int, close_date: date) -> None:
    open_rows = WarehouseStaffPositionVersion.query.filter_by(
        position_id=position_id,
        valid_to=None,
    ).all()
    for row in open_rows:
        if row.valid_from <= close_date:
            row.valid_to = close_date


def _insert_version(
    *,
    position_id: int,
    warehouse_id: int,
    name: str,
    monthly_rate: Decimal,
    headcount: int,
    valid_from: date,
) -> WarehouseStaffPositionVersion:
    row = WarehouseStaffPositionVersion(
        position_id=position_id,
        warehouse_id=warehouse_id,
        name=name,
        monthly_rate=monthly_rate,
        headcount=headcount,
        valid_from=valid_from,
    )
    db.session.add(row)
    return row


def create_staff_position(warehouse_id: int, data: dict) -> dict:
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("name_required")
    headcount = int(data.get("headcount") or 1)
    if headcount < 1:
        raise ValueError("invalid_headcount")
    rate = _d(data.get("monthly_rate"))
    effective_from = date.fromisoformat(str(data.get("effective_from") or date.today())[:10])
    pos = WarehouseStaffPosition(
        warehouse_id=warehouse_id,
        name=name,
        monthly_rate=rate,
        headcount=headcount,
        sort_order=int(data.get("sort_order") or 100),
        is_active=True,
    )
    db.session.add(pos)
    db.session.flush()
    _insert_version(
        position_id=pos.id,
        warehouse_id=warehouse_id,
        name=name,
        monthly_rate=rate,
        headcount=headcount,
        valid_from=effective_from,
    )
    return {
        "id": pos.id,
        "warehouse_id": warehouse_id,
        "name": name,
        "monthly_rate": float(rate),
        "headcount": headcount,
        "monthly_total": float(rate * headcount),
        "is_active": True,
        "sort_order": pos.sort_order,
    }


def update_staff_position(position_id: int, data: dict) -> dict:
    pos = db.session.get(WarehouseStaffPosition, position_id)
    if not pos:
        raise ValueError("not_found")
    headcount = data.get("headcount")
    if headcount is not None and int(headcount) < 1:
        raise ValueError("invalid_headcount")

    new_name = (data.get("name") or pos.name).strip()
    new_rate = _d(data.get("monthly_rate", pos.monthly_rate))
    new_headcount = int(headcount if headcount is not None else pos.headcount)
    rate_changed = "monthly_rate" in data and new_rate != _d(pos.monthly_rate)
    hc_changed = headcount is not None and new_headcount != int(pos.headcount)
    name_changed = "name" in data and new_name != pos.name

    if rate_changed or hc_changed or name_changed:
        effective_from = date.fromisoformat(str(data.get("effective_from") or date.today())[:10])
        close_date = effective_from - timedelta(days=1)
        if close_date >= date(1900, 1, 1):
            _close_open_version(pos.id, close_date)
        _insert_version(
            position_id=pos.id,
            warehouse_id=pos.warehouse_id,
            name=new_name,
            monthly_rate=new_rate,
            headcount=new_headcount,
            valid_from=effective_from,
        )

    if "name" in data:
        pos.name = new_name
    if "monthly_rate" in data:
        pos.monthly_rate = new_rate
    if headcount is not None:
        pos.headcount = new_headcount
    if "sort_order" in data:
        pos.sort_order = int(data["sort_order"])
    if "is_active" in data:
        pos.is_active = bool(data["is_active"])
    db.session.flush()
    items = list_staff_positions(pos.warehouse_id, active_only=False)
    return next(x for x in items if x["id"] == pos.id)


def deactivate_staff_position(position_id: int) -> None:
    pos = db.session.get(WarehouseStaffPosition, position_id)
    if not pos:
        raise ValueError("not_found")
    pos.is_active = False


def create_staff_position_version(
    *,
    position_id: int,
    warehouse_id: int,
    name: str,
    monthly_rate: Decimal,
    headcount: int,
    valid_from: date,
) -> WarehouseStaffPositionVersion:
    return _insert_version(
        position_id=position_id,
        warehouse_id=warehouse_id,
        name=name,
        monthly_rate=monthly_rate,
        headcount=headcount,
        valid_from=valid_from,
    )
