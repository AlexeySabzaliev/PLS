"""Расчёт биллинга по договору."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.db import db
from app.modules.billing.aggregates import load_vehicle_operations
from app.modules.billing.storage_strategy import StorageBillingStrategy, billing_line_to_dict
from app.modules.billing.tariffs import diagnose_tariffs_for_billing_period, tariffs_for_billing_period
from app.modules.reference.models import Contract, ProductType
from app.modules.uss.models import ShiftReport
from app.modules.uss.services.shift_day_confirm import is_day_confirmed


def _month_bounds(period_from: date, period_to: date) -> tuple[int, int]:
    if period_from.year == period_to.year and period_from.month == period_to.month:
        return period_from.year, period_from.month
    return period_from.year, period_from.month


def load_contract_dict(contract_id: int) -> dict | None:
    contract = db.session.get(Contract, contract_id)
    if not contract:
        return None
    pt = db.session.get(ProductType, contract.product_type_id)
    return {
        "id": contract.id,
        "number": contract.number,
        "warehouse_id": contract.warehouse_id,
        "product_type_code": pt.code if pt else "",
        "billing_config": contract.billing_config or {},
    }


def load_shifts(warehouse_id: int, period_start: date, period_end: date) -> list[dict]:
    """Складские отчёты с информацией о подтверждении дня."""
    from app.modules.uss.services.shift_day_confirm import day_summary
    
    rows = (
        ShiftReport.query.filter(
            ShiftReport.warehouse_id == warehouse_id,
            ShiftReport.report_date >= period_start,
            ShiftReport.report_date <= period_end,
        )
        .order_by(ShiftReport.report_date)
        .all()
    )
    result = []
    for r in rows:
        summary = day_summary(warehouse_id, r.report_date)
        result.append({
            "report_date": r.report_date,
            "area_entries": r.area_entries or {},
            "extra_entries": r.extra_entries or {},
            "is_day_confirmed": is_day_confirmed(warehouse_id, r.report_date),
        })
    return result


class BillingCalculator:
    """Калькулятор биллинга ОХ (модель Аристон)."""

    def __init__(self, process_line_id: int | None = None):
        self.process_line_id = process_line_id

    def calculate_period(
        self,
        contract_id: int,
        period_from: date,
        period_to: date,
    ) -> dict:
        contract = load_contract_dict(contract_id)
        if not contract:
            return {"status": "error", "message": "Договор не найден", "error": "contract_not_found"}

        if period_from > period_to:
            return {
                "status": "error",
                "message": "Начало периода не может быть позже конца периода",
                "error": "invalid_period",
            }

        period_start = period_from
        period_end = period_to
        year, month = period_start.year, period_start.month

        tariffs = tariffs_for_billing_period(contract_id, period_start, period_end)
        if not tariffs:
            diag = diagnose_tariffs_for_billing_period(contract_id, period_start, period_end)
            return {
                "status": "error",
                "message": diag["message"] if diag else (
                    "Нет активных ставок за период — добавьте ДС со ставками "
                    "или проверьте даты действия."
                ),
                "error": diag["error"] if diag else "no_tariffs",
            }
        operations = load_vehicle_operations(
            contract_id, contract["warehouse_id"], period_start, period_end,
        )
        shifts = load_shifts(contract["warehouse_id"], period_start, period_end)

        lines = StorageBillingStrategy().calculate(
            contract, year, month, tariffs, operations, shifts,
            period_start=period_start,
            period_end=period_end,
            is_final=False,  # Предварительный биллинг - считаем только до текущей даты
        )
        total = sum((line.amount_ex_vat for line in lines), Decimal("0"))
        by_code = {line.line_code: billing_line_to_dict(line) for line in lines}

        return {
            "status": "ok",
            "contract_id": contract_id,
            "period_from": period_start.isoformat(),
            "period_to": period_end.isoformat(),
            "process_line_id": self.process_line_id,
            "lines": [billing_line_to_dict(line) for line in lines],
            "lines_by_code": by_code,
            "total_ex_vat": float(total),
        }
