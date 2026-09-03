"""Нормализация имён клиентов для предотвращения дублей."""
from __future__ import annotations

import re
import unicodedata

CANONICAL_ARISTON_CLIENT = 'ООО "Аристон Термо Русь"'
CANONICAL_GAUFF_CLIENT = 'ООО "Гауф Рус"'

# Канонические алиасы (ключ — нормализованная форма)
CLIENT_ALIASES: dict[str, str] = {
    "аристон": CANONICAL_ARISTON_CLIENT,
    "ооо аристон термо русь": CANONICAL_ARISTON_CLIENT,
    "ооо аристон термо рус": CANONICAL_ARISTON_CLIENT,
    "аристон термо рус": CANONICAL_ARISTON_CLIENT,
    "ariston": CANONICAL_ARISTON_CLIENT,
    "гауф": CANONICAL_GAUFF_CLIENT,
    "гауф рус": CANONICAL_GAUFF_CLIENT,
    "ооо гауф рус": CANONICAL_GAUFF_CLIENT,
    "gauf": CANONICAL_GAUFF_CLIENT,
}


def normalize_client_name(name: str) -> str:
    """Привести имя к сравнимой форме (нижний регистр, без кавычек и лишних пробелов)."""
    if not name:
        return ""
    text = unicodedata.normalize("NFKC", str(name)).strip().lower()
    text = text.replace("«", "").replace("»", "").replace('"', "").replace("'", "")
    text = re.sub(r"\s+", " ", text)
    return text


def canonical_client_name(name: str) -> str:
    """Вернуть каноническое имя, если известен алиас."""
    key = normalize_client_name(name)
    return CLIENT_ALIASES.get(key, name.strip())


def find_duplicate_client_name(name: str, *, exclude_id: int | None = None) -> str | None:
    """Проверить, есть ли активный клиент с тем же нормализованным именем."""
    from app.modules.reference.models import Client

    target = normalize_client_name(canonical_client_name(name))
    if not target:
        return None
    for row in Client.query.filter_by(is_active=True).all():
        if exclude_id and row.id == exclude_id:
            continue
        if normalize_client_name(canonical_client_name(row.name)) == target:
            return row.name
    return None
