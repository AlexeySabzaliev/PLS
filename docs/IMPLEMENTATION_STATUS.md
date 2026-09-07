# Статус реализации PLS

Портал УСС + УЗнТ на `D:\PLS`. Эталон логики: `D:\Billings`.

**Последнее обновление:** 2026-09-07  
**Тесты:** `pytest -q` — **238 passed**

---

## Миграция ОУБ из Billings (2026-09-02)

### Выполнено

| Область | Статус |
|---------|--------|
| Справочники (API + `reference-ui.js`) | Импорт insert-only, `PLS_FREEZE_REFERENCE=1`, seed не перезаписывает |
| Биллинг (`calculator`, `storage_strategy`, `tariffs`) | Порт с Billings, Ariston-тесты |
| Смены склад / инвентаризация | `warehouse_shift`, `inventory_shift`, schema-driven UI |
| **Транспорт** | `transport_shift`, `transport_waybills`, `operation_daily_totals`, `uss_transport.js` |
| `report_schema`, `tariff_*`, `tariff_quantity` | Портированы |
| ФОТ (`fot_efficiency`, staff positions) | Портированы |
| Импорт данных | `flask pls import-from-billings --only=all` — insert-only (`vehicle_operations`, `operation_daily_totals`) |
| ДС-6/2024, ДС-5 | Импортированы из Billings (активные) |
| **Портал охраны** | `security_intranet.py`: разбор ТС (vehicle_plates), фильтр клиента/склада, stub/Negotiate/local DB |
| Синх «С охраны» | `POST /api/uss/transport/sync-security`, тесты E2E после OUB-подобных данных |

### Транспорт (паритет Billings)

- `transport_shift.py` — CRUD ТС, суточные допы, синх с охраной, period lock, `report_schema`
- `overtime.py` — флаг `is_overtime` по `departed_at` (пн–пт после 17:30, выходные)
- `uss_transport.js` — колонки из schema, кнопка «С охраны», бейдж security-строк
- `import-from-billings --only=shifts` — `vehicle_operations` + `operation_daily_totals`
- Тесты: `test_transport_shift`, `test_transport_waybills`, `test_security_intranet`, `test_overtime`

### Защита от перезаписи справочников

- `PLS_FREEZE_REFERENCE=1` в `.env`
- `seed_reference()` / `seed_demo()` пропускают изменения при freeze
- `fix-ariston-canonical` блокируется без `--force`
- `import-from-billings` — insert-only (`skip_existing=True` по умолчанию)

### Security (охрана)

- Парсинг госномеров: `vehicle_plates.py` (с/п, п/п, слэш, иностранные)
- `visitReason` **не** используется как номер (только `vehicleNumber` / `vehiclePlate`)
- `SECURITY_PORTAL_STUB=1` — демо-заявки для dev/E2E
- `SECURITY_USE_LOCAL_DB=1` — чтение из `security_admission_form` (если таблица есть)
- Тесты: `test_security_vehicle_plates`, `test_security_intranet`, sync после OUB-клиента

### Не перенесено (намеренно / позже)

- `LeaseBillingStrategy` — аренда/субаренда (только ОХ в prod)
- Расширенный `inventory_shift` Billings (dedupe_extra_entries, setup_status) — упрощённая модель PLS

### Добавлено (2026-09-02, вечер)

- `excel_export.py` — `GET /api/billing/export?contract_id=&year=&month=`, кнопка «Экспорт Excel» в `/uss/billing`
- `amendments_overview.py` — `GET /api/reference/amendments-overview`, блок обзора на вкладке «Доп. соглашения»

## УЗнТ: заявки на перевозку (2026-09-07)

Полный CRUD раздела «заявки на перевозку» реализован по паттерну `uss/transport`.

- **Модель** `TransportRequest` (`transport_requests`) в `app/modules/uznt/models.py`:
  номер (автогенерация `UZNT-ГГГГММДД-NNNN`), дата, клиент, площадка, маршрут,
  груз (объём/вес), количество/единица, тип ТС, число машин, цена, статус, приоритет,
  примечания, аудит (created/updated_by, created/updated_at).
- **Статусы**: `new / accepted / in_transit / delivered / cancelled`; **приоритеты**: `normal / high`.
- **Сервис** `app/modules/uznt/services.py` — `list/get/create/update/delete`, валидация
  (дата, клиент/площадка/тип ТС, уникальность номера, статус/приоритет), сериализация,
  `request_meta` (списки справочников без доступа к разделу «Справочники»).
- **API** `app/modules/uznt/api.py` — blueprint `/api/uznt`: `GET/POST /requests`,
  `GET/PUT/DELETE /requests/<id>`, `GET /meta`. Права: `requests_transport` (просмотр+правка),
  `requests_view_all` (только просмотр), админ — всё.
- **Веб** `GET /uznt/requests` (модуль УЗнТ): шаблоны `frontend/templates/uznt/base.html`,
  `uznt/requests.html`, JS `uznt_requests.js` + `uznt_common.js`, стили в `main.css`.
  Заглушка раздела из `stub_routes.py` заменена реальной страницей.
- **section_guard**: добавлен `/api/uznt` → `requests_transport` (техработы блокируют и API УЗнТ).
- **Миграция** `migrations/versions/019_uznt_requests.py`.
- **Тесты** `tests/test_uznt_requests.py` (7): CRUD-поток, валидация, уникальность номера,
  права (403 для роли без секции), meta, страница, админ. Итого **238 passed** (231 + 7).

---

## Рефакторинг и отчёты (2026-09-07)

### Биллинг (сверка Ariston / август)

- `BillingCalculator` теперь считает по факт-границам `period_from`/`period_to`, а не фиксирует месяц (валидация `period_from > period_to`).
- `StorageBillingStrategy` и `operational_revenue` принимают явные границы периода; `daily_operational_revenue` умеет срез по периоду.
- Включены кастомные строки тарифа с ручными источниками (`manual_vehicle`/`manual_daily`) — решена задача из `REFACTORING_PLAN.md` №2.
- Тест `test_billing_ariston_august.py::test_ariston_august_billing_matches_excel` — **passed** (эталон = Excel август, переносом из Billings). Сентябрь: данные будут наполняться вручную с 2026-09-08, проверка по кодам и формулам.

### Охрана (портал security, задача №1)

- `_fetch_raw_requests`: при отсутствии live-SSO `SECURITY_USE_LOCAL_DB` делает offline-fallback на локальную БД с меткой источника `local_db_offline` (при error — `local_db_fallback`).
- Тест `test_security_sql_import.py::test_fetch_from_local_db` приведён к новому контракту (`src.startswith("local_db")`).

### Отчёт отклонений «заявлено в охране vs приехало» (задача №4)

- `arrival_gap_report.py` — агрегаты по дням: `planned`, `arrived`, `no_show`, `processed`, `gap = planned − arrived`, `confirmation_rate = processed / planned × 100`.
- API `GET /api/uss/transport/arrival-gap` + шаблон `uss/arrival_gap.html` + JS `uss_arrival_gap.js` + пункт навигации.
- Тест `test_arrival_gap_report.py` — формулы по кодам (source=`security`), `warehouse_not_found`.

### Прочее

- `tests/test_password.py::test_change_password` — исправлен предсуществующий сбой: проверка входа теперь через HTTP-эндпоинт, а не прямой вызов `login_user_password()` вне request-контекста.

---

## Сводка по фазам

| Фаза | Описание | Готовность |
|------|----------|------------|
| 0 | Auth/SSO, роли, оболочка | ~80% |
| 1 | Схема БД, миграции, backup/restore | ~90% |
| 2 | Операции УСС (склад/инвентаризация/транспорт+охрана) | ~95% |
| 3 | report_schema, справочники, UI | ~90% |
| 4 | Биллинг, сверка Ariston | ~85% |
| 5 | Prod cutover | ~30% (данные импортированы) |

---

## Ссылки

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [BILLING_DATA_ROLES.md](./BILLING_DATA_ROLES.md)
- [USS_ARCHITECTURE.md](./USS_ARCHITECTURE.md)
