# Конфигураторы линий процессов

## Зачем

Один базовый процесс (`transport_logistics`, `warehouse_logistics`, `inventory_management`) описывает общую модель сбора данных. **Линия процесса** настраивает клиентскую «изюминку» без форков кода.

## Шаги: новая линия

### 1. Выберите базовый процесс

| Код | Когда использовать |
|-----|-------------------|
| `transport_logistics` | Учёт ТС, путевые, суточные допы transport |
| `warehouse_logistics` | Только суточные работы склада (без машин) |
| `inventory_management` | Площади и допы УЗ |

Шаблоны: `app/modules/processes/templates.py` → `BASE_PROCESS_TEMPLATES`.

### 2. Создайте запись `process_lines`

```json
POST /api/process-lines  (через админку или SQL)
{
  "code": "ariston_standard",
  "name": "Аристон стандарт",
  "base_process": "warehouse_logistics",
  "client_id": 1
}
```

### 3. Задайте `config_json`

```json
{
  "enabled_sections": ["period_inputs", "day_confirm"],
  "extra_billing_line_codes": ["valve_gluing"],
  "form_fields": [
    {
      "billing_line_code": "valve_gluing",
      "label": "Подклейка клапанов",
      "input_kind": "period",
      "quantity_source": "manual_daily"
    }
  ],
  "validation_rules": {},
  "ui_labels": { "title": "Склад Аристон" }
}
```

Ставки из ДС подмешиваются автоматически при запросе схемы с `contract_id` и `on_date`.

### 4. Проверьте схему

```http
GET /api/process-lines/{id}/schema?contract_id=1&on_date=2026-08-01
```

Ответ содержит объединённые `period_inputs`, `vehicle_fixed_fields`, `validation_rules`, `ui_labels`.

### 5. Привяжите UI

Страницы УСС читают схему и рендерят поля динамически (фаза 3+). Сохранение — по `billing_line_code` в соответствующую таблицу (см. `BILLING_DATA_ROLES.md`).

## Примеры в репозитории

| code | base_process | Особенность |
|------|--------------|-------------|
| `ariston_standard` | warehouse_logistics | `valve_gluing` в period_inputs |
| `gazprom_logistics` | transport_logistics | `waybill_doc_type` на строке ТС |

## Антипаттерны

- ❌ Отдельный Python-модуль на каждого клиента
- ❌ Хардкод колонок в JS
- ✅ Всё через `resolve_process_schema` + `tariff_rules`
