"""Pydantic schemas for common areas and bookings (common-area-scheduling spec)."""

from datetime import datetime

from pydantic import BaseModel, Field


class CommonAreaCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    capacity: int | None = Field(default=None, ge=0)


class CommonAreaUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    capacity: int | None = Field(default=None, ge=0)


class CommonAreaView(BaseModel):
    id: int
    name: str
    description: str | None = None
    capacity: int | None = None


class BookingCreate(BaseModel):
    area_id: int
    start_at: datetime
    end_at: datetime
    unit_id: int | None = None
    person_id: int | None = None


class BookingView(BaseModel):
    id: int
    area_id: int
    area_name: str | None = None
    unit_id: int | None = None
    unit_code: str | None = None
    person_id: int | None = None
    person_name: str | None = None
    start_at: datetime
    end_at: datetime
    status: str
