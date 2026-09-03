"""Обзор ДС по складам."""
from app.modules.reference.amendments_overview import amendments_overview


def test_amendments_overview_admin(app):
    with app.app_context():
        user = {"is_admin": True, "warehouse_ids": []}
        data = amendments_overview(user)
    assert isinstance(data, list)
    if data:
        wh = data[0]
        assert "warehouse_name" in wh
        assert "clients" in wh
        if wh["clients"]:
            cl = wh["clients"][0]
            assert "amendments" in cl
            assert isinstance(cl["amendments"], list)


def test_amendments_overview_api(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.get("/api/reference/amendments-overview")
    assert resp.status_code == 200
    assert isinstance(resp.json, list)
