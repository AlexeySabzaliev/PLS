"""Базовые шаблоны операционных процессов."""
from __future__ import annotations

REPORT_ROLES = frozenset({
    "transport_logistics",
    "warehouse_logistics",
    "inventory_management",
})

BASE_PROCESS_TEMPLATES: dict[str, dict] = {
    "transport_logistics": {
        "code": "transport_logistics",
        "name": "Транспортная логистика",
        "report_role": "transport_logistics",
        "sections": ["vehicle_operations", "period_inputs", "day_confirm"],
        "vehicle_fixed_fields": [
            {"field": "volume_document_m3", "label": "Объём, м³"},
            {"field": "handling_type_code", "label": "Тип обработки"},
            {"field": "extra_handling_m3", "label": "Доп. обработка, м³"},
            {"field": "extra_document_set_qty", "label": "Доп. комплект"},
            {"field": "registered_at", "label": "Прибытие"},
            {"field": "departed_at", "label": "Убытие"},
        ],
        "period_inputs": [],
        "inventory_areas": [],
        "inventory_extra": [],
    },
    "warehouse_logistics": {
        "code": "warehouse_logistics",
        "name": "Складская логистика",
        "report_role": "warehouse_logistics",
        "sections": ["period_inputs", "day_confirm"],
        "vehicle_fixed_fields": [],
        "period_inputs": [],
        "inventory_areas": [],
        "inventory_extra": [],
    },
    "inventory_management": {
        "code": "inventory_management",
        "name": "Управление запасами",
        "report_role": "inventory_management",
        "sections": ["inventory_areas", "inventory_extra", "period_inputs", "day_confirm"],
        "vehicle_fixed_fields": [],
        "period_inputs": [],
        "inventory_areas": [],
        "inventory_extra": [],
    },
}

# Примеры линий процесса (сидируются в миграции/тестах)
EXAMPLE_LINE_CONFIGS: dict[str, dict] = {
    "ariston_standard": {
        "enabled_sections": ["period_inputs", "day_confirm"],
        "extra_billing_line_codes": ["valve_gluing"],
        "form_fields": [
            {
                "billing_line_code": "valve_gluing",
                "label": "Подклейка клапанов",
                "input_kind": "period",
                "quantity_source": "manual_daily",
            }
        ],
        "ui_labels": {"title": "Склад Аристон"},
    },
    "gazprom_logistics": {
        "enabled_sections": ["vehicle_operations", "period_inputs", "day_confirm"],
        "extra_billing_line_codes": ["custom_waybill_type"],
        "form_fields": [
            {
                "field": "waybill_doc_type",
                "label": "Тип документа",
                "section": "vehicle_operations",
            }
        ],
        "validation_rules": {"waybill_doc_type": {"required": True}},
        "ui_labels": {"title": "Транспорт Газпром"},
    },
}
