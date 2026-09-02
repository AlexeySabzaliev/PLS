"""Alembic environment."""
from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from flask import current_app

config = context.config
if config.config_file_name is not None and os.path.isfile(config.config_file_name):
    fileConfig(config.config_file_name)


def get_metadata():
    from app.db import db
    return db.metadata


def run_migrations_offline() -> None:
    url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=get_metadata(), literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from app import create_app
    from app.db import db

    app = create_app(os.environ.get("FLASK_CONFIG", "development"))
    with app.app_context():
        connectable = db.engine
        with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=db.metadata)
            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
