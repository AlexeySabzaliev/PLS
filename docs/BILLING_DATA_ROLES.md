# Модель ролей операционных данных (ПЛС)

> Архитектурное правило миграции ОУБ → портал ПЛС (**УЗнТ** + **УСС**).  
> Каноническая копия для репозитория PLS.  
> **Биллинг-калькулятор** (`app/modules/billing/calculator.py`) — фаза 4, **не менять** до сверки с Excel.

## Модули портала

| Модуль | Назначение | Blueprint |
|--------|------------|-----------|
| **УЗнТ** | Заявки на транспортировку (GP, материалы, тендеры) | существующий Transport |
| **УСС** | Операционный учёт и биллинг ответственного хранения (бывший ОУБ) | `uss` (`/uss/`, `/api/uss/`) |

### Заглушки UI (фаза 0–2)

При переносе нужно **воссоздать заглушки разделов** для обоих модулей — пользователь с правами видит пункт меню и страницу «в разработке», а не 404:

- **УСС** — `GET /uss/`, справочники, смены (transport / warehouse / inventory), биллинг, отчёты
- **УЗнТ** — разделы заявок и справочников, для которых ещё нет полного UI в объединённом портале

Секции прав: `app/core/permissions.py` (`REQUEST_SECTIONS`, `USS_SECTIONS`).

## Эталоны Excel (Ariston billing)

- **Репозиторий:** `tests/fixtures/ariston_billing/` (README) или `ARISTON_BILLING_FIXTURES_PATH` в `.env`
- На **других листах** workbook — выгрузки по ролям (ТС, склад, инвентаризация)
- Парсер листа Billing: `backend/scripts/billing_excel_ref.py`

## Три роли сбора данных

| Роль | `report_role` | Привязка к ТС | Основной контур ввода |
|------|---------------|---------------|------------------------|
| Транспортная логистика | `transport_logistics` | **Да** (основной объём) + суточные итоги без ТС | `vehicle_operations` + часть `operation_daily_totals` |
| Складская логистика | `warehouse_logistics` | **Нет** | `operation_daily_totals` |
| Управление запасами | `inventory_management` | **Нет** | `shift_reports` + `operation_daily_totals` |

Назначение ролей ставкам: `tariff_quantity.py`, схема полей: `report_schema.py`.

---

## Допуслуги без привязки к ТС (динамический набор)

> **Не фиксированный enum.** Состав полей ввода определяется **ставками активного ДС** по договору, а не жёстким списком в коде UI.

### Принцип

**Сколько клиентов — столько допуслуг:** у каждого договора свой набор строк `tariff_rules` с уникальным `billing_line_code`, названием (`name`), единицей и ролью отчёта. Один и тот же тип работы у разных клиентов может иметь разные коды (`custom_valve`, `agreed_1`, `repack_units` и т.д.).

Источник истины:

| Слой | Что даёт |
|------|----------|
| `tariff_rules` | `billing_line_code`, `name`, `report_role`, `report_scope`, `quantity_source`, `is_custom` |
| `report_schema.py` | динамическая схема формы: `period_inputs`, `inventory_areas`, `inventory_extra` |
| `tariff_quantity.py` | дефолты для **известных** системных кодов (`LINE_QUANTITY_REGISTRY`); для остальных — из полей ставки |

Схема строится на дату смены:

```text
tariff_rules (активное ДС, contract_id, on_date)
  → report_schema.schema_for_contract_role(conn, contract_id, on_date, role)
  → списки полей для UI и валидации сохранения
```

### Куда пишутся объёмы (по `quantity_source`)

| `quantity_source` | Хранение | Роли (типично) |
|-------------------|----------|----------------|
| `manual_daily` | `operation_daily_totals` (`billing_line_code`, `quantity`, `report_date`) | `warehouse_logistics`, иногда `transport_logistics` |
| `manual_inventory` | `shift_reports.extra_entries` / `area_entries` (JSON по `billing_line_code`) | `inventory_management` |
| `auto_vehicle` | поля `vehicle_operations` | `transport_logistics` (это **с привязкой к ТС**, не допуслуга без машин) |

Ключ агрегации везде — **`billing_line_code`** из ставки, не имя колонки в БД и не константа во frontend.

### Иллюстрации (не эталон для всех договоров)

Примеры из реальных договоров (в т.ч. Аристон) — **только для понимания**, не полный перечень:

| Пример работы | Возможный `billing_line_code` | Роль / хранение |
|---------------|------------------------------|-----------------|
| Подклейка клапанов гофрокоробов | `valve_gluing`, `custom_valve`, … | по ДС → `manual_daily` или `manual_inventory` |
| Паспорта ELCO | `elco_passports`, … | по ДС |
| Слив котлов ELCO | `elco_drain_hours` | `warehouse_logistics` → `manual_daily` |
| Переупаковка | `repack_units`, `custom_pallet`, … | `inventory_management` → `extra_entries` |
| Стикерование дымоходов | `flue_stickering`, … | `warehouse_logistics` → `manual_daily` |

Новая ставка в ДС с `accounting_mode` / `report_role` и ручным `quantity_source` **автоматически** появляется в схеме отчёта без правок enum в коде.

### Антипаттерны при миграции в УСС

- ❌ Хардкод списка допуслуг в JS/Python (`INVENTORY_STANDARD_CODES`, фиксированные колонки формы)
- ❌ Ожидание, что у всех клиентов одинаковый набор `billing_line_code`
- ❌ Привязка складских/инвентаризационных допов к `vehicle_operations`
- ✅ Читать схему из API (`report_schema` / `schema_for_contract_role`) и сохранять по `billing_line_code`

---

## 1. Транспортная логистика

### Основной ввод — строка ТС

Каждая машина = строка в `vehicle_operations` (+ waybills, времена, тип обработки):

| Данные | Поле / сущность | Учёт в биллинге |
|--------|-----------------|-----------------|
| Объём документов, м³ | `volume_document_m3` | авто по типу обработки (мех/ручная) |
| Тип обработки | `handling_type_code` | выбор мех/ручная на строке ТС |
| Прибытие / убытие | `registered_at`, `departed_at` | сверхурочные |
| Путевые листы | `transport_waybills` | справочно |

### Доп. поля на форме машины (кол-во × ставка)

| Поле UI | Поле БД | Ставка (`billing_line_code`) |
|---------|---------|------------------------------|
| Доп. комплект документов | `extra_document_set_qty` | `extra_vehicle_docs` |
| Доп. обработка, м³ | `extra_handling_m3` | `extra_manual_m3` (мех/ручная — от `handling_type_code` на строке) |

Источник количества: `auto_vehicle` / поля транспорта (`TRANSPORT_FIELD_CODES` в `tariff_quantity.py`).

### Суточные итоги без привязки к машине

Ставки роли `transport_logistics` с `quantity_source = manual_daily` попадают в **`period_inputs`** схемы (`report_schema`) — набор **зависит от ДС**, см. раздел «Допуслуги без привязки к ТС».

**Хранение:** `operation_daily_totals` (`billing_line_code`, `quantity`, `contract_id`, `warehouse_id`, `report_date`).

Сервис: `operation_daily_totals.py`. Пример иллюстрации (один из договоров): суточный итог по `vehicle_docs` — не универсальное поле для всех клиентов.

---

## 2. Складская логистика

> **Не зависит от машин.** Любые упоминания привязки складской роли к `vehicle_operations` / `report_quantities` на ТС — устаревшие; при переносе в УСС исправить.

Оператор вводит **допработы по дню** на уровне склада/договора. Поля формы — **`period_inputs`** из `report_schema` (динамически из `tariff_rules`).

Иллюстрации (не фиксированный перечень): слив котлов ELCO (`elco_drain_hours`), стикерование (`flue_stickering`) — у другого клиента будут другие коды и названия.

**Хранение:** только `operation_daily_totals` (суточный итог по `billing_line_code`).

**Не использовать:** `report_quantities` на `vehicle_operations`, `warehouse_saved_at` на строке ТС как основной контур складской роли.

Сервис (целевой): `warehouse_shift.py` → дневная форма + `upsert_daily_totals`.  
*Текущий Billings-код ещё содержит legacy-путь через ТС — при миграции переписать под эту модель.*

---

## 3. Управление запасами

> **Не привязано к ТС.** Ввод по дню, **не на одном клиенте** — несколько договоров/клиентов на одном складе.

### Ежедневный ввод

| Тип данных | Хранение | Откуда берётся состав |
|------------|----------|------------------------|
| Доп. площади | `shift_reports.area_entries` | `inventory_areas` в схеме (коды вроде `storage_area_extra` — по ДС) |
| Прочие допы УЗ | `shift_reports.extra_entries` | `inventory_extra` — **все** ставки `manual_inventory` роли УЗ, кроме area-слота |
| Суточные строки `manual_daily` в роли УЗ | `operation_daily_totals` | если так задано в ставке |

Схема: `report_schema` → `inventory_areas`, `inventory_extra`. Legacy-колонки `inventory_hours`, `repack_units` в `shift_reports` — исторический путь; целевой контракт — JSON `extra_entries` по `billing_line_code`.

### Закрытие месяца (биллинг)

- **Средняя доп. площадь** за период → `storage_area_extra` × ставка × дни
- **Фикс. площадь** из параметра ДС → `storage_area_fixed` (авто, без ежедневного ввода)
- **Допы** (переупаковка, часы и т.д.) — из накопленных `shift_reports` / `operation_daily_totals`

Сервис: `inventory_shift.py`.

---

## Разделение таблиц (сводка)

```
┌─────────────────────────┬──────────────────────────────────────────────────┐
│ Таблица                 │ Кто пишет                                        │
├─────────────────────────┼──────────────────────────────────────────────────┤
│ vehicle_operations      │ transport_logistics (только строки ТС)           │
│ transport_waybills      │ transport_logistics                                │
│ operation_daily_totals  │ transport (суточные допы), warehouse (все),      │
│                         │ inventory (если manual_daily по ДС)                │
│ shift_reports           │ inventory_management (area_entries, extras)        │
│ shift_day_confirmations │ все три роли (отдельная запись на роль/день)     │
└─────────────────────────┴──────────────────────────────────────────────────┘
```

### `quantity_source` → таблица

| `quantity_source` | Куда пишется |
|-------------------|--------------|
| `auto_vehicle` | поля `vehicle_operations` |
| `manual_vehicle` | `vehicle_operations.report_quantities` (только transport, если есть по ДС) |
| `manual_daily` | `operation_daily_totals` |
| `manual_inventory` | `shift_reports` (`area_entries` / `extra_entries`) |
| `auto_contract_param` | параметр ДС, без операционного ввода |

---

## Закрытие дня

Все **три роли** участвуют в закрытии смены, но **контуры данных разные**:

| Роль | Что должно быть заполнено до confirm | Таблица подтверждения |
|------|--------------------------------------|------------------------|
| `transport_logistics` | строки ТС + суточные допы transport | `shift_day_confirmations` |
| `warehouse_logistics` | `operation_daily_totals` за день | `shift_day_confirmations` |
| `inventory_management` | `shift_reports` (+ daily при необходимости) | `shift_day_confirmations` |

День считается полностью закрытым, когда подтверждены **все три** роли (`shift_day_confirm.py`, `GET /day-summary`).

Подтверждение **не блокирует** последующее редактирование (явная отметка, не hard lock).

---

## Связь с кодом

### Billings (источник логики)

| Роль | Сервисы |
|------|---------|
| transport | `transport_shift.py`, `transport_waybills.py`, `operation_daily_totals.py` |
| warehouse | `warehouse_shift.py` (→ переписать под daily), `operation_daily_totals.py` |
| inventory | `inventory_shift.py`, `operation_daily_totals.py` |
| закрытие дня | `shift_day_confirm.py` |

### Transport / УСС (целевой модуль)

| Роль Billings | Секции УСС |
|---------------|------------|
| `transport_logistics` | `uss_ops_transport`, `uss_catalog_vehicle_types` |
| `warehouse_logistics` | `uss_ops_warehouse` |
| `inventory_management` | `uss_ops_inventory` |

### Фазы миграции

| Фаза | Содержание | Calculator |
|------|------------|------------|
| 2 | `vehicle_operations`, `operation_daily_totals`, `shift_reports`, `shift_day_confirmations`, UI смен | — |
| 3 | `report_schema`, справочники, `tariff_quantity` (read) | — |
| 4 | `billing/calculator.py`, сверка с Excel | **да** |

**Правило фаз 2–3:** явно разделять `vehicle_operations` vs `operation_daily_totals` vs `shift_reports`; не смешивать inventory/warehouse в транспортные строки.

---

## Сверка с эталоном

```bash
cd backend
pytest tests/test_ariston_billing_ref.py -v          # парсер Excel, без БД
python scripts/verify_billing_cycle.py --verify    # полная сверка (фаза 4+)
```
