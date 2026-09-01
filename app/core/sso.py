"""Корпоративный SSO: заголовки IIS / Windows SSPI / dev bypass."""
from __future__ import annotations

import os
import sys

from app.config import Config


def sso_config_public() -> dict:
    return {
        "enabled": Config.SSO_ENABLED,
        "mode": Config.SSO_MODE if Config.SSO_ENABLED else None,
        "password_login": Config.SSO_ALLOW_PASSWORD_LOGIN,
        "dev_bypass": bool(Config.SSO_DEV_IDENTITY) and not _is_production(),
    }


def _is_production() -> bool:
    return os.getenv("FLASK_ENV", "development").lower() == "production"


def normalize_identity(raw: str) -> tuple[str, str | None]:
    """DOMAIN\\login или login@domain → (email, local_part)."""
    value = (raw or "").strip()
    if not value:
        return "", None
    if "\\" in value:
        value = value.split("\\")[-1].strip()
    if "@" in value:
        email = value.lower()
        return email, email.split("@", 1)[0]
    domain = (Config.SSO_EMAIL_DOMAIN or "bsh-ru.ru").strip().lstrip("@")
    local = value.lower()
    return f"{local}@{domain}", local


def _identity_from_headers(headers) -> str | None:
    header = Config.SSO_USER_HEADER or "Remote-User"
    for key, val in headers.items():
        if key.lower() == header.lower() and val and val.strip():
            return val.strip()
    for alt in ("X-Remote-User", "X-IIS-WindowsAuth", "X-Forwarded-User"):
        for key, val in headers.items():
            if key.lower() == alt.lower() and val and val.strip():
                return val.strip()
    return None


def get_windows_identity() -> str | None:
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        secur32 = ctypes.windll.secur32
        size = wintypes.ULONG(0)
        secur32.GetUserNameExW(2, None, ctypes.byref(size))
        if size.value == 0:
            return None
        buf = ctypes.create_unicode_buffer(size.value)
        if secur32.GetUserNameExW(2, buf, ctypes.byref(size)):
            return buf.value.strip() or None
    except Exception:
        pass
    user = os.environ.get("USERNAME", "").strip()
    domain = os.environ.get("USERDOMAIN", "").strip()
    if user and domain and domain.upper() not in ("", "WORKGROUP"):
        return f"{domain}\\{user}"
    return user or None


def resolve_sso_identity(headers=None) -> str | None:
    if not Config.SSO_ENABLED:
        return None
    mode = (Config.SSO_MODE or "headers").lower()
    raw: str | None = None
    if mode == "headers" and headers is not None:
        raw = _identity_from_headers(headers)
    elif mode == "windows":
        raw = get_windows_identity()
    if not raw and Config.SSO_DEV_IDENTITY and not _is_production():
        raw = Config.SSO_DEV_IDENTITY
    return raw
