"""Идемпотентная правка канонических данных Аристон / Стрельна."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import update

from app.db import db
from app.modules.billing.models import BillingPeriod
from app.modules.processes.schema_resolver import ProcessLine
from app.modules.reference.client_names import CANONICAL_ARISTON_CLIENT, normalize_client_name
from app.modules.reference.models import (
    Client,
    Contract,
    ContractAmendment,
    ProductType,
    TariffRule,
    UnitOfMeasure,
    UserWarehouseAccess,
    Warehouse,
)
from app.modules.uss.models import (
    OperationDailyTotal,
    ShiftDayConfirmation,
    ShiftReport,
    VehicleOperation,
    WarehouseStaffPosition,
    WarehouseStaffPositionVersion,
)
from app.modules.uss.services.tariff_codes import formula_for_code
from app.seeds.ariston_tariffs import (
    ARISTON_DS6_EXTRA_CODES,
    ARISTON_TARIFF_SPECS,
    AristonTariffSpec,
    ariston_spec_by_code,
)

CANONICAL_CLIENT_NAME = CANONICAL_ARISTON_CLIENT
WRONG_CLIENT_NAMES = frozenset({"Аристон"})
CANONICAL_WH_CODE = "strelna"
WRONG_WH_CODE = "spb1"
CANONICAL_CONTRACT_NUMBER = "АР-БСХ 24"
WRONG_CONTRACT_NUMBER = "STR-OH-ARISTON"
CANONICAL_DS_NUMBER = "ДС-6/2024"
DUPLICATE_DS6_NUMBER = "ДС-6"
WRONG_DS_NUMBER = "ДС-01/2025"
HISTORICAL_DS_NUMBER = "ДС-5"
HISTORICAL_DS_FROM = date(2025, 5, 1)
HISTORICAL_DS_TO = date(2026, 7, 31)
CANONICAL_DS_FROM = date(2026, 8, 1)

BILLING_CONFIG = {"area_mode": "two_tier", "fixed_m2days": 9435}

# 8 основных ставок ДС-6/2024 (без доп. is_custom)
DS6_CORE_CODES = frozenset({
    "storage_area_fixed",
    "storage_area_extra",
    "manual_m3",
    "mechanized_m3",
    "vehicle_docs",
    "repack_units",
    "overtime_m3",
    "inventory_hours",
})

DS6_EXTRA_CODES = ARISTON_DS6_EXTRA_CODES

# Канонический набор ставок ДС-6/2024
CANONICAL_DS6_TARIFF_CODES = DS6_CORE_CODES | DS6_EXTRA_CODES

REDUNDANT_DS6_CODES = frozenset()


@dataclass
class FixReport:
    dry_run: bool = False
    actions: list[str] = field(default_factory=list)

    def log(self, msg: str) -> None:
        prefix = "[dry-run] " if self.dry_run else ""
        self.actions.append(f"{prefix}{msg}")


def _spec_by_code(code: str) -> AristonTariffSpec | None:
    return ariston_spec_by_code(code)


def _rate_for_code(code: str, *, extra_area_rate: str) -> str:
    if code == "storage_area_extra":
        return extra_area_rate
    spec = _spec_by_code(code)
    if spec and spec.rate_ex_vat:
        return spec.rate_ex_vat
    from app.seeds.ariston_tariffs import ARISTON_RATE_EX_VAT

    return ARISTON_RATE_EX_VAT.get(code, "0")


def _ensure_client(report: FixReport) -> Client:
    canonical = Client.query.filter(Client.name == CANONICAL_CLIENT_NAME).first()
    if not canonical:
        canonical = Client(name=CANONICAL_CLIENT_NAME, is_active=True)
        db.session.add(canonical)
        db.session.flush()
        report.log(f"Создан клиент: {CANONICAL_CLIENT_NAME} (id={canonical.id})")
    elif not canonical.is_active:
        canonical.is_active = True
        report.log(f"Активирован клиент id={canonical.id}")

    for wrong_name in WRONG_CLIENT_NAMES:
        wrong = Client.query.filter_by(name=wrong_name, is_active=True).first()
        if not wrong or wrong.id == canonical.id:
            continue
        for model, field in (
            (Contract, "client_id"),
            (ProcessLine, "client_id"),
        ):
            count = model.query.filter_by(**{field: wrong.id}).count()
            if count:
                if not report.dry_run:
                    db.session.execute(
                        update(model).where(getattr(model, field) == wrong.id).values(**{field: canonical.id})
                    )
                report.log(f"Перенесено {count} {model.__tablename__}.{field}: {wrong.id} -> {canonical.id}")
        if not report.dry_run:
            remaining = Contract.query.filter_by(client_id=wrong.id).count()
            if remaining == 0:
                db.session.delete(wrong)
                report.log(f"Удалён ошибочный клиент «{wrong_name}» id={wrong.id}")
            else:
                wrong.is_active = False
                report.log(f"Деактивирован дубль клиента «{wrong_name}» id={wrong.id} (остались договоры: {remaining})")
        else:
            report.log(f"Удалить/деактивировать дубль клиента «{wrong_name}» id={wrong.id}")
    return canonical


def _ensure_warehouse(report: FixReport) -> Warehouse:
    canonical = Warehouse.query.filter_by(code=CANONICAL_WH_CODE).first()
    if not canonical:
        canonical = Warehouse(code=CANONICAL_WH_CODE, name="Стрельна", is_active=True)
        db.session.add(canonical)
        db.session.flush()
        report.log(f"Создан склад {CANONICAL_WH_CODE} id={canonical.id}")

    wrong = Warehouse.query.filter_by(code=WRONG_WH_CODE).first()
    if wrong and wrong.id != canonical.id:
        for model in (
            Contract,
            UserWarehouseAccess,
            WarehouseStaffPosition,
            WarehouseStaffPositionVersion,
            VehicleOperation,
            OperationDailyTotal,
            ShiftReport,
            ShiftDayConfirmation,
        ):
            count = model.query.filter_by(warehouse_id=wrong.id).count()
            if count:
                if not report.dry_run:
                    db.session.execute(
                        update(model).where(model.warehouse_id == wrong.id).values(warehouse_id=canonical.id)
                    )
                report.log(f"Перенесено {count} {model.__tablename__}.warehouse_id: {wrong.id} -> {canonical.id}")
        if not report.dry_run:
            wrong.is_active = False
        report.log(f"Деактивирован склад {WRONG_WH_CODE} id={wrong.id}")
    return canonical




def _delete_amendment_tree(report: FixReport, amd: ContractAmendment) -> None:
    if not report.dry_run:
        TariffRule.query.filter_by(amendment_id=amd.id).delete(synchronize_session=False)
        db.session.delete(amd)
    report.log(f"Удалено ошибочное ДС id={amd.id} №{amd.number}")


def _remove_wrong_contract(report: FixReport, wrong: Contract, canonical_contract: Contract) -> None:
    _reassign_operation_daily_totals(
        report,
        from_contract_id=wrong.id,
        to_contract_id=canonical_contract.id,
    )
    for model in (VehicleOperation, BillingPeriod):
        count = model.query.filter_by(contract_id=wrong.id).count()
        if count:
            if not report.dry_run:
                db.session.execute(
                    update(model).where(model.contract_id == wrong.id).values(contract_id=canonical_contract.id)
                )
            report.log(
                f"Перенесено {count} {model.__tablename__}.contract_id: {wrong.id} -> {canonical_contract.id}"
            )
    for amd in ContractAmendment.query.filter_by(contract_id=wrong.id).all():
        _delete_amendment_tree(report, amd)
    if not report.dry_run:
        TariffRule.query.filter_by(contract_id=wrong.id).delete(synchronize_session=False)
        db.session.delete(wrong)
    report.log(f"Удалён ошибочный договор {wrong.number} id={wrong.id}")


def purge_legacy_ariston_seed_data(
    *,
    dry_run: bool = False,
    canonical_contract: Contract | None = None,
) -> FixReport:
    """Удалить ошибочные сиды: клиент «Аристон», STR-OH-ARISTON, ДС-01/2025."""
    report = FixReport(dry_run=dry_run)
    if canonical_contract is None:
        canonical_contract = Contract.query.filter(
            Contract.number.ilike(f"%{CANONICAL_CONTRACT_NUMBER}%")
        ).first()

    for wrong in list(Contract.query.filter_by(number=WRONG_CONTRACT_NUMBER).all()):
        if canonical_contract and wrong.id != canonical_contract.id:
            _remove_wrong_contract(report, wrong, canonical_contract)
        elif not canonical_contract:
            for amd in ContractAmendment.query.filter_by(contract_id=wrong.id).all():
                _delete_amendment_tree(report, amd)
            if not report.dry_run:
                TariffRule.query.filter_by(contract_id=wrong.id).delete(synchronize_session=False)
                db.session.delete(wrong)
            report.log(f"Удалён ошибочный договор {wrong.number} id={wrong.id}")

    for amd in list(ContractAmendment.query.filter_by(number=WRONG_DS_NUMBER).all()):
        _delete_amendment_tree(report, amd)

    canonical_client = Client.query.filter_by(name=CANONICAL_CLIENT_NAME).first()
    for wrong_name in WRONG_CLIENT_NAMES:
        for cl in Client.query.filter_by(name=wrong_name).all():
            if canonical_client and cl.id == canonical_client.id:
                continue
            if Contract.query.filter_by(client_id=cl.id).first():
                continue
            if not report.dry_run:
                db.session.delete(cl)
            report.log(f"Удалён ошибочный клиент «{wrong_name}» id={cl.id}")

    if not dry_run:
        db.session.commit()
    else:
        db.session.rollback()
    return report


def _reassign_operation_daily_totals(
    report: FixReport,
    *,
    from_contract_id: int,
    to_contract_id: int,
) -> None:
    """Перенос daily totals без нарушения uq (contract, date, code)."""
    rows = OperationDailyTotal.query.filter_by(contract_id=from_contract_id).all()
    if not rows:
        return
    moved = 0
    merged = 0
    for row in rows:
        existing = OperationDailyTotal.query.filter_by(
            contract_id=to_contract_id,
            report_date=row.report_date,
            billing_line_code=row.billing_line_code,
        ).first()
        if existing:
            if not report.dry_run:
                existing.quantity = (existing.quantity or 0) + (row.quantity or 0)
                db.session.delete(row)
            merged += 1
        else:
            if not report.dry_run:
                row.contract_id = to_contract_id
            moved += 1
    report.log(
        "Перенесено operation_daily_totals: %s строк, объединено %s дубликатов (%s -> %s)"
        % (moved, merged, from_contract_id, to_contract_id)
    )

def _ensure_contract(report: FixReport, client: Client, warehouse: Warehouse) -> Contract:
    pt = ProductType.query.filter_by(code="RESPONSIBLE_STORAGE").first()
    if not pt:
        raise RuntimeError("Нет product_type RESPONSIBLE_STORAGE")

    contract = Contract.query.filter(
        Contract.number.ilike(f"%{CANONICAL_CONTRACT_NUMBER}%"),
        Contract.warehouse_id == warehouse.id,
    ).first()
    if not contract:
        contract = Contract(
            client_id=client.id,
            warehouse_id=warehouse.id,
            product_type_id=pt.id,
            number=CANONICAL_CONTRACT_NUMBER,
            status="active",
            billing_config=BILLING_CONFIG,
        )
        db.session.add(contract)
        db.session.flush()
        report.log(f"Создан договор {CANONICAL_CONTRACT_NUMBER} id={contract.id}")
    else:
        if contract.client_id != client.id:
            if not report.dry_run:
                contract.client_id = client.id
            report.log(f"Договор id={contract.id}: client_id -> {client.id}")
        if contract.status != "active":
            if not report.dry_run:
                contract.status = "active"
            report.log(f"Договор id={contract.id}: status -> active")
        if not report.dry_run:
            contract.billing_config = BILLING_CONFIG

    wrong = Contract.query.filter_by(number=WRONG_CONTRACT_NUMBER).first()
    if wrong and wrong.id != contract.id:
        _remove_wrong_contract(report, wrong, contract)
    return contract


def _upsert_amendment(
    report: FixReport,
    *,
    contract: Contract,
    number: str,
    effective_from: date,
    effective_to: date | None,
    status: str,
) -> ContractAmendment:
    amd = ContractAmendment.query.filter_by(contract_id=contract.id, number=number).first()
    if not amd:
        amd = ContractAmendment(
            contract_id=contract.id,
            number=number,
            status=status,
            effective_from=effective_from,
            effective_to=effective_to,
        )
        db.session.add(amd)
        db.session.flush()
        report.log(f"Создано ДС №{number} id={amd.id} с {effective_from}")
    else:
        changed = False
        if amd.effective_from != effective_from:
            if not report.dry_run:
                amd.effective_from = effective_from
            changed = True
        if amd.effective_to != effective_to:
            if not report.dry_run:
                amd.effective_to = effective_to
            changed = True
        if amd.status != status:
            if not report.dry_run:
                amd.status = status
            changed = True
        if changed:
            report.log(f"Обновлено ДС №{number} id={amd.id}")
    return amd


def _ensure_tariffs(
    report: FixReport,
    *,
    contract: Contract,
    amendment: ContractAmendment,
    codes: frozenset[str],
    valid_from: date,
    valid_to: date | None,
    extra_area_rate: str,
) -> int:
    units = {u.code: u for u in UnitOfMeasure.query.all()}
    touched = 0
    for code in codes:
        spec = _spec_by_code(code)
        if not spec:
            continue
        rate = _rate_for_code(code, extra_area_rate=extra_area_rate)
        unit = units.get(spec.unit_code)
        row = TariffRule.query.filter_by(
            contract_id=contract.id,
            amendment_id=amendment.id,
            billing_line_code=code,
        ).first()
        is_custom = code in DS6_EXTRA_CODES
        if not row:
            if report.dry_run:
                report.log(f"  + ставка {code} ({rate}) is_custom={is_custom}")
                touched += 1
                continue
            row = TariffRule(
                contract_id=contract.id,
                amendment_id=amendment.id,
                billing_line_code=code,
                name=spec.name,
                unit_id=unit.id if unit else None,
                report_role=spec.report_role,
                report_scope=spec.report_scope,
                quantity_source=spec.quantity_source,
                rate_line_code=spec.rate_line_code,
                quantity_divisor=spec.quantity_divisor,
                is_custom=is_custom,
                sort_order=spec.sort_order,
                valid_from=valid_from,
                valid_to=valid_to,
                rate_ex_vat=Decimal(rate),
                formula=formula_for_code(code),
            )
            db.session.add(row)
            touched += 1
            report.log(f"  + ставка {code} rate={rate} is_custom={is_custom}")
        else:
            updates = []
            if row.is_custom != is_custom:
                if not report.dry_run:
                    row.is_custom = is_custom
                updates.append(f"is_custom={is_custom}")
            expected_rate = Decimal(rate)
            if row.rate_ex_vat != expected_rate:
                if not report.dry_run:
                    row.rate_ex_vat = expected_rate
                updates.append(f"rate={rate}")
            if row.valid_from != valid_from:
                if not report.dry_run:
                    row.valid_from = valid_from
                updates.append(f"valid_from={valid_from}")
            if row.valid_to != valid_to:
                if not report.dry_run:
                    row.valid_to = valid_to
                updates.append(f"valid_to={valid_to}")
            if row.amendment_id != amendment.id:
                if not report.dry_run:
                    row.amendment_id = amendment.id
                updates.append(f"amendment_id={amendment.id}")
            if spec.name and row.name != spec.name:
                if not report.dry_run:
                    row.name = spec.name
                updates.append("name")
            if row.report_role != spec.report_role:
                if not report.dry_run:
                    row.report_role = spec.report_role
                updates.append(f"report_role={spec.report_role}")
            if row.report_scope != spec.report_scope:
                if not report.dry_run:
                    row.report_scope = spec.report_scope
                updates.append(f"report_scope={spec.report_scope}")
            if row.quantity_source != spec.quantity_source:
                if not report.dry_run:
                    row.quantity_source = spec.quantity_source
                updates.append(f"quantity_source={spec.quantity_source}")
            if row.rate_line_code != spec.rate_line_code:
                if not report.dry_run:
                    row.rate_line_code = spec.rate_line_code
                updates.append(f"rate_line_code={spec.rate_line_code}")
            expected_divisor = Decimal(spec.quantity_divisor)
            if row.quantity_divisor != expected_divisor:
                if not report.dry_run:
                    row.quantity_divisor = expected_divisor
                updates.append(f"quantity_divisor={spec.quantity_divisor}")
            if updates:
                report.log(f"  ~ ставка {code}: {', '.join(updates)}")
                touched += 1
    return touched


def _supersede_duplicate_ds6(report: FixReport, contract: Contract, canonical: ContractAmendment) -> None:
    """Убрать дубль «ДС-6» без /2024 — ставки не переносим, канон в ДС-6/2024."""
    dupes = ContractAmendment.query.filter(
        ContractAmendment.contract_id == contract.id,
        ContractAmendment.number == DUPLICATE_DS6_NUMBER,
    ).all()
    for amd in dupes:
        if amd.id == canonical.id:
            continue
        count = TariffRule.query.filter_by(amendment_id=amd.id).count()
        if count and not report.dry_run:
            TariffRule.query.filter_by(amendment_id=amd.id).delete(synchronize_session=False)
        if not report.dry_run:
            amd.status = "superseded"
            amd.effective_to = amd.effective_to or (canonical.effective_from or CANONICAL_DS_FROM)
        report.log(f"Отключён дубль {DUPLICATE_DS6_NUMBER} id={amd.id} ({count} ставок удалено)")


def _trim_canonical_tariffs(report: FixReport, contract: Contract, amendment: ContractAmendment) -> None:
    """Оставить только канонические коды; убрать legacy extra_vehicle_docs и прочие лишние."""
    rows = TariffRule.query.filter_by(contract_id=contract.id, amendment_id=amendment.id).all()
    removed = 0
    for row in rows:
        drop = False
        if row.billing_line_code in REDUNDANT_DS6_CODES:
            drop = True
        elif row.billing_line_code not in CANONICAL_DS6_TARIFF_CODES:
            drop = True
        if drop:
            if not report.dry_run:
                db.session.delete(row)
            removed += 1
            report.log(f"  − лишняя ставка {row.billing_line_code} (ДС id={amendment.id})")
    if removed:
        report.log(f"ДС-6/2024: удалено {removed} лишних ставок")


def fix_ariston_canonical(*, dry_run: bool = False, with_ds5: bool = True, force: bool = False) -> FixReport:
    """Привести справочники Аристон к каноническому виду."""
    from flask import current_app

    report = FixReport(dry_run=dry_run)
    if current_app.config.get("PLS_FREEZE_REFERENCE") and not force:
        report.log(
            "Пропуск: PLS_FREEZE_REFERENCE=1 — справочники заморожены. "
            "Повторите с --force для принудительной правки."
        )
        return report
    report.log("Старт fix-ariston-canonical")

    client = _ensure_client(report)
    warehouse = _ensure_warehouse(report)
    contract = _ensure_contract(report, client, warehouse)

    if with_ds5:
        ds5 = _upsert_amendment(
            report,
            contract=contract,
            number=HISTORICAL_DS_NUMBER,
            effective_from=HISTORICAL_DS_FROM,
            effective_to=HISTORICAL_DS_TO,
            status="superseded",
        )
        n5 = _ensure_tariffs(
            report,
            contract=contract,
            amendment=ds5,
            codes=DS6_CORE_CODES,
            valid_from=HISTORICAL_DS_FROM,
            valid_to=HISTORICAL_DS_TO,
            extra_area_rate="19.71",
        )
        report.log(f"ДС-5: {n5} ставок (extra_area=19.71)")

    ds6 = _upsert_amendment(
        report,
        contract=contract,
        number=CANONICAL_DS_NUMBER,
        effective_from=CANONICAL_DS_FROM,
        effective_to=None,
        status="active",
    )
    n6 = _ensure_tariffs(
        report,
        contract=contract,
        amendment=ds6,
        codes=CANONICAL_DS6_TARIFF_CODES,
        valid_from=CANONICAL_DS_FROM,
        valid_to=None,
        extra_area_rate="24",
    )
    report.log(f"ДС-6/2024: {n6} ставок (extra_area=24)")
    _supersede_duplicate_ds6(report, contract, ds6)
    _trim_canonical_tariffs(report, contract, ds6)
    purge_legacy_ariston_seed_data(dry_run=dry_run, canonical_contract=contract)

    if not dry_run:
        db.session.commit()
    else:
        db.session.rollback()

    report.log(
        f"Готово. Канон: client={client.id}, wh={warehouse.code}, "
        f"contract={contract.number} (id={contract.id}), ДС-6 id={ds6.id}"
    )
    return report


def client_name_collides(name: str, exclude_id: int | None = None) -> bool:
    """Проверка дубля по нормализованному имени (для API)."""
    target = normalize_client_name(name)
    q = Client.query.filter_by(is_active=True)
    for row in q.all():
        if exclude_id and row.id == exclude_id:
            continue
        if normalize_client_name(row.name) == target:
            return True
    return False
