"""Common-area routes (common-area-scheduling spec). Management by síndico/admin."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.core.permissions import PERM_COMMON_AREAS_MANAGE, PERM_COMMON_AREAS_READ
from app.db import get_db
from app.schemas.bookings import CommonAreaCreate, CommonAreaUpdate, CommonAreaView
from app.services import bookings_service

router = APIRouter(prefix="/common-areas", tags=["common-areas"])


@router.get("", response_model=list[CommonAreaView])
async def list_common_areas(
    scope=Depends(require_permission(PERM_COMMON_AREAS_READ)),
    session: AsyncSession = Depends(get_db),
) -> list[CommonAreaView]:
    return await bookings_service.list_common_areas(session, scope)


@router.post("", response_model=CommonAreaView, status_code=201)
async def create_common_area(
    body: CommonAreaCreate,
    scope=Depends(require_permission(PERM_COMMON_AREAS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> CommonAreaView:
    return await bookings_service.create_common_area(
        session,
        scope,
        name=body.name,
        description=body.description,
        capacity=body.capacity,
    )


@router.patch("/{area_id}", response_model=CommonAreaView)
async def update_common_area(
    area_id: int,
    body: CommonAreaUpdate,
    scope=Depends(require_permission(PERM_COMMON_AREAS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> CommonAreaView:
    return await bookings_service.update_common_area(
        session,
        scope,
        area_id,
        name=body.name,
        description=body.description,
        capacity=body.capacity,
    )


@router.delete("/{area_id}", status_code=204)
async def delete_common_area(
    area_id: int,
    scope=Depends(require_permission(PERM_COMMON_AREAS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> None:
    await bookings_service.delete_common_area(session, scope, area_id)
    return None
