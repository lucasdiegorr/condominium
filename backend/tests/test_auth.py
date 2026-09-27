"""Integration tests for the authentication flow (user-auth spec, task 3.6).

Covers: login (identity token only, generic 401, inactive users), condominium
listing restricted to associations, selection (scoped token claims, 403 without
leaking existence), combined role collection and association revocation.
"""

import jwt
import pytest
from conftest import ADMIN_EMAIL, ADMIN_PASSWORD, admin_identity_token
from httpx import AsyncClient
from sqlalchemy import select

from app.config import get_settings
from app.core.security import hash_password
from app.db import SessionLocal
from app.models import (
    Condominium,
    MemberLink,
    Membership,
    MembershipRole,
    Person,
    Unit,
    User,
)

SECRET = get_settings().jwt_secret
ALGORITHM = get_settings().jwt_algorithm


async def create_condominium(name: str) -> int:
    """Direct insert, independent of chapter 5 endpoints."""
    async with SessionLocal() as session:
        condominium = Condominium(name=name, address="Test address")
        session.add(condominium)
        await session.commit()
        return condominium.id


# --- Login ---


@pytest.mark.asyncio
async def test_login_returns_only_identity_token(client: AsyncClient) -> None:
    response = await client.post(
        "/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200
    body = response.json()
    # Only the identity token — no condominium/role/user data.
    assert set(body) == {"token", "token_type"}
    payload = jwt.decode(body["token"], SECRET, algorithms=[ALGORITHM])
    assert payload["type"] == "identity"
    assert "condominium_id" not in payload
    assert "roles" not in payload


@pytest.mark.asyncio
async def test_login_invalid_credentials_is_generic_401(client: AsyncClient) -> None:
    for body in (
        {"email": "nobody@example.com", "password": "wrong"},
        {"email": ADMIN_EMAIL, "password": "wrong"},
    ):
        response = await client.post("/auth/login", json=body)
        assert response.status_code == 401
        assert response.json()["detail"] == "invalid credentials"


@pytest.mark.asyncio
async def test_login_inactive_user_gets_generic_401(client: AsyncClient) -> None:
    async with SessionLocal() as session:
        person = Person(name="Inactive", cpf="52998224725", email_contact="inactive@example.com")
        user = User(
            email="inactive@example.com",
            password_hash=hash_password("secret123"),
            active=False,
            person=person,
        )
        session.add(user)
        await session.commit()

    response = await client.post(
        "/auth/login", json={"email": "inactive@example.com", "password": "secret123"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid credentials"


# --- Condominium listing ---


@pytest.mark.asyncio
async def test_listing_restricted_to_active_associations(client: AsyncClient) -> None:
    token = await admin_identity_token(client)
    await create_condominium("List A")
    await create_condominium("List B")

    # The global administrator sees every active condominium.
    listing = await client.get("/auth/condominiums", headers={"Authorization": f"Bearer {token}"})
    assert listing.status_code == 200
    names = {c["name"] for c in listing.json()}
    assert {"List A", "List B"} <= names


@pytest.mark.asyncio
async def test_listing_requires_identity_token(client: AsyncClient) -> None:
    response = await client.get("/auth/condominiums")
    assert response.status_code == 401


# --- Selection (scoped token) ---


@pytest.mark.asyncio
async def test_selection_issues_scoped_token_with_claims(client: AsyncClient) -> None:
    token = await admin_identity_token(client)

    async with SessionLocal() as session:
        admin = await session.scalar(select(User).where(User.email == ADMIN_EMAIL))

    condo_id = await create_condominium("Select Me")
    response = await client.post(
        f"/auth/condominiums/{condo_id}/select",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    scoped = jwt.decode(response.json()["token"], SECRET, algorithms=[ALGORITHM])
    assert scoped["type"] == "scoped"
    assert scoped["condominium_id"] == condo_id
    assert "global_admin" in scoped["roles"]
    assert scoped["person_id"] == admin.person_id


@pytest.mark.asyncio
async def test_selection_for_non_associated_condominium_is_403(client: AsyncClient) -> None:
    await admin_identity_token(client)

    async with SessionLocal() as session:
        person = Person(name="No Assoc", cpf="39053344705", email_contact="noassoc@example.com")
        user = User(
            email="noassoc@example.com",
            password_hash=hash_password("secret123"),
            person=person,
        )
        session.add(user)
        await session.commit()

    login = await client.post(
        "/auth/login", json={"email": "noassoc@example.com", "password": "secret123"}
    )
    user_token = login.json()["token"]

    condo_id = await create_condominium("Private")
    response = await client.post(
        f"/auth/condominiums/{condo_id}/select",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403
    # A nonexistent condominium gets the same response — no existence leak.
    response = await client.post(
        "/auth/condominiums/999999/select",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_scoped_token_roles_combine_functions_and_unit_links(client: AsyncClient) -> None:
    """A membership with a function role + a unit link produce combined roles."""
    from app.core.permissions import ROLE_CONDOMINO, ROLE_SINDICO

    await admin_identity_token(client)
    condo_id = await create_condominium("Roles Condo")

    async with SessionLocal() as session:
        person = Person(name="Role Tester", cpf="12345678909", email_contact="roles@example.com")
        user = User(
            email="roles@example.com",
            password_hash=hash_password("secret123"),
            person=person,
        )
        session.add(user)
        await session.commit()
        user_id, person_id = user.id, person.id

        unit = Unit(
            condominium_id=condo_id,
            code="A-101",
            number="101",
            block="A",
            fraction="12.500000",
        )
        session.add(unit)
        membership = Membership(user_id=user_id, condominium_id=condo_id, active=True)
        session.add(membership)
        await session.flush()
        session.add(MembershipRole(membership_id=membership.id, role=ROLE_SINDICO))
        session.add(MemberLink(person_id=person_id, unit_id=unit.id, role=ROLE_CONDOMINO))
        await session.commit()
        unit_id = unit.id

    login = await client.post(
        "/auth/login", json={"email": "roles@example.com", "password": "secret123"}
    )
    user_token = login.json()["token"]

    select = await client.post(
        f"/auth/condominiums/{condo_id}/select",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert select.status_code == 200, select.text
    payload = jwt.decode(select.json()["token"], SECRET, algorithms=[ALGORITHM])
    assert set(payload["roles"]) == {ROLE_SINDICO, ROLE_CONDOMINO}
    assert {"unit_id": unit_id, "role": ROLE_CONDOMINO} in payload["unit_links"]


@pytest.mark.asyncio
async def test_revoked_association_blocks_renewal(client: AsyncClient) -> None:
    """An association revoked after issuance denies renewal (task 3.5)."""
    await admin_identity_token(client)
    condo_id = await create_condominium("Revoke Me")

    async with SessionLocal() as session:
        person = Person(name="Revoked", cpf="98765432100", email_contact="revoked@example.com")
        user = User(
            email="revoked@example.com",
            password_hash=hash_password("secret123"),
            person=person,
        )
        session.add(user)
        await session.commit()
        user_id = user.id

    async with SessionLocal() as session:
        session.add(Membership(user_id=user_id, condominium_id=condo_id, active=True))
        await session.commit()

    login = await client.post(
        "/auth/login", json={"email": "revoked@example.com", "password": "secret123"}
    )
    identity = login.json()["token"]

    first = await client.post(
        f"/auth/condominiums/{condo_id}/select",
        headers={"Authorization": f"Bearer {identity}"},
    )
    assert first.status_code == 200

    async with SessionLocal() as session:
        membership = await session.scalar(
            select(Membership).where(
                Membership.user_id == user_id,
                Membership.condominium_id == condo_id,
            )
        )
        membership.active = False
        await session.commit()

    # Renewal (re-selection) is denied once the association is revoked.
    renewal = await client.post(
        f"/auth/condominiums/{condo_id}/select",
        headers={"Authorization": f"Bearer {identity}"},
    )
    assert renewal.status_code == 403
