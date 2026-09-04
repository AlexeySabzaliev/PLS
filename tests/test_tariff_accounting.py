"""Вид учёта ставки: accounting_kind ↔ поля БД."""
from app.modules.uss.services.tariff_accounting import (
    apply_accounting_kind,
    tariff_accounting_kind,
)


def test_tariff_accounting_kind_auto_contract():
    assert tariff_accounting_kind({"quantity_source": "auto_contract_param"}) == "auto_contract"


def test_tariff_accounting_kind_vehicle_extra():
    t = {"quantity_source": "manual_vehicle", "report_scope": "vehicle"}
    assert tariff_accounting_kind(t) == "vehicle_extra"


def test_tariff_accounting_kind_daily_extra_inventory():
    t = {
        "quantity_source": "manual_inventory",
        "report_role": "inventory_management",
        "report_scope": "period",
    }
    assert tariff_accounting_kind(t) == "daily_extra"


def test_apply_accounting_kind_vehicle_extra():
    out = apply_accounting_kind({
        "accounting_kind": "vehicle_extra",
        "is_custom": True,
    })
    assert out["quantity_source"] == "manual_vehicle"
    assert out["report_scope"] == "vehicle"
    assert out["report_role"] == "transport_logistics"


def test_apply_accounting_kind_daily_warehouse():
    out = apply_accounting_kind({
        "accounting_kind": "daily_extra",
        "report_role": "warehouse_logistics",
        "is_custom": True,
    })
    assert out["quantity_source"] == "manual_daily"
    assert out["report_scope"] == "period"
    assert out["report_role"] == "warehouse_logistics"


def test_apply_accounting_kind_daily_inventory():
    out = apply_accounting_kind({
        "accounting_kind": "daily_extra",
        "report_role": "inventory_management",
        "is_custom": True,
    })
    assert out["quantity_source"] == "manual_inventory"
