from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_admin, get_session
from core.exceptions import NotFoundError
from repositories.restaurant import RestaurantRepository
from schemas.table import TableCreate, TableOut, TableUpdate

router = APIRouter(tags=["tables"])


@router.post(
    "/restaurants/{restaurant_id}/tables",
    response_model=TableOut,
    status_code=201,
    summary="Добавить стол (admin)",
)
async def create_table(
    restaurant_id: int,
    data: TableCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _admin: Annotated[bool, Depends(get_current_admin)],
) -> TableOut:
    repository = RestaurantRepository(session)
    restaurant = await repository.get(restaurant_id)
    if restaurant is None:
        raise NotFoundError("Ресторан не найден")

    table = await repository.add_table(restaurant_id, data.number, data.capacity)
    await session.commit()
    await session.refresh(table)
    return TableOut.model_validate(table)


@router.get("/tables/{table_id}", response_model=TableOut, summary="Стол по id")
async def get_table(
    table_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TableOut:
    repository = RestaurantRepository(session)
    table = await repository.get_table(table_id)
    if table is None:
        raise NotFoundError("Стол не найден")
    return TableOut.model_validate(table)


@router.put("/tables/{table_id}", response_model=TableOut, summary="Обновить стол (admin)")
async def update_table(
    table_id: int,
    data: TableUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _admin: Annotated[bool, Depends(get_current_admin)],
) -> TableOut:
    repository = RestaurantRepository(session)
    table = await repository.get_table(table_id)
    if table is None:
        raise NotFoundError("Стол не найден")

    table = await repository.update_table(table, data.model_dump(exclude_unset=True))
    await session.commit()
    await session.refresh(table)
    return TableOut.model_validate(table)


@router.delete("/tables/{table_id}", status_code=204, summary="Удалить стол (admin)")
async def delete_table(
    table_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    _admin: Annotated[bool, Depends(get_current_admin)],
) -> None:
    repository = RestaurantRepository(session)
    table = await repository.get_table(table_id)
    if table is None:
        raise NotFoundError("Стол не найден")

    await repository.delete_table(table)
    await session.commit()