"""Заявки на восстановление пароля."""
from __future__ import annotations

from datetime import datetime

from app.core.auth import hash_password
from app.core.passwords import validate_password
from app.core.user_admin import normalize_email, serialize_user, validate_email
from app.db import db
from app.modules.reference.models import PasswordResetRequest, User


def record_password_reset_request(email: str, *, note: str | None = None) -> tuple[bool, str]:
    """Создать/обновить заявку. Возвращает (создана, email)."""
    norm = validate_email(email) or normalize_email(email)
    if not norm:
        return False, ""
    user = User.query.filter(db.func.lower(User.email) == norm, User.is_active.is_(True)).first()
    if not user:
        return False, norm
    now = datetime.utcnow()
    row = PasswordResetRequest.query.filter_by(email=norm).first()
    if row:
        if row.status != "pending":
            row.status = "pending"
            row.request_count = 1
            row.resolved_at = None
            row.resolved_by = None
            row.admin_note = None
        else:
            row.request_count = (row.request_count or 0) + 1
        row.user_id = user.id
        row.display_name = user.full_name or row.display_name
        row.last_seen_at = now
        if note:
            row.user_note = note.strip()[:512]
    else:
        row = PasswordResetRequest(
            email=norm,
            user_id=user.id,
            display_name=user.full_name,
            status="pending",
            request_count=1,
            user_note=(note or "").strip()[:512] or None,
            first_seen_at=now,
            last_seen_at=now,
        )
        db.session.add(row)
    db.session.commit()
    return True, norm


def list_pending_password_resets() -> list[dict]:
    rows = (
        PasswordResetRequest.query.filter_by(status="pending")
        .order_by(PasswordResetRequest.last_seen_at.desc())
        .all()
    )
    return [_serialize(row) for row in rows]


def pending_password_reset_count() -> int:
    return PasswordResetRequest.query.filter_by(status="pending").count()


def _serialize(row: PasswordResetRequest) -> dict:
    return {
        "id": row.id,
        "email": row.email,
        "display_name": row.display_name,
        "user_id": row.user_id,
        "status": row.status,
        "request_count": row.request_count,
        "user_note": row.user_note,
        "first_seen_at": row.first_seen_at.isoformat() if row.first_seen_at else None,
        "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
        "admin_note": row.admin_note,
    }


def dismiss_password_reset(request_id: int, admin_user_id: int, note: str | None = None) -> dict:
    row = db.session.get(PasswordResetRequest, request_id)
    if not row or row.status != "pending":
        return {"error": "not_found", "message": "Заявка не найдена или уже обработана"}
    row.status = "dismissed"
    row.resolved_at = datetime.utcnow()
    row.resolved_by = admin_user_id
    if note:
        row.admin_note = note.strip()[:512]
    db.session.commit()
    return {"ok": True, "request": _serialize(row)}


def approve_password_reset(
    request_id: int,
    admin_user_id: int,
    *,
    new_password: str,
    note: str | None = None,
) -> dict:
    row = db.session.get(PasswordResetRequest, request_id)
    if not row or row.status != "pending":
        return {"error": "not_found", "message": "Заявка не найдена или уже обработана"}

    user = db.session.get(User, row.user_id) if row.user_id else None
    if not user:
        user = User.query.filter(db.func.lower(User.email) == row.email.lower()).first()
    if not user:
        return {"error": "user_not_found", "message": "Пользователь не найден"}
    row.user_id = user.id

    ok, err = validate_password(new_password, email=user.email)
    if not ok:
        return {"error": err}

    user.password_hash = hash_password(new_password)
    row.status = "approved"
    row.resolved_at = datetime.utcnow()
    row.resolved_by = admin_user_id
    if note:
        row.admin_note = note.strip()[:512]
    db.session.commit()
    return {"ok": True, "user": serialize_user(user), "request": _serialize(row)}
