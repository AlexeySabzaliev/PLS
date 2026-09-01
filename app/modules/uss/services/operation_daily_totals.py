"""Суточные итоги без привязки к ТС."""
from __future__ import annotations

from datetime import date

from app.db import db
from app.modules.uss.models import OperationDailyTotal


def upsert_daily_totals(
    contract_id: int,
    warehouse_id: int,
    report_date: date,
    entries: list[dict],
) -> list[dict]:
    saved = []
    for entry in entries:
        code = entry.get("billing_line_code")
        if not code:
            continue
        qty = entry.get("quantity", 0)
        row = OperationDailyTotal.query.filter_by(
            contract_id=contract_id,
            warehouse_id=warehouse_id,
            report_date=report_date,
            billing_line_code=code,
        ).first()
        if row:
            row.quantity = qty
        else:
            row = OperationDailyTotal(
                contract_id=contract_id,
                warehouse_id=warehouse_id,
                report_date=report_date,
                billing_line_code=code,
                quantity=qty,
            )
            db.session.add(row)
        saved.append({"billing_line_code": code, "quantity": float(qty)})
    db.session.commit()
    return saved


def list_daily_totals(contract_id: int, warehouse_id: int, report_date: date) -> list[dict]:
    rows = OperationDailyTotal.query.filter_by(
        contract_id=contract_id,
        warehouse_id=warehouse_id,
        report_date=report_date,
    ).all()
    return [
        {"billing_line_code": r.billing_line_code, "quantity": float(r.quantity or 0)}
        for r in rows
    ]
