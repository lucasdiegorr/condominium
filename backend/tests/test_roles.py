"""Integration tests for role administration and permissions (access-control).

Covers: differentiated role types (functions x unit links), the unit-link rule
(guaranteed membership for accounts, link-only for residents), single inquilino
per unit, multiple links per person, 403 outside the role and scope mismatch.
"""

import jwt
import pytest
from conftest import ADMIN_EMAIL, ADMIN_PASSWORD
from httpx import AsyncClient
from sqlalchemy import select

from app.config import get_settings
from app.core.permissions import (
    ROLE_CONDOMINO,
    ROLE_CONSELHO,
    ROLE_INQUILINO,
    ROLE_SINDICO,
)
from app.db import SessionLocal
from app.models import MemberLink, Membership, MembershipRole, Unit, User
from tests.helpers import (
    bearer,
    create_condominium_api,
    create_person_only,
    create_person_user,
    login_identity,
    select_scoped,
)

SECRET = get_settings().jwt_secret
ALGORITHM = get_settings().jwt_algorithm


@pytest.fixture
async def condo_and_admin(client: AsyncClient) -> tuple[int, str]:
    """A condominium and the admin's scoped token for it."""
    identity = await login_identity(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    condominium = await create_condominium_api(client, identity, "Roles HQ")
    scoped = await select_scoped(client, identity, condominium["id"])
    return condominium["id"], scoped


# --- Differentiated role types ---


@pytest.mark.asyncio
async def test_set_function_roles_creates_membership(
    client: AsyncClient, condo_and_admin: tuple[int, str]
) -> None:
    condo_id, admin_scoped = condo_and_admin
    person_id, user_id = await create_person_user(
        email="functions@example.com", name="Function Holder"
    )

    response = await client.put(
        f"/admin/condominiums/{condo_id}/users/{user_id}/functions",
        headers=bearer(admin_scoped),
        json={"roles": [ROLE_SINDICO]},
    )
    assert response.status_code == 200, response.text
    overview = response.json()
    entry = next(m for m in overview["memberships"] if m["user_id"] == user_id)
    assert entry["functions"] == [ROLE_SINDICO]
    assert entry["active"] is True


@pytest.mark.asyncio
async def test_set_functions_rejects_unit_link_role(
    client: AsyncClient, condo_and_admin: tuple[int, str]
) -> None:
    condo_id, admin_scoped = condo_and_admin
    _, user_id = await create_person_user(email="badrole@example.com")

    response = await client.put(
        f"/admin/condominiums/{condo_id}/users/{user_id}/functions",
        headers=bearer(admin_scoped),
        json={"roles": [ROLE_CONDOMINO]},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_unit_link_auto_creates_membership_for_account_holder(
    client: AsyncClient, condo_and_admin: tuple[int, str]
) -> None:
    condo_id, admin_scoped = condo_and_admin
    person_id, user_id = await create_person_user(email="owner@example.com")

    # Register a unit first (direct insert — unit endpoints land in chapter 7).
    async with SessionLocal() as session:
        unit = Unit(
            condominium_id=condo_id,
            code="T1-101",
            number="101",
            block="T1",
            fraction="20.000000",
        )
        session.add(unit)
        await session.commit()
        unit_id = unit.id

    response = await client.post(
        f"/admin/condominiums/{condo_id}/people/{person_id}/links",
        headers=bearer(admin_scoped),
        json={"role": ROLE_CONDOMINO, "unit_id": unit_id},
    )
    assert response.status_code == 200, response.text
    overview = response.json()
    assert any(
        link["person_id"] == person_id and link["role"] == ROLE_CONDOMINO
        for link in overview["unit_links"]
    )

    # The rule: the person's account guarantees an active membership.
    async with SessionLocal() as session:
        membership = await session.scalar(
            select(Membership).where(
                Membership.user_id == user_id,
                Membership.condominium_id == condo_id,
            )
        )
    assert membership is not None and membership.active is True

    # Re-selecting puts the link role in the scoped token.
    identity = await login_identity(client, "owner@example.com")
    scoped = await select_scoped(client, identity, condo_id)
    payload = jwt.decode(scoped, SECRET, algorithms=[ALGORITHM])
    assert ROLE_CONDOMINO in payload["roles"]
    assert any(link["unit_id"] == unit_id for link in payload["unit_links"])


@pytest.mark.asyncio
async def test_unit_link_without_account_creates_no_membership(
    client: AsyncClient, condo_and_admin: tuple[int, str]
) -> None:
    condo_id, admin_scoped = condo_and_admin
    person_id = await create_person_only(name="Resident Without Login")

    async with SessionLocal() as session:
        unit = Unit(
            condominium_id=condo_id,
            code="T1-202",
            number="202",
            block="T1",
            fraction="15.000000",
        )
        session.add(unit)
        await session.commit()
        unit_id = unit.id

    response = await client.post(
        f"/admin/condominiums/{condo_id}/people/{person_id}/links",
        headers=bearer(admin_scoped),
        json={"role": ROLE_INQUILINO, "unit_id": unit_id},
    )
    assert response.status_code == 200, response.text

    async with SessionLocal() as session:
        link = await session.scalar(select(MemberLink).where(MemberLink.person_id == person_id))
        rows = (
            await session.execute(
                select(Membership, User).join(User, User.id == Membership.user_id)
            )
        ).all()
    assert link is not None
    assert all(user.person_id != person_id for _, user in rows), (
        "resident without login must not get a membership"
    )


@pytest.mark.asyncio
async def test_only_one_inquilino_per_unit(
    client: AsyncClient, condo_and_admin: tuple[int, str]
) -> None:
    condo_id, admin_scoped = condo_and_admin
    person_a, _ = await create_person_user(email="tenant-a@example.com")
    person_b, _ = await create_person_user(email="tenant-b@example.com")

    async with SessionLocal() as session:
        unit = Unit(
            condominium_id=condo_id,
            code="T2-303",
            number="303",
            block="T2",
            fraction="10.000000",
        )
        session.add(unit)
        await session.commit()
        unit_id = unit.id

    first = await client.post(
        f"/admin/condominiums/{condo_id}/people/{person_a}/links",
        headers=bearer(admin_scoped),
        json={"role": ROLE_INQUILINO, "unit_id": unit_id},
    )
    assert first.status_code == 200

    second = await client.post(
        f"/admin/condominiums/{condo_id}/people/{person_b}/links",
        headers=bearer(admin_scoped),
        json={"role": ROLE_INQUILINO, "unit_id": unit_id},
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_multiple_condomino_links_per_person(
    client: AsyncClient, condo_and_admin: tuple[int, str]
) -> None:
    condo_id, admin_scoped = condo_and_admin
    person_id, _ = await create_person_user(email="two-units@example.com")

    async with SessionLocal() as session:
        unit_a = Unit(
            condominium_id=condo_id,
            code="A-101",
            number="101",
            block="A",
            fraction="8.000000",
        )
        unit_b = Unit(
            condominium_id=condo_id,
            code="A-102",
            number="102",
            block="A",
            fraction="8.000000",
        )
        session.add_all([unit_a, unit_b])
        await session.commit()
        unit_ids = [unit_a.id, unit_b.id]

    for unit_id in unit_ids:
        response = await client.post(
            f"/admin/condominiums/{condo_id}/people/{person_id}/links",
            headers=bearer(admin_scoped),
            json={"role": ROLE_CONDOMINO, "unit_id": unit_id},
        )
        assert response.status_code == 200, response.text

    async with SessionLocal() as session:
        links = (
            await session.scalars(select(MemberLink).where(MemberLink.person_id == person_id))
        ).all()
    assert len(links) == 2


@pytest.mark.asyncio
async def test_delete_unit_link(client: AsyncClient, condo_and_admin: tuple[int, str]) -> None:
    condo_id, admin_scoped = condo_and_admin
    person_id, _ = await create_person_user(email="removed@example.com")

    async with SessionLocal() as session:
        unit = Unit(
            condominium_id=condo_id,
            code="B-101",
            number="101",
            block="B",
            fraction="5.000000",
        )
        session.add(unit)
        await session.commit()
        unit_id = unit.id

    created = await client.post(
        f"/admin/condominiums/{condo_id}/people/{person_id}/links",
        headers=bearer(admin_scoped),
        json={"role": ROLE_CONDOMINO, "unit_id": unit_id},
    )
    link_id = next(
        link["id"] for link in created.json()["unit_links"] if link["person_id"] == person_id
    )

    deleted = await client.delete(
        f"/admin/condominiums/{condo_id}/links/{link_id}",
        headers=bearer(admin_scoped),
    )
    assert deleted.status_code == 200
    assert all(link["id"] != link_id for link in deleted.json()["unit_links"])


# --- Permissions (403 outside the role) ---


async def _role_holder(client: AsyncClient, condo_id: int, role: str, email: str) -> str:
    """Create a user with `role` in the condominium and return a scoped token."""
    person_id, user_id = await create_person_user(email=email, name=f"Holder {role}")
    async with SessionLocal() as session:
        membership = Membership(user_id=user_id, condominium_id=condo_id, active=True)
        session.add(membership)
        await session.flush()
        session.add(MembershipRole(membership_id=membership.id, role=role))
        await session.commit()

    identity = await login_identity(client, email)
    return await select_scoped(client, identity, condo_id)


@pytest.mark.asyncio
async def test_sindico_cannot_manage_roles(
    client: AsyncClient, condo_and_admin: tuple[int, str]
) -> None:
    condo_id, _ = condo_and_admin
    sindico_scoped = await _role_holder(client, condo_id, ROLE_SINDICO, "sindico@example.com")
    response = await client.get(
        f"/admin/condominiums/{condo_id}/roles",
        headers=bearer(sindico_scoped),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cross_condominium_path_vs_scope_is_denied(
    client: AsyncClient, condo_and_admin: tuple[int, str]
) -> None:
    """Even the admin: path condominium must match the scoped one (5.4)."""
    _, admin_scoped = condo_and_admin
    identity = await login_identity(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    other = await create_condominium_api(client, identity, "Other Condo")

    response = await client.get(
        f"/admin/condominiums/{other['id']}/roles",
        headers=bearer(admin_scoped),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_identity_token_on_admin_scope_route_is_401(
    client: AsyncClient, condo_and_admin: tuple[int, str]
) -> None:
    identity = await login_identity(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    response = await client.get(
        f"/admin/condominiums/{condo_and_admin[0]}/roles",
        headers=bearer(identity),
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_conselho_has_no_role_management(
    client: AsyncClient, condo_and_admin: tuple[int, str]
) -> None:
    condo_id, _ = condo_and_admin
    conselho_scoped = await _role_holder(client, condo_id, ROLE_CONSELHO, "conselho@example.com")
    response = await client.get(
        f"/admin/condominiums/{condo_id}/roles",
        headers=bearer(conselho_scoped),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_non_role_user_cannot_read_functions(
    client: AsyncClient, condo_and_admin: tuple[int, str]
) -> None:
    condo_id, _ = condo_and_admin
    scoped = await _role_holder(client, condo_id, ROLE_CONDOMINO, "condomino@example.com")
    response = await client.get(
        f"/admin/condominiums/{condo_id}/roles",
        headers=bearer(scoped),
    )
    assert response.status_code == 403
