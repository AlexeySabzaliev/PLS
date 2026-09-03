# Архитектура USS (УСС) — отчёты по ролям

## Размещение полей в UI

| Тип | `quantity_source` | `report_scope` | Где в UI |
|-----|-------------------|----------------|----------|
| Зависимое от ТС, ручное | `manual_vehicle` | `vehicle` | **Колонки таблицы ТС** (после «Доп. обработка», до «Прибытие») |
| Зависимое от ТС, авто | `auto_vehicle` | — | Системные колонки ТС (объём, тип обработки, доп. комплект) |
| Независимое от ТС, ручное | `manual_daily` / `manual_inventory` | `period` | Вкладка **«Дополнительный»** по роли |
| Параметр договора | `auto_contract_param` | — | Без ввода в смене (биллинг из ДС) |

## Транспорт (`transport_logistics`)

- Таблица ТС — основной ввод: 1 строка = 1 машина.
- `manual_vehicle` (elco_passports, extra_vehicle_docs_rf/rb и др.) — колонки в таблице, значения в `vehicle_operations.report_quantities`.
- `manual_daily` (напр. подклейка клапанов `is_custom` у Аристон) — только вкладка «Дополнительный», `operation_daily_totals`.
- Вкладка «Дополнительный» **не** показывает поля, привязанные к ТС.

## Склад / УЗ

- `warehouse_logistics`: только `period_inputs` на экране смены.
- `inventory_management`: `inventory_areas` + `inventory_extra` на вкладке «Дополнительный».
- Если у роли появятся `manual_vehicle` — read-only колонки идентификации ТС + редактируемые поля ДС (без правки основных полей ТС).

## Канон Аристон (ДС-6/2024)

- Договор: `АР-БСХ 24`, склад `strelna`, клиент `Аристон Термо Рус`.
- Подклейка клапанов (`valve_gluing`, `is_custom`) — вкладка «Дополнительный».
- ELCO/RF/RB (`elco_passports`, `extra_vehicle_docs_rf`, `extra_vehicle_docs_rb`) — колонки строки ТС.

## Импорт из Billings (одноразовый)

```bash
# 1. Dry-run
flask pls import-from-billings --dry-run

# 2. Только справочники
flask pls import-from-billings --only=reference

# 3. Смены (после справочников)
flask pls import-from-billings --only=shifts

# 4. Полный импорт
flask pls import-from-billings --only=all

# 5. Заморозить справочники от сидов
set PLS_FREEZE_REFERENCE=1

# 6. Очистка сирот (сначала dry-run)
flask pls db-vacuum
flask pls db-vacuum --yes
```

Повторный импорт **не перезаписывает** существующие записи (insert-only). `--force` разрешает обновление. `fix-ariston-canonical` требует `--force` при `PLS_FREEZE_REFERENCE=1`.

## DELETE в справочниках

`DELETE /api/reference/<catalog>/<id>` — **hard delete**. При нарушении FK возвращается `409 constraint_violation`; удалите зависимости или `flask pls db-vacuum --yes`.

## Файлы

| Слой | Файлы |
|------|-------|
| Схема | `app/modules/uss/services/report_schema.py` |
| API смен | `transport_shift.py`, `warehouse_shift.py`, `inventory_shift.py` |
| UI | `uss_transport.js`, `uss_common.js`, `uss_warehouse.js`, `uss_inventory.js` |
| Импорт | `app/seeds/import_from_billings.py`, `app/cli.py` |
