"""Тесты резервного копирования БД."""
from __future__ import annotations

import sqlite3

import pytest

from app import create_app
from app.services.db_backup import BackupError, create_backup, prune_backups, restore_backup


@pytest.fixture
def sqlite_backup_ctx(tmp_path, monkeypatch):
    db_file = tmp_path / "pls.db"
    with sqlite3.connect(db_file) as conn:
        conn.execute(
            "CREATE TABLE warehouses ("
            "id INTEGER PRIMARY KEY, code TEXT, name TEXT, security_visit_place TEXT)"
        )
        conn.execute(
            "INSERT INTO warehouses (code, name, security_visit_place) VALUES (?, ?, ?)",
            ("strelna", "Стрельна", "Склад ГП"),
        )

    uri = "sqlite:///" + db_file.as_posix()
    backup_dir = tmp_path / "backups"
    monkeypatch.setenv("PLS_BACKUP_DIR", str(backup_dir))
    monkeypatch.setattr("app.services.db_backup._database_uri", lambda: uri)

    application = create_app("testing")
    ctx = application.app_context()
    ctx.push()
    try:
        yield db_file, backup_dir
    finally:
        ctx.pop()


def test_backup_creates_sqlite_dump(sqlite_backup_ctx):
    path, size = create_backup()
    assert path.is_file()
    assert size > 0
    assert path.suffix == ".sql"
    text = path.read_text(encoding="utf-8")
    assert "warehouses" in text.lower()
    assert "Склад ГП" in text


def test_restore_sqlite_from_backup(sqlite_backup_ctx):
    db_file, _ = sqlite_backup_ctx
    backup_path, _ = create_backup()

    with sqlite3.connect(db_file) as conn:
        conn.execute(
            "UPDATE warehouses SET security_visit_place = NULL, name = 'Изменено' WHERE code = 'strelna'"
        )

    restore_backup(backup_path, safety_backup=False)

    with sqlite3.connect(db_file) as conn:
        row = conn.execute(
            "SELECT name, security_visit_place FROM warehouses WHERE code = 'strelna'"
        ).fetchone()
    assert row == ("Стрельна", "Склад ГП")


def test_backup_memory_sqlite_raises(app):
    with app.app_context():
        with pytest.raises(BackupError, match="in-memory"):
            create_backup()


def test_prune_backups_keeps_latest(sqlite_backup_ctx):
    for _ in range(3):
        create_backup()
    removed = prune_backups(keep=2)
    assert removed == 1
    from app.services.db_backup import list_backups

    assert len(list_backups()) == 2
