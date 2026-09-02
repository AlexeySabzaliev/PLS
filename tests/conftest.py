import os
import tempfile

import pytest
from flask_migrate import upgrade

from app import create_app
from app.db import db
from app.seeds.bootstrap import seed_test_fixtures


@pytest.fixture
def migrated_app():
    """Временная БД с alembic upgrade (для сидов и биллинга)."""
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


@pytest.fixture
def app():
    application = create_app("testing")
    with application.app_context():
        db.create_all()
        seed_test_fixtures()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    def _login(email, password):
        resp = client.post("/api/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200
        return client

    return _login
