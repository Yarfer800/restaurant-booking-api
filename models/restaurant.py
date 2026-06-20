from __future__ import annotations

from datetime import time
from typing import TYPE_CHECKING

from sqlalchemy import String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.table import Table


class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    address: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(32))
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    opening_time: Mapped[time] = mapped_column(Time)
    closing_time: Mapped[time] = mapped_column(Time)

    tables: Mapped[list[Table]] = relationship(
        back_populates="restaurant",
        cascade="all, delete-orphan",
    )
