# ПЛС — Портал логистических сервисов

Единая точка входа: **УЗнТ** (заявки) + **УСС** (операционный учёт и биллинг ответственного хранения).

## Быстрый старт

```bash
cd D:\PLS
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Настройте DATABASE_URL (PostgreSQL) или оставьте SQLite по умолчанию

set FLASK_APP=run.py
flask db upgrade   # после инициализации миграций
python run.py
```

Откройте http://localhost:5000

## SSO (Windows)

В `.env`:

```env
SSO_ENABLED=true
SSO_MODE=headers          # или windows | oidc
SSO_USER_HEADER=Remote-User
SSO_EMAIL_DOMAIN=bsh-ru.ru
SSO_DEV_IDENTITY=BSH\your.login   # только dev, не production
```

Пользователь должен существовать в БД с тем же email. Роли — в `user_roles`.

Локальный вход (dev): `SSO_ALLOW_PASSWORD_LOGIN=true`, `POST /api/auth/login`.

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

Если репозиторий ещё не создан на GitHub:

```bash
gh auth login
gh repo create PLS --public --source=. --remote=origin --push
```

## Документация

- [Архитектура](docs/ARCHITECTURE.md)
- [Модель ролей данных](docs/BILLING_DATA_ROLES.md)
- [Конфигураторы процессов](docs/PROCESS_CONFIGURATORS.md)
