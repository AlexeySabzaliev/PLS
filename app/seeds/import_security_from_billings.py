"""Импорт security_admission_form из Billings PostgreSQL в локальную SQLite ПЛС."""
from __future__ import annotations

import os
from datetime import date

from sqlalchemy import text

from app.db import db

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS security_admission_form (
    id BIGINT PRIMARY KEY,
    visitor_full_name VARCHAR(200) NOT NULL,
    contractor_name VARCHAR(200),
    visit_place VARCHAR(50) NOT NULL,
    visit_date_from DATE NOT NULL,
    visit_date_to DATE NOT NULL,
    visit_reason VARCHAR(1000),
    has_vehicle_access BOOLEAN NOT NULL DEFAULT 0,
    vehicle_number VARCHAR(200),
    gate_number SMALLINT,
    is_approved BOOLEAN NOT NULL DEFAULT 0
)
"""


def import_security_from_billings(
    *,
    since: date | None = None,
    verbose: bool = True,
) -> dict:
    """Скопировать заявки с ТС из Billings в локальную таблицу PLS."""
    url = os.getenv("BILLINGS_DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("BILLINGS_DATABASE_URL не задан в .env")

    import psycopg

    db.session.execute(text(CREATE_SQL))
    db.session.commit()

    conditions = ["has_vehicle_access = TRUE", "is_approved = TRUE"]
    params: dict = {}
    if since:
        conditions.append("visit_date_to >= %(since)s")
        params["since"] = since

    sql = f"""
        SELECT id, visitor_full_name, contractor_name, visit_place,
               visit_date_from, visit_date_to, visit_reason,
               has_vehicle_access, vehicle_number, gate_number, is_approved
        FROM security_admission_form
        WHERE {" AND ".join(conditions)}
        ORDER BY id
    """
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [d.name for d in cur.description]
            rows = [dict(zip(cols, row)) for row in cur.fetchall()]

    db.session.execute(text("DELETE FROM security_admission_form"))
    inserted = 0
    for row in rows:
        db.session.execute(
            text(
                """
                INSERT INTO security_admission_form (
                    id, visitor_full_name, contractor_name, visit_place,
                    visit_date_from, visit_date_to, visit_reason,
                    has_vehicle_access, vehicle_number, gate_number, is_approved
                ) VALUES (
                    :id, :visitor_full_name, :contractor_name, :visit_place,
                    :visit_date_from, :visit_date_to, :visit_reason,
                    :has_vehicle_access, :vehicle_number, :gate_number, :is_approved
                )
                """
            ),
            {
                **row,
                "has_vehicle_access": bool(row.get("has_vehicle_access")),
                "is_approved": bool(row.get("is_approved")),
            },
        )
        inserted += 1
    db.session.commit()

    if verbose:
        print(f"security_admission_form: импортировано {inserted} строк из Billings")
    return {"imported": inserted}
