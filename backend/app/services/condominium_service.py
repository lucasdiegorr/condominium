"""Condominium CRUD and user-association management (condominium-management spec)."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Condominium, Membership, User


async def list_all(session: AsyncSession) -> list[Condominium]:
    return list((await session.scalars(select(Condominium).order_by(Condominium.name))).all())


async def get_or_404(session: AsyncSession, condominium_id: int) -> Condominium:
    condominium = await session.get(Condominium, condominium_id)
    if condominium is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "condominium not found")
    return condominium


async def create(session: AsyncSession, name: str, address: str | None) -> Condominium:
    from app.services.roles_service import ensure_suggested_categories

    condominium = Condominium(name=name, address=address, active=True)
    session.add(condominium)
    await session.flush()
    await ensure_suggested_categories(session, condominium.id)
    await session.commit()
    await session.refresh(condominium)
    return condominium


async def update(
    session: AsyncSession, condominium: Condominium, name: str | None, address: str | None
) -> Condominium:
    if name is not None:
        condominium.name = name
    if address is not None:
        condominium.address = address
    await session.commit()
    await session.refresh(condominium)
    return condominium


async def deactivate(session: AsyncSession, condominium: Condominium) -> None:
    """Deactivate: data preserved, listing/selection blocked (spec scenario)."""
    condominium.active = False
    await session.commit()


async def list_associations(session: AsyncSession, condominium_id: int) -> list[dict]:
    memberships = (
        await session.scalars(
            select(Membership)
            .where(Membership.condominium_id == condominium_id)
            .options(
                selectinload(Membership.user).selectinload(User.person),
                selectinload(Membership.roles),
            )
            .order_by(Membership.user_id)
        )
    ).all()
    views = []
    for membership in memberships:
        user = membership.user
        views.append(
            {
                "user_id": membership.user_id,
                "email": user.email if user else None,
                "person_name": user.person.name if user else None,
                "active": membership.active,
                "functions": [role.role for role in membership.roles],
            }
        )
    return views


async def set_association(
    session: AsyncSession, condominium_id: int, user_id: int, active: bool
) -> dict:
    user = await session.get(User, user_id)
    if user is None or not user.active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")

    membership = await session.scalar(
        select(Membership).where(
            Membership.user_id == user_id,
            Membership.condominium_id == condominium_id,
        )
    )
    if membership is None:
        membership = Membership(user_id=user_id, condominium_id=condominium_id, active=active)
        session.add(membership)
    else:
        membership.active = active
    await session.commit()

    views = await list_associations(session, condominium_id)
    return next(view for view in views if view["user_id"] == user_id)


async def remove_association(session: AsyncSession, condominium_id: int, user_id: int) -> None:
    membership = await session.scalar(
        select(Membership).where(
            Membership.user_id == user_id,
            Membership.condominium_id == condominium_id,
        )
    )
    if membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "association not found")
    await session.delete(membership)
    await session.commit()
