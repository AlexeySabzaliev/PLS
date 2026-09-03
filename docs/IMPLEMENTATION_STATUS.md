# Статус реализации PLS

Портал УСС + УЗнТ на `D:\PLS`. Эталон логики: `D:\Billings`.

**Последнее обновление:** 2026-09-02  
**Тесты:** `pytest -q` — **155 passed**

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
