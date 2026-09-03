"""Импорт штатных позиций ФОТ из БД Billings в ПЛС (только warehouse_staff_positions)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import create_engine, text

from app.db import db
from app.modules.reference.models import Warehouse
from app.modules.uss.models import WarehouseStaffPosition
from app.modules.uss.services.staff_positions import create_staff_position


@dataclass
class StaffImportReport:
    dry_run: bool = False
    actions: list[str] = field(default_factory=list)
    imported: int = 0
    skipped: int = 0

    def log(self, msg: str) -> None:
        prefix = "[dry-run] " if self.dry_run else ""
        self.actions.append(f"{prefix}{msg}")


def _billings_engine():
    uri = os.getenv("BILLINGS_DATABASE_URL", "").strip()
    if not uri:
        raise RuntimeError(
            "Переменная BILLINGS_DATABASE_URL не задана "
            "(например postgresql://user:pass@host/billings)"
        )
    return create_engine(uri)


def _fetch_billings_staff(*, warehouse_code: str | None = None) -> list[dict]:
    sql = """
        SELECT w.code AS warehouse_code,
               p.name,
               p.monthly_rate,
               p.headcount,
               p.sort_order,
               p.is_active
        FROM warehouse_staff_positions p
        JOIN warehouses w ON w.id = p.warehouse_id
        WHERE p.is_active = TRUE
    """
    params: dict = {}
    if warehouse_code:
        sql += " AND w.code = :warehouse_code"
        params["warehouse_code"] = warehouse_code
    sql += " ORDER BY w.code, p.sort_order, p.name, p.id"

    engine = _billings_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]


def import_staff_from_billings(
    *,
    warehouse_code: str | None = None,
    dry_run: bool = False,
    skip_existing: bool = True,
) -> StaffImportReport:
    """Скопировать штат из Billings в ПЛС по коду склада. Другие справочники не трогаем."""
    report = StaffImportReport(dry_run=dry_run)
    rows = _fetch_billings_staff(warehouse_code=warehouse_code)
    if not rows:
        report.log("В Billings нет активных штатных позиций для импорта")
        return report

    by_wh: dict[str, list[dict]] = {}
    for row in rows:
        by_wh.setdefault(row["warehouse_code"], []).append(row)

    effective_from = date.today().replace(day=1).isoformat()

    for wh_code, items in sorted(by_wh.items()):
        pls_wh = Warehouse.query.filter_by(code=wh_code, is_active=True).first()
        if not pls_wh:
            report.log(f"Склад {wh_code}: нет в ПЛС — пропуск ({len(items)} поз.)")
            report.skipped += len(items)
            continue

        existing = WarehouseStaffPosition.query.filter_by(
            warehouse_id=pls_wh.id,
            is_active=True,
        ).count()
        if skip_existing and existing:
            report.log(
                f"Склад {wh_code} (id={pls_wh.id}): уже {existing} поз. — пропуск импорта"
            )
            report.skipped += len(items)
            continue

        for item in items:
            name = (item.get("name") or "").strip()
            if not name:
                report.skipped += 1
                continue
            payload = {
                "name": name,
                "monthly_rate": float(item.get("monthly_rate") or 0),
                "headcount": int(item.get("headcount") or 1),
                "sort_order": int(item.get("sort_order") or 100),
                "effective_from": effective_from,
            }
            if dry_run:
                report.log(f"  + {wh_code}: {name} ×{payload['headcount']} @ {payload['monthly_rate']}")
                report.imported += 1
                continue
            create_staff_position(pls_wh.id, payload)
            report.imported += 1
            report.log(f"  + {wh_code}: {name}")

    if not dry_run:
        db.session.commit()
    else:
        db.session.rollback()

    report.log(f"Готово: импортировано {report.imported}, пропущено {report.skipped}")
    return report
