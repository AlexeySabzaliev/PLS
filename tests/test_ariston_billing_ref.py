"""Сверка эталонного Excel биллинга Аристон (без БД)."""
from decimal import Decimal

import pytest

from app.seeds.ariston_august import resolve_august_excel_path
from app.seeds.billing_excel_ref import (
    CANONICAL_AUGUST_2026_PRR,
    assert_prr_matches_billing,
    dedupe_prr_rows,
    read_billing_reference,
    read_prr_rows,
    summarize_prr_handling_m3,
)


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
    assert lines["valve_gluing"]["qty"] == Decimal("374")
    assert lines["flue_stickering"]["qty"] == Decimal("1595")


@pytest.mark.skipif(resolve_august_excel_path() is None, reason="Нет Ariston billing 08.2026.xlsx")
def test_august_prr_volumes_match_billing_sheet():
    """Объёмы ПРР (после дедупа и слияния накладных) = строки 2/3 Billing."""
    path = resolve_august_excel_path()
    manual, mech = assert_prr_matches_billing(path, month=8)
    assert manual == CANONICAL_AUGUST_2026_PRR["manual_m3"]
    assert mech == CANONICAL_AUGUST_2026_PRR["mechanized_m3"]


@pytest.mark.skipif(resolve_august_excel_path() is None, reason="Нет Ariston billing 08.2026.xlsx")
def test_august_prr_has_no_exact_duplicates():
    path = resolve_august_excel_path()
    rows, skipped = dedupe_prr_rows(read_prr_rows(path))
    assert len(rows) == 95
    assert skipped == 0
    manual, mech = summarize_prr_handling_m3(rows)
    assert manual == Decimal("2867.014")
    assert mech == Decimal("1564.572")
