"""Ставки демо-договора Аристон (операционный ввод → биллинг)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.db import db
from app.modules.reference.models import TariffRule, UnitOfMeasure
from app.modules.uss.services.tariff_codes import formula_for_code


@dataclass(frozen=True)
class AristonTariffSpec:
    billing_line_code: str
    name: str
    unit_code: str
    report_role: str | None
    quantity_source: str
    report_scope: str | None = None
    rate_line_code: str | None = None
    quantity_divisor: str = "1"
    sort_order: int = 0
    is_custom: bool = False
    rate_ex_vat: str | None = None


# Ставки без НДС (эталон Billings / август 2026)
ARISTON_RATE_EX_VAT: dict[str, str] = {
    "storage_area_fixed": "24",
    "storage_area_extra": "24",
    "manual_m3": "250",
    "mechanized_m3": "180",
    "vehicle_docs": "109.52",
    "extra_vehicle_docs": "109.52",
    "extra_vehicle_docs_rf": "109.52",
    "extra_vehicle_docs_rb": "109.52",
    "elco_passports": "109.52",
    "repack_units": "219.04",
    "flue_stickering": "21.904",
    "vietnam_stickering": "27.38",
    "overtime_m3": "438.08",
    "inventory_hours": "985.68",
    "elco_drain_hours": "985.68",
    "extra_manual_m3": "250",
}


# Дополнительные ставки ДС-6/2024 (раздел «Дополнительные» в справочнике, is_custom=True)
ARISTON_DS6_EXTRA_CODES = frozenset({
    "extra_vehicle_docs",
    "elco_passports",
    "valve_gluing",
    "flue_stickering",
    "elco_drain_hours",
})


# Операционный учёт и привязка к тарифу биллинга (repack_units / vehicle_docs).
ARISTON_TARIFF_SPECS: tuple[AristonTariffSpec, ...] = (
    # --- Основные (ДС-6) ---
    AristonTariffSpec(
        "storage_area_fixed",
        "Площадь хранения, фиксированный объём, м²",
        "m2",
        None,
        "auto_contract_param",
        sort_order=11,
        rate_ex_vat="24",
    ),
    AristonTariffSpec(
        "storage_area_extra",
        "Площадь хранения, дополнительный объём, м²",
        "m2",
        "inventory_management",
        "manual_inventory",
        sort_order=12,
        rate_ex_vat="24",
    ),
    AristonTariffSpec(
        "manual_m3",
        "Ручная обработка (вход и выход), м³",
        "m3",
        "transport_logistics",
        "auto_vehicle",
        sort_order=20,
        rate_ex_vat="250",
    ),
    AristonTariffSpec(
        "extra_manual_m3",
        "Доп. ручная обработка (поле ТС), м³",
        "m3",
        "transport_logistics",
        "auto_vehicle",
        sort_order=21,
        rate_ex_vat="250",
    ),
    AristonTariffSpec(
        "mechanized_m3",
        "Механизированная обработка (вход и выход), м³",
        "m3",
        "transport_logistics",
        "auto_vehicle",
        sort_order=30,
        rate_ex_vat="180",
    ),
    AristonTariffSpec(
        "overtime_m3",
        "Сверхурочная обработка (вход и выход), м³",
        "m3",
        "transport_logistics",
        "auto_vehicle",
        sort_order=35,
        rate_ex_vat="438.08",
    ),
    AristonTariffSpec(
        "vehicle_docs",
        "Количество пакетов документов (машин)",
        "vehicle",
        "transport_logistics",
        "auto_vehicle",
        sort_order=40,
        rate_ex_vat="109.52",
    ),
    AristonTariffSpec(
        "repack_units",
        "Переупаковка (единиц приборов)",
        "pcs",
        "inventory_management",
        "manual_inventory",
        sort_order=50,
        rate_ex_vat="219.04",
    ),
    AristonTariffSpec(
        "inventory_hours",
        "Инвентаризация (чел./час)",
        "hour",
        "inventory_management",
        "manual_inventory",
        sort_order=60,
        rate_ex_vat="985.68",
    ),
    # --- ДС-6: дополнительные ---
    AristonTariffSpec(
        "extra_vehicle_docs",
        "Дополнительные комплекты ТСД = 1:1 Количество пакетов документов (машин)",
        "vehicle",
        "transport_logistics",
        "auto_vehicle",
        sort_order=61,
        rate_line_code="vehicle_docs",
        quantity_divisor="1",
        is_custom=True,
        rate_ex_vat="109.52",
    ),
    AristonTariffSpec(
        "elco_passports",
        "Паспорта ELCO = 1:1 Количество пакетов документов (машин)",
        "vehicle",
        "transport_logistics",
        "manual_vehicle",
        "vehicle",
        rate_line_code="vehicle_docs",
        quantity_divisor="1",
        sort_order=62,
        is_custom=True,
        rate_ex_vat="109.52",
    ),
    AristonTariffSpec(
        "valve_gluing",
        "Подклейка клапанов гофрокоробов = 1:1 Переупаковка (единиц приборов)",
        "pcs",
        "warehouse_logistics",
        "manual_daily",
        rate_line_code="repack_units",
        quantity_divisor="1",
        sort_order=63,
        is_custom=True,
        rate_ex_vat="109.52",
    ),
    AristonTariffSpec(
        "flue_stickering",
        "Стикерование дымоходов = 10:1 Переупаковка (единиц приборов)",
        "pcs",
        "warehouse_logistics",
        "manual_daily",
        rate_line_code="repack_units",
        quantity_divisor="10",
        sort_order=64,
        is_custom=True,
        rate_ex_vat="21.904",
    ),
    AristonTariffSpec(
        "elco_drain_hours",
        "Слив технологической жидкости с котлов ELCO",
        "hour",
        "warehouse_logistics",
        "manual_daily",
        sort_order=65,
        is_custom=True,
        rate_ex_vat="985.68",
    ),
    # --- Операционные (вне ДС-6, при необходимости вручную) ---
    AristonTariffSpec(
        "extra_vehicle_docs_rf",
        "Дополнительные комплекты РФ (на ТС)",
        "vehicle",
        "transport_logistics",
        "manual_vehicle",
        "vehicle",
        rate_line_code="vehicle_docs",
        quantity_divisor="1",
        sort_order=71,
        rate_ex_vat="109.52",
    ),
    AristonTariffSpec(
        "extra_vehicle_docs_rb",
        "Дополнительные комплекты РБ (на ТС)",
        "vehicle",
        "transport_logistics",
        "manual_vehicle",
        "vehicle",
        rate_line_code="vehicle_docs",
        quantity_divisor="1",
        sort_order=72,
        rate_ex_vat="109.52",
    ),
    AristonTariffSpec(
        "vietnam_stickering",
        "Дополнительное стикерование Вьетнам",
        "pcs",
        "warehouse_logistics",
        "manual_daily",
        rate_line_code="repack_units",
        quantity_divisor="8",
        sort_order=73,
        rate_ex_vat="27.38",
    ),
)


def ariston_spec_by_code(code: str) -> AristonTariffSpec | None:
    for spec in ARISTON_TARIFF_SPECS:
        if spec.billing_line_code == code:
            return spec
    return None


def _apply_spec_to_row(row: TariffRule, spec: AristonTariffSpec, units: dict[str, UnitOfMeasure]) -> bool:
    """Обновить существующую ставку по канонической спецификации. Возвращает True, если были изменения."""
    changed = False
    unit = units.get(spec.unit_code)
    if unit and row.unit_id != unit.id:
        row.unit_id = unit.id
        changed = True
    if spec.name and row.name != spec.name:
        row.name = spec.name
        changed = True
    if row.report_role != spec.report_role:
        row.report_role = spec.report_role
        changed = True
    if row.report_scope != spec.report_scope:
        row.report_scope = spec.report_scope
        changed = True
    if row.quantity_source != spec.quantity_source:
        row.quantity_source = spec.quantity_source
        changed = True
    if row.rate_line_code != spec.rate_line_code:
        row.rate_line_code = spec.rate_line_code
        changed = True
    expected_divisor = Decimal(spec.quantity_divisor)
    if row.quantity_divisor != expected_divisor:
        row.quantity_divisor = expected_divisor
        changed = True
    if row.is_custom != spec.is_custom:
        row.is_custom = spec.is_custom
        changed = True
    if row.sort_order != spec.sort_order:
        row.sort_order = spec.sort_order
        changed = True
    if not row.formula:
        row.formula = formula_for_code(spec.billing_line_code)
        changed = True
    return changed


def sync_ariston_tariff_specs(contract_id: int, amendment_id: int | None = None) -> int:
    """Привести существующие ставки Аристон к ARISTON_TARIFF_SPECS."""
    units = {u.code: u for u in UnitOfMeasure.query.all()}
    updated = 0
    for spec in ARISTON_TARIFF_SPECS:
        query = TariffRule.query.filter_by(
            contract_id=contract_id,
            billing_line_code=spec.billing_line_code,
        )
        if amendment_id is not None:
            query = query.filter_by(amendment_id=amendment_id)
        row = query.first()
        if not row:
            continue
        if _apply_spec_to_row(row, spec, units):
            updated += 1
    return updated


def ensure_ariston_tariffs(
    contract_id: int,
    amendment_id: int,
    *,
    valid_from: date | None = None,
) -> int:
    """Добавить недостающие ставки Аристон к договору. Возвращает число новых строк."""
    valid_from = valid_from or date(2026, 1, 1)
    units = {u.code: u for u in UnitOfMeasure.query.all()}
    added = 0
    for spec in ARISTON_TARIFF_SPECS:
        exists = TariffRule.query.filter_by(
            contract_id=contract_id,
            billing_line_code=spec.billing_line_code,
        ).first()
        if exists:
            continue
        unit = units.get(spec.unit_code)
        if not unit:
            continue
        db.session.add(
            TariffRule(
                contract_id=contract_id,
                amendment_id=amendment_id,
                billing_line_code=spec.billing_line_code,
                name=spec.name,
                unit_id=unit.id,
                report_role=spec.report_role,
                report_scope=spec.report_scope,
                quantity_source=spec.quantity_source,
                rate_line_code=spec.rate_line_code,
                quantity_divisor=spec.quantity_divisor,
                is_custom=spec.is_custom,
                sort_order=spec.sort_order,
                valid_from=valid_from,
                rate_ex_vat=Decimal(spec.rate_ex_vat or ARISTON_RATE_EX_VAT.get(spec.billing_line_code, "0")),
                formula=formula_for_code(spec.billing_line_code),
            )
        )
        added += 1
    sync_ariston_tariff_specs(contract_id, amendment_id)
    ensure_ariston_billing_rates(contract_id)
    return added


def ensure_ariston_billing_rates(contract_id: int) -> int:
    """Обновить rate_ex_vat у существующих ставок Аристон."""
    updated = 0
    specs_with_rate_line = {
        spec.billing_line_code
        for spec in ARISTON_TARIFF_SPECS
        if spec.rate_line_code
    }
    for rule in TariffRule.query.filter_by(contract_id=contract_id).all():
        if rule.billing_line_code in specs_with_rate_line:
            continue
        rate = ARISTON_RATE_EX_VAT.get(rule.billing_line_code)
        if rate is None:
            continue
        rule.rate_ex_vat = Decimal(rate)
        if not rule.formula:
            rule.formula = formula_for_code(rule.billing_line_code)
        updated += 1
    return updated
