"""Pydantic schemas for units and parking spots (unit-management spec)."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

UnitType = Literal["apartment", "commercial", "other"]
SpotType = Literal["covered", "uncovered"]


class UnitCreate(BaseModel):
    number: str = Field(min_length=1, max_length=50)
    block: str | None = Field(default=None, max_length=50)
    unit_type: UnitType = "apartment"
    fraction: Decimal = Field(gt=0, le=Decimal("100"))


class UnitUpdate(BaseModel):
    number: str | None = Field(default=None, min_length=1, max_length=50)
    block: str | None = Field(default=None, max_length=50)
    unit_type: UnitType | None = None
    fraction: Decimal | None = Field(default=None, gt=0, le=Decimal("100"))
    active: bool | None = None


class ParkingSpotView(BaseModel):
    id: int
    identifier: str
    spot_type: str
    unit_id: int | None = None


class UnitView(BaseModel):
    id: int
    code: str
    number: str
    block: str | None = None
    unit_type: str
    fraction: str
    active: bool
    parking_spots: list[ParkingSpotView] = Field(default_factory=list)


class ParkingSpotCreate(BaseModel):
    identifier: str = Field(min_length=1, max_length=50)
    spot_type: SpotType = "uncovered"
