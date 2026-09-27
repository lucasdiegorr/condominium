"""Vehicle routes with resident self-service (vehicles-pets spec)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_any_permission
from app.core.permissions import PERM_VEHICLES_MANAGE, PERM_VEHICLES_READ, PERM_VEHICLES_SELF
from app.db import get_db
from app.schemas.vehicles_pets import VehicleCreate, VehicleUpdate, VehicleView
from app.services import vehicles_pets_service

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


def _resolve_vehicle_target(scope, body: VehicleCreate) -> tuple[int, int]:
    """Return (resident_id, unit_id) honoring manage vs self-service."""
    if scope.has_permission(PERM_VEHICLES_MANAGE):
        if body.resident_id is None or body.unit_id is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "resident_id and unit_id are required",
            )
        return body.resident_id, body.unit_id
    # Self-service: own person on a unit they are linked to.
    if body.unit_id is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "unit_id is required")
    if not scope.has_unit_link(body.unit_id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "you are not linked to this unit",
        )
    return scope.person_id, body.unit_id


@router.get("", response_model=list[VehicleView])
async def list_vehicles(
    scope=Depends(require_any_permission(PERM_VEHICLES_READ, PERM_VEHICLES_SELF)),
    session: AsyncSession = Depends(get_db),
) -> list[VehicleView]:
    return await vehicles_pets_service.list_vehicles(session, scope)


@router.post("", response_model=VehicleView, status_code=201)
async def create_vehicle(
    body: VehicleCreate,
    scope=Depends(require_any_permission(PERM_VEHICLES_MANAGE, PERM_VEHICLES_SELF)),
    session: AsyncSession = Depends(get_db),
) -> VehicleView:
    resident_id, unit_id = _resolve_vehicle_target(scope, body)
    return await vehicles_pets_service.create_vehicle(
        session,
        scope,
        plate=body.plate,
        model=body.model,
        color=body.color,
        resident_id=resident_id,
        unit_id=unit_id,
    )


@router.get("/{vehicle_id}", response_model=VehicleView)
async def get_vehicle(
    vehicle_id: int,
    scope=Depends(require_any_permission(PERM_VEHICLES_READ, PERM_VEHICLES_SELF)),
    session: AsyncSession = Depends(get_db),
) -> VehicleView:
    return await vehicles_pets_service.get_vehicle(session, scope, vehicle_id)


@router.patch("/{vehicle_id}", response_model=VehicleView)
async def update_vehicle(
    vehicle_id: int,
    body: VehicleUpdate,
    scope=Depends(require_any_permission(PERM_VEHICLES_MANAGE, PERM_VEHICLES_SELF)),
    session: AsyncSession = Depends(get_db),
) -> VehicleView:
    return await vehicles_pets_service.update_vehicle(
        session, scope, vehicle_id, model=body.model, color=body.color
    )


@router.delete("/{vehicle_id}", status_code=204)
async def delete_vehicle(
    vehicle_id: int,
    scope=Depends(require_any_permission(PERM_VEHICLES_MANAGE, PERM_VEHICLES_SELF)),
    session: AsyncSession = Depends(get_db),
) -> None:
    await vehicles_pets_service.delete_vehicle(session, scope, vehicle_id)
    return None
