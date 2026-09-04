"""Сверка биллинга Аристон август 2026: БД vs Excel."""
from datetime import date
from decimal import Decimal

import pytest

from app.modules.billing.calculator import BillingCalculator
from app.seeds.ariston_august import resolve_august_excel_path, seed_ariston_strelna_august
from app.seeds.billing_excel_ref import read_billing_reference
from app.seeds.bootstrap import seed_reference
from app.seeds.fix_ariston_canonical import CANONICAL_CONTRACT_NUMBER, fix_ariston_canonical
from app.modules.reference.models import Contract

TOLERANCE = Decimal("0.02")


@pytest.mark.skipif(resolve_august_excel_path() is None, reason="Нет Ariston billing 08.2026.xlsx")
def test_ariston_august_billing_matches_excel(migrated_app):
    with migrated_app.app_context():
        seed_reference()
        fix_ariston_canonical(dry_run=False, with_ds5=False)
        excel_path = resolve_august_excel_path()
        seed_ariston_strelna_august(excel_path=excel_path)
        contract = Contract.query.filter(
            Contract.number.ilike(f"%{CANONICAL_CONTRACT_NUMBER}%")
        ).first()
        assert contract is not None

        result = BillingCalculator().calculate_period(
            contract.id,
            date(2026, 8, 1),
            date(2026, 8, 31),
        )
        assert result["status"] == "ok"

        ref_lines, ref_total, _ = read_billing_reference(excel_path, month=8)

        calc_total = Decimal(str(result["total_ex_vat"])).quantize(Decimal("0.01"))
        assert abs(calc_total - ref_total) <= Decimal("100"), (
            f"итого {calc_total} vs эталон {ref_total}"
        )

        by_code = {line["line_code"]: line for line in result["lines"]}
        for code in (
            "storage_area_fixed",
            "storage_area_extra",
            "manual_m3",
            "mechanized_m3",
            "vehicle_docs",
            "extra_vehicle_docs",
            "elco_passports",
            "repack_units",
            "valve_gluing",
            "flue_stickering",
        ):
            if code not in ref_lines:
                continue
            ref = ref_lines[code]
            line = by_code[code]
            tol_amt = Decimal("100") if code in ("manual_m3", "mechanized_m3") else TOLERANCE
            assert abs(Decimal(str(line["amount_ex_vat"])) - ref["amount"]) <= tol_amt, code
            assert abs(Decimal(str(line["quantity"])) - ref["qty"]) <= Decimal("0.02"), code
