"""API и страница биллинга."""
from datetime import date


def test_billing_page(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.get("/uss/reports/billing")
    assert resp.status_code == 200
    assert "Биллинг" in resp.get_data(as_text=True)

    legacy = client.get("/uss/billing")
    assert legacy.status_code == 302
    assert "/uss/reports/billing" in legacy.headers.get("Location", "")


def test_billing_context(auth_client, client):
    auth_client("admin@test.local", "admin")
    resp = client.get("/api/billing/context?warehouse_id=1")
    assert resp.status_code == 200
    data = resp.json
    assert data["warehouse_id"] == 1
    assert len(data["contracts"]) >= 1


def test_billing_calculate(auth_client, client):
    auth_client("admin@test.local", "admin")
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
    assert data["status"] == "ok"
    assert "lines" in data
    assert "total_ex_vat" in data


def test_billing_forbidden_without_role(client):
    resp = client.get("/api/billing/context")
    assert resp.status_code in (401, 403)
