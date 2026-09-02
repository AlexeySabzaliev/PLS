"""Справочник типов ТС."""
from __future__ import annotations

from app.db import db
from app.modules.reference.models import VehicleType

VEHICLE_TYPE_SPECS = [
    ("truck", "Фура (тягач + полуприцеп)", 10),
    ("gazelle", "Газель", 20),
    ("van", "Фургон", 30),
    ("container", "Контейнеровоз", 40),
    ("tent", "Тентованный", 50),
    ("refrigerator", "Рефрижератор", 60),
    ("other", "Прочее", 99),
]


def ensure_vehicle_types() -> int:
    existing = {r.code for r in VehicleType.query.all()}
    added = 0
    for code, name, sort_order in VEHICLE_TYPE_SPECS:
        if code in existing:
            continue
        db.session.add(VehicleType(code=code, name=name, sort_order=sort_order))
        added += 1
    if added:
        db.session.commit()
    return added
