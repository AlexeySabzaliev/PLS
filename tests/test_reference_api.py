"""Тесты CRUD API справочников."""


def test_reference_meta(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.get("/api/reference/meta")
    assert resp.status_code == 200
    codes = [c["code"] for c in resp.json["catalogs"]]
    assert "clients" in codes
    assert "tariff_rules" in codes


def test_reference_clients_crud(auth_client, client):
    auth_client("admin@test.local", "admin")
    create = client.post(
        "/api/reference/clients",
        json={"name": "Тест Клиент", "is_active": True},
    )
    assert create.status_code == 201
    cid = create.json["id"]

    update = client.put(
        f"/api/reference/clients/{cid}",
        json={"name": "Тест Клиент 2", "is_active": False},
    )
    assert update.status_code == 200
    assert update.json["name"] == "Тест Клиент 2"
    assert update.json["is_active"] is False

    delete = client.delete(f"/api/reference/clients/{cid}")
    assert delete.status_code == 200
    assert delete.json["deleted"] is True


def test_reference_forbidden_for_transport(auth_client, client):
    auth_client("transport@test.local", "test")
    resp = client.get("/api/reference/clients")
    assert resp.status_code == 403


def test_reference_units_list(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.get("/api/reference/units")
    assert resp.status_code == 200
    assert len(resp.json["items"]) >= 1


def test_reference_vehicle_types_crud(auth_client, client):
    auth_client("admin@test.local", "admin")
    create = client.post(
        "/api/reference/vehicle_types",
        json={
            "code": "test_van",
            "name": "Тестовый фургон",
            "sort_order": 500,
            "dimensions_label": "5,0×2,0×2,0",
        },
    )
    assert create.status_code == 201
    vid = create.json["id"]
    assert create.json["dimensions_label"] == "5,0×2,0×2,0"

    update = client.put(
        f"/api/reference/vehicle_types/{vid}",
        json={"dimensions_label": "5,1×2,1×2,1"},
    )
    assert update.status_code == 200
    assert update.json["dimensions_label"] == "5,1×2,1×2,1"

    delete = client.delete(f"/api/reference/vehicle_types/{vid}")
    assert delete.status_code == 200
