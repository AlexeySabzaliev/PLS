"""Очистка сирот и неактивных записей справочников."""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import text

from app.db import db
from app.modules.reference.models import Client, Contract, ContractAmendment, TariffRule


@dataclass
class VacuumReport:
    dry_run: bool = False
    actions: list[str] = field(default_factory=list)
    removed: int = 0

    def log(self, msg: str) -> None:
        prefix = "[dry-run] " if self.dry_run else ""
        self.actions.append(f"{prefix}{msg}")


def vacuum_orphans(*, dry_run: bool = True) -> VacuumReport:
    """Удалить ставки без договора/ДС и договоры без клиента (hard delete)."""
    report = VacuumReport(dry_run=dry_run)
    report.log("Старт db-vacuum")

    orphan_tariffs = db.session.execute(
        text(
            """
            SELECT t.id, t.billing_line_code
            FROM tariff_rules t
            LEFT JOIN contracts c ON c.id = t.contract_id
            LEFT JOIN contract_amendments a ON a.id = t.amendment_id
            WHERE c.id IS NULL OR a.id IS NULL
            """
        )
    ).mappings().all()
    for row in orphan_tariffs:
        report.log(f"  − сирота-ставка id={row['id']} ({row['billing_line_code']})")
        if not dry_run:
            db.session.execute(text("DELETE FROM tariff_rules WHERE id = :id"), {"id": row["id"]})
        report.removed += 1

    inactive_clients = Client.query.filter_by(is_active=False).all()
    for cl in inactive_clients:
        if Contract.query.filter_by(client_id=cl.id).count():
            continue
        report.log(f"  − неактивный клиент без договоров id={cl.id} «{cl.name}»")
        if not dry_run:
            db.session.delete(cl)
        report.removed += 1

    superseded_empty = db.session.execute(
        text(
            """
            SELECT a.id, a.number, a.contract_id
            FROM contract_amendments a
            WHERE a.status = 'superseded'
              AND NOT EXISTS (SELECT 1 FROM tariff_rules t WHERE t.amendment_id = a.id)
            """
        )
    ).mappings().all()
    for row in superseded_empty:
        amd = db.session.get(ContractAmendment, row["id"])
        if not amd:
            continue
        report.log(f"  − пустое superseded ДС id={row['id']} №{row['number']}")
        if not dry_run:
            db.session.delete(amd)
        report.removed += 1

    if not dry_run:
        db.session.commit()
    else:
        db.session.rollback()

    report.log(f"Готово: удалено/помечено {report.removed}")
    return report
