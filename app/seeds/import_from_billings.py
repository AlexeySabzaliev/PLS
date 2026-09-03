"""Одноразовый импорт справочников и смен из БД Billings в ПЛС (insert-only)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import create_engine, text

from app.db import db
from app.modules.reference.models import (
    Client,
    Contract,
    ContractAmendment,
    ProductType,
    TariffRule,
    UnitOfMeasure,
    Warehouse,
)
from app.modules.uss.models import OperationDailyTotal, ShiftReport, VehicleOperation
from app.modules.uss.services.staff_positions import create_staff_position
from app.seeds.import_staff_from_billings import import_staff_from_billings


@dataclass
class ImportReport:
    dry_run: bool = False
    only: str = "all"
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


def _fetch(sql: str, params: dict | None = None) -> list[dict]:
    engine = _billings_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params or {}).mappings().all()
    return [dict(r) for r in rows]


def _unit_map() -> dict[str, UnitOfMeasure]:
    return {u.code: u for u in UnitOfMeasure.query.all()}


def _product_type_map() -> dict[str, ProductType]:
    return {p.code: p for p in ProductType.query.all()}


def _touch_import(entity_type: str, entity_key: str, billings_id: int | None = None) -> None:
    db.session.execute(
        text(
            """
            INSERT INTO import_registry (entity_type, entity_key, imported_at, billings_id)
            VALUES (:entity_type, :entity_key, :imported_at, :billings_id)
            ON CONFLICT (entity_type, entity_key) DO UPDATE
            SET imported_at = excluded.imported_at,
                billings_id = COALESCE(excluded.billings_id, import_registry.billings_id)
            """
        ),
        {
            "entity_type": entity_type,
            "entity_key": entity_key,
            "imported_at": datetime.utcnow(),
            "billings_id": billings_id,
        },
    )


def _was_user_modified(entity_type: str, entity_key: str, updated_at: datetime | None) -> bool:
    row = db.session.execute(
        text(
            "SELECT imported_at FROM import_registry "
            "WHERE entity_type = :entity_type AND entity_key = :entity_key"
        ),
        {"entity_type": entity_type, "entity_key": entity_key},
    ).mappings().first()
    if not row or not updated_at:
        return False
    imported_at = row["imported_at"]
    if imported_at and updated_at > imported_at:
        return True
    return False


def _import_clients(report: ImportReport, *, skip_existing: bool) -> dict[int, Client]:
    mapping: dict[int, Client] = {}
    for row in _fetch(
        "SELECT id, name, security_name, is_active FROM clients WHERE is_active = TRUE ORDER BY id"
    ):
        name = (row.get("name") or "").strip()
        if not name:
            report.skipped += 1
            continue
        key = f"name:{name.lower()}"
        existing = Client.query.filter(db.func.lower(Client.name) == name.lower()).first()
        if existing:
            mapping[row["id"]] = existing
            if skip_existing or _was_user_modified("client", key, existing.updated_at):
                report.skipped += 1
                report.log(f"Клиент «{name}»: уже в ПЛС id={existing.id} — пропуск")
                continue
        if report.dry_run:
            report.log(f"  + клиент «{name}»")
            report.imported += 1
            continue
        if not existing:
            existing = Client(
                name=name,
                security_name=row.get("security_name"),
                is_active=True,
            )
            db.session.add(existing)
            db.session.flush()
            report.log(f"  + клиент «{name}» id={existing.id}")
            report.imported += 1
        _touch_import("client", key, row["id"])
        mapping[row["id"]] = existing
    return mapping


def _import_warehouses(report: ImportReport, *, skip_existing: bool) -> dict[int, Warehouse]:
    mapping: dict[int, Warehouse] = {}
    for row in _fetch(
        "SELECT id, code, name, security_visit_place, is_active "
        "FROM warehouses WHERE is_active = TRUE ORDER BY id"
    ):
        code = (row.get("code") or "").strip()
        if not code:
            report.skipped += 1
            continue
        key = f"code:{code}"
        existing = Warehouse.query.filter_by(code=code).first()
        if existing:
            mapping[row["id"]] = existing
            if skip_existing or _was_user_modified("warehouse", key, existing.updated_at):
                report.skipped += 1
                report.log(f"Склад {code}: уже в ПЛС id={existing.id} — пропуск")
                continue
        if report.dry_run:
            report.log(f"  + склад {code}")
            report.imported += 1
            continue
        if not existing:
            existing = Warehouse(
                code=code,
                name=row.get("name") or code,
                security_visit_place=row.get("security_visit_place"),
                is_active=True,
            )
            db.session.add(existing)
            db.session.flush()
            report.log(f"  + склад {code} id={existing.id}")
            report.imported += 1
        _touch_import("warehouse", key, row["id"])
        mapping[row["id"]] = existing
    return mapping


def _import_contracts(
    report: ImportReport,
    *,
    clients: dict[int, Client],
    warehouses: dict[int, Warehouse],
    skip_existing: bool,
) -> dict[int, Contract]:
    mapping: dict[int, Contract] = {}
    pt_default = ProductType.query.filter_by(code="RESPONSIBLE_STORAGE").first()
    for row in _fetch(
        """
        SELECT c.id, c.client_id, c.warehouse_id, c.product_type_id,
               c.number, c.status, c.billing_config
        FROM contracts c
        ORDER BY c.id
        """
    ):
        number = (row.get("number") or "").strip()
        pls_client = clients.get(row["client_id"])
        pls_wh = warehouses.get(row["warehouse_id"])
        if not number or not pls_client or not pls_wh:
            report.skipped += 1
            continue
        key = f"{pls_client.id}:{number}"
        existing = Contract.query.filter_by(client_id=pls_client.id, number=number).first()
        if existing:
            mapping[row["id"]] = existing
            if skip_existing or _was_user_modified("contract", key, existing.updated_at):
                report.skipped += 1
                report.log(f"Договор {number}: уже в ПЛС id={existing.id} — пропуск")
                continue
        if report.dry_run:
            report.log(f"  + договор {number}")
            report.imported += 1
            continue
        if not existing:
            existing = Contract(
                client_id=pls_client.id,
                warehouse_id=pls_wh.id,
                product_type_id=pt_default.id if pt_default else row["product_type_id"],
                number=number,
                status=row.get("status") or "active",
                billing_config=row.get("billing_config") or {},
            )
            db.session.add(existing)
            db.session.flush()
            report.log(f"  + договор {number} id={existing.id}")
            report.imported += 1
        _touch_import("contract", key, row["id"])
        mapping[row["id"]] = existing
    return mapping


def _import_amendments(
    report: ImportReport,
    *,
    contracts: dict[int, Contract],
    skip_existing: bool,
) -> dict[int, ContractAmendment]:
    mapping: dict[int, ContractAmendment] = {}
    for row in _fetch(
        """
        SELECT id, contract_id, number, status, effective_from, effective_to,
               source_document AS source_file_path
        FROM contract_amendments
        ORDER BY contract_id, effective_from, id
        """
    ):
        pls_contract = contracts.get(row["contract_id"])
        number = (row.get("number") or "").strip()
        if not pls_contract or not number:
            report.skipped += 1
            continue
        key = f"{pls_contract.id}:{number}"
        existing = ContractAmendment.query.filter_by(
            contract_id=pls_contract.id,
            number=number,
        ).first()
        if existing:
            mapping[row["id"]] = existing
            if skip_existing or _was_user_modified("amendment", key, existing.updated_at):
                report.skipped += 1
                continue
        if report.dry_run:
            report.log(f"  + ДС {number} (договор {pls_contract.number})")
            report.imported += 1
            continue
        if not existing:
            existing = ContractAmendment(
                contract_id=pls_contract.id,
                number=number,
                status=row.get("status") or "active",
                effective_from=row["effective_from"],
                effective_to=row.get("effective_to"),
                source_file_path=row.get("source_file_path"),
            )
            db.session.add(existing)
            db.session.flush()
            report.log(f"  + ДС {number} id={existing.id}")
            report.imported += 1
        _touch_import("amendment", key, row["id"])
        mapping[row["id"]] = existing
    return mapping


def _import_tariffs(
    report: ImportReport,
    *,
    contracts: dict[int, Contract],
    amendments: dict[int, ContractAmendment],
    skip_existing: bool,
) -> None:
    units = _unit_map()
    for row in _fetch(
        """
        SELECT t.id, t.contract_id, t.amendment_id, t.billing_line_code, t.name,
               t.unit_id, t.report_role, t.report_scope, t.quantity_source,
               NULL::text AS rate_line_code, 1 AS quantity_divisor, t.is_custom, t.price_agreed,
               t.sort_order, t.valid_from, t.valid_to, t.rate_ex_vat, t.formula,
               u.code AS unit_code
        FROM tariff_rules t
        LEFT JOIN units_of_measure u ON u.id = t.unit_id
        ORDER BY t.contract_id, t.amendment_id, t.sort_order, t.id
        """
    ):
        pls_contract = contracts.get(row["contract_id"])
        pls_amd = amendments.get(row["amendment_id"]) if row.get("amendment_id") else None
        code = (row.get("billing_line_code") or "").strip()
        if not pls_contract or not code:
            report.skipped += 1
            continue
        amd_id = pls_amd.id if pls_amd else None
        key = f"{pls_contract.id}:{amd_id}:{code}"
        q = TariffRule.query.filter_by(
            contract_id=pls_contract.id,
            billing_line_code=code,
        )
        if amd_id:
            q = q.filter_by(amendment_id=amd_id)
        existing = q.first()
        if existing:
            if skip_existing or _was_user_modified("tariff", key, existing.updated_at):
                report.skipped += 1
                continue
        if not pls_amd:
            report.skipped += 1
            report.log(f"  ! ставка {code}: нет ДС в ПЛС — пропуск")
            continue
        unit = units.get(row.get("unit_code")) if row.get("unit_code") else None
        if report.dry_run:
            report.log(f"  + ставка {code} ({pls_contract.number})")
            report.imported += 1
            continue
        if not existing:
            existing = TariffRule(
                contract_id=pls_contract.id,
                amendment_id=pls_amd.id,
                billing_line_code=code,
                name=row.get("name") or code,
                unit_id=unit.id if unit else row.get("unit_id"),
                report_role=row.get("report_role"),
                report_scope=row.get("report_scope"),
                quantity_source=row.get("quantity_source"),
                rate_line_code=row.get("rate_line_code"),
                quantity_divisor=row.get("quantity_divisor") or 1,
                is_custom=bool(row.get("is_custom")),
                price_agreed=row.get("price_agreed") if row.get("price_agreed") is not None else True,
                sort_order=row.get("sort_order") or 0,
                valid_from=row["valid_from"],
                valid_to=row.get("valid_to"),
                rate_ex_vat=Decimal(str(row["rate_ex_vat"])) if row.get("rate_ex_vat") is not None else None,
                formula=row.get("formula"),
            )
            db.session.add(existing)
            report.log(f"  + ставка {code}")
            report.imported += 1
        _touch_import("tariff", key, row["id"])


def _import_shifts(
    report: ImportReport,
    *,
    contracts: dict[int, Contract],
    warehouses: dict[int, Warehouse],
    skip_existing: bool,
) -> None:
    for row in _fetch(
        """
        SELECT id, contract_id, warehouse_id, operation_date, tractor_plate, trailer_plate,
               COALESCE(vehicle_number, tractor_plate) AS plate_number, operation_type_code, seal_number, torg2_number,
               volume_document_m3, handling_type_code, extra_handling_m3,
               extra_document_set_qty, registered_at, departed_at, report_quantities, source
        FROM vehicle_operations
        ORDER BY operation_date, id
        """
    ):
        pls_contract = contracts.get(row["contract_id"])
        pls_wh = warehouses.get(row["warehouse_id"])
        if not pls_contract or not pls_wh:
            report.skipped += 1
            continue
        op_date = row["operation_date"]
        plate = row.get("plate_number") or row.get("tractor_plate") or ""
        key = f"vo:{pls_contract.id}:{pls_wh.id}:{op_date}:{plate}:{row['id']}"
        existing = VehicleOperation.query.filter_by(
            contract_id=pls_contract.id,
            warehouse_id=pls_wh.id,
            operation_date=op_date,
            plate_number=plate or None,
        ).first()
        if existing and skip_existing:
            report.skipped += 1
            continue
        if report.dry_run:
            report.log(f"  + ТС {plate} {op_date}")
            report.imported += 1
            continue
        if not existing:
            vo = VehicleOperation(
                contract_id=pls_contract.id,
                warehouse_id=pls_wh.id,
                operation_date=op_date,
                plate_number=plate or None,
                tractor_plate=row.get("tractor_plate"),
                trailer_plate=row.get("trailer_plate"),
                operation_type_code=row.get("operation_type_code"),
                seal_number=row.get("seal_number"),
                torg2_number=row.get("torg2_number"),
                volume_document_m3=row.get("volume_document_m3"),
                handling_type_code=row.get("handling_type_code"),
                extra_handling_m3=row.get("extra_handling_m3"),
                extra_document_set_qty=row.get("extra_document_set_qty"),
                registered_at=row.get("registered_at"),
                departed_at=row.get("departed_at"),
                report_quantities=row.get("report_quantities") or {},
                source=row.get("source") or "import",
            )
            db.session.add(vo)
            report.imported += 1
        _touch_import("vehicle_operation", key, row["id"])

    for row in _fetch(
        """
        SELECT contract_id, warehouse_id, report_date, billing_line_code, quantity
        FROM operation_daily_totals
        ORDER BY report_date, id
        """
    ):
        pls_contract = contracts.get(row["contract_id"])
        pls_wh = warehouses.get(row["warehouse_id"])
        code = row.get("billing_line_code")
        if not pls_contract or not pls_wh or not code:
            report.skipped += 1
            continue
        key = f"odt:{pls_contract.id}:{pls_wh.id}:{row['report_date']}:{code}"
        existing = OperationDailyTotal.query.filter_by(
            contract_id=pls_contract.id,
            warehouse_id=pls_wh.id,
            report_date=row["report_date"],
            billing_line_code=code,
        ).first()
        if existing and skip_existing:
            report.skipped += 1
            continue
        if report.dry_run:
            report.log(f"  + суточное {code} {row['report_date']}")
            report.imported += 1
            continue
        if not existing:
            db.session.add(
                OperationDailyTotal(
                    contract_id=pls_contract.id,
                    warehouse_id=pls_wh.id,
                    report_date=row["report_date"],
                    billing_line_code=code,
                    quantity=row.get("quantity") or 0,
                )
            )
            report.imported += 1
        _touch_import("daily_total", key, None)


def import_from_billings(
    *,
    dry_run: bool = False,
    only: str = "all",
    skip_existing: bool = True,
) -> ImportReport:
    """Импорт из Billings: только вставка отсутствующих записей (preserve user edits)."""
    report = ImportReport(dry_run=dry_run, only=only)
    report.log(f"Старт import-from-billings (only={only}, skip_existing={skip_existing})")

    if only in ("all", "reference"):
        report.log("--- Справочники ---")
        clients = _import_clients(report, skip_existing=skip_existing)
        warehouses = _import_warehouses(report, skip_existing=skip_existing)
        contracts = _import_contracts(
            report, clients=clients, warehouses=warehouses, skip_existing=skip_existing,
        )
        amendments = _import_amendments(
            report, contracts=contracts, skip_existing=skip_existing,
        )
        _import_tariffs(
            report, contracts=contracts, amendments=amendments, skip_existing=skip_existing,
        )
        staff_report = import_staff_from_billings(dry_run=dry_run, skip_existing=skip_existing)
        report.actions.extend(staff_report.actions)
        report.imported += staff_report.imported
        report.skipped += staff_report.skipped

    if only in ("all", "shifts"):
        report.log("--- Смены ---")
        if only == "shifts" and not Contract.query.first():
            report.log("Нет договоров в ПЛС — сначала импортируйте reference")
        else:
            clients = {r["id"]: Client.query.filter(db.func.lower(Client.name) == (r.get("name") or "").lower()).first()
                       for r in _fetch("SELECT id, name FROM clients")}
            clients = {k: v for k, v in clients.items() if v}
            warehouses = {
                r["id"]: Warehouse.query.filter_by(code=r["code"]).first()
                for r in _fetch("SELECT id, code FROM warehouses")
            }
            warehouses = {k: v for k, v in warehouses.items() if v}
            contracts = {}
            for r in _fetch("SELECT id, client_id, number FROM contracts"):
                pls_c = clients.get(r["client_id"])
                if pls_c:
                    ct = Contract.query.filter_by(client_id=pls_c.id, number=r["number"]).first()
                    if ct:
                        contracts[r["id"]] = ct
            _import_shifts(
                report, contracts=contracts, warehouses=warehouses, skip_existing=skip_existing,
            )

    if not dry_run:
        db.session.commit()
    else:
        db.session.rollback()

    report.log(f"Готово: импортировано {report.imported}, пропущено {report.skipped}")
    return report
