# -*- coding: utf-8 -*-
from datetime import date
from unittest.mock import MagicMock

import app.modules.uss.services.security_intranet as sec
from app.seeds.import_security_from_portal import (
    _row_active_between,
    fetch_portal_rows,
    upsert_portal_rows,
)


def test_row_active_between():
    row = {"visitDateFrom": "2026-09-02", "visitDateTo": "2026-09-05"}
    assert _row_active_between(row, date(2026, 9, 1), date(2026, 9, 30))
    assert _row_active_between(row, date(2026, 9, 3), date(2026, 9, 3))
    assert not _row_active_between(row, date(2026, 8, 1), date(2026, 8, 31))


def test_fetch_portal_rows_filters_clients(monkeypatch):
    sample = {
        "id": 1001,
        "visitorFullName": "Test",
        "contractorName": "Аристон",
        "visitPlace": "Склад ГП",
        "visitDateFrom": "2026-09-03",
        "visitDateTo": "2026-09-03",
        "hasVehicleAccess": True,
        "vehicleNumber": "А111АА198",
    }

    session = MagicMock()
    session.get.return_value = MagicMock(ok=True, status_code=200, json=lambda: {"rows": [sample]})
    monkeypatch.setattr(
        "app.seeds.import_security_from_portal.get_authenticated_session",
        lambda *a, **k: session,
    )
    rows = fetch_portal_rows(
        "Склад ГП",
        day_from=date(2026, 9, 1),
        day_to=date(2026, 9, 30),
    )
    assert len(rows) == 1
    assert rows[0]["contractorName"] == "Аристон"


def test_upsert_portal_rows(app):
    row = {
        "id": 9001,
        "visitorFullName": "Водитель",
        "contractorName": "Гауф Рус",
        "visitPlace": "Склад ГП",
        "visitDateFrom": "2026-09-03",
        "visitDateTo": "2026-09-03",
        "visitReason": "отгрузка",
        "hasVehicleAccess": True,
        "vehicleNumber": "К123КК147",
        "gateNumber": 3,
    }
    with app.app_context():
        stats = upsert_portal_rows([row], verbose=False)
        assert stats["saved"] == 1
