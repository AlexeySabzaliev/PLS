"""Политика и проверка паролей."""
from __future__ import annotations

import re

from app.config import Config

_PASSWORD_ERRORS = {
    "empty": "Укажите пароль",
    "too_short": "Пароль слишком короткий",
    "no_letter": "Пароль должен содержать букву",
    "no_digit": "Пароль должен содержать цифру",
    "same_as_email": "Пароль не должен совпадать с email",
    "mismatch": "Пароли не совпадают",
    "same_as_current": "Новый пароль должен отличаться от текущего",
    "user_not_found": "Пользователь не найден",
    "not_found": "Заявка не найдена или уже обработана",
}


def password_policy_public() -> dict:
    return {
        "min_length": Config.PASSWORD_MIN_LENGTH,
        "require_letter": True,
        "require_digit": True,
    }


def password_policy_hint() -> str:
    p = password_policy_public()
    return f"Не менее {p['min_length']} символов, буква и цифра"


def validate_password(password: str, *, email: str | None = None) -> tuple[bool, str | None]:
    """Проверка сложности. Возвращает (ok, код_ошибки)."""
    if not password or not str(password).strip():
        return False, "empty"
    if len(password) < Config.PASSWORD_MIN_LENGTH:
        return False, "too_short"
    if not re.search(r"[A-Za-zА-Яа-яЁё]", password):
        return False, "no_letter"
    if not re.search(r"\d", password):
        return False, "no_digit"
    if email:
        local = email.split("@", 1)[0].lower()
        if password.lower() == email.lower() or password.lower() == local:
            return False, "same_as_email"
    return True, None


def password_error_message(code: str | None) -> str:
    return _PASSWORD_ERRORS.get(code or "", "Некорректный пароль")
