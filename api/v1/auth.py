from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_bearer_token, get_session
from core.exceptions import RateLimitError
from core.redis import rate_limited
from schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenData,
    UserOut,
)
from services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201, summary="Регистрация нового пользователя")
async def register(
    data: RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserOut:
    service = AuthService(session)
    user = await service.register(data)
    await session.commit()
    await session.refresh(user)
    return UserOut.model_validate(user)


@router.post("/login", response_model=TokenData, summary="Вход и выдача токенов")
async def login(
    data: LoginRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenData:
    ip = request.client.host if request.client is not None else "unknown"
    if not await rate_limited(f"login:{ip}", limit=10, window_seconds=60):
        raise RateLimitError("Слишком много попыток входа, попробуйте позже")

    service = AuthService(session)
    user = await service.authenticate(data)
    return await service.issue_tokens(user)


@router.post("/refresh", response_model=TokenData, summary="Ротация refresh-токена")
async def refresh(
    data: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenData:
    service = AuthService(session)
    return await service.refresh_tokens(data.refresh_token)


@router.post("/logout", summary="Выход: токены попадают в blacklist")
async def logout(
    data: LogoutRequest,
    access_token: Annotated[str, Depends(get_bearer_token)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    service = AuthService(session)
    await service.logout(access_token, data.refresh_token)
    return {"detail": "Вы вышли из системы"}
