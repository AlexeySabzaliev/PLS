"""Сопоставление наименований услуг со стандартными кодами биллинга."""
from __future__ import annotations

STANDARD_BILLING_CODES = frozenset({
    "storage_area_fixed",
    "storage_area_extra",
    "storage_area",
    "manual_m3",
    "extra_manual_m3",
    "mechanized_m3",
    "vehicle_docs",
    "extra_vehicle_docs",
    "repack_units",
    "overtime_m3",
    "inventory_hours",
    "elco_drain_hours",
    "valve_gluing",
    "vietnam_stickering",
    "flue_stickering",
    "elco_passports",
    "extra_vehicle_docs_rf",
    "extra_vehicle_docs_rb",
})

BILLING_MERGE_INTO = {
    "manual_m3_extra": "manual_m3",
}

AREA_LINE_CODES = frozenset({
    "storage_area_fixed",
    "storage_area_extra",
    "storage_area",
})

UNIT_BY_CODE = {
    "storage_area_fixed": "m2",
    "storage_area_extra": "m2",
    "storage_area": "m2",
    "manual_m3": "m3",
    "extra_manual_m3": "m3",
    "mechanized_m3": "m3",
    "overtime_m3": "m3",
    "vehicle_docs": "vehicle",
    "extra_vehicle_docs": "vehicle",
    "repack_units": "pcs",
    "inventory_hours": "hour",
    "elco_drain_hours": "hour",
}

INVENTORY_TRACKED_DEFAULT = frozenset({
    "storage_area_extra",
    "repack_units",
    "inventory_hours",
    "elco_drain_hours",
    "extra_vehicle_docs",
})

FORMULA_BY_CODE = {
    "storage_area_fixed": "rate_times_days_times_qty",
    "storage_area_extra": "rate_times_days_times_qty",
    "storage_area": "rate_times_days_times_qty",
    "manual_m3": "rate_times_qty",
    "extra_manual_m3": "rate_times_qty",
    "mechanized_m3": "rate_times_qty",
    "vehicle_docs": "rate_times_qty",
    "extra_vehicle_docs": "rate_times_qty",
    "repack_units": "rate_times_qty",
    "overtime_m3": "rate_times_qty",
    "inventory_hours": "rate_times_qty",
    "elco_drain_hours": "rate_times_qty",
}

_NAME_RULES: list[tuple[tuple[str, ...], str]] = [
    (("фиксированн",), "storage_area_fixed"),
    (("дополнительн", "объем"), "storage_area_extra"),
    (("дополнительн", "объём"), "storage_area_extra"),
    (("дополнительн", "м²"), "storage_area_extra"),
    (("дополнительн", "м2"), "storage_area_extra"),
    (("занимаемая", "площадь"), "storage_area"),
    (("ручн", "обработ"), "manual_m3"),
    (("дополнительн", "ручн"), "extra_manual_m3"),
    (("механиз", "обработ"), "mechanized_m3"),
    (("дополнительн", "пакет"), "extra_vehicle_docs"),
    (("дополнительн", "документ"), "extra_vehicle_docs"),
    (("пакет", "документ"), "vehicle_docs"),
    (("машин",), "vehicle_docs"),
    (("переупак",), "repack_units"),
    (("сверхур",), "overtime_m3"),
    (("инвентариз",), "inventory_hours"),
    (("слив", "elco"), "elco_drain_hours"),
    (("слив", "элко"), "elco_drain_hours"),
]


def is_area_line_code(code: str | None) -> bool:
    return (code or "").strip() in AREA_LINE_CODES


def default_inventory_tracked(billing_line_code: str | None, explicit: bool | None = None) -> bool:
    if explicit is not None:
        return bool(explicit)
    return (billing_line_code or "").strip() in INVENTORY_TRACKED_DEFAULT


def is_placeholder_code(code: str | None) -> bool:
    if not code:
        return True
    c = code.strip().lower()
    return c.startswith(("line_", "custom_row_")) or c == "line"


def infer_billing_line_code(name: str, existing: str | None = None) -> str:
    if existing and not is_placeholder_code(existing):
        return existing.strip()
    low = (name or "").lower()
    for keywords, billing_code in _NAME_RULES:
        if all(k in low for k in keywords):
            return billing_code
    if existing and existing.strip():
        return existing.strip()
    return f"custom_{abs(hash(low)) % 10_000_000}"


def formula_for_code(code: str) -> str:
    return FORMULA_BY_CODE.get(code, "rate_times_qty")


def unit_code_for_billing_line(code: str) -> str | None:
    return UNIT_BY_CODE.get(code)


def billing_line_for_tariff(code: str) -> str:
    return BILLING_MERGE_INTO.get(code, code)


def is_agreed_work_code(code: str) -> bool:
    return code.startswith(("agreed_", "custom_inv_"))


def is_standard_catalog_tariff(code: str, is_custom: bool = False) -> bool:
    if is_agreed_work_code(code):
        return False
    if code in STANDARD_BILLING_CODES:
        return True
    return not is_custom and not is_placeholder_code(code)
