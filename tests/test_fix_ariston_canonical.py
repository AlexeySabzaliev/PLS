"""Тесты канонической правки Аристон."""
from datetime import date
from decimal import Decimal

from app.db import db
from app.modules.reference.models import Client, Contract, ContractAmendment, ProductType, TariffRule, UnitOfMeasure, Warehouse
from app.seeds.fix_ariston_canonical import (
    CANONICAL_CLIENT_NAME,
    CANONICAL_CONTRACT_NUMBER,
    CANONICAL_DS_NUMBER,
    DUPLICATE_DS6_NUMBER,
    WRONG_CONTRACT_NUMBER,
    fix_ariston_canonical,
)


def _seed_duplicates(app):
    with app.app_context():
        wh_strelna = Warehouse.query.filter_by(code="strelna").first()
        if not wh_strelna:
            wh_strelna = Warehouse(code="strelna", name="Стрельна", is_active=True)
            db.session.add(wh_strelna)
        wh_spb1 = Warehouse.query.filter_by(code="spb1").first()
        if not wh_spb1:
            wh_spb1 = Warehouse(code="spb1", name="СПб-1", is_active=True)
            db.session.add(wh_spb1)
        db.session.flush()

        pt = ProductType.query.filter_by(code="RESPONSIBLE_STORAGE").first()
        if not pt:
            pt = ProductType(code="RESPONSIBLE_STORAGE", name="ОХ")
            db.session.add(pt)
            db.session.flush()

        from app.modules.reference.models import UnitOfMeasure

        for code, name in [("m2", "м²"), ("m3", "м³"), ("pcs", "шт."), ("vehicle", "машина"), ("hour", "час")]:
            if not UnitOfMeasure.query.filter_by(code=code).first():
                db.session.add(UnitOfMeasure(code=code, name=name))
        db.session.flush()

        client_wrong = Client.query.filter_by(name="Аристон").first()
        if not client_wrong:
            client_wrong = Client(name="Аристон", is_active=True)
            db.session.add(client_wrong)
        client_ok = Client.query.filter_by(name=CANONICAL_CLIENT_NAME).first()
        if not client_ok:
            client_ok = Client(name=CANONICAL_CLIENT_NAME, is_active=True)
            db.session.add(client_ok)
        db.session.flush()

        wrong_contract = Contract.query.filter_by(number=WRONG_CONTRACT_NUMBER).first()
        if not wrong_contract:
            wrong_contract = Contract(
                client_id=client_wrong.id,
                warehouse_id=wh_strelna.id,
                product_type_id=pt.id,
                number=WRONG_CONTRACT_NUMBER,
                status="active",
            )
            db.session.add(wrong_contract)
            db.session.flush()
        if not ContractAmendment.query.filter_by(contract_id=wrong_contract.id, number="ДС-01/2025").first():
            db.session.add(ContractAmendment(
                contract_id=wrong_contract.id,
                number="ДС-01/2025",
                status="active",
                effective_from=date(2025, 6, 1),
            ))
        db.session.commit()


def test_fix_ariston_supersedes_short_ds6_duplicate(app):
    _seed_duplicates(app)
    with app.app_context():
        from app.seeds.fix_ariston_canonical import CANONICAL_DS6_TARIFF_CODES, DUPLICATE_DS6_NUMBER

        contract = Contract.query.filter(
            Contract.number.ilike(f"%{CANONICAL_CONTRACT_NUMBER}%")
        ).first()
        if not contract:
            contract = Contract(
                client_id=Client.query.filter_by(name=CANONICAL_CLIENT_NAME).first().id,
                warehouse_id=Warehouse.query.filter_by(code="strelna").first().id,
                product_type_id=ProductType.query.filter_by(code="RESPONSIBLE_STORAGE").first().id,
                number=CANONICAL_CONTRACT_NUMBER,
                status="active",
            )
            db.session.add(contract)
            db.session.flush()

        short = ContractAmendment(
            contract_id=contract.id,
            number=DUPLICATE_DS6_NUMBER,
            status="draft",
            effective_from=date(2026, 8, 1),
        )
        db.session.add(short)
        db.session.flush()
        unit = UnitOfMeasure.query.filter_by(code="m3").first()
        db.session.add(TariffRule(
            contract_id=contract.id,
            amendment_id=short.id,
            billing_line_code="manual_m3",
            name="test",
            unit_id=unit.id if unit else None,
            valid_from=date(2026, 8, 1),
            rate_ex_vat=Decimal("250"),
        ))
        db.session.commit()

        fix_ariston_canonical(dry_run=False, with_ds5=False)

        short = ContractAmendment.query.filter_by(
            contract_id=contract.id, number=DUPLICATE_DS6_NUMBER
        ).first()
        assert short.status == "superseded"
        assert TariffRule.query.filter_by(amendment_id=short.id).count() == 0

        ds6 = ContractAmendment.query.filter_by(
            contract_id=contract.id, number=CANONICAL_DS_NUMBER
        ).first()
        codes = {t.billing_line_code for t in TariffRule.query.filter_by(amendment_id=ds6.id).all()}
        assert "extra_vehicle_docs" in codes
        assert codes.issubset(CANONICAL_DS6_TARIFF_CODES)


def test_fix_ariston_canonical_merges_and_creates_ds6(app):
    _seed_duplicates(app)
    with app.app_context():
        report = fix_ariston_canonical(dry_run=False, with_ds5=True)
        assert any("ДС-6/2024" in a for a in report.actions)

        canonical_client = Client.query.filter_by(name=CANONICAL_CLIENT_NAME, is_active=True).first()
        assert canonical_client is not None
        wrong_client = Client.query.filter_by(name="Аристон").first()
        assert wrong_client is None

        spb1 = Warehouse.query.filter_by(code="spb1").first()
        assert spb1.is_active is False

        contract = Contract.query.filter(
            Contract.number.ilike(f"%{CANONICAL_CONTRACT_NUMBER}%")
        ).first()
        assert contract is not None
        assert contract.client_id == canonical_client.id
        assert contract.warehouse_id == Warehouse.query.filter_by(code="strelna").first().id

        wrong = Contract.query.filter_by(number=WRONG_CONTRACT_NUMBER).first()
        assert wrong is None

        ds6 = ContractAmendment.query.filter_by(contract_id=contract.id, number=CANONICAL_DS_NUMBER).first()
        assert ds6 is not None
        assert ds6.effective_from == date(2026, 8, 1)
        assert ds6.status == "active"

        tariffs = TariffRule.query.filter_by(amendment_id=ds6.id).all()
        assert len(tariffs) == 13
        codes = {t.billing_line_code for t in tariffs}
        assert "storage_area_fixed" in codes
        assert "manual_m3" in codes
        assert "extra_vehicle_docs" in codes
        assert "extra_vehicle_docs_rf" not in codes
        assert "extra_vehicle_docs_rb" not in codes
        extra = next(t for t in tariffs if t.billing_line_code == "storage_area_extra")
        assert extra.rate_ex_vat == Decimal("24")
        extra_docs = next(t for t in tariffs if t.billing_line_code == "extra_vehicle_docs")
        assert extra_docs.is_custom is True
        assert extra_docs.rate_ex_vat == Decimal("109.52")
        assert extra_docs.rate_line_code == "vehicle_docs"
        valve = next(t for t in tariffs if t.billing_line_code == "valve_gluing")
        assert valve.is_custom is True
        assert valve.rate_ex_vat == Decimal("109.52")
        flue = next(t for t in tariffs if t.billing_line_code == "flue_stickering")
        assert flue.is_custom is True
        assert flue.rate_ex_vat == Decimal("21.904")
        elco = next(t for t in tariffs if t.billing_line_code == "elco_passports")
        assert elco.is_custom is True
        drain = next(t for t in tariffs if t.billing_line_code == "elco_drain_hours")
        assert drain.is_custom is True
        assert drain.rate_ex_vat == Decimal("985.68")

        dup = ContractAmendment.query.filter_by(
            contract_id=contract.id, number="ДС-6"
        ).first()
        if dup:
            assert dup.status == "superseded"
            assert TariffRule.query.filter_by(amendment_id=dup.id).count() == 0

        ds5 = ContractAmendment.query.filter_by(contract_id=contract.id, number="ДС-5").first()
        assert ds5 is not None
        ds5_extra = TariffRule.query.filter_by(
            amendment_id=ds5.id, billing_line_code="storage_area_extra"
        ).first()
        assert ds5_extra.rate_ex_vat == Decimal("19.71")


def test_fix_ariston_canonical_dry_run_no_commit(app):
    _seed_duplicates(app)
    with app.app_context():
        before = ContractAmendment.query.count()
        report = fix_ariston_canonical(dry_run=True, with_ds5=False)
        assert report.dry_run
        assert any("[dry-run]" in a for a in report.actions)
        assert ContractAmendment.query.count() == before


def test_client_duplicate_validation(auth_client, client, app):
    auth_client("admin@test.local", "admin")
    with app.app_context():
        db.session.add(Client(name=CANONICAL_CLIENT_NAME, is_active=True))
        db.session.commit()
    resp = client.post("/api/reference/clients", json={"name": "Аристон", "is_active": True})
    assert resp.status_code == 422
    assert resp.json.get("error") == "duplicate_client"


def test_warehouse_work_hours_update(auth_client, client):
    auth_client("admin@test.local", "admin")
    create = client.post(
        "/api/reference/warehouses",
        json={
            "code": "wh_hours",
            "name": "Тест графика",
            "work_day_start": "09:00",
            "work_day_end": "17:30",
            "is_active": True,
        },
    )
    assert create.status_code == 201
    wid = create.json["id"]
    assert create.json["work_day_start"] == "09:00"
    assert create.json["work_day_end"] == "17:30"

    update = client.put(
        f"/api/reference/warehouses/{wid}",
        json={"work_day_end": "18:00"},
    )
    assert update.status_code == 200
    assert update.json["work_day_end"] == "18:00"


def test_warehouse_staff_effective_from_persisted(auth_client, client, app):
    auth_client("admin@test.local", "admin")
    with app.app_context():
        wh = Warehouse.query.filter_by(code="strelna").first() or Warehouse(
            code="strelna", name="Стрельна", is_active=True
        )
        db.session.add(wh)
        db.session.commit()
        wh_id = wh.id

    create = client.post(
        "/api/reference/warehouse-staff",
        json={
            "warehouse_id": wh_id,
            "name": "Оператор",
            "monthly_rate": 80000,
            "headcount": 2,
            "effective_from": "2026-01-01",
        },
    )
    assert create.status_code == 201
    pid = create.json["id"]

    listing = client.get(f"/api/reference/warehouse-staff?warehouse_id={wh_id}")
    assert listing.status_code == 200
    row = next(x for x in listing.json["items"] if x["id"] == pid)
    assert row["effective_from"] == "2026-01-01"

    versions = client.get(f"/api/reference/warehouse-staff/{pid}/versions")
    assert versions.status_code == 200
    assert len(versions.json["items"]) >= 1
    assert versions.json["items"][0]["valid_from"] == "2026-01-01"

    update = client.put(
        f"/api/reference/warehouse-staff/{pid}",
        json={"monthly_rate": 85000, "effective_from": "2026-02-01"},
    )
    assert update.status_code == 200
    assert update.json["monthly_rate"] == 85000

    listing2 = client.get(f"/api/reference/warehouse-staff?warehouse_id={wh_id}")
    row2 = next(x for x in listing2.json["items"] if x["id"] == pid)
    assert row2["effective_from"] == "2026-02-01"

    versions2 = client.get(f"/api/reference/warehouse-staff/{pid}/versions")
    assert len(versions2.json["items"]) >= 2

    date_only = client.put(
        f"/api/reference/warehouse-staff/{pid}",
        json={"effective_from": "2026-08-01"},
    )
    assert date_only.status_code == 200
    listing3 = client.get(f"/api/reference/warehouse-staff?warehouse_id={wh_id}")
    row3 = next(x for x in listing3.json["items"] if x["id"] == pid)
    assert row3["effective_from"] == "2026-08-01"
    assert row3["monthly_rate"] == 85000

    delete = client.delete(f"/api/reference/warehouse-staff/{pid}")
    assert delete.status_code == 200
