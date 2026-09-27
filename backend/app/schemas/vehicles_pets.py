"""Pydantic schemas for vehicles and pets (vehicles-pets spec)."""

from pydantic import BaseModel, Field


class VehicleCreate(BaseModel):
    plate: str = Field(min_length=7, max_length=10)
    model: str = Field(min_length=1, max_length=120)
    color: str | None = Field(default=None, max_length=50)
    resident_id: int | None = None
    unit_id: int | None = None


class VehicleUpdate(BaseModel):
    model: str | None = Field(default=None, min_length=1, max_length=120)
    color: str | None = Field(default=None, max_length=50)


class VehicleView(BaseModel):
    id: int
    plate: str
    model: str
    color: str | None = None
    resident_id: int
    resident_name: str
    unit_id: int
    unit_code: str | None = None


class PetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    species: str = Field(min_length=1, max_length=50)
    breed: str | None = Field(default=None, max_length=100)
    resident_id: int | None = None


class PetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    species: str | None = Field(default=None, min_length=1, max_length=50)
    breed: str | None = Field(default=None, max_length=100)


class PetView(BaseModel):
    id: int
    name: str
    species: str
    breed: str | None = None
    resident_id: int
    resident_name: str
