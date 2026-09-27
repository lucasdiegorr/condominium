"""Common areas and bookings within a condominium scope (common-area-scheduling).

Bookings are simple: no payment, no approval flow. Overlap is rejected atomically
by the PostgreSQL exclusion constraint (reserved bookings only); cancellations
free the time slot. Residents book for themselves; síndico/administrator book
and cancel for the whole condominium.
"""

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.permissions import (
    PERM_BOOKINGS_MANAGE,
    PERM_BOOKINGS_READ,
)
from app.core.scope import Scope
from app.models import Booking, CommonArea, MemberLink, Unit


def _error(status_code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail=detail)


def _area_view(area: CommonArea) -> dict:
    return {
        "id": area.id,
        "name": area.name,
        "description": area.description,
        "capacity": area.capacity,
    }


def _booking_view(booking: Booking) -> dict:
    return {
        "id": booking.id,
        "area_id": booking.area_id,
        "area_name": booking.area.name if booking.area else None,
        "unit_id": booking.unit_id,
        "unit_code": booking.unit.code if booking.unit else None,
        "person_id": booking.person_id,
        "person_name": booking.person.name if booking.person else None,
        "start_at": booking.start_at,
        "end_at": booking.end_at,
        "status": booking.status,
    }


# --- Common areas ---


async def list_common_areas(session: AsyncSession, scope: Scope) -> list[dict]:
    areas = (
        await session.scalars(
            select(CommonArea)
            .where(CommonArea.condominium_id == scope.condominium_id)
            .order_by(CommonArea.name)
        )
    ).all()
    return [_area_view(area) for area in areas]


async def get_area_in_scope(session: AsyncSession, scope: Scope, area_id: int) -> CommonArea:
    area = await session.scalar(
        select(CommonArea).where(
            CommonArea.id == area_id,
            CommonArea.condominium_id == scope.condominium_id,
        )
    )
    if area is None:
        raise _error(status.HTTP_403_FORBIDDEN, "common area not in this condominium")
    return area


async def create_common_area(
    session: AsyncSession,
    scope: Scope,
    *,
    name: str,
    description: str | None,
    capacity: int | None,
) -> dict:
    area = CommonArea(
        condominium_id=scope.condominium_id,
        name=name,
        description=description,
        capacity=capacity,
    )
    session.add(area)
    await session.commit()
    await session.refresh(area)
    return _area_view(area)


async def update_common_area(
    session: AsyncSession,
    scope: Scope,
    area_id: int,
    *,
    name: str | None,
    description: str | None,
    capacity: int | None,
) -> dict:
    area = await get_area_in_scope(session, scope, area_id)
    if name is not None:
        area.name = name
    if description is not None:
        area.description = description
    if capacity is not None:
        area.capacity = capacity
    await session.commit()
    await session.refresh(area)
    return _area_view(area)


async def delete_common_area(session: AsyncSession, scope: Scope, area_id: int) -> None:
    area = await get_area_in_scope(session, scope, area_id)
    await session.delete(area)
    await session.commit()


# --- Bookings ---


async def _booking_or_403(session: AsyncSession, scope: Scope, booking_id: int) -> Booking:
    booking = await session.scalar(
        select(Booking)
        .where(
            Booking.id == booking_id,
            Booking.condominium_id == scope.condominium_id,
        )
        .options(
            selectinload(Booking.area),
            selectinload(Booking.unit),
            selectinload(Booking.person),
        )
    )
    if booking is None:
        raise _error(status.HTTP_403_FORBIDDEN, "booking not in this condominium")
    return booking


async def list_bookings(session: AsyncSession, scope: Scope) -> list[dict]:
    query = (
        select(Booking)
        .where(Booking.condominium_id == scope.condominium_id)
        .options(
            selectinload(Booking.area),
            selectinload(Booking.unit),
            selectinload(Booking.person),
        )
    )
    # Self-service roles see their own bookings; read roles the whole condominium.
    if not scope.has_permission(PERM_BOOKINGS_MANAGE) and not scope.has_permission(
        PERM_BOOKINGS_READ
    ):
        query = query.where(Booking.person_id == scope.person_id)
    bookings = (await session.scalars(query.order_by(Booking.start_at.desc()))).all()
    return [_booking_view(booking) for booking in bookings]


async def create_booking(
    session: AsyncSession,
    scope: Scope,
    *,
    area_id: int,
    start_at: datetime,
    end_at: datetime,
    unit_id: int | None,
    person_id: int | None,
) -> dict:
    if end_at <= start_at:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "booking end must be after its start",
        )
    await get_area_in_scope(session, scope, area_id)

    if scope.has_permission(PERM_BOOKINGS_MANAGE):
        if person_id is None or unit_id is None:
            raise _error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "person_id and unit_id are required",
            )
        await _person_in_scope(session, scope, person_id)
        await _unit_in_scope(session, scope, unit_id)
    else:
        # Residents book only for themselves, on a unit they are linked to.
        if unit_id is None:
            raise _error(status.HTTP_422_UNPROCESSABLE_CONTENT, "unit_id is required")
        if not scope.has_unit_link(unit_id):
            raise _error(status.HTTP_403_FORBIDDEN, "you are not linked to this unit")
        person_id = scope.person_id

    booking = Booking(
        condominium_id=scope.condominium_id,
        area_id=area_id,
        unit_id=unit_id,
        person_id=person_id,
        start_at=start_at,
        end_at=end_at,
        status="reserved",
        created_by_user_id=scope.user_id,
    )
    session.add(booking)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise _error(
            status.HTTP_409_CONFLICT,
            "time slot overlaps an existing booking in this area",
        ) from exc
    return _booking_view(await _booking_or_403(session, scope, booking.id))


async def cancel_booking(session: AsyncSession, scope: Scope, booking_id: int) -> dict:
    booking = await _booking_or_403(session, scope, booking_id)
    if booking.status != "reserved":
        raise _error(status.HTTP_409_CONFLICT, "booking is not reserved")
    if not scope.has_permission(PERM_BOOKINGS_MANAGE):
        if booking.person_id != scope.person_id:
            raise _error(status.HTTP_403_FORBIDDEN, "not your booking")
    booking.status = "cancelled"
    await session.commit()
    return _booking_view(booking)


async def _person_in_scope(session: AsyncSession, scope: Scope, person_id: int) -> None:
    link = await session.scalar(
        select(MemberLink)
        .join(Unit, Unit.id == MemberLink.unit_id)
        .where(
            MemberLink.person_id == person_id,
            Unit.condominium_id == scope.condominium_id,
        )
    )
    if link is None:
        raise _error(status.HTTP_403_FORBIDDEN, "person is not a resident of this condominium")


async def _unit_in_scope(session: AsyncSession, scope: Scope, unit_id: int) -> None:
    unit = await session.scalar(
        select(Unit).where(Unit.id == unit_id, Unit.condominium_id == scope.condominium_id)
    )
    if unit is None:
        raise _error(status.HTTP_403_FORBIDDEN, "unit not in this condominium")
