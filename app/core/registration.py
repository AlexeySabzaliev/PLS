"""Саморегистрация пользователей (роль «просмотр отчётов»)."""
from __future__ import annotations

from app.config import Config
from app.core.auth import login_user_password
from app.core.passwords import validate_password
from app.core.user_admin import create_user, validate_email

_REGISTRATION_ERRORS = {
    "disabled": "Регистрация отключена",
    "invalid_email": "Укажите корректный email",
    "invalid_domain": "Регистрация доступна только для корпоративных адресов",
    "duplicate_email": "Пользователь с таким email уже зарегистрирован",
    "mismatch": "Пароли не совпадают",
}


def registration_email_domain() -> str:
    raw = (Config.PLS_REGISTRATION_EMAIL_DOMAIN or "").strip().lstrip("@").lower()
    return raw


def email_allowed_for_registration(email: str) -> bool:
    domain = registration_email_domain()
    if not domain:
        return True
    norm = validate_email(email)
    if not norm:
        return False
    return norm.endswith("@" + domain)


def register_user(
    *,
    email: str,
    password: str,
    confirm_password: str,
    full_name: str | None = None,
) -> tuple[dict | None, str | None]:
    """Создать учётку с ролью reports_viewer и войти в сессию."""
    if not Config.PLS_REGISTRATION_ENABLED:
        return None, "disabled"
    if password != confirm_password:
        return None, "mismatch"
    norm = validate_email(email)
    if not norm:
        return None, "invalid_email"
    if not email_allowed_for_registration(norm):
        return None, "invalid_domain"
    ok, perr = validate_password(password, email=norm)
    if not ok:
        return None, perr
    user, err = create_user(
        email=norm,
        full_name=full_name,
        role_codes=["reports_viewer"],
        password=password,
    )
    if err:
        return None, err
    logged_in, login_err = login_user_password(norm, password)
    if not logged_in:
        return user, login_err
    return logged_in, None


def registration_error_message(code: str | None) -> str:
    if code in _REGISTRATION_ERRORS:
        return _REGISTRATION_ERRORS[code]
    from app.core.passwords import password_error_message

    return password_error_message(code)
