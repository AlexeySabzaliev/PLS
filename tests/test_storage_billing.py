"""Расчёт площади и storage billing (порт тестов Billings)."""
from datetime import date
from decimal import Decimal

import pytest

from app.modules.billing import storage_strategy as ss
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
    # Со 2 июля значение 50 переносится на все оставшиеся календарные дни (включая выходные)
    assert avg * Decimal(31) == Decimal(100) + Decimal(50) * Decimal(30)


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


class _FrozenDate(date):
    _frozen = date(2026, 9, 10)

    @classmethod
    def today(cls):
        return cls._frozen


@pytest.fixture
def frozen_today(monkeypatch):
    monkeypatch.setattr(ss, "date", _FrozenDate)
    return _FrozenDate


def test_billing_end_limits_to_today(frozen_today):
    assert ss._billing_end(date(2026, 9, 1), date(2026, 9, 30), False) == date(2026, 9, 10)
    assert ss._billing_end(date(2026, 8, 1), date(2026, 8, 31), False) == date(2026, 8, 31)
    assert ss._billing_end(date(2026, 9, 1), date(2026, 9, 30), True) == date(2026, 9, 30)


def test_provisional_fixed_area_charges_only_elapsed_days(frozen_today):
    """Предварительный биллинг текущего месяца: хранение за 10 дней, а не за 30."""
    tariffs = [{
        "billing_line_code": "storage_area_fixed",
        "rate_ex_vat": "24",
        "valid_from": date(2026, 9, 1),
        "valid_to": None,
        "formula": "rate_times_days_times_qty",
        "unit_code": "m2",
        "quantity_source": "auto_contract_param",
        "sort_order": 11,
    }]
    contract = {"id": 1, "billing_config": {"area_mode": "two_tier", "fixed_m2days": 9435}}
    lines = StorageBillingStrategy().calculate(
        contract, 2026, 9, tariffs, [], [], [],
        period_start=date(2026, 9, 1), period_end=date(2026, 9, 30), is_final=False,
    )
    fixed = [line for line in lines if line.line_code == "storage_area_fixed"][0]
    assert fixed.days_count == 10
    assert fixed.amount_ex_vat == Decimal("9435") * Decimal("24") * Decimal("10")


def test_extra_vehicle_docs_line_pulled_from_vehicle_columns():
    """Строка ДС «Доп. комплекты ТС» не должна теряться: значения в колонке ТС."""
    tariffs = [{
        "billing_line_code": "extra_vehicle_docs",
        "name": "Дополнительные комплекты ТСД",
        "rate_ex_vat": "109.52",
        "valid_from": date(2026, 8, 1),
        "valid_to": None,
        "unit_code": "vehicle",
        "report_role": "transport_logistics",
        "report_scope": "vehicle",
        "quantity_source": "auto_vehicle",
        "sort_order": 61,
    }]
    operations = [
        {"operation_date": date(2026, 8, 3), "extra_document_set_qty": 2, "report_quantities": {}},
        {"operation_date": date(2026, 8, 4), "extra_document_set_qty": 1, "report_quantities": {}},
    ]
    contract = {"id": 1, "billing_config": {"area_mode": "two_tier"}}
    lines = StorageBillingStrategy().calculate(
        contract, 2026, 8, tariffs, operations, [], [],
        period_start=date(2026, 8, 1), period_end=date(2026, 8, 31), is_final=True,
    )
    line = [x for x in lines if x.line_code == "extra_vehicle_docs"][0]
    assert line.quantity == Decimal("3")
    assert line.amount_ex_vat == Decimal("3") * Decimal("109.52")
