from pydantic import BaseModel, ConfigDict, Field


class TableCreate(BaseModel):
    number: str = Field(min_length=1, max_length=32)
    capacity: int = Field(ge=1, le=100)


class TableUpdate(BaseModel):
    number: str | None = Field(default=None, min_length=1, max_length=32)
    capacity: int | None = Field(default=None, ge=1, le=100)


class TableOut(BaseModel):
    id: int
    restaurant_id: int
    number: str
    capacity: int

    model_config = ConfigDict(from_attributes=True)
