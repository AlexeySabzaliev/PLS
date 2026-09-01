"""Конфигурация портала ПЛС."""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))
project_root = os.path.abspath(os.path.join(basedir, ".."))


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

    SSO_ENABLED = os.getenv("SSO_ENABLED", "false").lower() in ("1", "true", "yes")
    SSO_MODE = os.getenv("SSO_MODE", "headers").lower()
    SSO_USER_HEADER = os.getenv("SSO_USER_HEADER", "Remote-User")
    SSO_EMAIL_DOMAIN = os.getenv("SSO_EMAIL_DOMAIN", "bsh-ru.ru")
    _sso_pw = os.getenv("SSO_ALLOW_PASSWORD_LOGIN")
    if _sso_pw is None:
        SSO_ALLOW_PASSWORD_LOGIN = not SSO_ENABLED
    else:
        SSO_ALLOW_PASSWORD_LOGIN = _sso_pw.lower() in ("1", "true", "yes")
    SSO_OIDC_ISSUER = os.getenv("SSO_OIDC_ISSUER", "")
    SSO_OIDC_CLIENT_ID = os.getenv("SSO_OIDC_CLIENT_ID", "")
    SSO_OIDC_CLIENT_SECRET = os.getenv("SSO_OIDC_CLIENT_SECRET", "")
    SSO_OIDC_REDIRECT_URI = os.getenv("SSO_OIDC_REDIRECT_URI", "")
    SSO_OIDC_SCOPE = os.getenv("SSO_OIDC_SCOPE", "openid email profile")
    SSO_DEV_IDENTITY = os.getenv("SSO_DEV_IDENTITY", "").strip()

    ARISTON_BILLING_FIXTURES_PATH = os.getenv("ARISTON_BILLING_FIXTURES_PATH", "").strip()


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


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
