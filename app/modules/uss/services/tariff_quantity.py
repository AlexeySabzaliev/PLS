"""Источники количеств по ставкам (упрощённый порт Billings)."""
from __future__ import annotations

QUANTITY_SOURCES = frozenset({
    "auto_vehicle",
    "auto_contract_param",
    "manual_vehicle",
    "manual_daily",
    "manual_inventory",
    "none",
})

INVENTORY_AREA_CODES = frozenset({"storage_area", "storage_area_extra", "storage_area_fixed"})

ROLE_DEFAULT_SOURCE = {
    "transport_logistics": "manual_vehicle",
    "warehouse_logistics": "manual_daily",
    "inventory_management": "manual_inventory",
}


def apply_tariff_defaults(t: dict) -> dict:
    row = dict(t)
    code = (row.get("billing_line_code") or "").strip()
    role = (row.get("report_role") or "").strip() or None
    src = (row.get("quantity_source") or "").strip().lower()
    if not src and role:
        src = ROLE_DEFAULT_SOURCE.get(role, "")
    if not src and code in INVENTORY_AREA_CODES:
        src = "manual_inventory"
    if src:
        row["quantity_source"] = src
    if role:
        row["report_role"] = role
    return row


def effective_quantity_source(t: dict) -> str:
    row = apply_tariff_defaults(t)
    return (row.get("quantity_source") or "none").lower()


def needs_manual_daily_input(t: dict) -> bool:
    return effective_quantity_source(t) == "manual_daily"


def needs_manual_vehicle_input(t: dict) -> bool:
    return effective_quantity_source(t) == "manual_vehicle"


def needs_manual_inventory_input(t: dict) -> bool:
    return effective_quantity_source(t) == "manual_inventory"


def is_inventory_area_tariff(t: dict) -> bool:
    code = (t.get("billing_line_code") or "").lower()
    if code in INVENTORY_AREA_CODES:
        return True
    return "area" in code and "extra" not in code
