"""Синхронизация м³ обработки по типу операции и обработки."""
from __future__ import annotations

from decimal import Decimal


def sync_handling_m3_updates(row: dict) -> dict[str, float]:
    """Заполнить inbound/outbound manual/mech в report_quantities из объёма и типа."""
    volume = Decimal(str(row.get("volume_document_m3") or 0))
    handling = (row.get("handling_type_code") or "").strip()
    op = (row.get("operation_type_code") or "inbound").strip()
    qty = volume if volume > 0 else Decimal("0")

    fields = {
        "inbound_manual_m3": Decimal("0"),
        "inbound_mech_m3": Decimal("0"),
        "outbound_manual_m3": Decimal("0"),
        "outbound_mech_m3": Decimal("0"),
    }
    if handling in ("manual", "mechanized") and qty > 0:
        if op == "inbound":
            key = "inbound_manual_m3" if handling == "manual" else "inbound_mech_m3"
        else:
            key = "outbound_manual_m3" if handling == "manual" else "outbound_mech_m3"
        fields[key] = qty
    return {k: float(v) for k, v in fields.items()}


def infer_handling_from_volumes(
    inbound_manual,
    inbound_mech,
    outbound_manual,
    outbound_mech,
) -> str:
    """Определить manual/mechanized по доминирующему объёму в ПРР."""
    manual = Decimal(str(inbound_manual or 0)) + Decimal(str(outbound_manual or 0))
    mech = Decimal(str(inbound_mech or 0)) + Decimal(str(outbound_mech or 0))
    if manual <= 0 and mech <= 0:
        return ""
    return "mechanized" if mech >= manual else "manual"
