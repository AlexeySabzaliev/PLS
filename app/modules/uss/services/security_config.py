"""Конфигурация доступа к порталу охраны (отдельно от входа пользователей в ПЛС)."""
from __future__ import annotations

import os
import sys

# Режимы аутентификации **сервера** к security.bsh-ru.ru (не пользователь ПЛС):
#   negotiate — prod: Kerberos/SSPI учётки службы (Windows)
#   cookie    — cookie/файл сессии (операционное обновление)
#   browser   — dev: cookies из Yandex/Edge на машине разработчика
#   local_db  — dev: локальный кэш security_admission_form
#   stub      — dev: демо-данные

_VALID_MODES = frozenset({"negotiate", "cookie", "browser", "local_db", "stub"})


def _is_production() -> bool:
    return os.getenv("FLASK_ENV", "development").lower() == "production"


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in ("1", "true", "yes")


def security_use_mock() -> bool:
    if os.getenv("SECURITY_PORTAL_STUB", "").lower() in ("1", "true", "yes"):
        return True
    return os.getenv("SECURITY_USE_MOCK", "").lower() in ("1", "true", "yes")


def security_use_negotiate() -> bool:
    default = sys.platform == "win32"
    return _env_bool("SECURITY_USE_NEGOTIATE", default)


def security_use_local_db() -> bool:
    return _env_bool("SECURITY_USE_LOCAL_DB")


def security_offline_only() -> bool:
    return _env_bool("SECURITY_OFFLINE_ONLY")


def security_auto_browser_cookies() -> bool:
    # В prod браузер разработчика не используем
    if _is_production():
        return _env_bool("SECURITY_AUTO_BROWSER_COOKIES", False)
    return _env_bool("SECURITY_AUTO_BROWSER_COOKIES", True)


def resolve_security_auth_mode() -> str:
    explicit = (os.getenv("SECURITY_AUTH_MODE") or "").strip().lower()
    if explicit in _VALID_MODES:
        return explicit
    if security_use_mock():
        return "stub"
    if security_offline_only():
        return "local_db"
    if security_use_negotiate():
        return "negotiate"
    if os.getenv("SECURITY_API_COOKIE", "").strip() or os.getenv("SECURITY_COOKIE_FILE", "").strip():
        return "cookie"
    if security_auto_browser_cookies():
        return "browser"
    return "negotiate" if sys.platform == "win32" else "cookie"


def security_auth_mode_label(mode: str) -> str:
    labels = {
        "negotiate": "SSO сервера (Kerberos/Negotiate, учётка службы)",
        "cookie": "сессия по cookie/файлу",
        "browser": "dev: cookies браузера на ПК разработчика",
        "local_db": "dev: локальный кэш БД",
        "stub": "dev: демо-заглушка",
    }
    return labels.get(mode, mode)
