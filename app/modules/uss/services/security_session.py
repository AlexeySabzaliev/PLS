"""Сессия портала security.bsh-ru.ru — серверный SSO (prod) и dev-обходы."""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from http.cookiejar import Cookie
from http.cookiejar import MozillaCookieJar
from pathlib import Path

import requests

from app.modules.uss.services.security_config import (
    resolve_security_auth_mode,
    security_auth_mode_label,
    security_auto_browser_cookies,
    security_use_negotiate,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SESSION_JAR = PROJECT_ROOT / "instance" / "security_session.txt"
COOKIE_DOMAINS = ("security.bsh-ru.ru", "adfs.bsh-ru.ru")
BROWSER_PROFILES = (
    ("yandex", Path(os.environ.get("LOCALAPPDATA", "")) / "Yandex/YandexBrowser/User Data/Default"),
    ("edge", Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Edge/User Data/Default"),
)

SECURITY_BASE_URL = os.getenv("SECURITY_BASE_URL", "https://security.bsh-ru.ru").rstrip("/")


def _stop_browser_on_lock() -> bool:
    return os.getenv("SECURITY_STOP_BROWSER", "1").lower() in ("1", "true", "yes")


def _negotiate_auth():
    if not security_use_negotiate():
        return None
    try:
        from requests_negotiate_sspi import HttpNegotiateAuth

        return HttpNegotiateAuth()
    except ImportError:
        try:
            from requests_negotiate import HttpNegotiateAuth

            return HttpNegotiateAuth()
        except ImportError:
            return None


def _new_session(cookie_header: str | None = None) -> requests.Session:
    session = requests.Session()
    session.headers.update({"Accept": "application/json", "User-Agent": "PLS-security-client/1.0"})
    if cookie_header:
        _apply_cookie_header(session, cookie_header)
    return session


def _apply_cookie_header(session: requests.Session, cookie_header: str) -> None:
    session.headers["Cookie"] = cookie_header.strip()
    for part in cookie_header.split(";"):
        piece = part.strip()
        if not piece or "=" not in piece:
            continue
        name, value = piece.split("=", 1)
        domain = "security.bsh-ru.ru"
        if name.startswith("MSIS"):
            domain = "adfs.bsh-ru.ru"
        session.cookies.set(name.strip(), value.strip(), domain=domain, path="/")


def _load_jar(session: requests.Session) -> bool:
    if not SESSION_JAR.is_file():
        return False
    try:
        jar = MozillaCookieJar(str(SESSION_JAR))
        jar.load(ignore_discard=True, ignore_expires=True)
        session.cookies.update(jar)
        return bool(session.cookies)
    except OSError as exc:
        logger.warning("security session jar load failed: %s", exc)
        return False


def save_session_jar(session: requests.Session) -> None:
    SESSION_JAR.parent.mkdir(parents=True, exist_ok=True)
    jar = MozillaCookieJar(str(SESSION_JAR))
    for cookie in session.cookies:
        jar.set_cookie(cookie)
    jar.save(ignore_discard=True, ignore_expires=True)


def session_authenticated(session: requests.Session, base_url: str) -> bool:
    try:
        resp = session.get(f"{base_url}/api/auth/status", timeout=15)
        if not resp.ok:
            return False
        data = resp.json()
        return bool(data.get("authenticated") and data.get("user", {}).get("username"))
    except (requests.RequestException, ValueError):
        return False


def _chromium_local_state(profile: Path) -> Path:
    return profile.parent / "Local State"


def _stop_browser_processes() -> None:
    if os.name != "nt":
        return
    try:
        subprocess.run(
            ["taskkill", "/IM", "browser.exe", "/F"],
            check=False,
            capture_output=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("security browser stop failed: %s", exc)


def _copy_cookies_file(src: Path, dst: Path) -> bool:
    try:
        shutil.copy2(src, dst)
        return True
    except OSError as exc:
        logger.info("security cookies copy locked: %s", exc)
        if not _stop_browser_on_lock():
            return False
        _stop_browser_processes()
        try:
            shutil.copy2(src, dst)
            return True
        except OSError as retry_exc:
            logger.warning("security cookies copy retry failed: %s", retry_exc)
            return False


def _session_from_browser_cookies(cookies) -> requests.Session | None:
    session = _new_session()
    found = False
    for cookie in cookies:
        domain = cookie.domain or ""
        if not any(token in domain for token in COOKIE_DOMAINS):
            continue
        found = True
        session.cookies.set_cookie(
            Cookie(
                version=0,
                name=cookie.name,
                value=cookie.value,
                port=None,
                port_specified=False,
                domain=domain.lstrip("."),
                domain_specified=bool(domain),
                domain_initial_dot=domain.startswith("."),
                path=cookie.path or "/",
                path_specified=bool(cookie.path),
                secure=bool(cookie.secure),
                expires=cookie.expires,
                discard=False,
                comment=None,
                comment_url=None,
                rest={"HttpOnly": cookie.has_nonstandard_attr("HttpOnly")},
                rfc2109=False,
            )
        )
    if not found:
        return None
    return session


def _cookies_from_profile(label: str, profile: Path, browser_cookie3) -> requests.Session | None:
    cookies_file = profile / "Network" / "Cookies"
    if not cookies_file.is_file():
        return None

    tmp = Path(tempfile.mkdtemp(prefix="pls-sec-cookies-"))
    dst = tmp / "Cookies"
    try:
        if not _copy_cookies_file(cookies_file, dst):
            return None
        key_file = _chromium_local_state(profile)
        if label == "edge":
            jar = browser_cookie3.edge(domain_name="security.bsh-ru.ru")
            return _session_from_browser_cookies(jar)
        jar = browser_cookie3.chrome(cookie_file=str(dst), key_file=str(key_file))
        return _session_from_browser_cookies(jar)
    except Exception as exc:
        logger.warning("security browser %s cookies failed: %s", label, exc)
        return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _session_from_browser() -> requests.Session | None:
    if not security_auto_browser_cookies():
        return None
    try:
        import browser_cookie3
    except ImportError:
        logger.warning("browser-cookie3 не установлен")
        return None

    for label, profile in BROWSER_PROFILES:
        if not profile.is_dir():
            continue
        session = _cookies_from_profile(label, profile, browser_cookie3)
        if session and session_authenticated(session, SECURITY_BASE_URL):
            return session
    return None


def _session_with_negotiate(base_url: str) -> requests.Session | None:
    auth = _negotiate_auth()
    if not auth:
        return None
    session = _new_session()
    session.auth = auth
    try:
        session.get(f"{base_url}/", timeout=20)
        sso = session.get(f"{base_url}/api/auth/sso", timeout=25)
        if sso.ok and session_authenticated(session, base_url):
            return session
    except requests.RequestException as exc:
        logger.warning("security negotiate session failed: %s", exc)
    return None


def security_refresh_hint(mode: str | None = None) -> str:
    mode = mode or resolve_security_auth_mode()
    if mode == "negotiate":
        return (
            "Нет SSO-сессии портала охраны. Проверьте учётку службы Windows (SPN, "
            "«Выполнять вход как») и SECURITY_USE_NEGOTIATE=true."
        )
    if mode == "cookie":
        return (
            "Нет сессии портала охраны. Задайте SECURITY_API_COOKIE или "
            "SECURITY_COOKIE_FILE, либо: flask pls security-refresh-session"
        )
    if mode == "browser":
        return (
            "Нет SSO-сессии портала охраны (dev). Войдите на https://security.bsh-ru.ru "
            "в Yandex/Edge под доменной учёткой, затем: flask pls security-refresh-session"
        )
    if mode == "local_db":
        return "Режим локального кэша: импортируйте заявки (flask pls security-import-sql)."
    return "Портал охраны недоступен."


def refresh_security_session(base_url: str, *, cookie_header: str | None = None) -> dict:
    """Обновить сессию к порталу по настроенному режиму (серверный SSO в prod)."""
    mode = resolve_security_auth_mode()
    methods: list[str] = []

    if mode == "negotiate":
        session = _session_with_negotiate(base_url)
        if session:
            save_session_jar(session)
            return {"ok": True, "method": "negotiate", "methods": ["negotiate"], "auth_mode": mode}
        return {
            "ok": False,
            "method": None,
            "methods": ["negotiate"],
            "auth_mode": mode,
            "hint": security_refresh_hint("negotiate"),
        }

    if mode == "cookie":
        session = _new_session()
        if _load_jar(session):
            methods.append("jar")
            if session_authenticated(session, base_url):
                save_session_jar(session)
                return {"ok": True, "method": "jar", "methods": methods, "auth_mode": mode}
        if cookie_header:
            session = _new_session(cookie_header)
            methods.append("env_cookie")
            if session_authenticated(session, base_url):
                save_session_jar(session)
                return {"ok": True, "method": "env_cookie", "methods": methods, "auth_mode": mode}
        return {
            "ok": False,
            "method": None,
            "methods": methods,
            "auth_mode": mode,
            "hint": security_refresh_hint("cookie"),
        }

    if mode == "browser":
        browser_session = _session_from_browser()
        if browser_session:
            save_session_jar(browser_session)
            return {"ok": True, "method": "browser", "methods": ["browser"], "auth_mode": mode}
        return {
            "ok": False,
            "method": None,
            "methods": ["browser"],
            "auth_mode": mode,
            "hint": security_refresh_hint("browser"),
        }

    # local_db / stub — live-сессия не нужна
    return {"ok": False, "method": None, "methods": [], "auth_mode": mode, "hint": security_refresh_hint(mode)}


def get_authenticated_session(base_url: str, *, cookie_header: str | None = None) -> requests.Session | None:
    mode = resolve_security_auth_mode()
    if mode == "negotiate":
        session = _session_with_negotiate(base_url)
        if session:
            save_session_jar(session)
        return session

    info = refresh_security_session(base_url, cookie_header=cookie_header)
    if not info.get("ok"):
        return None
    session = _new_session()
    if _load_jar(session):
        return session
    if mode == "cookie" and cookie_header:
        session = _new_session(cookie_header)
        return session if session_authenticated(session, base_url) else None
    return None
