"""Flask CLI: миграции и сиды."""
from __future__ import annotations

import click
from flask import Flask, current_app
from flask.cli import with_appcontext

from app.db import db
from app.seeds import seed_admin, seed_demo, seed_reference
from app.seeds.ariston_august import seed_ariston_strelna_august


def register_cli(app: Flask) -> None:
    @app.cli.group("pls")
    def pls_group():
        """Команды ПЛС: БД и демо-данные."""

    @pls_group.command("init-db")
    @click.option("--demo", is_flag=True, help="Добавить демо-контракт и операции")
    @with_appcontext
    def init_db(demo: bool):
        """flask db upgrade + справочники + admin (+ demo)."""
        from flask_migrate import upgrade

        upgrade()
        seed_reference(verbose=True)
        seed_admin(verbose=True)
        if demo:
            seed_demo(verbose=True)
        click.echo("БД инициализирована.")

    @pls_group.command("seed-reference")
    @with_appcontext
    def cmd_seed_reference():
        """Справочники и роли."""
        seed_reference(verbose=True)

    @pls_group.command("seed-admin")
    @with_appcontext
    def cmd_seed_admin():
        """Пользователи admin и transport."""
        seed_admin(verbose=True)

    @pls_group.command("seed-demo")
    @with_appcontext
    def cmd_seed_demo():
        """Демо: Аристон / Стрельна / август 2026."""
        seed_demo(verbose=True)

    @pls_group.command("seed-ariston-august")
    @with_appcontext
    def cmd_seed_ariston_august():
        """Импорт августа Аристон (Стрельна) из Excel Billings."""
        seed_admin(verbose=False)
        seed_ariston_strelna_august(verbose=True)

    @pls_group.command("db-check")
    @with_appcontext
    def db_check():
        """Проверка подключения к БД."""
        db.session.execute(db.text("SELECT 1"))
        uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
        safe = uri.split("@")[-1] if "@" in uri else uri
        click.echo(f"OK: {safe}")
