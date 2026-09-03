# Резервное копирование БД ПЛС

Резервные копии создаются командой `flask pls backup` и восстанавливаются через `flask pls restore`.

Поддерживаются **PostgreSQL** (`pg_dump` / `psql`) и **SQLite** (дамп через `iterdump`).

## Переменные окружения

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `DATABASE_URL` | `sqlite:///instance/pls.db` | Подключение к БД |
| `PLS_BACKUP_DIR` | `backups/` (от корня проекта) | Каталог для `.sql` файлов |
| `PLS_BACKUP_RETENTION` | пусто | Сколько **последних** копий хранить (остальные удаляются после backup) |

Имена файлов: `pls_YYYYMMDD_HHMMSS.sql`.

## Ручной бэкап

```bash
cd D:\PLS
flask pls backup
```

С ограничением числа копий:

```bash
flask pls backup --retention 30
```

Если `--retention` не указан, используется `PLS_BACKUP_RETENTION` из `.env`.

## Восстановление (production)

1. Остановите приложение (IIS / служба), чтобы не было активных сессий к БД.
2. Убедитесь, что есть свежий бэкап: `dir backups` или `ls backups`.
3. Восстановите (перед этим автоматически создаётся бэкап текущего состояния):

```bash
flask pls restore --file backups\pls_20260902_030000.sql --yes
```

Флаги:

- `--yes` — без интерактивного подтверждения (для скриптов).
- `--no-safety-backup` — не создавать копию перед восстановлением (не рекомендуется на prod).

4. Запустите приложение и проверьте: `flask pls db-check`.

## Планировщик Windows (Task Scheduler)

Скрипт: `scripts/backup_pls.ps1`

1. **Task Scheduler** → Create Task.
2. **Triggers:** Daily, 02:00.
3. **Actions:** Start a program  
   - Program: `powershell.exe`  
   - Arguments: `-NoProfile -ExecutionPolicy Bypass -File "D:\PLS\scripts\backup_pls.ps1"`
4. Учётная запись с правами на `PLS_BACKUP_DIR` и `pg_dump` в PATH.
5. В `D:\PLS\.env` задайте `DATABASE_URL`, `PLS_BACKUP_DIR`, `PLS_BACKUP_RETENTION`.

Логи: `backups/backup.log`.

## Cron (Linux)

```cron
0 2 * * * cd /opt/pls && ./scripts/backup_pls.sh >> backups/backup.log 2>&1
```

## Требования

- **PostgreSQL:** `pg_dump` и `psql` в PATH.
- **SQLite:** файл БД должен существовать.
- На prod: `PLS_BACKUP_DIR=D:\backups\pls` (абсолютный путь).

## Проверка

```bash
pytest tests/test_db_backup.py -v
```
