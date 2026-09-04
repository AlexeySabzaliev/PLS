"""Вид учёта ставки: одно поле «Как считается» → источник количества и место ввода."""
from __future__ import annotations

ACCOUNTING_KIND_CHOICES: list[tuple[str, str]] = [
    ("auto_contract", "Авто: параметры договора"),
    ("auto_vehicle", "Авто: по записи ТС"),
    ("vehicle_extra", "Доп. услуга на строке ТС"),
    ("daily_extra", "Доп. услуга: итог за день"),
]

_KIND_LABELS = dict(ACCOUNTING_KIND_CHOICES)

_LEGACY_KIND_MAP = {
    "auto_contract_param": "auto_contract",
    "auto_vehicle": "auto_vehicle",
    "manual_vehicle": "vehicle_extra",
    "manual": "daily_extra",
    "manual_daily": "daily_extra",
    "manual_inventory": "daily_extra",
}


def normalize_accounting_kind(raw: str | None) -> str:
    key = (raw or "").strip()
    return _LEGACY_KIND_MAP.get(key, key)


def tariff_accounting_kind(tariff: dict) -> str:
    """Вычислить вид учёта для отображения в справочнике."""
    explicit = normalize_accounting_kind(tariff.get("accounting_kind"))
    if explicit in _KIND_LABELS:
        return explicit

    qs = (tariff.get("quantity_source") or "").strip()
    scope = (tariff.get("report_scope") or "").strip()
    role = (tariff.get("report_role") or "").strip()

    if qs == "auto_contract_param":
        return "auto_contract"
    if qs == "auto_vehicle":
        return "auto_vehicle"
    if qs == "manual_vehicle" or scope == "vehicle":
        return "vehicle_extra"
    if qs in ("manual_daily", "manual_inventory", "manual"):
        return "daily_extra"
    if role in ("transport_logistics", "warehouse_logistics", "inventory_management"):
        return "daily_extra"
    if tariff.get("is_custom"):
        return "daily_extra"
    return "auto_vehicle" if qs == "auto_vehicle" else "auto_contract"


def accounting_kind_label(kind: str | None) -> str:
    return _KIND_LABELS.get(normalize_accounting_kind(kind), kind or "—")


def apply_accounting_kind(data: dict) -> dict:
    """Развернуть accounting_kind в quantity_source, report_role, report_scope."""
    out = dict(data)
    is_custom = bool(out.get("is_custom"))
    kind = normalize_accounting_kind(out.get("accounting_kind") or out.get("quantity_source"))

    if kind == "auto_contract":
        out["quantity_source"] = "auto_contract_param"
        out["report_role"] = None
        out["report_scope"] = "period"
    elif kind == "auto_vehicle":
        out["quantity_source"] = "auto_vehicle"
        out["report_role"] = None
        out["report_scope"] = "period"
    elif kind == "vehicle_extra":
        out["quantity_source"] = "manual_vehicle"
        out["report_role"] = "transport_logistics"
        out["report_scope"] = "vehicle"
    elif kind == "daily_extra":
        role = (out.get("report_role") or "").strip()
        if not role:
            out["report_role"] = "warehouse_logistics" if is_custom else role or None
            role = out["report_role"] or ""
        out["report_scope"] = "period"
        if role == "inventory_management":
            out["quantity_source"] = "manual_inventory"
        else:
            out["quantity_source"] = "manual_daily"
    out.pop("accounting_kind", None)
    return out


def report_role_required_for_kind(kind: str | None) -> bool:
    return normalize_accounting_kind(kind) == "daily_extra"
