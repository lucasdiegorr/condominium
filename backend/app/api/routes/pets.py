"""Pet routes with resident self-service (vehicles-pets spec)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_any_permission
from app.core.permissions import PERM_PETS_MANAGE, PERM_PETS_READ, PERM_PETS_SELF
from app.db import get_db
from app.schemas.vehicles_pets import PetCreate, PetUpdate, PetView
from app.services import vehicles_pets_service

router = APIRouter(prefix="/pets", tags=["pets"])


def _resolve_pet_resident(scope, body: PetCreate) -> int:
    if scope.has_permission(PERM_PETS_MANAGE):
        if body.resident_id is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "resident_id is required")
        return body.resident_id
    return scope.person_id  # self-service


@router.get("", response_model=list[PetView])
async def list_pets(
    scope=Depends(require_any_permission(PERM_PETS_READ, PERM_PETS_SELF)),
    session: AsyncSession = Depends(get_db),
) -> list[PetView]:
    return await vehicles_pets_service.list_pets(session, scope)


@router.post("", response_model=PetView, status_code=201)
async def create_pet(
    body: PetCreate,
    scope=Depends(require_any_permission(PERM_PETS_MANAGE, PERM_PETS_SELF)),
    session: AsyncSession = Depends(get_db),
) -> PetView:
    resident_id = _resolve_pet_resident(scope, body)
    return await vehicles_pets_service.create_pet(
        session,
        scope,
        name=body.name,
        species=body.species,
        breed=body.breed,
        resident_id=resident_id,
    )


@router.get("/{pet_id}", response_model=PetView)
async def get_pet(
    pet_id: int,
    scope=Depends(require_any_permission(PERM_PETS_READ, PERM_PETS_SELF)),
    session: AsyncSession = Depends(get_db),
) -> PetView:
    return await vehicles_pets_service.get_pet(session, scope, pet_id)


@router.patch("/{pet_id}", response_model=PetView)
async def update_pet(
    pet_id: int,
    body: PetUpdate,
    scope=Depends(require_any_permission(PERM_PETS_MANAGE, PERM_PETS_SELF)),
    session: AsyncSession = Depends(get_db),
) -> PetView:
    return await vehicles_pets_service.update_pet(
        session, scope, pet_id, name=body.name, species=body.species, breed=body.breed
    )


@router.delete("/{pet_id}", status_code=204)
async def delete_pet(
    pet_id: int,
    scope=Depends(require_any_permission(PERM_PETS_MANAGE, PERM_PETS_SELF)),
    session: AsyncSession = Depends(get_db),
) -> None:
    await vehicles_pets_service.delete_pet(session, scope, pet_id)
    return None
