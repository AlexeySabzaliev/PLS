"""Конфигураторы линий процессов: модели и слияние схем."""
from __future__ import annotations

from datetime import date

from app.db import db
from app.modules.processes.templates import BASE_PROCESS_TEMPLATES, REPORT_ROLES


class ProcessLine(db.Model):
    __tablename__ = "process_lines"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    base_process = db.Column(db.String(64), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    config = db.relationship("ProcessLineConfig", uselist=False, back_populates="process_line")


class ProcessLineConfig(db.Model):
    __tablename__ = "process_line_config"
    id = db.Column(db.Integer, primary_key=True)
    process_line_id = db.Column(db.Integer, db.ForeignKey("process_lines.id"), unique=True, nullable=False)
    config_json = db.Column(db.JSON, default=dict, nullable=False)
    process_line = db.relationship("ProcessLine", back_populates="config")


def _deep_merge_dict(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge_dict(result[key], val)
        elif isinstance(val, list) and key in result and isinstance(result[key], list):
            result[key] = result[key] + [x for x in val if x not in result[key]]
        else:
            result[key] = val
    return result


def _tariff_fields_for_contract(contract_id: int, on_date: date, role: str) -> dict:
    """Динамические поля из ставок ДС."""
    from app.modules.uss.services.report_schema import schema_for_contract_role

    sch = schema_for_contract_role(contract_id, on_date, role)
    return {
        "period_inputs": sch.get("period_inputs", []),
        "inventory_areas": sch.get("inventory_areas", []),
        "inventory_extra": sch.get("inventory_extra", []),
        "vehicle_inputs": sch.get("vehicle_inputs", []),
    }


def merge_process_schema(base: dict, line_config: dict | None) -> dict:
    """Слияние базового шаблона и конфигурации линии."""
    cfg = line_config or {}
    enabled = set(cfg.get("enabled_sections") or base.get("sections", []))
    schema = {
        "base_process": base["code"],
        "report_role": base.get("report_role"),
        "sections": [s for s in base.get("sections", []) if s in enabled],
        "vehicle_fixed_fields": list(base.get("vehicle_fixed_fields", [])),
        "period_inputs": list(base.get("period_inputs", [])),
        "inventory_areas": list(base.get("inventory_areas", [])),
        "inventory_extra": list(base.get("inventory_extra", [])),
        "form_fields": list(cfg.get("form_fields") or []),
        "validation_rules": dict(cfg.get("validation_rules") or {}),
        "ui_labels": dict(cfg.get("ui_labels") or {}),
        "extra_billing_line_codes": list(cfg.get("extra_billing_line_codes") or []),
    }
    for ff in cfg.get("form_fields") or []:
        kind = ff.get("input_kind")
        if kind == "period":
            schema["period_inputs"].append(ff)
        elif kind == "inventory_area":
            schema["inventory_areas"].append(ff)
        elif kind == "inventory_extra":
            schema["inventory_extra"].append(ff)
        elif kind == "vehicle":
            schema.setdefault("vehicle_inputs", []).append(ff)
    if cfg.get("ui_labels"):
        schema["ui_labels"] = _deep_merge_dict(schema["ui_labels"], cfg["ui_labels"])
    return schema


def resolve_process_schema(
    line_id: int,
    *,
    contract_id: int | None = None,
    on_date: date | None = None,
) -> dict:
    """Итоговая схема для линии: шаблон + overrides + ставки ДС."""
    line = db.session.get(ProcessLine, line_id)
    if not line or not line.is_active:
        return {"error": "process_line_not_found"}
    base = BASE_PROCESS_TEMPLATES.get(line.base_process)
    if not base:
        return {"error": "unknown_base_process", "base_process": line.base_process}
    cfg = line.config.config_json if line.config else {}
    schema = merge_process_schema(base, cfg)
    schema["line_id"] = line.id
    schema["line_code"] = line.code
    schema["line_name"] = line.name
    if contract_id and on_date and schema.get("report_role") in REPORT_ROLES:
        tariff_part = _tariff_fields_for_contract(contract_id, on_date, schema["report_role"])
        for key in ("period_inputs", "inventory_areas", "inventory_extra", "vehicle_inputs"):
            existing_codes = {
                x.get("billing_line_code") for x in schema.get(key, []) if x.get("billing_line_code")
            }
            for row in tariff_part.get(key, []):
                if row["billing_line_code"] not in existing_codes:
                    schema.setdefault(key, []).append(row)
    return schema
