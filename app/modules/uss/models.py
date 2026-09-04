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
    billing_document_qty = db.Column(db.Integer, nullable=False, default=1)
    registered_at = db.Column(db.DateTime)
    departed_at = db.Column(db.DateTime)
    report_quantities = db.Column(db.JSON, default=dict)
    vehicle_type_id = db.Column(db.Integer, db.ForeignKey("vehicle_types.id"))
    source = db.Column(db.String(32), nullable=False, default="manual")
    security_request_id = db.Column(db.String(64))
    arrival_status = db.Column(db.String(32), nullable=False, default="expected")
    processed_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    processed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    waybills = db.relationship(
        "VehicleWaybill",
        back_populates="operation",
        cascade="all, delete-orphan",
        order_by="VehicleWaybill.sort_order",
    )


class VehicleWaybill(db.Model):
    """Накладные по строке ТС (несколько на одну машину)."""
    __tablename__ = "vehicle_waybills"
    id = db.Column(db.Integer, primary_key=True)
    vehicle_operation_id = db.Column(
        db.Integer, db.ForeignKey("vehicle_operations.id", ondelete="CASCADE"), nullable=False,
    )
    waybill_number = db.Column(db.String(256))
    mx_number = db.Column(db.String(256))
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    operation = db.relationship("VehicleOperation", back_populates="waybills")


class VehicleOperationAuditLog(db.Model):
    """История изменений строки ТС."""
    __tablename__ = "vehicle_operation_audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    vehicle_operation_id = db.Column(
        db.Integer, db.ForeignKey("vehicle_operations.id", ondelete="CASCADE"), nullable=False,
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    user_name = db.Column(db.String(255))
    action = db.Column(db.String(64), nullable=False)
    changes = db.Column(db.JSON)
    snapshot = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


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


class WarehouseStaffPosition(db.Model):
    """Штат ответхранения: должность, оклад/мес, количество."""
    __tablename__ = "warehouse_staff_positions"
    id = db.Column(db.Integer, primary_key=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    monthly_rate = db.Column(db.Numeric(18, 2), nullable=False, default=0)
    headcount = db.Column(db.SmallInteger, nullable=False, default=1)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    versions = db.relationship(
        "WarehouseStaffPositionVersion",
        back_populates="position",
        cascade="all, delete-orphan",
    )


class WarehouseStaffPositionVersion(db.Model):
    """История окладов/численности штата ФОТ."""
    __tablename__ = "warehouse_staff_position_versions"
    id = db.Column(db.Integer, primary_key=True)
    position_id = db.Column(
        db.Integer,
        db.ForeignKey("warehouse_staff_positions.id", ondelete="CASCADE"),
        nullable=False,
    )
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    monthly_rate = db.Column(db.Numeric(18, 2), nullable=False, default=0)
    headcount = db.Column(db.SmallInteger, nullable=False, default=1)
    valid_from = db.Column(db.Date, nullable=False)
    valid_to = db.Column(db.Date)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    position = db.relationship("WarehouseStaffPosition", back_populates="versions")
