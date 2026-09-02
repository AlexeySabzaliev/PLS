"""CRUD API справочников."""
from __future__ import annotations

from datetime import date

from flask import Blueprint, g, request

from app.core.auth import login_required
from app.core.permissions import user_has_reference_section
from app.db import db
from app.modules.reference.models import (
    Client,
    Contract,
    ContractAmendment,
    ProductType,
    Role,
    StaffPosition,
    TariffRule,
    UnitOfMeasure,
    VehiclePlate,
    VehicleType,
    Warehouse,
)

bp = Blueprint("reference_api", __name__, url_prefix="/api/reference")

CATALOGS: dict[str, tuple[type, list[str]]] = {
    "clients": (Client, ["id", "name", "security_name", "is_active"]),
    "warehouses": (Warehouse, ["id", "code", "name", "security_visit_place", "is_active"]),
    "product_types": (ProductType, ["id", "code", "name"]),
    "contracts": (Contract, ["id", "client_id", "warehouse_id", "product_type_id", "number", "status"]),
    "amendments": (ContractAmendment, ["id", "contract_id", "number", "status", "effective_from", "effective_to"]),
    "units": (UnitOfMeasure, ["id", "code", "name"]),
    "tariff_rules": (TariffRule, [
        "id", "contract_id", "amendment_id", "billing_line_code", "name",
        "unit_id", "report_role", "report_scope", "quantity_source",
        "rate_line_code", "quantity_divisor",
        "is_custom", "price_agreed", "sort_order", "valid_from", "valid_to",
    ]),
    "staff": (StaffPosition, ["id", "code", "name", "is_active"]),
    "vehicles": (VehiclePlate, ["id", "plate_number", "vehicle_type", "is_active"]),
    "vehicle_types": (VehicleType, ["id", "code", "name", "sort_order", "dimensions_label"]),
    "roles": (Role, ["id", "code", "name"]),
}

READ_ONLY_CATALOGS = frozenset({"product_types"})

SECTION_MAP = {
    "clients": "ref_clients",
    "contracts": "ref_contracts",
    "amendments": "ref_amendments",
    "warehouses": "ref_locations",
    "product_types": "ref_clients",
    "units": "ref_units",
    "tariff_rules": "ref_tariff_codes",
    "staff": "ref_staff",
    "vehicles": "ref_vehicles",
    "vehicle_types": "ref_vehicles",
    "roles": "ref_roles",
}

DATE_FIELDS = frozenset({"effective_from", "effective_to", "valid_from", "valid_to"})
BOOL_FIELDS = frozenset({"is_active", "is_custom", "price_agreed"})
INT_FIELDS = frozenset({
    "client_id", "warehouse_id", "product_type_id", "contract_id",
    "amendment_id", "unit_id", "sort_order", "vehicle_type_id",
})


def _serialize(model, fields: list[str]) -> dict:
    out = {}
    for f in fields:
        val = getattr(model, f)
        if isinstance(val, date):
            out[f] = val.isoformat()
        else:
            out[f] = val
    return out


def _coerce_field(name: str, value):
    if value is None or value == "":
        return None
    if name in BOOL_FIELDS:
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("1", "true", "yes", "on")
    if name in INT_FIELDS:
        return int(value)
    if name == "quantity_divisor":
        return float(value)
    if name in DATE_FIELDS:
        return date.fromisoformat(str(value)[:10])
    return value


def _apply_payload(model, data: dict, fields: list[str], *, for_create: bool) -> None:
    skip = {"id"} if for_create else {"id"}
    for key, value in data.items():
        if key in skip or key not in fields:
            continue
        setattr(model, key, _coerce_field(key, value))


def _check_ref_access(catalog: str) -> bool:
    section = SECTION_MAP.get(catalog, "ref_clients")
    return user_has_reference_section(g.user, section)


def _get_catalog(catalog: str):
    if catalog not in CATALOGS:
        return None, None
    return CATALOGS[catalog]


@bp.get("/meta")
@login_required
def catalog_meta():
    items = []
    for code, (_, fields) in CATALOGS.items():
        items.append({
            "code": code,
            "fields": fields,
            "read_only": code in READ_ONLY_CATALOGS,
            "section": SECTION_MAP.get(code),
        })
    return {"catalogs": items}


@bp.get("/<catalog>")
@login_required
def list_catalog(catalog: str):
    spec = _get_catalog(catalog)
    if not spec[0]:
        return {"error": "not_found"}, 404
    if not _check_ref_access(catalog):
        return {"error": "forbidden"}, 403
    model, fields = spec
    if catalog == "vehicle_types":
        rows = model.query.order_by(VehicleType.sort_order, VehicleType.id).limit(500).all()
    else:
        rows = model.query.order_by(model.id).limit(500).all()
    return {"items": [_serialize(r, fields) for r in rows]}


@bp.post("/<catalog>")
@login_required
def create_catalog_item(catalog: str):
    spec = _get_catalog(catalog)
    if not spec[0]:
        return {"error": "not_found"}, 404
    if catalog in READ_ONLY_CATALOGS:
        return {"error": "read_only"}, 400
    if not _check_ref_access(catalog):
        return {"error": "forbidden"}, 403
    model, fields = spec
    data = request.get_json(silent=True) or {}
    row = model()
    _apply_payload(row, data, fields, for_create=True)
    db.session.add(row)
    db.session.commit()
    return _serialize(row, fields), 201


@bp.put("/<catalog>/<int:item_id>")
@login_required
def update_catalog_item(catalog: str, item_id: int):
    spec = _get_catalog(catalog)
    if not spec[0]:
        return {"error": "not_found"}, 404
    if catalog in READ_ONLY_CATALOGS:
        return {"error": "read_only"}, 400
    if not _check_ref_access(catalog):
        return {"error": "forbidden"}, 403
    model, fields = spec
    row = db.session.get(model, item_id)
    if not row:
        return {"error": "not_found"}, 404
    data = request.get_json(silent=True) or {}
    _apply_payload(row, data, fields, for_create=False)
    db.session.commit()
    return _serialize(row, fields)


@bp.delete("/<catalog>/<int:item_id>")
@login_required
def delete_catalog_item(catalog: str, item_id: int):
    spec = _get_catalog(catalog)
    if not spec[0]:
        return {"error": "not_found"}, 404
    if catalog in READ_ONLY_CATALOGS:
        return {"error": "read_only"}, 400
    if not _check_ref_access(catalog):
        return {"error": "forbidden"}, 403
    model, _fields = spec
    row = db.session.get(model, item_id)
    if not row:
        return {"error": "not_found"}, 404
    db.session.delete(row)
    db.session.commit()
    return {"deleted": True, "id": item_id}
