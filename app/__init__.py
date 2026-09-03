"""Фабрика Flask-приложения портала ПЛС."""
from __future__ import annotations

import os

from flask import Flask

from app.config import config
from app.core.auth import before_request_auth
from app.db import db, migrate


def create_app(config_name: str | None = None) -> Flask:
    if config_name is None:
        config_name = os.environ.get("FLASK_CONFIG") or os.environ.get("FLASK_ENV") or "default"
    if config_name not in config:
        config_name = "default"

    app = Flask(
        __name__,
        template_folder="../frontend/templates",
        static_folder="../frontend/static",
        static_url_path="/static",
    )
    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db)

    # Импорт моделей для Alembic / create_all
    from app.modules import billing  # noqa: F401
    from app.modules.billing import models as billing_models  # noqa: F401
    from app.modules.processes import schema_resolver  # noqa: F401
    from app.modules.reference import models  # noqa: F401
    from app.modules.uss import models as uss_models  # noqa: F401

    from app.api.admin import bp as admin_bp
    from app.api.auth import bp as auth_bp
    from app.api.health import bp as health_bp
    from app.api.maintenance import bp as maintenance_bp
    from app.modules.billing.api import bp as billing_bp
    from app.modules.processes.api import bp as process_bp
    from app.modules.reference.api import bp as ref_bp
    from app.modules.uss.api import bp as uss_bp
    from app.web.routes import bp as web_bp
    from app.web.stub_routes import bp as stub_web_bp

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(maintenance_bp)
    app.register_blueprint(ref_bp)
    app.register_blueprint(process_bp)
    app.register_blueprint(uss_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(web_bp)
    app.register_blueprint(stub_web_bp)

    @app.before_request
    def _auth():
        return before_request_auth()

    from app.cli import register_cli

    register_cli(app)

    @app.context_processor
    def _inject_globals():
        return {"pls_build": app.config.get("PLS_BUILD_ID", "dev")}

    @app.after_request
    def _no_cache_html(response):
        if app.config.get("DEBUG") and response.content_type and "text/html" in response.content_type:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
        return response

    return app
