"""Конфигурация портала ПЛС."""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))
project_root = os.path.abspath(os.path.join(basedir, ".."))


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in ("1", "true", "yes")


def resolve_database_uri(uri: str | None = None) -> str:
    raw = (uri or os.environ.get("DATABASE_URL") or "").strip()
    if not raw:
        raw = "sqlite:///instance/pls.db"
    if not raw.startswith("sqlite:///"):
        return raw
    path = raw[len("sqlite:///") :]
    if len(path) >= 2 and path[1] == ":":
        abs_path = path.replace("/", os.sep)
    elif os.path.isabs(path):
        abs_path = path
    else:
        abs_path = os.path.normpath(os.path.join(project_root, path))
    parent = os.path.dirname(abs_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    return "sqlite:///" + abs_path.replace("\\", "/")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = resolve_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_AS_ASCII = False

    APP_NAME = os.environ.get("APP_NAME", "Портал логистических сервисов")
    APP_SHORT = os.environ.get("APP_SHORT", "ПЛС")
    MODULE_UZNT_NAME = os.environ.get("MODULE_UZNT_NAME", "УЗнТ")
    MODULE_USS_NAME = os.environ.get("MODULE_USS_NAME", "УСС")
    # Версия статики/HTML — меняйте при правках фронта (сброс кэша браузера)
    PLS_BUILD_ID = os.environ.get("PLS_BUILD_ID", "20260904p")

    _is_dev = os.getenv("FLASK_ENV", "development").lower() != "production"
    _sso_enabled_env = os.getenv("SSO_ENABLED")
    if _sso_enabled_env is None:
        SSO_ENABLED = sys.platform == "win32" and _is_dev
    else:
        SSO_ENABLED = _sso_enabled_env.lower() in ("1", "true", "yes")
    _sso_mode_env = os.getenv("SSO_MODE")
    if _sso_mode_env:
        SSO_MODE = _sso_mode_env.lower()
    elif not _is_dev:
        SSO_MODE = "headers"
    elif sys.platform == "win32":
        SSO_MODE = "auto"
    else:
        SSO_MODE = "headers"
    SSO_USER_HEADER = os.getenv("SSO_USER_HEADER", "Remote-User")
    SSO_EMAIL_DOMAIN = os.getenv("SSO_EMAIL_DOMAIN", "bsh-ru.ru")
    # Fallback GetUserNameExW — только локальная разработка; на сервере под службой бесполезен
    _win_fb = os.getenv("SSO_ALLOW_WINDOWS_FALLBACK")
    if _win_fb is None:
        SSO_ALLOW_WINDOWS_FALLBACK = _is_dev
    else:
        SSO_ALLOW_WINDOWS_FALLBACK = _win_fb.lower() in ("1", "true", "yes")
    _sso_pw = os.getenv("SSO_ALLOW_PASSWORD_LOGIN")
    if _sso_pw is None:
        SSO_ALLOW_PASSWORD_LOGIN = True
    else:
        SSO_ALLOW_PASSWORD_LOGIN = _sso_pw.lower() in ("1", "true", "yes")
    SSO_OIDC_ISSUER = os.getenv("SSO_OIDC_ISSUER", "")
    SSO_OIDC_CLIENT_ID = os.getenv("SSO_OIDC_CLIENT_ID", "")
    SSO_OIDC_CLIENT_SECRET = os.getenv("SSO_OIDC_CLIENT_SECRET", "")
    SSO_OIDC_REDIRECT_URI = os.getenv("SSO_OIDC_REDIRECT_URI", "")
    SSO_OIDC_SCOPE = os.getenv("SSO_OIDC_SCOPE", "openid email profile")
    SSO_DEV_IDENTITY = os.getenv("SSO_DEV_IDENTITY", "").strip()

    PASSWORD_MIN_LENGTH = max(6, int(os.getenv("PASSWORD_MIN_LENGTH", "8")))

    PLS_REGISTRATION_ENABLED = _env_bool("PLS_REGISTRATION_ENABLED", True)
    PLS_REGISTRATION_EMAIL_DOMAIN = (
        os.getenv("PLS_REGISTRATION_EMAIL_DOMAIN") or os.getenv("SSO_EMAIL_DOMAIN") or "bsh-ru.ru"
    ).strip().lstrip("@").lower()

    # Dev-заглушки интеграций (игнорируются в production)
    PLS_SSO_STUB = _env_bool("PLS_SSO_STUB")
    SECURITY_PORTAL_STUB = _env_bool("SECURITY_PORTAL_STUB")

    ARISTON_BILLING_FIXTURES_PATH = os.getenv("ARISTON_BILLING_FIXTURES_PATH", "").strip()

    # После одноразового импорта из Billings — блокировать перезапись справочников сидами
    PLS_FREEZE_REFERENCE = _env_bool("PLS_FREEZE_REFERENCE")
    BILLINGS_DATABASE_URL = os.getenv("BILLINGS_DATABASE_URL", "").strip()


def _apply_dev_stub_overrides(cfg: type[Config]) -> None:
    """Включить SSO/охрану в dev без prod-конфигурации."""
    if os.getenv("FLASK_ENV", "development").lower() == "production":
        return
    if cfg.PLS_SSO_STUB:
        cfg.SSO_ENABLED = True
        if not cfg.SSO_DEV_IDENTITY:
            cfg.SSO_DEV_IDENTITY = (
                os.getenv("PLS_ADMIN_EMAIL", "admin@bsh-ru.ru").strip() or "admin@bsh-ru.ru"
            )
    if cfg.SECURITY_PORTAL_STUB:
        os.environ.setdefault("SECURITY_PORTAL_STUB", "1")


_apply_dev_stub_overrides(Config)


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SSO_ENABLED = False
    SSO_ALLOW_PASSWORD_LOGIN = True
    # Тесты не должны наследовать PLS_FREEZE_REFERENCE из .env prod/dev
    PLS_FREEZE_REFERENCE = False
    PLS_REGISTRATION_EMAIL_DOMAIN = ""


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
