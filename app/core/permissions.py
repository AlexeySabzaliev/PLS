"""Права по разделам: УЗнТ и УСС."""
from __future__ import annotations

ROLE_CODES = frozenset({
    "admin",
    "supervisor",
    "transport_logistics",
    "warehouse_logistics",
    "commercial_logistics",
    "inventory_management",
})

# УЗнТ — заявки (заглушки фазы 0)
REQUEST_SECTIONS: dict[str, frozenset[str]] = {
    "admin": frozenset({"request_analytics"}),
    "transport_logistics": frozenset({"requests_view_all", "requests_transport"}),
    "commercial_logistics": frozenset({"requests_view_all", "tenders", "request_analytics"}),
}

# УСС — операционный учёт
USS_SECTIONS: dict[str, frozenset[str]] = {
    "admin": frozenset({
        "uss_admin", "uss_catalog_clients", "uss_catalog_contracts",
        "uss_catalog_amendments", "uss_catalog_locations", "uss_catalog_rates",
        "uss_catalog_staff", "uss_catalog_vehicles", "uss_catalog_vehicle_types", "uss_ops_transport",
        "uss_ops_warehouse", "uss_ops_inventory", "uss_billing",
        "uss_process_lines",
    }),
    "supervisor": frozenset({"uss_admin", "uss_catalog_locations", "uss_process_lines"}),
    "transport_logistics": frozenset({"uss_ops_transport", "uss_catalog_vehicles", "uss_catalog_vehicle_types"}),
    "warehouse_logistics": frozenset({"uss_ops_warehouse"}),
    "inventory_management": frozenset({"uss_ops_inventory"}),
    "commercial_logistics": frozenset({
        "uss_catalog_clients", "uss_catalog_contracts", "uss_catalog_amendments",
        "uss_catalog_rates", "uss_billing", "uss_process_lines",
    }),
}

# Справочники (общие)
REFERENCE_SECTIONS: dict[str, frozenset[str]] = {
    "admin": frozenset({"ref_clients", "ref_contracts", "ref_amendments", "ref_locations",
                         "ref_tariff_codes", "ref_units", "ref_staff", "ref_vehicles",
                         "ref_roles", "ref_permissions"}),
    "commercial_logistics": frozenset({
        "ref_clients", "ref_contracts", "ref_amendments", "ref_tariff_codes",
    }),
    "supervisor": frozenset({"ref_locations", "ref_roles", "ref_permissions"}),
}


def effective_role_codes(user: dict | None) -> set[str]:
    if not user:
        return set()
    codes = set(user.get("role_codes") or [])
    if user.get("is_admin"):
        codes.add("admin")
    return codes


def user_can_manage(user: dict | None) -> bool:
    if not user:
        return False
    return bool(user.get("is_admin") or effective_role_codes(user) & {"admin", "supervisor"})


def _has_section(user: dict | None, section: str, matrix: dict[str, frozenset[str]]) -> bool:
    if not user:
        return False
    if user.get("is_admin"):
        return True
    for code in effective_role_codes(user):
        if section in matrix.get(code, frozenset()):
            return True
    return False


def user_has_uss_section(user: dict | None, section: str) -> bool:
    return _has_section(user, section, USS_SECTIONS)


def user_has_request_section(user: dict | None, section: str) -> bool:
    return _has_section(user, section, REQUEST_SECTIONS)


def user_has_reference_section(user: dict | None, section: str) -> bool:
    return _has_section(user, section, REFERENCE_SECTIONS)
