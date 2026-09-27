"""Integration tests for persons and residents (people spec, chapter 6).

Covers: person distinct from user, unique CPF/e-mail, multiple links per person
and per unit, síndico registration inside its scope (403 outside), and account
creation restricted to the global administrator.
"""

import pytest
from conftest import ADMIN_EMAIL, ADMIN_PASSWORD
from httpx import AsyncClient
from sqlalchemy import select

from app.db import SessionLocal
from app.models import MemberLink, Membership, Person, Unit, User
from tests.helpers import (
    bearer,
    create_condominium_api,
    create_person_only,
    create_person_user,
    login_identity,
    role_scoped_token,
    select_scoped,
    unique_cpf,
)


async def admin_identity(client: AsyncClient) -> str:
    return await login_identity(client, ADMIN_EMAIL, ADMIN_PASSWORD)


async def make_condo_and_sindico(client: AsyncClient) -> tuple[int, str, str]:
    identity = await admin_identity(client)
    condominium = await create_condominium_api(client, identity, "People Condo")
    sindico = await role_scoped_token(
        client, condominium["id"], "sindico", f"sindico-{condominium['id']}@example.com"
    )
    return condominium["id"], identity, sindico


async def seed_unit(session_id: int, code: str, fraction: str = "10.000000") -> int:
    async with SessionLocal() as session:
        unit = Unit(
            condominium_id=session_id,
            code=code,
            number=code.split("-")[-1],
            fraction=fraction,
        )
        session.add(unit)
        await session.commit()
        return unit.id


@pytest.fixture
async def people_scope(client: AsyncClient) -> tuple[int, str, str]:
    """(condominium_id, admin identity token, síndico scoped token)."""
    return await make_condo_and_sindico(client)


# --- Person registration ---


@pytest.mark.asyncio
async def test_sindico_registers_person_without_account(
    client: AsyncClient, people_scope: tuple[int, str, str]
) -> None:
    condo_id, _, sindico = people_scope
    response = await client.post(
        "/residents",
        headers=bearer(sindico),
        json={"name": "No Login Resident", "cpf": unique_cpf()},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["has_account"] is False
    assert body["links"] == []

    # No user account exists for the person.
    async with SessionLocal() as session:
        person = await session.get(Person, body["id"])
        user_rows = (await session.scalars(select(User))).all()
    assert person is not None
    assert all(u.person_id != body["id"] for u in user_rows)


@pytest.mark.asyncio
async def test_duplicate_cpf_rejected(
    client: AsyncClient, people_scope: tuple[int, str, str]
) -> None:
    _, _, sindico = people_scope
    cpf = unique_cpf()
    first = await client.post(
        "/residents", headers=bearer(sindico), json={"name": "First", "cpf": cpf}
    )
    assert first.status_code == 201
    second = await client.post(
        "/residents", headers=bearer(sindico), json={"name": "Second", "cpf": cpf}
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_invalid_cpf_rejected(
    client: AsyncClient, people_scope: tuple[int, str, str]
) -> None:
    _, _, sindico = people_scope
    response = await client.post(
        "/residents",
        headers=bearer(sindico),
        json={"name": "Bad CPF", "cpf": "11122233344"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_conselho_can_list_but_not_create(
    client: AsyncClient, people_scope: tuple[int, str, str]
) -> None:
    condo_id, _, _ = people_scope
    conselho = await role_scoped_token(
        client, condo_id, "conselho", f"conselho-{condo_id}@example.com"
    )
    listing = await client.get("/residents", headers=bearer(conselho))
    assert listing.status_code == 200
    creation = await client.post(
        "/residents",
        headers=bearer(conselho),
        json={"name": "Nope", "cpf": unique_cpf()},
    )
    assert creation.status_code == 403


# --- Unit links ---


@pytest.mark.asyncio
async def test_sindico_links_resident_and_guarantees_membership(
    client: AsyncClient, people_scope: tuple[int, str, str]
) -> None:
    condo_id, _, sindico = people_scope
    person_id, user_id = await create_person_user(email="owner-6@example.com")
    unit_id = await seed_unit(condo_id, "P-101")

    response = await client.post(
        f"/residents/{person_id}/links",
        headers=bearer(sindico),
        json={"role": "condomino", "unit_id": unit_id},
    )
    assert response.status_code == 201, response.text
    links = response.json()["links"]
    assert len(links) == 1 and links[0]["role"] == "condomino"
    assert links[0]["unit_code"] == "P-101"

    async with SessionLocal() as session:
        membership = await session.scalar(
            select(Membership).where(
                Membership.user_id == user_id,
                Membership.condominium_id == condo_id,
            )
        )
    assert membership is not None and membership.active


@pytest.mark.asyncio
async def test_couple_condominos_and_one_inquilino_coexist(
    client: AsyncClient, people_scope: tuple[int, str, str]
) -> None:
    """João + Maria as condôminos and Pedro as inquilino on the same unit."""
    condo_id, _, sindico = people_scope
    unit_id = await seed_unit(condo_id, "P-202")
    joao, _ = await create_person_user(email="joao@example.com", name="João")
    maria, _ = await create_person_user(email="maria@example.com", name="Maria")
    pedro, _ = await create_person_user(email="pedro@example.com", name="Pedro")

    for person_id in (joao, maria):
        response = await client.post(
            f"/residents/{person_id}/links",
            headers=bearer(sindico),
            json={"role": "condomino", "unit_id": unit_id},
        )
        assert response.status_code == 201, response.text
    response = await client.post(
        f"/residents/{pedro}/links",
        headers=bearer(sindico),
        json={"role": "inquilino", "unit_id": unit_id},
    )
    assert response.status_code == 201

    async with SessionLocal() as session:
        links = (
            await session.scalars(select(MemberLink).where(MemberLink.unit_id == unit_id))
        ).all()
    assert len(links) == 3
    assert sum(1 for link in links if link.role == "condomino") == 2
    assert sum(1 for link in links if link.role == "inquilino") == 1


@pytest.mark.asyncio
async def test_links_are_isolated_between_condominiums(
    client: AsyncClient, people_scope: tuple[int, str, str]
) -> None:
    """A person owning units in two condominiums keeps links per scope (6.4)."""
    condo_a, _, sindico_a = people_scope
    admin = await admin_identity(client)
    condo_b = await create_condominium_api(client, admin, "Second Condo")
    person_id, _ = await create_person_user(email="two-condos@example.com")

    unit_a = await seed_unit(condo_a, "X-101")
    unit_b = await seed_unit(condo_b["id"], "X-101")

    await client.post(
        f"/residents/{person_id}/links",
        headers=bearer(sindico_a),
        json={"role": "condomino", "unit_id": unit_a},
    )
    sindico_b = await role_scoped_token(client, condo_b["id"], "sindico", "sindico-b@example.com")
    await client.post(
        f"/residents/{person_id}/links",
        headers=bearer(sindico_b),
        json={"role": "condomino", "unit_id": unit_b},
    )

    # Listing in A shows only the link in A.
    listing_a = await client.get("/residents", headers=bearer(sindico_a))
    entry = next(p for p in listing_a.json() if p["id"] == person_id)
    assert [link["unit_id"] for link in entry["links"]] == [unit_a]


@pytest.mark.asyncio
async def test_sindico_cannot_link_unit_of_another_condominium(
    client: AsyncClient, people_scope: tuple[int, str, str]
) -> None:
    condo_a, _, sindico_a = people_scope
    admin = await admin_identity(client)
    condo_b = await create_condominium_api(client, admin, "Foreign Condo")
    person_id, _ = await create_person_user(email="foreign-unit@example.com")
    unit_b = await seed_unit(condo_b["id"], "F-999")

    response = await client.post(
        f"/residents/{person_id}/links",
        headers=bearer(sindico_a),
        json={"role": "condomino", "unit_id": unit_b},
    )
    assert response.status_code == 403


# --- Accounts (users.manage = global administrator) ---


@pytest.mark.asyncio
async def test_only_administrator_creates_accounts(
    client: AsyncClient, people_scope: tuple[int, str, str]
) -> None:
    condo_id, admin, _ = people_scope
    person_id = await create_person_only(name="Lee Tenant")
    unit_id = await seed_unit(condo_id, "A-101")
    # Give the person a roster link so the account can be created in scope.
    async with SessionLocal() as session:
        session.add(MemberLink(person_id=person_id, unit_id=unit_id, role="condomino"))
        await session.commit()

    scoped_admin = await select_scoped(client, admin, condo_id)
    response = await client.post(
        f"/residents/{person_id}/account",
        headers=bearer(scoped_admin),
        json={"email": "new-account@example.com", "password": "a-strong-pass"},
    )
    assert response.status_code == 201, response.text

    # The new credentials authenticate.
    identity = await login_identity(client, "new-account@example.com", "a-strong-pass")
    assert identity


@pytest.mark.asyncio
async def test_sindico_cannot_create_account(
    client: AsyncClient, people_scope: tuple[int, str, str]
) -> None:
    condo_id, _, sindico = people_scope
    person_id, _ = await create_person_user(email="no-admin@example.com")
    unit_id = await seed_unit(condo_id, "A-102")
    async with SessionLocal() as session:
        session.add(MemberLink(person_id=person_id, unit_id=unit_id, role="condomino"))
        await session.commit()

    response = await client.post(
        f"/residents/{person_id}/account",
        headers=bearer(sindico),
        json={"email": "blocked@example.com", "password": "a-strong-pass"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_duplicate_email_and_weak_password_rejected(
    client: AsyncClient, people_scope: tuple[int, str, str]
) -> None:
    condo_id, admin, _ = people_scope
    person_id = await create_person_only(name="Existing Account")
    person_two = await create_person_only(name="Second Person")
    unit_id = await seed_unit(condo_id, "A-103")
    async with SessionLocal() as session:
        session.add_all(
            [
                MemberLink(person_id=person_id, unit_id=unit_id, role="condomino"),
                MemberLink(person_id=person_two, unit_id=unit_id, role="condomino"),
            ]
        )
        await session.commit()

    scoped_admin = await select_scoped(client, admin, condo_id)

    first = await client.post(
        f"/residents/{person_id}/account",
        headers=bearer(scoped_admin),
        json={"email": "dupe@example.com", "password": "a-strong-pass"},
    )
    assert first.status_code == 201, first.text

    duplicate = await client.post(
        f"/residents/{person_two}/account",
        headers=bearer(scoped_admin),
        json={"email": "dupe@example.com", "password": "a-strong-pass"},
    )
    assert duplicate.status_code == 409

    weak = await client.post(
        f"/residents/{person_two}/account",
        headers=bearer(scoped_admin),
        json={"email": "fresh@example.com", "password": "short"},
    )
    assert weak.status_code == 422
