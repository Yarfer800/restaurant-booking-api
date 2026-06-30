from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReservationCreate(BaseModel):
    table_id: int
    guest_count: int = Field(ge=1, le=100)
    start_time: datetime
    end_time: datetime


class ReservationOut(BaseModel):
    id: int
    user_id: int
    table_id: int
    guest_count: int
    start_time: datetime
    end_time: datetime
    status: str
    table_number: str | None = None
    restaurant_name: str | None = None

    model_config = ConfigDict(from_attributes=True)
