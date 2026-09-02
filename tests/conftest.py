import pytest

from app import create_app
from app.db import db
from app.seeds.bootstrap import seed_test_fixtures


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
