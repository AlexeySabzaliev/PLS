"""Биллинг без ставок — понятная ошибка."""


def test_billing_calculate_no_tariffs(auth_client, client, app):
    from app.db import db
    from app.modules.reference.models import ContractAmendment, TariffRule

    auth_client("admin@test.local", "admin")
    with app.app_context():
        TariffRule.query.delete()
        ContractAmendment.query.update({"status": "draft"})
        db.session.commit()

    resp = client.post(
        "/api/billing/calculate",
        json={
            "contract_id": 1,
            "period_from": "2026-08-01",
            "period_to": "2026-08-31",
        },
    )
    assert resp.status_code == 200
    data = resp.json
    assert data["status"] == "error"
    assert data["error"] == "amendment_draft"
    assert "черновик" in data["message"]

    with app.app_context():
        ContractAmendment.query.update({"status": "active"})
        db.session.commit()


def test_billing_allows_draft_amendment_in_development(auth_client, client, app):
    """В dev-режиме черновик ДС со ставками допускается для расчёта."""
    from app.db import db
    from app.modules.reference.models import ContractAmendment

    auth_client("admin@test.local", "admin")
    with app.app_context():
        ContractAmendment.query.update({"status": "draft"})
        db.session.commit()

    app.config["TESTING"] = False
    try:
        resp = client.post(
            "/api/billing/calculate",
            json={
                "contract_id": 1,
                "period_from": "2026-08-01",
                "period_to": "2026-08-31",
            },
        )
        assert resp.status_code == 200
        data = resp.json
        assert data["status"] == "ok", data
    finally:
        app.config["TESTING"] = True
