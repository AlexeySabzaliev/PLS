"""Роли и области отчёта по ставкам."""
from __future__ import annotations

from app.modules.uss.services.tariff_quantity import (
    apply_tariff_defaults,
    default_report_assignment,
    effective_quantity_source,
)

REPORT_ROLES = frozenset({
    "transport_logistics",
    "warehouse_logistics",
    "inventory_management",
})

REPORT_SCOPES = frozenset({"vehicle", "period"})

ROLE_LABELS = {
    "transport_logistics": "Транспортная логистика",
    "warehouse_logistics": "Складская логистика",
    "inventory_management": "Управление запасами",
}


def tariff_is_assigned(t: dict) -> bool:
    role = (t.get("report_role") or "").strip()
    return role in REPORT_ROLES


def tariff_in_role_report(t: dict, role: str) -> bool:
    """Ставка участвует в операционном отчёте роли (только ручной ввод этой роли)."""
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


def default_report_role(billing_line_code: str, *, inventory_tracked: bool = False) -> str | None:
    role, _, _ = default_report_assignment(billing_line_code)
    if role:
        return role
    if inventory_tracked:
        return "inventory_management"
    return None


def default_report_scope(billing_line_code: str, report_role: str | None) -> str:
    _, scope, source = default_report_assignment(billing_line_code)
    if scope:
        return scope
    if report_role == "inventory_management":
        return "period"
    if source == "manual_vehicle":
        return "vehicle"
    return "period"
