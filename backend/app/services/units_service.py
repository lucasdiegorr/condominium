"""Unit and parking-spot management within a condominium scope (unit-management spec)."""

from decimal import Decimal, InvalidOperation

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ParkingSpot, Unit

UNIT_TYPES = ("apartment", "commercial", "other")
SPOT_TYPES = ("covered", "uncovered")


def _error(status_code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail=detail)


def _coerce_fraction(value) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise _error(status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid ideal fraction") from exc


async def _active_fraction_sum(
    session: AsyncSession, condominium_id: int, exclude_unit_id: int | None = None
) -> Decimal:
    query = select(func.coalesce(func.sum(Unit.fraction), 0)).where(
        Unit.condominium_id == condominium_id, Unit.active.is_(True)
    )
    if exclude_unit_id is not None:
        query = query.where(Unit.id != exclude_unit_id)
    total = await session.scalar(query)
    return _coerce_fraction(total)


async def _fraction_within_total(
    session: AsyncSession,
    condominium_id: int,
    fraction: Decimal,
    exclude_unit_id: int | None = None,
) -> bool:
    total = await _active_fraction_sum(session, condominium_id, exclude_unit_id=exclude_unit_id)
    return total + fraction <= Decimal("100")


def _make_code(number: str, block: str | None) -> str:
    return f"{block}-{number}" if block else number


def _unit_view(unit: Unit) -> dict:
    spots = [
        {
            "id": spot.id,
            "identifier": spot.identifier,
            "spot_type": spot.spot_type,
        }
        for spot in unit.parking_spots
    ]
    return {
        "id": unit.id,
        "code": unit.code,
        "number": unit.number,
        "block": unit.block,
        "unit_type": unit.unit_type,
        "fraction": str(unit.fraction),
        "active": unit.active,
        "parking_spots": spots,
    }


async def list_units(session: AsyncSession, condominium_id: int) -> list[dict]:
    units = (
        await session.scalars(
            select(Unit)
            .where(Unit.condominium_id == condominium_id)
            .options(selectinload(Unit.parking_spots))
            .order_by(Unit.code)
        )
    ).all()
    return [_unit_view(unit) for unit in units]


async def get_unit_in_scope(session: AsyncSession, condominium_id: int, unit_id: int) -> Unit:
    unit = await session.scalar(
        select(Unit)
        .where(Unit.id == unit_id, Unit.condominium_id == condominium_id)
        .options(selectinload(Unit.parking_spots))
    )
    if unit is None:
        raise _error(status.HTTP_403_FORBIDDEN, "unit not in this condominium")
    return unit


async def get_unit_detail(session: AsyncSession, condominium_id: int, unit_id: int) -> dict:
    return _unit_view(await get_unit_in_scope(session, condominium_id, unit_id))


async def create_unit(
    session: AsyncSession,
    condominium_id: int,
    *,
    number: str,
    block: str | None,
    unit_type: str,
    fraction: Decimal,
) -> dict:
    if unit_type not in UNIT_TYPES:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"unit type must be one of: {', '.join(UNIT_TYPES)}",
        )
    code = _make_code(number, block)
    existing = await session.scalar(
        select(Unit).where(Unit.condominium_id == condominium_id, Unit.code == code)
    )
    if existing is not None:
        raise _error(status.HTTP_409_CONFLICT, "unit code already exists")

    if not await _fraction_within_total(session, condominium_id, fraction):
        raise _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "the sum of ideal fractions would exceed 100%",
        )

    unit = Unit(
        condominium_id=condominium_id,
        code=code,
        number=number,
        block=block,
        unit_type=unit_type,
        fraction=str(fraction),
    )
    session.add(unit)
    await session.commit()
    return await get_unit_detail(session, condominium_id, unit.id)


async def update_unit(
    session: AsyncSession,
    condominium_id: int,
    unit_id: int,
    *,
    number: str | None = None,
    block: str | None = None,
    unit_type: str | None = None,
    fraction: Decimal | None = None,
    active: bool | None = None,
) -> dict:
    unit = await get_unit_in_scope(session, condominium_id, unit_id)

    if unit_type is not None and unit_type not in UNIT_TYPES:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"unit type must be one of: {', '.join(UNIT_TYPES)}",
        )

    new_fraction = (
        _coerce_fraction(fraction) if fraction is not None else _coerce_fraction(unit.fraction)
    )
    if new_fraction <= 0:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "ideal fraction must be greater than 0",
        )
    if not await _fraction_within_total(
        session, condominium_id, new_fraction, exclude_unit_id=unit_id
    ):
        raise _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "the sum of ideal fractions would exceed 100%",
        )

    if number is not None:
        unit.number = number
    if block is not None:
        unit.block = block
    if unit_type is not None:
        unit.unit_type = unit_type
    if fraction is not None:
        unit.fraction = str(new_fraction)
    if active is not None:
        unit.active = active

    new_code = _make_code(unit.number, unit.block)
    if new_code != unit.code:
        duplicate = await session.scalar(
            select(Unit).where(
                Unit.condominium_id == condominium_id,
                Unit.code == new_code,
                Unit.id != unit_id,
            )
        )
        if duplicate is not None:
            raise _error(status.HTTP_409_CONFLICT, "unit code already exists")
        unit.code = new_code

    await session.commit()
    return await get_unit_detail(session, condominium_id, unit.id)


async def delete_unit(session: AsyncSession, condominium_id: int, unit_id: int) -> None:
    unit = await get_unit_in_scope(session, condominium_id, unit_id)
    try:
        await session.delete(unit)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise _error(
            status.HTTP_409_CONFLICT,
            "unit is referenced by other records and cannot be removed",
        ) from exc


async def list_parking_spots(
    session: AsyncSession, condominium_id: int, unit_id: int | None = None
) -> list[dict]:
    query = select(ParkingSpot).where(ParkingSpot.condominium_id == condominium_id)
    if unit_id is not None:
        query = query.where(ParkingSpot.unit_id == unit_id)
    spots = (await session.scalars(query.order_by(ParkingSpot.identifier))).all()
    return [
        {
            "id": spot.id,
            "identifier": spot.identifier,
            "spot_type": spot.spot_type,
            "unit_id": spot.unit_id,
        }
        for spot in spots
    ]


async def create_parking_spot(
    session: AsyncSession,
    condominium_id: int,
    *,
    unit_id: int,
    identifier: str,
    spot_type: str,
) -> dict:
    if spot_type not in SPOT_TYPES:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"spot type must be one of: {', '.join(SPOT_TYPES)}",
        )
    await get_unit_in_scope(session, condominium_id, unit_id)
    existing = await session.scalar(
        select(ParkingSpot).where(
            ParkingSpot.condominium_id == condominium_id,
            ParkingSpot.identifier == identifier,
        )
    )
    if existing is not None:
        raise _error(status.HTTP_409_CONFLICT, "parking identifier already in use")

    spot = ParkingSpot(
        condominium_id=condominium_id,
        unit_id=unit_id,
        identifier=identifier,
        spot_type=spot_type,
    )
    session.add(spot)
    await session.commit()
    await session.refresh(spot)
    return {
        "id": spot.id,
        "identifier": spot.identifier,
        "spot_type": spot.spot_type,
        "unit_id": spot.unit_id,
    }


async def delete_parking_spot(session: AsyncSession, condominium_id: int, spot_id: int) -> None:
    spot = await session.scalar(
        select(ParkingSpot).where(
            ParkingSpot.id == spot_id,
            ParkingSpot.condominium_id == condominium_id,
        )
    )
    if spot is None:
        raise _error(status.HTTP_404_NOT_FOUND, "parking spot not found")
    await session.delete(spot)
    await session.commit()
