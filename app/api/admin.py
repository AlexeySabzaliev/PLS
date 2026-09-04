"""API администрирования."""
from __future__ import annotations

from flask import Blueprint, g, request

from app.core.auth import login_required
from app.core.password_reset import (
    approve_password_reset,
    dismiss_password_reset,
    list_pending_password_resets,
    pending_password_reset_count,
)
from app.core.passwords import password_error_message
from app.core.user_admin import (
    admin_set_password,
    get_user,
    list_users,
    role_catalog,
    update_user,
    warehouse_catalog,
)

bp = Blueprint("admin_api", __name__, url_prefix="/api/admin")


def _require_admin():
    if not g.user or not g.user.get("is_admin"):
        return {"error": "forbidden"}, 403
    return None


@bp.get("/password-reset-requests")
@login_required
def get_password_reset_requests():
    err = _require_admin()
    if err:
        return err
    return {
        "pending_count": pending_password_reset_count(),
        "items": list_pending_password_resets(),
        "roles": role_catalog(),
        "warehouses": warehouse_catalog(),
    }


@bp.get("/users/meta")
@login_required
def get_users_meta():
    err = _require_admin()
    if err:
        return err
    return {
        "roles": role_catalog(),
        "warehouses": warehouse_catalog(),
    }


@bp.get("/users")
@login_required
def get_users():
    err = _require_admin()
    if err:
        return err
    include_inactive = request.args.get("include_inactive", "1") != "0"
    return {
        "items": list_users(include_inactive=include_inactive),
        "roles": role_catalog(),
        "warehouses": warehouse_catalog(),
    }


@bp.post("/users")
@login_required
def post_user():
    err = _require_admin()
    if err:
        return err
    return {
        "error": "registration_only",
        "message": "Новые пользователи регистрируются сами на главной странице. "
        "Здесь — только сброс пароля и изменение ролей.",
    }, 403


@bp.put("/users/<int:user_id>")
@login_required
def put_user(user_id: int):
    err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    role_codes = data.get("role_codes")
    if g.user.get("id") == user_id and data.get("is_active") is False:
        return {"error": "forbidden", "message": "Нельзя деактивировать свою учётку"}, 400
    if g.user.get("id") == user_id and role_codes is not None and "admin" not in role_codes:
        return {"error": "forbidden", "message": "Нельзя снять с себя роль администратора"}, 400
    user, error = update_user(
        user_id,
        full_name=data.get("full_name"),
        is_active=data.get("is_active") if "is_active" in data else None,
        role_codes=role_codes if role_codes is not None else None,
        warehouse_ids=data.get("warehouse_ids") if "warehouse_ids" in data else None,
    )
    if error == "not_found":
        return {"error": "not_found"}, 404
    return {"ok": True, "user": user}


@bp.get("/users/<int:user_id>")
@login_required
def get_user_detail(user_id: int):
    err = _require_admin()
    if err:
        return err
    user = get_user(user_id)
    if not user:
        return {"error": "not_found"}, 404
    return user


@bp.post("/users/<int:user_id>/password")
@login_required
def post_user_password(user_id: int):
    err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    password = (data.get("password") or "").strip()
    if not password:
        return {"error": "empty", "message": password_error_message("empty")}, 400
    user, error = admin_set_password(user_id, password)
    if error == "not_found":
        return {"error": "not_found"}, 404
    if error:
        return {"error": error, "message": password_error_message(error)}, 400
    return {"ok": True, "user": user}


@bp.post("/password-reset-requests/<int:request_id>/approve")
@login_required
def post_password_reset_approve(request_id: int):
    err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    password = (data.get("password") or "").strip()
    if not password:
        return {"error": "empty", "message": password_error_message("empty")}, 400
    result = approve_password_reset(
        request_id,
        g.user["id"],
        new_password=password,
        note=data.get("note"),
    )
    if result.get("error"):
        code = result["error"]
        if code == "not_found":
            return result, 404
        return {
            "error": code,
            "message": result.get("message") or password_error_message(code),
        }, 400
    return result


@bp.post("/password-reset-requests/<int:request_id>/dismiss")
@login_required
def post_password_reset_dismiss(request_id: int):
    err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    result = dismiss_password_reset(request_id, g.user["id"], note=data.get("note"))
    if result.get("error"):
        return result, 404
    return result
