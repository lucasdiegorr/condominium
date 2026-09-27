"""Person / resident management for a condominium scope (people spec).

A person may or may not have a login; unit links build the residents roster.
All queries are filtered by the scoped condominium (design: never query domain
data without the scope filter).
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.cpf import validate_cpf
from app.core.security import hash_password
from app.models import MemberLink, Person, Unit, User
from app.services import roles_service


def _error(status_code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail=detail)


async def _person_links_in_scope(
    session: AsyncSession, condominium_id: int, person_id: int
) -> list[MemberLink]:
    """Unit links of `person` inside `condominium` (preloaded units)."""
    person = await session.scalar(
        select(Person)
        .where(Person.id == person_id)
        .options(selectinload(Person.member_links).selectinload(MemberLink.unit))
    )
    if person is None:
        return []
    return [
        link
        for link in person.member_links
        if link.unit is not None and link.unit.condominium_id == condominium_id
    ]


def _link_view(link: MemberLink) -> dict:
    return {
        "id": link.id,
        "person_id": link.person_id,
        "unit_id": link.unit_id,
        "unit_code": link.unit.code if link.unit else None,
        "role": link.role,
    }


async def _person_view(session: AsyncSession, condominium_id: int, person: Person) -> dict:
    """Build the response view with the links inside the scope only."""
    links = await _person_links_in_scope(session, condominium_id, person.id)
    user = await session.scalar(select(User).where(User.person_id == person.id))
    return {
        "id": person.id,
        "name": person.name,
        "cpf": person.cpf,
        "phone": person.phone,
        "email_contact": person.email_contact,
        "has_account": user is not None,
        "links": [_link_view(link) for link in links],
    }


async def list_roster(session: AsyncSession, condominium_id: int) -> list[dict]:
    """People holding at least one unit link in the condominium (roster)."""
    people = (
        await session.scalars(
            select(Person)
            .join(MemberLink, MemberLink.person_id == Person.id)
            .join(Unit, Unit.id == MemberLink.unit_id)
            .where(Unit.condominium_id == condominium_id)
            .distinct()
            .order_by(Person.name)
        )
    ).all()
    return [await _person_view(session, condominium_id, person) for person in people]


async def create_person(
    session: AsyncSession,
    condominium_id: int,  # scope context (used for the view links)
    *,
    name: str,
    cpf: str,
    phone: str | None = None,
    email_contact: str | None = None,
) -> dict:
    if not validate_cpf(cpf):
        raise _error(status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid CPF check digits")
    existing = await session.scalar(select(Person).where(Person.cpf == cpf))
    if existing is not None:
        raise _error(status.HTTP_409_CONFLICT, "CPF already registered")

    person = Person(name=name, cpf=cpf, phone=phone, email_contact=email_contact)
    session.add(person)
    await session.commit()
    await session.refresh(person)
    return await _person_view(session, condominium_id, person)


async def get_person_in_scope(session: AsyncSession, condominium_id: int, person_id: int) -> Person:
    """Fetch a person whose roster link exists in the scope; 403 otherwise."""
    person = await session.scalar(
        select(Person)
        .join(MemberLink, MemberLink.person_id == Person.id)
        .join(Unit, Unit.id == MemberLink.unit_id)
        .where(Person.id == person_id, Unit.condominium_id == condominium_id)
    )
    if person is None:
        raise _error(status.HTTP_403_FORBIDDEN, "person not in this condominium")
    return person


async def get_person_detail(session: AsyncSession, condominium_id: int, person_id: int) -> dict:
    person = await get_person_in_scope(session, condominium_id, person_id)
    return await _person_view(session, condominium_id, person)


async def update_person(
    session: AsyncSession,
    condominium_id: int,
    person_id: int,
    *,
    name: str | None = None,
    phone: str | None = None,
    email_contact: str | None = None,
) -> dict:
    person = await get_person_in_scope(session, condominium_id, person_id)
    if name is not None:
        person.name = name
    if phone is not None:
        person.phone = phone
    if email_contact is not None:
        person.email_contact = email_contact
    await session.commit()
    return await _person_view(session, condominium_id, person)


async def add_unit_link(
    session: AsyncSession,
    condominium_id: int,
    person_id: int,
    *,
    role: str,
    unit_id: int,
) -> dict:
    """Bind a resident to a unit (rule 4.4: membership guaranteed for accounts)."""
    await roles_service.create_unit_link(session, condominium_id, person_id, role, unit_id)
    person = await session.get(Person, person_id)
    return await _person_view(session, condominium_id, person)


async def remove_unit_link(
    session: AsyncSession,
    condominium_id: int,
    person_id: int,
    link_id: int,
) -> dict:
    link = await session.scalar(
        select(MemberLink)
        .join(Unit, Unit.id == MemberLink.unit_id)
        .where(
            MemberLink.id == link_id,
            MemberLink.person_id == person_id,
            Unit.condominium_id == condominium_id,
        )
    )
    if link is None:
        raise _error(status.HTTP_404_NOT_FOUND, "link not found")
    await session.delete(link)
    await session.commit()
    return await _person_view(session, condominium_id, person_id)


async def create_account(
    session: AsyncSession,
    condominium_id: int,
    person_id: int,
    *,
    email: str,
    password: str,
) -> dict:
    """Create a login for a person of this condominium (users.manage = admin)."""
    if len(password) < 8:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "password must have at least 8 characters",
        )
    await get_person_in_scope(session, condominium_id, person_id)
    existing_user = await session.scalar(select(User).where(User.person_id == person_id))
    if existing_user is not None:
        raise _error(status.HTTP_409_CONFLICT, "person already has an account")
    existing_email = await session.scalar(select(User).where(User.email == email))
    if existing_email is not None:
        raise _error(status.HTTP_409_CONFLICT, "e-mail already in use")

    account = User(email=email, password_hash=hash_password(password), person_id=person_id)
    session.add(account)
    await session.commit()
    return {"person_id": person_id, "email": email}
