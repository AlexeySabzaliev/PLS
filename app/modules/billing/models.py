"""Модели биллинга."""
from __future__ import annotations

from datetime import datetime

from app.db import db

# draft — операции открыты; under_review/confirmed/invoiced — блок для не-admin
PERIOD_STATUSES = ("draft", "under_review", "confirmed", "invoiced")


class BillingPeriod(db.Model):
    __tablename__ = "billing_periods"
    __table_args__ = (
        db.UniqueConstraint(
            "contract_id", "period_year", "period_month",
            name="uq_billing_period_contract_ym",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("contracts.id"), nullable=False)
    period_year = db.Column(db.Integer, nullable=False)
    period_month = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(32), nullable=False, default="draft")
    total_ex_vat = db.Column(db.Numeric(14, 2))
    locked_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    locked_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
