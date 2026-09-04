# Развёртывание ПЛС за IIS с Windows SSO

В продакшене Flask почти всегда работает под **служебной учёткой** (или Local System).  
`GetUserNameExW` на сервере возвращает **эту** учётку, а не пользователя в браузере на `10.9.31.34`.

Правильная схема:

```
Браузер (доменный пользователь)
    → Negotiate/NTLM
IIS (Windows Authentication)
    → LOGON_USER / REMOTE_USER в окружение
Flask (SSO_MODE=headers, SSO_ALLOW_WINDOWS_FALLBACK=false)
    → поиск users по UPN / SAM
```

## Переменные окружения (production)

```env
FLASK_ENV=production
SSO_ENABLED=true
SSO_MODE=headers
SSO_ALLOW_WINDOWS_FALLBACK=false
SSO_ALLOW_PASSWORD_LOGIN=true
SSO_EMAIL_DOMAIN=bsh-ru.ru
```

`SSO_MODE=auto` с `SSO_ALLOW_WINDOWS_FALLBACK=false` — то же самое: только заголовки/IIS, без учётки процесса.

## IIS + HttpPlatformHandler

1. Установить **HttpPlatformHandler** (IIS).
2. Сайт: **Anonymous Authentication — Off**, **Windows Authentication — On** (Negotiate, NTLM).
3. Скопировать `deploy/web.config` в корень сайта, поправить пути к Python и `run.py`.
4. Убедиться, что в логе `/api/auth/sso/config` поле `identity_source` = **`headers`**, а `resolved_identity` — UPN пользователя (`alexey.sabzaliev@bsh-ru.ru`).

При успешной настройке IIS передаёт в процесс переменные `LOGON_USER`, `AUTH_USER` — приложение читает их из `request.environ`.

## IIS как reverse proxy (ARR)

Если Flask слушает `127.0.0.1:5000` отдельно:

1. Windows Auth на сайте IIS.
2. URL Rewrite → proxy на `http://127.0.0.1:5000/{R:0}`.
3. В **Allowed Server Variables** разрешить и пробросить `AUTH_USER` / `LOGON_USER` как заголовок `X-Remote-User` (или настроить `Remote-User`).

Без проброса идентификатора клиента Flask увидит только службу на `:5000`.

## Проверка

| `identity_source` | Значение |
|-------------------|----------|
| `headers` | OK — пришёл пользователь с IIS/прокси |
| `windows` | Только dev: учётка процесса Python |
| `none` | IIS не передал логин — настраивать прокси |

## Локальная разработка

- `python run.py` на рабочей станции: `SSO_MODE=auto`, `SSO_ALLOW_WINDOWS_FALLBACK=true` — UPN текущего пользователя ПК.
- Без домена: `PLS_SSO_STUB=1` или вход по паролю.

## Пользователи в БД

Email в `users` = корпоративный UPN. Дополнительно — поле **SSO-алиасы** (`sabzaliev`), если IIS отдаёт SAM `BSH-RU\sabzaliev`.
