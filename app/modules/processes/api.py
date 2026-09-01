"""API конфигураторов линий процессов."""
from __future__ import annotations

from datetime import date

from flask import Blueprint, g, request

from app.core.auth import login_required
from app.core.permissions import user_has_uss_section
from app.db import db
from app.modules.processes.schema_resolver import ProcessLine, ProcessLineConfig, resolve_process_schema

bp = Blueprint("process_lines_api", __name__, url_prefix="/api/process-lines")


def _line_to_dict(line: ProcessLine) -> dict:
    return {
        "id": line.id,
        "code": line.code,
        "name": line.name,
        "base_process": line.base_process,
        "client_id": line.client_id,
        "is_active": line.is_active,
        "config": line.config.config_json if line.config else {},
    }


@bp.get("")
@login_required
def list_lines():
    if not user_has_uss_section(g.user, "uss_process_lines"):
        return {"error": "forbidden"}, 403
    lines = ProcessLine.query.order_by(ProcessLine.code).all()
    return {"items": [_line_to_dict(l) for l in lines]}


@bp.get("/<int:line_id>")
@login_required
def get_line(line_id: int):
    line = db.session.get(ProcessLine, line_id)
    if not line:
        return {"error": "not_found"}, 404
    return _line_to_dict(line)


@bp.put("/<int:line_id>")
@login_required
def update_line(line_id: int):
    if not user_has_uss_section(g.user, "uss_process_lines"):
        return {"error": "forbidden"}, 403
    line = db.session.get(ProcessLine, line_id)
    if not line:
        return {"error": "not_found"}, 404
    data = request.get_json(silent=True) or {}
    for field in ("name", "base_process", "client_id", "is_active"):
        if field in data:
            setattr(line, field, data[field])
    if "config" in data:
        if not line.config:
            line.config = ProcessLineConfig(process_line_id=line.id, config_json=data["config"])
            db.session.add(line.config)
        else:
            line.config.config_json = data["config"]
    db.session.commit()
    return _line_to_dict(line)


@bp.get("/<int:line_id>/schema")
@login_required
def get_schema(line_id: int):
    contract_id = request.args.get("contract_id", type=int)
    on_date_raw = request.args.get("on_date")
    on_date = date.fromisoformat(on_date_raw) if on_date_raw else date.today()
    schema = resolve_process_schema(line_id, contract_id=contract_id, on_date=on_date)
    if schema.get("error"):
        return schema, 404
    return schema
