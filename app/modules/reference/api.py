"""CRUD API справочников (заглушки с базовой логикой)."""
from __future__ import annotations

from flask import Blueprint, g, request

from app.core.auth import login_required
from app.core.permissions import user_has_reference_section
from app.db import db
from app.modules.reference.models import (
    Client,
    Contract,
    ContractAmendment,
    Role,
    StaffPosition,
    TariffRule,
    UnitOfMeasure,
    VehiclePlate,
    Warehouse,
)

bp = Blueprint("reference_api", __name__, url_prefix="/api/reference")

CATALOGS = {
    "clients": (Client, ["id", "name", "security_name", "is_active"]),
    "warehouses": (Warehouse, ["id", "code", "name", "security_visit_place", "is_active"]),
    "contracts": (Contract, ["id", "client_id", "warehouse_id", "number", "status"]),
    "amendments": (ContractAmendment, ["id", "contract_id", "number", "status", "effective_from"]),
    "units": (UnitOfMeasure, ["id", "code", "name"]),
    "tariff_codes": (TariffRule, ["id", "billing_line_code", "name", "report_role", "quantity_source"]),
    "staff": (StaffPosition, ["id", "code", "name", "is_active"]),
    "vehicles": (VehiclePlate, ["id", "plate_number", "vehicle_type", "is_active"]),
    "roles": (Role, ["id", "code", "name"]),
}


def _serialize(model, fields):
    return {f: getattr(model, f) for f in fields}


def _check_ref_access(catalog: str) -> bool:
    section_map = {
        "clients": "ref_clients",
        "contracts": "ref_contracts",
        "amendments": "ref_amendments",
        "warehouses": "ref_locations",
        "tariff_codes": "ref_tariff_codes",
        "staff": "ref_staff",
        "vehicles": "ref_vehicles",
        "roles": "ref_roles",
    }
    section = section_map.get(catalog, "ref_clients")
    return user_has_reference_section(g.user, section)


@bp.get("/<catalog>")
@login_required
def list_catalog(catalog: str):
    if catalog not in CATALOGS:
        return {"error": "not_found"}, 404
    if not _check_ref_access(catalog):
        return {"error": "forbidden"}, 403
    model, fields = CATALOGS[catalog]
    rows = model.query.order_by(model.id).limit(500).all()
    return {"items": [_serialize(r, fields) for r in rows]}


@bp.post("/<catalog>")
@login_required
def create_catalog_item(catalog: str):
    if catalog not in CATALOGS:
        return {"error": "not_found"}, 404
    if not _check_ref_access(catalog):
        return {"error": "forbidden"}, 403
    model, fields = CATALOGS[catalog]
    data = request.get_json(silent=True) or {}
    allowed = {k: v for k, v in data.items() if k in fields and k != "id"}
    row = model(**allowed)
    db.session.add(row)
    db.session.commit()
    return _serialize(row, fields), 201
