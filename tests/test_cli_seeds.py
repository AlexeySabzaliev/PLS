"""Тесты CLI и миграций."""
import os
import tempfile

import pytest
from flask_migrate import upgrade

from app import create_app
from app.db import db
from app.modules.reference.models import Client, Role, User
from app.seeds.bootstrap import seed_demo, seed_reference


@pytest.fixture
def migrated_app():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    uri = "sqlite:///" + path.replace("\\", "/")
    os.environ["DATABASE_URL"] = uri
    application = create_app("development")
    application.config["SQLALCHEMY_DATABASE_URI"] = uri
    with application.app_context():
        upgrade()
        yield application
    os.environ.pop("DATABASE_URL", None)
    try:
        os.remove(path)
    except OSError:
        pass


def test_migration_and_seed_reference(migrated_app):
    with migrated_app.app_context():
        seed_reference()
        assert Role.query.filter_by(code="admin").first() is not None
        assert Role.query.count() >= 6

        # Идемпотентность
        seed_reference()
        assert Role.query.filter_by(code="admin").count() == 1


def test_seed_demo_creates_contract(migrated_app):
    with migrated_app.app_context():
        seed_demo()
        assert Client.query.filter_by(name="Аристон").first() is not None
        assert User.query.filter_by(email="admin@bsh-ru.ru").first() is not None
