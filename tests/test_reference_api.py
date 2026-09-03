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


def test_reference_product_types_toggle(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.get("/api/reference/product_types")
    assert resp.status_code == 200
    assert resp.json["items"]
    row = resp.json["items"][0]
    assert "is_active" in row
    new_val = not row["is_active"]

    update = client.put(
        f"/api/reference/product_types/{row['id']}",
        json={"is_active": new_val},
    )
    assert update.status_code == 200
    assert update.json["is_active"] is new_val


def test_reference_lookups(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.get("/api/reference/lookups")
    assert resp.status_code == 200
    assert "clients" in resp.json
    assert "contracts" in resp.json
    assert resp.json["clients"][0]["label"]


def test_reference_meta_hides_staff(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.get("/api/reference/meta")
    codes = [c["code"] for c in resp.json["catalogs"]]
    assert "staff" not in codes
    assert "roles" not in codes
    assert "vehicles" not in codes
    pt = next(c for c in resp.json["catalogs"] if c["code"] == "product_types")
    assert pt["read_only"] is False
    assert "lookups" in resp.json
    assert "clients" in resp.json["lookups"]


def test_reference_vehicles_catalog_removed(auth_client, client):
    """Справочник госномеров ТС убран — номера вводятся вручную в смене."""
    auth_client("admin@test.local", "admin")
    resp = client.get("/api/reference/vehicles")
    assert resp.status_code == 404


def test_tariff_rules_bulk_delete_by_amendment(auth_client, client):
    auth_client("admin@test.local", "admin")
    tariffs = client.get("/api/reference/tariff_rules").json["items"]
    assert tariffs
    amendment_id = tariffs[0]["amendment_id"]
    before = len([t for t in tariffs if t["amendment_id"] == amendment_id])
    assert before > 0

    resp = client.delete(f"/api/reference/tariff_rules/bulk?amendment_id={amendment_id}")
    assert resp.status_code == 200
    assert resp.json["deleted"] == before

    after = client.get("/api/reference/tariff_rules").json["items"]
    assert not [t for t in after if t["amendment_id"] == amendment_id]


def test_tariff_rules_bulk_delete_by_client(auth_client, client, app):
    auth_client("admin@test.local", "admin")
    from app.modules.reference.models import Client

    with app.app_context():
        client_row = Client.query.filter_by(name="Аристон").first()
        client_id = client_row.id

    before = client.get("/api/reference/tariff_rules").json["items"]
    assert before

    resp = client.delete(f"/api/reference/tariff_rules/bulk?client_id={client_id}")
    assert resp.status_code == 200
    assert resp.json["deleted"] == len(before)

    after = client.get("/api/reference/tariff_rules").json["items"]
    assert not after


def test_tariff_rules_bulk_delete_unlinked(auth_client, client, app):
    auth_client("admin@test.local", "admin")
    from datetime import date

    from app.db import db
    from app.modules.reference.models import Contract, TariffRule

    with app.app_context():
        contract = Contract.query.first()
        assert contract
        contract_id = contract.id
        orphan = TariffRule(
            contract_id=contract_id,
            amendment_id=999999,
            billing_line_code="orphan_test",
            name="Тест без ДС",
            valid_from=date(2026, 1, 1),
        )
        db.session.add(orphan)
        db.session.commit()
        orphan_id = orphan.id

    resp = client.delete(f"/api/reference/tariff_rules/bulk?contract_id={contract_id}&unlinked=1")
    assert resp.status_code == 200
    assert resp.json["deleted"] >= 1

    after = client.get("/api/reference/tariff_rules").json["items"]
    assert not [t for t in after if t["id"] == orphan_id]


def test_amendment_lookup_includes_ds_number(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.get("/api/reference/lookups?all=1")
    am = resp.json["amendments"][0]
    assert "number" in am
    assert am["label"].startswith("ДС №")


def test_tariff_rules_bulk_delete_missing_params(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.delete("/api/reference/tariff_rules/bulk")
    assert resp.status_code == 400
    assert resp.json.get("error") == "amendment_id_client_id_or_contract_unlinked_required"


def test_tariff_rules_require_amendment(auth_client, client, app):
    auth_client("admin@test.local", "admin")
    from datetime import date

    from app.modules.reference.models import Contract

    with app.app_context():
        contract = Contract.query.first()
        assert contract

    resp = client.post(
        "/api/reference/tariff_rules",
        json={
            "contract_id": contract.id,
            "name": "Тест без ДС",
            "valid_from": date(2026, 1, 1).isoformat(),
        },
    )
    assert resp.status_code == 400
    assert resp.json.get("error") == "amendment_required"


def test_tariff_rules_create_additional_manual(auth_client, client, app):
    """Ручное добавление дополнительной ставки (как inline-строка в UI)."""
    auth_client("admin@test.local", "admin")
    from datetime import date

    from app.modules.reference.models import ContractAmendment, UnitOfMeasure

    with app.app_context():
        am = ContractAmendment.query.first()
        assert am
        unit = UnitOfMeasure.query.filter_by(code="pcs").first()
        assert unit

    payload = {
        "contract_id": am.contract_id,
        "amendment_id": am.id,
        "name": "Подклейка клапанов (тест)",
        "unit_id": unit.id,
        "report_role": "transport_logistics",
        "quantity_source": "manual_daily",
        "valid_from": date(2026, 8, 1).isoformat(),
        "rate_ex_vat": 210.04,
        "is_custom": True,
        "billing_line_code": f"custom_test_manual_{am.id}",
    }
    resp = client.post("/api/reference/tariff_rules", json=payload)
    assert resp.status_code == 201
    body = resp.json
    assert body["billing_line_code"] == payload["billing_line_code"]
    assert body["name"] == payload["name"]
    assert body["is_custom"] is True
    assert body["report_role"] == "transport_logistics"
    assert body["quantity_source"] == "manual_daily"
    assert body["rate_ex_vat"] == 210.04

    client.delete(f"/api/reference/tariff_rules/{body['id']}")


def test_tariff_rules_create_main_without_billing_code(auth_client, client, app):
    """Основная ставка: billing_line_code генерируется на сервере при создании."""
    auth_client("admin@test.local", "admin")
    from datetime import date

    from app.modules.reference.models import ContractAmendment

    with app.app_context():
        am = ContractAmendment.query.first()
        assert am

    resp = client.post(
        "/api/reference/tariff_rules",
        json={
            "amendment_id": am.id,
            "name": "Тест основная ставка",
            "valid_from": date(2026, 1, 1).isoformat(),
            "is_custom": False,
        },
    )
    assert resp.status_code == 201
    assert resp.json["billing_line_code"].startswith("custom_")
    assert resp.json["is_custom"] is False

    client.delete(f"/api/reference/tariff_rules/{resp.json['id']}")


def test_reference_meta_billing_line_choices(auth_client, client):
    """Каталог ставок: billing_line_code с русскими подписями в meta."""
    auth_client("admin@test.local", "admin")
    resp = client.get("/api/reference/meta")
    assert resp.status_code == 200
    tariff = next(c for c in resp.json["catalogs"] if c["code"] == "tariff_rules")
    bl = next(f for f in tariff["field_meta"] if f["field"] == "billing_line_code")
    assert bl["type"] == "select"
    assert bl["choices"]
    codes = {c["value"] for c in bl["choices"]}
    assert "storage_area_fixed" in codes
    assert "manual_m3" in codes
    fixed = next(c for c in bl["choices"] if c["value"] == "storage_area_fixed")
    assert "Хранение на площади (фикс)" in fixed["label"]
    assert "auto_contract_param" in fixed["label"]
    assert fixed.get("unit_code") == "m2"
    assert fixed.get("quantity_source") == "auto_contract_param"


def test_warehouse_partial_update_preserves_security_visit_place(auth_client, client):
    """PUT только изменённых полей не затирает security_visit_place."""
    auth_client("admin@test.local", "admin")
    create = client.post(
        "/api/reference/warehouses",
        json={
            "code": "strelna",
            "name": "Стрельна",
            "security_visit_place": "Склад ГП",
            "is_active": True,
        },
    )
    assert create.status_code == 201
    wid = create.json["id"]

    update = client.put(
        f"/api/reference/warehouses/{wid}",
        json={"name": "Стрельна (обновлено)"},
    )
    assert update.status_code == 200
    assert update.json["name"] == "Стрельна (обновлено)"
    assert update.json["security_visit_place"] == "Склад ГП"

    clear = client.put(
        f"/api/reference/warehouses/{wid}",
        json={"security_visit_place": None},
    )
    assert clear.status_code == 200
    assert clear.json["security_visit_place"] is None
