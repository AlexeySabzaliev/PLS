"""Управление пользователями и ролями."""
from app.core.user_admin import create_user, list_users, sync_user_roles, update_user
from app.modules.reference.models import Role, User, UserRole, Warehouse


def test_create_user_with_roles(app):
    with app.app_context():
        from app.modules.reference.models import Warehouse

        wh = Warehouse.query.first()
        wh_id = wh.id
        user, err = create_user(
            email="new.user@bsh-ru.ru",
            full_name="Новый Пользователь",
            role_codes=["transport_logistics"],
            warehouse_ids=[wh_id],
        )
    assert err is None
    assert user["email"] == "new.user@bsh-ru.ru"
    assert "transport_logistics" in user["role_codes"]
    assert wh_id in user["warehouse_ids"]


def test_list_users_admin_only(auth_client, client):
    auth_client("transport@test.local", "test")
    resp = client.get("/api/admin/users")
    assert resp.status_code == 403

    auth_client("admin@test.local", "admin")
    resp2 = client.get("/api/admin/users")
    assert resp2.status_code == 200
    assert "items" in resp2.json
    assert "roles" in resp2.json


def test_update_user_roles(app):
    with app.app_context():
        user, err = create_user(
            email="roles.test@bsh-ru.ru",
            role_codes=["warehouse_logistics"],
        )
        assert err is None
        role_tl = Role.query.filter_by(code="transport_logistics").first()
        assert role_tl

        updated, err2 = update_user(
            user["id"],
            role_codes=["transport_logistics", "warehouse_logistics"],
        )
        assert err2 is None
        assert set(updated["role_codes"]) == {"transport_logistics", "warehouse_logistics"}


def test_sync_user_roles_replaces(app):
    with app.app_context():
        user = User(email="sync.roles@bsh-ru.ru", is_active=True)
        from app.db import db
        db.session.add(user)
        db.session.flush()
        sync_user_roles(user.id, ["transport_logistics", "warehouse_logistics"])
        sync_user_roles(user.id, ["commercial_logistics"])
        codes = {r.role.code for r in UserRole.query.filter_by(user_id=user.id).all()}
        assert codes == {"commercial_logistics"}


def test_role_catalog_in_meta(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.get("/api/admin/users/meta")
    assert resp.status_code == 200
    roles = resp.json["roles"]
    codes = {r["code"] for r in roles}
    assert "transport_logistics" in codes
    assert "ved_specialist" in codes
    assert "reports_viewer" in codes
    assert "supervisor" not in codes
    assert all("modules" not in r for r in roles)
