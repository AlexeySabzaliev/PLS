"""Загрузка заявок с портала security.bsh-ru.ru в локальную security_admission_form."""
from __future__ import annotations

import logging
import os
from datetime import date

from sqlalchemy import text

from app.db import db
from app.modules.reference.client_names import CANONICAL_ARISTON_CLIENT, CANONICAL_GAUFF_CLIENT
from app.modules.uss.services.security_intranet import (
    SECURITY_BASE_URL,
    _row_matches_client,
    _vehicle_raw_from_row,
)
from app.modules.uss.services.security_session import get_authenticated_session, security_refresh_hint
from app.seeds.import_security_from_billings import CREATE_SQL

logger = logging.getLogger(__name__)

DEFAULT_CLIENTS = (CANONICAL_ARISTON_CLIENT, CANONICAL_GAUFF_CLIENT)


def _live_api_params(visit_place: str, *, today_only: bool) -> dict[str, str]:
    params: dict[str, str] = {"scope": "review", "approved": "approved"}
    token = visit_place.split("|")[0].strip()
    if token:
        params["visitPlace"] = token
    if today_only:
        params["today"] = "1"
    return params


def _row_active_between(row: dict, day_from: date, day_to: date) -> bool:
    d_from = row.get("visitDateFrom") or row.get("visit_date_from")
    d_to = row.get("visitDateTo") or row.get("visit_date_to") or d_from
    if not d_from:
        return False
    try:
        start = date.fromisoformat(str(d_from)[:10])
        end = date.fromisoformat(str(d_to)[:10]) if d_to else start
    except ValueError:
        return False
    return start <= day_to and end >= day_from


def _portal_row_to_db(row: dict) -> dict:
    vehicle = _vehicle_raw_from_row(row) or (row.get("vehicleNumber") or row.get("vehiclePlate") or "").strip()
    gate = row.get("gateNumber")
    return {
        "id": int(row["id"]),
        "visitor_full_name": (row.get("visitorFullName") or row.get("visitor_full_name") or "").strip() or "—",
        "contractor_name": row.get("contractorName") or row.get("contractor_name"),
        "visit_place": (row.get("visitPlace") or row.get("visit_place") or "").strip(),
        "visit_date_from": date.fromisoformat(str(row.get("visitDateFrom") or row["visit_date_from"])[:10]),
        "visit_date_to": date.fromisoformat(
            str(row.get("visitDateTo") or row.get("visit_date_to") or row.get("visitDateFrom"))[:10]
        ),
        "visit_reason": (row.get("visitReason") or row.get("visit_reason") or "")[:1000],
        "has_vehicle_access": bool(row.get("hasVehicleAccess") if "hasVehicleAccess" in row else row.get("has_vehicle_access")),
        "vehicle_number": vehicle[:200] if vehicle else None,
        "gate_number": int(gate) if gate not in (None, "") else None,
        "is_approved": True,
    }


def fetch_portal_rows(
    visit_place: str,
    *,
    day_from: date,
    day_to: date,
    clients: tuple[str, ...] = DEFAULT_CLIENTS,
    vehicles_only: bool = True,
) -> list[dict]:
    """Скачать заявки с портала и отфильтровать по периоду и клиентам."""
    session = get_authenticated_session(SECURITY_BASE_URL)
    if session is None:
        raise RuntimeError(security_refresh_hint())

    today_only = day_from == day_to == date.today()
    params = _live_api_params(visit_place, today_only=today_only)
    resp = session.get(f"{SECURITY_BASE_URL}/api/requests", params=params, timeout=45)
    if resp.status_code == 401:
        raise RuntimeError("Портал вернул 401 — обновите сессию: flask pls security-refresh-session")
    resp.raise_for_status()
    raw_rows = resp.json().get("rows") or []

    # Без today API отдаёт широкий список; для прошлых дат дополняем по дням с today=1
    if not today_only and day_to >= date.today() >= day_from:
        seen = {int(r["id"]) for r in raw_rows if r.get("id")}
        p = _live_api_params(visit_place, today_only=True)
        resp_today = session.get(f"{SECURITY_BASE_URL}/api/requests", params=p, timeout=45)
        if resp_today.ok:
            for row in resp_today.json().get("rows") or []:
                rid = row.get("id")
                if rid and int(rid) not in seen:
                    raw_rows.append(row)
                    seen.add(int(rid))

    out: list[dict] = []
    for row in raw_rows:
        if vehicles_only and not row.get("hasVehicleAccess"):
            continue
        if not _row_active_between(row, day_from, day_to):
            continue
        if clients:
            if not any(_row_matches_client(row, client) for client in clients):
                continue
        out.append(row)
    return out


def upsert_portal_rows(rows: list[dict], *, verbose: bool = True) -> dict:
    """INSERT OR REPLACE в security_admission_form."""
    db.session.execute(text(CREATE_SQL))
    inserted = 0
    for row in rows:
        payload = _portal_row_to_db(row)
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
                ON CONFLICT(id) DO UPDATE SET
                    visitor_full_name = excluded.visitor_full_name,
                    contractor_name = excluded.contractor_name,
                    visit_place = excluded.visit_place,
                    visit_date_from = excluded.visit_date_from,
                    visit_date_to = excluded.visit_date_to,
                    visit_reason = excluded.visit_reason,
                    has_vehicle_access = excluded.has_vehicle_access,
                    vehicle_number = excluded.vehicle_number,
                    gate_number = excluded.gate_number,
                    is_approved = excluded.is_approved
                """
            ),
            payload,
        )
        inserted += 1
    db.session.commit()
    if verbose:
        print(f"security_admission_form: сохранено {inserted} заявок с портала")
    return {"saved": inserted}


def import_security_from_portal(
    *,
    visit_place: str = "Склад ГП",
    day_from: date,
    day_to: date,
    clients: tuple[str, ...] = DEFAULT_CLIENTS,
    verbose: bool = True,
) -> dict:
    rows = fetch_portal_rows(
        visit_place,
        day_from=day_from,
        day_to=day_to,
        clients=clients,
    )
    if not rows:
        return {"fetched": 0, "saved": 0}
    stats = upsert_portal_rows(rows, verbose=verbose)
    return {"fetched": len(rows), **stats}
