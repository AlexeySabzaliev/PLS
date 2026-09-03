"""Разбор госномеров тягача и прицепа."""
from __future__ import annotations

import re

_SPLIT_RE = re.compile(r"[/\\|,;]+")

# Маркеры прицепа в тексте заявки (с/п, п/п, «прицеп») — не путать с разделителем «/».
_TRAILER_MARK = re.compile(
    r"\s*(?:с\s*/\s*п|с\.?\s*п\.?|п\s*/\s*п|п\.?\s*п\.?|прицеп)\s*",
    re.IGNORECASE,
)

# Госномер РФ (кириллица и латиница — отдельные ветки: mixed class + IGNORECASE ломает 218CS61).
_RU_PLATE = re.compile(
    r"(?:[АВЕКМНОРСТУХ]\s*\d{3}\s*[АВЕКМНОРСТУХ]{2}\s*\d{2,3}"
    r"|[ABEKMHOPCTYX]\s*\d{3}\s*[ABEKMHOPCTYX]{2}\s*\d{2,3})",
    re.IGNORECASE,
)
# Прицеп РФ: 2 буквы + 3–4 цифры + опциональный регион.
_RU_TRAILER = re.compile(
    r"(?:[АВЕКМНОРСТУХ]{2}\s*\d{3,4}\s*\d{0,3}|[A-Z]{2}\s*\d{3,4}\s*\d{0,3})",
    re.IGNORECASE,
)
# Иностранный / транзитный формат: 218CS61, M853CE26.
_FOREIGN_PLATE = re.compile(
    r"(?:\d{3}[A-Z]{2}\d{2,3}|[A-Z]\d{3}[A-Z]{2,3})",
    re.IGNORECASE,
)
# Короткий прицепной/иностранный: K7161.
_SHORT_FOREIGN = re.compile(
    r"[A-Z]\d{3,4}|[A-Z]{2}\d{3,5}",
    re.IGNORECASE,
)


def _compact_plate(token: str) -> str:
    return re.sub(r"\s+", "", token.strip())


def _plate_tokens_in_text(text: str, *, allow_trailer: bool = True) -> list[str]:
    """Извлекает фрагменты, похожие на госномер, из произвольного текста заявки."""
    if not text:
        return []
    spans: list[tuple[int, int, str]] = []
    for pattern in (_RU_PLATE, _FOREIGN_PLATE):
        for match in pattern.finditer(text):
            token = _compact_plate(match.group(0))
            if len(token) >= 5:
                spans.append((match.start(), match.end(), token))
    if allow_trailer:
        for pattern in (_RU_TRAILER, _SHORT_FOREIGN):
            for match in pattern.finditer(text):
                start, end = match.span()
                if any(s < end and start < e for s, e, _ in spans):
                    continue
                token = _compact_plate(match.group(0))
                if len(token) >= 4:
                    spans.append((start, end, token))
    spans.sort(key=lambda item: (-(item[1] - item[0]), item[0]))
    found: list[str] = []
    seen: set[str] = set()
    for _, _, token in spans:
        if token in seen:
            continue
        if any(token in kept or kept in token for kept in found):
            continue
        seen.add(token)
        found.append(token)
    return found


def _normalize_security_segments(raw: str) -> list[str]:
    """Делит строку портала на блоки тягача/прицепа без ложного split по «/» в «с/п»."""
    text = _TRAILER_MARK.sub(" / ", raw.strip())
    text = re.sub(r"\s*/\s*", "/", text)
    if "/" in text:
        return [part.strip() for part in text.split("/") if part.strip()]
    # Запятая иногда отделяет тягач от прицепа/модели без госномера.
    if "," in text:
        return [part.strip() for part in text.split(",") if part.strip()]
    return [text] if text else []


def parse_security_vehicle_plates(raw: str | None) -> tuple[str | None, str | None]:
    """Разбор поля vehicleNumber с портала охраны (марка ТС, с/п, слэш, запятая)."""
    if not raw or not str(raw).strip():
        return None, None
    segments = _normalize_security_segments(str(raw))
    if not segments:
        return None, None

    per_segment = [
        _plate_tokens_in_text(seg, allow_trailer=(idx > 0 or "/" in str(raw)))
        for idx, seg in enumerate(segments)
    ]
    if len(segments) == 1 and len(per_segment[0]) == 1:
        extra = _plate_tokens_in_text(segments[0], allow_trailer=True)
        if len(extra) >= 2:
            per_segment = [extra]
    flat = [token for group in per_segment for token in group]
    if not flat:
        return None, None

    tractor = flat[0]
    trailer: str | None = None
    if len(per_segment) >= 2 and per_segment[1]:
        trailer = per_segment[1][0]
    elif len(flat) >= 2:
        trailer = flat[1]
    if trailer and trailer == tractor:
        trailer = None
    return tractor[:64], (trailer[:64] if trailer else None)


def parse_vehicle_plates(raw: str | None) -> tuple[str | None, str | None]:
    if not raw or not str(raw).strip():
        return None, None
    # Сначала — умный разбор формата охраны; иначе — простой split.
    tractor, trailer = parse_security_vehicle_plates(raw)
    if tractor:
        return tractor, trailer
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
