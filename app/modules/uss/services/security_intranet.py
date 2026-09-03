"""Клиент security.bsh-ru.ru — заявки на въезд ТС.

Сопоставление клиента — частичное по name (см. Billings security_intranet).
Поле clients.security_name в UI не показываем; при необходимости = name.
Место визита (visit_place) — warehouses.security_visit_place, справочник «Склады».

Маппинг портал → строка vehicle_operations:
  id                  → security_request_id
  vehicleNumber       → tractor_plate + trailer_plate (+ plate_number)
  vehiclePlate        → запасное поле номера (если vehicleNumber пуст)
  visitReason         → fallback для номера, если в vehicleNumber пусто
  contractorName      → фильтр клиента (частичное совпадение с clients.name)
  visitorFullName     → фильтр клиента
  visitPlace          → фильтр склада (подстрока security_visit_place)
  visitDateFrom/To    → активность заявки на дату смены
  hasVehicleAccess    → пропуск заявок без доступа ТС

Переменные окружения:
  SECURITY_BASE_URL — URL портала (по умолчанию https://security.bsh-ru.ru)
  SECURITY_API_COOKIE — cookie сессии портала (альтернатива Negotiate)
  SECURITY_USE_NEGOTIATE — Windows SSPI (по умолчанию true на Windows)
  SECURITY_PORTAL_STUB / SECURITY_USE_MOCK — демо-заявки без обращения к порталу
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from app.modules.reference.client_names import canonical_client_name, normalize_client_name
from app.modules.uss.services.security_session import (
    SESSION_JAR,
    get_authenticated_session,
    refresh_security_session,
)
from app.modules.uss.services.vehicle_plates import combine_vehicle_plates, parse_security_vehicle_plates

logger = logging.getLogger(__name__)

_DEBUG_LOG = Path(__file__).resolve().parents[4] / "debug-48a3e2.log"


def _agent_log(hypothesis_id: str, location: str, message: str, data: dict | None = None) -> None:
    # #region agent log
    try:
        import json
        import time

        payload = {
            "sessionId": "48a3e2",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data or {},
            "timestamp": int(time.time() * 1000),
        }
        with _DEBUG_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError:
        pass
    # #endregion

SECURITY_BASE_URL = os.getenv("SECURITY_BASE_URL", "https://security.bsh-ru.ru").rstrip("/")
SECURITY_API_COOKIE = os.getenv("SECURITY_API_COOKIE", "")
SECURITY_COOKIE_FILE = os.getenv("SECURITY_COOKIE_FILE", "").strip()
SECURITY_USE_LOCAL_DB = os.getenv("SECURITY_USE_LOCAL_DB", "").lower() in ("1", "true", "yes")
SECURITY_LOCAL_FALLBACK = os.getenv("SECURITY_LOCAL_FALLBACK", "").lower() in ("1", "true", "yes")
_negotiate_default = "true" if sys.platform == "win32" else "false"
SECURITY_USE_NEGOTIATE = os.getenv("SECURITY_USE_NEGOTIATE", _negotiate_default).lower() in (
    "1",
    "true",
    "yes",
)


def _use_mock() -> bool:
    if os.getenv("SECURITY_PORTAL_STUB", "").lower() in ("1", "true", "yes"):
        return True
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
    """Публичный статус для UI — без технических деталей."""
    stub = _use_mock()
    has_auth = (
        bool(_resolve_security_cookie())
        or SESSION_JAR.is_file()
        or _negotiate_auth() is not None
        or SECURITY_USE_LOCAL_DB
        or os.getenv("SECURITY_AUTO_BROWSER_COOKIES", "1").lower() in ("1", "true", "yes")
    )
    available = stub or has_auth
    demo_fallback = not available
    if SECURITY_USE_LOCAL_DB:
        source = "local"
        label = "локальная БД (SECURITY_USE_LOCAL_DB)"
    elif stub:
        source = "stub"
        label = "заглушка (SECURITY_PORTAL_STUB)"
    elif demo_fallback:
        source = "demo"
        label = "демо (нет доступа к порталу)"
    else:
        source = "remote"
        label = "портал security.bsh-ru.ru"
    return {
        "available": available or demo_fallback,
        "source": source,
        "label": label,
        "stub": stub,
        "has_auth": has_auth,
    }


def _resolve_security_cookie() -> str:
    """Cookie сессии портала: env или файл (удобно для dev без браузера)."""
    raw = ""
    if SECURITY_API_COOKIE:
        raw = SECURITY_API_COOKIE.strip()
    elif SECURITY_COOKIE_FILE:
        try:
            raw = Path(SECURITY_COOKIE_FILE).read_text(encoding="utf-8").strip()
        except OSError:
            return ""
    if not raw:
        return ""
    # Устаревший JWT из .env без имени cookie (security_session=...) не работает с API.
    if raw.startswith("eyJ") and "=" not in raw.split(";")[0]:
        return ""
    return raw


def _live_api_params(visit_place: str | None, day: date) -> dict[str, str]:
    """Параметры /api/requests для роли vehicleReviewer (вкладка «На проверке»)."""
    params: dict[str, str] = {"scope": "review", "approved": "approved"}
    if day == date.today():
        params["today"] = "1"
    if visit_place:
        params["visitPlace"] = visit_place.split("|")[0].strip()
    return params


def _live_session(*, refresh: bool = False):
    cookie = _resolve_security_cookie() or None
    if refresh:
        info = refresh_security_session(SECURITY_BASE_URL, cookie_header=cookie)
        if not info.get("ok"):
            return None
    return get_authenticated_session(SECURITY_BASE_URL, cookie_header=cookie)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _looks_like_vehicle_number(value: str) -> bool:
    text = value.strip()
    if len(text) < 4:
        return False
    low = text.lower()
    if any(x in low for x in ("накладн", "въезд по", "отгрузка по", "по накладным")):
        return False
    return parse_security_vehicle_plates(text)[0] is not None


def _vehicle_raw_from_row(row: dict) -> str:
    """Поля портала → сырая строка с номером (vehicleNumber / vehiclePlate / trailerPlate)."""
    parts: list[str] = []
    for key in ("vehicleNumber", "vehiclePlate"):
        val = (row.get(key) or "").strip()
        if val:
            parts.append(val)
    trailer_only = (row.get("trailerPlate") or row.get("trailerNumber") or "").strip()
    if trailer_only and parts:
        main = parts[0]
        if trailer_only not in main:
            return f"{main} / {trailer_only}"
    if parts:
        return parts[0]
    return trailer_only


def _extract_vehicle_number(row: dict) -> str | None:
    raw = _vehicle_raw_from_row(row)
    if not raw or not _looks_like_vehicle_number(raw):
        return None
    tractor, trailer = parse_security_vehicle_plates(raw)
    if not tractor:
        return None
    return combine_vehicle_plates(tractor, trailer)


def _client_match_keys(client_name: str, security_name: str | None) -> list[str]:
    """Ключи для точного сопоставления с contractorName (без коротких подстрок вроде «аристон»)."""
    keys: list[str] = []
    seen: set[str] = set()

    def add(raw: str | None) -> None:
        if not raw:
            return
        norm = normalize_client_name(canonical_client_name(raw))
        if len(norm) < 5 or norm in seen:
            return
        seen.add(norm)
        keys.append(norm)

    add(client_name)
    add(security_name)
    canonical = canonical_client_name(client_name or "")
    bare = normalize_client_name(canonical).removeprefix("ооо ").strip()
    if bare and bare not in seen and len(bare) >= 5:
        seen.add(bare)
        keys.append(bare)
    return keys


def _same_client_entity(left: str, right: str) -> bool:
    if not left or not right:
        return False
    return normalize_client_name(canonical_client_name(left)) == normalize_client_name(
        canonical_client_name(right)
    )


def _row_matches_client(row: dict, client_name: str, security_name: str | None = None) -> bool:
    """Сопоставление по каноническому имени (contractorName часто «Аристон», не полное ООО)."""
    for field in (row.get("contractorName"), row.get("visitorFullName")):
        if not field:
            continue
        if _same_client_entity(field, client_name):
            return True
        if security_name and _same_client_entity(field, security_name):
            return True

    targets: list[str] = []
    seen: set[str] = set()
    for raw in (client_name, security_name):
        if not raw:
            continue
        norm = normalize_client_name(canonical_client_name(raw))
        if norm and norm not in seen:
            seen.add(norm)
            targets.append(norm)
    if not targets:
        return False

    candidates: list[str] = []
    for field in (row.get("contractorName"), row.get("visitorFullName")):
        if not field:
            continue
        norm = normalize_client_name(canonical_client_name(field))
        if norm:
            candidates.append(norm)
    if not candidates:
        return False

    for target in targets:
        for cand in candidates:
            if cand == target:
                return True
            shorter, longer = (cand, target) if len(cand) <= len(target) else (target, cand)
            if len(shorter) >= 10 and shorter in longer:
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


_DEMO_PLATE_PREFIXES = ("А000АА", "В111ВВ")


def is_mock_security_request_id(request_id: str | None) -> bool:
    return (request_id or "").strip().lower().startswith("mock-")


def is_demo_security_plate(plate: str | None) -> bool:
    """Госномера из SECURITY_PORTAL_STUB (_mock_rows)."""
    text = (plate or "").strip()
    if len(text) != 8:
        return False
    return text[:6] in _DEMO_PLATE_PREFIXES and text[6:].isdigit()


def is_demo_security_vehicle(
    *,
    security_request_id: str | None = None,
    tractor_plate: str | None = None,
    plate_number: str | None = None,
) -> bool:
    if is_mock_security_request_id(security_request_id):
        return True
    if is_demo_security_plate(tractor_plate):
        return True
    primary = (plate_number or "").split("/")[0].strip()
    return is_demo_security_plate(primary)


def purge_demo_security_vehicles(warehouse_id: int, day: date) -> int:
    """Удалить демо-ТС охраны (после отключения SECURITY_PORTAL_STUB)."""
    from app.db import db
    from app.modules.uss.models import VehicleOperation

    rows = VehicleOperation.query.filter_by(
        warehouse_id=warehouse_id,
        operation_date=day,
        source="security",
    ).all()
    deleted = 0
    for row in rows:
        if not is_demo_security_vehicle(
            security_request_id=row.security_request_id,
            tractor_plate=row.tractor_plate,
            plate_number=row.plate_number,
        ):
            continue
        db.session.delete(row)
        deleted += 1
    if deleted:
        db.session.flush()
    return deleted


def _client_slug(client_name: str) -> str:
    """Уникальный slug для mock-заявок (кириллица → хэш, не «client» для всех)."""
    norm = normalize_client_name(canonical_client_name(client_name))
    slug = re.sub(r"[^a-z0-9]+", "", norm)
    if len(slug) < 3:
        slug = hashlib.md5(norm.encode("utf-8")).hexdigest()[:10]
    return slug[:12]


def _mock_rows(client_name: str, visit_place: str | None, day: date) -> list[SecurityVehicleRow]:
    suffix = day.strftime("%d%m")
    slug = _client_slug(client_name)
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
        SecurityVehicleRow(
            request_id=f"mock-{slug}-{suffix}-2",
            vehicle_number=f"В111ВВ{suffix[:2]}",
            contractor_name=client_name,
            visit_place=visit_place,
            visit_date_from=day,
            visit_date_to=day,
            visitor_full_name=client_name,
            matched_client=client_name,
        ),
    ]


def _row_to_api(raw: dict) -> dict:
    """Строка БД / API → единый формат для фильтрации."""
    return {
        "id": raw.get("id"),
        "visitorFullName": raw.get("visitor_full_name") or raw.get("visitorFullName"),
        "contractorName": raw.get("contractor_name") or raw.get("contractorName"),
        "visitPlace": raw.get("visit_place") or raw.get("visitPlace"),
        "visitDateFrom": str(raw.get("visit_date_from") or raw.get("visitDateFrom") or "")[:10] or None,
        "visitDateTo": str(raw.get("visit_date_to") or raw.get("visitDateTo") or "")[:10] or None,
        "visitReason": raw.get("visit_reason") or raw.get("visitReason"),
        "hasVehicleAccess": raw.get("has_vehicle_access") if "has_vehicle_access" in raw else raw.get("hasVehicleAccess"),
        "vehicleNumber": raw.get("vehicle_number") or raw.get("vehicleNumber"),
        "vehiclePlate": raw.get("vehicle_plate") or raw.get("vehiclePlate"),
        "trailerPlate": raw.get("trailer_plate") or raw.get("trailerPlate"),
        "trailerNumber": raw.get("trailer_number") or raw.get("trailerNumber"),
        "gateNumber": raw.get("gate_number") if "gate_number" in raw else raw.get("gateNumber"),
    }


def _fetch_from_local_db(visit_place: str | None, day: date) -> tuple[list[dict], str]:
    from sqlalchemy import text

    from app.db import db

    conditions = [
        "has_vehicle_access = 1",
        "is_approved = 1",
        "visit_date_from <= :day",
        "visit_date_to >= :day",
    ]
    params: dict = {"day": day}
    if visit_place:
        token = visit_place.split("|")[0].strip()
        if token:
            conditions.append("(visit_place = :place OR visit_place LIKE :place_like)")
            params["place"] = token
            params["place_like"] = f"%{token}%"
    where = " AND ".join(conditions)
    try:
        rows = db.session.execute(
            text(
                f"""
                SELECT id, visitor_full_name, contractor_name, visit_place,
                       visit_date_from, visit_date_to, visit_reason,
                       has_vehicle_access, vehicle_number, gate_number
                FROM security_admission_form
                WHERE {where}
                ORDER BY id
                """
            ),
            params,
        ).mappings().all()
        return [_row_to_api(dict(r)) for r in rows], "local_db"
    except Exception as exc:
        logger.warning("security local db fetch failed: %s", exc)
        return [], f"error:{exc}"


def _try_local_db(visit_place: str | None, day: date) -> tuple[list[dict], str]:
    rows, src = _fetch_from_local_db(visit_place, day)
    if not rows and visit_place:
        rows, src = _fetch_from_local_db(None, day)
        if rows:
            src = f"{src}_relaxed"
    return rows, src


def _fetch_raw_requests(visit_place: str | None, day: date) -> tuple[list[dict], str]:
    if _use_mock():
        return [], "mock"
    if SECURITY_USE_LOCAL_DB:
        rows, src = _try_local_db(visit_place, day)
        return rows or [], src if rows else "local_db"

    params = _live_api_params(visit_place, day)
    session = _live_session()
    if session is None:
        if SECURITY_LOCAL_FALLBACK:
            rows, src = _try_local_db(visit_place, day)
            if rows:
                return rows, src
        _agent_log(
            "H1",
            "security_intranet._fetch_raw_requests",
            "no live session",
            {"visit_place": visit_place, "day": day.isoformat()},
        )
        return [], "no_auth"

    try:
        resp = session.get(f"{SECURITY_BASE_URL}/api/requests", params=params, timeout=25)
        if resp.status_code == 401:
            session = _live_session(refresh=True)
            if session is None:
                if SECURITY_LOCAL_FALLBACK:
                    rows, src = _try_local_db(visit_place, day)
                    if rows:
                        return rows, src
                return [], "unauthorized"
            resp = session.get(f"{SECURITY_BASE_URL}/api/requests", params=params, timeout=25)
        if resp.status_code == 401:
            if SECURITY_LOCAL_FALLBACK:
                rows, src = _try_local_db(visit_place, day)
                if rows:
                    return rows, src
            _agent_log(
                "H1",
                "security_intranet._fetch_raw_requests",
                "live api unauthorized",
                {"visit_place": visit_place, "day": day.isoformat()},
            )
            return [], "unauthorized"
        resp.raise_for_status()
        payload = resp.json()
        rows = payload.get("rows") or []
        _agent_log(
            "H2",
            "security_intranet._fetch_raw_requests",
            "live api rows",
            {"rows": len(rows), "day": day.isoformat(), "visit_place": visit_place, "params": params},
        )
        if not rows and SECURITY_LOCAL_FALLBACK:
            local_rows, local_src = _try_local_db(visit_place, day)
            if local_rows:
                return local_rows, local_src
        return rows, "live"
    except Exception as exc:
        logger.warning("security fetch failed: %s", exc)
        if SECURITY_LOCAL_FALLBACK:
            rows, src = _try_local_db(visit_place, day)
            if rows:
                return rows, src
        return [], f"error:{exc}"


def fetch_vehicle_requests(
    *,
    client_name: str,
    security_name: str | None,
    visit_place: str | None,
    day: date,
    prefetched: list[dict] | None = None,
    fetch_source: str | None = None,
    stats: dict | None = None,
) -> tuple[list[SecurityVehicleRow], str]:
    match_keys = _client_match_keys(client_name, security_name)
    source = fetch_source or "live"
    _agent_log(
        "H1",
        "security_intranet.fetch_vehicle_requests",
        "client filter",
        {"client_name": client_name, "match_keys": match_keys, "prefetched": len(prefetched or [])},
    )

    if prefetched is None:
        prefetched, source = _fetch_raw_requests(visit_place, day)

    if source in ("mock", "unauthorized", "no_auth") or source.startswith("error"):
        if _use_mock():
            return _mock_rows(client_name, visit_place, day), "stub"
        return [], source

    out: list[SecurityVehicleRow] = []
    seen: set[str] = set()
    for raw in prefetched:
        if not _row_matches_client(raw, client_name, security_name):
            continue
        if not _row_matches_place(raw, visit_place):
            continue
        if not _row_active_on(raw, day):
            continue
        if stats is not None:
            stats["matched_filters"] = stats.get("matched_filters", 0) + 1
        item = _normalize_row(raw)
        if not item:
            if stats is not None:
                stats["skipped_no_plate"] = stats.get("skipped_no_plate", 0) + 1
                samples = stats.setdefault("skipped_samples", [])
                if len(samples) < 5:
                    sample = _vehicle_raw_from_row(raw) or str(raw.get("id") or "")
                    if sample and sample not in samples:
                        samples.append(sample[:120])
            continue
        if item.request_id in seen:
            continue
        item.matched_client = client_name
        seen.add(item.request_id)
        out.append(item)
    _agent_log(
        "H2",
        "security_intranet.fetch_vehicle_requests",
        "matched rows",
        {
            "client_name": client_name,
            "matched": len(out),
            "source": source,
            "plates": [x.vehicle_number for x in out[:8]],
        },
    )
    return out, source


def fetch_all_for_warehouse(visit_place: str | None, day: date) -> tuple[list[dict], str]:
    return _fetch_raw_requests(visit_place, day)
