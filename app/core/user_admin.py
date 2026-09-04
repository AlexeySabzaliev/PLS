"""Управление пользователями и ролями (админ)."""
from __future__ import annotations

import re

from app.core.auth import hash_password, set_user_password
from app.core.passwords import validate_password
from app.core.permissions import ROLE_CODES
from app.db import db
from app.modules.reference.models import Role, User, UserRole, UserWarehouseAccess, Warehouse

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Порядок ролей в UI (единый список для ПЛС / УСС / УЗнТ)
ROLE_DISPLAY_ORDER = [
    "admin",
    "commercial_logistics",
    "transport_logistics",
    "warehouse_logistics",
    "inventory_management",
    "ved_specialist",
    "reports_viewer",
]


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def validate_email(email: str) -> str | None:
    """Нормализованный email или None."""
    norm = normalize_email(email)
    if not norm or not _EMAIL_RE.match(norm):
        return None
    return norm


def role_catalog() -> list[dict]:
    """Единый справочник ролей портала (без разбиения по модулям)."""
    by_code = {r.code: r for r in Role.query.all()}
    out: list[dict] = []
    for code in ROLE_DISPLAY_ORDER:
        if code not in ROLE_CODES:
            continue
        row = by_code.get(code)
        if row:
            out.append({"code": row.code, "name": row.name})
    return out


def warehouse_catalog() -> list[dict]:
    return [
        {"id": w.id, "code": w.code, "name": w.name, "is_active": w.is_active}
        for w in Warehouse.query.order_by(Warehouse.code).all()
    ]


def _user_role_codes(user_id: int) -> list[str]:
    rows = (
        db.session.query(Role.code)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user_id)
        .order_by(Role.code)
        .all()
    )
    return [r[0] for r in rows]


def _user_warehouse_ids(user_id: int) -> list[int]:
    rows = (
        UserWarehouseAccess.query.filter_by(user_id=user_id)
        .order_by(UserWarehouseAccess.warehouse_id)
        .all()
    )
    return [r.warehouse_id for r in rows]


def serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": bool(user.is_active),
        "is_admin": bool(user.is_admin),
        "has_password": bool(user.password_hash),
        "role_codes": _user_role_codes(user.id),
        "warehouse_ids": _user_warehouse_ids(user.id),
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }


def list_users(*, include_inactive: bool = True) -> list[dict]:
    q = User.query.order_by(User.email)
    if not include_inactive:
        q = q.filter_by(is_active=True)
    return [serialize_user(u) for u in q.all()]


def get_user(user_id: int) -> dict | None:
    user = db.session.get(User, user_id)
    if not user:
        return None
    return serialize_user(user)


def _resolve_role_ids(role_codes: list[str] | None) -> list[int]:
    if not role_codes:
        return []
    codes = {c.strip() for c in role_codes if c and c.strip() in ROLE_CODES}
    if not codes:
        return []
    roles = Role.query.filter(Role.code.in_(codes)).all()
    return [r.id for r in roles]


def _sync_admin_flag(user: User, role_codes: list[str] | None) -> None:
    """Флаг is_admin синхронизируется с ролью admin."""
    user.is_admin = "admin" in (role_codes or [])


def sync_user_roles(user_id: int, role_codes: list[str] | None) -> list[str]:
    """Заменить роли пользователя. Возвращает итоговые коды."""
    role_ids = set(_resolve_role_ids(role_codes or []))
    existing = UserRole.query.filter_by(user_id=user_id).all()
    existing_ids = {r.role_id for r in existing}
    for row in existing:
        if row.role_id not in role_ids:
            db.session.delete(row)
    for rid in role_ids - existing_ids:
        db.session.add(UserRole(user_id=user_id, role_id=rid))
    db.session.flush()
    codes = _user_role_codes(user_id)
    user = db.session.get(User, user_id)
    if user:
        _sync_admin_flag(user, codes)
    return codes


def sync_user_warehouses(user_id: int, warehouse_ids: list[int] | None) -> list[int]:
    """Заменить доступ к складам."""
    wanted = {int(w) for w in (warehouse_ids or []) if w is not None}
    existing = UserWarehouseAccess.query.filter_by(user_id=user_id).all()
    existing_ids = {r.warehouse_id for r in existing}
    for row in existing:
        if row.warehouse_id not in wanted:
            db.session.delete(row)
    for wid in wanted - existing_ids:
        if db.session.get(Warehouse, wid):
            db.session.add(UserWarehouseAccess(user_id=user_id, warehouse_id=wid))
    db.session.flush()
    return _user_warehouse_ids(user_id)


def create_user(
    *,
    email: str,
    full_name: str | None = None,
    is_admin: bool = False,
    is_active: bool = True,
    role_codes: list[str] | None = None,
    warehouse_ids: list[int] | None = None,
    password: str | None = None,
) -> tuple[dict | None, str | None]:
    norm = validate_email(email)
    if not norm:
        return None, "invalid_email"
    if User.query.filter(db.func.lower(User.email) == norm).first():
        return None, "duplicate_email"
    if password:
        ok, perr = validate_password(password, email=norm)
        if not ok:
            return None, perr
    user = User(
        email=norm,
        full_name=(full_name or "").strip() or norm.split("@", 1)[0],
        is_active=is_active,
        is_admin=False,
        password_hash=hash_password(password) if password else None,
    )
    db.session.add(user)
    db.session.flush()
    codes = sync_user_roles(user.id, role_codes)
    if is_admin and "admin" not in codes:
        codes = sync_user_roles(user.id, list(codes) + ["admin"])
    sync_user_warehouses(user.id, warehouse_ids)
    db.session.commit()
    return serialize_user(user), None


def update_user(
    user_id: int,
    *,
    full_name: str | None = None,
    is_admin: bool | None = None,
    is_active: bool | None = None,
    role_codes: list[str] | None = None,
    warehouse_ids: list[int] | None = None,
) -> tuple[dict | None, str | None]:
    user = db.session.get(User, user_id)
    if not user:
        return None, "not_found"
    if full_name is not None:
        user.full_name = full_name.strip() or user.full_name
    if is_active is not None:
        user.is_active = bool(is_active)
    if is_admin is not None and is_admin and role_codes is None:
        codes = _user_role_codes(user.id)
        if "admin" not in codes:
            sync_user_roles(user.id, codes + ["admin"])
    elif role_codes is not None:
        sync_user_roles(user.id, role_codes)
    elif is_admin is False:
        codes = [c for c in _user_role_codes(user.id) if c != "admin"]
        sync_user_roles(user.id, codes)
    if warehouse_ids is not None:
        sync_user_warehouses(user.id, warehouse_ids)
    db.session.commit()
    return serialize_user(user), None


def provision_user_from_sso(
    *,
    email: str,
    full_name: str | None,
    role_codes: list[str] | None = None,
    warehouse_ids: list[int] | None = None,
    is_admin: bool = False,
) -> tuple[User, bool]:
    """Создать или активировать пользователя (SSO approve / ручное добавление)."""
    norm = validate_email(email) or normalize_email(email)
    user = User.query.filter(db.func.lower(User.email) == norm).first()
    created = False
    if not user:
        user = User(
            email=norm,
            full_name=(full_name or "").strip() or norm.split("@", 1)[0],
            is_active=True,
            is_admin=False,
        )
        db.session.add(user)
        created = True
    else:
        if full_name and not user.full_name:
            user.full_name = full_name.strip()
        user.is_active = True
    db.session.flush()
    codes: list[str] | None = list(role_codes) if role_codes is not None else None
    if is_admin:
        codes = list(codes or _user_role_codes(user.id))
        if "admin" not in codes:
            codes.append("admin")
    if codes is not None:
        sync_user_roles(user.id, codes)
    if warehouse_ids is not None:
        sync_user_warehouses(user.id, warehouse_ids)
    return user, created


def admin_set_password(user_id: int, password: str) -> tuple[dict | None, str | None]:
    user = db.session.get(User, user_id)
    if not user:
        return None, "not_found"
    err = set_user_password(user_id, password, email=user.email)
    if err:
        return None, err
    db.session.refresh(user)
    return serialize_user(user), None
