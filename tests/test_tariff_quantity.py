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
    resolve_tariff_quantity_source,
    resolve_tariff_period_quantity,
    unit_display_label,
)
from app.modules.uss.services.tariff_report import tariff_in_role_report


def test_unit_display_label():
    assert unit_display_label("pcs") == "шт."
    assert unit_display_label("pcs", name="шт.") == "шт."
    assert unit_display_label("m3") == "м³"
    assert unit_display_label(None) == ""


def test_billing_line_code_choices_catalog():
    choices = billing_line_code_choices()
    assert len(choices) >= 15
    fixed = next(c for c in choices if c["value"] == "storage_area_fixed")
    assert "Хранение на площади (фикс)" in fixed["label"]
    assert fixed["unit_code"] == "m2"
    assert fixed["quantity_source"] == "auto_contract_param"
    rf = next(c for c in choices if c["value"] == "extra_vehicle_docs_rf")
    assert "РФ" in rf["label"]
    assert rf["quantity_source"] == "manual_vehicle"
    assert rf["report_role"] == "transport_logistics"
    rb = next(c for c in choices if c["value"] == "extra_vehicle_docs_rb")
    assert "РБ" in rb["label"]
    assert rb["report_scope"] == "vehicle"


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


def test_resolve_tariff_quantity_source_manual_by_role():
    assert resolve_tariff_quantity_source(
        quantity_source="manual",
        report_role="warehouse_logistics",
        report_scope="period",
        is_custom=True,
    ) == "manual_daily"
    assert resolve_tariff_quantity_source(
        quantity_source="manual",
        report_role="transport_logistics",
        report_scope="vehicle",
        is_custom=True,
    ) == "manual_vehicle"
    assert resolve_tariff_quantity_source(
        quantity_source="manual",
        report_role="inventory_management",
        report_scope="period",
        is_custom=True,
    ) == "manual_inventory"


def test_custom_tariff_keeps_user_transport_role():
    """Доп. ставка: роль/место ввода из справочника не перетираются реестром кодов."""
    t = apply_tariff_defaults({
        "billing_line_code": "valve_gluing",
        "name": "Подклейка клапанов",
        "report_role": "transport_logistics",
        "report_scope": "vehicle",
        "quantity_source": "manual_vehicle",
        "is_custom": True,
    })
    assert t["report_role"] == "transport_logistics"
    assert t["report_scope"] == "vehicle"
    assert effective_quantity_source(t) == "manual_vehicle"
    assert tariff_in_role_report(t, "transport_logistics")


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


def test_vehicle_docs_sums_billing_document_qty():
    from app.modules.uss.services.tariff_quantity import auto_vehicle_quantity

    ops = [
        {"operation_date": date(2026, 8, 1), "billing_document_qty": 3},
        {"operation_date": date(2026, 8, 2), "billing_document_qty": 1},
    ]
    assert auto_vehicle_quantity("vehicle_docs", ops) == Decimal("4")
