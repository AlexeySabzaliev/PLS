"""Наполнение БД: справочники, роли, демо-контракт."""
from __future__ import annotations

import os
from datetime import date, datetime
from decimal import Decimal

from app.core.auth import hash_password
from app.core.permissions import REFERENCE_SECTIONS, REQUEST_SECTIONS, USS_SECTIONS
from app.db import db
from app.modules.processes.schema_resolver import ProcessLine, ProcessLineConfig
from app.modules.processes.templates import EXAMPLE_LINE_CONFIGS
from app.modules.reference.models import (
    Client,
    Contract,
    ContractAmendment,
    ProductType,
    Role,
    SectionPermission,
    TariffRule,
    UnitOfMeasure,
    User,
    UserRole,
    UserWarehouseAccess,
    Warehouse,
)
from app.modules.uss.models import OperationDailyTotal, VehicleOperation
from app.seeds.ariston_tariffs import ensure_ariston_tariffs

PRODUCT_TYPES = [
    ("RESPONSIBLE_STORAGE", "Ответственное хранение"),
    ("SUBLEASE", "Субаренда"),
    ("RENT", "Аренда"),
]

UNITS = [
    ("m2", "м²"),
    ("m2day", "м²·день"),
    ("m3", "м³"),
    ("pcs", "шт."),
    ("vehicle", "машина"),
    ("hour", "час"),
]

WAREHOUSES = [
    ("sofino", "Софьино"),
    ("strelna", "Стрельна"),
    ("spb1", "СПб-1"),
]

ROLE_DEFINITIONS = [
    ("admin", "Администратор"),
    ("supervisor", "Руководитель смены"),
    ("transport_logistics", "Транспортная логистика"),
    ("warehouse_logistics", "Складская логистика"),
    ("inventory_management", "Управление запасами"),
    ("commercial_logistics", "Коммерческая логистика"),
]


def _all_section_permissions() -> dict[str, set[str]]:
    merged: dict[str, set[str]] = {}
    for matrix in (USS_SECTIONS, REFERENCE_SECTIONS, REQUEST_SECTIONS):
        for role_code, sections in matrix.items():
            merged.setdefault(role_code, set()).update(sections)
    return merged


def seed_reference(*, verbose: bool = False) -> dict:
    """Справочники, роли, права разделов."""
    stats = {
        "product_types": 0,
        "units": 0,
        "warehouses": 0,
        "roles": 0,
        "section_permissions": 0,
    }

    for code, name in PRODUCT_TYPES:
        if not ProductType.query.filter_by(code=code).first():
            db.session.add(ProductType(code=code, name=name))
            stats["product_types"] += 1

    for code, name in UNITS:
        if not UnitOfMeasure.query.filter_by(code=code).first():
            db.session.add(UnitOfMeasure(code=code, name=name))
            stats["units"] += 1

    for code, name in WAREHOUSES:
        if not Warehouse.query.filter_by(code=code).first():
            db.session.add(Warehouse(code=code, name=name, is_active=True))
            stats["warehouses"] += 1

    role_by_code: dict[str, Role] = {r.code: r for r in Role.query.all()}
    for code, name in ROLE_DEFINITIONS:
        if code not in role_by_code:
            row = Role(code=code, name=name)
            db.session.add(row)
            role_by_code[code] = row
            stats["roles"] += 1

    db.session.flush()
    role_by_code = {r.code: r for r in Role.query.all()}

    for role_code, sections in _all_section_permissions().items():
        role = role_by_code.get(role_code)
        if not role:
            continue
        for section in sections:
            exists = SectionPermission.query.filter_by(
                role_id=role.id, section_code=section
            ).first()
            if not exists:
                db.session.add(SectionPermission(role_id=role.id, section_code=section))
                stats["section_permissions"] += 1

    db.session.commit()
    if verbose:
        print(f"seed-reference: {stats}")
    return stats


def seed_admin(*, verbose: bool = False) -> dict:
    """Администратор и демо-пользователь транспорта."""
    seed_reference(verbose=False)
    stats = {"admin": 0, "transport_user": 0}

    admin_email = os.getenv("PLS_ADMIN_EMAIL", "admin@bsh-ru.ru").strip().lower()
    admin_password = os.getenv("PLS_ADMIN_PASSWORD", "admin")
    transport_email = os.getenv("PLS_TRANSPORT_EMAIL", "transport@bsh-ru.ru").strip().lower()

    admin = User.query.filter_by(email=admin_email).first()
    if not admin:
        admin = User(
            email=admin_email,
            full_name="Администратор ПЛС",
            password_hash=hash_password(admin_password),
            is_active=True,
            is_admin=True,
        )
        db.session.add(admin)
        stats["admin"] = 1
    else:
        admin.is_admin = True
        admin.is_active = True
        if admin_password and not admin.password_hash:
            admin.password_hash = hash_password(admin_password)

    transport = User.query.filter_by(email=transport_email).first()
    if not transport:
        transport = User(
            email=transport_email,
            full_name="Транспортная логистика",
            password_hash=hash_password(os.getenv("PLS_TRANSPORT_PASSWORD", "transport")),
            is_active=True,
        )
        db.session.add(transport)
        stats["transport_user"] = 1

    db.session.flush()

    roles = {r.code: r for r in Role.query.all()}
    if admin and roles.get("admin"):
        if not UserRole.query.filter_by(user_id=admin.id, role_id=roles["admin"].id).first():
            db.session.add(UserRole(user_id=admin.id, role_id=roles["admin"].id))

    wh = Warehouse.query.filter_by(code="sofino").first() or Warehouse.query.first()
    if transport and roles.get("transport_logistics"):
        if not UserRole.query.filter_by(
            user_id=transport.id, role_id=roles["transport_logistics"].id
        ).first():
            db.session.add(UserRole(user_id=transport.id, role_id=roles["transport_logistics"].id))
        if wh and not UserWarehouseAccess.query.filter_by(
            user_id=transport.id, warehouse_id=wh.id
        ).first():
            db.session.add(UserWarehouseAccess(user_id=transport.id, warehouse_id=wh.id))

    db.session.commit()
    if verbose:
        print(f"seed-admin: {stats} (admin={admin_email})")
    return stats


def seed_demo(*, verbose: bool = False) -> dict:
    """Демо: клиент Аристон, договор, линии процессов, ТС и суточный итог."""
    seed_admin(verbose=False)
    stats = {
        "client": 0,
        "contract": 0,
        "amendment": 0,
        "tariff": 0,
        "process_lines": 0,
        "vehicle": 0,
        "daily_total": 0,
    }

    wh = Warehouse.query.filter_by(code="sofino").first()
    pt = ProductType.query.filter_by(code="RESPONSIBLE_STORAGE").first()
    unit_pcs = UnitOfMeasure.query.filter_by(code="pcs").first()
    unit_hour = UnitOfMeasure.query.filter_by(code="hour").first()
    if not wh or not pt:
        if verbose:
            print("seed-demo: пропуск — нет склада или типа продукта")
        return stats

    client = Client.query.filter_by(name="Аристон").first()
    if not client:
        client = Client(name="Аристон", is_active=True)
        db.session.add(client)
        db.session.flush()
        stats["client"] = 1

    contract = Contract.query.filter_by(number="ДЕМО-АРИСТОН-1").first()
    if not contract:
        contract = Contract(
            client_id=client.id,
            warehouse_id=wh.id,
            product_type_id=pt.id,
            number="ДЕМО-АРИСТОН-1",
            status="active",
        )
        db.session.add(contract)
        db.session.flush()
        stats["contract"] = 1

    am = ContractAmendment.query.filter_by(contract_id=contract.id, number="ДС-1").first()
    if not am:
        am = ContractAmendment(
            contract_id=contract.id,
            number="ДС-1",
            status="active",
            effective_from=date(2026, 1, 1),
        )
        db.session.add(am)
        db.session.flush()
        stats["amendment"] = 1

    added_tariffs = ensure_ariston_tariffs(contract.id, am.id, valid_from=date(2026, 1, 1))
    stats["tariff"] += added_tariffs

    for line_code, base_process, line_name in (
        ("ariston_standard", "warehouse_logistics", "Аристон стандарт"),
        ("gazprom_logistics", "transport_logistics", "Газпром логистика"),
    ):
        line = ProcessLine.query.filter_by(code=line_code).first()
        if not line:
            line = ProcessLine(
                code=line_code,
                name=line_name,
                base_process=base_process,
                client_id=client.id if line_code == "ariston_standard" else None,
                is_active=True,
            )
            db.session.add(line)
            db.session.flush()
            stats["process_lines"] += 1
        cfg = line.config
        if not cfg and line_code in EXAMPLE_LINE_CONFIGS:
            db.session.add(
                ProcessLineConfig(
                    process_line_id=line.id,
                    config_json=EXAMPLE_LINE_CONFIGS[line_code],
                )
            )

    demo_date = date(2026, 8, 15)
    if not VehicleOperation.query.filter_by(
        contract_id=contract.id, operation_date=demo_date, plate_number="А123ВС78"
    ).first():
        db.session.add(
            VehicleOperation(
                contract_id=contract.id,
                warehouse_id=wh.id,
                operation_date=demo_date,
                plate_number="А123ВС78",
                volume_document_m3=Decimal("32.5"),
                handling_type_code="manual",
                registered_at=datetime(2026, 8, 15, 9, 0),
                departed_at=datetime(2026, 8, 15, 11, 30),
            )
        )
        stats["vehicle"] = 1

    if not OperationDailyTotal.query.filter_by(
        contract_id=contract.id,
        report_date=demo_date,
        billing_line_code="valve_gluing",
    ).first():
        db.session.add(
            OperationDailyTotal(
                contract_id=contract.id,
                warehouse_id=wh.id,
                report_date=demo_date,
                billing_line_code="valve_gluing",
                quantity=Decimal("120"),
            )
        )
        stats["daily_total"] = 1

    db.session.commit()
    if verbose:
        print(f"seed-demo: {stats}")
    return stats


def seed_test_fixtures() -> None:
    """Минимальный набор для pytest (in-memory SQLite)."""
    wh = Warehouse(code="spb1", name="СПб-1", is_active=True)
    pt = ProductType(code="RESPONSIBLE_STORAGE", name="Ответственное хранение")
    client = Client(name="Аристон", is_active=True)
    db.session.add_all([wh, pt, client])
    db.session.flush()

    contract = Contract(
        client_id=client.id,
        warehouse_id=wh.id,
        product_type_id=pt.id,
        number="Д-001",
        status="active",
    )
    db.session.add(contract)
    db.session.flush()

    am = ContractAmendment(
        contract_id=contract.id,
        number="ДС-1",
        status="active",
        effective_from=date(2025, 1, 1),
    )
    unit = UnitOfMeasure(code="pcs", name="шт")
    units_extra = [
        UnitOfMeasure(code="vehicle", name="машина"),
        UnitOfMeasure(code="hour", name="час"),
        UnitOfMeasure(code="m2day", name="м²·день"),
    ]
    db.session.add_all([am, unit, *units_extra])
    db.session.flush()

    db.session.add(
        TariffRule(
            contract_id=contract.id,
            amendment_id=am.id,
            billing_line_code="valve_gluing",
            name="Подклейка клапанов",
            unit_id=unit.id,
            report_role="warehouse_logistics",
            quantity_source="manual_daily",
            rate_line_code="repack_units",
            quantity_divisor=1,
            valid_from=date(2025, 1, 1),
        )
    )
    ensure_ariston_tariffs(contract.id, am.id, valid_from=date(2025, 1, 1))

    for code, name in [
        ("admin", "Администратор"),
        ("transport_logistics", "Транспортная логистика"),
    ]:
        db.session.add(Role(code=code, name=name))
    db.session.flush()

    admin = User(
        email="admin@test.local",
        full_name="Админ",
        password_hash=hash_password("admin"),
        is_active=True,
        is_admin=True,
    )
    transport = User(
        email="transport@test.local",
        full_name="Транспорт",
        password_hash=hash_password("test"),
        is_active=True,
    )
    db.session.add_all([admin, transport])
    db.session.flush()

    roles = {r.code: r for r in Role.query.all()}
    db.session.add(UserRole(user_id=admin.id, role_id=roles["admin"].id))
    db.session.add(UserRole(user_id=transport.id, role_id=roles["transport_logistics"].id))
    db.session.add(UserWarehouseAccess(user_id=transport.id, warehouse_id=wh.id))

    line_wh = ProcessLine(
        code="ariston_standard",
        name="Аристон стандарт",
        base_process="warehouse_logistics",
        client_id=client.id,
    )
    line_tr = ProcessLine(
        code="gazprom_logistics",
        name="Газпром логистика",
        base_process="transport_logistics",
    )
    db.session.add_all([line_wh, line_tr])
    db.session.flush()
    db.session.add(
        ProcessLineConfig(
            process_line_id=line_wh.id,
            config_json=EXAMPLE_LINE_CONFIGS["ariston_standard"],
        )
    )
    db.session.add(
        ProcessLineConfig(
            process_line_id=line_tr.id,
            config_json=EXAMPLE_LINE_CONFIGS["gazprom_logistics"],
        )
    )
    db.session.commit()
