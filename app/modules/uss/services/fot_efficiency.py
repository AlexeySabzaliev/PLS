"""Отчёт ФОТ vs операционка по складу."""
from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import Decimal

from app.modules.billing.aggregates import load_vehicle_operations
from app.modules.billing.calculator import load_shifts
from app.modules.billing.operational_revenue import daily_operational_revenue_for_contract
from app.modules.billing.tariffs import tariffs_for_billing_period
from app.modules.reference.models import Contract, ProductType
from app.modules.uss.services.staff_positions import (
    daily_fot_for_date,
    list_versions_for_period,
    monthly_fot_total_for_period,
)
from app.modules.uss.services.work_calendar import is_workday, workdays_in_month


def _d(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _float(value: Decimal | int | float) -> float:
    if value is None:
        return 0.0
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return float(value.quantize(Decimal("0.01")))


def _staff_summary_for_period(warehouse_id: int, period_start: date, period_end: date) -> list[dict]:
    """Сегменты штата, действовавшие в периоде (для отображения в отчёте)."""
    versions = list_versions_for_period(warehouse_id, period_start, period_end)
    out = []
    for v in versions:
        rate = _d(v["monthly_rate"])
        hc = int(v["headcount"] or 0)
        out.append({
            "position_id": v["position_id"],
            "name": v["name"],
            "monthly_rate": float(rate),
            "headcount": hc,
            "monthly_total": float(rate * hc),
            "valid_from": v["valid_from"].isoformat() if v.get("valid_from") else None,
            "valid_to": v["valid_to"].isoformat() if v.get("valid_to") else None,
        })
    return out


def _contracts_for_warehouse(warehouse_id: int, effective_on: date) -> list[dict]:
    rows = (
        Contract.query.join(ProductType)
        .filter(
            Contract.warehouse_id == warehouse_id,
            Contract.status == "active",
            ProductType.code == "RESPONSIBLE_STORAGE",
        )
        .order_by(Contract.number)
        .all()
    )
    return [{"contract_id": c.id, "number": c.number} for c in rows]


def build_fot_report(
    warehouse_id: int,
    year: int,
    month: int,
    *,
    contract_id: int | None = None,
) -> dict:
    """Живой расчёт: версионированный ФОТ + операционка по текущим данным."""
    cal_days = calendar.monthrange(year, month)[1]
    period_start = date(year, month, 1)
    period_end = date(year, month, cal_days)

    monthly_fot = monthly_fot_total_for_period(warehouse_id, year, month)
    staff = _staff_summary_for_period(warehouse_id, period_start, period_end)

    all_contracts = _contracts_for_warehouse(warehouse_id, period_end)
    contracts = all_contracts
    if contract_id:
        contracts = [c for c in all_contracts if c["contract_id"] == contract_id]

    daily_ops: dict[date, Decimal] = {
        period_start + timedelta(days=i): Decimal("0") for i in range(cal_days)
    }

    for contract in contracts:
        contract_id_val = contract["contract_id"]
        tariffs = tariffs_for_billing_period(contract_id_val, period_start, period_end)
        operations = load_vehicle_operations(
            contract_id_val, warehouse_id, period_start, period_end,
        )
        shifts = load_shifts(warehouse_id, period_start, period_end)
        contract_daily = daily_operational_revenue_for_contract(
            year,
            month,
            tariffs,
            operations,
            shifts,
        )
        for on_date, amount in contract_daily.items():
            daily_ops[on_date] = daily_ops.get(on_date, Decimal("0")) + amount

    daily_rows = []
    cumulative = Decimal("0")
    monthly_ops = Decimal("0")
    for i in range(cal_days):
        on_date = period_start + timedelta(days=i)
        ops = daily_ops.get(on_date, Decimal("0"))
        day_fot = daily_fot_for_date(warehouse_id, on_date, cal_days)
        delta = ops - day_fot
        cumulative += delta
        monthly_ops += ops
        daily_rows.append({
            "date": on_date.isoformat(),
            "ops_revenue": _float(ops),
            "fot": _float(day_fot),
            "delta": _float(delta),
            "cumulative_delta": _float(cumulative),
            "goal_met": delta >= 0,
            "is_workday": is_workday(on_date),
        })

    weekly_rows = []
    week_no = 1
    idx = 0
    while idx < cal_days:
        chunk = daily_rows[idx:idx + 7]
        if not chunk:
            break
        ops_sum = sum(_d(r["ops_revenue"]) for r in chunk)
        fot_sum = sum(_d(r["fot"]) for r in chunk)
        delta = ops_sum - fot_sum
        weekly_rows.append({
            "week": week_no,
            "from": chunk[0]["date"],
            "to": chunk[-1]["date"],
            "days": len(chunk),
            "ops_revenue": _float(ops_sum),
            "fot": _float(fot_sum),
            "delta": _float(delta),
            "goal_met": delta >= 0,
        })
        week_no += 1
        idx += 7

    monthly_delta = monthly_ops - monthly_fot
    work_days = workdays_in_month(year, month)
    avg_daily_fot = monthly_fot / Decimal(work_days) if work_days else Decimal("0")

    report = {
        "warehouse_id": warehouse_id,
        "year": year,
        "month": month,
        "calendar_days": cal_days,
        "workdays": work_days,
        "staff": staff,
        "monthly_fot": _float(monthly_fot),
        "daily_fot": _float(avg_daily_fot),
        "monthly_ops_revenue": _float(monthly_ops),
        "monthly_delta": _float(monthly_delta),
        "goal_met": monthly_delta >= 0,
        "contracts_count": len(contracts),
        "contract_id": contract_id,
        "daily": daily_rows,
        "weekly": weekly_rows,
        "live": True,
    }
    if not staff:
        report["staff_missing"] = True
        report["staff_message"] = (
            "Справочник «Штат ФОТ» не заполнен для этого склада — "
            "операционка рассчитана, ФОТ = 0. "
            "Заполните должности, оклады и численность в Справочники → Штат ФОТ "
            "или импортируйте из Billings: flask pls import-staff-from-billings."
        )
    return report
