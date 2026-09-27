"""Booking routes (common-area-scheduling spec). No payment, no approval flow."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_any_permission
from app.core.permissions import PERM_BOOKINGS_MANAGE, PERM_BOOKINGS_READ, PERM_BOOKINGS_SELF
from app.db import get_db
from app.schemas.bookings import BookingCreate, BookingView
from app.services import bookings_service

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.get("", response_model=list[BookingView])
async def list_bookings(
    scope=Depends(require_any_permission(PERM_BOOKINGS_READ, PERM_BOOKINGS_SELF)),
    session: AsyncSession = Depends(get_db),
) -> list[BookingView]:
    return await bookings_service.list_bookings(session, scope)


@router.post("", response_model=BookingView, status_code=201)
async def create_booking(
    body: BookingCreate,
    scope=Depends(require_any_permission(PERM_BOOKINGS_MANAGE, PERM_BOOKINGS_SELF)),
    session: AsyncSession = Depends(get_db),
) -> BookingView:
    return await bookings_service.create_booking(
        session,
        scope,
        area_id=body.area_id,
        start_at=body.start_at,
        end_at=body.end_at,
        unit_id=body.unit_id,
        person_id=body.person_id,
    )


@router.post("/{booking_id}/cancel", response_model=BookingView)
async def cancel_booking(
    booking_id: int,
    scope=Depends(require_any_permission(PERM_BOOKINGS_MANAGE, PERM_BOOKINGS_SELF)),
    session: AsyncSession = Depends(get_db),
) -> BookingView:
    return await bookings_service.cancel_booking(session, scope, booking_id)
