from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.restaurant import Restaurant
from models.table import Table
from schemas.restaurant import RestaurantCreate


class RestaurantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_with_pagination(self, offset: int, limit: int) -> tuple[list[Restaurant], int]:
        total = await self._session.scalar(select(func.count(Restaurant.id)))
        result = await self._session.scalars(
            select(Restaurant).order_by(Restaurant.id).offset(offset).limit(limit),
        )
        return list(result), total or 0

    async def get(self, restaurant_id: int) -> Restaurant | None:
        return await self._session.get(Restaurant, restaurant_id)

    async def get_with_tables(self, restaurant_id: int) -> Restaurant | None:
        stmt = select(Restaurant).options(selectinload(Restaurant.tables)).where(Restaurant.id == restaurant_id)
        return await self._session.scalar(stmt)

    async def get_table(self, table_id: int) -> Table | None:
        return await self._session.get(Table, table_id)

    async def create(self, data: RestaurantCreate) -> Restaurant:
        restaurant = Restaurant(**data.model_dump())
        self._session.add(restaurant)
        await self._session.flush()
        return restaurant

    async def update(self, restaurant: Restaurant, data: dict[str, Any]) -> Restaurant:
        for field, value in data.items():
            setattr(restaurant, field, value)
        await self._session.flush()
        return restaurant

    async def delete(self, restaurant: Restaurant) -> None:
        await self._session.delete(restaurant)
        await self._session.flush()

    async def add_table(self, restaurant_id: int, number: str, capacity: int) -> Table:
        table = Table(restaurant_id=restaurant_id, number=number, capacity=capacity)
        self._session.add(table)
        await self._session.flush()
        return table

    async def update_table(self, table: Table, data: dict[str, Any]) -> Table:
        for field, value in data.items():
            setattr(table, field, value)
        await self._session.flush()
        return table

    async def delete_table(self, table: Table) -> None:
        await self._session.delete(table)
        await self._session.flush()
