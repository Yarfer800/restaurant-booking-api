from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.reservation import Reservation
    from models.restaurant import Restaurant


class Table(Base):
    __tablename__ = "tables"
    __table_args__ = (UniqueConstraint("restaurant_id", "number", name="uq_table_restaurant_number"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        index=True,
    )
    number: Mapped[str] = mapped_column(String(32))
    capacity: Mapped[int] = mapped_column(Integer)

    restaurant: Mapped[Restaurant] = relationship(back_populates="tables")
    reservations: Mapped[list[Reservation]] = relationship(back_populates="table")
