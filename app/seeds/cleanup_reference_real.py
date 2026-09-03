"""Очистка справочников: только Аристон и Гауф, ДС из реальных DOCX."""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from flask import current_app
from sqlalchemy import text

from app.db import db
from app.modules.reference.amendment_apply import apply_parsed_to_amendment
from app.modules.reference.amendment_docx_import import ParsedAmendment, parse_amendment_docx
from app.modules.reference.client_names import (
    CANONICAL_ARISTON_CLIENT,
    CANONICAL_GAUFF_CLIENT,
    canonical_client_name,
    normalize_client_name,
)
from app.modules.reference.models import (
    Client,
    Contract,
    ContractAmendment,
    ProductType,
    TariffRule,
    Warehouse,
)
from app.seeds.ariston_tariffs import ARISTON_TARIFF_SPECS, AristonTariffSpec
from app.services.db_backup import BackupError, create_backup

CANONICAL_ARISTON_CONTRACT = '№ АР-БСХ 24 от 06 июня 2024'
CANONICAL_GAUFF_CONTRACT = '№ Х-30/2025 от 19.09.2025 г.'

ARISTON_AMENDMENT_FILES = (
    "ДС №4 к Договору_ОХ_Аристон_180925_индексация (1).docx",
    "ДС №5 к Договору_ОХ_Аристон_170626_изменение ставок (1).docx",
    "ДС №6 к Договору_ОХ_Аристон_010926_изменение ставки на доп.площади.docx",
)
GAUFF_AMENDMENT_FILE = "ДС 3 к Договору Х-30-2025_270826 (2).docx"

_SPEC_BY_CODE: dict[str, AristonTariffSpec] = {s.billing_line_code: s for s in ARISTON_TARIFF_SPECS}


@dataclass
class CleanupReport:
    dry_run: bool = False
    actions: list[str] = field(default_factory=list)

    def log(self, msg: str) -> None:
        prefix = "[dry-run] " if self.dry_run else ""
        self.actions.append(f"{prefix}{msg}")


def _is_ariston_name(name: str) -> bool:
    key = normalize_client_name(name)
    return key in {"аристон", "ооо аристон термо русь", "ariston"}


def _is_gauff_name(name: str) -> bool:
    key = normalize_client_name(name)
    return "гауф" in key


def _is_ariston_contract(number: str, client_name: str) -> bool:
    num = (number or "").upper()
    return "АР-БСХ" in num or "STR-OH-ARISTON" in num or _is_ariston_name(client_name)


def _is_gauff_contract(number: str, client_name: str) -> bool:
    num = (number or "").upper()
    return "Х-30" in num or _is_gauff_name(client_name)


def _end_of_year(d: date) -> date:
    return date(d.year, 12, 31)


def _compute_effective_to(
    effective_from: date,
    next_effective_from: date | None,
) -> date:
    if next_effective_from:
        return next_effective_from - timedelta(days=1)
    return _end_of_year(effective_from)


def _enrich_ariston_tariffs(parsed: ParsedAmendment) -> None:
    for t in parsed.tariffs:
        spec = _SPEC_BY_CODE.get(t.billing_line_code)
        if spec:
            t.name = spec.name


def _billing_config_from_parameters(parsed: ParsedAmendment) -> dict:
    cfg: dict = {"area_mode": "two_tier"}
    for p in parsed.parameters:
        if p.param_type == "fixed_storage_m2days":
            cfg["fixed_m2days"] = int(p.numeric_value)
    return cfg


def _resolve_docx(path: Path | None, default_name: str, docx_dir: Path | None) -> Path:
    if path and path.exists():
        return path
    if docx_dir:
        candidate = docx_dir / default_name
        if candidate.exists():
            return candidate
    downloads = Path.home() / "Downloads" / default_name
    if downloads.exists():
        return downloads
    raise FileNotFoundError(default_name)


def _load_parsed(path: Path, *, ariston: bool) -> ParsedAmendment:
    parsed = parse_amendment_docx(path.read_bytes(), path.name)
    if ariston:
        _enrich_ariston_tariffs(parsed)
    return parsed


def _pick_or_create_client(name: str, report: CleanupReport) -> Client:
    canonical = CANONICAL_ARISTON_CLIENT if _is_ariston_name(name) else canonical_client_name(name)
    matches = [
        c for c in Client.query.order_by(Client.id).all()
        if normalize_client_name(c.name) == normalize_client_name(canonical)
    ]
    if matches:
        client = matches[0]
        if client.name != canonical:
            report.log(f"Клиент id={client.id}: «{client.name}» -> «{canonical}»")
            if not report.dry_run:
                client.name = canonical
        if len(matches) > 1:
            report.log(f"Дублей клиента «{canonical}»: {len(matches)} (удалятся после переноса договоров)")
        return client
    report.log(f"Создать клиента «{canonical}»")
    client = Client(name=canonical, is_active=True)
    if not report.dry_run:
        db.session.add(client)
        db.session.flush()
    return client


def _pick_or_create_contract(
    *,
    client: Client,
    number: str,
    warehouse_id: int,
    product_type_id: int,
    billing_config: dict,
    report: CleanupReport,
) -> Contract:
    rows = Contract.query.filter_by(client_id=client.id, warehouse_id=warehouse_id).all()
    chosen = None
    for row in rows:
        if _is_ariston_contract(row.number, client.name) or _is_gauff_contract(row.number, client.name):
            chosen = row
            break
    if chosen is None and rows:
        chosen = rows[0]
    if chosen is None:
        report.log(f"Создать договор «{number}» для клиента id={client.id}")
        chosen = Contract(
            client_id=client.id,
            warehouse_id=warehouse_id,
            product_type_id=product_type_id,
            number=number,
            status="active",
            billing_config=billing_config,
        )
        if not report.dry_run:
            db.session.add(chosen)
            db.session.flush()
        return chosen

    report.log(f"Канонический договор id={chosen.id} «{chosen.number}» -> «{number}»")
    if not report.dry_run:
        chosen.number = number
        chosen.status = "active"
        chosen.billing_config = billing_config
        chosen.client_id = client.id
    return chosen


def _remap_daily_totals(src_id: int, target_id: int, report: CleanupReport) -> None:
    rows = db.session.execute(
        text(
            "SELECT id, report_date, billing_line_code, quantity "
            "FROM operation_daily_totals WHERE contract_id = :src"
        ),
        {"src": src_id},
    ).mappings().all()
    if not rows:
        return
    report.log(f"Слияние {len(rows)} operation_daily_totals: contract {src_id} -> {target_id}")
    for row in rows:
        existing = db.session.execute(
            text(
                "SELECT id, quantity FROM operation_daily_totals "
                "WHERE contract_id = :cid AND report_date = :d AND billing_line_code = :code"
            ),
            {"cid": target_id, "d": row["report_date"], "code": row["billing_line_code"]},
        ).mappings().first()
        if existing:
            new_qty = float(Decimal(str(existing["quantity"])) + Decimal(str(row["quantity"])))
            db.session.execute(
                text("UPDATE operation_daily_totals SET quantity = :q WHERE id = :id"),
                {"q": new_qty, "id": existing["id"]},
            )
            db.session.execute(
                text("DELETE FROM operation_daily_totals WHERE id = :id"),
                {"id": row["id"]},
            )
        else:
            db.session.execute(
                text("UPDATE operation_daily_totals SET contract_id = :target WHERE id = :id"),
                {"target": target_id, "id": row["id"]},
            )


def _remap_operations(ariston_id: int, gauff_id: int, report: CleanupReport) -> None:
    contracts = {
        row.id: row
        for row in Contract.query.all()
    }
    clients = {c.id: c for c in Client.query.all()}

    for row in contracts.values():
        client = clients.get(row.client_id)
        client_name = client.name if client else ""
        target = None
        if _is_ariston_contract(row.number, client_name):
            target = ariston_id
        elif _is_gauff_contract(row.number, client_name):
            target = gauff_id
        if target and row.id != target:
            for table in ("vehicle_operations", "billing_periods"):
                count = db.session.execute(
                    text(f"SELECT COUNT(*) FROM {table} WHERE contract_id = :cid"),
                    {"cid": row.id},
                ).scalar() or 0
                if count:
                    report.log(f"Перенос {count} строк {table}: contract {row.id} -> {target}")
                    if not report.dry_run:
                        db.session.execute(
                            text(f"UPDATE {table} SET contract_id = :target WHERE contract_id = :src"),
                            {"target": target, "src": row.id},
                        )
            count = db.session.execute(
                text("SELECT COUNT(*) FROM operation_daily_totals WHERE contract_id = :cid"),
                {"cid": row.id},
            ).scalar() or 0
            if count and not report.dry_run:
                _remap_daily_totals(row.id, target, report)
            elif count:
                report.log(f"Слияние {count} operation_daily_totals: contract {row.id} -> {target}")

    for table in ("vehicle_operations", "operation_daily_totals", "billing_periods"):
        count = db.session.execute(
            text(
                f"SELECT COUNT(*) FROM {table} "
                f"WHERE contract_id NOT IN (:a, :g)"
            ),
            {"a": ariston_id, "g": gauff_id},
        ).scalar() or 0
        if count:
            report.log(f"Удалить {count} строк {table} без канонических договоров")
            if not report.dry_run:
                db.session.execute(
                    text(f"DELETE FROM {table} WHERE contract_id NOT IN (:a, :g)"),
                    {"a": ariston_id, "g": gauff_id},
                )


def _purge_reference_except(ariston_id: int, gauff_id: int, report: CleanupReport) -> None:
    keep = {ariston_id, gauff_id}
    t_count = TariffRule.query.count()
    report.log(f"Удалить все ставки ({t_count})")
    if not report.dry_run:
        TariffRule.query.delete()

    a_count = ContractAmendment.query.count()
    report.log(f"Удалить все ДС ({a_count})")
    if not report.dry_run:
        ContractAmendment.query.delete()

    for row in Contract.query.filter(Contract.id.notin_(keep)).all():
        report.log(f"Удалить договор id={row.id} «{row.number}»")
        if not report.dry_run:
            db.session.delete(row)

    keep_client_ids = {
        c.client_id for c in Contract.query.filter(Contract.id.in_(keep)).all()
    }
    for cl in Client.query.filter(Client.id.notin_(keep_client_ids)).all():
        report.log(f"Удалить клиента id={cl.id} «{cl.name}»")
        if not report.dry_run:
            db.session.delete(cl)


def _store_docx_copy(src: Path, amendment_id: int) -> str | None:
    upload_root = Path(current_app.config.get("UPLOAD_FOLDER", "uploads"))
    dest_dir = upload_root / "amendments"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"amendment_{amendment_id}_{src.name}"
    shutil.copy2(src, dest)
    return str(dest)


def _create_amendments_for_contract(
    contract: Contract,
    parsed_list: list[tuple[Path, ParsedAmendment]],
    report: CleanupReport,
) -> None:
    ordered = sorted(parsed_list, key=lambda x: x[1].effective_from or date.min)
    for idx, (path, parsed) in enumerate(ordered):
        eff_from = parsed.effective_from
        if not eff_from:
            report.log(f"Пропуск ДС без даты: {path.name}")
            continue
        next_from = ordered[idx + 1][1].effective_from if idx + 1 < len(ordered) else None
        eff_to = _compute_effective_to(eff_from, next_from)
        is_last = idx == len(ordered) - 1
        status = "active" if is_last else "superseded"

        report.log(
            f"ДС {parsed.number}: {eff_from} — {eff_to} ({status}), ставок {len(parsed.tariffs)}"
        )
        if report.dry_run:
            continue

        amendment = ContractAmendment(
            contract_id=contract.id,
            number=parsed.number or path.stem,
            status=status,
            effective_from=eff_from,
            effective_to=eff_to,
        )
        db.session.add(amendment)
        db.session.flush()
        amendment.source_file_path = _store_docx_copy(path, amendment.id)

        parsed.effective_to = eff_to
        apply_parsed_to_amendment(amendment, parsed, replace_tariffs=True)

        for rule in TariffRule.query.filter_by(amendment_id=amendment.id).all():
            rule.valid_from = eff_from
            rule.valid_to = eff_to


def cleanup_reference_real(
    *,
    dry_run: bool = False,
    force: bool = False,
    docx_dir: Path | None = None,
    skip_backup: bool = False,
) -> CleanupReport:
    report = CleanupReport(dry_run=dry_run)

    if current_app.config.get("PLS_FREEZE_REFERENCE") and not force:
        report.log(
            "Пропуск: PLS_FREEZE_REFERENCE=1. Запустите с --force."
        )
        return report

    if not dry_run and not skip_backup:
        try:
            path, size = create_backup()
            report.log(f"Бэкап: {path} ({size} байт)")
        except BackupError as exc:
            report.log(f"ОШИБКА бэкапа: {exc}")
            return report

    report.log("Старт cleanup-reference-real")

    wh = Warehouse.query.filter_by(code="strelna").first()
    if not wh:
        report.log("Склад strelna не найден")
        return report
    pt = ProductType.query.filter_by(code="RESPONSIBLE_STORAGE").first()
    if not pt:
        report.log("Тип RESPONSIBLE_STORAGE не найден")
        return report

    ariston_paths = [
        _resolve_docx(None, name, docx_dir) for name in ARISTON_AMENDMENT_FILES
    ]
    gauff_path = _resolve_docx(None, GAUFF_AMENDMENT_FILE, docx_dir)

    ariston_parsed = [(p, _load_parsed(p, ariston=True)) for p in ariston_paths]
    gauff_parsed = [(gauff_path, _load_parsed(gauff_path, ariston=False))]

    latest_ariston = ariston_parsed[-1][1]
    ariston_billing = _billing_config_from_parameters(latest_ariston)

    ariston_client = _pick_or_create_client(CANONICAL_ARISTON_CLIENT, report)
    gauff_client = _pick_or_create_client(CANONICAL_GAUFF_CLIENT, report)
    if not report.dry_run:
        db.session.flush()

    ariston_contract = _pick_or_create_contract(
        client=ariston_client,
        number=CANONICAL_ARISTON_CONTRACT,
        warehouse_id=wh.id,
        product_type_id=pt.id,
        billing_config=ariston_billing,
        report=report,
    )
    gauff_contract = _pick_or_create_contract(
        client=gauff_client,
        number=CANONICAL_GAUFF_CONTRACT,
        warehouse_id=wh.id,
        product_type_id=pt.id,
        billing_config=_billing_config_from_parameters(gauff_parsed[0][1]) or {"area_mode": "simple"},
        report=report,
    )
    if not report.dry_run:
        db.session.flush()

    _remap_operations(ariston_contract.id, gauff_contract.id, report)
    _purge_reference_except(ariston_contract.id, gauff_contract.id, report)

    _create_amendments_for_contract(ariston_contract, ariston_parsed, report)
    _create_amendments_for_contract(gauff_contract, gauff_parsed, report)

    if not report.dry_run:
        db.session.commit()
    else:
        db.session.rollback()

    report.log("Готово")
    return report
