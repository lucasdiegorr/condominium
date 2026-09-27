"""Unit and parking-spot routes (unit-management spec). All scoped."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.core.permissions import PERM_UNITS_MANAGE, PERM_UNITS_READ
from app.db import get_db
from app.schemas.units import (
    ParkingSpotCreate,
    ParkingSpotView,
    UnitCreate,
    UnitUpdate,
    UnitView,
)
from app.services import units_service

router = APIRouter(prefix="/units", tags=["units"])


@router.get("", response_model=list[UnitView])
async def list_units(
    scope=Depends(require_permission(PERM_UNITS_READ)),
    session: AsyncSession = Depends(get_db),
) -> list[UnitView]:
    return await units_service.list_units(session, scope.condominium_id)


@router.get("/parking", response_model=list[ParkingSpotView])
async def list_parking_spots(
    unit_id: int | None = Query(default=None),
    scope=Depends(require_permission(PERM_UNITS_READ)),
    session: AsyncSession = Depends(get_db),
) -> list[ParkingSpotView]:
    return await units_service.list_parking_spots(session, scope.condominium_id, unit_id=unit_id)


@router.post("", response_model=UnitView, status_code=201)
async def create_unit(
    body: UnitCreate,
    scope=Depends(require_permission(PERM_UNITS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> UnitView:
    return await units_service.create_unit(
        session,
        scope.condominium_id,
        number=body.number,
        block=body.block,
        unit_type=body.unit_type,
        fraction=body.fraction,
    )


@router.post("/{unit_id}/parking", response_model=ParkingSpotView, status_code=201)
async def create_parking_spot(
    unit_id: int,
    body: ParkingSpotCreate,
    scope=Depends(require_permission(PERM_UNITS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> ParkingSpotView:
    return await units_service.create_parking_spot(
        session,
        scope.condominium_id,
        unit_id=unit_id,
        identifier=body.identifier,
        spot_type=body.spot_type,
    )


@router.get("/{unit_id}", response_model=UnitView)
async def get_unit(
    unit_id: int,
    scope=Depends(require_permission(PERM_UNITS_READ)),
    session: AsyncSession = Depends(get_db),
) -> UnitView:
    unit = await units_service.get_unit_detail(session, scope.condominium_id, unit_id)
    return unit


@router.patch("/{unit_id}", response_model=UnitView)
async def update_unit(
    unit_id: int,
    body: UnitUpdate,
    scope=Depends(require_permission(PERM_UNITS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> UnitView:
    return await units_service.update_unit(
        session,
        scope.condominium_id,
        unit_id,
        number=body.number,
        block=body.block,
        unit_type=body.unit_type,
        fraction=body.fraction,
        active=body.active,
    )


@router.delete("/{unit_id}", status_code=204)
async def delete_unit(
    unit_id: int,
    scope=Depends(require_permission(PERM_UNITS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> None:
    await units_service.delete_unit(session, scope.condominium_id, unit_id)
    return None


@router.delete("/parking/{spot_id}", status_code=204)
async def delete_parking_spot(
    spot_id: int,
    scope=Depends(require_permission(PERM_UNITS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> None:
    await units_service.delete_parking_spot(session, scope.condominium_id, spot_id)
    return None
