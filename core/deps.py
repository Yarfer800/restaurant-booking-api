from collections.abc import AsyncGenerator

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import session_manager
from core.exceptions import AuthError, ForbiddenError
from core.redis import is_token_blacklisted
from core.security import decode_token
from models.user import User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with session_manager.session() as session:
        yield session


async def get_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if credentials is None:
        raise AuthError("Требуется авторизация")
    return credentials.credentials


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    if credentials is None:
        raise AuthError("Требуется авторизация")

    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError:
        raise AuthError("Невалидный или истёкший токен") from None

    if payload.get("type") != "access":
        raise AuthError("Ожидался access-токен")

    if await is_token_blacklisted(payload.get("jti")):
        raise AuthError("Токен отозван")

    user = await session.get(User, int(payload["sub"]))
    if user is None:
        raise AuthError("Пользователь не найден")
    return user


async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.admin:
        raise ForbiddenError("Требуются права администратора")
    return user
