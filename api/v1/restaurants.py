import json
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_admin, get_session
from core.exceptions import NotFoundError, ValidationError
from core.redis import get_redis
from repositories.restaurant import RestaurantRepository
from schemas.restaurant import (
    RestaurantCreate,
    RestaurantDetail,
    RestaurantList,
    RestaurantOut,
    RestaurantUpdate,
)
from schemas.table import TableOut
from services.reservation import ReservationService

router = APIRouter(prefix="/restaurants", tags=["restaurants"])


@router.get("", response_model=RestaurantList, summary="Список ресторанов (пагинация)")
async def list_restaurants(
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RestaurantList:
    repository = RestaurantRepository(session)
    items, total = await repository.list_with_pagination(offset=offset, limit=limit)
    return RestaurantList(items=items, total=total, limit=limit, offset=offset)


@router.get("/{restaurant_id}", response_model=RestaurantDetail, summary="Ресторан со столами")
async def get_restaurant(
    restaurant_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RestaurantDetail:
    repository = RestaurantRepository(session)
    restaurant = await repository.get_with_tables(restaurant_id)
    if restaurant is None:
        raise NotFoundError("Ресторан не найден")
    return RestaurantDetail.model_validate(restaurant)


@router.post("", response_model=RestaurantOut, status_code=201, summary="Создать ресторан (admin)")
async def create_restaurant(
    data: RestaurantCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _admin: Annotated[bool, Depends(get_current_admin)],
) -> RestaurantOut:
    repository = RestaurantRepository(session)
    restaurant = await repository.create(data)
    await session.commit()
    await session.refresh(restaurant)
    return RestaurantOut.model_validate(restaurant)


@router.patch("/{restaurant_id}", response_model=RestaurantOut, summary="Обновить ресторан (admin)")
async def update_restaurant(
    restaurant_id: int,
    data: RestaurantUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _admin: Annotated[bool, Depends(get_current_admin)],
) -> RestaurantOut:
    repository = RestaurantRepository(session)
    restaurant = await repository.get(restaurant_id)
    if restaurant is None:
        raise NotFoundError("Ресторан не найден")

    updates = data.model_dump(exclude_unset=True)
    opening = updates.get("opening_time")
    closing = updates.get("closing_time")
    if opening is not None and closing is not None and opening >= closing:
        raise ValidationError("Время открытия должно быть раньше времени закрытия")

    restaurant = await repository.update(restaurant, updates)
    await session.commit()
    await session.refresh(restaurant)
    return RestaurantOut.model_validate(restaurant)


@router.delete("/{restaurant_id}", status_code=204, summary="Удалить ресторан (admin)")
async def delete_restaurant(
    restaurant_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    _admin: Annotated[bool, Depends(get_current_admin)],
) -> None:
    repository = RestaurantRepository(session)
    restaurant = await repository.get(restaurant_id)
    if restaurant is None:
        raise NotFoundError("Ресторан не найден")
    await repository.delete(restaurant)
    await session.commit()


@router.get("/{restaurant_id}/tables/available", response_model=list[TableOut], summary="Свободные столы на время")
async def available_tables(
    restaurant_id: int,
    start: datetime,
    end: datetime,
    guests: Annotated[int, Query(ge=1)],
    session: Annotated[AsyncSession, Depends(get_session)],
    redis: Annotated[Redis | None, Depends(get_redis)],
) -> list[TableOut]:
    repository = RestaurantRepository(session)
    restaurant = await repository.get(restaurant_id)
    if restaurant is None:
        raise NotFoundError("Ресторан не найден")

    if start >= end:
        raise ValidationError("Время начала должно быть раньше времени окончания")

    cache_key = f"available:{restaurant_id}:{start.isoformat()}:{end.isoformat()}:{guests}"
    if redis is not None:
        cached = await redis.get(cache_key)
        if cached is not None:
            return [TableOut.model_validate(item) for item in json.loads(cached)]

    service = ReservationService(session)
    tables = await service.available_tables(restaurant_id, start, end, guests)
    result = [TableOut.model_validate(t) for t in tables]

    if redis is not None:
        payload = json.dumps([t.model_dump(mode="json") for t in result])
        await redis.set(cache_key, payload, ex=60)

    return result
