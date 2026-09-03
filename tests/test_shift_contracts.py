"""Тесты выбора договоров смены и действия ДС на дату."""
from datetime import date
from decimal import Decimal


def test_draft_amendment_visible_in_development(auth_client, client, app):
    from app.db import db
    from app.modules.reference.models import ContractAmendment

    auth_client("admin@test.local", "admin")
    with app.app_context():
        ContractAmendment.query.update({"status": "draft"})
        db.session.commit()

    app.config["TESTING"] = False
    try:
        resp = client.get("/api/uss/inventory/shift?warehouse_id=1&date=2026-09-02")
        assert resp.status_code == 200
        data = resp.json
        assert len(data["contracts"]) >= 1
        assert data["schemas"]["1"]["inventory_extra"] or data["schemas"]["1"]["inventory_areas"]
    finally:
        app.config["TESTING"] = True
        with app.app_context():
            ContractAmendment.query.update({"status": "active"})
            db.session.commit()


def test_draft_amendment_transport_schema_in_development(auth_client, client, app):
    from app.db import db
    from app.modules.reference.models import ContractAmendment

    auth_client("transport@test.local", "test")
    with app.app_context():
        ContractAmendment.query.update({"status": "draft"})
        db.session.commit()

    app.config["TESTING"] = False
    try:
        resp = client.get("/api/uss/transport/shift?warehouse_id=1&date=2026-09-02")
        assert resp.status_code == 200
        schema = resp.json["schemas"]["1"]
        assert schema["period_inputs"] or schema["vehicle_inputs"]
    finally:
        app.config["TESTING"] = True
        with app.app_context():
            ContractAmendment.query.update({"status": "active"})
            db.session.commit()


def test_effective_from_falls_back_to_tariff_valid_from(auth_client, client, app):
    from app.db import db
    from app.modules.reference.models import Contract, ContractAmendment, TariffRule

    auth_client("admin@test.local", "admin")
    with app.app_context():
        contract = Contract.query.first()
        am = ContractAmendment.query.filter_by(contract_id=contract.id).first()
        am.status = "active"
        am.effective_from = date(2026, 12, 1)
        TariffRule.query.filter_by(amendment_id=am.id).update({"valid_from": date(2026, 8, 1)})
        db.session.commit()

    try:
        resp = client.get("/api/uss/inventory/shift?warehouse_id=1&date=2026-09-02")
        assert resp.status_code == 200
        assert any(c["id"] == 1 for c in resp.json["contracts"])
    finally:
        with app.app_context():
            am = ContractAmendment.query.filter_by(contract_id=1).first()
            am.effective_from = date(2025, 1, 1)
            db.session.commit()


def test_shift_block_header_contains_amendment(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.get("/api/uss/transport/shift?warehouse_id=1&date=2026-08-01")
    assert resp.status_code == 200
    blocks = resp.json["contracts"]
    assert blocks
    first = blocks[0]
    assert first.get("amendment_number")
    assert "ДС №" in first.get("header", "")
    assert "договор" in first.get("header", "")


def test_schema_uses_single_amendment_when_duplicates(app):
    from app.db import db
    from app.modules.reference.models import Contract, ContractAmendment, TariffRule, UnitOfMeasure
    from app.modules.uss.services.report_schema import schema_for_contract_role

    with app.app_context():
        contract = Contract.query.first()
        canonical = ContractAmendment.query.filter_by(contract_id=contract.id).first()
        duplicate = ContractAmendment(
            contract_id=contract.id,
            number="ДС-6",
            status="draft",
            effective_from=date(2026, 8, 1),
        )
        db.session.add(duplicate)
        db.session.flush()
        unit = UnitOfMeasure.query.filter_by(code="pcs").first()
        db.session.add(
            TariffRule(
                contract_id=contract.id,
                amendment_id=duplicate.id,
                billing_line_code="custom_podklejka",
                name="только в дубле",
                unit_id=unit.id if unit else None,
                report_role="warehouse_logistics",
                quantity_source="manual_daily",
                is_custom=True,
                valid_from=date(2026, 8, 1),
                rate_ex_vat=Decimal("1"),
            )
        )
        db.session.commit()

        sch_dup = schema_for_contract_role(
            contract.id, date(2026, 9, 2), "warehouse_logistics", amendment_id=duplicate.id,
        )
        sch_auto = schema_for_contract_role(contract.id, date(2026, 9, 2), "warehouse_logistics")
        dup_codes = {x["billing_line_code"] for x in sch_dup["period_inputs"]}
        auto_codes = {x["billing_line_code"] for x in sch_auto["period_inputs"]}
        assert "custom_podklejka" in dup_codes
        assert "custom_podklejka" not in auto_codes
        assert sch_auto["amendment_id"] != duplicate.id

        TariffRule.query.filter_by(amendment_id=duplicate.id).delete()
        db.session.delete(duplicate)
        db.session.commit()


def test_inventory_shows_contract_with_saved_shift_data(auth_client, client, app):
    from app.db import db
    from app.modules.reference.models import ContractAmendment

    auth_client("admin@test.local", "admin")
    save = client.post(
        "/api/uss/inventory/shift",
        json={
            "warehouse_id": 1,
            "report_date": "2026-09-03",
            "area_entries": {"storage_area_extra": 100},
            "extra_entries": {},
        },
    )
    assert save.status_code == 200

    with app.app_context():
        ContractAmendment.query.update({"status": "draft", "effective_from": date(2099, 1, 1)})
        db.session.commit()

    app.config["TESTING"] = True
    resp = client.get("/api/uss/inventory/shift?warehouse_id=1&date=2026-09-03")
    assert resp.status_code == 200
    assert len(resp.json["contracts"]) >= 1

    with app.app_context():
        ContractAmendment.query.update({"status": "active", "effective_from": date(2025, 1, 1)})
        db.session.commit()
