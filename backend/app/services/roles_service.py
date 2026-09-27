"""Role management for the global administrator (access-control spec).

Handles condominium-level function roles (sindico, conselho) via membership,
and unit links (condomino, inquilino) via member_links. Enforces the rule:
a unit link for a person WITH a login guarantees an active membership, while
a resident without an account gets only the member_link.
"""

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import permissions
from app.models import (
    MemberLink,
    Membership,
    MembershipRole,
    Person,
    Unit,
    User,
)


def _error(status_code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail=detail)


async def list_role_overview(session: AsyncSession, condominium_id: int) -> dict:
    """Overview of function roles and unit links bound in a condominium."""
    memberships = (
        await session.scalars(
            select(Membership)
            .where(Membership.condominium_id == condominium_id)
            .options(
                selectinload(Membership.user).selectinload(User.person),
                selectinload(Membership.roles),
            )
            .order_by(Membership.id)
        )
    ).all()

    membership_views = []
    for membership in memberships:
        user = membership.user
        membership_views.append(
            {
                "user_id": membership.user_id,
                "email": user.email if user else None,
                "person_name": user.person.name if user else None,
                "active": membership.active,
                "functions": [role.role for role in membership.roles],
            }
        )

    links = (
        await session.scalars(
            select(MemberLink)
            .join(Unit, Unit.id == MemberLink.unit_id)
            .where(Unit.condominium_id == condominium_id)
            .order_by(MemberLink.id)
        )
    ).all()

    link_views = []
    for link in links:
        person = await session.get(Person, link.person_id)
        unit = await session.get(Unit, link.unit_id)
        link_views.append(
            {
                "id": link.id,
                "person_id": link.person_id,
                "person_name": person.name if person else None,
                "unit_id": link.unit_id,
                "unit_code": unit.code if unit else None,
                "role": link.role,
            }
        )

    return {
        "condominium_id": condominium_id,
        "memberships": membership_views,
        "unit_links": link_views,
    }


async def set_function_roles(
    session: AsyncSession,
    condominium_id: int,
    user_id: int,
    roles: list[str],
) -> dict:
    """Set exactly `roles` as the user's function roles in the condominium.

    Creates a membership when missing and rejects unit-link roles here.
    """
    unknown = [role for role in roles if role not in permissions.FUNCTION_ROLES]
    if unknown or not isinstance(roles, list):
        raise _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "only function roles are allowed: sindico, conselho",
        )

    user = await session.get(User, user_id)
    if user is None or not user.active:
        raise _error(status.HTTP_404_NOT_FOUND, "user not found")

    membership = await session.scalar(
        select(Membership).where(
            Membership.user_id == user_id,
            Membership.condominium_id == condominium_id,
        )
    )
    if membership is None:
        membership = Membership(user_id=user_id, condominium_id=condominium_id, active=True)
        session.add(membership)
        await session.flush()

    await session.execute(
        delete(MembershipRole).where(MembershipRole.membership_id == membership.id)
    )
    for role in roles:
        session.add(MembershipRole(membership_id=membership.id, role=role))
    await session.commit()

    return await list_role_overview(session, condominium_id)


async def create_unit_link(
    session: AsyncSession,
    condominium_id: int,
    person_id: int,
    role: str,
    unit_id: int,
) -> dict:
    """Bind a person to a unit as condomino/inquilino.

    Guarantees an active membership when the person has a login (design: access
    always flows through the association). A resident without an account gets
    only the member_link.
    """
    if not permissions.is_unit_link_role(role):
        raise _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "only unit-link roles are allowed: condomino, inquilino",
        )

    person = await session.get(Person, person_id)
    if person is None:
        raise _error(status.HTTP_404_NOT_FOUND, "person not found")

    unit = await session.scalar(
        select(Unit).where(Unit.id == unit_id, Unit.condominium_id == condominium_id)
    )
    if unit is None:
        raise _error(status.HTTP_403_FORBIDDEN, "unit not found in this condominium")

    # Only one active inquilino per unit at a time.
    if role == permissions.ROLE_INQUILINO:
        existing_inquilino = await session.scalar(
            select(MemberLink)
            .join(Unit, Unit.id == MemberLink.unit_id)
            .where(
                Unit.condominium_id == condominium_id,
                MemberLink.unit_id == unit_id,
                MemberLink.role == permissions.ROLE_INQUILINO,
            )
        )
        if existing_inquilino is not None:
            raise _error(
                status.HTTP_409_CONFLICT,
                "this unit already has an inquilino",
            )

    duplicate = await session.scalar(
        select(MemberLink).where(
            MemberLink.person_id == person_id,
            MemberLink.unit_id == unit_id,
            MemberLink.role == role,
        )
    )
    if duplicate is not None:
        raise _error(status.HTTP_409_CONFLICT, "link already exists")

    link = MemberLink(person_id=person_id, unit_id=unit_id, role=role)
    session.add(link)

    # Rule: a person with an account must have an active membership.
    user = await session.scalar(select(User).where(User.person_id == person_id))
    if user is not None:
        membership = await session.scalar(
            select(Membership).where(
                Membership.user_id == user.id,
                Membership.condominium_id == condominium_id,
            )
        )
        if membership is None:
            session.add(Membership(user_id=user.id, condominium_id=condominium_id, active=True))
        elif not membership.active:
            membership.active = True

    await session.commit()
    return await list_role_overview(session, condominium_id)


async def delete_unit_link(session: AsyncSession, condominium_id: int, link_id: int) -> None:
    """Remove a unit link that belongs to the condominium."""
    link = await session.scalar(
        select(MemberLink)
        .join(Unit, Unit.id == MemberLink.unit_id)
        .where(MemberLink.id == link_id, Unit.condominium_id == condominium_id)
    )
    if link is None:
        raise _error(status.HTTP_404_NOT_FOUND, "link not found")
    await session.delete(link)
    await session.commit()


async def ensure_suggested_categories(session: AsyncSession, condominium_id: int) -> None:
    """Create the suggested chart-of-accounts categories for a condominium."""
    from app.models import AccountCategory
    from app.seed import SUGGESTED_CATEGORIES

    existing = {
        (c.name, c.kind)
        for c in (
            await session.scalars(
                select(AccountCategory).where(AccountCategory.condominium_id == condominium_id)
            )
        ).all()
    }
    for name, kind in SUGGESTED_CATEGORIES:
        if (name, kind) not in existing:
            session.add(AccountCategory(condominium_id=condominium_id, name=name, kind=kind))
