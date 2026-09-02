"""Клиент security.bsh-ru.ru — заявки на въезд ТС."""
from __future__ import annotations

import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import date

logger = logging.getLogger(__name__)

SECURITY_BASE_URL = os.getenv("SECURITY_BASE_URL", "https://security.bsh-ru.ru").rstrip("/")
SECURITY_API_COOKIE = os.getenv("SECURITY_API_COOKIE", "")
_negotiate_default = "true" if sys.platform == "win32" else "false"
SECURITY_USE_NEGOTIATE = os.getenv("SECURITY_USE_NEGOTIATE", _negotiate_default).lower() in (
    "1",
    "true",
    "yes",
)


def _use_mock() -> bool:
    return os.getenv("SECURITY_USE_MOCK", "").lower() in ("1", "true", "yes")


@dataclass
class SecurityVehicleRow:
    request_id: str
    vehicle_number: str
    contractor_name: str | None
    visit_place: str | None
    visit_date_from: date | None
    visit_date_to: date | None
    visitor_full_name: str | None
    matched_client: str | None = None


def _negotiate_auth():
    if not SECURITY_USE_NEGOTIATE:
        return None
    try:
        from requests_negotiate_sspi import HttpNegotiateAuth

        return HttpNegotiateAuth()
    except ImportError:
        try:
            from requests_negotiate import HttpNegotiateAuth

            return HttpNegotiateAuth()
        except ImportError:
            logger.warning("SECURITY_USE_NEGOTIATE включён, но пакет negotiate не установлен")
            return None


def security_status() -> dict:
    available = _use_mock() or bool(SECURITY_API_COOKIE) or _negotiate_auth() is not None
    demo_fallback = not available
    return {
        "available": available or demo_fallback,
        "source": "demo" if demo_fallback else "remote",
    }


def _session():
    import requests

    s = requests.Session()
    s.headers.update({"Accept": "application/json"})
    if SECURITY_API_COOKIE:
        s.headers["Cookie"] = SECURITY_API_COOKIE
    else:
        auth = _negotiate_auth()
        if auth:
            s.auth = auth
    return s


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


_PLATE_HINT = re.compile(r"[АВЕКМНОРСТУХABEKMHOPCTYX]\s*\d", re.IGNORECASE)


def _looks_like_vehicle_number(value: str) -> bool:
    text = value.strip()
    if len(text) < 5:
        return False
    low = text.lower()
    if any(x in low for x in ("накладн", "въезд по", "отгрузка по", "по накладным")):
        return False
    return bool(_PLATE_HINT.search(text.replace(" ", "")))


def _extract_vehicle_number(row: dict) -> str | None:
    raw = (row.get("vehicleNumber") or row.get("vehiclePlate") or "").strip()
    if not raw or not _looks_like_vehicle_number(raw):
        return None
    primary = re.split(r"[/\\|,;]", raw)[0].strip()
    return primary or raw


def _client_match_keys(client_name: str, security_name: str | None) -> list[str]:
    keys = []
    for raw in (security_name, client_name):
        if raw:
            k = raw.strip().lower()
            if k and k not in keys:
                keys.append(k)
    return keys


def _row_matches_client(row: dict, match_keys: list[str]) -> bool:
    if not match_keys:
        return False
    haystack = " ".join(
        filter(
            None,
            [row.get("contractorName"), row.get("visitorFullName"), row.get("visitReason")],
        )
    ).lower()
    for key in match_keys:
        if key in haystack or haystack in key:
            return True
        parts = key.split()
        if parts and parts[0] in haystack:
            return True
    return False


def _row_matches_place(row: dict, visit_place: str | None) -> bool:
    if not visit_place:
        return True
    place = (row.get("visitPlace") or "").lower()
    for part in visit_place.split("|"):
        token = part.strip().lower()
        if token and token in place:
            return True
    return False


def _row_active_on(row: dict, day: date) -> bool:
    d_from = _parse_date(row.get("visitDateFrom"))
    d_to = _parse_date(row.get("visitDateTo")) or d_from
    if not d_from:
        return day == date.today()
    if d_to and d_to < day:
        return False
    return d_from <= day


def _normalize_row(row: dict) -> SecurityVehicleRow | None:
    if row.get("hasVehicleAccess") is False:
        return None
    plate = _extract_vehicle_number(row)
    if not plate:
        return None
    rid = str(row.get("id") or "").strip()
    if not rid:
        return None
    return SecurityVehicleRow(
        request_id=rid,
        vehicle_number=plate,
        contractor_name=row.get("contractorName"),
        visit_place=row.get("visitPlace"),
        visit_date_from=_parse_date(row.get("visitDateFrom")),
        visit_date_to=_parse_date(row.get("visitDateTo")),
        visitor_full_name=row.get("visitorFullName"),
    )


def _mock_rows(client_name: str, visit_place: str | None, day: date) -> list[SecurityVehicleRow]:
    suffix = day.strftime("%d%m")
    slug = re.sub(r"[^a-z0-9]", "", client_name.lower())[:6] or "client"
    return [
        SecurityVehicleRow(
            request_id=f"mock-{slug}-{suffix}-1",
            vehicle_number=f"А000АА{suffix[:2]}",
            contractor_name=client_name,
            visit_place=visit_place,
            visit_date_from=day,
            visit_date_to=day,
            visitor_full_name=client_name,
            matched_client=client_name,
        ),
    ]


def _fetch_raw_requests(visit_place: str | None, day: date) -> tuple[list[dict], str]:
    if _use_mock():
        return [], "mock"
    if not SECURITY_API_COOKIE and not _negotiate_auth():
        return [], "no_auth"

    params: dict[str, str] = {}
    if day == date.today():
        params["today"] = "1"
    if visit_place:
        params["visitPlace"] = visit_place.split("|")[0].strip()

    try:
        resp = _session().get(f"{SECURITY_BASE_URL}/api/requests", params=params, timeout=25)
        if resp.status_code == 401:
            return [], "unauthorized"
        resp.raise_for_status()
        payload = resp.json()
        return payload.get("rows") or [], "live"
    except Exception as exc:
        logger.warning("security fetch failed: %s", exc)
        return [], f"error:{exc}"


def fetch_vehicle_requests(
    *,
    client_name: str,
    security_name: str | None,
    visit_place: str | None,
    day: date,
    prefetched: list[dict] | None = None,
    fetch_source: str | None = None,
) -> tuple[list[SecurityVehicleRow], str]:
    match_keys = _client_match_keys(client_name, security_name)
    source = fetch_source or "live"

    if prefetched is None:
        prefetched, source = _fetch_raw_requests(visit_place, day)

    if source in ("mock", "unauthorized", "no_auth") or source.startswith("error"):
        if source in ("unauthorized", "no_auth", "mock") or source.startswith("error"):
            return _mock_rows(client_name, visit_place, day), "mock_fallback"
        return [], source

    out: list[SecurityVehicleRow] = []
    seen: set[str] = set()
    for raw in prefetched:
        if not _row_matches_client(raw, match_keys):
            continue
        if not _row_matches_place(raw, visit_place):
            continue
        if not _row_active_on(raw, day):
            continue
        item = _normalize_row(raw)
        if not item or item.request_id in seen:
            continue
        item.matched_client = client_name
        seen.add(item.request_id)
        out.append(item)
    return out, source


def fetch_all_for_warehouse(visit_place: str | None, day: date) -> tuple[list[dict], str]:
    return _fetch_raw_requests(visit_place, day)
