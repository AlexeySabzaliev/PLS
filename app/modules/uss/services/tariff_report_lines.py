"""Ставки для операционных отчётов по ролям."""
from __future__ import annotations

from datetime import date

from app.modules.uss.services.report_schema import (
    schema_for_contract_role,
    tariffs_by_role_from_schema,
)


def active_report_tariffs(
    contract_id: int,
    on_date: date,
    *,
    role: str | None = None,
    scope: str | None = None,
) -> list[dict]:
    if not role:
        return []
    sch = schema_for_contract_role(contract_id, on_date, role)
    out = sch["vehicle_inputs"] + sch["period_inputs"]
    if role == "inventory_management":
        out = sch["inventory_areas"] + sch["inventory_extra"]
    if scope == "vehicle":
        return [t for t in out if t.get("input_kind") == "vehicle"]
    if scope == "period":
        return [t for t in out if t.get("input_kind") == "period"]
    return out


def tariffs_by_role_for_contracts(
    contract_ids: list[int],
    on_date: date,
    role: str,
) -> dict[int, dict]:
    return tariffs_by_role_from_schema(contract_ids, on_date, role)
