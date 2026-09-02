"""Стратегии расчёта биллинга (порт из Billings)."""
from __future__ import annotations

import calendar
import json
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.modules.billing.aggregates import sum_daily_totals_by_code, sum_vehicle_report_quantities
from app.modules.uss.services.tariff_billing import operational_to_billing_quantity
from app.modules.uss.services.tariff_codes import (
    AREA_LINE_CODES,
    BILLING_MERGE_INTO,
    billing_line_for_tariff,
)
from app.modules.uss.services.tariff_quantity import (
    billing_formula_comment,
    effective_quantity_source,
    is_inventory_area_tariff,
    resolve_billing_only_quantity,
    resolve_tariff_period_quantity,
)


@dataclass
class BillingLineResult:
    line_code: str
    name: str
    tariff: Decimal | None
    days_count: int | None
    quantity: Decimal
    unit_code: str
    amount_ex_vat: Decimal
    details: list[dict[str, Any]]
    sort_order: int
    formula_comment: str = ""


def _d(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    last = _days_in_month(year, month)
    return date(year, month, 1), date(year, month, last)


def _tariff_on(tariffs: list[dict], line_code: str, on_date: date) -> dict | None:
    matched: list[dict] = []
    for t in tariffs:
        if t["billing_line_code"] != line_code:
            continue
        vf = t["valid_from"]
        if isinstance(vf, str):
            vf = date.fromisoformat(vf[:10])
        vt = t.get("valid_to")
        if isinstance(vt, str):
            vt = date.fromisoformat(vt[:10])
        if vf <= on_date and (vt is None or vt >= on_date):
            matched.append(t)
    if not matched:
        return None
    matched.sort(key=lambda x: (x.get("valid_from") or date.min, x.get("sort_order") or 0), reverse=True)
    return matched[0]


def _effective_rate(t: dict) -> Decimal:
    if t.get("rate_ex_vat") is not None:
        return _d(t["rate_ex_vat"])
    return _d(t["rate"])


def _charge_rate_and_quantity(
    tariffs: list[dict],
    tariff: dict,
    operational_qty: Decimal,
    on_date: date,
) -> tuple[Decimal, Decimal]:
    """Ставка и кол-во для суммы (учёт rate_line_code и quantity_divisor, как в Excel)."""
    rate_code = (tariff.get("rate_line_code") or "").strip()
    if rate_code:
        bill_code, bill_qty = operational_to_billing_quantity(tariff, operational_qty)
        rate_tariff = _tariff_for_line(tariffs, bill_code, on_date) or tariff
        rate = _effective_rate(rate_tariff)
        bill_qty = bill_qty.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return rate, bill_qty
    return _effective_rate(tariff), operational_qty


def _tariff_segments(
    tariffs: list[dict],
    line_code: str,
    period_start: date,
    period_end: date,
) -> list[tuple[date, date, int, dict]]:
    """Разбить месяц на отрезки с одним действующим тарифом (смена ставки внутри периода)."""
    relevant = [t for t in tariffs if t["billing_line_code"] == line_code]
    if not relevant:
        return []

    boundaries = {period_start}
    for t in relevant:
        vf = t["valid_from"]
        if isinstance(vf, str):
            vf = date.fromisoformat(vf[:10])
        vt = t.get("valid_to")
        if isinstance(vt, str):
            vt = date.fromisoformat(vt[:10])
        if period_start < vf <= period_end:
            boundaries.add(vf)
        if vt and period_start <= vt < period_end:
            boundaries.add(vt + timedelta(days=1))
    points = sorted(boundaries)
    segments: list[tuple[date, date, int, dict]] = []
    for i, seg_start in enumerate(points):
        if seg_start > period_end:
            break
        seg_end = period_end if i == len(points) - 1 else min(points[i + 1] - timedelta(days=1), period_end)
        tariff = _tariff_on(tariffs, line_code, seg_start)
        if not tariff:
            continue
        vt = tariff.get("valid_to")
        if isinstance(vt, str):
            vt = date.fromisoformat(vt[:10])
        if vt and seg_end > vt:
            seg_end = vt
        if seg_start > seg_end:
            continue
        days = (seg_end - seg_start).days + 1
        if days > 0:
            segments.append((seg_start, seg_end, days, tariff))
    return segments


def _segment_detail(seg_start: date, seg_end: date, rate: Decimal, qty: Decimal, amount: Decimal) -> dict:
    return {
        "date": str(seg_start),
        "description": f"{seg_start} — {seg_end}, тариф {rate}",
        "quantity": float(qty),
        "amount": float(amount),
        "source_type": "tariff_segment",
    }


def _apply_formula(formula: str, rate: Decimal, qty: Decimal, days: int | None) -> Decimal:
    if formula == "rate_times_days_times_qty" and days:
        return rate * Decimal(days) * qty
    if formula == "rate_times_days" and days:
        return rate * Decimal(days)
    return rate * qty


def _contract_reserved_area_m2(
    contract: dict,
    period_end: date,
) -> Decimal:
    """Резерв площади из billing_config договора (м² в сутки)."""
    config = contract.get("billing_config") or {}
    for key in ("fixed_storage_m2days", "fixed_m2days"):
        val = config.get(key)
        if val is not None:
            area = _d(val)
            if area > 0:
                return area
    return Decimal("0")


def _tariff_for_line(
    tariffs: list[dict],
    line_code: str,
    on_date: date,
) -> dict | None:
    """Тариф для строки биллинга; доп. коды (extra_manual_m3) — только если нет основного."""
    primary = _tariff_on(tariffs, line_code, on_date)
    if primary:
        return primary
    for alt, target in BILLING_MERGE_INTO.items():
        if target == line_code:
            alt_t = _tariff_on(tariffs, alt, on_date)
            if alt_t:
                return alt_t
    return None


def _iter_shift_code_qty(raw) -> list[tuple[str, Decimal]]:
    """extra_entries / area_entries: dict {code: qty} или list[{billing_line_code, quantity}]."""
    if not raw:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    if isinstance(raw, dict):
        return [(str(k), _d(v)) for k, v in raw.items() if k and _d(v) > 0]
    if isinstance(raw, list):
        out: list[tuple[str, Decimal]] = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            code = (entry.get("billing_line_code") or "").strip()
            if not code:
                continue
            qty = _d(entry.get("quantity") or entry.get("area_m2"))
            if qty > 0:
                out.append((code, qty))
        return out
    return []


def _sum_extra_entries(
    shifts: list[dict],
    period_start: date,
    period_end: date,
) -> dict[str, Decimal]:
    """Суммы из extra_entries упр. запасами по billing_line_code."""
    totals: dict[str, Decimal] = {}
    for shift in shifts:
        rd = shift.get("report_date")
        if isinstance(rd, str):
            rd = date.fromisoformat(rd[:10])
        if not (period_start <= rd <= period_end):
            continue
        for code, qty in _iter_shift_code_qty(shift.get("extra_entries")):
            bill_code = billing_line_for_tariff(code)
            totals[bill_code] = totals.get(bill_code, Decimal("0")) + qty
            if bill_code != code:
                totals[code] = totals.get(code, Decimal("0")) + qty
    return totals


def _parse_json_list(value) -> list:
    if not value:
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []
    return value if isinstance(value, list) else []


def _parse_area_entries(shift: dict) -> list[dict]:
    return _parse_json_list(shift.get("area_entries"))


def _avg_extra_area_m2(
    shifts: list[dict],
    period_start: date,
    period_end: date,
    calendar_days: int,
) -> Decimal:
    """Средняя доп. площадь (м²/сут) за месяц по отчётам упр. запасами."""
    from app.services.tariff_quantity import avg_inventory_area_m2

    return avg_inventory_area_m2(
        shifts, period_start, period_end, calendar_days, "storage_area_extra",
    )


_DEFAULT_SORT_ORDER: dict[str, int] = {
    "storage_area": 10,
    "storage_area_fixed": 11,
    "storage_area_extra": 12,
    "manual_m3": 20,
    "mechanized_m3": 30,
    "vehicle_docs": 40,
    "extra_vehicle_docs": 41,
    "repack_units": 50,
    "overtime_m3": 60,
    "inventory_hours": 70,
    "elco_drain_hours": 80,
}


def _billing_sort_order(tariff: dict | None, *, default: int = 900) -> int:
    """sort_order из тарифа ДС; fallback — по коду или default (0 — валидное значение)."""
    if not tariff:
        return default
    so = tariff.get("sort_order")
    if so is not None:
        return int(so)
    code = (tariff.get("billing_line_code") or "").strip()
    return _DEFAULT_SORT_ORDER.get(code, default)

# В блок «Детализация по отрезкам» — только доп. площадь; операционные строки в основной таблице.
TARIFF_SEGMENT_DETAIL_CODES = frozenset({"storage_area_extra"})


def _build_billing_quantity_context(
    contract: dict,
    period_start: date,
    period_end: date,
    operations: list[dict],
    shifts: list[dict],
) -> tuple[dict[str, Decimal], dict[str, Decimal], dict[str, Decimal], Decimal]:
    """Контекст количеств для resolve_tariff_period_quantity."""
    daily_totals = sum_daily_totals_by_code(contract["id"], period_start, period_end)
    vehicle_qty = sum_vehicle_report_quantities(operations, period_start, period_end)
    extra_totals = _sum_extra_entries(shifts, period_start, period_end)
    reserved_m2 = _contract_reserved_area_m2(contract, period_end)
    return daily_totals, vehicle_qty, extra_totals, reserved_m2


def _segment_quantity(
    tariff: dict,
    period_qty: Decimal,
    seg_start: date,
    seg_end: date,
    period_days: int,
    *,
    operations: list[dict],
    shifts: list[dict],
    daily_totals: dict[str, Decimal],
    vehicle_qty: dict[str, Decimal],
    extra_totals: dict[str, Decimal],
    contract_reserved_m2: Decimal,
    calendar_days: int,
) -> Decimal:
    """Количество на отрезке тарифа (для смены ставки внутри месяца)."""
    source = effective_quantity_source(tariff)
    if source == "auto_vehicle":
        return resolve_tariff_period_quantity(
            tariff,
            operations=operations,
            shifts=shifts,
            daily_totals=daily_totals,
            vehicle_qty=vehicle_qty,
            extra_totals=extra_totals,
            period_start=seg_start,
            period_end=seg_end,
            contract_reserved_m2=contract_reserved_m2,
            calendar_days=calendar_days,
        )
    if source == "auto_contract_param" or is_inventory_area_tariff(tariff):
        return period_qty
    if period_days <= 0:
        return period_qty
    seg_days = (seg_end - seg_start).days + 1
    return period_qty * Decimal(seg_days) / Decimal(period_days)


def _tariff_line_segments(
    tariffs: list[dict],
    line_code: str,
    period_start: date,
    period_end: date,
    period_days: int,
) -> list[tuple[date, date, int, dict]]:
    segments = _tariff_segments(tariffs, line_code, period_start, period_end)
    if segments:
        return segments
    t = _tariff_for_line(tariffs, line_code, period_end)
    if t:
        return [(period_start, period_end, period_days, t)]
    return []


def _area_segment_amount(
    rate: Decimal,
    area_m2: Decimal,
    seg_days: int,
) -> tuple[Decimal, Decimal]:
    """Площадь: ставка × м² × дни отрезка."""
    if area_m2 <= 0 or seg_days <= 0:
        return Decimal("0"), Decimal("0")
    seg_m2days = area_m2 * Decimal(seg_days)
    return rate * seg_m2days, seg_m2days


class StorageBillingStrategy:
    """Ответственное хранение (модель Аристон и аналоги)."""

    def calculate(
        self,
        contract: dict,
        year: int,
        month: int,
        tariffs: list[dict],
        operations: list[dict],
        shifts: list[dict],
        snapshots: list[dict] | None = None,
        **_kwargs,
    ) -> list[BillingLineResult]:
        snapshots = snapshots or []
        period_start, period_end = _month_bounds(year, month)
        days = _days_in_month(year, month)
        config = contract.get("billing_config") or {}
        lines: list[BillingLineResult] = []
        area_mode = config.get("area_mode", "two_tier")

        daily_totals, vehicle_qty, extra_totals, reserved_m2 = _build_billing_quantity_context(
            contract, period_start, period_end, operations, shifts,
        )
        qty_ctx = {
            "operations": operations,
            "shifts": shifts,
            "daily_totals": daily_totals,
            "vehicle_qty": vehicle_qty,
            "extra_totals": extra_totals,
            "contract_reserved_m2": reserved_m2,
            "calendar_days": days,
        }
        billed_codes: set[str] = set()

        if area_mode == "two_tier":
            for area_code in ("storage_area_fixed", "storage_area_extra"):
                tariff = _tariff_for_line(tariffs, area_code, period_end)
                if not tariff:
                    continue
                period_qty = resolve_tariff_period_quantity(
                    tariff,
                    period_start=period_start,
                    period_end=period_end,
                    **qty_ctx,
                )
                if area_code == "storage_area_fixed" and period_qty <= 0:
                    continue
                if area_code == "storage_area_extra" and period_qty <= 0:
                    continue
                segments = _tariff_line_segments(
                    tariffs, area_code, period_start, period_end, days,
                )
                if not segments:
                    continue
                total_amount = Decimal("0")
                billed_days = 0
                details: list[dict] = []
                first = segments[0][3]
                for seg_start, seg_end, seg_days, t in segments:
                    rate = _effective_rate(t)
                    area_m2 = _segment_quantity(
                        tariff, period_qty, seg_start, seg_end, days, **qty_ctx,
                    )
                    amt, seg_m2days = _area_segment_amount(rate, area_m2, seg_days)
                    total_amount += amt
                    billed_days += seg_days
                    # Фикс. площадь — авто из параметра ДС; отрезки в детализации не нужны.
                    if area_code != "storage_area_fixed":
                        details.append(_segment_detail(seg_start, seg_end, rate, seg_m2days, amt))
                default_names = {
                    "storage_area_fixed": "Площадь хранения, фиксированный объём, м²",
                    "storage_area_extra": "Площадь хранения, дополнительный объём, м²",
                }
                lines.append(
                    BillingLineResult(
                        line_code=area_code,
                        name=first.get("name") or default_names[area_code],
                        tariff=_effective_rate(first),
                        days_count=billed_days,
                        quantity=period_qty,
                        unit_code="m2",
                        amount_ex_vat=total_amount,
                        details=details,
                        sort_order=_billing_sort_order(first, default=_DEFAULT_SORT_ORDER[area_code]),
                        formula_comment=billing_formula_comment(
                            area_code,
                            period_qty,
                            days_count=billed_days,
                            unit_code="m2",
                            tariff=first,
                        ),
                    )
                )
                billed_codes.add(area_code)
        else:
            total_m2days = sum(_d(s["area_m2"]) for s in snapshots)
            t = _tariff_on(tariffs, "storage_area", period_end)
            if not t:
                t = _tariff_for_line(tariffs, "storage_area_fixed", period_end)
            if t and total_m2days > 0:
                rate = _effective_rate(t)
                amount = rate * total_m2days
                lines.append(
                    BillingLineResult(
                        line_code="storage_area",
                        name=t.get("name") or "Занимаемая площадь хранения, м²",
                        tariff=rate,
                        days_count=days,
                        quantity=total_m2days,
                        unit_code="m2",
                        amount_ex_vat=amount,
                        details=[{"date": str(s["snapshot_date"]), "quantity": float(s["area_m2"])} for s in snapshots],
                        sort_order=_billing_sort_order(t, default=_DEFAULT_SORT_ORDER["storage_area"]),
                        formula_comment=billing_formula_comment(
                            "storage_area",
                            total_m2days,
                            days_count=days,
                            unit_code="m2",
                            tariff=t,
                        ),
                    )
                )
                billed_codes.add("storage_area")

        for tariff in sorted(tariffs, key=lambda t: (_billing_sort_order(t), t.get("id") or 0)):
            code = (tariff.get("billing_line_code") or "").strip()
            if not code or code in BILLING_MERGE_INTO:
                continue
            bill_code = billing_line_for_tariff(code)
            if bill_code in billed_codes:
                continue
            if area_mode == "two_tier" and bill_code in AREA_LINE_CODES:
                continue

            period_qty = resolve_tariff_period_quantity(
                tariff,
                period_start=period_start,
                period_end=period_end,
                **qty_ctx,
            )
            if period_qty <= 0:
                continue

            segments = _tariff_line_segments(
                tariffs, bill_code, period_start, period_end, days,
            )
            if not segments:
                continue

            total_amount = Decimal("0")
            details: list[dict] = []
            seg_qty_total = Decimal("0")
            first_t = segments[0][3]

            for seg_start, seg_end, _seg_days, t in segments:
                seg_qty = _segment_quantity(
                    tariff, period_qty, seg_start, seg_end, days, **qty_ctx,
                )
                if seg_qty <= 0:
                    continue
                rate, charge_qty = _charge_rate_and_quantity(tariffs, t, seg_qty, seg_end)
                amt = rate * charge_qty
                total_amount += amt
                seg_qty_total += seg_qty
                if bill_code in TARIFF_SEGMENT_DETAIL_CODES:
                    details.append(_segment_detail(seg_start, seg_end, rate, seg_qty, amt))

            if seg_qty_total <= 0:
                continue

            billed_codes.add(bill_code)
            lines.append(
                BillingLineResult(
                    line_code=bill_code,
                    name=first_t.get("name") or code,
                    tariff=_effective_rate(first_t),
                    days_count=None,
                    quantity=seg_qty_total,
                    unit_code=first_t.get("unit_code") or "pcs",
                    amount_ex_vat=total_amount,
                    details=details,
                    sort_order=_billing_sort_order(first_t, default=_DEFAULT_SORT_ORDER.get(bill_code, 900)),
                    formula_comment=billing_formula_comment(
                        bill_code,
                        seg_qty_total,
                        unit_code=first_t.get("unit_code") or "pcs",
                        tariff=first_t,
                    ),
                )
            )

        return sorted(lines, key=lambda x: x.sort_order)


def billing_line_to_dict(line: BillingLineResult) -> dict[str, Any]:
    return {
        "line_code": line.line_code,
        "name": line.name,
        "tariff": float(line.tariff) if line.tariff is not None else None,
        "days_count": line.days_count,
        "quantity": float(line.quantity),
        "unit_code": line.unit_code,
        "amount_ex_vat": float(line.amount_ex_vat),
        "details": line.details,
        "sort_order": line.sort_order,
        "formula_comment": line.formula_comment,
    }
