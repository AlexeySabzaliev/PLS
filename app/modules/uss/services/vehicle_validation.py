"""Правила заполнения строки ежесменного отчёта транспортной логистики."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

ARRIVAL_EXPECTED = "expected"
ARRIVAL_ARRIVED = "arrived"
ARRIVAL_NO_SHOW = "no_show"

# Обязательны для статуса «обработано» (прицеп — нет, если ТС без прицепа)
_REQUIRED_FIELDS = ("tractor_plate", "operation_type_code", "registered_at", "departed_at")


def _norm_str(value: Any) -> str:
    return (value or "").strip() if value is not None else ""


def row_field_values(row: Any, payload: dict | None = None) -> dict[str, Any]:
    """Слить сохранённую строку и payload."""
    payload = payload or {}
    values = {
        "tractor_plate": payload.get("tractor_plate", getattr(row, "tractor_plate", None)),
        "trailer_plate": payload.get("trailer_plate", getattr(row, "trailer_plate", None)),
        "operation_type_code": payload.get("operation_type_code", getattr(row, "operation_type_code", None)),
        "registered_at": payload.get("registered_at", getattr(row, "registered_at", None)),
        "departed_at": payload.get("departed_at", getattr(row, "departed_at", None)),
        "arrival_status": payload.get("arrival_status", getattr(row, "arrival_status", ARRIVAL_EXPECTED)),
    }
    return values


def missing_required_fields(values: dict[str, Any]) -> list[str]:
    if values.get("arrival_status") == ARRIVAL_NO_SHOW:
        return []
    missing: list[str] = []
    if not _norm_str(values.get("tractor_plate")):
        missing.append("tractor_plate")
    if not _norm_str(values.get("operation_type_code")):
        missing.append("operation_type_code")
    if not values.get("registered_at"):
        missing.append("registered_at")
    if not values.get("departed_at"):
        missing.append("departed_at")
    return missing


def is_row_complete(values: dict[str, Any]) -> bool:
    return not missing_required_fields(values)


def field_labels() -> dict[str, str]:
    return {
        "tractor_plate": "Тягач, №",
        "trailer_plate": "Прицеп, №",
        "operation_type_code": "Операция",
        "registered_at": "Прибытие",
        "departed_at": "Убытие",
    }
