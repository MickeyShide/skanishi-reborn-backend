# Техническое задание на backend Compactics

Версия документа: 1.0  
Дата: 2026-06-29  
Область: только backend, без frontend, CSS, HTML и клиентской логики.

## 1. Цель проекта

Backend Compactics обслуживает Telegram Mini App / web-приложение для коллекционирования предметов. Пользователь авторизуется через Telegram `initData`, получает access-token и refresh-cookie, просматривает каталог предметов, сканирует QR/startapp-секреты, получает предметы в свою коллекцию, видит свой прогресс и рейтинг по конкретному предмету.

Цель переписывания с нуля: сохранить текущую бизнес-идею, но построить backend как production-ready сервис:

- без хардкода секретов;
- с безопасной авторизацией и refresh-сессиями;
- с валидируемыми входными DTO;
- с предсказуемыми JSON-ответами;
- с корректными транзакциями и защитой от гонок;
- с индексами под реальные запросы;
- с нормальным логированием, healthcheck, миграциями и тестами.

## 2. Границы системы

Входит в backend:

- HTTP API;
- Telegram initData authentication;
- JWT access-token;
- refresh-token через HttpOnly cookie;
- работа с PostgreSQL;
- кэширование счетчиков и rate limit через Redis;
- миграции Alembic;
- фоновый Telegram bot worker, если он нужен как отдельный процесс;
- OpenAPI-документация;
- health/readiness endpoints;
- structured logging.

Не входит:

- frontend;
- CSS/HTML;
- Telegram Mini App UI;
- генерация QR-картинок на клиенте;
- платежи;
- публичная админ-панель как UI.

## 3. Рекомендуемый стек

Язык и рантайм:

- Python 3.13 или последняя стабильная версия, поддерживаемая используемыми библиотеками.
- Асинхронный backend.

HTTP/API:

- FastAPI.
- Uvicorn как ASGI server.
- Pydantic v2 для DTO и settings.

База данных:

- PostgreSQL 16+.
- SQLAlchemy 2.x async ORM/Core.
- asyncpg.
- Alembic для миграций.

Кэш и технические ключи:

- Redis 7+.

JWT:

- Предпочтительно `PyJWT[crypto]` или другая поддерживаемая библиотека.
- Не тянуть тяжелые или уязвимые транзитивные зависимости без необходимости.
- Если остается `python-jose`, обновлять все транзитивные зависимости и регулярно гонять `pip-audit`.

Telegram:

- `init-data-py` или ручная проверка Telegram initData по официальному алгоритму.
- `aiogram` только если реально запускается bot worker. Если bot worker не нужен, не добавлять зависимость.

Качество:

- `pytest`, `pytest-asyncio`, `httpx` для API-тестов.
- `ruff` для линтинга и форматирования.
- `mypy` или `pyright` по возможности.
- `pip-audit` в CI.

## 4. Конфигурация окружения

Все значения читаются из переменных окружения. Никакие пароли, токены, URL БД или Telegram bot token не должны храниться в git.

Обязательные переменные:

| Переменная | Тип | Пример | Назначение |
| --- | --- | --- | --- |
| `APP_ENV` | enum | `local`, `test`, `prod` | Режим приложения |
| `DATABASE_URL` | str | `postgresql+asyncpg://user:pass@db:5432/app` | Подключение к PostgreSQL |
| `REDIS_URL` | str | `redis://redis:6379/0` | Подключение к Redis |
| `SECRET_KEY` | str | 32+ байта энтропии | Подпись JWT и HMAC |
| `JWT_ALGORITHM` | str | `HS256` | Алгоритм JWT |
| `ACCESS_TOKEN_TTL_SECONDS` | int | `900` | TTL access-token |
| `REFRESH_TOKEN_TTL_SECONDS` | int | `2592000` | TTL refresh-token |
| `BOT_TOKEN` | str | Telegram bot token | Проверка initData |
| `FRONTEND_ORIGINS` | CSV/list | `https://app.example.com` | Разрешенные CORS origins |
| `COOKIE_DOMAIN` | str/null | `.example.com` | Домен refresh-cookie |
| `COOKIE_SECURE` | bool | `true` in prod | Только HTTPS cookie |
| `COOKIE_SAMESITE` | enum | `lax` или `none` | SameSite policy |
| `SQL_ECHO` | bool | `false` | SQL debug, в prod всегда false |
| `LOG_LEVEL` | str | `INFO` | Уровень логирования |

Правила:

- В production `COOKIE_SECURE=true`.
- В production `SQL_ECHO=false`.
- `FRONTEND_ORIGINS` задается списком точных origins. Не добавлять localhost в production.
- Alembic должен брать `DATABASE_URL` из окружения, а не из файла миграций.
- Docker Compose для production не должен публиковать наружу порты PostgreSQL и Redis.

## 5. Архитектура проекта

Рекомендуемая структура:

```text
backend/
  app/
    main.py
    config.py
    api/
      v1/
        router.py
        auth.py
        items.py
        profile.py
        user_settings.py
        admin.py
        health.py
        dependencies.py
    core/
      security.py
      errors.py
      logging.py
      pagination.py
    db/
      engine.py
      session.py
      models/
      repositories/
    schemas/
      auth.py
      user.py
      item.py
      validation.py
      common.py
    services/
      auth_service.py
      item_service.py
      validation_service.py
      user_service.py
      session_service.py
    workers/
      bot.py
  migrations/
  tests/
  requirements.in
  requirements.txt
  Dockerfile
```

Правило слоев:

- `api` принимает HTTP, валидирует DTO, вызывает сервисы, возвращает DTO.
- `services` содержит бизнес-логику и транзакционные сценарии.
- `repositories` содержит SQL-запросы.
- `models` содержит ORM-модели.
- `schemas` содержит Pydantic DTO.
- `core/security.py` отвечает за JWT, hashing и cookie.
- Сервисный слой не должен импортировать FastAPI `Request`/`Response`, кроме auth-service, если cookie устанавливается на API-границе.

## 6. База данных

Общие правила для всех таблиц:

- `id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY`;
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`;
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`;
- `updated_at` обновляется автоматически либо через ORM hook, либо через DB trigger;
- все foreign key должны иметь индексы, если по ним есть join/filter;
- все бизнес-уникальности фиксируются constraints, не только кодом.

### 6.1 `users`

Пользователи Telegram.

| Колонка | Тип | Ограничения | Описание |
| --- | --- | --- | --- |
| `id` | bigint | pk | Внутренний ID |
| `tg_id` | bigint | unique, not null | Telegram user id |
| `first_name` | varchar(128) | not null | Имя из Telegram |
| `last_name` | varchar(128) | nullable | Фамилия из Telegram |
| `username` | varchar(64) | nullable, unique | Telegram username |
| `photo_url` | text | nullable | URL аватара |
| `is_premium` | bool | not null default false | Telegram Premium |
| `is_private` | bool | not null default true | Скрывать пользователя в рейтинге |
| `role` | enum | not null default `USER` | `USER`, `MOD`, `ADMIN` |
| `created_at` | timestamptz | not null | Создан |
| `updated_at` | timestamptz | not null | Обновлен |

Индексы:

- unique index `ux_users_tg_id` on `tg_id`;
- unique partial index `ux_users_username_not_null` on `username` where `username is not null`;
- index `ix_users_role` on `role`, если есть admin-фильтры.

Важно: `username`, `last_name`, `photo_url` nullable, потому что Telegram не гарантирует эти поля.

### 6.2 `categories`

Категории предметов.

| Колонка | Тип | Ограничения |
| --- | --- | --- |
| `id` | bigint | pk |
| `title` | varchar(128) | not null, unique |
| `color` | varchar(32) | not null |
| `description` | text | not null default empty |
| `created_at` | timestamptz | not null |
| `updated_at` | timestamptz | not null |

Validation:

- `color` должен быть hex (`#RRGGBB`) или один из разрешенных design tokens.

### 6.3 `types`

Типы предметов.

| Колонка | Тип | Ограничения |
| --- | --- | --- |
| `id` | bigint | pk |
| `title` | varchar(128) | not null, unique |
| `description` | text | not null default empty |
| `photo_url` | text | nullable |
| `created_at` | timestamptz | not null |
| `updated_at` | timestamptz | not null |

### 6.4 `prototypes`

Прототипы предметов.

| Колонка | Тип | Ограничения |
| --- | --- | --- |
| `id` | bigint | pk |
| `title` | varchar(128) | not null |
| `description` | text | not null default empty |
| `photo_url` | text | nullable |
| `type_id` | bigint | fk `types.id`, not null |
| `created_at` | timestamptz | not null |
| `updated_at` | timestamptz | not null |

Индексы:

- index `ix_prototypes_type_id` on `type_id`.

### 6.5 `items`

Предметы каталога.

| Колонка | Тип | Ограничения |
| --- | --- | --- |
| `id` | bigint | pk |
| `title` | varchar(128) | not null |
| `number` | int | not null |
| `prototype_id` | bigint | fk `prototypes.id`, not null |
| `category_id` | bigint | fk `categories.id`, not null |
| `type_id` | bigint | fk `types.id`, not null |
| `validation_count` | int | not null default 0 |
| `is_active` | bool | not null default true |
| `created_at` | timestamptz | not null |
| `updated_at` | timestamptz | not null |

Constraints:

- unique `ux_items_number` on `number`, если номер глобально уникален;
- check `number > 0`;
- check `validation_count >= 0`.

Индексы:

- `ix_items_category_id`;
- `ix_items_prototype_id`;
- `ix_items_type_id`;
- `ix_items_is_active`;
- optional composite `ix_items_category_type` on `(category_id, type_id)`.

`validation_count` нужен для безопасного ранжирования без `count(*)` под нагрузкой.

### 6.6 `item_images`

Изображения предметов.

| Колонка | Тип | Ограничения |
| --- | --- | --- |
| `id` | bigint | pk |
| `item_id` | bigint | fk `items.id`, not null |
| `url` | text | not null |
| `is_main` | bool | not null default false |
| `position` | int | not null default 0 |
| `created_at` | timestamptz | not null |
| `updated_at` | timestamptz | not null |

Индексы:

- `ix_item_images_item_id`;
- unique partial `ux_item_images_one_main_per_item` on `item_id` where `is_main = true`.

### 6.7 `item_secrets`

Секреты, которые попадают в QR/startapp token.

Не хранить сырой секрет в БД. Хранить только hash.

| Колонка | Тип | Ограничения |
| --- | --- | --- |
| `id` | bigint | pk |
| `item_id` | bigint | fk `items.id`, not null |
| `secret_hash` | char(64) | unique, not null |
| `title` | varchar(128) | not null |
| `coords` | varchar(128) | nullable |
| `is_active` | bool | not null default true |
| `expires_at` | timestamptz | nullable |
| `created_at` | timestamptz | not null |
| `updated_at` | timestamptz | not null |

Индексы:

- `ux_item_secrets_secret_hash`;
- `ix_item_secrets_item_id`;
- `ix_item_secrets_active` on `is_active`.

Hash:

- `secret_hash = sha256(secret_value + SECRET_KEY pepper)` или HMAC-SHA256.
- Сырой секрет показывается только при генерации QR и не логируется.

### 6.8 `validations`

Факт получения предмета пользователем.

| Колонка | Тип | Ограничения |
| --- | --- | --- |
| `id` | bigint | pk |
| `user_id` | bigint | fk `users.id`, not null |
| `item_id` | bigint | fk `items.id`, not null |
| `item_secret_id` | bigint | fk `item_secrets.id`, not null |
| `rank` | int | not null |
| `created_at` | timestamptz | not null |
| `updated_at` | timestamptz | not null |

Constraints:

- unique `ux_validations_user_item` on `(user_id, item_id)`;
- unique `ux_validations_item_rank` on `(item_id, rank)`;
- check `rank > 0`.

Индексы:

- `ix_validations_user_id`;
- `ix_validations_item_id`;
- `ix_validations_item_secret_id`;
- `ix_validations_item_created_at` on `(item_id, created_at, id)`.

Правило rank:

- rank показывает порядковый номер получения конкретного item.
- rank назначается только внутри транзакции.
- Нельзя делать `rank = count(*) + 1` без блокировки.
- Надежный вариант: заблокировать строку `items` через `SELECT ... FOR UPDATE`, увеличить `items.validation_count`, использовать новое значение как rank, вставить validation, commit.

### 6.9 `refresh_sessions`

Серверные refresh-сессии.

| Колонка | Тип | Ограничения |
| --- | --- | --- |
| `id` | bigint | pk |
| `user_id` | bigint | fk `users.id`, not null |
| `jti` | uuid | unique, not null |
| `token_hash` | char(64) | unique, not null |
| `ip_address` | inet/text | nullable |
| `user_agent` | text | nullable |
| `expires_at` | timestamptz | not null |
| `revoked_at` | timestamptz | nullable |
| `last_used_at` | timestamptz | nullable |
| `replaced_by_session_id` | bigint | nullable fk `refresh_sessions.id` |
| `created_at` | timestamptz | not null |
| `updated_at` | timestamptz | not null |

Индексы:

- `ix_refresh_sessions_user_id`;
- `ux_refresh_sessions_jti`;
- `ux_refresh_sessions_token_hash`;
- `ix_refresh_sessions_expires_at`;
- partial index `ix_refresh_sessions_active` where `revoked_at is null`.

Правила:

- refresh-token хранится в БД только как hash.
- при refresh выполняется ротация: старая сессия помечается revoked, новая создается.
- повторное использование уже revoked refresh-token считается подозрительным событием.

## 7. DTO и JSON-схемы

Все даты возвращаются в ISO 8601 UTC.

### 7.1 Общие DTO

`ErrorResponse`:

```json
{
  "error": {
    "code": "invalid_token",
    "message": "Invalid access token",
    "details": {},
    "request_id": "req_01h..."
  }
}
```

`PageMeta`:

```json
{
  "limit": 50,
  "offset": 0,
  "total": 120
}
```

`PaginatedResponse[T]`:

```json
{
  "items": [],
  "meta": {
    "limit": 50,
    "offset": 0,
    "total": 120
  }
}
```

### 7.2 User DTO

`UserPublic`:

```json
{
  "id": 1,
  "first_name": "Mickey",
  "last_name": null,
  "photo_url": null,
  "is_private": false
}
```

Не отдавать публично:

- `tg_id`;
- `role`;
- username, если это не нужно интерфейсу;
- timestamps, если они не нужны.

`UserMe`:

```json
{
  "id": 1,
  "tg_id": 123456789,
  "first_name": "Mickey",
  "last_name": null,
  "username": "mickey",
  "photo_url": null,
  "is_premium": false,
  "is_private": true,
  "role": "USER"
}
```

### 7.3 Auth DTO

`TokenResponse`:

```json
{
  "access_token": "jwt...",
  "token_type": "Bearer",
  "expires_in": 900,
  "user": {
    "id": 1,
    "tg_id": 123456789,
    "first_name": "Mickey",
    "last_name": null,
    "username": "mickey",
    "photo_url": null,
    "is_premium": false,
    "is_private": true,
    "role": "USER"
  }
}
```

Refresh-token не возвращать в JSON. Он устанавливается только в HttpOnly cookie.

Cookie:

- name: `refresh_token`;
- `HttpOnly=true`;
- `Secure=true` in prod;
- `SameSite=Lax` по умолчанию;
- `Path=/api/v1/auth/refresh` для refresh endpoint;
- для logout можно также использовать `Path=/api/v1/auth`.

JWT access-token claims:

```json
{
  "sub": "1",
  "tg_id": 123456789,
  "role": "USER",
  "token_type": "access",
  "iat": 1710000000,
  "exp": 1710000900
}
```

JWT refresh-token claims:

```json
{
  "sub": "1",
  "jti": "uuid",
  "token_type": "refresh",
  "iat": 1710000000,
  "exp": 1712592000
}
```

### 7.4 Catalog DTO

`CategoryResponse`:

```json
{
  "id": 1,
  "title": "Common",
  "color": "#88AAFF",
  "description": "Base category"
}
```

`TypeResponse`:

```json
{
  "id": 1,
  "title": "Sticker",
  "description": "Digital item type",
  "photo_url": null
}
```

`PrototypeResponse`:

```json
{
  "id": 1,
  "title": "Prototype title",
  "description": "Prototype description",
  "photo_url": null,
  "type_id": 1
}
```

`ItemFullResponse`:

```json
{
  "state": "collected",
  "id": 1,
  "title": "Item title",
  "number": 1,
  "type": {
    "id": 1,
    "title": "Sticker",
    "description": "Digital item type",
    "photo_url": null
  },
  "category": {
    "id": 1,
    "title": "Common",
    "color": "#88AAFF",
    "description": "Base category"
  },
  "prototype": {
    "id": 1,
    "title": "Prototype title",
    "description": "Prototype description",
    "photo_url": null,
    "type_id": 1
  }
}
```

`ItemHiddenResponse`:

```json
{
  "state": "hidden",
  "id": 1,
  "title": null,
  "number": null,
  "type": {
    "id": 1,
    "title": "Sticker",
    "description": "Digital item type",
    "photo_url": null
  },
  "category": {
    "id": 1,
    "title": "Common",
    "color": "#88AAFF",
    "description": "Base category"
  },
  "prototype": {
    "id": 1,
    "title": "Prototype title",
    "description": "Prototype description",
    "photo_url": null,
    "type_id": 1
  }
}
```

`state` обязателен, чтобы frontend и тесты не гадали по nullable-полям.

### 7.5 Validation DTO

`SecretValidationRequest`:

```json
{
  "token": "base64url.jwt"
}
```

Validation:

- `token`: string, required;
- min length: 16;
- max length: 4096;
- allowed chars: base64url charset plus dots if передается неупакованный JWT.

`ValidationResponse`:

```json
{
  "status": "created",
  "validation": {
    "id": 10,
    "item_id": 1,
    "rank": 5,
    "created_at": "2026-06-29T06:00:00Z"
  },
  "item": {
    "state": "collected",
    "id": 1,
    "title": "Item title",
    "number": 1,
    "type": {},
    "category": {},
    "prototype": {}
  }
}
```

`status` values:

- `created`: новая validation создана;
- `already_collected`: пользователь уже получал этот item.

Для совместимости со старым поведением можно вместо `already_collected` возвращать `409`, но production-friendly API лучше делать идемпотентным.

`RatingEntryResponse`:

```json
{
  "rank": 1,
  "created_at": "2026-06-29T06:00:00Z",
  "user": {
    "id": 1,
    "first_name": "Mickey",
    "last_name": null,
    "photo_url": null,
    "is_private": false
  }
}
```

Если пользователь приватный:

```json
{
  "rank": 1,
  "created_at": "2026-06-29T06:00:00Z",
  "user": null
}
```

### 7.6 Settings DTO

`PrivacyResponse`:

```json
{
  "privacy": true
}
```

`PrivacyUpdateRequest`:

```json
{
  "privacy": false
}
```

### 7.7 Profile DTO

`ValidationCountResponse`:

```json
{
  "count": 12
}
```

## 8. HTTP API

Базовый префикс: `/api/v1`.

Все protected endpoints требуют:

```http
Authorization: Bearer <access_token>
```

### 8.1 Health

#### `GET /health/live`

Назначение: процесс жив.

Ответ `200`:

```json
{
  "status": "ok"
}
```

Не проверяет БД/Redis.

#### `GET /health/ready`

Назначение: сервис готов принимать трафик.

Проверяет:

- PostgreSQL `select 1`;
- Redis `ping`, если Redis обязателен.

Ответ `200`:

```json
{
  "status": "ready",
  "db": "ok",
  "redis": "ok"
}
```

Ответ `503`:

```json
{
  "error": {
    "code": "service_not_ready",
    "message": "Service is not ready",
    "details": {
      "db": "ok",
      "redis": "failed"
    },
    "request_id": "req_..."
  }
}
```

### 8.2 Auth

#### `POST /auth/init`

Content-Type: `application/x-www-form-urlencoded`.

Request:

| Поле | Тип | Ограничения |
| --- | --- | --- |
| `tg_web_app_data` | str | required, max 4096 |

Логика:

1. Принять `tg_web_app_data`.
2. Проверить подпись Telegram через `BOT_TOKEN`.
3. Проверить lifetime, например 3600 секунд.
4. Опционально защититься от replay: сохранить hash initData в Redis на 3600 секунд и отклонять повтор, если это критично для продукта.
5. Найти пользователя по `tg_id`.
6. Если найден, обновить Telegram-поля.
7. Если не найден, создать пользователя с `role=USER`, `is_private=true`.
8. Создать access-token.
9. Создать refresh-token и запись `refresh_sessions`.
10. Установить refresh-cookie.
11. Вернуть `TokenResponse`.

Ответ `200`: `TokenResponse`.

Ошибки:

- `400 invalid_init_data`: initData не парсится;
- `403 invalid_telegram_signature`: подпись неверна;
- `403 expired_init_data`: initData устарел;
- `500 internal_error`: неожиданная ошибка.

Важно:

- Не логировать `tg_web_app_data`.
- Не печатать пользователя через `print`.
- Ошибки Telegram-валидации не должны раскрывать секреты.

#### `POST /auth/refresh`

Request:

- body отсутствует;
- refresh-token берется из HttpOnly cookie `refresh_token`.

Логика:

1. Проверить наличие cookie.
2. Декодировать JWT refresh-token.
3. Проверить `token_type=refresh`.
4. Найти refresh session по `jti` и `token_hash`.
5. Проверить `revoked_at is null`.
6. Проверить `expires_at > now()`.
7. В транзакции пометить старую сессию revoked.
8. Создать новую refresh session.
9. Выдать новый access-token.
10. Установить новый refresh-cookie.
11. Вернуть `TokenResponse`.

Ответ `200`: `TokenResponse`.

Ошибки:

- `401 missing_refresh_token`;
- `401 invalid_refresh_token`;
- `401 expired_refresh_token`;
- `401 revoked_refresh_token`;
- `403 refresh_reuse_detected`, если обнаружено повторное использование уже revoked токена.

#### `POST /auth/logout`

Protected или cookie-based endpoint.

Логика:

1. Если есть refresh-cookie, найти session и пометить revoked.
2. Очистить refresh-cookie.
3. Вернуть `204 No Content`.

#### `GET /auth/me`

Protected.

Ответ `200`: `UserMe`.

Ошибки:

- `401 invalid_access_token`;
- `404 user_not_found`, если пользователь удален/несогласован.

### 8.3 Items

#### `GET /items`

Protected.

Назначение: получить полный активный каталог.

Query:

| Параметр | Тип | Default | Ограничения |
| --- | --- | --- | --- |
| `limit` | int | 100 | 1..200 |
| `offset` | int | 0 | >=0 |
| `category_id` | int | null | >0 |
| `type_id` | int | null | >0 |

Ответ `200`:

```json
{
  "items": [
    {
      "state": "collected",
      "id": 1,
      "title": "Item title",
      "number": 1,
      "type": {},
      "category": {},
      "prototype": {}
    }
  ],
  "meta": {
    "limit": 100,
    "offset": 0,
    "total": 1
  }
}
```

Для MVP можно возвращать просто массив, но для production лучше сразу ввести pagination envelope.

SQL:

- один запрос на items с `selectinload`/join для category, prototype, type;
- никаких запросов в цикле.

#### `GET /items/my`

Protected.

Назначение: каталог с учетом коллекции текущего пользователя.

Логика:

1. Проверить access-token.
2. Получить текущего пользователя.
3. Получить активные items с category/prototype/type.
4. Одним запросом получить `item_id`, которые пользователь уже собрал.
5. Собрать список:
   - собранные: `ItemFullResponse`;
   - несобранные: `ItemHiddenResponse`.
6. Отсортировать по `number` или `id`.

Ответ `200`:

```json
{
  "items": [
    {
      "state": "hidden",
      "id": 1,
      "title": null,
      "number": null,
      "type": {},
      "category": {},
      "prototype": {}
    },
    {
      "state": "collected",
      "id": 2,
      "title": "Known item",
      "number": 2,
      "type": {},
      "category": {},
      "prototype": {}
    }
  ],
  "meta": {
    "limit": 100,
    "offset": 0,
    "total": 2
  }
}
```

#### `GET /items/{item_id}`

Protected.

Path:

- `item_id`: int, >0.

Назначение: получить item. Если предмет не собран пользователем, вернуть hidden view.

Ответ `200`: `ItemFullResponse` или `ItemHiddenResponse`.

Ошибки:

- `404 item_not_found`.

#### `GET /items/{item_id}/full`

Protected.

Назначение: legacy/explicit endpoint для полного item.

Рекомендуемое правило:

- если предмет не собран, обычный пользователь получает `403 item_not_collected`;
- `MOD`/`ADMIN` может получить полный item всегда.

Ответ `200`: `ItemFullResponse`.

Ошибки:

- `403 item_not_collected`;
- `404 item_not_found`.

#### `GET /items/{item_id}/rating`

Protected.

Query:

| Параметр | Тип | Default |
| --- | --- | --- |
| `limit` | int | 100 |
| `offset` | int | 0 |

Логика:

1. Проверить item exists.
2. Получить validations по `item_id`, сортировка `rank asc`.
3. Подгрузить users через `selectinload` или join.
4. Если `user.is_private=true`, вернуть `user=null`.

Ответ `200`:

```json
{
  "items": [
    {
      "rank": 1,
      "created_at": "2026-06-29T06:00:00Z",
      "user": null
    }
  ],
  "meta": {
    "limit": 100,
    "offset": 0,
    "total": 1
  }
}
```

Ошибки:

- `404 item_not_found`.

#### `POST /items/secret`

Protected.

Назначение: обработать QR/startapp token и засчитать предмет.

Request:

```json
{
  "token": "base64url.jwt"
}
```

Содержимое decoded QR/startapp JWT:

```json
{
  "secret": "raw-secret-value",
  "token_type": "item_secret",
  "iat": 1710000000,
  "exp": 1712592000
}
```

Логика:

1. Проверить access-token и получить пользователя.
2. Валидировать request body Pydantic-схемой.
3. Base64url decode, если токен передается упакованным.
4. Декодировать JWT.
5. Проверить `token_type=item_secret`.
6. Проверить `exp`.
7. Достать `secret`.
8. Посчитать `secret_hash`.
9. Найти активный `item_secret` по hash.
10. Проверить `expires_at`, если задан.
11. Если у пользователя уже есть validation для item, вернуть `status=already_collected`.
12. В транзакции:
    - заблокировать item row `FOR UPDATE`;
    - увеличить `items.validation_count`;
    - создать validation с новым rank;
    - commit.
13. Инвалидировать Redis key `user:{user_id}:validation_count`.
14. Вернуть `ValidationResponse`.

Ошибки:

- `400 invalid_secret_token`: base64/JWT не парсится;
- `400 missing_secret`: нет claim `secret`;
- `400 invalid_secret_type`: неверный `token_type`;
- `401 invalid_access_token`;
- `404 secret_not_found`;
- `409 validation_conflict`: только если уникальный constraint сработал неожиданно;
- `422 validation_error`: тело запроса не прошло Pydantic.

Транзакция должна быть короткой. Нельзя держать транзакцию во время сетевых вызовов в Redis или Telegram.

### 8.4 Profile

#### `GET /profile/validations/count`

Protected.

Назначение: количество собранных предметов текущим пользователем.

Логика:

1. Проверить пользователя.
2. Попробовать прочитать Redis key `user:{user_id}:validation_count`.
3. Если Redis недоступен или ключа нет, прочитать из PostgreSQL.
4. Если Redis доступен, записать значение с TTL 600 секунд.
5. Вернуть DTO.

Ответ `200`:

```json
{
  "count": 12
}
```

Redis должен быть fail-open: падение Redis не должно ронять этот endpoint.

### 8.5 User Settings

#### `GET /users/settings/privacy`

Protected.

Ответ `200`:

```json
{
  "privacy": true
}
```

#### `PATCH /users/settings/privacy`

Protected.

Request:

```json
{
  "privacy": false
}
```

Логика:

1. Проверить пользователя.
2. Обновить `users.is_private`.
3. Вернуть новое значение.

Ответ `200`:

```json
{
  "privacy": false
}
```

### 8.6 Admin API

Если каталог не редактируется вручную через seed/migrations, production backend должен иметь закрытый admin API.

Все endpoints требуют роль `ADMIN` или `MOD`, где явно указано.

Минимальный набор:

- `POST /admin/categories`;
- `PATCH /admin/categories/{id}`;
- `POST /admin/types`;
- `PATCH /admin/types/{id}`;
- `POST /admin/prototypes`;
- `PATCH /admin/prototypes/{id}`;
- `POST /admin/items`;
- `PATCH /admin/items/{id}`;
- `POST /admin/items/{item_id}/secrets`;
- `POST /admin/items/{item_id}/images`;
- `DELETE /admin/items/{item_id}/images/{image_id}` или soft delete.

Пример `CreateItemRequest`:

```json
{
  "title": "Item title",
  "number": 1,
  "prototype_id": 1,
  "category_id": 1,
  "type_id": 1,
  "is_active": true
}
```

Пример `CreateSecretResponse`:

```json
{
  "id": 1,
  "item_id": 1,
  "token": "base64url.jwt",
  "expires_at": null
}
```

Важно: сырой secret/token возвращается только один раз при создании. В БД хранится только hash.

## 9. Бизнес-сценарии

### 9.1 Startup

1. Приложение читает settings.
2. Валидирует обязательные env.
3. Создает async engine PostgreSQL.
4. Создает Redis client.
5. Регистрирует routers.
6. Настраивает CORS из `FRONTEND_ORIGINS`.
7. Настраивает middleware request id и logging.

Если settings невалидны, приложение должно падать на старте.

### 9.2 Telegram login

Основной happy path:

1. Клиент получает Telegram `initData`.
2. Клиент отправляет `POST /auth/init`.
3. Backend проверяет подпись.
4. Backend upsert пользователя.
5. Backend создает access и refresh.
6. Backend ставит refresh-cookie.
7. Клиент хранит access-token в памяти приложения.

Не хранить access-token в localStorage, если можно избежать. Это фронтенд-решение, но backend должен быть готов к короткому access TTL.

### 9.3 Access-token protected request

1. API dependency читает `Authorization`.
2. Проверяет формат `Bearer`.
3. Декодирует JWT.
4. Проверяет `token_type=access`.
5. Проверяет `exp`.
6. Возвращает `CurrentUserContext`.

Ошибки JWT не глотать бесследно. В лог писать безопасный код причины, но не сам token.

### 9.4 Refresh

1. Клиент вызывает `/auth/refresh`, browser автоматически отправляет cookie.
2. Backend проверяет refresh-token.
3. Backend делает rotation.
4. Backend возвращает новый access-token.
5. Backend ставит новый refresh-cookie.

Если refresh-token использован повторно после revoke:

- пометить все активные сессии пользователя как revoked или поднять security event;
- вернуть `403 refresh_reuse_detected`.

### 9.5 Получение предмета по QR/startapp secret

1. Пользователь открывает QR/startapp.
2. Клиент отправляет token на `/items/secret`.
3. Backend проверяет пользователя и secret.
4. Backend ищет item_secret.
5. Backend проверяет, что пользователь еще не получал item.
6. Backend создает validation с безопасным rank.
7. Backend инвалидирует кэш count.
8. Backend возвращает item и validation.

Конкурентный сценарий:

- два пользователя одновременно сканируют один item;
- оба запроса должны успешно получить разные rank;
- не должно быть случайного `500` из-за unique `(item_id, rank)`.

### 9.6 Рейтинг item

1. Пользователь запрашивает `/items/{id}/rating`.
2. Backend возвращает список validations по rank.
3. Для приватных пользователей поле `user=null`.
4. Для публичных пользователей отдаются только безопасные публичные поля.

### 9.7 Privacy

1. Пользователь включает privacy.
2. Его прошлые и будущие записи в рейтинге показывают `user=null`.
3. Сами validations остаются, rank не меняется.

## 10. Ошибки и исключения

Правила:

- Не использовать голый `except Exception` без повторного `raise` или явного преобразования в доменное исключение.
- Не возвращать `None` из security-функций, если причина важна. Лучше бросать типизированные исключения.
- Ошибки БД ловить на границе бизнес-сценария.
- Stack trace должен сохраняться через `raise ... from e`.
- В HTTP отдавать безопасные сообщения, без SQL, token, cookie, raw secret.

Рекомендуемые доменные исключения:

- `InvalidAuthorizationHeader`;
- `InvalidAccessToken`;
- `ExpiredAccessToken`;
- `InvalidRefreshToken`;
- `RefreshTokenReuseDetected`;
- `UserNotFound`;
- `ItemNotFound`;
- `SecretNotFound`;
- `InvalidSecretToken`;
- `ValidationAlreadyExists`;
- `Forbidden`.

HTTP mapping:

| Exception | HTTP | code |
| --- | --- | --- |
| Invalid request body | 422 | `validation_error` |
| Invalid secret token | 400 | `invalid_secret_token` |
| Missing auth | 401 | `missing_authorization` |
| Invalid access token | 401 | `invalid_access_token` |
| Expired access token | 401 | `expired_access_token` |
| Forbidden | 403 | `forbidden` |
| Not found | 404 | `not_found` |
| Business duplicate | 409 | `conflict` |
| Unexpected DB error | 500 | `internal_error` |

## 11. Безопасность

Обязательные требования:

- Все secrets только через env/secret manager.
- Немедленно ротировать любой bot token, который когда-либо был в git.
- Refresh-token только HttpOnly cookie.
- Refresh-token хранить в БД только hash.
- Access-token TTL короткий: 10-20 минут.
- Refresh-token TTL: 7-30 дней по продуктовой политике.
- CORS whitelist только из env.
- Не использовать `allow_origins=["*"]` вместе с credentials.
- Не логировать Authorization header, cookies, initData, raw secret, JWT payload целиком.
- Включить rate limit:
  - `/auth/init`: например 10/min per IP;
  - `/auth/refresh`: 30/min per IP/session;
  - `/items/secret`: 20/min per user.
- Ограничить размер body на уровне reverse proxy и приложения.
- Все входные строки иметь max length.
- Для admin endpoints проверять `role`.
- SQLAlchemy queries строить параметризованно, без string interpolation.

CSRF:

- `/auth/refresh` использует cookie. При `SameSite=Lax` риск ниже.
- Если `SameSite=None` из-за cross-site Telegram/WebView, добавить double-submit CSRF token или другой защитный механизм.

## 12. Производительность

Требования:

- Запросы каталога не должны делать DB query в цикле.
- Для связей item/category/prototype/type использовать `selectinload` или join.
- Для рейтинга использовать pagination.
- Для count использовать Redis cache, но Redis fail-open.
- Индексы должны соответствовать фильтрам.
- Транзакции должны быть короткими.
- Не выполнять Redis/Telegram/http calls внутри DB transaction.

Целевые показатели для MVP:

- `/health/live`: p95 < 20 ms;
- `/items/my` на 1000 items: p95 < 300 ms при warm DB;
- `/items/secret`: p95 < 250 ms без внешних сетевых вызовов;
- `/items/{id}/rating` с pagination 100 rows: p95 < 200 ms.

## 13. Redis

Ключи:

| Key | TTL | Назначение |
| --- | --- | --- |
| `user:{user_id}:validation_count` | 600s | Кэш количества validations |
| `rate:{scope}:{id}:{window}` | window TTL | Rate limiting |
| `telegram_init:{hash}` | 3600s | Опциональная защита от replay |

Правила:

- Redis connection errors не должны ронять read endpoints, если данные можно получить из БД.
- После создания validation удалять `user:{user_id}:validation_count`.
- Не хранить JWT или raw secrets в Redis без необходимости.

## 14. Миграции

Требования:

- Alembic `env.py` читает `DATABASE_URL` из env.
- Каждая миграция имеет понятное имя.
- Не использовать anonymous foreign keys/constraints, если потом нужен downgrade.
- Все constraints именовать явно.
- Не добавлять `NOT NULL` колонку в заполненную таблицу без backfill.
- Для больших таблиц:
  - добавить nullable колонку;
  - backfill батчами;
  - добавить constraint;
  - сделать `NOT NULL`.

Минимальная начальная миграция должна создать:

- enum `user_role`;
- `users`;
- `categories`;
- `types`;
- `prototypes`;
- `items`;
- `item_images`;
- `item_secrets`;
- `validations`;
- `refresh_sessions`;
- все constraints и индексы.

## 15. Логирование и наблюдаемость

Логи:

- JSON logs в production;
- поля: `timestamp`, `level`, `request_id`, `method`, `path`, `status_code`, `duration_ms`, `user_id`, `error_code`;
- не логировать tokens/cookies/initData/raw secrets.

Middleware:

- request id создается, если клиент не передал `X-Request-ID`;
- request id возвращается в response header.

Метрики:

- request count by route/status;
- latency histogram;
- db query errors;
- redis errors;
- auth failures by reason;
- secret validation success/failure;
- refresh token reuse events.

## 16. Docker и production запуск

Dockerfile:

- использовать slim image;
- ставить зависимости из lock-файла;
- запускать от non-root user;
- не копировать `.env`;
- command:

```text
uvicorn app.main:app --host 0.0.0.0 --port 4000
```

Production Compose/Kubernetes:

- backend доступен reverse proxy;
- PostgreSQL и Redis не публикуются наружу;
- env через secrets;
- healthcheck использует `/health/ready`;
- миграции запускаются отдельным job до выката приложения;
- rolling deploy не должен запускать миграции из каждого backend replica одновременно.

## 17. Тестирование

Минимальный набор тестов:

Auth:

- valid Telegram initData создает пользователя;
- повторный initData обновляет пользователя;
- invalid signature возвращает 403;
- expired initData возвращает 403;
- refresh rotation работает;
- повтор старого refresh-token ловится.

Items:

- `/items/my` возвращает hidden для несобранных и full для собранных;
- `/items/{id}/rating` скрывает приватного пользователя;
- несуществующий item возвращает 404.

Secret validation:

- валидный secret создает validation;
- повторный scan возвращает `already_collected` или 409, в зависимости от выбранного контракта;
- битый base64/JWT возвращает 400;
- неизвестный secret возвращает 404;
- параллельные scans одного item получают разные rank.

DB:

- unique `(user_id, item_id)` работает;
- unique `(item_id, rank)` работает;
- индексы есть в миграциях.

Redis:

- count читается из cache;
- при падении Redis endpoint читает из БД;
- после validation cache invalidated.

Security:

- protected endpoints без token возвращают 401;
- role-protected endpoints возвращают 403 обычному user;
- в логах нет token/cookie/raw secret.

CI pipeline:

1. install dependencies;
2. ruff format/check;
3. type check;
4. unit tests;
5. integration tests with PostgreSQL/Redis;
6. alembic upgrade head на пустой БД;
7. pip-audit;
8. build Docker image.

## 18. Критерии приемки

Backend считается готовым, если:

- все endpoints из раздела 8 реализованы или явно помечены как out of scope;
- OpenAPI соответствует DTO из раздела 7;
- нет секретов в git;
- `pip-audit` не показывает known vulnerabilities или есть зафиксированные exceptions с причиной;
- все миграции применяются на пустую БД;
- все hot queries имеют индексы;
- refresh-token не возвращается в JSON;
- refresh-session rotation покрыта тестами;
- параллельное создание validations не дает случайных 500;
- Redis outage не роняет read-only профильный count;
- CORS и cookies управляются env;
- Docker image запускает приложение без `python app/main.py`;
- production logs не содержат PII/tokens.

## 19. Рекомендуемый порядок реализации с нуля

1. Создать FastAPI app, settings, health endpoints.
2. Подключить PostgreSQL async engine и Alembic.
3. Описать модели и первую миграцию со всеми индексами.
4. Реализовать repositories без магического DI.
5. Реализовать DTO.
6. Реализовать security: JWT access/refresh, hashing, cookies.
7. Реализовать `/auth/init`, `/auth/refresh`, `/auth/logout`, `/auth/me`.
8. Реализовать protected dependency `CurrentUser`.
9. Реализовать каталог `/items`, `/items/my`, `/items/{id}`, rating.
10. Реализовать `/items/secret` с транзакцией и блокировкой item.
11. Подключить Redis cache для count и rate limit.
12. Реализовать settings/profile endpoints.
13. Добавить admin API или seed-скрипты.
14. Написать тесты на auth, validations, гонки, Redis fallback.
15. Настроить Docker, CI, `pip-audit`.
16. Прогнать миграции на чистой БД и тестовой БД.

## 20. Roadmap по этапам и оценка времени

Оценка дана для одного разработчика, который пишет проект с нуля по этому ТЗ без ИИ-помощника. Диапазон учитывает чтение документации, отладку, мелкие ошибки в миграциях, локальный Docker и ручную проверку API.

Итоговая оценка:

| Сценарий | Часы | Рабочие дни по 6 часов | Комментарий |
| --- | ---: | ---: | --- |
| MVP без admin API, без полноценного CI, но с безопасным auth и основными тестами | 82-118 | 14-20 дней | Достаточно, чтобы приложение работало надежно локально и на тестовом сервере |
| Production baseline по этому ТЗ | 132-190 | 22-32 дня | Включает Docker, CI, audit, observability, rate limit, admin/seed flow |
| Production с запасом на полировку, документацию и неожиданные баги | 170-240 | 29-40 дней | Более честная оценка, если делать спокойно и без накопления техдолга |

### Этап 0. Подготовка и проектирование

Оценка: 6-10 часов.

Результат этапа:

- создан новый backend-проект;
- выбран менеджер зависимостей;
- заведены `.env.example`, `.gitignore`, базовая структура папок;
- решено, нужен ли `admin API` сразу или достаточно seed-скриптов;
- решено, остается ли Telegram bot worker в первой версии.

Работы:

| Задача | Часы |
| --- | ---: |
| Создать чистую структуру проекта | 1-2 |
| Настроить зависимости, ruff, pytest | 2-3 |
| Завести settings и `.env.example` | 1-2 |
| Принять решения по MVP scope | 1 |
| Первичный запуск пустого FastAPI | 1-2 |

Готово, когда:

- `uvicorn app.main:app` запускается;
- `/health/live` возвращает `200`;
- проект не требует секретов, захардкоженных в коде.

### Этап 1. Инфраструктурный каркас backend

Оценка: 10-16 часов.

Результат этапа:

- приложение стартует через lifespan;
- есть request id middleware;
- есть единый формат ошибок;
- есть CORS из env;
- есть подключение к PostgreSQL и Redis;
- есть `/health/live` и `/health/ready`.

Работы:

| Задача | Часы |
| --- | ---: |
| FastAPI app factory, routers, lifespan | 2-3 |
| Settings через Pydantic | 1-2 |
| DB engine/session dependency | 2-3 |
| Redis client с fail-open helper | 1-2 |
| Error handlers и `ErrorResponse` | 2-3 |
| Request id и базовое logging middleware | 2-3 |

Готово, когда:

- приложение падает на старте при невалидных env;
- `/health/ready` проверяет БД и Redis;
- все ошибки имеют единый JSON-формат.

### Этап 2. Модели БД и миграции

Оценка: 14-22 часа.

Результат этапа:

- описаны все ORM-модели;
- создана первая Alembic migration;
- все constraints и индексы названы явно;
- миграция применяется на пустую БД.

Работы:

| Задача | Часы |
| --- | ---: |
| Настроить Alembic с `DATABASE_URL` из env | 2-3 |
| Описать `users`, `refresh_sessions` | 2-4 |
| Описать catalog tables: categories, types, prototypes, items, images | 3-5 |
| Описать `item_secrets`, `validations` | 2-4 |
| Создать индексы и constraints | 2-3 |
| Прогнать upgrade/downgrade на чистой БД | 2-3 |
| Исправить типовые ошибки миграций | 1-3 |

Готово, когда:

- `alembic upgrade head` проходит с нуля;
- foreign keys и hot indexes есть в БД;
- nullable-поля Telegram соответствуют реальности.

### Этап 3. DTO, repositories и базовые сервисы

Оценка: 12-18 часов.

Результат этапа:

- есть Pydantic-схемы из раздела 7;
- есть repositories без магического runtime DI;
- есть сервисы для users, sessions, items, validations;
- запросы не делают N+1.

Работы:

| Задача | Часы |
| --- | ---: |
| Описать DTO для auth/user/catalog/validation/common | 3-5 |
| Реализовать repository base pattern | 2-3 |
| Реализовать user/session repositories | 2-3 |
| Реализовать item/catalog repositories с eager loading | 2-4 |
| Реализовать validation repository | 2-3 |
| Написать простые unit tests на DTO/serializing | 1-2 |

Готово, когда:

- DTO не отдают лишние поля;
- все публичные ответы имеют `response_model`;
- запросы каталога используют join/selectinload, а не запросы в цикле.

### Этап 4. Security и auth

Оценка: 18-28 часов.

Результат этапа:

- реализована проверка Telegram initData;
- есть access JWT;
- refresh-token хранится в HttpOnly cookie;
- refresh-сессии хранятся на сервере;
- refresh rotation работает;
- logout отзывает session.

Работы:

| Задача | Часы |
| --- | ---: |
| JWT helpers: create/verify access/refresh | 3-5 |
| Hash refresh-token и raw secret helpers | 2-3 |
| CurrentUser dependency | 2-3 |
| Telegram initData verification | 3-5 |
| `/auth/init` | 3-5 |
| `/auth/refresh` с rotation | 4-6 |
| `/auth/logout`, `/auth/me` | 2-3 |
| Auth tests | 4-6 |

Готово, когда:

- refresh-token не возвращается в JSON;
- повтор старого refresh-token ловится;
- invalid/expired tokens дают разные контролируемые ошибки;
- auth-тесты проходят.

### Этап 5. Catalog API

Оценка: 12-18 часов.

Результат этапа:

- реализованы `/items`, `/items/my`, `/items/{id}`, `/items/{id}/full`, `/items/{id}/rating`;
- hidden/full модель работает;
- privacy скрывает пользователя в рейтинге;
- pagination есть там, где список может расти.

Работы:

| Задача | Часы |
| --- | ---: |
| `GET /items` с фильтрами и pagination | 2-4 |
| `GET /items/my` с collected flag | 3-5 |
| `GET /items/{id}` и `/full` | 2-3 |
| `GET /items/{id}/rating` | 2-3 |
| Tests на hidden/full/rating/privacy | 3-4 |

Готово, когда:

- несобранные items не раскрывают `title` и `number`;
- приватный пользователь в рейтинге возвращается как `user=null`;
- нет N+1 на списках.

### Этап 6. Secret validation flow

Оценка: 14-24 часа.

Результат этапа:

- реализован `POST /items/secret`;
- secret token валидируется схемой;
- сырой secret не хранится в БД;
- rank создается без гонки;
- count cache инвалидируется.

Работы:

| Задача | Часы |
| --- | ---: |
| DTO и validation для secret request | 1-2 |
| Decode base64url/JWT с контролируемыми ошибками | 2-3 |
| Поиск `item_secret` по hash | 2-3 |
| Транзакция с `SELECT ... FOR UPDATE` по item | 4-6 |
| Idempotent duplicate behavior или `409` | 2-3 |
| Redis invalidation | 1-2 |
| Tests, включая параллельные scans | 4-8 |

Готово, когда:

- битый token возвращает 400, а не 500;
- параллельные scans одного item получают разные rank;
- повторный scan одного пользователя не создает дубль.

### Этап 7. Profile, settings, cache и rate limit

Оценка: 8-14 часов.

Результат этапа:

- реализован profile count;
- Redis cache работает и не роняет endpoint при отказе;
- privacy settings работают;
- базовый rate limit подключен к чувствительным endpoints.

Работы:

| Задача | Часы |
| --- | ---: |
| `GET /profile/validations/count` | 1-2 |
| Redis cache read/write/fallback | 2-3 |
| `GET/PATCH /users/settings/privacy` | 2-3 |
| Rate limit helper через Redis | 2-4 |
| Tests на Redis fallback и privacy | 2-3 |

Готово, когда:

- Redis outage не ломает profile count;
- после scan count обновляется корректно;
- privacy сразу влияет на rating.

### Этап 8. Admin API или seed-скрипты

Оценка: 10-24 часа.

Результат этапа:

- есть способ управлять каталогом;
- можно создать category/type/prototype/item/secret/image;
- секрет для QR возвращается только один раз;
- обычный пользователь не имеет доступа.

Вариант MVP через seed-скрипты: 4-8 часов.

Вариант production admin API: 16-24 часа.

Работы:

| Задача | Часы |
| --- | ---: |
| Role dependency для `ADMIN`/`MOD` | 1-2 |
| CRUD categories/types/prototypes | 4-6 |
| CRUD items/images | 4-7 |
| Создание item secret и одноразовый возврат token | 3-5 |
| Admin tests | 4-6 |

Готово, когда:

- каталог можно наполнить без ручного SQL;
- raw secret не сохраняется;
- role checks покрыты тестами.

### Этап 9. Bot worker, если он нужен

Оценка: 6-16 часов.

Результат этапа:

- Telegram bot запускается отдельным процессом;
- зависимость `aiogram` явно добавлена;
- bot не импортирует web app settings неправильно;
- bot не ломает backend startup.

Работы:

| Задача | Часы |
| --- | ---: |
| Решить, нужен ли bot в MVP | 1 |
| Добавить worker entrypoint | 2-3 |
| Разделить web/backend и bot lifecycle | 2-4 |
| Реализовать нужные команды | 2-6 |
| Smoke tests/manual checks | 1-2 |

Готово, когда:

- backend можно запускать без bot;
- bot можно запускать без HTTP server;
- секреты bot не лежат в коде.

### Этап 10. Тесты, качество и security audit

Оценка: 16-28 часов.

Результат этапа:

- есть тестовая БД;
- тесты покрывают критичные сценарии;
- `ruff`, type check и `pip-audit` проходят;
- нет известных уязвимостей без решения.

Работы:

| Задача | Часы |
| --- | ---: |
| Test fixtures: app, db, redis | 4-6 |
| Auth integration tests | 3-5 |
| Items/profile/settings tests | 3-5 |
| Secret validation race tests | 4-8 |
| Ruff/type check cleanup | 2-4 |
| `pip-audit` и обновление зависимостей | 1-3 |

Готово, когда:

- тесты запускаются одной командой;
- миграции прогоняются в тестовом окружении;
- критичные сценарии не проверяются только руками.

### Этап 11. Docker, CI и production readiness

Оценка: 14-24 часа.

Результат этапа:

- backend image собирается;
- приложение запускается non-root;
- env/secrets не попадают в image;
- CI гоняет проверки;
- production compose/deploy не публикует БД и Redis наружу.

Работы:

| Задача | Часы |
| --- | ---: |
| Dockerfile для backend | 2-4 |
| docker-compose local/test/prod cleanup | 3-5 |
| Migration job или ручная команда deploy | 2-4 |
| CI pipeline | 4-7 |
| Логи, healthcheck, graceful shutdown | 2-4 |
| Финальный smoke test | 1-2 |

Готово, когда:

- новый разработчик может поднять проект по README;
- image стартует командой `uvicorn app.main:app`;
- production env не содержит открытых портов БД/Redis.

### Этап 12. Документация и финальная приемка

Оценка: 8-14 часов.

Результат этапа:

- написан README для запуска;
- описаны env;
- описаны команды миграций и тестов;
- проверены критерии приемки из раздела 18;
- OpenAPI руками сверена с этим ТЗ.

Работы:

| Задача | Часы |
| --- | ---: |
| README local setup | 2-3 |
| Описание env и secrets | 1-2 |
| Описание deploy/migrations | 2-3 |
| Финальная сверка OpenAPI | 2-3 |
| Ручная проверка happy paths | 2-3 |

Готово, когда:

- проект можно поднять с нуля по README;
- все endpoints из ТЗ либо реализованы, либо явно отложены;
- список известных ограничений записан.

### Контрольные точки

| Milestone | Что должно работать | Накопительно, часы |
| --- | --- | ---: |
| M1. Каркас | App, settings, health, DB, Redis | 16-26 |
| M2. Схема данных | Модели, миграции, индексы | 30-48 |
| M3. Auth готов | Telegram login, access, refresh rotation | 60-94 |
| M4. Каталог готов | Items, my items, rating, privacy | 84-130 |
| M5. Scan flow готов | Secret validation без гонки | 98-154 |
| M6. MVP готов | Profile, settings, cache, базовые тесты | 112-176 |
| M7. Production baseline | Admin/seed, CI, Docker, audit, docs | 132-190 |

### Что можно отложить, если хочется быстрее получить MVP

Можно отложить:

- полноценный admin API, заменить seed-скриптами;
- Telegram bot worker;
- advanced metrics;
- replay protection для Telegram initData;
- CSRF double-submit, если `SameSite=Lax` достаточно для выбранной схемы;
- сложный RBAC, оставить только `USER` и `ADMIN`.

Нельзя откладывать:

- отсутствие секретов в git;
- refresh-token только в HttpOnly cookie;
- серверные refresh-сессии и rotation;
- Pydantic validation для входных body;
- безопасный rank без гонки;
- индексы под foreign keys и hot queries;
- базовые tests на auth и secret validation.

## 21. Отличия от текущего backend, которые обязательно исправить

- Убрать hardcoded `BOT_TOKEN`, `SECRET_KEY`, `DATABASE_URL`.
- Перенести URL Alembic в env.
- Не возвращать refresh-token в JSON.
- Хранить refresh-сессии на сервере.
- Сделать refresh rotation.
- Убрать `print(data)`, `print(cookies)`, `print(user_data)`.
- Не хранить сырой item secret в БД.
- Валидировать body `/items/secret` через Pydantic model.
- Ловить ошибки base64/JWT и возвращать 400, а не 500.
- Разделить причины JWT errors.
- Исправить гонку при rank.
- Добавить индексы на foreign keys и hot filters.
- Сделать Redis fail-open и invalidation count cache.
- Добавить response_model на все endpoints.
- Сделать DTO-ответы объектами, а не голыми `int`/`bool`, где это публичный API.
- Убрать магический runtime DI через `__getattr__` или заменить на явные зависимости.
- Добавить тесты.
