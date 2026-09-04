"""Отчёт «Свод договоров и ДС»."""
from datetime import date

from app.db import db
from app.modules.reference.models import (
    Client,
    Contract,
    ContractAmendment,
    ProductType,
    Warehouse,
)
from app.modules.uss.services.contracts_registry import build_contracts_registry_report


def test_contracts_registry_requires_auth(client):
    resp = client.get("/api/uss/reports/contracts?warehouse_id=1")
    assert resp.status_code in (401, 403)


def test_contracts_registry_api(auth_client, client, app):
    auth_client("admin@test.local", "admin")
    with app.app_context():
        wh = Warehouse.query.filter_by(code="WH1").first() or Warehouse.query.first()
        client_row = Client(name="Тестовый клиент свод", is_active=True)
        db.session.add(client_row)
        db.session.flush()
        pt = ProductType.query.filter_by(code="RESPONSIBLE_STORAGE").first()
        contract = Contract(
            client_id=client_row.id,
            warehouse_id=wh.id,
            product_type_id=pt.id,
            number="TEST-CR-001",
            status="active",
            auto_renew=False,
        )
        db.session.add(contract)
        db.session.flush()
        am_renew = ContractAmendment(
            contract_id=contract.id,
            number="1",
            status="active",
            effective_from=date(2025, 1, 1),
            effective_to=date(2026, 12, 31),
            auto_renew=True,
        )
        am_exp = ContractAmendment(
            contract_id=contract.id,
            number="2",
            status="active",
            effective_from=date(2026, 1, 1),
            effective_to=date.today().replace(day=1),
            auto_renew=False,
        )
        db.session.add_all([am_renew, am_exp])
        db.session.commit()
        wh_id = wh.id

    resp = client.get(f"/api/uss/reports/contracts?warehouse_id={wh_id}&expiring_days=365")
    assert resp.status_code == 200
    data = resp.json
    assert data["warehouse_id"] == wh_id
    assert "clients" in data
    assert data["summary"]["contracts_total"] >= 1

    rows = []
    for c in data["clients"]:
        if c["client_name"] == "Тестовый клиент свод":
            rows = c["rows"]
            break
    assert len(rows) == 2
    renew_row = next(r for r in rows if r["amendment_number"] == "1")
    assert renew_row["end_display"] == "∞"
    assert renew_row["auto_renew"] is True


def test_contracts_registry_expiring_filter(auth_client, client, app):
    auth_client("admin@test.local", "admin")
    with app.app_context():
        wh = Warehouse.query.first()
        wh_id = wh.id

    resp = client.get(
        f"/api/uss/reports/contracts?warehouse_id={wh_id}&status_filter=expiring&expiring_days=365"
    )
    assert resp.status_code == 200
    for client_block in resp.json["clients"]:
        for row in client_block["rows"]:
            assert row["expiring_soon"] is True
