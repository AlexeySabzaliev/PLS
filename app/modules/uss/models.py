"""Операционные таблицы УСС."""
from __future__ import annotations

from datetime import date, datetime

from app.db import db


class VehicleOperation(db.Model):
    __tablename__ = "vehicle_operations"
    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("contracts.id"), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False)
    operation_date = db.Column(db.Date, nullable=False)
    plate_number = db.Column(db.String(32))
    operation_type_code = db.Column(db.String(32))
    tractor_plate = db.Column(db.String(64))
    trailer_plate = db.Column(db.String(64))
    waybill_number = db.Column(db.String(256))
    mx1_number = db.Column(db.String(256))
    mx3_number = db.Column(db.String(256))
    seal_number = db.Column(db.String(128))
    torg2_number = db.Column(db.String(128))
    volume_document_m3 = db.Column(db.Numeric(12, 3))
    handling_type_code = db.Column(db.String(32))
    extra_handling_m3 = db.Column(db.Numeric(12, 3))
    extra_document_set_qty = db.Column(db.Integer)
    registered_at = db.Column(db.DateTime)
    departed_at = db.Column(db.DateTime)
    report_quantities = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class OperationDailyTotal(db.Model):
    __tablename__ = "operation_daily_totals"
    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("contracts.id"), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False)
    report_date = db.Column(db.Date, nullable=False)
    billing_line_code = db.Column(db.String(64), nullable=False)
    quantity = db.Column(db.Numeric(14, 3), nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ShiftReport(db.Model):
    __tablename__ = "shift_reports"
    id = db.Column(db.Integer, primary_key=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False)
    report_date = db.Column(db.Date, nullable=False)
    area_entries = db.Column(db.JSON, default=dict)
    extra_entries = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ShiftDayConfirmation(db.Model):
    __tablename__ = "shift_day_confirmations"
    id = db.Column(db.Integer, primary_key=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False)
    report_date = db.Column(db.Date, nullable=False)
    report_role = db.Column(db.String(64), nullable=False)
    confirmed_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    confirmed_at = db.Column(db.DateTime, default=datetime.utcnow)
