"""Справочник типов ТС."""
from __future__ import annotations

from app.db import db
from app.modules.reference.models import VehicleType

# name, sort_order, габариты (отображаемая строка, м)
VEHICLE_TYPE_SPECS = [
    ("truck", "Фура (тягач + полуприцеп)", 10, "13,6×2,45×2,70"),
    ("gazelle", "Газель", 20, "6,0×2,1×2,2"),
    ("van", "Фургон", 30, "4,2×2,0×2,2"),
    ("container", "Контейнеровоз", 40, "13,6×2,45×2,70"),
    ("tent", "Тентованный", 50, "13,6×2,45×2,70"),
    ("refrigerator", "Рефрижератор", 60, "13,6×2,45×2,70"),
    ("other", "Прочее", 99, None),
]


def ensure_vehicle_types() -> int:
    existing = {r.code: r for r in VehicleType.query.all()}
    changed = 0
    for code, name, sort_order, dims in VEHICLE_TYPE_SPECS:
        row = existing.get(code)
        if not row:
            db.session.add(
                VehicleType(
                    code=code,
                    name=name,
                    sort_order=sort_order,
                    dimensions_label=dims,
                )
            )
            changed += 1
        elif dims and not row.dimensions_label:
            row.dimensions_label = dims
            changed += 1
    if changed:
        db.session.commit()
    return changed
