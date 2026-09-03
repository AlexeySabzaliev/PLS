"""Справочник типов ТС."""
from __future__ import annotations

from app.db import db
from app.modules.reference.models import VehicleType

# code, название (объём в имени), sort_order, габариты д×ш×в (м)
VEHICLE_TYPE_SPECS = [
    ("truck", "Авто 82м³", 10, "13,6×2,45×2,70"),
    ("container", "НС 45′", 20, "13,6×2,45×2,70"),
    ("gazelle", "Газель", 30, "6,0×2,1×2,2"),
    ("van", "Фургон", 40, "4,2×2,0×2,2"),
    ("tent", "Тент", 50, "13,6×2,45×2,70"),
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
        else:
            updated = False
            if row.name != name:
                row.name = name
                updated = True
            if dims and row.dimensions_label != dims:
                row.dimensions_label = dims
                updated = True
            if row.sort_order != sort_order:
                row.sort_order = sort_order
                updated = True
            if updated:
                changed += 1
    if changed:
        db.session.commit()
    return changed
