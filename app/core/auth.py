"""Аутентификация: сессии и вход по паролю."""
from __future__ import annotations

from functools import wraps

from flask import g, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from app.db import db

PUBLIC_PATHS = frozenset({
    "/api/health",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/register-policy",
    "/api/auth/password-policy",
    "/api/auth/password-reset/request",
})


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    if not password_hash:
        return False
    return check_password_hash(password_hash, password)


def load_user_dict(user_id: int) -> dict | None:
    from app.modules.reference.models import User, UserRole, UserWarehouseAccess, Warehouse

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
        "has_password": bool(user.password_hash),
    }


def find_user_by_email(email: str):
    from app.modules.reference.models import User

    return User.query.filter(
        db.func.lower(User.email) == email.lower(),
        User.is_active.is_(True),
    ).first()


def login_user_password(email: str, password: str) -> tuple[dict | None, str | None]:
    """Вход по email/паролю. Ошибки: invalid_credentials, no_password, inactive."""
    from app.modules.reference.models import User

    norm = (email or "").strip().lower()
    if not norm or not password:
        return None, "invalid_credentials"
    user = User.query.filter(db.func.lower(User.email) == norm).first()
    if not user:
        return None, "invalid_credentials"
    if not user.is_active:
        return None, "inactive"
    if not user.password_hash:
        return None, "no_password"
    if not verify_password(user.password_hash, password):
        return None, "invalid_credentials"
    session["user_id"] = user.id
    session.permanent = True
    return load_user_dict(user.id), None


def set_user_password(user_id: int, new_password: str, *, email: str | None = None) -> str | None:
    """Установить пароль (админ). Возвращает код ошибки валидации или None."""
    from app.core.passwords import validate_password
    from app.modules.reference.models import User

    ok, err = validate_password(new_password, email=email)
    if not ok:
        return err
    user = db.session.get(User, user_id)
    if not user:
        return "not_found"
    user.password_hash = hash_password(new_password)
    db.session.commit()
    return None


def change_user_password(
    user_id: int,
    *,
    current_password: str | None,
    new_password: str,
) -> str | None:
    """Смена/установка пароля. Без текущего — только если пароль ещё не задан."""
    from app.core.passwords import validate_password
    from app.modules.reference.models import User

    user = db.session.get(User, user_id)
    if not user or not user.is_active:
        return "not_found"
    if user.password_hash:
        if not current_password or not verify_password(user.password_hash, current_password):
            return "invalid_current"
        if verify_password(user.password_hash, new_password):
            return "same_as_current"
    ok, err = validate_password(new_password, email=user.email)
    if not ok:
        return err
    user.password_hash = hash_password(new_password)
    db.session.commit()
    return None


def update_user_profile(user_id: int, *, full_name: str | None) -> dict | None:
    from app.modules.reference.models import User

    user = db.session.get(User, user_id)
    if not user or not user.is_active:
        return None
    if full_name is not None:
        user.full_name = full_name.strip() or user.full_name
    db.session.commit()
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


def edit_required(view):
    """Запретить изменение данных роли «только просмотр отчётов»."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        from app.core.permissions import user_can_edit

        if not user_can_edit(g.user):
            return {"error": "forbidden", "message": "Доступ только на просмотр"}, 403
        return view(*args, **kwargs)

    return wrapped


def before_request_auth():
    path = request.path
    if path.startswith("/static/"):
        g.user = None
        return None

    is_public = path in PUBLIC_PATHS
    if path.startswith("/api/"):
        user = get_current_user()
        if not user and not is_public and not path.startswith("/api/auth/"):
            return jsonify({"error": "unauthorized", "message": "Требуется вход"}), 401
        g.user = user
    else:
        g.user = get_current_user()
    return None
