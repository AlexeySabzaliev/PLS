"""Тесты реестра источников количеств и схемы отчётов."""
from datetime import date
from decimal import Decimal

from app.modules.uss.services.tariff_quantity import (
    apply_tariff_defaults,
    billing_line_code_choices,
    collect_manual_quantity_warnings,
    effective_quantity_source,
    needs_manual_inventory_input,
    needs_manual_vehicle_input,
    resolve_tariff_period_quantity,
)
from app.modules.uss.services.tariff_report import tariff_in_role_report


def test_billing_line_code_choices_catalog():
    choices = billing_line_code_choices()
    assert len(choices) >= 15
    fixed = next(c for c in choices if c["value"] == "storage_area_fixed")
    assert "Хранение на площади (фикс)" in fixed["label"]
    assert fixed["unit_code"] == "m2"
    assert fixed["quantity_source"] == "auto_contract_param"


def test_storage_area_fixed_never_gets_report_role():
    t = apply_tariff_defaults({
        "billing_line_code": "storage_area_fixed",
        "report_role": "inventory_management",
        "accounting_mode": "inventory_management",
    })
    assert effective_quantity_source(t) == "auto_contract_param"
    assert t["report_role"] is None


def test_auto_vehicle_codes_never_get_report_role():
    for code in ("manual_m3", "vehicle_docs", "overtime_m3"):
        t = apply_tariff_defaults({
            "billing_line_code": code,
            "report_role": "transport_logistics",
            "accounting_mode": "transport_logistics",
        })
        assert effective_quantity_source(t) == "auto_vehicle"
        assert t["report_role"] is None


def test_standard_manual_m3_is_auto_vehicle():
    t = apply_tariff_defaults({"billing_line_code": "manual_m3"})
    assert effective_quantity_source(t) == "auto_vehicle"
    assert not needs_manual_vehicle_input(t)


def test_custom_vehicle_scope_is_manual_vehicle():
    t = apply_tariff_defaults({
        "billing_line_code": "custom_valve",
        "report_role": "transport_logistics",
        "report_scope": "vehicle",
        "is_custom": True,
    })
    assert effective_quantity_source(t) == "manual_vehicle"
    assert needs_manual_vehicle_input(t)


def test_storage_area_extra_is_manual_inventory():
    t = apply_tariff_defaults({"billing_line_code": "storage_area_extra"})
    assert effective_quantity_source(t) == "manual_inventory"
    assert needs_manual_inventory_input(t)


def test_elco_is_manual_daily_warehouse():
    t = apply_tariff_defaults({"billing_line_code": "elco_drain_hours"})
    assert effective_quantity_source(t) == "manual_daily"
    assert t["report_role"] == "warehouse_logistics"


def test_custom_pallet_is_manual_vehicle_transport():
    t = apply_tariff_defaults({"billing_line_code": "custom_pallet"})
    assert t["report_role"] == "transport_logistics"
    assert effective_quantity_source(t) == "manual_vehicle"
    assert needs_manual_vehicle_input(t)


def test_custom_pallet_fixes_stale_inventory_role():
    t = apply_tariff_defaults({
        "billing_line_code": "custom_pallet",
        "report_role": "inventory_management",
        "quantity_source": "manual_inventory",
    })
    assert t["report_role"] == "transport_logistics"
    assert effective_quantity_source(t) == "manual_vehicle"


def test_custom_transport_role_gets_manual_vehicle():
    t = apply_tariff_defaults({
        "billing_line_code": "custom_fee",
        "accounting_mode": "transport_logistics",
        "is_custom": True,
    })
    assert t["report_role"] == "transport_logistics"
    assert effective_quantity_source(t) == "manual_vehicle"
    assert needs_manual_vehicle_input(t)


def test_repack_units_defaults_inventory_role():
    t = apply_tariff_defaults({"billing_line_code": "repack_units"})
    assert effective_quantity_source(t) == "manual_inventory"
    assert t["report_role"] == "inventory_management"
    assert needs_manual_inventory_input(t)


def test_extra_manual_m3_is_separate_auto_line():
    t = apply_tariff_defaults({"billing_line_code": "extra_manual_m3"})
    assert effective_quantity_source(t) == "auto_vehicle"
    assert t["report_role"] is None


def test_custom_warehouse_role_gets_manual_daily():
    t = apply_tariff_defaults({
        "billing_line_code": "custom_fee",
        "accounting_mode": "warehouse_logistics",
        "is_custom": True,
    })
    assert t["report_role"] == "warehouse_logistics"
    assert effective_quantity_source(t) == "manual_daily"


def test_manual_quantity_warning_when_zero_with_activity():
    tariffs = [{
        "billing_line_code": "repack_units",
        "name": "Переупаковка",
        "quantity_source": "manual_inventory",
    }]
    warnings = collect_manual_quantity_warnings(
        tariffs,
        operations=[{"operation_date": date(2026, 7, 1)}],
        shifts=[{"report_date": date(2026, 7, 1), "extra_entries": []}],
        daily_totals={},
        vehicle_qty={},
        extra_totals={},
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31),
    )
    assert len(warnings) == 1
    assert "repack_units" in warnings[0]


def test_resolve_manual_inventory_without_double_count():
    tariff = {"billing_line_code": "repack_units", "quantity_source": "manual_inventory"}
    qty = resolve_tariff_period_quantity(
        tariff,
        operations=[],
        shifts=[],
        daily_totals={},
        vehicle_qty={},
        extra_totals={"repack_units": Decimal("10")},
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31),
    )
    assert qty == Decimal("10")


def test_no_manual_warning_when_quantity_present():
    tariffs = [{
        "billing_line_code": "repack_units",
        "name": "Переупаковка",
        "quantity_source": "manual_inventory",
    }]
    warnings = collect_manual_quantity_warnings(
        tariffs,
        operations=[],
        shifts=[{"report_date": date(2026, 7, 1), "extra_entries": []}],
        daily_totals={},
        vehicle_qty={},
        extra_totals={"repack_units": Decimal("5")},
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31),
    )
    assert warnings == []


def test_tariff_in_role_report_filters_auto_and_foreign_role():
    assert not tariff_in_role_report(
        apply_tariff_defaults({"billing_line_code": "manual_m3", "report_role": "transport_logistics"}),
        "transport_logistics",
    )
    assert tariff_in_role_report(
        apply_tariff_defaults({
            "billing_line_code": "custom_fee",
            "accounting_mode": "warehouse_logistics",
            "is_custom": True,
        }),
        "warehouse_logistics",
    )
    assert not tariff_in_role_report(
        apply_tariff_defaults({
            "billing_line_code": "custom_fee",
            "accounting_mode": "warehouse_logistics",
            "is_custom": True,
        }),
        "transport_logistics",
    )


def test_avg_inventory_area_from_dict_entries():
    from app.modules.uss.services.tariff_quantity import avg_inventory_area_m2

    shifts = [
        {"report_date": date(2026, 7, 1), "area_entries": {"storage_area_extra": 100}},
        {"report_date": date(2026, 7, 2), "area_entries": {"storage_area_extra": 200}},
    ]
    avg = avg_inventory_area_m2(
        shifts,
        date(2026, 7, 1),
        date(2026, 7, 31),
        31,
        "storage_area_extra",
    )
    assert avg == Decimal("150")


def test_effective_source_inventory_overrides_wrong_daily():
    t = {
        "billing_line_code": "repack_units",
        "report_role": "inventory_management",
        "quantity_source": "manual_daily",
    }
    assert effective_quantity_source(t) == "manual_inventory"
    assert needs_manual_inventory_input(t)


def test_effective_source_transport_vehicle_from_scope():
    t = {
        "billing_line_code": "elco_passports",
        "report_role": "transport_logistics",
        "report_scope": "vehicle",
        "quantity_source": "manual_daily",
    }
    assert effective_quantity_source(t) == "manual_vehicle"
    assert needs_manual_vehicle_input(t)


def test_effective_source_transport_daily_from_scope():
    t = {
        "billing_line_code": "custom_valve",
        "report_role": "transport_logistics",
        "report_scope": "period",
        "quantity_source": "manual_vehicle",
    }
    assert effective_quantity_source(t) == "manual_daily"


def test_tariff_in_role_report_includes_transport_extras_with_stale_source():
    t = apply_tariff_defaults({
        "billing_line_code": "elco_passports",
        "report_role": "transport_logistics",
        "report_scope": "vehicle",
        "quantity_source": "manual_daily",
        "is_custom": True,
    })
    assert tariff_in_role_report(t, "transport_logistics")
    assert needs_manual_vehicle_input(t)


def test_tariff_in_role_report_includes_inventory_with_stale_daily_source():
    t = apply_tariff_defaults({
        "billing_line_code": "repack_units",
        "report_role": "inventory_management",
        "quantity_source": "manual_daily",
    })
    assert tariff_in_role_report(t, "inventory_management")
    assert needs_manual_inventory_input(t)
