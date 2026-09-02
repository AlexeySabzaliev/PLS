"""Схема полей отчёта по договору и роли (из tariff_rules)."""
from __future__ import annotations

from datetime import date

from app.db import db
from app.modules.reference.models import ContractAmendment, TariffRule, UnitOfMeasure
from app.modules.uss.services.tariff_quantity import (
    is_inventory_area_tariff,
    needs_manual_daily_input,
    needs_manual_inventory_input,
    needs_manual_vehicle_input,
    apply_tariff_defaults,
)
from app.modules.uss.services.tariff_report import REPORT_ROLES, tariff_in_role_report

TRANSPORT_FIXED_FIELDS = [
    {"field": "plate_number", "label": "Гос. номер", "input_type": "text"},
    {"field": "volume_document_m3", "label": "Объём, м³", "input_type": "number"},
    {"field": "handling_type_code", "label": "Тип обработки", "input_type": "text"},
    {"field": "extra_handling_m3", "label": "Доп. обработка, м³", "input_type": "number"},
    {"field": "extra_document_set_qty", "label": "Доп. комплект", "input_type": "number"},
    {"field": "registered_at", "label": "Прибытие", "input_type": "datetime-local"},
    {"field": "departed_at", "label": "Убытие", "input_type": "datetime-local"},
]


def _active_tariffs(contract_id: int, on_date: date) -> list[dict]:
    amendments = ContractAmendment.query.filter(
        ContractAmendment.contract_id == contract_id,
        ContractAmendment.status == "active",
        ContractAmendment.effective_from <= on_date,
        db.or_(
            ContractAmendment.effective_to.is_(None),
            ContractAmendment.effective_to >= on_date,
        ),
    ).all()
    am_ids = [a.id for a in amendments]
    if not am_ids:
        return []

    rows = (
        TariffRule.query.filter(
            TariffRule.contract_id == contract_id,
            TariffRule.amendment_id.in_(am_ids),
            TariffRule.valid_from <= on_date,
            db.or_(TariffRule.valid_to.is_(None), TariffRule.valid_to >= on_date),
        )
        .order_by(TariffRule.sort_order, TariffRule.id)
        .all()
    )
    unit_ids = {r.unit_id for r in rows if r.unit_id}
    units = {
        u.id: u.code
        for u in UnitOfMeasure.query.filter(UnitOfMeasure.id.in_(unit_ids)).all()
    } if unit_ids else {}

    result = []
    for r in rows:
        result.append(
            apply_tariff_defaults({
                "id": r.id,
                "tariff_id": r.id,
                "billing_line_code": r.billing_line_code,
                "name": r.name,
                "report_role": r.report_role,
                "report_scope": r.report_scope,
                "quantity_source": r.quantity_source,
                "is_custom": r.is_custom,
                "price_agreed": r.price_agreed,
                "sort_order": r.sort_order or 0,
                "unit_code": units.get(r.unit_id),
            })
        )
    return result


def _tariff_row(t: dict, *, input_kind: str) -> dict:
    return {
        "tariff_id": t.get("tariff_id") or t.get("id"),
        "billing_line_code": t["billing_line_code"],
        "name": t["name"],
        "unit_code": t.get("unit_code"),
        "quantity_source": t.get("quantity_source"),
        "report_role": t.get("report_role"),
        "report_scope": t.get("report_scope"),
        "input_kind": input_kind,
        "price_agreed": t.get("price_agreed", True),
        "is_custom": t.get("is_custom", False),
        "sort_order": t.get("sort_order") or 0,
    }


def schema_for_contract_role(contract_id: int, on_date: date, role: str) -> dict:
    """Схема ввода для договора и роли отчёта."""
    if role not in REPORT_ROLES:
        return {
            "report_role": role,
            "vehicle_inputs": [],
            "period_inputs": [],
            "inventory_areas": [],
            "inventory_extra": [],
            "vehicle_fixed_fields": [],
        }

    tariffs = _active_tariffs(contract_id, on_date)
    role_tariffs = [t for t in tariffs if tariff_in_role_report(t, role)]

    schema = {
        "report_role": role,
        "contract_id": contract_id,
        "on_date": on_date.isoformat(),
        "vehicle_inputs": [
            _tariff_row(t, input_kind="vehicle")
            for t in role_tariffs
            if needs_manual_vehicle_input(t)
        ],
        "period_inputs": [
            _tariff_row(t, input_kind="period")
            for t in role_tariffs
            if needs_manual_daily_input(t)
        ],
        "inventory_areas": [
            _tariff_row(t, input_kind="inventory_area")
            for t in role_tariffs
            if needs_manual_inventory_input(t) and is_inventory_area_tariff(t)
        ],
        "inventory_extra": [
            _tariff_row(t, input_kind="inventory_extra")
            for t in role_tariffs
            if needs_manual_inventory_input(t) and not is_inventory_area_tariff(t)
        ],
        "vehicle_fixed_fields": [],
    }
    if role == "transport_logistics":
        schema["vehicle_fixed_fields"] = list(TRANSPORT_FIXED_FIELDS)
    return schema
