from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_admin, get_current_user, get_session
from core.exceptions import ForbiddenError, NotFoundError, RateLimitError
from core.redis import rate_limited
from models.user import User
from repositories.reservation import ReservationRepository
from schemas.reservation import ReservationCreate, ReservationOut
from services.reservation import ReservationService

router = APIRouter(tags=["reservations"])


@router.post("/reservations", response_model=ReservationOut, status_code=201, summary="Создать бронь")
async def create_reservation(
    data: ReservationCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ReservationOut:
    if not await rate_limited(f"reservations:{user.id}", limit=10, window_seconds=60):
        raise RateLimitError("Слишком много броней за короткое время, попробуйте позже")

    service = ReservationService(session)
    try:
        reservation = await service.create(user, data)
    except Exception:
        await session.rollback()
        raise
    await session.commit()
    return await service.to_output(reservation)


@router.get("/me/reservations", response_model=list[ReservationOut], summary="Мои брони")
async def my_reservations(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ReservationOut]:
    repository = ReservationRepository(session)
    reservations = await repository.list_for_user(user.id)
    service = ReservationService(session)
    return [await service.to_output(r) for r in reservations]


@router.get("/reservations/{reservation_id}", response_model=ReservationOut, summary="Бронь по id (владелец или admin)")
async def get_reservation(
    reservation_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ReservationOut:
    repository = ReservationRepository(session)
    reservation = await repository.get(reservation_id)
    if reservation is None:
        raise NotFoundError("Бронь не найдена")
    if reservation.user_id != user.id:
        raise ForbiddenError("Нет доступа к этой брони")
    return await ReservationService(session).to_output(reservation)


@router.post(
    "/reservations/{reservation_id}/cancel",
    response_model=ReservationOut,
    summary="Отменить бронь (владелец или admin)",
)
async def cancel_reservation(
    reservation_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ReservationOut:
    repository = ReservationRepository(session)
    reservation = await repository.get(reservation_id)
    if reservation is None:
        raise NotFoundError("Бронь не найдена")
    if reservation.user_id != user.id:
        raise ForbiddenError("Нет доступа к этой брони")

    service = ReservationService(session)
    reservation = await service.cancel(reservation)
    await session.commit()
    return await service.to_output(reservation)


@router.post(
    "/reservations/{reservation_id}/confirm",
    response_model=ReservationOut,
    summary="Подтвердить бронь (admin)",
)
async def confirm_reservation(
    reservation_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    _admin: Annotated[bool, Depends(get_current_admin)],
) -> ReservationOut:
    repository = ReservationRepository(session)
    reservation = await repository.get(reservation_id)
    if reservation is None:
        raise NotFoundError("Бронь не найдена")

    service = ReservationService(session)
    reservation = await service.confirm(reservation)
    await session.commit()
    return await service.to_output(reservation)


@router.post(
    "/reservations/{reservation_id}/complete",
    response_model=ReservationOut,
    summary="Завершить бронь (admin)",
)
async def complete_reservation(
    reservation_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    _admin: Annotated[bool, Depends(get_current_admin)],
) -> ReservationOut:
    repository = ReservationRepository(session)
    reservation = await repository.get(reservation_id)
    if reservation is None:
        raise NotFoundError("Бронь не найдена")

    service = ReservationService(session)
    reservation = await service.complete(reservation)
    await session.commit()
    return await service.to_output(reservation)
