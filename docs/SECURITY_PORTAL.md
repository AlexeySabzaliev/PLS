# Портал охраны (security.bsh-ru.ru)

Интеграция **не связана** с входом пользователей в ПЛС. Пользователь, открывший транспортную смену, не передаёт свою сессию на портал охраны.

## Два контура

| Контур | Назначение | Prod |
|--------|------------|------|
| **Вход в ПЛС** | email + пароль | Только пароль |
| **Портал охраны** | заявки на въезд ТС | **SSO сервера** (учётка службы Windows) |

## Prod: серверный SSO (Negotiate)

На IIS/Windows-сервере приложение обращается к `https://security.bsh-ru.ru` от имени **учётки службы** (не пользователя браузера):

```env
FLASK_ENV=production
SECURITY_AUTH_MODE=negotiate
SECURITY_USE_NEGOTIATE=true
SECURITY_AUTO_BROWSER_COOKIES=0
SECURITY_USE_LOCAL_DB=0
```

Требования:

- Пул приложений / служба запущена под доменной учёткой с доступом к порталу охраны
- Установлен `requests-negotiate-sspi` (Windows)
- При необходимости настроены SPN и делегирование Kerberos

Проверка: `flask pls security-refresh-session` — метод `negotiate`.

## Dev / тесты (временно)

Текущая локальная конфигурация для разработки:

```env
SECURITY_USE_LOCAL_DB=1
# SECURITY_OFFLINE_ONLY=1   # только кэш, без сети
# SECURITY_AUTO_BROWSER_COOKIES=1  # cookies Yandex/Edge на ПК разработчика
# SECURITY_PORTAL_STUB=1    # демо-заявки
```

| Режим | Переменные | Когда |
|-------|------------|-------|
| Локальный кэш + live | `SECURITY_USE_LOCAL_DB=1` | ответы портала сохраняются в `security_admission_form` |
| Только кэш | `SECURITY_OFFLINE_ONLY=1` | без запросов к порталу |
| Браузер (dev) | `SECURITY_AUTH_MODE=browser` | SSO с ПК разработчика |
| Cookie вручную | `SECURITY_API_COOKIE` / `SECURITY_COOKIE_FILE` | операционное обновление сессии |
| Заглушка | `SECURITY_PORTAL_STUB=1` | E2E без портала |

## CLI

```bash
flask pls security-refresh-session   # обновить сессию (режим зависит от SECURITY_AUTH_MODE)
flask pls security-fetch-portal      # скачать заявки в локальный кэш
flask pls security-import-sql        # импорт SQL-дампа IT
```

Файл сессии (режим cookie/browser): `instance/security_session.txt`.

## Код

- `app/modules/uss/services/security_config.py` — режим аутентификации
- `app/modules/uss/services/security_session.py` — HTTP-сессия к порталу
- `app/modules/uss/services/security_intranet.py` — заявки и статус для UI
