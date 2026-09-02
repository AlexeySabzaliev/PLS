"""Тесты ставок Аристон и конверсии в биллинг."""
from decimal import Decimal

from app.modules.uss.services.tariff_billing import operational_to_billing_quantity
from app.seeds.ariston_tariffs import ARISTON_TARIFF_SPECS, ensure_ariston_tariffs


def test_ariston_vietnam_stickering_divisor():
    spec = next(s for s in ARISTON_TARIFF_SPECS if s.billing_line_code == "vietnam_stickering")
    assert spec.rate_line_code == "repack_units"
    assert spec.quantity_divisor == "8"
    tariff = {
        "billing_line_code": spec.billing_line_code,
        "rate_line_code": spec.rate_line_code,
        "quantity_divisor": spec.quantity_divisor,
    }
    code, qty = operational_to_billing_quantity(tariff, Decimal("80"))
    assert code == "repack_units"
    assert qty == Decimal("10")


def test_ariston_flue_stickering_divisor():
    spec = next(s for s in ARISTON_TARIFF_SPECS if s.billing_line_code == "flue_stickering")
    tariff = {
        "billing_line_code": spec.billing_line_code,
        "rate_line_code": spec.rate_line_code,
        "quantity_divisor": spec.quantity_divisor,
    }
    code, qty = operational_to_billing_quantity(tariff, Decimal("100"))
    assert code == "repack_units"
    assert qty == Decimal("10")


def test_ensure_ariston_tariffs_idempotent(app):
    with app.app_context():
        from app.modules.reference.models import Contract, ContractAmendment, TariffRule

        contract = Contract.query.first()
        am = ContractAmendment.query.filter_by(contract_id=contract.id).first()
        before = TariffRule.query.filter_by(contract_id=contract.id).count()
        added = ensure_ariston_tariffs(contract.id, am.id)
        after = TariffRule.query.filter_by(contract_id=contract.id).count()
        assert added >= 0
        assert after >= before
        codes = {t.billing_line_code for t in TariffRule.query.filter_by(contract_id=contract.id).all()}
        assert "repack_units" in codes
        assert "vietnam_stickering" in codes
        assert "extra_vehicle_docs_rf" in codes
