"""Заглушки разделов и ролей (техобслуживание)."""
from __future__ import annotations

from app.db import db
from app.modules.reference.models import SectionMaintenance


def get_active_maintenance() -> list[dict]:
    rows = (
        SectionMaintenance.query.filter_by(is_active=True)
        .order_by(SectionMaintenance.target_type, SectionMaintenance.target_key)
        .all()
    )
    return [
        {
            "id": row.id,
            "target_type": row.target_type,
            "target_key": row.target_key,
            "message": row.message,
            "is_active": row.is_active,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        for row in rows
    ]


def maintenance_for_user(user: dict | None) -> dict:
    """Активные заглушки: sections и roles — словари key → message."""
    if user and user.get("is_admin"):
        return {"sections": {}, "roles": {}}
    sections: dict[str, str] = {}
    roles: dict[str, str] = {}
    user_roles = set(user.get("role_codes") or []) if user else set()
    for entry in get_active_maintenance():
        if entry["target_type"] == "section":
            sections[entry["target_key"]] = entry["message"]
        elif entry["target_type"] == "role" and entry["target_key"] in user_roles:
            roles[entry["target_key"]] = entry["message"]
    return {"sections": sections, "roles": roles}


def is_section_blocked(user: dict | None, section_id: str, maintenance: dict | None = None) -> str | None:
    """Текст заглушки для раздела или None."""
    if user and user.get("is_admin"):
        return None
    data = maintenance or maintenance_for_user(user)
    return data.get("sections", {}).get(section_id)


def upsert_maintenance(
    *,
    target_type: str,
    target_key: str,
    message: str,
    is_active: bool,
    updated_by: int | None,
) -> SectionMaintenance:
    row = SectionMaintenance.query.filter_by(
        target_type=target_type,
        target_key=target_key,
    ).first()
    if row:
        row.message = message
        row.is_active = is_active
        row.updated_by = updated_by
    else:
        row = SectionMaintenance(
            target_type=target_type,
            target_key=target_key,
            message=message,
            is_active=is_active,
            updated_by=updated_by,
        )
        db.session.add(row)
    db.session.commit()
    return row


def delete_maintenance(item_id: int) -> bool:
    row = db.session.get(SectionMaintenance, item_id)
    if not row:
        return False
    db.session.delete(row)
    db.session.commit()
    return True
