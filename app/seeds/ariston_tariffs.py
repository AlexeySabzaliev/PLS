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
    "valve_gluing": "219.04",
    "flue_stickering": "21.904",
    "vietnam_stickering": "27.38",
    "overtime_m3": "438.08",
    "inventory_hours": "985.68",
    "elco_drain_hours": "985.68",
}


# Операционный учёт и привязка к тарифу биллинга (repack_units / vehicle_docs).
ARISTON_TARIFF_SPECS: tuple[AristonTariffSpec, ...] = (
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
        "manual_m3",
        "Ручная обработка (вход и выход), м³",
        "m3",
        "transport_logistics",
        "auto_vehicle",
        sort_order=20,
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
    # --- Переупаковка (УЗ) ---
    AristonTariffSpec(
        "repack_units",
        "Переупаковка непосредственно",
        "pcs",
        "inventory_management",
        "manual_inventory",
        sort_order=50,
    ),
    # --- Склад: ввод штук, биллинг по тарифу переупаковки ---
    AristonTariffSpec(
        "valve_gluing",
        "Подклейка клапанов",
        "pcs",
        "warehouse_logistics",
        "manual_daily",
        rate_line_code="repack_units",
        quantity_divisor="1",
        sort_order=52,
    ),
    AristonTariffSpec(
        "vietnam_stickering",
        "Дополнительное стикерование Вьетнам",
        "pcs",
        "warehouse_logistics",
        "manual_daily",
        rate_line_code="repack_units",
        quantity_divisor="8",
        sort_order=53,
    ),
    AristonTariffSpec(
        "flue_stickering",
        "Дополнительное стикерование дымоходов",
        "pcs",
        "warehouse_logistics",
        "manual_daily",
        rate_line_code="repack_units",
        quantity_divisor="10",
        sort_order=54,
    ),
    # --- Транспорт: пакеты документов ---
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
        "extra_vehicle_docs",
        "Дополнительные комплекты документов",
        "vehicle",
        "transport_logistics",
        "auto_vehicle",
        sort_order=41,
        rate_ex_vat="109.52",
    ),
    AristonTariffSpec(
        "extra_vehicle_docs_rf",
        "Дополнительные комплекты РФ",
        "vehicle",
        "transport_logistics",
        "manual_vehicle",
        "vehicle",
        rate_line_code="vehicle_docs",
        quantity_divisor="1",
        sort_order=41,
        is_custom=True,
    ),
    AristonTariffSpec(
        "extra_vehicle_docs_rb",
        "Дополнительные комплекты РБ",
        "vehicle",
        "transport_logistics",
        "manual_vehicle",
        "vehicle",
        rate_line_code="vehicle_docs",
        quantity_divisor="1",
        sort_order=42,
        is_custom=True,
    ),
    AristonTariffSpec(
        "elco_passports",
        "Паспорта ELCO",
        "vehicle",
        "transport_logistics",
        "manual_vehicle",
        "vehicle",
        rate_line_code="vehicle_docs",
        quantity_divisor="1",
        sort_order=43,
        is_custom=True,
    ),
    # Склад / УЗ — уже в базовом наборе
    AristonTariffSpec(
        "elco_drain_hours",
        "Слив ELCO",
        "hour",
        "warehouse_logistics",
        "manual_daily",
        sort_order=80,
    ),
    AristonTariffSpec(
        "storage_area_extra",
        "Доп. площадь",
        "m2",
        "inventory_management",
        "manual_inventory",
        sort_order=12,
        rate_ex_vat="24",
    ),
)


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
    ensure_ariston_billing_rates(contract_id)
    return added


def ensure_ariston_billing_rates(contract_id: int) -> int:
    """Обновить rate_ex_vat у существующих ставок Аристон."""
    updated = 0
    for rule in TariffRule.query.filter_by(contract_id=contract_id).all():
        rate = ARISTON_RATE_EX_VAT.get(rule.billing_line_code)
        if rate is None:
            continue
        rule.rate_ex_vat = Decimal(rate)
        if not rule.formula:
            rule.formula = formula_for_code(rule.billing_line_code)
        updated += 1
    return updated
