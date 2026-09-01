"""Тесты слияния схем конфигураторов."""
from datetime import date

from app.modules.processes.schema_resolver import merge_process_schema, resolve_process_schema
from app.modules.processes.templates import BASE_PROCESS_TEMPLATES, EXAMPLE_LINE_CONFIGS


def test_merge_adds_custom_fields():
    base = BASE_PROCESS_TEMPLATES["warehouse_logistics"]
    merged = merge_process_schema(base, EXAMPLE_LINE_CONFIGS["ariston_standard"])
    assert "valve_gluing" in merged["extra_billing_line_codes"]
    codes = [x["billing_line_code"] for x in merged["period_inputs"]]
    assert "valve_gluing" in codes
    assert merged["ui_labels"].get("title") == "Склад Аристон"


def test_transport_line_keeps_vehicle_section(app):
    with app.app_context():
        from app.modules.processes.schema_resolver import ProcessLine

        line = ProcessLine.query.filter_by(code="gazprom_logistics").first()
        schema = resolve_process_schema(line.id)
        assert "vehicle_operations" in schema["sections"]
        assert schema["validation_rules"].get("waybill_doc_type", {}).get("required")


def test_schema_includes_tariffs_from_contract(app):
    with app.app_context():
        from app.modules.processes.schema_resolver import ProcessLine
        from app.modules.reference.models import Contract

        line = ProcessLine.query.filter_by(code="ariston_standard").first()
        contract = Contract.query.first()
        schema = resolve_process_schema(
            line.id,
            contract_id=contract.id,
            on_date=date(2026, 1, 15),
        )
        codes = [x["billing_line_code"] for x in schema["period_inputs"]]
        assert "valve_gluing" in codes
