"""API аутентификации."""
from __future__ import annotations

from flask import Blueprint, request, session

from app.config import Config
from app.core.auth import attempt_sso_login, get_current_user, login_user_password, logout_user
from app.core.sso import sso_config_public

bp = Blueprint("auth_api", __name__, url_prefix="/api/auth")


@bp.get("/sso/config")
def sso_config():
    return sso_config_public()


@bp.post("/sso/attempt")
def sso_attempt():
    if not Config.SSO_ENABLED:
        return {"error": "sso_disabled"}, 404
    user = attempt_sso_login(request.headers)
    if not user:
        return {"error": "sso_no_access"}, 403
    return {"user": user}


@bp.post("/login")
def login():
    if Config.SSO_ENABLED and not Config.SSO_ALLOW_PASSWORD_LOGIN:
        return {"error": "password_login_disabled"}, 403
    data = request.get_json(silent=True) or {}
    user = login_user_password(data.get("email", ""), data.get("password", ""))
    if not user:
        return {"error": "invalid_credentials"}, 401
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
    payload["sso"] = sso_config_public()
    return payload
