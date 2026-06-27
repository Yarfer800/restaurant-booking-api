import logging

import redis as redis_lib
from redis.asyncio import Redis

from config import config

logger = logging.getLogger("core.redis")


class RedisService:
    """Тонкая обёртка над асинхронным клиентом Redis."""

    def __init__(self) -> None:
        self._client: Redis | None = None

    async def connect(self) -> None:
        try:
            self._client = redis_lib.asyncio.from_url(config.redis_url, decode_responses=True)
            await self._client.ping()
            logger.info("Подключение к Redis установлено")
        except Exception:
            logger.warning("Redis недоступен, приложение работает без кэша и rate-limit")
            self._client = None

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> Redis | None:
        return self._client


redis_service = RedisService()


def get_redis() -> Redis | None:
    """Dependency: клиент Redis (может быть None, если Redis недоступен)."""
    return redis_service.client


async def rate_limited(key: str, limit: int, window_seconds: int) -> bool:
    """True — лимит не превышен. Fixed window: incr + expire."""
    client = redis_service.client
    if client is None:
        return True
    current = await client.incr(key)
    if current == 1:
        await client.expire(key, window_seconds)
    return current <= limit


async def blacklist_token(jti: str, ttl_seconds: int) -> None:
    client = redis_service.client
    if client is None:
        logger.warning("Redis недоступен, токен не попал в blacklist")
        return
    if ttl_seconds <= 0:
        return
    await client.set(f"blacklist:{jti}", "1", ex=ttl_seconds)


async def is_token_blacklisted(jti: str) -> bool:
    client = redis_service.client
    if client is None:
        return False
    return bool(await client.get(f"blacklist:{jti}"))
