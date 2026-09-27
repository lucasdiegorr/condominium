"""Authentication service — identity token, condominium listing, scoped token."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import permissions
from app.core.security import create_scoped_token, verify_password
from app.models import Condominium, MemberLink, Membership, MembershipRole, Unit, User


async def authenticate_user(session: AsyncSession, email: str, password: str) -> User | None:
    """Return the user when credentials are valid and the account is active."""
    user = await session.scalar(select(User).where(User.email == email.lower().strip()))
    if user is None or not user.active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def list_available_condominiums(session: AsyncSession, user: User) -> list[Condominium]:
    """Condominiums the user can select: active memberships + (admin) all active."""
    query = select(Condominium).where(Condominium.active.is_(True))
    if user.is_global_admin:
        return list((await session.scalars(query)).all())
    query = (
        select(Condominium)
        .join(Membership, Membership.condominium_id == Condominium.id)
        .where(Membership.user_id == user.id, Membership.active.is_(True))
        .where(Condominium.active.is_(True))
    )
    return list((await session.scalars(query)).all())


async def has_active_association(session: AsyncSession, user: User, condominium_id: int) -> bool:
    if user.is_global_admin:
        condominium = await session.get(Condominium, condominium_id)
        return condominium is not None and condominium.active
    membership = await session.scalar(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.condominium_id == condominium_id,
            Membership.active.is_(True),
        )
    )
    return membership is not None


async def collect_scoped_roles(
    session: AsyncSession, user: User, condominium_id: int
) -> tuple[list[str], list[dict]]:
    """Combine function roles (membership_roles) and unit-link roles (member_links).

    Returns (role_codes, unit_links) for the scoped token. Function roles and unit
    links are always revalidated from the database at issuance.
    """
    roles: list[str] = []
    if user.is_global_admin:
        roles.append(permissions.ROLE_GLOBAL_ADMIN)

    membership = await session.scalar(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.condominium_id == condominium_id,
            Membership.active.is_(True),
        )
    )
    if membership is not None:
        membership_roles = await session.scalars(
            select(MembershipRole).where(MembershipRole.membership_id == membership.id)
        )
        roles.extend(mr.role for mr in membership_roles.all())

    unit_links: list[dict] = []
    member_links = await session.scalars(
        select(MemberLink)
        .join(Unit, Unit.id == MemberLink.unit_id)
        .where(MemberLink.person_id == user.person_id, Unit.condominium_id == condominium_id)
    )
    for link in member_links.all():
        roles.append(link.role)
        unit_links.append({"unit_id": link.unit_id, "role": link.role})
    return roles, unit_links


async def issue_scoped_token(session: AsyncSession, user: User, condominium_id: int) -> str:
    roles, unit_links = await collect_scoped_roles(session, user, condominium_id)
    return create_scoped_token(
        user_id=user.id,
        person_id=user.person_id,
        condominium_id=condominium_id,
        roles=roles,
        unit_links=unit_links,
    )
