"""Наполнение БД: справочники, роли, демо-контракт."""
from __future__ import annotations

import os
from datetime import date, time
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
from app.seeds.ariston_tariffs import ensure_ariston_tariffs
from app.seeds.ariston_august import seed_ariston_strelna_august
from app.seeds.vehicle_types import ensure_vehicle_types

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
    from flask import current_app

    frozen = current_app.config.get("PLS_FREEZE_REFERENCE")
    stats = {
        "product_types": 0,
        "units": 0,
        "warehouses": 0,
        "roles": 0,
        "section_permissions": 0,
    }

    for code, name in PRODUCT_TYPES:
        row = ProductType.query.filter_by(code=code).first()
        active = code == "RESPONSIBLE_STORAGE"
        if not row:
            db.session.add(ProductType(code=code, name=name, is_active=active))
            stats["product_types"] += 1
        elif not frozen and (not hasattr(row, "is_active") or row.is_active is None):
            row.is_active = active

    for code, name in UNITS:
        row = UnitOfMeasure.query.filter_by(code=code).first()
        active = code not in ("m2day", "vehicle")
        if not row:
            db.session.add(UnitOfMeasure(code=code, name=name, is_active=active))
            stats["units"] += 1
        elif not frozen and row.is_active is None:
            row.is_active = active

    for code, name in WAREHOUSES:
        row = Warehouse.query.filter_by(code=code).first()
        if not row:
            db.session.add(Warehouse(
                code=code,
                name=name,
                is_active=True,
                work_day_start=time(9, 0),
                work_day_end=time(17, 30),
            ))
            stats["warehouses"] += 1
        elif not frozen:
            if row.work_day_start is None:
                row.work_day_start = time(9, 0)
            if row.work_day_end is None:
                row.work_day_end = time(17, 30)

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
    stats["vehicle_types"] = ensure_vehicle_types()
    if verbose:
        print(f"seed-reference: {stats}")
    return stats


def _ensure_demo_user(
    *,
    email: str,
    full_name: str,
    password: str,
    role_code: str,
    warehouse: Warehouse,
    roles: dict[str, Role],
    stats: dict,
    stat_key: str,
) -> User:
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            is_active=True,
        )
        db.session.add(user)
        stats[stat_key] = 1
    db.session.flush()
    role = roles.get(role_code)
    if role and not UserRole.query.filter_by(user_id=user.id, role_id=role.id).first():
        db.session.add(UserRole(user_id=user.id, role_id=role.id))
    if not UserWarehouseAccess.query.filter_by(user_id=user.id, warehouse_id=warehouse.id).first():
        db.session.add(UserWarehouseAccess(user_id=user.id, warehouse_id=warehouse.id))
    return user


def seed_admin(*, verbose: bool = False) -> dict:
    """Администратор и демо-пользователи УСС (Стрельна / Аристон)."""
    seed_reference(verbose=False)
    stats = {"admin": 0, "transport_user": 0, "warehouse_user": 0, "inventory_user": 0}

    admin_email = os.getenv("PLS_ADMIN_EMAIL", "admin@bsh-ru.ru").strip().lower()
    admin_password = os.getenv("PLS_ADMIN_PASSWORD", "admin")

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

    db.session.flush()

    roles = {r.code: r for r in Role.query.all()}
    if admin and roles.get("admin"):
        if not UserRole.query.filter_by(user_id=admin.id, role_id=roles["admin"].id).first():
            db.session.add(UserRole(user_id=admin.id, role_id=roles["admin"].id))

    wh = Warehouse.query.filter_by(code="strelna").first() or Warehouse.query.first()
    if not wh:
        db.session.commit()
        if verbose:
            print("seed-admin: нет склада strelna")
        return stats

    _ensure_demo_user(
        email=os.getenv("PLS_TRANSPORT_EMAIL", "transport@bsh-ru.ru").strip().lower(),
        full_name="Транспортная логистика",
        password=os.getenv("PLS_TRANSPORT_PASSWORD", "transport"),
        role_code="transport_logistics",
        warehouse=wh,
        roles=roles,
        stats=stats,
        stat_key="transport_user",
    )
    _ensure_demo_user(
        email=os.getenv("PLS_WAREHOUSE_EMAIL", "warehouse@bsh-ru.ru").strip().lower(),
        full_name="Складская логистика",
        password=os.getenv("PLS_WAREHOUSE_PASSWORD", "warehouse"),
        role_code="warehouse_logistics",
        warehouse=wh,
        roles=roles,
        stats=stats,
        stat_key="warehouse_user",
    )
    _ensure_demo_user(
        email=os.getenv("PLS_INVENTORY_EMAIL", "inventory@bsh-ru.ru").strip().lower(),
        full_name="Управление запасами",
        password=os.getenv("PLS_INVENTORY_PASSWORD", "inventory"),
        role_code="inventory_management",
        warehouse=wh,
        roles=roles,
        stats=stats,
        stat_key="inventory_user",
    )

    db.session.commit()
    if verbose:
        print(
            f"seed-admin: {stats} (admin={admin_email}, склад={wh.code}, "
            "transport/warehouse/inventory@bsh-ru.ru)"
        )
    return stats


def seed_demo(*, verbose: bool = False) -> dict:
    """Демо: Аристон / Стрельна / август 2026 (из эталонного Excel Billings)."""
    seed_admin(verbose=False)
    stats = seed_ariston_strelna_august(verbose=verbose)
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
    ensure_vehicle_types()
    db.session.commit()
