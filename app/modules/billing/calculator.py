"""Биллинг: интерфейс калькулятора (фаза 4 — заглушка)."""
from __future__ import annotations

from datetime import date
from typing import Any


class BillingCalculator:
    """Заглушка калькулятора. Фаза 4: портировать calculator.py из Billings."""

    def __init__(self, process_line_id: int | None = None):
        self.process_line_id = process_line_id

    def calculate_period(
        self,
        contract_id: int,
        period_from: date,
        period_to: date,
    ) -> dict[str, Any]:
        return {
            "status": "stub",
            "contract_id": contract_id,
            "period_from": period_from.isoformat(),
            "period_to": period_to.isoformat(),
            "process_line_id": self.process_line_id,
            "lines": [],
            "total": 0,
            "message": "Калькулятор будет подключён на фазе 4 после сверки с Excel",
        }
