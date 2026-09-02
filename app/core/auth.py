"""Аутентификация: сессии, SSO, загрузка пользователя."""
from __future__ import annotations

from functools import wraps

from flask import g, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from app.core.sso import normalize_identity, resolve_sso_identity
from app.db import db

PUBLIC_PATHS = frozenset({
    "/api/health",
    "/api/auth/login",
    "/api/auth/sso/config",
    "/api/auth/sso/attempt",
})


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    if not password_hash:
        return False
    return check_password_hash(password_hash, password)


def load_user_dict(user_id: int) -> dict | None:
    from app.modules.reference.models import Role, User, UserRole, UserWarehouseAccess, Warehouse

    user = db.session.get(User, user_id)
    if not user or not user.is_active:
        return None
    role_codes = [ur.role.code for ur in UserRole.query.filter_by(user_id=user.id).all()]
    wh_ids = [
        uwa.warehouse_id
        for uwa in UserWarehouseAccess.query.filter_by(user_id=user.id).all()
    ]
    warehouses = Warehouse.query.filter(Warehouse.id.in_(wh_ids), Warehouse.is_active.is_(True)).all() if wh_ids else []
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "is_admin": user.is_admin,
        "role_codes": role_codes,
        "warehouse_ids": [w.id for w in warehouses],
        "warehouses": [{"id": w.id, "code": w.code, "name": w.name} for w in warehouses],
    }


def find_user_by_email(email: str):
    from app.modules.reference.models import User

    return User.query.filter(
        db.func.lower(User.email) == email.lower(),
        User.is_active.is_(True),
    ).first()


def attempt_sso_login(headers) -> dict | None:
    raw = resolve_sso_identity(headers)
    if not raw:
        return None
    email, _ = normalize_identity(raw)
    user = find_user_by_email(email)
    if not user:
        from app.core.sso_access import record_sso_access_request

        record_sso_access_request(raw)
        return None
    session["user_id"] = user.id
    session.permanent = True
    return load_user_dict(user.id)


def login_user_password(email: str, password: str) -> dict | None:
    from app.modules.reference.models import User

    user = User.query.filter(db.func.lower(User.email) == email.lower()).first()
    if not user or not user.is_active or not verify_password(user.password_hash, password):
        return None
    session["user_id"] = user.id
    session.permanent = True
    return load_user_dict(user.id)


def logout_user() -> None:
    session.pop("user_id", None)


def get_current_user() -> dict | None:
    uid = session.get("user_id")
    if not uid:
        return None
    return load_user_dict(uid)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = get_current_user()
        if not user:
            return {"error": "unauthorized", "message": "Требуется вход"}, 401
        g.user = user
        return view(*args, **kwargs)

    return wrapped


def before_request_auth():
    path = request.path
    if path in PUBLIC_PATHS or path.startswith("/static/"):
        g.user = None
        return None
    if path.startswith("/api/"):
        user = get_current_user()
        if not user and not path.startswith("/api/auth/"):
            return jsonify({"error": "unauthorized", "message": "Требуется вход"}), 401
        g.user = user
    else:
        g.user = get_current_user()
    return None
