import os
from collections.abc import AsyncGenerator

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:////tmp/restaurant_booking_test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test-secret-0123456789abcdef0123456789abcdef")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "30")

import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient

from core.db import session_manager
from core.redis import redis_service
from core.security import hash_password
from main import create_app
from models import Base
from models.user import User, UserRole


@pytest.fixture
async def setup_database() -> AsyncGenerator[None]:
    session_manager.init()
    async with session_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    redis_service._client = fakeredis.aioredis.FakeRedis(decode_responses=True)

    yield

    await redis_service.close()
    await session_manager.close()


@pytest.fixture
async def client(setup_database) -> AsyncGenerator[AsyncClient]:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def register_user(
    client: AsyncClient,
    email: str = "user@example.com",
    password: str = "password123",
):
    return await client.post("/auth/register", json={"email": email, "password": password})


async def login_user(
    client: AsyncClient,
    email: str = "user@example.com",
    password: str = "password123",
):
    return await client.post("/auth/login", json={"email": email, "password": password})


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


async def create_entity_user(email: str, role: UserRole = UserRole.user) -> User:
    async with session_manager.session() as session:
        user = User(email=email, hashed_password=hash_password("password123"), role=role)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def login_as(client: AsyncClient, email: str) -> tuple[str, str]:
    """Возвращает (access, refresh) для прямого созданного пользователя."""
    resp = await client.post("/auth/login", json={"email": email, "password": "password123"})
    assert resp.status_code == 200
    body = resp.json()
    return body["access_token"], body["refresh_token"]


async def admin_headers(client: AsyncClient) -> dict[str, str]:
    """Создаёт админа и возвращает заголовки с его access-токеном."""
    await create_entity_user("admin@example.com", UserRole.admin)
    access, _ = await login_as(client, "admin@example.com")
    return auth_headers(access)


async def create_restaurant(client: AsyncClient, headers: dict[str, str], **overrides):
    payload = {
        "name": "Тестовый ресторан",
        "address": "Москва, ул. Пушкина",
        "phone": "+7 900 000 00 00",
        "description": "Уютное место",
        "opening_time": "09:00",
        "closing_time": "23:00",
        **overrides,
    }
    return await client.post("/restaurants", json=payload, headers=headers)


async def create_table(client: AsyncClient, restaurant_id: int, headers: dict[str, str], **overrides):
    payload = {"number": "1", "capacity": 4, **overrides}
    return await client.post(f"/restaurants/{restaurant_id}/tables", json=payload, headers=headers)
