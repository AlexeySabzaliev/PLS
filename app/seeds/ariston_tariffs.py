"""Ставки демо-договора Аристон (операционный ввод → биллинг)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.db import db
from app.modules.reference.models import TariffRule, UnitOfMeasure


@dataclass(frozen=True)
class AristonTariffSpec:
    billing_line_code: str
    name: str
    unit_code: str
    report_role: str
    quantity_source: str
    report_scope: str | None = None
    rate_line_code: str | None = None
    quantity_divisor: str = "1"
    sort_order: int = 0
    is_custom: bool = False


# Операционный учёт и привязка к тарифу биллинга (repack_units / vehicle_docs).
ARISTON_TARIFF_SPECS: tuple[AristonTariffSpec, ...] = (
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
        "m2day",
        "inventory_management",
        "manual_inventory",
        sort_order=12,
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
            )
        )
        added += 1
    return added
