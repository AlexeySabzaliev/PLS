# Статус реализации PLS

Портал УСС + УЗнТ на `D:\PLS`. Эталон логики: `D:\Billings`; `D:\transport` — только для переноса кода, не целевой репозиторий.

**Последнее обновление:** 2026-09-02  
**Тесты:** `pytest -v` — 11 passed (целевое состояние на момент scaffold)

---

## Сводка по фазам

| Фаза | Описание | Готовность | Следующий шаг |
|------|----------|------------|---------------|
| 0 | Auth/SSO, роли, оболочка портала | ~70% | Полный portal shell, проверка SSO на IIS |
| 1 | Схема БД, модели | ~75% | PostgreSQL в dev, seed prod |
| 2 | Операции УСС (транспорт/склад/инвентаризация) | ~55% | UI редактирования, period_lock, waybills |
| 3 | report_schema, справочники, конфигураторы, UI из схемы | ~35% | Порт `report_schema` из Billings, schema-driven UI |
| 4 | Биллинг, сверка Ariston Excel | ~5% | Порт calculator + fixtures и тесты |
| 5 | Prod cutover, консолидация, отключение Billings | ~10% | GitHub, миграция данных, deploy |

---

## Фаза 0 — Auth/SSO, роли, portal shell

**Сделано:** Flask factory, config, `.env.example`; Windows SSO (headers / windows / oidc), dev bypass; сессия, `POST /api/auth/login`, матрица permissions; главная с навигацией УСС и справочников.

**Осталось:** полноценная оболочка портала (navbar, роли в UI); страницы-заглушки УЗнТ; OIDC end-to-end при необходимости; проверка SSO в production.

---

## Фаза 1 — DB schema, models

**Сделано:** SQLAlchemy-модели; **миграция `001_initial`** (все таблицы, индексы, unique); `flask pls init-db`, `seed-reference`, `seed-admin`, `seed-demo`; `docker-compose.yml` (PostgreSQL 16).

**Осталось:** seed для prod-окружения; при импорте данных — паритет с миграциями Billings.

---

## Фаза 2 — USS operations

**Сделано:** `transport_shift` (list/save, daily totals); `warehouse_shift` + `operation_daily_totals`; `shift_day_confirm` + API; `inventory_shift` (базовый JSON); `/api/uss/*`.

**Осталось:** полный UI смен (сейчас transport — в основном read-only); warehouse/inventory UI; `period_lock`, overtime, security; `transport_waybills`, `shift_vehicle`, `vehicle_plates`; полная логика inventory по `report_schema`.

---

## Фаза 3 — report_schema, configurators, UI

**Сделано:** `BASE_PROCESS_TEMPLATES`, `resolve_process_schema`, merge + tariffs; API `/api/process-lines`, `GET …/schema`; CRUD справочников (list/create); пресеты `ariston_standard`, `gazprom_logistics`; заготовка `admin/reference.html`.

**Осталось:** порт `report_schema.py`, `tariff_quantity`, `tariff_report`, `tariff_report_lines`; полный CRUD и валидация; **динамический UI** из схемы; admin UI справочников (как `catalog-ui.js` в Billings).

---

## Фаза 4 — Billing

**Сделано:** stub `BillingCalculator`, `POST /api/billing/calculate`; README для fixtures Ariston.

**Осталось:** порт `billing/calculator.py`, `tariffs.py`, `excel_export.py`; fixtures и `test_ariston_billing_ref.py`; `verify_billing_cycle.py`, reconciliation; связка billing ↔ tariff rules process_line.

---

## Фаза 5 — Cutover

**Сделано:** локальный git-репозиторий, документация в `docs/`.

**Осталось:** публикация на GitHub; миграция prod-данных Billings → PLS PostgreSQL; deploy (IIS/SSO, `DATABASE_URL`); переключение пользователей; модуль УЗнТ из transport или отдельный трек.

---

## Приоритеты (кратко)

1. **P0:** GitHub push (`gh auth login`).
2. **P1:** ~~Alembic, seed, PostgreSQL~~ — сделано; проверить prod deploy.
3. **P2:** Schema-driven UI УСС; порт report_schema / tariff_* из Billings.
4. **P3:** Billing + Ariston tests.
5. **P4:** УЗнТ и prod cutover.

---

## Ссылки

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [PROCESS_CONFIGURATORS.md](./PROCESS_CONFIGURATORS.md)
- [BILLING_DATA_ROLES.md](./BILLING_DATA_ROLES.md)
