"""Парсинг ДС Гауф: ручная обработка и паллетирование."""
from pathlib import Path

import pytest

from app.modules.reference.amendment_docx_import import parse_amendment_docx

GAUFF_DOCX = Path(__file__).resolve().parent / "fixtures" / "amendments" / "ДС 3 к Договору Х-30-2025_270826 (2).docx"


@pytest.mark.skipif(not GAUFF_DOCX.exists(), reason="Нет fixture DOCX Гауф")
def test_gauff_ds3_tariffs():
    parsed = parse_amendment_docx(GAUFF_DOCX.read_bytes(), GAUFF_DOCX.name)
    by_code = {t.billing_line_code: t for t in parsed.tariffs}

    assert "manual_m3" in by_code
    assert float(by_code["manual_m3"].rate) == 250.0
    assert by_code["manual_m3"].unit_code == "m3"

    assert "mechanized_m3" in by_code
    assert float(by_code["mechanized_m3"].rate) == 180.0

    assert "custom_pallet" in by_code
    assert float(by_code["custom_pallet"].rate) == pytest.approx(477.30)
    assert by_code["custom_pallet"].unit_code == "pcs"
    assert "паллет" in by_code["custom_pallet"].name.lower()

    assert "overtime_m3" not in by_code

    assert float(by_code["vehicle_docs"].rate) == 100.0
    assert float(by_code["repack_units"].rate) == 220.0
