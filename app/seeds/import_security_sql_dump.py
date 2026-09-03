"""Импорт admission_form из MSSQL-дампа IT в локальную SQLite (dev/тест)."""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from sqlalchemy import text

from app.db import db
from app.seeds.import_security_from_billings import CREATE_SQL

_INSERT_MARKER = "INSERT [dbo].[admission_form]"
_CAST_DATE_RE = re.compile(
    r"CAST\(N'(?P<value>[^']+)'\s+AS\s+Date(?:Time2)?(?:\(\d+\))?\)",
    re.IGNORECASE,
)
_CAST_DT_RE = re.compile(
    r"CAST\(N'(?P<value>[^']+)'\s+AS\s+DateTime2(?:\(\d+\))?\)",
    re.IGNORECASE,
)


def _unescape_mssql_string(value: str) -> str:
    return value.replace("''", "'")


def _split_mssql_values(body: str) -> list[str]:
    """Разбор списка VALUES MSSQL с учётом N'...' и вложенных скобок."""
    parts: list[str] = []
    buf: list[str] = []
    i = 0
    depth = 0
    in_string = False

    def flush() -> None:
        token = "".join(buf).strip()
        if token:
            parts.append(token)
        buf.clear()

    while i < len(body):
        ch = body[i]
        nxt = body[i + 1] if i + 1 < len(body) else ""

        if not in_string:
            if ch == "(":
                depth += 1
                buf.append(ch)
                i += 1
                continue
            if ch == ")":
                depth -= 1
                buf.append(ch)
                i += 1
                continue
            if ch == "," and depth == 0:
                flush()
                i += 1
                continue
            if ch == "N" and nxt == "'":
                in_string = True
                i += 2
                continue
            if ch == "'":
                in_string = True
                i += 1
                continue
            buf.append(ch)
            i += 1
            continue

        if ch == "'":
            if nxt == "'":
                buf.append("'")
                i += 2
                continue
            in_string = False
            i += 1
            continue
        buf.append(ch)
        i += 1

    flush()
    return parts


def _parse_scalar(token: str):
    token = token.strip()
    if not token or token.upper() == "NULL":
        return None
    cast = re.search(
        r"CAST\s*\(\s*(?:N)?'?(?P<value>\d{4}-\d{2}-\d{2})'?\s+AS\s+Date(?:Time2)?(?:\(\d+\))?\s*\)",
        token,
        re.IGNORECASE,
    )
    if cast:
        return cast.group("value")[:10]
    if token.startswith("N'") and token.endswith("'"):
        return _unescape_mssql_string(token[2:-1])
    if token.startswith("'") and token.endswith("'"):
        return _unescape_mssql_string(token[1:-1])
    if token.lower() in ("0", "1"):
        return token == "1"
    if re.fullmatch(r"-?\d+", token):
        return int(token)
    return token


def _parse_insert_block(block: str) -> dict | None:
    upper = block.upper()
    if _INSERT_MARKER.upper() not in upper or " VALUES " not in upper:
        return None
    _, values_part = re.split(r"\bVALUES\b", block, maxsplit=1, flags=re.IGNORECASE)
    values_part = values_part.strip()
    if not values_part.startswith("("):
        return None
    depth = 0
    end = 0
    for idx, ch in enumerate(values_part):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                end = idx
                break
    if end <= 0:
        return None
    raw_values = values_part[1:end]
    cols = _split_mssql_values(raw_values)
    if len(cols) < 16:
        return None
    return {
        "id": int(cols[0]),
        "visitor_full_name": str(_parse_scalar(cols[1]) or ""),
        "contractor_name": _parse_scalar(cols[5]),
        "visit_place": str(_parse_scalar(cols[6]) or ""),
        "visit_date_from": _parse_scalar(cols[7]),
        "visit_date_to": _parse_scalar(cols[8]),
        "visit_reason": _parse_scalar(cols[9]),
        "has_vehicle_access": bool(_parse_scalar(cols[11])),
        "vehicle_number": _parse_scalar(cols[12]),
        "gate_number": _parse_scalar(cols[13]),
        "is_approved": bool(_parse_scalar(cols[15])),
    }


def parse_mssql_dump(path: Path) -> list[dict]:
    text_body = path.read_text(encoding="utf-8")
    blocks = re.split(r"\nGO\s*\n", text_body, flags=re.IGNORECASE)
    rows: list[dict] = []
    for block in blocks:
        if _INSERT_MARKER not in block:
            continue
        row = _parse_insert_block(block)
        if row:
            rows.append(row)
    return rows


def import_security_sql_dump(
    path: Path,
    *,
    only_approved_vehicles: bool = True,
    verbose: bool = True,
) -> dict:
    """Загрузить дамп IT (admission_form) в security_admission_form SQLite."""
    if not path.is_file():
        raise FileNotFoundError(path)

    parsed = parse_mssql_dump(path)
    if not parsed:
        raise RuntimeError(f"В файле {path} не найдено INSERT admission_form")

    db.session.execute(text(CREATE_SQL))
    db.session.execute(text("DELETE FROM security_admission_form"))

    inserted = 0
    for row in parsed:
        if only_approved_vehicles and not (row["has_vehicle_access"] and row["is_approved"]):
            continue
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
                "visit_date_from": date.fromisoformat(str(row["visit_date_from"])[:10]),
                "visit_date_to": date.fromisoformat(str(row["visit_date_to"])[:10]),
                "gate_number": int(row["gate_number"]) if row.get("gate_number") is not None else None,
            },
        )
        inserted += 1
    db.session.commit()

    if verbose:
        print(f"security_admission_form: импортировано {inserted} строк из {path.name}")
        print("Для синхронизации в dev: SECURITY_USE_LOCAL_DB=1 в .env и перезапуск сервера")
    return {"imported": inserted, "parsed": len(parsed)}
