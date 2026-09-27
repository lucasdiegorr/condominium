"""Vehicles and pets with resident self-service (vehicles-pets spec).

Condômino/inquilino act on their own records (self-service); síndico and the
global administrator manage the whole condominium. All queries scoped.
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.permissions import (
    PERM_PETS_MANAGE,
    PERM_PETS_READ,
    PERM_VEHICLES_MANAGE,
    PERM_VEHICLES_READ,
)
from app.core.scope import Scope
from app.models import MemberLink, Pet, Unit, Vehicle


def _error(status_code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail=detail)


def _normalize_plate(plate: str) -> str:
    return plate.upper().strip().replace(" ", "")


def _vehicle_view(vehicle: Vehicle) -> dict:
    return {
        "id": vehicle.id,
        "plate": vehicle.plate,
        "model": vehicle.model,
        "color": vehicle.color,
        "resident_id": vehicle.resident_id,
        "resident_name": vehicle.resident.name,
        "unit_id": vehicle.unit_id,
        "unit_code": vehicle.unit.code if vehicle.unit else None,
    }


def _pet_view(pet: Pet) -> dict:
    return {
        "id": pet.id,
        "name": pet.name,
        "species": pet.species,
        "breed": pet.breed,
        "resident_id": pet.resident_id,
        "resident_name": pet.resident.name,
    }


async def _person_in_scope(session: AsyncSession, condominium_id: int, person_id: int) -> None:
    """A responsible resident must have a link in the scoped condominium."""
    link = await session.scalar(
        select(MemberLink)
        .join(Unit, Unit.id == MemberLink.unit_id)
        .where(
            MemberLink.person_id == person_id,
            Unit.condominium_id == condominium_id,
        )
    )
    if link is None:
        raise _error(
            status.HTTP_403_FORBIDDEN,
            "resident does not belong to this condominium",
        )


async def _unit_in_scope(session: AsyncSession, condominium_id: int, unit_id: int) -> None:
    unit = await session.scalar(
        select(Unit).where(Unit.id == unit_id, Unit.condominium_id == condominium_id)
    )
    if unit is None:
        raise _error(status.HTTP_403_FORBIDDEN, "unit not in this condominium")


async def _vehicle_or_403(session: AsyncSession, condominium_id: int, vehicle_id: int) -> Vehicle:
    vehicle = await session.scalar(
        select(Vehicle)
        .where(Vehicle.id == vehicle_id, Vehicle.condominium_id == condominium_id)
        .options(selectinload(Vehicle.resident), selectinload(Vehicle.unit))
    )
    if vehicle is None:
        raise _error(status.HTTP_403_FORBIDDEN, "vehicle not in this condominium")
    return vehicle


async def _pet_or_403(session: AsyncSession, condominium_id: int, pet_id: int) -> Pet:
    pet = await session.scalar(
        select(Pet)
        .where(Pet.id == pet_id, Pet.condominium_id == condominium_id)
        .options(selectinload(Pet.resident))
    )
    if pet is None:
        raise _error(status.HTTP_403_FORBIDDEN, "pet not in this condominium")
    return pet


def _manage_whole_scope(scope: Scope, permission: str) -> bool:
    return scope.has_permission(permission)


# --- Vehicles ---


async def list_vehicles(session: AsyncSession, scope: Scope) -> list[dict]:
    query = (
        select(Vehicle)
        .options(selectinload(Vehicle.resident), selectinload(Vehicle.unit))
        .where(Vehicle.condominium_id == scope.condominium_id)
    )
    if not _manage_whole_scope(scope, PERM_VEHICLES_MANAGE) and not scope.has_permission(
        PERM_VEHICLES_READ
    ):
        query = query.where(Vehicle.resident_id == scope.person_id)
    vehicles = (await session.scalars(query.order_by(Vehicle.plate))).all()
    return [_vehicle_view(vehicle) for vehicle in vehicles]


async def get_vehicle(session: AsyncSession, scope: Scope, vehicle_id: int) -> dict:
    vehicle = await _vehicle_or_403(session, scope.condominium_id, vehicle_id)
    if not _manage_whole_scope(scope, PERM_VEHICLES_MANAGE):
        if not scope.has_permission(PERM_VEHICLES_READ) and vehicle.resident_id != scope.person_id:
            raise _error(status.HTTP_403_FORBIDDEN, "not your vehicle")
    return _vehicle_view(vehicle)


async def create_vehicle(
    session: AsyncSession,
    scope: Scope,
    *,
    plate: str,
    model: str,
    color: str | None,
    resident_id: int,
    unit_id: int,
) -> dict:
    plate = _normalize_plate(plate)
    existing = await session.scalar(
        select(Vehicle).where(
            Vehicle.condominium_id == scope.condominium_id,
            Vehicle.plate == plate,
        )
    )
    if existing is not None:
        raise _error(status.HTTP_409_CONFLICT, "plate already registered")

    await _person_in_scope(session, scope.condominium_id, resident_id)
    await _unit_in_scope(session, scope.condominium_id, unit_id)

    vehicle = Vehicle(
        condominium_id=scope.condominium_id,
        plate=plate,
        model=model,
        color=color,
        resident_id=resident_id,
        unit_id=unit_id,
    )
    session.add(vehicle)
    await session.commit()
    return _vehicle_view(await _vehicle_or_403(session, scope.condominium_id, vehicle.id))


async def update_vehicle(
    session: AsyncSession,
    scope: Scope,
    vehicle_id: int,
    *,
    model: str | None,
    color: str | None,
) -> dict:
    vehicle = await _vehicle_or_403(session, scope.condominium_id, vehicle_id)
    if (
        not _manage_whole_scope(scope, PERM_VEHICLES_MANAGE)
        and vehicle.resident_id != scope.person_id
    ):
        raise _error(status.HTTP_403_FORBIDDEN, "not your vehicle")
    if model is not None:
        vehicle.model = model
    if color is not None:
        vehicle.color = color
    await session.commit()
    return _vehicle_view(vehicle)


async def delete_vehicle(session: AsyncSession, scope: Scope, vehicle_id: int) -> None:
    vehicle = await _vehicle_or_403(session, scope.condominium_id, vehicle_id)
    if (
        not _manage_whole_scope(scope, PERM_VEHICLES_MANAGE)
        and vehicle.resident_id != scope.person_id
    ):
        raise _error(status.HTTP_403_FORBIDDEN, "not your vehicle")
    await session.delete(vehicle)
    await session.commit()


# --- Pets ---


async def list_pets(session: AsyncSession, scope: Scope) -> list[dict]:
    query = (
        select(Pet)
        .options(selectinload(Pet.resident))
        .where(Pet.condominium_id == scope.condominium_id)
    )
    if not _manage_whole_scope(scope, PERM_PETS_MANAGE) and not scope.has_permission(
        PERM_PETS_READ
    ):
        query = query.where(Pet.resident_id == scope.person_id)
    pets = (await session.scalars(query.order_by(Pet.name))).all()
    return [_pet_view(pet) for pet in pets]


async def get_pet(session: AsyncSession, scope: Scope, pet_id: int) -> dict:
    pet = await _pet_or_403(session, scope.condominium_id, pet_id)
    if not _manage_whole_scope(scope, PERM_PETS_MANAGE):
        if not scope.has_permission(PERM_PETS_READ) and pet.resident_id != scope.person_id:
            raise _error(status.HTTP_403_FORBIDDEN, "not your pet")
    return _pet_view(pet)


async def create_pet(
    session: AsyncSession,
    scope: Scope,
    *,
    name: str,
    species: str,
    breed: str | None,
    resident_id: int,
) -> dict:
    await _person_in_scope(session, scope.condominium_id, resident_id)
    pet = Pet(
        condominium_id=scope.condominium_id,
        name=name,
        species=species,
        breed=breed,
        resident_id=resident_id,
    )
    session.add(pet)
    await session.commit()
    return _pet_view(await _pet_or_403(session, scope.condominium_id, pet.id))


async def update_pet(
    session: AsyncSession,
    scope: Scope,
    pet_id: int,
    *,
    name: str | None,
    species: str | None,
    breed: str | None,
) -> dict:
    pet = await _pet_or_403(session, scope.condominium_id, pet_id)
    if not _manage_whole_scope(scope, PERM_PETS_MANAGE) and pet.resident_id != scope.person_id:
        raise _error(status.HTTP_403_FORBIDDEN, "not your pet")
    if name is not None:
        pet.name = name
    if species is not None:
        pet.species = species
    if breed is not None:
        pet.breed = breed
    await session.commit()
    return _pet_view(pet)


async def delete_pet(session: AsyncSession, scope: Scope, pet_id: int) -> None:
    pet = await _pet_or_403(session, scope.condominium_id, pet_id)
    if not _manage_whole_scope(scope, PERM_PETS_MANAGE) and pet.resident_id != scope.person_id:
        raise _error(status.HTTP_403_FORBIDDEN, "not your pet")
    await session.delete(pet)
    await session.commit()
