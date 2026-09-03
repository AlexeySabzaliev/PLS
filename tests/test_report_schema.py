"""Тесты report_schema API и смен с schema в ответе."""
from datetime import date


def test_report_schema_warehouse(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.get(
        "/api/uss/report-schema?contract_id=1&role=warehouse_logistics&date=2026-01-15"
    )
    assert resp.status_code == 200
    codes = [x["billing_line_code"] for x in resp.json["period_inputs"]]
    assert "valve_gluing" in codes


def test_transport_shift_includes_schema(auth_client, client):
    auth_client("transport@test.local", "test")
    resp = client.get("/api/uss/transport/shift?warehouse_id=1&date=2026-01-15")
    assert resp.status_code == 200
    data = resp.json
    assert "schemas" in data
    assert "1" in data["schemas"]
    assert "vehicle_fixed_fields" in data["schemas"]["1"]


def test_warehouse_shift_no_vehicles(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.get("/api/uss/warehouse/shift?warehouse_id=1&date=2026-01-15")
    assert resp.status_code == 200
    data = resp.json
    assert "vehicles" not in data
    assert "schemas" in data
    assert "daily_totals" in data


def test_warehouse_save_daily(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.post(
        "/api/uss/warehouse/shift",
        json={
            "warehouse_id": 1,
            "contract_id": 1,
            "report_date": "2026-01-20",
            "entries": [{"billing_line_code": "valve_gluing", "quantity": 42}],
        },
    )
    assert resp.status_code == 200
    get_resp = client.get("/api/uss/warehouse/shift?warehouse_id=1&date=2026-01-20")
    totals = get_resp.json["daily_totals"]["1"]
    assert any(t["billing_line_code"] == "valve_gluing" and t["quantity"] == 42 for t in totals)


def test_inventory_shift_schema(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.get("/api/uss/inventory/shift?warehouse_id=1&date=2026-01-15")
    assert resp.status_code == 200
    data = resp.json
    assert "schemas" in data
    assert "contracts" in data
    assert "status" not in data


def test_inventory_save(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.post(
        "/api/uss/inventory/shift",
        json={
            "warehouse_id": 1,
            "report_date": "2026-02-01",
            "area_entries": {"storage_area_extra": 1500},
            "extra_entries": {},
        },
    )
    assert resp.status_code == 200
    get_resp = client.get("/api/uss/inventory/shift?warehouse_id=1&date=2026-02-01")
    assert get_resp.json["area_entries"].get("storage_area_extra") == 1500


def test_shift_context(auth_client, client):
    auth_client("transport@test.local", "test")
    resp = client.get("/api/uss/context?role=transport_logistics&date=2026-08-01")
    assert resp.status_code == 200
    data = resp.json
    assert data["warehouse_id"] == 1
    assert len(data["warehouses"]) >= 1
    assert len(data["contracts"]) >= 1


def test_transport_schema_includes_manual_daily_and_vehicle(app):
    from datetime import date

    from app.db import db
    from app.modules.reference.models import Contract, ContractAmendment, TariffRule, UnitOfMeasure
    from app.modules.uss.services.report_schema import schema_for_contract_role

    with app.app_context():
        contract = Contract.query.first()
        am = ContractAmendment.query.filter_by(contract_id=contract.id, status="active").first()
        unit = UnitOfMeasure.query.filter_by(code="pcs").first()
        db.session.add(
            TariffRule(
                contract_id=contract.id,
                amendment_id=am.id,
                billing_line_code="custom_podklejka",
                name="Подклейка клапанов тест",
                unit_id=unit.id,
                report_role="transport_logistics",
                report_scope="period",
                quantity_source="manual_daily",
                is_custom=True,
                valid_from=date(2025, 1, 1),
            )
        )
        elco = TariffRule.query.filter_by(
            contract_id=contract.id, billing_line_code="elco_passports",
        ).first()
        if elco:
            elco.report_role = "transport_logistics"
            elco.report_scope = "vehicle"
            elco.quantity_source = "manual_daily"
        db.session.commit()

        sch = schema_for_contract_role(contract.id, date(2026, 9, 2), "transport_logistics")
        period_codes = {x["billing_line_code"] for x in sch["period_inputs"]}
        vehicle_codes = {x["billing_line_code"] for x in sch["vehicle_inputs"]}
        fixed_tariff_codes = {
            f["billing_line_code"] for f in sch["vehicle_fixed_fields"] if f.get("tariff_input")
        }
        assert "custom_podklejka" in period_codes
        if elco:
            assert "elco_passports" in vehicle_codes
            assert "elco_passports" in fixed_tariff_codes


def test_transport_extra_handling_field_requires_tariff(app):
    from datetime import date

    from app.db import db
    from app.modules.reference.models import Contract, ContractAmendment, TariffRule, UnitOfMeasure
    from app.modules.uss.services.report_schema import schema_for_contract_role

    with app.app_context():
        contract = Contract.query.first()
        am = ContractAmendment.query.filter_by(contract_id=contract.id, status="active").first()
        unit = UnitOfMeasure.query.filter_by(code="m3").first()
        sch = schema_for_contract_role(contract.id, date(2026, 9, 3), "transport_logistics")
        fields = [f["field"] for f in sch["vehicle_fixed_fields"]]
        assert "extra_handling_m3" not in fields

        db.session.add(
            TariffRule(
                contract_id=contract.id,
                amendment_id=am.id,
                billing_line_code="extra_manual_m3",
                name="Доп. ручная обработка",
                unit_id=unit.id if unit else None,
                report_role="transport_logistics",
                report_scope="vehicle",
                quantity_source="auto_vehicle",
                valid_from=date(2025, 1, 1),
            )
        )
        db.session.commit()

        sch2 = schema_for_contract_role(contract.id, date(2026, 9, 3), "transport_logistics")
        fields2 = [f["field"] for f in sch2["vehicle_fixed_fields"]]
        assert "extra_handling_m3" in fields2
        handling_idx = fields2.index("handling_type_code")
        extra_idx = fields2.index("extra_handling_m3")
        assert handling_idx < extra_idx


def test_inventory_schema_with_wrong_repack_quantity_source(app):
    from datetime import date

    from app.db import db
    from app.modules.reference.models import Contract, TariffRule
    from app.modules.uss.services.report_schema import schema_for_contract_role

    with app.app_context():
        contract = Contract.query.first()
        repack = TariffRule.query.filter_by(
            contract_id=contract.id, billing_line_code="repack_units",
        ).first()
        assert repack is not None
        repack.quantity_source = "manual_daily"
        db.session.commit()

        sch = schema_for_contract_role(contract.id, date(2026, 9, 2), "inventory_management")
        extra_codes = {x["billing_line_code"] for x in sch["inventory_extra"]}
        area_codes = {x["billing_line_code"] for x in sch["inventory_areas"]}
        assert "repack_units" in extra_codes
        assert "repack_units" in extra_codes | area_codes
