# Эталон-бриф: PLS — Портал УСС + УЗнТ

> Самодостаточное описание «что делаем и как это должно работать», ориентируясь на эталон (Billings / Excel). Готов для вставки в промпт.

## 1. Что это за проект
Переписываем/портируем **«Эталон» (легаси ОУБ / Billings с Excel-выгрузками)** в новый портал **PLS**. Идеал: **каждая строка счёта, каждая цифра в отчёте PLS должна совпадать с эталонным Excel**. Практически сверяется по **кодам и формулам**, а не «на глаз».

Каноническая база: **клиент Аристон, склад Стрельна, договор «АР-БСХ 24», ДС-6/2024** (с 2026-08-01), историческое ДС-5 (2025-05-01 … 2026-07-31).

## 2. Домены и модули
- **УЗнТ** — заявки на транспортировку (переиспользуем существующий Transport).
- **УСС (бывший ОУБ)** — операционный учёт и биллинг ответхранения:
  - `app/modules/reference` — справочники (клиенты, договоры, ДС, ставки `tariff_rules`);
  - `app/modules/uss` — операции смен: транспорт (`vehicle_operations`), склад и инвентаризация (`operation_daily_totals`, `shift_reports`);
  - `app/modules/billing` — калькуляция (`calculator.py`, `storage_strategy.py`, `aggregates.py`, `operational_revenue.py`, `period_lock.py`).

## 3. Три роли сбора данных
| Роль (`report_role`) | Привязка к ТС | Основной источник |
|---|---|---|
| `transport_logistics` | да | `vehicle_operations` + часть `operation_daily_totals` |
| `warehouse_logistics` | нет | `operation_daily_totals` |
| `inventory_management` | нет | `shift_reports` + `operation_daily_totals` |

День «закрыт» (`is_day_confirmed`), когда по всем ролям `ShiftDayConfirmation.confirmed_at` проставлен.

## 4. Биллинг — как ДОЛЖНО работать (эталон)

### 4.1 Тарифные коды — ядро сверки
Логика держится на **кодах строк ставок** (`billing_line_code` в `tariff_rules`).

- **Стандартные системные коды** (`STANDARD_BILLING_CODES` в `tariff_codes.py`): `storage_area_fixed`, `storage_area_extra`, `manual_m3`, `mechanized_m3`, `vehicle_docs`, `extra_vehicle_docs`, `repack_units`, `overtime_m3`, `inventory_hours`, `elco_drain_hours`, `valve_gluing`, `vietnam_stickering`, `flue_stickering`, `elco_passports`, `extra_vehicle_docs_rf`, `extra_vehicle_docs_rb` и др.
- **Кастомные коды** (`is_custom`, часто `custom_…`): у клиента/договора «свой» код для того же типа работ (результат объединения проектов — разные имена одной услуги у разных источников).
- **Правило эталона:** агрегация количеств идёт под **стандартными** кодами. Кастомный код «работает» только при маппинге на стандартный (`BILLING_MERGE_INTO`) или после приведения к **каноническим** кодам (`fix_ariston_canonical`).

### 4.2 Источник количества (`quantity_source`, `QTY_SRC`)
- системные (из `vehicle_operations`: например `vehicle_docs` = число машин; `manual_m3`/`mechanized_m3` = объёмы);
- суточные итоги (`operation_daily_totals`);
- поля смены;
- **ручной источник** (`manual_vehicle`, `manual_daily`, …) — вводит оператор. **Ручные участвуют в счёте** и не отбрасываются.

Схема: `tariff_quantity.py` даёт дефолты для известных кодов; для остальных — из полей ставки. Схема формы строится динамически на дату смены по активным ставкам ДС.

### 4.3 Расчёт периода
`BillingCalculator.calculate_period(contract_id, period_from, period_to)`:
1. грузит договор и тип продукта;
2. валидирует `period_from <= period_to` (иначе `invalid_period`);
3. берёт активные ставки на период из `tariff_rules`;
4. агрегирует количество (`aggregates.py`);
5. мапит кастомные коды в стандартные;
6. применяет формулу (`rate_times_qty` и др. в `storage_strategy.py`), ставку дня (`_effective_rate`);
7. считает **двухуровневое хранение на площади** (`area_mode = two_tier`, `fixed_m2days`);
8. возвращает строки счёта + агрегаты (транспорт/склад/инвентаризация).

`operational_revenue.py` — дневная выручка **без хранения** по календарным дням: ручная/мех. обработка (неразнесённый объём документа → в механообработку), машины, сверхурочные.

### 4.4 Сверка с эталоном
- Эталоны: `tests/fixtures/ariston_billing/` (листы: Billing, ТС, склад, инвентаризация).
- `test_ariston_august_billing_matches_excel` — эталон **August 2026**, сверяет счёт с Excel. Сейчас passed; расхождение точно объяснялось 4 кастомными строками с ручным `QTY_SRC`.
- Правило из `BILLING_DATA_ROLES.md`: биллинг-калькулятор до сверки с Excel не менять.

## 5. Охрана (портал КПП)
`security_intranet.py` тянет заявки с портала охраны:
- доступ SSO/Negotiate; без live-SSO — **offline-fallback на локальную БД** (`SECURITY_USE_LOCAL_DB`) с меткой `local_db_offline`/`local_db_fallback`;
- разбор госномеров `vehicle_plates.py`; заявка → `vehicle_operations` (`security_request_id`);
- демо/заглушка (`SECURITY_PORTAL_STUB`, `mock-…`) для dev/E2E на боевых экранах **не показывается**.

## 6. Отчёты
- **ФОТ** (`fot_efficiency.py`) — берёт операционную выручку (`operational_revenue` с периодом), сопоставляет со штатом позиций склада. Эталон: `test_fot_report` — passed.
- **Отклонения по прибытию** (`arrival_gap_report.py`): `planned` = строки `source="security"`; `arrived` = `registered_at` и `arrival_status ≠ no_show`; `no_show` = `arrival_status == no_show`; `processed` = `processed_at`; `gap = planned − arrived`; `confirmation_rate = processed / planned × 100`.

## 7. Канонические данные = результат объединения проектов
`fix_ariston_canonical.py` — идемпотентная «причёсывающая» правка к единому эталону:
- клиент «Аристон» → канонический; склад `spb1` → `strelna`; договор `STR-OH-ARISTON` → `АР-БСХ 24`;
- ДС `ДС-6`/`ДС-01/2025` → `ДС-6/2024`; ДС-5 исторический;
- тарифы сводятся к **каноническому набору**: 8 основных `DS6_CORE_CODES` + `DS6_EXTRA_CODES`; тримятся дубли и `custom_*`.

## 8. Принципы верификации
1. **Стандартные коды** — источник истины для количеств; кастомные либо маппятся, либо приводятся каноникой.
2. Каждый отчёт/формула фиксируется **тестом по кодам и формулам**: `test_billing_ariston_august`, `test_arrival_gap_report`, `test_fot_report`, `test_security_*`.
3. Итог: **226 тестов зелёные**, коммит `e75aa80` запушен в `origin/main`.
4. Осталось: **сентябрьские живые данные** (с 2026-09-08) → живая сверка ФОТ и отчёта отклонений; контроль, что тарифы сентября под стандартными/каноническими кодами.