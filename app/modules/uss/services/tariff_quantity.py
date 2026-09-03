"""Источники количеств по ставкам: авто vs ручной ввод в отчётах."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.modules.uss.services.tariff_codes import (
    BILLING_LINE_SHORT_NAMES,
    BILLING_MERGE_INTO,
    UNIT_BY_CODE,
    billing_line_for_tariff,
)

QUANTITY_SOURCES = frozenset({
    "auto_vehicle",
    "auto_contract_param",
    "manual_vehicle",
    "manual_daily",
    "manual_inventory",
    "none",
})

AUTO_QUANTITY_SOURCES = frozenset({"auto_vehicle", "auto_contract_param", "none"})

SYSTEM_FORMULA_HINTS: dict[str, str] = {
    "storage_area_fixed": "Площадь из параметра ДС × ставка × дни периода",
    "storage_area_extra": "Средняя доп. площадь за месяц × ставка × дни",
    "manual_m3": "Сумма м³ ручной загрузки/выгрузки по ТС",
    "mechanized_m3": "Сумма м³ механизированной загрузки/выгрузки по ТС",
    "extra_manual_m3": "Сумма м³ из поля «Доп. обработка» по ТС",
    "vehicle_docs": "Количество ТС (загрузка или выгрузка) × ставка",
    "extra_vehicle_docs": "Сумма из поля «Доп. комплект» по ТС",
    "overtime_m3": "Объём обработки сверхурочных ТС",
    "repack_units": "Количество из отчёта упр. запасами (без привязки к ТС)",
    "custom_pallet": "Количество паллет из строки ТС (транспорт)",
}

TRANSPORT_FIELD_CODES = frozenset({"extra_manual_m3", "extra_vehicle_docs"})
MANUAL_INPUT_SOURCES = frozenset({"manual_vehicle", "manual_daily", "manual_inventory"})

ROLE_OPERATIONAL_DEFAULTS: dict[str, tuple[str, str]] = {
    "transport_logistics": ("manual_vehicle", "vehicle"),
    "warehouse_logistics": ("manual_daily", "period"),
    "inventory_management": ("manual_inventory", "period"),
}

ROLE_ALLOWED_SOURCES: dict[str, frozenset[str]] = {
    "transport_logistics": frozenset({"manual_vehicle", "manual_daily"}),
    "warehouse_logistics": frozenset({"manual_daily", "manual_vehicle"}),
    "inventory_management": frozenset({"manual_inventory"}),
}

INVENTORY_AREA_CODES = frozenset({"storage_area_extra"})


@dataclass(frozen=True)
class LineQuantityDef:
    quantity_source: str
    default_report_role: str | None = None
    default_report_scope: str | None = None
    inventory_slot: str | None = None
    merge_into: str | None = None
    contract_param: str | None = None


LINE_QUANTITY_REGISTRY: dict[str, LineQuantityDef] = {
    "storage_area_fixed": LineQuantityDef(
        "auto_contract_param",
        contract_param="fixed_storage_m2days",
    ),
    "storage_area_extra": LineQuantityDef(
        "manual_inventory",
        default_report_role="inventory_management",
        default_report_scope="period",
        inventory_slot="area",
    ),
    "storage_area": LineQuantityDef("none"),
    "manual_m3": LineQuantityDef(
        "auto_vehicle",
        default_report_role="transport_logistics",
    ),
    "mechanized_m3": LineQuantityDef(
        "auto_vehicle",
        default_report_role="transport_logistics",
    ),
    "extra_manual_m3": LineQuantityDef(
        "auto_vehicle",
        default_report_role="transport_logistics",
    ),
    "vehicle_docs": LineQuantityDef(
        "auto_vehicle",
        default_report_role="transport_logistics",
    ),
    "extra_vehicle_docs": LineQuantityDef(
        "auto_vehicle",
        default_report_role="transport_logistics",
    ),
    "overtime_m3": LineQuantityDef(
        "auto_vehicle",
        default_report_role="transport_logistics",
    ),
    "repack_units": LineQuantityDef(
        "manual_inventory",
        default_report_role="inventory_management",
        default_report_scope="period",
        inventory_slot="extra",
    ),
    "custom_pallet": LineQuantityDef(
        "manual_vehicle",
        default_report_role="transport_logistics",
        default_report_scope="vehicle",
    ),
    "inventory_hours": LineQuantityDef(
        "manual_inventory",
        default_report_role="inventory_management",
        default_report_scope="period",
        inventory_slot="extra",
    ),
    "elco_drain_hours": LineQuantityDef(
        "manual_daily",
        default_report_role="warehouse_logistics",
        default_report_scope="period",
    ),
    "valve_gluing": LineQuantityDef(
        "manual_daily",
        default_report_role="warehouse_logistics",
        default_report_scope="period",
    ),
    "vietnam_stickering": LineQuantityDef(
        "manual_daily",
        default_report_role="warehouse_logistics",
        default_report_scope="period",
    ),
    "flue_stickering": LineQuantityDef(
        "manual_daily",
        default_report_role="warehouse_logistics",
        default_report_scope="period",
    ),
    "elco_passports": LineQuantityDef(
        "manual_vehicle",
        default_report_role="transport_logistics",
        default_report_scope="vehicle",
    ),
    "extra_vehicle_docs_rf": LineQuantityDef(
        "manual_vehicle",
        default_report_role="transport_logistics",
        default_report_scope="vehicle",
    ),
    "extra_vehicle_docs_rb": LineQuantityDef(
        "manual_vehicle",
        default_report_role="transport_logistics",
        default_report_scope="vehicle",
    ),
}


def line_def(billing_line_code: str | None) -> LineQuantityDef | None:
    return LINE_QUANTITY_REGISTRY.get((billing_line_code or "").strip())


def effective_quantity_source(tariff: dict) -> str:
    """Источник количества: роль отчёта и реестр кодов важнее устаревшего quantity_source в БД."""
    code = (tariff.get("billing_line_code") or "").strip()
    reg = line_def(code)
    role = (tariff.get("report_role") or "").strip()
    scope = (tariff.get("report_scope") or "").strip()
    explicit = (tariff.get("quantity_source") or "").strip()
    accounting = (tariff.get("accounting_mode") or "").strip()

    if accounting == "billing_only":
        return "none"
    if accounting == "system" and reg:
        return reg.quantity_source

    if reg and reg.quantity_source in INTRINSIC_AUTO_SOURCES:
        return reg.quantity_source

    if reg and reg.default_report_role and role == reg.default_report_role:
        return reg.quantity_source

    # Роль отчёта задаёт ручной ввод (исправляет manual_daily у repack_units и т.п.)
    if role == "inventory_management":
        return "manual_inventory"
    if role in ROLE_ALLOWED_SOURCES:
        allowed = ROLE_ALLOWED_SOURCES[role]
        if scope == "vehicle" and "manual_vehicle" in allowed:
            return "manual_vehicle"
        if scope == "period" and "manual_daily" in allowed:
            return "manual_daily"
        if explicit in allowed:
            return explicit
        return ROLE_OPERATIONAL_DEFAULTS[role][0]

    if explicit in QUANTITY_SOURCES:
        return explicit
    if reg:
        return reg.quantity_source
    if scope == "vehicle":
        return "manual_vehicle"
    if scope == "period":
        return "manual_daily"
    return "manual_daily"


INTRINSIC_AUTO_SOURCES = frozenset({"auto_vehicle", "auto_contract_param"})

_QUANTITY_SOURCE_HINT: dict[str, str] = {
    "auto_contract_param": "auto_contract_param",
    "auto_vehicle": "auto_vehicle",
    "manual_vehicle": "manual_vehicle",
    "manual_daily": "manual_daily",
    "manual_inventory": "manual_inventory",
    "none": "none",
}


def billing_line_code_choices() -> list[dict]:
    """Справочник известных billing_line_code для UI каталога ставок."""
    choices: list[dict] = []
    for code, reg in LINE_QUANTITY_REGISTRY.items():
        short = BILLING_LINE_SHORT_NAMES.get(code, code)
        src_hint = _QUANTITY_SOURCE_HINT.get(reg.quantity_source, reg.quantity_source)
        label = f"{short} — {src_hint}"
        if reg.default_report_role:
            label = f"{short} — {src_hint}, {reg.default_report_role}"
        scope = reg.default_report_scope
        if reg.quantity_source == "manual_vehicle":
            scope = scope or "vehicle"
        elif reg.quantity_source in ("manual_daily", "manual_inventory"):
            scope = scope or "period"
        elif reg.quantity_source in INTRINSIC_AUTO_SOURCES:
            scope = "period"
        choices.append({
            "value": code,
            "label": label,
            "unit_code": UNIT_BY_CODE.get(code),
            "report_role": reg.default_report_role,
            "quantity_source": reg.quantity_source,
            "report_scope": scope,
        })
    return choices


def is_intrinsic_auto_code(billing_line_code: str | None) -> bool:
    reg = line_def(billing_line_code)
    return reg is not None and reg.quantity_source in INTRINSIC_AUTO_SOURCES


def is_transport_field_code(billing_line_code: str | None) -> bool:
    return (billing_line_code or "").strip() in TRANSPORT_FIELD_CODES


def intrinsic_auto_label(quantity_source: str | None, *, billing_line_code: str | None = None) -> str:
    if is_transport_field_code(billing_line_code):
        return "Транспорт (поле ввода)"
    if quantity_source == "auto_contract_param":
        return "Авто (параметр ДС)"
    if quantity_source == "auto_vehicle":
        return "Авто (из таблицы ТС)"
    return "—"


def default_report_assignment(billing_line_code: str | None) -> tuple[str | None, str | None, str]:
    reg = line_def(billing_line_code)
    if not reg:
        return None, "period", "manual_daily"
    scope = reg.default_report_scope
    if reg.quantity_source == "manual_vehicle":
        scope = scope or "vehicle"
    elif reg.quantity_source == "manual_daily":
        scope = scope or "period"
    elif reg.quantity_source == "manual_inventory":
        scope = scope or "period"
    elif reg.quantity_source in ("auto_vehicle", "none", "auto_contract_param"):
        scope = None
    return reg.default_report_role, scope, reg.quantity_source


def apply_tariff_defaults(tariff: dict) -> dict:
    """Подставить quantity_source и роли по коду, если не заданы явно."""
    out = dict(tariff)
    code = (out.get("billing_line_code") or "").strip()
    accounting = (out.get("accounting_mode") or "").strip()
    reg = line_def(code)

    if accounting == "billing_only":
        out["report_role"] = None
        out["report_scope"] = "period"
        out["quantity_source"] = "none"
        return out

    if reg and reg.quantity_source in INTRINSIC_AUTO_SOURCES:
        out["quantity_source"] = reg.quantity_source
        out["report_role"] = None
        out["report_scope"] = "period"
        return out

    if accounting == "system":
        if reg:
            out["quantity_source"] = reg.quantity_source
        elif not out.get("quantity_source"):
            out["quantity_source"] = effective_quantity_source(out)
        out["report_role"] = None
        out["report_scope"] = "period"
        return out

    if accounting in ROLE_OPERATIONAL_DEFAULTS:
        out["report_role"] = accounting
        default_src, default_scope = ROLE_OPERATIONAL_DEFAULTS[accounting]
        allowed = ROLE_ALLOWED_SOURCES.get(accounting, frozenset())
        if reg and reg.quantity_source in MANUAL_INPUT_SOURCES and reg.quantity_source in allowed:
            out["quantity_source"] = reg.quantity_source
            if reg.default_report_scope:
                out["report_scope"] = reg.default_report_scope
            elif reg.quantity_source == "manual_vehicle":
                out["report_scope"] = "vehicle"
            else:
                out["report_scope"] = "period"
        else:
            out["quantity_source"] = default_src
            out["report_scope"] = default_scope
        if reg and reg.inventory_slot and accounting == "inventory_management":
            out.setdefault("inventory_slot", reg.inventory_slot)
        return out

    if not out.get("quantity_source"):
        out["quantity_source"] = effective_quantity_source(out)
    role, scope, _ = default_report_assignment(code)
    if accounting in ("transport_logistics", "warehouse_logistics", "inventory_management"):
        out["report_role"] = accounting
    elif not out.get("report_role") and role:
        out["report_role"] = role
    if not out.get("report_scope") or out.get("report_scope") == "period":
        if scope:
            out["report_scope"] = scope
    if reg and reg.inventory_slot and out.get("report_role") == "inventory_management":
        out.setdefault("inventory_slot", reg.inventory_slot)
    if reg and reg.default_report_role:
        probe = dict(out)
        probe["report_role"] = reg.default_report_role
        if reg.default_report_scope:
            probe["report_scope"] = reg.default_report_scope
        elif reg.quantity_source == "manual_vehicle":
            probe["report_scope"] = "vehicle"
        if effective_quantity_source(probe) != effective_quantity_source(out):
            out["report_role"] = reg.default_report_role
            out["report_scope"] = probe["report_scope"]
    out["quantity_source"] = effective_quantity_source(out)
    return out


def system_formula_hint(billing_line_code: str | None) -> str:
    code = (billing_line_code or "").strip()
    return SYSTEM_FORMULA_HINTS.get(code, "Автоматический расчёт по данным системы")


def is_system_managed(tariff: dict) -> bool:
    if (tariff.get("accounting_mode") or "") == "billing_only":
        return False
    if (tariff.get("accounting_mode") or "") == "system":
        return True
    if tariff.get("report_role"):
        return False
    return effective_quantity_source(tariff) in AUTO_QUANTITY_SOURCES


def accounting_mode_label(mode: str | None) -> str:
    labels = {
        "system": "Авто",
        "transport_logistics": "Транспорт",
        "warehouse_logistics": "Склад",
        "inventory_management": "Упр. запасами",
        "billing_only": "Только биллинг",
    }
    return labels.get((mode or "").strip(), mode or "—")


def _fmt_qty(value: Decimal | float | int) -> str:
    q = _d(value)
    if q == q.to_integral_value():
        return str(int(q))
    return f"{q:.4f}".rstrip("0").rstrip(".")


def billing_formula_comment(
    line_code: str,
    quantity: Decimal,
    *,
    days_count: int | None = None,
    unit_code: str | None = None,
    tariff: dict | None = None,
) -> str:
    code = (line_code or "").strip()
    qty_s = _fmt_qty(quantity)
    unit = (unit_code or (tariff or {}).get("unit_code") or "").strip()
    unit_labels = {"m2": "м²", "m3": "м³", "pcs": "шт.", "hour": "чел.ч."}
    unit_label = unit_labels.get(unit, unit or "ед.")

    if code == "storage_area_fixed":
        days = days_count or 0
        return f"Площадь {qty_s} {unit_label} × {days} дн."
    if code == "storage_area_extra":
        days = days_count or 0
        return f"Средняя доп. площадь {qty_s} {unit_label}/сут × {days} дн."
    if code == "vehicle_docs":
        return f"Кол-во ТС: {qty_s}"
    if code == "manual_m3":
        return f"Сумма м³ ручной обработки по ТС: {qty_s}"

    hint = system_formula_hint(code)
    source = effective_quantity_source(tariff or {"billing_line_code": code})
    if source == "manual_vehicle":
        return f"Ручной ввод на ТС: {qty_s} {unit_label}"
    if source == "manual_daily":
        return f"Итог за день (склад): {qty_s} {unit_label}"
    if source == "manual_inventory":
        return f"Упр. запасами: {qty_s} {unit_label}"
    if source == "auto_contract_param":
        days = days_count or 0
        if days:
            return f"{hint}: {qty_s} {unit_label} × {days} дн."
        return f"{hint}: {qty_s} {unit_label}"
    if source == "none":
        return f"Только биллинг: {qty_s} {unit_label}"
    return f"{hint}: {qty_s} {unit_label}"


def effective_accounting_mode(tariff: dict) -> str:
    explicit = (tariff.get("accounting_mode") or "").strip()
    if explicit:
        return explicit
    source = effective_quantity_source(tariff)
    if source in INTRINSIC_AUTO_SOURCES:
        return "system"
    if source == "none":
        return "billing_only"
    return (tariff.get("report_role") or "").strip() or "manual"


def is_inventory_area_tariff(tariff: dict) -> bool:
    code = (tariff.get("billing_line_code") or "").strip()
    if code in INVENTORY_AREA_CODES:
        return True
    reg = line_def(code)
    return reg is not None and reg.inventory_slot == "area"


def needs_manual_vehicle_input(tariff: dict) -> bool:
    return effective_quantity_source(tariff) == "manual_vehicle"


def needs_manual_daily_input(tariff: dict) -> bool:
    return effective_quantity_source(tariff) == "manual_daily"


def needs_manual_inventory_input(tariff: dict) -> bool:
    return effective_quantity_source(tariff) == "manual_inventory"


def _d(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _op_date(op: dict) -> date:
    od = op.get("operation_date")
    if isinstance(od, date):
        return od
    return date.fromisoformat(str(od)[:10])


def auto_vehicle_quantity(
    billing_line_code: str,
    operations: list[dict],
    *,
    period_start: date | None = None,
    period_end: date | None = None,
) -> Decimal:
    code = billing_line_code
    ops = operations
    if period_start and period_end:
        ops = [o for o in operations if period_start <= _op_date(o) <= period_end]

    if code == "vehicle_docs":
        return Decimal(len(ops))

    if code == "extra_vehicle_docs":
        qty = sum(int(o.get("extra_document_set_qty") or 0) for o in ops)
        if qty <= 0:
            qty = sum(1 for o in ops if o.get("extra_document_set"))
        return Decimal(qty)

    if code == "manual_m3":
        return sum(_d(o.get("inbound_manual_m3")) + _d(o.get("outbound_manual_m3")) for o in ops)

    if code == "extra_manual_m3":
        return sum(_d(o.get("extra_handling_m3")) for o in ops)

    if code == "mechanized_m3":
        total = Decimal("0")
        for o in ops:
            manual = _d(o.get("inbound_manual_m3")) + _d(o.get("outbound_manual_m3"))
            mech = _d(o.get("inbound_mech_m3")) + _d(o.get("outbound_mech_m3"))
            vol = _d(o.get("volume_document_m3"))
            total += mech + max(vol - manual - mech, Decimal("0"))
        return total

    if code == "overtime_m3":
        return sum(
            _d(o.get("inbound_manual_m3")) + _d(o.get("outbound_manual_m3"))
            + _d(o.get("inbound_mech_m3")) + _d(o.get("outbound_mech_m3"))
            for o in ops if o.get("is_overtime")
        )

    return Decimal("0")


def collect_manual_quantity_warnings(
    tariffs: list[dict],
    *,
    operations: list[dict],
    shifts: list[dict],
    daily_totals: dict[str, Decimal],
    vehicle_qty: dict[str, Decimal],
    extra_totals: dict[str, Decimal],
    period_start: date,
    period_end: date,
    contract_reserved_m2: Decimal | None = None,
) -> list[str]:
    if not tariffs:
        return []
    has_ops = bool(operations)
    has_shifts = bool(shifts)
    by_code: dict[str, dict] = {}
    for t in tariffs:
        code = (t.get("billing_line_code") or "").strip()
        if code:
            by_code[code] = t

    warnings: list[str] = []
    for code, t in by_code.items():
        source = effective_quantity_source(t)
        if source not in MANUAL_INPUT_SOURCES:
            continue
        qty = resolve_tariff_period_quantity(
            t,
            operations=operations,
            shifts=shifts,
            daily_totals=daily_totals,
            vehicle_qty=vehicle_qty,
            extra_totals=extra_totals,
            period_start=period_start,
            period_end=period_end,
            contract_reserved_m2=contract_reserved_m2,
        )
        if qty > 0:
            continue
        if source == "manual_vehicle" and not has_ops:
            continue
        if source == "manual_daily" and not (has_ops or has_shifts):
            continue
        if source == "manual_inventory" and not has_shifts:
            continue
        name = t.get("name") or code
        warnings.append(f"Не введено количество по «{name}» ({code}) при наличии операций за период")
    return warnings


def merge_billing_code(code: str) -> str:
    return BILLING_MERGE_INTO.get(code, code)


def _shift_report_date(shift: dict) -> date:
    rd = shift.get("report_date")
    if isinstance(rd, date):
        return rd
    return date.fromisoformat(str(rd)[:10])


def _area_value_for_code(area_entries, billing_line_code: str) -> Decimal | None:
    """Площадь из area_entries: dict {code: val} или list[{billing_line_code, area_m2}]."""
    if not area_entries:
        return None
    if isinstance(area_entries, dict):
        if billing_line_code not in area_entries:
            return None
        val = area_entries.get(billing_line_code)
        if val is None or str(val).strip() == "":
            return None
        return _d(val)
    if isinstance(area_entries, str):
        try:
            area_entries = json.loads(area_entries)
        except json.JSONDecodeError:
            return None
    if isinstance(area_entries, list):
        total = Decimal("0")
        found = False
        for entry in area_entries:
            if entry.get("billing_line_code") != billing_line_code:
                continue
            val = entry.get("area_m2")
            if val is not None and str(val).strip() != "":
                total += _d(val)
                found = True
        return total if found else None
    return None


def avg_inventory_area_m2(
    shifts: list[dict],
    period_start: date,
    period_end: date,
    calendar_days: int,
    billing_line_code: str,
) -> Decimal:
    del calendar_days
    daily_sum = Decimal("0")
    days_with_data = 0
    for shift in shifts:
        rd = _shift_report_date(shift)
        if not (period_start <= rd <= period_end):
            continue
        day_area = _area_value_for_code(shift.get("area_entries"), billing_line_code)
        if day_area is not None:
            daily_sum += day_area
            days_with_data += 1
    if days_with_data <= 0:
        return Decimal("0")
    return daily_sum / Decimal(days_with_data)


def parse_area_m2_from_text(text: str) -> Decimal:
    m = re.search(r"(\d[\d\s]{1,6})\s*м[²2]", text or "", re.IGNORECASE)
    if not m:
        return Decimal("0")
    return _d(re.sub(r"\s+", "", m.group(1)))


def resolve_billing_only_quantity(
    tariff: dict,
    *,
    contract: dict | None = None,
    product_type_code: str | None = None,
) -> Decimal:
    del product_type_code
    contract = contract or {}
    config = contract.get("billing_config") or {}
    for key in ("warehouse_area_m2", "fixed_m2days", "fixed_storage_m2days"):
        val = _d(config.get(key, 0))
        if val > 0:
            return val
    return parse_area_m2_from_text(tariff.get("name") or "")


def resolve_tariff_period_quantity(
    tariff: dict,
    *,
    operations: list[dict],
    shifts: list[dict],
    daily_totals: dict[str, Decimal],
    vehicle_qty: dict[str, Decimal],
    extra_totals: dict[str, Decimal],
    period_start: date,
    period_end: date,
    contract_reserved_m2: Decimal | None = None,
    calendar_days: int | None = None,
) -> Decimal:
    code = (tariff.get("billing_line_code") or "").strip()
    if not code:
        return Decimal("0")
    source = effective_quantity_source(tariff)
    bill_code = billing_line_for_tariff(code)

    if source == "auto_contract_param":
        return contract_reserved_m2 or Decimal("0")

    if source == "auto_vehicle":
        if code == "extra_vehicle_docs":
            inv_extra = extra_totals.get(code, Decimal("0"))
            if inv_extra > 0:
                return inv_extra
        return auto_vehicle_quantity(code, operations, period_start=period_start, period_end=period_end)

    if source == "manual_vehicle":
        qty = vehicle_qty.get(code, Decimal("0"))
        if bill_code != code:
            qty += vehicle_qty.get(bill_code, Decimal("0"))
        if qty <= 0:
            qty = extra_totals.get(code, Decimal("0"))
            if bill_code != code:
                qty += extra_totals.get(bill_code, Decimal("0"))
        return qty

    if source == "manual_daily":
        qty = daily_totals.get(code, Decimal("0"))
        if bill_code != code:
            qty += daily_totals.get(bill_code, Decimal("0"))
        return qty

    if source == "manual_inventory":
        if is_inventory_area_tariff(tariff) and calendar_days:
            return avg_inventory_area_m2(
                shifts, period_start, period_end, calendar_days, code,
            )
        qty = extra_totals.get(code, Decimal("0"))
        if bill_code != code:
            qty += extra_totals.get(bill_code, Decimal("0"))
        return qty

    return Decimal("0")
