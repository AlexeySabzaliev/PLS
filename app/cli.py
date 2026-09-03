"""Flask CLI: миграции и сиды."""
from __future__ import annotations

from pathlib import Path

import click
from flask import Flask, current_app
from flask.cli import with_appcontext

from app.db import db
from app.seeds import seed_admin, seed_demo, seed_reference
from app.seeds.cleanup_reference_real import cleanup_reference_real
from app.seeds.fix_ariston_canonical import fix_ariston_canonical
from app.seeds.import_from_billings import import_from_billings
from app.seeds.import_security_from_billings import import_security_from_billings
from app.seeds.import_security_sql_dump import import_security_sql_dump
from app.seeds.import_security_from_portal import import_security_from_portal
from app.seeds.import_staff_from_billings import import_staff_from_billings
from app.seeds.db_vacuum import vacuum_orphans
from app.seeds.ariston_august import seed_ariston_strelna_august
from app.services.db_backup import (
    BackupError,
    create_backup,
    default_retention_keep,
    format_size,
    prune_backups,
    restore_backup,
)


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

    @pls_group.command("cleanup-reference-real")
    @click.option("--dry-run", is_flag=True, help="Только показать план")
    @click.option("--force", is_flag=True, help="Выполнить даже при PLS_FREEZE_REFERENCE=1")
    @click.option("--docx-dir", type=click.Path(exists=True, file_okay=False), default=None, help="Папка с DOCX ДС")
    @click.option("--skip-backup", is_flag=True, help="Не создавать бэкап перед очисткой")
    @with_appcontext
    def cmd_cleanup_reference_real(dry_run: bool, force: bool, docx_dir: str | None, skip_backup: bool):
        """Оставить только Аристон и Гауф; ДС из реальных DOCX."""
        report = cleanup_reference_real(
            dry_run=dry_run,
            force=force,
            docx_dir=Path(docx_dir) if docx_dir else None,
            skip_backup=skip_backup,
        )
        for line in report.actions:
            click.echo(line)

    @pls_group.command("fix-ariston-canonical")
    @click.option("--dry-run", is_flag=True, help="Только показать действия, без commit")
    @click.option("--no-ds5", is_flag=True, help="Не создавать историческое ДС-5")
    @click.option("--force", is_flag=True, help="Выполнить даже при PLS_FREEZE_REFERENCE=1")
    @with_appcontext
    def cmd_fix_ariston_canonical(dry_run: bool, no_ds5: bool, force: bool):
        """Канонические данные Аристон: клиент, склад, договор, ДС-6/2024."""
        report = fix_ariston_canonical(dry_run=dry_run, with_ds5=not no_ds5, force=force)
        for line in report.actions:
            click.echo(line)

    @pls_group.command("import-from-billings")
    @click.option("--dry-run", is_flag=True, help="Показать план без записи в БД")
    @click.option(
        "--only",
        type=click.Choice(["reference", "shifts", "all"]),
        default="all",
        help="Что импортировать",
    )
    @click.option("--force", is_flag=True, help="Обновлять существующие записи (по умолчанию — только вставка)")
    @with_appcontext
    def cmd_import_from_billings(dry_run: bool, only: str, force: bool):
        """Одноразовый импорт справочников и смен из Billings (BILLINGS_DATABASE_URL)."""
        try:
            report = import_from_billings(dry_run=dry_run, only=only, skip_existing=not force)
        except RuntimeError as exc:
            raise click.ClickException(str(exc)) from exc
        for line in report.actions:
            click.echo(line)

    @pls_group.command("db-vacuum")
    @click.option("--dry-run", is_flag=True, default=True, help="Только показать (по умолчанию)")
    @click.option("--yes", is_flag=True, help="Выполнить удаление сирот")
    @with_appcontext
    def cmd_db_vacuum(dry_run: bool, yes: bool):
        """Очистка сирот: ставки без договора/ДС, неактивные клиенты без договоров."""
        report = vacuum_orphans(dry_run=not yes)
        for line in report.actions:
            click.echo(line)

    @pls_group.command("security-import-billings")
    @click.option("--since", default=None, help="Импортировать заявки с visit_date_to >= YYYY-MM-DD")
    @with_appcontext
    def cmd_security_import_billings(since: str | None):
        """Копия security_admission_form из Billings → локальная SQLite (резерв для синхронизации)."""
        from datetime import date as date_cls

        since_date = date_cls.fromisoformat(since) if since else None
        try:
            result = import_security_from_billings(since=since_date, verbose=True)
        except RuntimeError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(f"Готово: {result['imported']} заявок. Для чтения: SECURITY_USE_LOCAL_DB=1")

    @pls_group.command("security-import-sql")
    @click.argument(
        "sql_file",
        type=click.Path(exists=True, dir_okay=False, path_type=Path),
        default=Path("tests/fixtures/security/admission_form_mssql.sql"),
    )
    @click.option("--all-rows", is_flag=True, help="Импортировать все строки, не только ТС+approved")
    @with_appcontext
    def cmd_security_import_sql(sql_file: Path, all_rows: bool):
        """Дамп IT (admission_form MSSQL) → локальная security_admission_form (dev/тест)."""
        try:
            result = import_security_sql_dump(
                sql_file,
                only_approved_vehicles=not all_rows,
                verbose=True,
            )
        except (OSError, RuntimeError) as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(
            f"Готово: {result['imported']} заявок с ТС (всего в дампе: {result['parsed']}). "
            "Включите SECURITY_USE_LOCAL_DB=1 в .env"
        )

    @pls_group.command("security-fetch-portal")
    @click.option("--place", "visit_place", default="Склад ГП", show_default=True, help="Место визита")
    @click.option("--from", "day_from", default="2026-09-01", show_default=True, help="Начало периода YYYY-MM-DD")
    @click.option("--to", "day_to", default="2026-09-30", show_default=True, help="Конец периода YYYY-MM-DD")
    @with_appcontext
    def cmd_security_fetch_portal(visit_place: str, day_from: str, day_to: str):
        """Скачать заявки с портала → локальная security_admission_form (Аристон + Гауф)."""
        from datetime import date as date_cls

        try:
            result = import_security_from_portal(
                visit_place=visit_place,
                day_from=date_cls.fromisoformat(day_from),
                day_to=date_cls.fromisoformat(day_to),
            )
        except RuntimeError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(
            f"Готово: с портала {result['fetched']} заявок, сохранено {result.get('saved', 0)}. "
            "Режим чтения: SECURITY_USE_LOCAL_DB=1"
        )

    @pls_group.command("security-refresh-session")
    @with_appcontext
    def cmd_security_refresh_session():
        """Обновить SSO-cookie портала охраны (Yandex/Edge → instance/security_session.txt)."""
        import os

        from app.modules.uss.services.security_session import refresh_security_session

        base = os.getenv("SECURITY_BASE_URL", "https://security.bsh-ru.ru").rstrip("/")
        cookie = os.getenv("SECURITY_API_COOKIE", "").strip() or None
        if cookie and cookie.startswith("eyJ") and "=" not in cookie.split(";")[0]:
            cookie = None
        info = refresh_security_session(base, cookie_header=cookie)
        if info.get("ok"):
            click.echo(f"Сессия обновлена ({info.get('method')}).")
        else:
            raise click.ClickException(info.get("hint") or "Не удалось получить SSO-сессию.")

    @pls_group.command("import-staff-from-billings")
    @click.option("--warehouse", "warehouse_code", default=None, help="Только склад с этим code")
    @click.option("--dry-run", is_flag=True, help="Показать план без записи в БД")
    @click.option("--force", is_flag=True, help="Импортировать даже если в ПЛС уже есть позиции")
    @with_appcontext
    def cmd_import_staff_from_billings(warehouse_code: str | None, dry_run: bool, force: bool):
        """Импорт штатных позиций ФОТ из Billings (BILLINGS_DATABASE_URL)."""
        try:
            report = import_staff_from_billings(
                warehouse_code=warehouse_code,
                dry_run=dry_run,
                skip_existing=not force,
            )
        except RuntimeError as exc:
            raise click.ClickException(str(exc)) from exc
        for line in report.actions:
            click.echo(line)

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

    @pls_group.command("backup")
    @click.option(
        "--retention",
        type=int,
        default=None,
        help="Оставить не более N последних бэкапов (или PLS_BACKUP_RETENTION из .env)",
    )
    @with_appcontext
    def cmd_backup(retention: int | None):
        """Создать резервную копию БД (pg_dump или SQLite dump)."""
        try:
            path, size = create_backup()
        except BackupError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(f"Резервная копия создана: {path}")
        click.echo(f"Размер: {format_size(size)}")

        keep = retention if retention is not None else default_retention_keep()
        if keep:
            removed = prune_backups(keep=keep)
            if removed:
                click.echo(f"Удалено старых копий: {removed} (храним {keep})")

    @pls_group.command("restore")
    @click.option("--file", "backup_file", required=True, type=click.Path(exists=True), help="Путь к .sql")
    @click.option("--yes", is_flag=True, help="Без подтверждения (для скриптов)")
    @click.option("--no-safety-backup", is_flag=True, help="Не создавать бэкап перед восстановлением")
    @with_appcontext
    def cmd_restore(backup_file: str, yes: bool, no_safety_backup: bool):
        """Восстановить БД из файла .sql (перед этим создаётся бэкап текущего состояния)."""
        path = Path(backup_file)
        if not yes:
            click.confirm(
                f"Восстановить БД из {path}? Текущие данные будут перезаписаны.",
                abort=True,
            )
        try:
            safety, size = restore_backup(path, safety_backup=not no_safety_backup)
        except BackupError as exc:
            raise click.ClickException(str(exc)) from exc
        if safety:
            click.echo(f"Сохранён бэкап до восстановления: {safety}")
        click.echo(f"БД восстановлена из {path} ({format_size(size)})")
