from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.table import Table
    from models.user import User


class ReservationStatus(StrEnum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    table_id: Mapped[int] = mapped_column(
        ForeignKey("tables.id", ondelete="CASCADE"),
        index=True,
    )
    guest_count: Mapped[int] = mapped_column(
        CheckConstraint("guest_count > 0", name="ck_reservation_guest_count_positive"),
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[ReservationStatus] = mapped_column(
        SqlEnum(ReservationStatus, native_enum=False, length=16),
        default=ReservationStatus.pending,
    )

    user: Mapped[User] = relationship(back_populates="reservations")
    table: Mapped[Table] = relationship(back_populates="reservations")
