"""Заявки на доступ при SSO без учётки в БД."""
from __future__ import annotations

from datetime import datetime

from app.core.sso import identity_lookup_emails, normalize_identity
from app.db import db
from app.modules.reference.models import SsoAccessRequest


def _pick_request_email(raw_identity: str, preferred_email: str | None = None) -> str:
    if preferred_email and "@" in preferred_email:
        return preferred_email.strip().lower()
    emails = identity_lookup_emails(raw_identity)
    if emails:
        return emails[0]
    norm, _ = normalize_identity(raw_identity)
    return norm.lower()


def get_sso_access_status(email: str) -> dict:
    row = SsoAccessRequest.query.filter_by(email=email.lower()).first()
    if not row:
        return {"pending": False, "login_attempts": 0}
    return {
        "pending": row.status == "pending",
        "login_attempts": row.login_attempts or 0,
        "status": row.status,
    }


def record_sso_access_request(
    raw_identity: str,
    *,
    preferred_email: str | None = None,
    display_name: str | None = None,
    note: str | None = None,
) -> SsoAccessRequest:
    email = _pick_request_email(raw_identity, preferred_email)
    _, local = normalize_identity(raw_identity)
    display = (display_name or "").strip() or local or email.split("@", 1)[0]
    row = SsoAccessRequest.query.filter_by(email=email).first()
    now = datetime.utcnow()
    if row:
        if row.status == "pending":
            row.login_attempts = (row.login_attempts or 0) + 1
        row.last_seen_at = now
        row.raw_identity = raw_identity
        if display_name:
            row.display_name = display
        if note:
            row.admin_note = note
    else:
        row = SsoAccessRequest(
            email=email,
            raw_identity=raw_identity,
            display_name=display,
            status="pending",
            login_attempts=1,
            first_seen_at=now,
            last_seen_at=now,
            admin_note=note or None,
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


def approve_sso_request(
    request_id: int,
    admin_user_id: int,
    *,
    note: str | None = None,
    role_codes: list[str] | None = None,
    warehouse_ids: list[int] | None = None,
    is_admin: bool = False,
) -> dict:
    """Одобрить заявку: создать/активировать пользователя и назначить роли."""
    from app.core.user_admin import provision_user_from_sso

    row = db.session.get(SsoAccessRequest, request_id)
    if not row or row.status != "pending":
        return {"error": "not_found"}
    user, created = provision_user_from_sso(
        email=row.email,
        full_name=row.display_name,
        role_codes=role_codes,
        warehouse_ids=warehouse_ids,
        is_admin=is_admin,
    )
    row.status = "approved"
    row.resolved_at = datetime.utcnow()
    row.resolved_by = admin_user_id
    if note:
        row.admin_note = note.strip()
    db.session.commit()
    return {
        "ok": True,
        "user_created": created,
        "user_id": user.id,
        "request": _serialize_request(row),
    }


def pending_sso_count() -> int:
    return SsoAccessRequest.query.filter_by(status="pending").count()
