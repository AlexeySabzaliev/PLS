"""Справочники: клиенты, договоры, ставки, персонал, ТС."""
from __future__ import annotations

from datetime import date, datetime

from app.db import db


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Client(db.Model, TimestampMixin):
    __tablename__ = "clients"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    security_name = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class Warehouse(db.Model, TimestampMixin):
    __tablename__ = "warehouses"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    security_visit_place = db.Column(db.String(64))
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class ProductType(db.Model):
    __tablename__ = "product_types"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class Contract(db.Model, TimestampMixin):
    __tablename__ = "contracts"
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False)
    product_type_id = db.Column(db.Integer, db.ForeignKey("product_types.id"), nullable=False)
    number = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(32), default="active", nullable=False)
    billing_config = db.Column(db.JSON, default=dict)
    client = db.relationship("Client")
    warehouse = db.relationship("Warehouse")
    product_type = db.relationship("ProductType")


class ContractAmendment(db.Model, TimestampMixin):
    __tablename__ = "contract_amendments"
    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("contracts.id"), nullable=False)
    number = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(32), default="draft", nullable=False)
    effective_from = db.Column(db.Date, nullable=False)
    effective_to = db.Column(db.Date)
    source_file_path = db.Column(db.String(512))
    contract = db.relationship("Contract")


class UnitOfMeasure(db.Model):
    __tablename__ = "units_of_measure"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(16), unique=True, nullable=False)
    name = db.Column(db.String(64), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class TariffRule(db.Model, TimestampMixin):
    __tablename__ = "tariff_rules"
    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("contracts.id"), nullable=False)
    amendment_id = db.Column(db.Integer, db.ForeignKey("contract_amendments.id"), nullable=False)
    billing_line_code = db.Column(db.String(64), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey("units_of_measure.id"))
    report_role = db.Column(db.String(64))
    report_scope = db.Column(db.String(64))
    quantity_source = db.Column(db.String(64))
    rate_line_code = db.Column(db.String(64))
    quantity_divisor = db.Column(db.Numeric(12, 3), default=1, nullable=False)
    is_custom = db.Column(db.Boolean, default=False)
    price_agreed = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    valid_from = db.Column(db.Date, nullable=False)
    valid_to = db.Column(db.Date)
    rate_ex_vat = db.Column(db.Numeric(14, 4))
    formula = db.Column(db.String(64))
    unit = db.relationship("UnitOfMeasure")


class StaffPosition(db.Model):
    __tablename__ = "staff_positions"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    is_active = db.Column(db.Boolean, default=True)


class VehiclePlate(db.Model):
    __tablename__ = "vehicle_plates"
    id = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(db.String(32), unique=True, nullable=False)
    vehicle_type = db.Column(db.String(64))
    is_active = db.Column(db.Boolean, default=True)


class VehicleType(db.Model):
    """Справочник типов ТС для транспортного отчёта."""
    __tablename__ = "vehicle_types"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(256), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    dimensions_label = db.Column(db.String(128))


class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)


class SectionPermission(db.Model):
    __tablename__ = "section_permissions"
    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    section_code = db.Column(db.String(64), nullable=False)
    role = db.relationship("Role")


class User(db.Model, TimestampMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    full_name = db.Column(db.String(255))
    password_hash = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)


class UserRole(db.Model):
    __tablename__ = "user_roles"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    role = db.relationship("Role")


class UserWarehouseAccess(db.Model):
    __tablename__ = "user_warehouse_access"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False)


class SectionMaintenance(db.Model):
    """Заглушка раздела или роли (техобслуживание)."""
    __tablename__ = "section_maintenance"
    id = db.Column(db.Integer, primary_key=True)
    target_type = db.Column(db.String(16), nullable=False)  # section | role
    target_key = db.Column(db.String(64), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    __table_args__ = (db.UniqueConstraint("target_type", "target_key"),)


class SsoAccessRequest(db.Model):
    """Заявка на доступ: SSO-пользователь есть в AD, но нет в БД."""
    __tablename__ = "sso_access_requests"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    raw_identity = db.Column(db.String(255))
    display_name = db.Column(db.String(255))
    status = db.Column(db.String(32), default="pending", nullable=False)
    login_attempts = db.Column(db.Integer, default=1, nullable=False)
    first_seen_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = db.Column(db.DateTime)
    resolved_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    admin_note = db.Column(db.String(512))
