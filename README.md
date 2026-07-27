# restaurant-booking-api

REST API для бронирования столов в ресторанах. Пользователь ищет свободные столы по времени и
количеству гостей, создаёт брони; администратор управляет ресторанами, столами и статусами броней.

Без фронтенда — только JSON API с автодокументацией Swagger.

## Стек

- **Web:** FastAPI + uvicorn
- **ORM:** SQLAlchemy 2.0 (async) + asyncpg
- **БД:** PostgreSQL 16
- **Миграции:** Alembic
- **Кэш / rate-limit:** Redis
- **Аутентификация:** JWT (access + refresh, PyJWT), blacklist токенов в Redis
- **Тесты:** pytest + httpx
- **CI:** GitHub Actions (lint + тесты)

## Быстрый старт

### 1. Docker (вся инфраструктура одной командой)

```bash
cp .env.example .env      # при необходимости поменяйте JWT_SECRET
docker compose up --build
```

API будет доступен на http://localhost:8000, документация — http://localhost:8000/docs.

### 2. Локальная разработка

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn main:app --reload
```

PostgreSQL и Redis можно поднять без API:

```bash
docker compose up -d db redis
```

## Переменные окружения

| Переменная | По умолчанию | Описание |
|-----------|--------------|----------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/restaurant_booking` | Строка подключения к БД |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis (кэш, blacklist, rate-limit) |
| `JWT_SECRET` | `change-me` | Секрет для подписи токенов |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Время жизни access-токена |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Время жизни refresh-токена |
| `ENVIRONMENT` | `development` | Окружение |
| `ECHO_SQL` | `false` | Выводить SQL в логи |

## Эндпоинты

| Метод | Путь | Доступ | Описание |
|-------|------|--------|----------|
| `POST` | `/auth/register` | public | Регистрация |
| `POST` | `/auth/login` | public | Вход, выдача токенов (rate-limit по IP) |
| `POST` | `/auth/refresh` | public | Ротация refresh-токена |
| `POST` | `/auth/logout` | user | Выход, токены в blacklist |
| `GET` | `/restaurants` | public | Рестораны (пагинация) |
| `GET` | `/restaurants/{id}` | public | Ресторан со столами |
| `POST` | `/restaurants` | admin | Создать ресторан |
| `PATCH` | `/restaurants/{id}` | admin | Обновить ресторан |
| `DELETE` | `/restaurants/{id}` | admin | Удалить ресторан |
| `GET` | `/restaurants/{id}/tables/available` | public | Свободные столы на время (кэш Redis) |
| `POST` | `/restaurants/{id}/tables` | admin | Добавить стол |
| `GET` | `/tables/{id}` | public | Стол |
| `PUT` | `/tables/{id}` | admin | Обновить стол |
| `DELETE` | `/tables/{id}` | admin | Удалить стол |
| `POST` | `/reservations` | user | Создать бронь (rate-limit) |
| `GET` | `/me/reservations` | user | Свои брони |
| `GET` | `/reservations/{id}` | owner/admin | Бронь |
| `POST` | `/reservations/{id}/cancel` | owner/admin | Отменить бронь |
| `POST` | `/reservations/{id}/confirm` | admin | Подтвердить бронь |
| `POST` | `/reservations/{id}/complete` | admin | Завершить бронь |
| `GET` | `/health` | public | Проверка работоспособности |

## Примеры запросов

Регистрация и вход:

```bash
curl -X POST http://localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email": "user@example.com", "password": "password123"}'

curl -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email": "user@example.com", "password": "password123"}'
```

Создание ресторана (admin):

```bash
curl -X POST http://localhost:8000/restaurants \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <admin_access_token>' \
  -d '{
    "name": "Паприка",
    "address": "Москва, ул. Тверская, 1",
    "phone": "+7 900 000 00 00",
    "opening_time": "09:00",
    "closing_time": "23:00"
  }'
```

Поиск свободных столов и бронь:

```bash
curl 'http://localhost:8000/restaurants/1/tables/available?start=2026-08-01T18:00:00&end=2026-08-01T19:00:00&guests=4'

curl -X POST http://localhost:8000/reservations \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <access_token>' \
  -d '{
    "table_id": 1,
    "guest_count": 4,
    "start_time": "2026-08-01T18:00:00",
    "end_time": "2026-08-01T19:00:00"
  }'
```

## Логика бронирования

1. Валидация: `guest_count <= capacity`, `start < end`, интервал укладывается в рабочие часы.
2. Поиск пересечений по времени среди активных броней (`pending`, `confirmed`) того же стола.
3. Атомарная транзакция с `SELECT ... FOR UPDATE`.
4. При конфликте — `409 Conflict`.
5. Создаётся бронь со статусом `pending`.

## Тесты

```bash
uv run pytest
```

При локальном запуске тесты используют SQLite и fakeredis, в CI — реальные PostgreSQL и Redis.

## CI

GitHub Actions (`ci.yml`): job `lint` (ruff) и job `test` (postgres + redis services,
миграции alembic, pytest).