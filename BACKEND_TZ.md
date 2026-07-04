# Техническое задание на backend [БЫЛО: Compactics] -> [СТАЛО: Skanshi]

Версия документа: 1.0  
Дата: [БЫЛО: 2026-06-29] -> [СТАЛО: 2026-07-04]  
Область: только backend, без frontend, CSS, HTML и клиентской логики.

[ДОБАВЛЕНО] Основание изменения: фронтенд-проект называется `Skanshi Telegram Mini App` и содержит маршруты/экраны Skanshi, а не Compactics. См. `frontend/README.md`, `frontend/index.html`, `frontend/src/App.jsx`.

[ДОБАВЛЕНО] Статус сверки с фронтендом: текущий фронтенд фактически выполняет только один backend HTTP-запрос — `GET /map/api-key` без префикса `/api/v1`. Все остальные данные экранов сейчас берутся из `frontend/src/data/mockData.js`, auth-token не хранится и не отправляется, `Authorization: Bearer ...` в коде отсутствует, websocket/EventSource не используются. Поэтому ниже явно разделены:

- обязательный контракт для текущего фронтенда;
- DTO экранов, которые фронт уже ожидает по структуре mock-данных;
- production/backend roadmap endpoints, которые в текущей сборке фронта не вызываются.

Причина: `frontend/src/hooks/useYMapLoader.js:28` вызывает `fetch('/map/api-key', { credentials: 'include' })`; `frontend/src/context/AppStateContext.jsx` импортирует данные из `mockData.js`; поиск по `Authorization`, `Bearer`, `WebSocket`, `EventSource` в `src` не находит backend-интеграции.

## 1. Цель проекта

[БЫЛО: Backend Compactics обслуживает Telegram Mini App / web-приложение для коллекционирования предметов. Пользователь авторизуется через Telegram `initData`, получает access-token и refresh-cookie, просматривает каталог предметов, сканирует QR/startapp-секреты, получает предметы в свою коллекцию, видит свой прогресс и рейтинг по конкретному предмету.] -> [СТАЛО: Backend Skanshi обслуживает Telegram Mini App / web-приложение для AR-квестов, городской карты, точек сканирования, XP, квестов, достижений и профиля пользователя. Для текущей версии фронтенда обязательный backend-контракт состоит из runtime endpoint `GET /map/api-key`; остальные экраны пока получают данные из локальных mock-структур, но backend-ТЗ фиксирует их DTO, чтобы последующая серверная интеграция не расходилась с UI.]

// ИЗМЕНЕНО: фронтенд содержит экраны `home`, `map`, `scan`, `quests`, `profile`, `xp`, `achievements`; каталог предметов и рейтинг по item в текущем frontend-коде не вызываются. См. `frontend/src/App.jsx`, `frontend/src/data/mockData.js`.

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
| [ДОБАВЛЕНО] `YANDEX_MAPS_API_KEY` | str/null | `yandex-api-key` | Ключ Яндекс.Карт v3, который backend возвращает через `GET /map/api-key`, если ключ не внедрен во фронт через `VITE_YMAP_API_KEY`/`VITE_YANDEX_MAPS_API_KEY` |

Правила:

- В production `COOKIE_SECURE=true`.
- В production `SQL_ECHO=false`.
- `FRONTEND_ORIGINS` задается списком точных origins. Не добавлять localhost в production.
- Alembic должен брать `DATABASE_URL` из окружения, а не из файла миграций.
- Docker Compose для production не должен публиковать наружу порты PostgreSQL и Redis.
- [ДОБАВЛЕНО] Для `YANDEX_MAPS_API_KEY` обязательно настроить ограничения по allowed domains/origins в кабинете Яндекс.Карт. Этот ключ попадает в browser и не должен считаться серверным секретом уровня `BOT_TOKEN`.

// ИЗМЕНЕНО: фронт сначала ищет ключ в `window.RUNTIME_CONFIG?.VITE_YMAP_API_KEY`, `window.RUNTIME_CONFIG?.YMAP_API_KEY`, `import.meta.env.VITE_YMAP_API_KEY`, `import.meta.env.VITE_YANDEX_MAPS_API_KEY`, а при отсутствии вызывает `GET /map/api-key`. См. `frontend/src/hooks/useYMapLoader.js:11-28`.

## 5. Архитектура проекта

Рекомендуемая структура:

```text
backend/
  app/
    main.py
    config.py
    api/
      runtime.py
      v1/
        router.py
        auth.py
        items.py
        map_points.py
        quests.py
        achievements.py
        xp.py
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
      map.py
      quest.py
      achievement.py
      xp.py
      validation.py
      common.py
    services/
      auth_service.py
      item_service.py
      map_service.py
      quest_service.py
      achievement_service.py
      xp_service.py
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
- [ДОБАВЛЕНО] `api/runtime.py` содержит root-level endpoint `GET /map/api-key` без префикса `/api/v1`, потому что текущий frontend вызывает именно этот path.
- [ДОБАВЛЕНО] `map_points.py`, `quests.py`, `achievements.py`, `xp.py` нужны для серверной замены данных из `frontend/src/data/mockData.js`; текущий frontend их пока не вызывает, но DTO ниже фиксируют ожидаемую форму.

// ИЗМЕНЕНО: старое ТЗ покрывало только `items`, а фронтенд показывает карту, точки, квесты, XP-историю и достижения. См. `frontend/src/pages/*.jsx` и `frontend/src/data/mockData.js`.

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

### [ДОБАВЛЕНО] 6.10 `map_points`

Городские точки, которые фронт отображает на карте и в bottom sheet.

Причина: `frontend/src/data/mockData.js:33-74`, `frontend/src/pages/MapPage.jsx:328-449`, `frontend/src/pages/PointDetailPage.jsx:10`.

| Колонка | Тип | Ограничения | Описание |
| --- | --- | --- | --- |
| `id` | varchar(96) | pk | Стабильный slug/id точки, например `roof-beacon`; фронт использует строковый id |
| `name` | varchar(160) | not null | Название точки |
| `category` | varchar(64) | not null | Display-категория: `QR-метка`, `AR-сцена`, `Секрет` |
| `rarity` | enum | not null | `common`, `rare`, `epic`, `legendary`, `mythic` |
| `latitude` | numeric(9,6) | not null | Широта; фронтовый `coords[0]` |
| `longitude` | numeric(9,6) | not null | Долгота; фронтовый `coords[1]` |
| `reward_xp` | int | not null default 0 | Награда XP |
| `description` | text | not null default empty | Описание точки |
| `quest_id` | varchar(96) | nullable fk `quests.id` | Связанный квест |
| `is_big` | bool | not null default false | Увеличенный маркер на карте |
| `has_hint` | bool | not null default false | Показывать радиус-подсказку |
| `is_active` | bool | not null default true | Показывать точку во фронте |
| `created_at` | timestamptz | not null | Создана |
| `updated_at` | timestamptz | not null | Обновлена |

Индексы:

- `ix_map_points_active` on `is_active`;
- `ix_map_points_rarity` on `rarity`;
- `ix_map_points_lat_lon` on `(latitude, longitude)`;
- если подключен PostGIS: `geography(Point,4326)` + GiST index для nearby-запросов.

### [ДОБАВЛЕНО] 6.11 `quests`

Квесты, которые фронт показывает на главной и странице квестов.

Причина: `frontend/src/data/mockData.js:21-25`, `frontend/src/pages/HomePage.jsx:84-101`, `frontend/src/pages/QuestsPage.jsx:6-36`.

| Колонка | Тип | Ограничения |
| --- | --- | --- |
| `id` | varchar(96) | pk |
| `name` | varchar(160) | not null |
| `step_label` | varchar(80) | not null |
| `progress_percent` | int | not null default 0, check 0..100 |
| `rarity` | enum | not null |
| `reward_xp` | int | not null default 0 |
| `season_id` | varchar(96) | nullable |
| `is_active` | bool | not null default true |
| `created_at` | timestamptz | not null |
| `updated_at` | timestamptz | not null |

### [ДОБАВЛЕНО] 6.12 `events`

Активный сезонный/ивентовый блок главного экрана.

Причина: `frontend/src/data/mockData.js:14-18`, `frontend/src/pages/HomePage.jsx:69-78`.

| Колонка | Тип | Ограничения |
| --- | --- | --- |
| `id` | varchar(96) | pk |
| `title` | varchar(180) | not null |
| `rarity` | enum | not null |
| `xp_multiplier` | numeric(5,2) | not null default 1 |
| `starts_at` | timestamptz | not null |
| `ends_at` | timestamptz | not null |
| `is_active` | bool | not null default true |
| `created_at` | timestamptz | not null |
| `updated_at` | timestamptz | not null |

DTO должен дополнительно отдавать display-поля `xpMultiplier` и `timeLeft`, потому что текущий UI выводит готовые строки.

### [ДОБАВЛЕНО] 6.13 `xp_events`

История XP и недавние награды.

Причина: `frontend/src/data/mockData.js:27-31`, `frontend/src/data/mockData.js:100-116`, `frontend/src/pages/HomePage.jsx:108-128`, `frontend/src/pages/XpHistoryPage.jsx:46-76`.

| Колонка | Тип | Ограничения |
| --- | --- | --- |
| `id` | bigint | pk |
| `user_id` | bigint | fk `users.id`, not null |
| `source` | varchar(180) | not null |
| `tag` | varchar(32) | nullable |
| `xp` | int | not null |
| `multiplier` | numeric(5,2) | nullable |
| `color` | enum | nullable, values `cyan`, `violetHi`, `gold`, `pink` |
| `occurred_at` | timestamptz | not null |
| `created_at` | timestamptz | not null |

Индексы:

- `ix_xp_events_user_occurred` on `(user_id, occurred_at desc)`.

DTO должен отдавать `time` как display-строку (`"12 мин назад"`, `"14:22"`) или отдельно `occurred_at` и согласованное поле `time`.

### [ДОБАВЛЕНО] 6.14 `achievements` и `user_achievements`

Справочник достижений и прогресс пользователя.

Причина: `frontend/src/data/mockData.js:119-128`, `frontend/src/pages/AchievementsPage.jsx:7-65`.

`achievements`:

| Колонка | Тип | Ограничения |
| --- | --- | --- |
| `id` | varchar(96) | pk |
| `icon` | varchar(32) | not null |
| `name` | varchar(128) | not null |
| `rarity` | enum | not null |
| `description` | text | not null default empty |
| `reward_xp` | int | not null default 0 |
| `created_at` | timestamptz | not null |
| `updated_at` | timestamptz | not null |

`user_achievements`:

| Колонка | Тип | Ограничения |
| --- | --- | --- |
| `user_id` | bigint | fk `users.id`, not null |
| `achievement_id` | varchar(96) | fk `achievements.id`, not null |
| `unlocked` | bool | not null default false |
| `progress_percent` | int | not null default 0, check 0..100 |
| `unlocked_at` | timestamptz | nullable |

Constraint: unique `(user_id, achievement_id)`.

### [ДОБАВЛЕНО] 6.15 Расширение `users` под профиль Skanshi

[БЫЛО: `users` хранит только Telegram-поля, privacy и роль.] -> [СТАЛО: кроме Telegram-полей, backend должен уметь вернуть профильные поля, которые фронт отображает: `display_name`, `public_id`, `rank`, `level`, `level_progress`, `xp`, `next_level_xp`, `streak_days`, `season_label`. Их можно хранить в `users`, отдельной таблице `user_profiles` или вычислять из `xp_events`, но DTO ответа обязан содержать эти поля.]

Причина: `frontend/src/data/mockData.js:1-11`, `frontend/src/pages/HomePage.jsx:20-42`, `frontend/src/pages/ProfilePage.jsx:21-54`.

### [ДОБАВЛЕНО] 6.16 Совместимость старых `items` и новых AR-точек

Старые таблицы `items`, `item_secrets`, `validations` остаются допустимым production-механизмом коллекции, но текущий фронт не вызывает item-каталог и не отправляет secret token на backend. Для текущей версии UI обязательны `map_points`, `quests`, `xp_events`, `achievements` и runtime-config endpoint карты.

// ИЗМЕНЕНО: это устраняет расхождение, где ТЗ подробно описывало предметы, но не описывало основные сущности, уже видимые во frontend UI.

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

### [ДОБАВЛЕНО] 7.8 Runtime config DTO

`MapApiKeyResponse`:

```json
{
  "api_key": "yandex-maps-browser-key"
}
```

Правила:

- поле называется строго `api_key`, не `apiKey`;
- значение должно быть непустой строкой;
- endpoint не должен требовать `Authorization`, потому что текущий frontend не отправляет access-token;
- при отсутствии ключа вернуть `503` с `ErrorResponse`, а не HTML/plain text.

Причина: `frontend/src/hooks/useYMapLoader.js:28-38` вызывает `response.json()` и проверяет `typeof payload.api_key === 'string'`.

### [ДОБАВЛЕНО] 7.9 DTO экранов текущего frontend

Эти DTO соответствуют структурам из `frontend/src/data/mockData.js`. Текущий frontend пока не запрашивает их по HTTP, но backend-ТЗ должно фиксировать их как целевую форму для замены mock-данных без изменения UI-семантики.

`Rarity`:

```json
"common | rare | epic | legendary | mythic"
```

`UiColorToken`:

```json
"cyan | violetHi | gold | pink"
```

`CurrentUserDashboard`:

```json
{
  "name": "Нэйт",
  "username": "nate_void",
  "id": "0xN4TE",
  "rank": 142,
  "level": 14,
  "levelProgress": 68,
  "xp": 6840,
  "nextLevelXp": 10000,
  "streakDays": 6,
  "season": "СЕЗОН 2 · ПУЛЬС ГОРОДА"
}
```

`ActiveEventResponse`:

```json
{
  "rarity": "mythic",
  "title": "Затмение: Ночь Реликвий",
  "xpMultiplier": "×3 XP",
  "timeLeft": "2Д 14Ч"
}
```

`QuestCardResponse`:

```json
{
  "id": "old-town-shadows",
  "name": "Тени Старого города",
  "step": "Точка 3 из 5",
  "progress": 60,
  "rarity": "epic",
  "xp": 450
}
```

`RewardFeedItemResponse`:

```json
{
  "source": "Скан · ТЦ «Орбита»",
  "xp": 120,
  "multiplier": "×2",
  "time": "12 мин назад",
  "color": "cyan"
}
```

`MapPinResponse`:

```json
{
  "id": "roof-beacon",
  "name": "Маяк на крыше",
  "coords": [55.75162, 37.61866],
  "rarity": "epic",
  "big": true,
  "hint": false
}
```

`NearbyPointResponse`:

```json
{
  "id": "roof-beacon",
  "name": "Маяк на крыше",
  "coords": [55.75162, 37.61866],
  "category": "AR-сцена",
  "rarity": "epic",
  "distance": "120 м",
  "done": false
}
```

`PointDetailResponse`:

```json
{
  "id": "roof-beacon",
  "name": "Маяк на крыше",
  "category": "AR-СЦЕНА",
  "distance": "120 М",
  "rarity": "epic",
  "reward": 180,
  "status": "Не пройдено",
  "quest": "Тени Старого города",
  "description": "Описание точки"
}
```

`ProfileStatResponse`:

```json
{
  "value": "218",
  "label": "СКАНОВ",
  "color": "cyan"
}
```

`XpHistoryGroupResponse`:

```json
{
  "day": "СЕГОДНЯ",
  "items": [
    {
      "source": "Скан · Маяк на крыше",
      "tag": "AR",
      "xp": 180,
      "multiplier": "×3",
      "color": "cyan",
      "time": "14:22"
    }
  ]
}
```

`AchievementResponse`:

```json
{
  "icon": "qr",
  "name": "Первый скан",
  "rarity": "common",
  "unlocked": true,
  "progress": 100
}
```

`FrontendAppStateResponse`:

```json
{
  "user": {},
  "activeEvent": {},
  "quests": [],
  "recentRewards": [],
  "mapPins": [],
  "nearbyPoints": [],
  "pointDetails": {},
  "stats": [],
  "xpHistoryGroups": [],
  "achievements": []
}
```

Правила совместимости:

- Для DTO, которые заменяют `mockData.js`, использовать camelCase там, где фронт уже читает camelCase: `levelProgress`, `nextLevelXp`, `streakDays`, `activeEvent`, `recentRewards`, `mapPins`, `nearbyPoints`, `pointDetails`, `xpHistoryGroups`.
- `coords` отдавать как `[latitude, longitude]`; frontend сам преобразует в `[longitude, latitude]` для Yandex Maps. См. `frontend/src/pages/MapPage.jsx:45-52`.
- `distance`, `time`, `timeLeft`, `step`, `status`, `season`, `value` являются display-строками. Если backend также отдает числовые поля, они не заменяют эти строки без изменения фронта.
- `pointDetails` должен быть объектом, где ключ — id точки, а значение — `PointDetailResponse`, потому что frontend обращается как `pointDetails[selectedPointId]`.

// ИЗМЕНЕНО: старые DTO `ItemFullResponse`/`ValidationResponse` не покрывают данные, которые реально отображают страницы `HomePage`, `MapPage`, `QuestsPage`, `ProfilePage`, `XpHistoryPage`, `AchievementsPage`.

## 8. HTTP API

Базовый префикс: `/api/v1`.

[ДОБАВЛЕНО] Исключение из базового префикса: `GET /map/api-key` должен быть доступен по root-level path `/map/api-key`, потому что текущий frontend вызывает именно `fetch('/map/api-key', { credentials: 'include' })`. Реализация только на `/api/v1/map/api-key` не удовлетворяет текущему фронту без изменения frontend-кода.

Все protected endpoints требуют:

```http
Authorization: Bearer <access_token>
```

[ДОБАВЛЕНО] В текущем frontend-коде нет отправки `Authorization` header, access-token, refresh-token refresh-flow или websocket-событий. Поэтому protected endpoints ниже являются production roadmap/будущим backend API, но не обязательным контрактом для уже имеющегося frontend bundle. Причина: поиск по `Authorization`, `Bearer`, `/auth`, `WebSocket`, `EventSource` в `frontend/src` не находит вызовов.

### [ДОБАВЛЕНО] 8.0 Runtime config

#### `GET /map/api-key`

Статус: обязателен для текущего frontend fallback.

Auth:

- `Authorization` не требуется;
- cookie не требуется, но frontend отправляет `credentials: 'include'`, поэтому CORS/Set-Cookie политика не должна ломать запрос;
- endpoint должен работать до логина.

Request:

- body отсутствует;
- query параметры отсутствуют;
- headers специальные не требуются.

Логика:

1. Прочитать `YANDEX_MAPS_API_KEY` из env/secret manager.
2. Если ключ отсутствует или пустой, вернуть `503 map_api_key_not_configured`.
3. Вернуть JSON строго с полем `api_key`.

Ответ `200`:

```json
{
  "api_key": "yandex-maps-browser-key"
}
```

Ошибки:

- `503 map_api_key_not_configured`: ключ не настроен;
- `500 internal_error`: неожиданная ошибка чтения конфигурации.

Пояснение: frontend при любом `!response.ok`, невалидном JSON или отсутствии непустого `api_key` показывает fallback-состояние карты. См. `frontend/src/hooks/useYMapLoader.js:28-38`, текст fallback в `frontend/src/pages/MapPage.jsx:210`.

### [ДОБАВЛЕНО] 8.0.1 Статус endpoints относительно текущего фронта

| Endpoint/группа | Статус после сверки | Причина |
| --- | --- | --- |
| `GET /map/api-key` | обязательный, отсутствовал в ТЗ | Единственный фактический backend fetch во фронте: `frontend/src/hooks/useYMapLoader.js:28` |
| `POST /auth/init`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me` | [ДОБАВЛЕНО] не вызываются текущим frontend bundle; оставить как production roadmap | Login button просто ведет на `/home`, `useTelegram()` не отправляет `initData` на backend: `frontend/src/pages/LoginPage.jsx:45-58`, `frontend/src/hooks/useTelegram.js:55-75` |
| `/items`, `/items/my`, `/items/{id}`, `/items/{id}/rating`, `POST /items/secret` | [ДОБАВЛЕНО] не вызываются текущим frontend bundle; старый item-каталог не соответствует видимым экранам Skanshi | Scanner/result меняют локальный state: `frontend/src/pages/ScanPage.jsx:82`, `frontend/src/pages/ScanResultPage.jsx:8-12`; данные берутся из `mockData.js` |
| `/profile/validations/count`, `/users/settings/privacy` | [ДОБАВЛЕНО] не вызываются текущим frontend bundle; текущий профиль ожидает расширенный dashboard DTO | `frontend/src/pages/ProfilePage.jsx:15-80` читает `user`, `stats`, `profileLinks` из AppState |
| WebSocket/SSE | [ДОБАВЛЕНО] не используется | В `frontend/src` нет `WebSocket`/`EventSource`/socket.io |

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

### [ДОБАВЛЕНО] 8.6 Frontend data API для замены `mockData.js`

Статус: целевой контракт для серверной интеграции текущих экранов; текущий frontend bundle эти endpoints пока не вызывает.

Причина: все страницы получают данные через `useAppState()` из `frontend/src/context/AppStateContext.jsx`, а начальные значения импортируются из `frontend/src/data/mockData.js`.

#### `GET /app/state`

Protected после подключения реального auth. Для текущего mock-режима не вызывается.

Назначение: одним запросом вернуть данные первого экрана и навигационных разделов без N+1 на клиенте.

Ответ `200`: `FrontendAppStateResponse`.

Минимальный состав:

```json
{
  "user": {},
  "activeEvent": {},
  "quests": [],
  "recentRewards": [],
  "mapPins": [],
  "nearbyPoints": [],
  "pointDetails": {},
  "stats": [],
  "xpHistoryGroups": [],
  "achievements": []
}
```

#### `GET /map/points`

Protected после подключения реального auth. Для текущего mock-режима не вызывается.

Query:

| Параметр | Тип | Default | Описание |
| --- | --- | --- | --- |
| `lat` | number/null | null | Широта пользователя, если доступна |
| `lon` | number/null | null | Долгота пользователя, если доступна |
| `radius_meters` | int | 1000 | Радиус nearby |
| `rarity` | enum/null | null | Фильтр редкости |
| `category` | str/null | null | Фильтр категории |
| `done` | bool/null | null | Фильтр прохождения |

Ответ `200`:

```json
{
  "mapPins": [],
  "nearbyPoints": [],
  "pointDetails": {}
}
```

Правила:

- `coords` отдавать как `[latitude, longitude]`;
- `nearbyPoints` сортировать по расстоянию, потому что UI показывает `ПО РАССТОЯНИЮ`;
- фильтры должны поддерживать текущие UI-чипы: все, не пройдено, редкие, секреты. Сейчас чипы не отправляют query, но backend-контракт должен быть готов.

#### `GET /quests`

Protected после подключения реального auth. Ответ `200`:

```json
{
  "items": []
}
```

Элемент массива: `QuestCardResponse`.

#### `GET /xp/history`

Protected после подключения реального auth.

Query:

| Параметр | Тип | Default |
| --- | --- | --- |
| `limit` | int | 50 |
| `offset` | int | 0 |
| `tag` | str/null | null |

Ответ `200`:

```json
{
  "groups": []
}
```

Элемент `groups`: `XpHistoryGroupResponse`.

#### `GET /achievements`

Protected после подключения реального auth. Ответ `200`:

```json
{
  "items": [],
  "summary": {
    "unlocked": 23,
    "total": 60
  }
}
```

Элемент `items`: `AchievementResponse`.

#### `POST /scan/claim`

Protected после подключения реального auth. Для текущего frontend не вызывается: кнопка `Забрать награду` вызывает локальный `claimReward()`.

Request:

```json
{
  "scan_id": "string"
}
```

Ответ `200`:

```json
{
  "status": "claimed",
  "xp": 250,
  "user": {}
}
```

Ошибки:

- `404 scan_not_found`;
- `409 reward_already_claimed`;
- `422 validation_error`.

// ИЗМЕНЕНО: эти endpoints закрывают UI-данные, отсутствующие в старом ТЗ: карта, квесты, XP-история, достижения, агрегированный профиль.

### [БЫЛО: 8.6 Admin API] -> [СТАЛО: 8.7 Admin API]

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

### [ДОБАВЛЕНО] 9.1.1 Загрузка карты текущим frontend

Текущий happy path:

1. Frontend пытается получить ключ карты из `window.RUNTIME_CONFIG` или Vite env.
2. Если ключ не найден, frontend вызывает `GET /map/api-key` с `credentials: include`.
3. Backend возвращает `{"api_key":"..."}`.
4. Frontend подключает `https://api-maps.yandex.ru/v3/?apikey=<api_key>&lang=ru_RU`.
5. Frontend отображает `mapPins`, `nearbyPoints`, `pointDetails` из локального состояния.

Ошибочный сценарий:

- если backend возвращает не-2xx, не JSON или JSON без непустого `api_key`, frontend показывает fallback `"Карта ждёт подключение"`.

Причина: `frontend/src/hooks/useYMapLoader.js:11-38`, `frontend/src/pages/MapPage.jsx:210`.

### [БЫЛО: 9.2 Telegram login] -> [СТАЛО: 9.2 Telegram login, future production flow]

[ДОБАВЛЕНО] Статус: текущий frontend не отправляет `initData`/`tg_web_app_data` на backend. Этот сценарий остается требованием для production auth, но не является текущим фронтовым контрактом.

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

### [БЫЛО: 9.5 Получение предмета по QR/startapp secret] -> [СТАЛО: 9.5 Получение предмета по QR/startapp secret, future production flow]

[ДОБАВЛЕНО] Статус: текущий frontend не декодирует QR, не отправляет token на `/items/secret` и не вызывает backend при нажатии `Забрать награду`. Экран сканирования ведет на `/result`, а награда применяется локальным reducer. См. `frontend/src/pages/ScanPage.jsx:82`, `frontend/src/pages/ScanResultPage.jsx:8-12`, `frontend/src/context/AppStateContext.jsx:41-45`.

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
  - [ДОБАВЛЕНО] `/map/api-key`: например 60/min per IP, endpoint публичный и не требует auth;
  - `/auth/init`: например 10/min per IP;
  - `/auth/refresh`: 30/min per IP/session;
  - `/items/secret`: 20/min per user.
- Ограничить размер body на уровне reverse proxy и приложения.
- Все входные строки иметь max length.
- Для admin endpoints проверять `role`.
- SQLAlchemy queries строить параметризованно, без string interpolation.
- [ДОБАВЛЕНО] `YANDEX_MAPS_API_KEY`, возвращаемый в browser, должен быть ограничен по доменам в настройках Яндекс.Карт. Backend не должен логировать значение ключа.

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
- [ДОБАВЛЕНО] `/map/api-key`: p95 < 50 ms, без обращения к внешним сервисам;
- [ДОБАВЛЕНО] `/map/points` на 1000 active points: p95 < 250 ms при warm DB/PostGIS index, если endpoint реализуется;
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
- [ДОБАВЛЕНО] `map_points`;
- [ДОБАВЛЕНО] `quests`;
- [ДОБАВЛЕНО] `events`;
- [ДОБАВЛЕНО] `xp_events`;
- [ДОБАВЛЕНО] `achievements`;
- [ДОБАВЛЕНО] `user_achievements`;
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
- [ДОБАВЛЕНО] map api-key config failures by reason, без логирования самого ключа.

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

Runtime config:

- [ДОБАВЛЕНО] `GET /map/api-key` возвращает `200` и JSON `{"api_key": "..."}` при настроенном `YANDEX_MAPS_API_KEY`;
- [ДОБАВЛЕНО] `GET /map/api-key` не требует `Authorization`;
- [ДОБАВЛЕНО] `GET /map/api-key` возвращает `503 map_api_key_not_configured`, если ключ пустой;
- [ДОБАВЛЕНО] ответ не содержит `apiKey` вместо `api_key`;
- [ДОБАВЛЕНО] значение ключа не попадает в логи.

Frontend DTO:

- [ДОБАВЛЕНО] `MapPinResponse.coords` сериализуется как `[latitude, longitude]`;
- [ДОБАВЛЕНО] `pointDetails` сериализуется как объект по id точки, а не массив;
- [ДОБАВЛЕНО] DTO экранов сохраняют camelCase-поля, которые читает фронт: `levelProgress`, `nextLevelXp`, `streakDays`, `xpHistoryGroups`;
- [ДОБАВЛЕНО] `rarity` ограничен значениями `common`, `rare`, `epic`, `legendary`, `mythic`.

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

- [ДОБАВЛЕНО] для текущего frontend fallback реализован `GET /map/api-key` без префикса `/api/v1`;
- [ДОБАВЛЕНО] `GET /map/api-key` возвращает строго `api_key` и не требует `Authorization`;
- [ДОБАВЛЕНО] OpenAPI/документация явно помечает auth/items/profile endpoints как не вызываемые текущим frontend bundle, если они остаются в roadmap;
- [ДОБАВЛЕНО] DTO для будущей замены `mockData.js` соответствуют разделу 7.9;
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
2. [ДОБАВЛЕНО] Реализовать root-level `GET /map/api-key` и покрыть его тестами, потому что это единственный endpoint, который уже вызывает текущий frontend.
3. Подключить PostgreSQL async engine и Alembic.
4. Описать модели и первую миграцию со всеми индексами.
5. [ДОБАВЛЕНО] Описать модели `map_points`, `quests`, `events`, `xp_events`, `achievements`, `user_achievements`.
6. Реализовать repositories без магического DI.
7. Реализовать DTO.
8. [ДОБАВЛЕНО] Реализовать DTO раздела 7.9 для будущей замены `mockData.js`.
9. Реализовать security: JWT access/refresh, hashing, cookies.
10. Реализовать `/auth/init`, `/auth/refresh`, `/auth/logout`, `/auth/me`.
11. Реализовать protected dependency `CurrentUser`.
12. Реализовать каталог `/items`, `/items/my`, `/items/{id}`, rating.
13. Реализовать `/items/secret` с транзакцией и блокировкой item.
14. [ДОБАВЛЕНО] Реализовать `/app/state`, `/map/points`, `/quests`, `/xp/history`, `/achievements`, `/scan/claim`, если принято решение переводить текущие mock-экраны на backend.
15. Подключить Redis cache для count и rate limit.
16. Реализовать settings/profile endpoints.
17. Добавить admin API или seed-скрипты.
18. Написать тесты на auth, validations, гонки, Redis fallback.
19. [ДОБАВЛЕНО] Написать тесты на runtime map config и frontend DTO.
20. Настроить Docker, CI, `pip-audit`.
21. Прогнать миграции на чистой БД и тестовой БД.

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
- [ДОБАВЛЕНО] есть root-level `GET /map/api-key` для текущего frontend;
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
| [ДОБАВЛЕНО] Runtime endpoint `GET /map/api-key` + tests | 1-2 |
| Request id и базовое logging middleware | 2-3 |

Готово, когда:

- приложение падает на старте при невалидных env;
- [ДОБАВЛЕНО] `/map/api-key` возвращает `api_key` при настроенном ключе и `503` при пустом ключе;
- `/health/ready` проверяет БД и Redis;
- все ошибки имеют единый JSON-формат.

### Этап 2. Модели БД и миграции

Оценка: 14-22 часа.

Результат этапа:

- описаны все ORM-модели;
- создана первая Alembic migration;
- все constraints и индексы названы явно;
- миграция применяется на пустую БД.
- [ДОБАВЛЕНО] схема покрывает не только legacy items, но и сущности текущего UI: map points, quests, events, XP events, achievements.

Работы:

| Задача | Часы |
| --- | ---: |
| Настроить Alembic с `DATABASE_URL` из env | 2-3 |
| Описать `users`, `refresh_sessions` | 2-4 |
| Описать catalog tables: categories, types, prototypes, items, images | 3-5 |
| Описать `item_secrets`, `validations` | 2-4 |
| [ДОБАВЛЕНО] Описать `map_points`, `quests`, `events`, `xp_events`, `achievements`, `user_achievements` | 4-7 |
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
- [ДОБАВЛЕНО] есть DTO/repositories для `map_points`, `quests`, `events`, `xp_events`, `achievements`, если endpoints раздела 8.6 входят в scope;
- запросы не делают N+1.

Работы:

| Задача | Часы |
| --- | ---: |
| Описать DTO для auth/user/catalog/validation/common | 3-5 |
| [ДОБАВЛЕНО] Описать DTO экранов из раздела 7.9 | 2-4 |
| Реализовать repository base pattern | 2-3 |
| Реализовать user/session repositories | 2-3 |
| Реализовать item/catalog repositories с eager loading | 2-4 |
| Реализовать validation repository | 2-3 |
| [ДОБАВЛЕНО] Реализовать repositories для карты, квестов, XP и достижений | 4-7 |
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

- [ДОБАВЛЕНО] `GET /map/api-key`, если frontend не получает Yandex Maps key через `VITE_YMAP_API_KEY`, `VITE_YANDEX_MAPS_API_KEY` или `window.RUNTIME_CONFIG`;
- отсутствие секретов в git;
- refresh-token только в HttpOnly cookie;
- серверные refresh-сессии и rotation;
- Pydantic validation для входных body;
- безопасный rank без гонки;
- индексы под foreign keys и hot queries;
- базовые tests на auth и secret validation.

## 21. Отличия от текущего backend, которые обязательно исправить

- [ДОБАВЛЕНО] Добавить root-level endpoint `GET /map/api-key` без `/api/v1`, ответ `{"api_key":"..."}`.
- [ДОБАВЛЕНО] Добавить env `YANDEX_MAPS_API_KEY` и не логировать его значение.
- [ДОБАВЛЕНО] Документировать, что текущий frontend не вызывает `/auth/*`, `/items/*`, `/profile/*`, `/users/settings/*`, websocket/SSE.
- [ДОБАВЛЕНО] Добавить модели/DTO для текущих UI-доменов Skanshi: map points, quests, active event, XP history, achievements, dashboard profile.
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

## [ДОБАВЛЕНО] 22. Сводная таблица изменений после сверки с frontend

| Раздел / endpoint | Изменение | Почему нужно | Ссылка на frontend |
| --- | --- | --- | --- |
| Название и цель | `[БЫЛО: Compactics] -> [СТАЛО: Skanshi]`; цель расширена с коллекции предметов до AR-квестов, карты, XP, достижений и профиля | Фронтенд называется Skanshi и содержит соответствующие экраны | `frontend/README.md`, `frontend/index.html`, `frontend/src/App.jsx` |
| Общий статус API | Добавлен вывод аудита: текущий frontend реально вызывает только `GET /map/api-key`; остальные данные mock | Чтобы backend-разработчик не реализовывал старый API как якобы уже используемый фронтом | `frontend/src/context/AppStateContext.jsx`, `frontend/src/data/mockData.js` |
| Env | Добавлен `YANDEX_MAPS_API_KEY` | Backend должен уметь вернуть ключ карты, если он не внедрен во фронт через Vite/runtime config | `frontend/src/hooks/useYMapLoader.js:11-28` |
| Архитектура | Добавлены `api/runtime.py`, `map_points.py`, `quests.py`, `achievements.py`, `xp.py` и соответствующие schemas/services | Старый backend-layout не покрывал карту, квесты, XP и достижения | `frontend/src/pages/MapPage.jsx`, `frontend/src/pages/QuestsPage.jsx`, `frontend/src/pages/XpHistoryPage.jsx`, `frontend/src/pages/AchievementsPage.jsx` |
| DB | Добавлены `map_points`, `quests`, `events`, `xp_events`, `achievements`, `user_achievements`; расширен профиль пользователя | UI уже отображает точки, квесты, ивент, историю XP, достижения и профильные показатели | `frontend/src/data/mockData.js:1-128` |
| DTO | Добавлен `MapApiKeyResponse` со строгим `api_key` | Фронт проверяет именно `payload.api_key`; `apiKey` сломает карту | `frontend/src/hooks/useYMapLoader.js:34` |
| DTO | Добавлен набор DTO раздела 7.9 с camelCase-полями и display-строками | JSX читает `levelProgress`, `nextLevelXp`, `timeLeft`, `pointDetails[id]`, `coords` как `[lat, lon]` | `frontend/src/pages/HomePage.jsx`, `frontend/src/pages/MapPage.jsx`, `frontend/src/pages/ProfilePage.jsx` |
| `GET /map/api-key` | Добавлен root-level endpoint без `/api/v1`; public/no auth; response `{"api_key":"..."}`; error `503 map_api_key_not_configured` | Это единственный фактический backend fetch текущего frontend | `frontend/src/hooks/useYMapLoader.js:28-38` |
| `/auth/*` | Помечены как production roadmap, не текущий frontend contract | Login button не вызывает backend; `useTelegram()` не отправляет `initData` | `frontend/src/pages/LoginPage.jsx:45-58`, `frontend/src/hooks/useTelegram.js:55-75` |
| `/items/*`, `POST /items/secret` | Помечены как legacy/production roadmap, не текущий frontend contract | Сканирование и claim награды сейчас локальные, без request к backend | `frontend/src/pages/ScanPage.jsx:82`, `frontend/src/pages/ScanResultPage.jsx:8-12` |
| `/profile/validations/count`, `/users/settings/privacy` | Помечены как не вызываемые текущим frontend; добавлен будущий dashboard DTO | Профиль читает `user`, `stats`, `profileLinks` из AppState, не count/privacy endpoint | `frontend/src/pages/ProfilePage.jsx:15-80` |
| `GET /app/state` и frontend data API | Добавлены как целевой контракт для снятия `mockData.js`, но явно помечены как не вызываемые текущей сборкой | Позволяет backend-реализации соответствовать уже существующим формам UI без немедленного изменения фронта | `frontend/src/context/AppStateContext.jsx`, `frontend/src/data/mockData.js` |
| WebSocket/SSE | Явно указано, что не используется | В ТЗ не нужно добавлять websocket-события как обязательные | Поиск по `WebSocket`, `EventSource`, `socket.io` в `frontend/src` |
| Security | Добавлен rate limit для `/map/api-key`; ключ карты ограничивать по доменам и не логировать | Endpoint публичный, а ключ уходит в browser | `frontend/src/hooks/useYMapLoader.js:70` |
| Performance | Добавлены p95 для `/map/api-key` и `/map/points` | Новый обязательный endpoint должен иметь измеримые критерии | `frontend/src/pages/MapPage.jsx` |
| Tests | Добавлены тесты на `/map/api-key`, `api_key`, отсутствие auth, DTO координат и camelCase | Ловит основные несовместимости backend/frontend до ручной проверки | `frontend/src/hooks/useYMapLoader.js`, `frontend/src/data/mockData.js` |
| Acceptance | Добавлены критерии приемки для `/map/api-key` и DTO mockData replacement | Готовность backend теперь проверяется против текущих потребностей фронта | Разделы 7.8, 7.9, 8.0 |
