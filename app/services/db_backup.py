"""Резервное копирование и восстановление БД ПЛС (PostgreSQL или SQLite)."""
from __future__ import annotations

import os
import sqlite3
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import unquote, urlparse

from flask import current_app
from sqlalchemy.engine import make_url

from app.db import db


class BackupError(RuntimeError):
    """Ошибка резервного копирования или восстановления."""


def _project_root() -> Path:
    return Path(current_app.root_path).parent


def backup_directory() -> Path:
    """Каталог бэкапов: PLS_BACKUP_DIR или backups/ в корне проекта."""
    raw = (os.environ.get("PLS_BACKUP_DIR") or "backups").strip()
    path = Path(raw)
    if not path.is_absolute():
        path = _project_root() / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def _database_uri() -> str:
    return str(current_app.config.get("SQLALCHEMY_DATABASE_URI") or "")


def _sqlite_path(uri: str) -> Path:
    if not uri.startswith("sqlite:"):
        raise BackupError("Ожидался URI SQLite")
    database = make_url(uri).database
    if not database or database == ":memory:":
        raise BackupError("Резервная копия in-memory SQLite недоступна")
    return Path(database)


def _postgres_parts(uri: str) -> dict[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme not in ("postgresql", "postgres"):
        raise BackupError(f"Неподдерживаемая схема БД: {parsed.scheme or '(пусто)'}")
    dbname = (parsed.path or "").lstrip("/")
    if not dbname:
        raise BackupError("В DATABASE_URL не указано имя базы")
    return {
        "host": parsed.hostname or "localhost",
        "port": str(parsed.port or 5432),
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "dbname": dbname,
    }


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def _run(cmd: list[str], *, env: dict[str, str] | None = None) -> None:
    try:
        subprocess.run(cmd, check=True, env=env, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise BackupError(f"Не найдена утилита: {cmd[0]}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise BackupError(detail or f"Команда завершилась с кодом {exc.returncode}") from exc


def create_backup() -> tuple[Path, int]:
    """Создать дамп БД. Возвращает (путь к файлу, размер в байтах)."""
    uri = _database_uri()
    out_dir = backup_directory()
    stamp = _timestamp()

    if uri.startswith("sqlite:"):
        src = _sqlite_path(uri)
        if not src.is_file():
            raise BackupError(f"Файл SQLite не найден: {src}")
        dest = out_dir / f"pls_{stamp}.sql"
        with sqlite3.connect(src) as conn, dest.open("w", encoding="utf-8", newline="\n") as out:
            for line in conn.iterdump():
                out.write(f"{line}\n")
        size = dest.stat().st_size
        return dest, size

    parts = _postgres_parts(uri)
    dest = out_dir / f"pls_{stamp}.sql"
    env = os.environ.copy()
    if parts["password"]:
        env["PGPASSWORD"] = parts["password"]
    _run(
        [
            "pg_dump",
            "--no-owner",
            "--no-acl",
            "-h",
            parts["host"],
            "-p",
            parts["port"],
            "-U",
            parts["user"],
            "-d",
            parts["dbname"],
            "-f",
            str(dest),
        ],
        env=env,
    )
    size = dest.stat().st_size
    return dest, size


def restore_backup(path: Path, *, safety_backup: bool = True) -> tuple[Path | None, int]:
    """Восстановить БД из файла. При safety_backup создаётся копия перед восстановлением."""
    backup_path = path.resolve()
    if not backup_path.is_file():
        raise BackupError(f"Файл бэкапа не найден: {backup_path}")

    safety: Path | None = None
    if safety_backup:
        safety, _ = create_backup()

    uri = _database_uri()
    if uri.startswith("sqlite:"):
        target = _sqlite_path(uri)
        target.parent.mkdir(parents=True, exist_ok=True)
        db.session.remove()
        db.engine.dispose()
        sql = backup_path.read_text(encoding="utf-8")
        with sqlite3.connect(target) as conn:
            conn.execute("PRAGMA foreign_keys=OFF")
            tables = [
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
            ]
            for name in tables:
                conn.execute(f'DROP TABLE IF EXISTS "{name}"')
            conn.executescript(sql)
        db.engine.dispose()
        return safety, backup_path.stat().st_size

    parts = _postgres_parts(uri)
    env = os.environ.copy()
    if parts["password"]:
        env["PGPASSWORD"] = parts["password"]
    _run(
        [
            "psql",
            "-h",
            parts["host"],
            "-p",
            parts["port"],
            "-U",
            parts["user"],
            "-d",
            parts["dbname"],
            "-v",
            "ON_ERROR_STOP=1",
            "--single-transaction",
            "-f",
            str(backup_path),
        ],
        env=env,
    )
    return safety, backup_path.stat().st_size


def list_backups() -> list[Path]:
    """Список файлов pls_*.sql в каталоге бэкапов (новые первыми)."""
    return sorted(
        backup_directory().glob("pls_*.sql"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def prune_backups(*, keep: int | None = None, max_age_days: int | None = None) -> int:
    """Удалить старые бэкапы. keep — оставить N последних; max_age_days — старше N дней."""
    files = list_backups()
    to_remove: set[Path] = set()

    if keep is not None and keep > 0 and len(files) > keep:
        to_remove.update(files[keep:])

    if max_age_days is not None and max_age_days > 0:
        cutoff = datetime.now() - timedelta(days=max_age_days)
        for path in files:
            if datetime.fromtimestamp(path.stat().st_mtime) < cutoff:
                to_remove.add(path)

    for path in to_remove:
        path.unlink(missing_ok=True)
    return len(to_remove)


def default_retention_keep() -> int | None:
    """PLS_BACKUP_RETENTION — сколько последних копий хранить (0 = не чистить)."""
    raw = (os.environ.get("PLS_BACKUP_RETENTION") or "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def format_size(size: int) -> str:
    if size < 1024:
        return f"{size} Б"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} КБ"
    return f"{size / (1024 * 1024):.2f} МБ"
