"""Сверка эталонного Excel биллинга Аристон (без БД)."""
from decimal import Decimal

import pytest

from app.seeds.ariston_august import resolve_august_excel_path
from app.seeds.billing_excel_ref import read_billing_reference


@pytest.mark.skipif(resolve_august_excel_path() is None, reason="Нет Ariston billing 08.2026.xlsx")
def test_august_billing_reference_total():
    path = resolve_august_excel_path()
    lines, total, two_tier = read_billing_reference(path, month=8)
    assert two_tier is True
    assert total == Decimal("9899958.14")
    assert lines["storage_area_fixed"]["amount"] == Decimal("7019640")
    assert lines["storage_area_extra"]["amount"] == Decimal("1711200")
    assert lines["manual_m3"]["qty"] == Decimal("2867.014")
    assert lines["mechanized_m3"]["qty"] == Decimal("1564.572")
    assert lines["vehicle_docs"]["qty"] == Decimal("94")
    assert lines["extra_vehicle_docs"]["qty"] == Decimal("116")
    assert lines["elco_passports"]["qty"] == Decimal("67")
    assert lines["repack_units"]["qty"] == Decimal("107")
