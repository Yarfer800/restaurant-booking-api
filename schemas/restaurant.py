from datetime import time

from pydantic import BaseModel, ConfigDict, Field

from schemas.table import TableOut


class RestaurantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address: str = Field(min_length=1, max_length=255)
    phone: str = Field(min_length=3, max_length=32)
    description: str | None = None
    opening_time: time
    closing_time: time


class RestaurantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, min_length=3, max_length=32)
    description: str | None = None
    opening_time: time | None = None
    closing_time: time | None = None


class RestaurantOut(BaseModel):
    id: int
    name: str
    address: str
    phone: str
    description: str | None = None
    opening_time: time
    closing_time: time

    model_config = ConfigDict(from_attributes=True)


class RestaurantList(BaseModel):
    items: list[RestaurantOut]
    total: int
    limit: int
    offset: int


class RestaurantDetail(RestaurantOut):
    tables: list[TableOut] = []
