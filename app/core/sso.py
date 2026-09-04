"""Корпоративный SSO: заголовки IIS / Windows SSPI / dev bypass."""
from __future__ import annotations

import os
import sys

from app.config import Config

# GetUserNameExW: NameSamCompatible=2, NameUserPrincipal=8
_NAME_SAM_COMPATIBLE = 2
_NAME_USER_PRINCIPAL = 8


def sso_config_public(environ: dict | None = None) -> dict:
    payload = {
        "enabled": Config.SSO_ENABLED,
        "mode": Config.SSO_MODE if Config.SSO_ENABLED else None,
        "password_login": Config.SSO_ALLOW_PASSWORD_LOGIN,
        "windows_fallback": bool(Config.SSO_ALLOW_WINDOWS_FALLBACK),
        "dev_bypass": bool(Config.SSO_DEV_IDENTITY) and not _is_production(),
    }
    if Config.SSO_ENABLED:
        source, raw = resolve_sso_identity_with_source(environ=environ)
        payload["identity_source"] = source
        if raw:
            payload["resolved_identity"] = raw
            emails = identity_lookup_emails(raw)
            if emails:
                payload["resolved_email"] = emails[0]
                if len(emails) > 1:
                    payload["resolved_email_candidates"] = emails
        if source == "none" and (Config.SSO_MODE or "").lower() in ("headers", "auto") and not _is_production():
            payload["hint"] = (
                "Ожидается заголовок/IIS LOGON_USER от прокси. "
                "На сервере под службой Windows-учётка процесса не совпадает с пользователем браузера."
            )
    return payload


def _is_production() -> bool:
    return os.getenv("FLASK_ENV", "development").lower() == "production"


def normalize_identity(raw: str) -> tuple[str, str | None]:
    """DOMAIN\\login, login@domain или UPN → (email, local_part)."""
    value = (raw or "").strip()
    if not value:
        return "", None
    if "@" in value:
        email = value.lower()
        return email, email.split("@", 1)[0]
    if "\\" in value:
        sam = value.split("\\", 1)[-1].strip().lower()
        domain = (Config.SSO_EMAIL_DOMAIN or "bsh-ru.ru").strip().lstrip("@")
        return f"{sam}@{domain}", sam
    domain = (Config.SSO_EMAIL_DOMAIN or "bsh-ru.ru").strip().lstrip("@")
    local = value.lower()
    return f"{local}@{domain}", local


def identity_lookup_emails(raw: str) -> list[str]:
    """Варианты email для поиска учётки (UPN, SAM, частичное совпадение local-part)."""
    value = (raw or "").strip()
    if not value:
        return []
    out: list[str] = []
    if "@" in value:
        out.append(value.lower())
    norm, _ = normalize_identity(value)
    if norm:
        out.append(norm.lower())
    sam = value.split("\\", 1)[-1].strip().lower() if "\\" in value else ""
    if sam and "@" not in sam:
        domain = (Config.SSO_EMAIL_DOMAIN or "bsh-ru.ru").strip().lstrip("@")
        out.append(f"{sam}@{domain}")
    # уникальные, порядок важен
    seen: set[str] = set()
    unique: list[str] = []
    for item in out:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            unique.append(key)
    return unique


def _identity_from_headers(headers) -> str | None:
    if not headers:
        return None
    header = Config.SSO_USER_HEADER or "Remote-User"
    for key, val in headers.items():
        if key.lower() == header.lower() and val and val.strip():
            return val.strip()
    for alt in (
        "Remote-User",
        "X-Remote-User",
        "X-IIS-WindowsAuth",
        "X-Forwarded-User",
        "X-MS-CLIENT-PRINCIPAL-NAME",
    ):
        for key, val in headers.items():
            if key.lower() == alt.lower() and val and val.strip():
                return val.strip()
    return None


def _identity_from_environ(environ: dict | None) -> str | None:
    if not environ:
        return None
    for key in (
        "REMOTE_USER",
        "LOGON_USER",
        "AUTH_USER",
        "HTTP_REMOTE_USER",
        "HTTP_LOGON_USER",
        "HTTP_X_REMOTE_USER",
        "HTTP_X_IIS_WINDOWSAUTH",
        "HTTP_X_MS_CLIENT_PRINCIPAL_NAME",
    ):
        val = environ.get(key)
        if val and str(val).strip():
            return str(val).strip()
    return None


def _get_username_ex(name_format: int) -> str | None:
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        secur32 = ctypes.windll.secur32
        size = wintypes.ULONG(0)
        secur32.GetUserNameExW(name_format, None, ctypes.byref(size))
        if size.value < 2:
            return None
        buf = ctypes.create_unicode_buffer(size.value)
        if not secur32.GetUserNameExW(name_format, buf, ctypes.byref(size)):
            # повтор с запасом — иногда первый size без терминатора
            buf = ctypes.create_unicode_buffer(size.value + 1)
            size = wintypes.ULONG(len(buf))
            if not secur32.GetUserNameExW(name_format, buf, ctypes.byref(size)):
                return None
        return buf.value.strip() or None
    except Exception:
        return None


def get_windows_identity() -> str | None:
    """UPN (предпочтительно) или DOMAIN\\user на процессе Windows."""
    if sys.platform != "win32":
        return None
    upn = _get_username_ex(_NAME_USER_PRINCIPAL)
    if upn and "@" in upn:
        return upn
    sam = _get_username_ex(_NAME_SAM_COMPATIBLE)
    if sam:
        if "\\" in sam:
            return sam
        domain = os.environ.get("USERDOMAIN", "").strip()
        if domain and domain.upper() not in ("", "WORKGROUP"):
            return f"{domain}\\{sam}"
        return sam
    user = os.environ.get("USERNAME", "").strip()
    domain = os.environ.get("USERDOMAIN", "").strip()
    if user and domain and domain.upper() not in ("", "WORKGROUP"):
        return f"{domain}\\{user}"
    return user or None


def resolve_sso_identity(headers=None, environ: dict | None = None) -> str | None:
    _, raw = resolve_sso_identity_with_source(headers=headers, environ=environ)
    return raw


def resolve_sso_identity_with_source(
    headers=None,
    environ: dict | None = None,
) -> tuple[str, str | None]:
    """Источник: headers (IIS/прокси), windows (dev), dev_stub, none."""
    if not Config.SSO_ENABLED:
        return "none", None
    mode = (Config.SSO_MODE or "headers").lower()
    raw: str | None = None
    source = "none"

    if mode in ("auto", "headers"):
        raw = _identity_from_environ(environ)
        if raw:
            source = "headers"
        if not raw and headers is not None:
            raw = _identity_from_headers(headers)
            if raw:
                source = "headers"

    if not raw and mode in ("windows", "auto") and Config.SSO_ALLOW_WINDOWS_FALLBACK:
        raw = get_windows_identity()
        if raw:
            source = "windows"

    if not raw and Config.SSO_DEV_IDENTITY and not _is_production():
        raw = Config.SSO_DEV_IDENTITY
        if raw:
            source = "dev_stub"

    return source, raw
