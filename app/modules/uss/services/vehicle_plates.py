"""Разбор госномеров тягача и прицепа."""
from __future__ import annotations

import re

_SPLIT_RE = re.compile(r"[/\\|,;]+")


def parse_vehicle_plates(raw: str | None) -> tuple[str | None, str | None]:
    if not raw or not str(raw).strip():
        return None, None
    parts = [p.strip() for p in _SPLIT_RE.split(str(raw).strip()) if p.strip()]
    if len(parts) >= 2:
        return parts[0][:64], parts[1][:64]
    if len(parts) == 1:
        return parts[0][:64], None
    return None, None


def combine_vehicle_plates(tractor: str | None, trailer: str | None) -> str | None:
    t = (tractor or "").strip()
    r = (trailer or "").strip()
    if t and r:
        return f"{t}/{r}"[:32]
    return (t or r or None)
