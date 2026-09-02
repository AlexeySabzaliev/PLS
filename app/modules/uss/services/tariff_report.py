"""Роли отчёта по ставкам."""
from __future__ import annotations

from app.modules.uss.services.tariff_quantity import effective_quantity_source

REPORT_ROLES = frozenset({
    "transport_logistics",
    "warehouse_logistics",
    "inventory_management",
})


def tariff_is_assigned(t: dict) -> bool:
    return (t.get("report_role") or "").strip() in REPORT_ROLES


def tariff_in_role_report(t: dict, role: str) -> bool:
    if (t.get("report_role") or "").strip() != role:
        return False
    if not tariff_is_assigned(t):
        return False
    source = effective_quantity_source(t)
    if role == "transport_logistics":
        return source in ("manual_vehicle", "manual_daily")
    if role == "warehouse_logistics":
        return source in ("manual_vehicle", "manual_daily")
    if role == "inventory_management":
        return source == "manual_inventory"
    return False
