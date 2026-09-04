# ПЛС — Портал логистических сервисов

Единая точка входа: **УЗнТ** (заявки) + **УСС** (операционный учёт и биллинг ответственного хранения).

## Быстрый старт

> **Cursor:** откройте `PLS.code-workspace` (не Billings/OUB), Run Mode = Run Everything.  
> Подробно: [docs/CURSOR_DEV.md](docs/CURSOR_DEV.md)

### PostgreSQL (рекомендуется)

```powershell
cd D:\PLS
docker compose up -d postgres
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env

set FLASK_APP=run.py
flask pls init-db --demo
python run.py
```

### SQLite (без Docker)

```powershell
# В .env закомментируйте DATABASE_URL или укажите:
# DATABASE_URL=sqlite:///instance/pls.db
flask pls init-db --demo
python run.py
```

Откройте http://localhost:5000  
Логин: `admin@bsh-ru.ru` / `admin` (см. `.env` → `PLS_ADMIN_*`)

### CLI

| Команда | Описание |
|---------|----------|
| `flask pls init-db` | миграции + справочники + admin |
| `flask pls init-db --demo` | + демо Аристон, ТС, daily total |
| `flask pls seed-reference` | только справочники и роли |
| `flask pls seed-demo` | демо-данные |
| `flask pls db-check` | проверка подключения к БД |

## Вход

Email и пароль. Восстановление — кнопка «Забыли пароль?» на главной; админ обрабатывает заявку в справочнике «Пользователи и доступ».

Локальный dev: `admin@bsh-ru.ru` / `admin` (см. `.env` → `PLS_ADMIN_*`).

## Структура

```
app/
  core/           — auth, SSO, permissions
  modules/
    reference/    — справочники (CRUD API)
    processes/    — конфигураторы линий процессов
    uss/          — операции смен (transport, warehouse, inventory)
    billing/      — калькулятор (заглушка, фаза 4)
docs/             — ARCHITECTURE, BILLING_DATA_ROLES, PROCESS_CONFIGURATORS
frontend/         — шаблоны и статика
tests/
```

## API (основное)

| Endpoint | Описание |
|----------|----------|
| `GET /api/health` | Проверка сервиса |
| `GET /api/process-lines` | Список линий процессов |
| `GET /api/process-lines/{id}/schema` | Итоговая схема формы |
| `GET /api/uss/transport/shift` | Транспортная смена |
| `GET /api/reference/{catalog}` | Справочники |

## Тесты

```bash
pytest -v
```

## GitHub


> **GitHub (2026-09-02):** CLI установлен (C:\Program Files\GitHub CLI\gh.exe), но сессия не авторизована. Выполните gh auth login, затем команду ниже. Если gh не в PATH — вызывайте по полному пути.

Если репозиторий ещё не создан на GitHub:

```bash
gh auth login
gh repo create PLS --public --source=. --remote=origin --push
```

## Документация

- [Архитектура](docs/ARCHITECTURE.md)
- [Модель ролей данных](docs/BILLING_DATA_ROLES.md)
- [Статус реализации](docs/IMPLEMENTATION_STATUS.md)
- [Конфигураторы процессов](docs/PROCESS_CONFIGURATORS.md)
