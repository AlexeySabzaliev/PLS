"""Импорт MSSQL-дампа admission_form."""
from pathlib import Path

from app.seeds.import_security_sql_dump import parse_mssql_dump

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "security" / "admission_form_mssql.sql"


def test_parse_mssql_dump_has_ariston_vehicles():
    rows = parse_mssql_dump(_FIXTURE)
    assert len(rows) >= 90
    ariston = [
        r
        for r in rows
        if (r.get("contractor_name") or "").lower().startswith("аристон")
        and r.get("has_vehicle_access")
        and r.get("visit_place") == "Склад ГП"
    ]
    assert len(ariston) >= 5
    assert any("К582ВЕ147" in (r.get("vehicle_number") or "") for r in ariston)


def test_import_security_sql_dump(app):
    from app.seeds.import_security_sql_dump import import_security_sql_dump
    from sqlalchemy import text

    from app.db import db

    with app.app_context():
        result = import_security_sql_dump(_FIXTURE, verbose=False)
        assert result["imported"] > 30
        count = db.session.execute(
            text(
                "SELECT COUNT(*) FROM security_admission_form "
                "WHERE contractor_name = 'Аристон' AND visit_place = 'Склад ГП'"
            )
        ).scalar()
        assert count >= 5


def test_fetch_from_local_db(app, monkeypatch):
    from datetime import date

    import app.modules.uss.services.security_intranet as sec
    from app.seeds.import_security_sql_dump import import_security_sql_dump

    monkeypatch.setattr(sec, "SECURITY_USE_LOCAL_DB", True)
    with app.app_context():
        import_security_sql_dump(_FIXTURE, verbose=False)
        rows, src = sec._fetch_raw_requests("Склад ГП", date(2026, 8, 28))
        assert src == "local_db"
        assert len(rows) >= 3
        matched, _ = sec.fetch_vehicle_requests(
            client_name='ООО "Аристон Термо Русь"',
            security_name=None,
            visit_place="Склад ГП",
            day=date(2026, 8, 28),
            prefetched=rows,
            fetch_source=src,
        )
        assert len(matched) >= 3
