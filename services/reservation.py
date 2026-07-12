from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ConflictError, NotFoundError, ValidationError
from models.reservation import Reservation, ReservationStatus
from models.restaurant import Restaurant
from models.table import Table
from models.user import User
from repositories.reservation import ReservationRepository
from schemas.reservation import ReservationCreate, ReservationOut


class ReservationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = ReservationRepository(session)

    async def create(self, user: User, data: ReservationCreate) -> Reservation:
        table = await self._session.get(Table, data.table_id)
        if table is None:
            raise NotFoundError("Стол не найден")

        if data.guest_count > table.capacity:
            raise ValidationError("Количество гостей превышает вместимость стола")

        if data.start_time >= data.end_time:
            raise ValidationError("Время начала должно быть раньше времени окончания")

        restaurant = await self._session.get(Restaurant, table.restaurant_id)
        if restaurant is None:
            raise NotFoundError("Ресторан не найден")

        if not self._within_working_hours(restaurant, data.start_time, data.end_time):
            raise ValidationError(
                "Бронь должна полностью укладываться в рабочие часы заведения "
                f"({restaurant.opening_time}–{restaurant.closing_time})",
            )

        overlaps = await self._repository.find_overlapping(
            table.id,
            data.start_time,
            data.end_time,
            for_update=True,
        )
        if overlaps:
            raise ConflictError("Стол уже занят в выбранное время")

        return await self._repository.create(
            user_id=user.id,
            table=table,
            guest_count=data.guest_count,
            start_time=data.start_time,
            end_time=data.end_time,
        )

    async def available_tables(
        self,
        restaurant_id: int,
        start_time: datetime,
        end_time: datetime,
        guests: int,
    ) -> list[Table]:
        """Столы с достаточной вместимостью, не пересекающиеся по времени с активными бронями."""
        if start_time >= end_time:
            raise ValidationError("Время начала должно быть раньше времени окончания")

        candidates = await self._session.scalars(
            select(Table).where(
                Table.restaurant_id == restaurant_id,
                Table.capacity >= guests,
            ),
        )
        candidates = list(candidates)

        busy = await self._session.scalars(
            select(Reservation.table_id).where(
                Reservation.table_id.in_([t.id for t in candidates]),
                Reservation.start_time < end_time,
                Reservation.end_time > start_time,
                Reservation.status.in_(
                    (ReservationStatus.pending, ReservationStatus.confirmed),
                ),
            ),
        )
        busy_ids = set(busy)
        return [t for t in candidates if t.id not in busy_ids]

    async def cancel(self, reservation: Reservation) -> Reservation:
        if reservation.status not in (ReservationStatus.pending, ReservationStatus.confirmed):
            raise ValidationError(
                f"Бронь в статусе {reservation.status.value} нельзя отменить",
            )
        return await self._repository.update_status(reservation, ReservationStatus.cancelled)

    async def confirm(self, reservation: Reservation) -> Reservation:
        if reservation.status != ReservationStatus.pending:
            raise ValidationError("Подтвердить можно только бронь в статусе pending")
        return await self._repository.update_status(reservation, ReservationStatus.confirmed)

    async def complete(self, reservation: Reservation) -> Reservation:
        if reservation.status != ReservationStatus.confirmed:
            raise ValidationError("Завершить можно только подтверждённую бронь")
        return await self._repository.update_status(reservation, ReservationStatus.completed)

    async def to_output(self, reservation: Reservation) -> ReservationOut:
        table = await self._session.get(Table, reservation.table_id)
        restaurant = None
        if table is not None:
            restaurant = await self._session.get(Restaurant, table.restaurant_id)
        return ReservationOut(
            id=reservation.id,
            user_id=reservation.user_id,
            table_id=reservation.table_id,
            guest_count=reservation.guest_count,
            start_time=reservation.start_time,
            end_time=reservation.end_time,
            status=reservation.status.value,
            table_number=table.number if table is not None else None,
            restaurant_name=restaurant.name if restaurant is not None else None,
        )

    @staticmethod
    def _within_working_hours(
        restaurant: Restaurant,
        start_time: datetime,
        end_time: datetime,
    ) -> bool:
        return (
            restaurant.opening_time <= start_time.time() <= restaurant.closing_time
            and restaurant.opening_time <= end_time.time() <= restaurant.closing_time
        )
