"""Заявки на доступ при SSO без учётки в БД."""
from __future__ import annotations

from datetime import datetime

from app.core.sso import normalize_identity
from app.db import db
from app.modules.reference.models import SsoAccessRequest, User


def record_sso_access_request(raw_identity: str) -> SsoAccessRequest:
    email, local = normalize_identity(raw_identity)
    email = email.lower()
    display = local or email.split("@", 1)[0]
    row = SsoAccessRequest.query.filter_by(email=email).first()
    now = datetime.utcnow()
    if row:
        if row.status == "pending":
            row.login_attempts = (row.login_attempts or 0) + 1
        row.last_seen_at = now
        row.raw_identity = raw_identity
        if not row.display_name:
            row.display_name = display
    else:
        row = SsoAccessRequest(
            email=email,
            raw_identity=raw_identity,
            display_name=display,
            status="pending",
            login_attempts=1,
            first_seen_at=now,
            last_seen_at=now,
        )
        db.session.add(row)
    db.session.commit()
    return row


def list_pending_sso_requests() -> list[dict]:
    rows = (
        SsoAccessRequest.query.filter_by(status="pending")
        .order_by(SsoAccessRequest.last_seen_at.desc())
        .all()
    )
    return [_serialize_request(r) for r in rows]


def _serialize_request(row: SsoAccessRequest) -> dict:
    return {
        "id": row.id,
        "email": row.email,
        "display_name": row.display_name,
        "raw_identity": row.raw_identity,
        "status": row.status,
        "login_attempts": row.login_attempts,
        "first_seen_at": row.first_seen_at.isoformat() if row.first_seen_at else None,
        "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
        "admin_note": row.admin_note,
    }


def dismiss_sso_request(request_id: int, admin_user_id: int, note: str | None = None) -> dict:
    row = db.session.get(SsoAccessRequest, request_id)
    if not row or row.status != "pending":
        return {"error": "not_found"}
    row.status = "dismissed"
    row.resolved_at = datetime.utcnow()
    row.resolved_by = admin_user_id
    row.admin_note = (note or "").strip() or None
    db.session.commit()
    return {"ok": True, "request": _serialize_request(row)}


def approve_sso_request(request_id: int, admin_user_id: int, *, note: str | None = None) -> dict:
    """Одобрить: создать пользователя без ролей (роли назначает админ)."""
    row = db.session.get(SsoAccessRequest, request_id)
    if not row or row.status != "pending":
        return {"error": "not_found"}
    user = User.query.filter(db.func.lower(User.email) == row.email.lower()).first()
    created = False
    if not user:
        user = User(
            email=row.email,
            full_name=row.display_name or row.email.split("@", 1)[0],
            is_active=True,
            is_admin=False,
        )
        db.session.add(user)
        created = True
    elif not user.is_active:
        user.is_active = True
    row.status = "approved"
    row.resolved_at = datetime.utcnow()
    row.resolved_by = admin_user_id
    row.admin_note = (note or "").strip() or None
    db.session.commit()
    return {
        "ok": True,
        "user_created": created,
        "user_id": user.id,
        "request": _serialize_request(row),
    }


def pending_sso_count() -> int:
    return SsoAccessRequest.query.filter_by(status="pending").count()
