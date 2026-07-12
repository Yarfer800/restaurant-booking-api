from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.reservation import Reservation, ReservationStatus
from models.table import Table

ACTIVE_STATUSES = (ReservationStatus.pending, ReservationStatus.confirmed)


class ReservationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, reservation_id: int) -> Reservation | None:
        return await self._session.get(Reservation, reservation_id)

    async def list_for_user(self, user_id: int) -> list[Reservation]:
        result = await self._session.scalars(
            select(Reservation).where(Reservation.user_id == user_id).order_by(Reservation.start_time.desc()),
        )
        return list(result)

    async def find_overlapping(
        self,
        table_id: int,
        start_time: datetime,
        end_time: datetime,
        *,
        for_update: bool = False,
    ) -> list[Reservation]:
        """Активные брони стола, пересекающиеся с [start_time, end_time) по времени."""
        stmt = (
            select(Reservation)
            .where(
                Reservation.table_id == table_id,
                Reservation.start_time < end_time,
                Reservation.end_time > start_time,
                Reservation.status.in_(ACTIVE_STATUSES),
            )
            .order_by(Reservation.start_time)
        )
        if for_update:
            stmt = stmt.with_for_update()
        result = await self._session.scalars(stmt)
        return list(result)

    async def create(
        self,
        user_id: int,
        table: Table,
        guest_count: int,
        start_time: datetime,
        end_time: datetime,
    ) -> Reservation:
        reservation = Reservation(
            user_id=user_id,
            table_id=table.id,
            guest_count=guest_count,
            start_time=start_time,
            end_time=end_time,
            status=ReservationStatus.pending,
        )
        self._session.add(reservation)
        await self._session.flush()
        return reservation

    async def update_status(self, reservation: Reservation, status: ReservationStatus) -> Reservation:
        reservation.status = status
        await self._session.flush()
        return reservation
