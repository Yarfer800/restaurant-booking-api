import logging
from datetime import UTC, datetime

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import AuthError, ConflictError
from core.redis import blacklist_token, is_token_blacklisted
from core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from models.user import User, UserRole
from schemas.auth import LoginRequest, RegisterRequest, TokenData

logger = logging.getLogger("services.auth")


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def register(self, data: RegisterRequest) -> User:
        existing = await self._session.scalar(select(User).where(User.email == data.email))
        if existing is not None:
            raise ConflictError("Пользователь с таким email уже зарегистрирован")

        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            role=UserRole.user,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def authenticate(self, data: LoginRequest) -> User:
        user = await self._session.scalar(select(User).where(User.email == data.email))
        if user is None or not verify_password(data.password, user.hashed_password):
            raise AuthError("Неверный email или пароль")
        return user

    async def issue_tokens(self, user: User) -> TokenData:
        access_token, _ = create_access_token(user.id, user.role.value)
        refresh_token, _ = create_refresh_token(user.id, user.role.value)
        return TokenData(access_token=access_token, refresh_token=refresh_token)

    async def refresh_tokens(self, refresh_token: str) -> TokenData:
        try:
            payload = decode_token(refresh_token)
        except jwt.PyJWTError:
            raise AuthError("Невалидный или истёкший refresh-токен") from None

        if payload.get("type") != "refresh":
            raise AuthError("Ожидался refresh-токен")

        jti = payload.get("jti")
        if jti is None:
            raise AuthError("Refresh-токен без идентификатора")

        if await is_token_blacklisted(jti):
            raise AuthError("Refresh-токен отозван")

        user = await self._session.get(User, int(payload["sub"]))
        if user is None:
            raise AuthError("Пользователь не найден")

        await self._blacklist_with_remaining_ttl(payload, jti)
        return await self.issue_tokens(user)

    async def logout(self, access_token: str, refresh_token: str | None) -> None:
        try:
            access_payload = decode_token(access_token)
        except jwt.PyJWTError:
            raise AuthError("Невалидный access-токен") from None

        await self._blacklist_with_remaining_ttl(access_payload, access_payload.get("jti"))

        if refresh_token is not None:
            try:
                refresh_payload = decode_token(refresh_token)
            except jwt.PyJWTError:
                raise AuthError("Невалидный refresh-токен") from None
            await self._blacklist_with_remaining_ttl(refresh_payload, refresh_payload.get("jti"))

    @staticmethod
    async def _blacklist_with_remaining_ttl(payload: dict, jti: str | None) -> None:
        if jti is None:
            return
        exp = payload.get("exp")
        if exp is None:
            return
        ttl = int(exp - datetime.now(UTC).timestamp())
        await blacklist_token(jti, ttl)
