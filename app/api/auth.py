"""API аутентификации."""
from __future__ import annotations

from flask import Blueprint, request

from app.core.auth import (
    change_user_password,
    get_current_user,
    login_user_password,
    logout_user,
    update_user_profile,
)
from app.core.password_reset import record_password_reset_request
from app.core.passwords import password_error_message, password_policy_public
from app.core.registration import register_user, registration_error_message
from app.config import Config
from app.services.maintenance import maintenance_for_user

bp = Blueprint("auth_api", __name__, url_prefix="/api/auth")

_LOGIN_MESSAGES = {
    "invalid_credentials": "Неверный email или пароль",
    "no_password": "Пароль не задан. Запросите восстановление или обратитесь к администратору.",
    "inactive": "Учётная запись отключена",
}


@bp.get("/password-policy")
def password_policy():
    return password_policy_public()


@bp.post("/password-reset/request")
def password_reset_request():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    note = (data.get("note") or "").strip()
    if email:
        record_password_reset_request(email, note=note or None)
    # Не раскрываем, есть ли пользователь
    return {
        "ok": True,
        "message": "Если учётная запись найдена, заявка отправлена администратору.",
    }


@bp.post("/register")
def register():
    if not Config.PLS_REGISTRATION_ENABLED:
        return {
            "error": "disabled",
            "message": registration_error_message("disabled"),
        }, 403
    data = request.get_json(silent=True) or {}
    user, err = register_user(
        email=data.get("email", ""),
        password=data.get("password") or "",
        confirm_password=data.get("confirm_password") or "",
        full_name=data.get("full_name"),
    )
    if not user:
        code = err or "invalid_email"
        status = 409 if code == "duplicate_email" else 400
        return {"error": code, "message": registration_error_message(code)}, status
    return {"ok": True, "user": user, "message": "Регистрация выполнена. Доступ — просмотр отчётов."}


@bp.get("/register-policy")
def register_policy():
    domain = (Config.PLS_REGISTRATION_EMAIL_DOMAIN or "").strip()
    return {
        "enabled": Config.PLS_REGISTRATION_ENABLED,
        "email_domain": domain or None,
        "default_role": "reports_viewer",
        "password_policy": password_policy_public(),
    }


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    user, err = login_user_password(data.get("email", ""), data.get("password", ""))
    if not user:
        code = err or "invalid_credentials"
        return {
            "error": code,
            "message": _LOGIN_MESSAGES.get(code, _LOGIN_MESSAGES["invalid_credentials"]),
        }, 401
    return {"user": user}


@bp.post("/logout")
def logout():
    logout_user()
    return {"ok": True}


@bp.get("/me")
def me():
    user = get_current_user()
    if not user:
        return {"error": "unauthorized"}, 401
    payload = dict(user)
    payload["password_policy"] = password_policy_public()
    payload["maintenance"] = maintenance_for_user(user)
    return payload


@bp.get("/profile")
def get_profile():
    user = get_current_user()
    if not user:
        return {"error": "unauthorized"}, 401
    return {
        **user,
        "password_policy": password_policy_public(),
    }


@bp.put("/profile")
def put_profile():
    user = get_current_user()
    if not user:
        return {"error": "unauthorized"}, 401
    data = request.get_json(silent=True) or {}
    updated = update_user_profile(user["id"], full_name=data.get("full_name"))
    if not updated:
        return {"error": "not_found"}, 404
    updated["password_policy"] = password_policy_public()
    return {"ok": True, "user": updated}


@bp.post("/change-password")
def post_change_password():
    user = get_current_user()
    if not user:
        return {"error": "unauthorized"}, 401
    data = request.get_json(silent=True) or {}
    new_password = data.get("new_password") or ""
    confirm = data.get("confirm_password") or ""
    if new_password != confirm:
        return {
            "error": "mismatch",
            "message": password_error_message("mismatch"),
        }, 400
    err = change_user_password(
        user["id"],
        current_password=data.get("current_password"),
        new_password=new_password,
    )
    if err == "invalid_current":
        return {"error": err, "message": "Неверный текущий пароль"}, 400
    if err:
        return {"error": err, "message": password_error_message(err)}, 400
    return {"ok": True, "message": "Пароль обновлён"}
