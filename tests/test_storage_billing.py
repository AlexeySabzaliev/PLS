"""Расчёт площади и storage billing (порт тестов Billings)."""
from datetime import date
from decimal import Decimal

from app.modules.billing.storage_strategy import (
    StorageBillingStrategy,
    _contract_reserved_area_m2,
)
from app.modules.uss.services.tariff_quantity import avg_inventory_area_m2


def test_reserved_area_august():
    contract = {"billing_config": {"fixed_m2days": 9435}}
    m2 = _contract_reserved_area_m2(contract, date(2026, 8, 31))
    assert m2 == Decimal("9435")
    assert Decimal("24") * m2 * Decimal("31") == Decimal("7019640")


def test_avg_extra_area_dict_entries():
    shifts = [
        {"report_date": date(2026, 7, 1), "area_entries": {"storage_area_extra": 100}},
        {"report_date": date(2026, 7, 2), "area_entries": {"storage_area_extra": 50}},
    ]
    avg = avg_inventory_area_m2(
        shifts, date(2026, 7, 1), date(2026, 7, 31), 31, "storage_area_extra",
    )
    assert avg == Decimal("75")


def test_storage_billing_fixed_area_line():
    tariffs = [{
        "billing_line_code": "storage_area_fixed",
        "rate_ex_vat": "24",
        "valid_from": date(2026, 7, 1),
        "valid_to": None,
        "formula": "rate_times_days_times_qty",
        "unit_code": "m2",
        "quantity_source": "auto_contract_param",
        "sort_order": 11,
    }]
    contract = {"id": 1, "billing_config": {"area_mode": "two_tier", "fixed_m2days": 9435}}
    lines = StorageBillingStrategy().calculate(
        contract, 2026, 7, tariffs, [], [], [],
    )
    fixed = [line for line in lines if line.line_code == "storage_area_fixed"][0]
    assert fixed.quantity == Decimal("9435")
    assert fixed.days_count == 31
    assert fixed.amount_ex_vat == Decimal("7019640")
