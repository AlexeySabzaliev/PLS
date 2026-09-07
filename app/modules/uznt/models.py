"""Модель заявок на перевозку (УЗнТ): транспорт_requests."""
from __future__ import annotations

from datetime import datetime

from app.db import db

# Статусы заявки (от создания до закрытия).
TRANSPORT_REQUEST_STATUSES = (
    "new",
    "accepted",
    "in_transit",
    "delivered",
    "cancelled",
)

TRANSPORT_REQUEST_STATUS_LABELS = {
    "new": "Новая",
    "accepted": "Принята",
    "in_transit": "В пути",
    "delivered": "Доставлена",
    "cancelled": "Отменена",
}

# Приоритеты заявки.
TRANSPORT_REQUEST_PRIORITIES = (
    "normal",
    "high",
)

TRANSPORT_REQUEST_PRIORITY_LABELS = {
    "normal": "Обычный",
    "high": "Высокий",
}


class TransportRequest(db.Model):
    """Заявка на перевозку (GP / материалы): маршрут, груз, транспорт, статус."""

    __tablename__ = "transport_requests"
    id = db.Column(db.Integer, primary_key=True)
    # Номер заявки — уникален, генерируется при создании при необходимости.
    number = db.Column(db.String(64), nullable=False)
    request_date = db.Column(db.Date, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey("warehouses.id"), nullable=False)
    # Маршрут.
    from_location = db.Column(db.String(255))
    to_location = db.Column(db.String(255))
    # Груз.
    cargo_name = db.Column(db.String(255))
    cargo_volume_m3 = db.Column(db.Numeric(12, 3))
    cargo_weight_t = db.Column(db.Numeric(12, 3))
    quantity = db.Column(db.Numeric(14, 3), nullable=False, default=1)
    unit = db.Column(db.String(32), nullable=False, default="pcs")
    # Транспорт.
    vehicle_type_id = db.Column(db.Integer, db.ForeignKey("vehicle_types.id"))
    trucks_count = db.Column(db.Integer, nullable=False, default=1)
    # Стоимость / статус.
    price = db.Column(db.Numeric(14, 2))
    status = db.Column(db.String(32), nullable=False, default="new")
    priority = db.Column(db.String(16), nullable=False, default="normal")
    notes = db.Column(db.Text)
    # Аудит.
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )