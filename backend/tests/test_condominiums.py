"""Integration tests for condominium CRUD and associations
(condominium-management spec, chapter 5)."""

import jwt
import pytest
from conftest import ADMIN_EMAIL, ADMIN_PASSWORD
from httpx import AsyncClient
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import AccountCategory, Condominium, Membership
from tests.helpers import (
    bearer,
    create_condominium_api,
    create_person_user,
    login_identity,
    select_scoped,
)

SECRET = get_settings().jwt_secret
ALGORITHM = get_settings().jwt_algorithm


async def admin_identity(client: AsyncClient) -> str:
    return await login_identity(client, ADMIN_EMAIL, ADMIN_PASSWORD)


# --- CRUD ---


@pytest.mark.asyncio
async def test_admin_creates_condominium_with_categories(client: AsyncClient) -> None:
    identity = await admin_identity(client)
    created = await create_condominium_api(client, identity, "Lake Towers", "Av. das Águas, 100")
    assert created["name"] == "Lake Towers"
    assert created["active"] is True

    async with SessionLocal() as session:
        categories = (
            await session.scalars(
                select(AccountCategory).where(AccountCategory.condominium_id == created["id"])
            )
        ).all()
    assert len(categories) == 5  # suggested chart of accounts


@pytest.mark.asyncio
async def test_admin_lists_condominiums(client: AsyncClient) -> None:
    identity = await admin_identity(client)
    await create_condominium_api(client, identity, "Listing One")
    response = await client.get("/admin/condominiums", headers=bearer(identity))
    assert response.status_code == 200
    assert any(c["name"] == "Listing One" for c in response.json())


@pytest.mark.asyncio
async def test_update_condominium(client: AsyncClient) -> None:
    identity = await admin_identity(client)
    created = await create_condominium_api(client, identity, "Before Rename")
    scoped = await select_scoped(client, identity, created["id"])

    response = await client.patch(
        f"/admin/condominiums/{created['id']}",
        headers=bearer(scoped),
        json={"name": "After Rename", "address": "New Street, 5"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "After Rename"
    assert response.json()["address"] == "New Street, 5"


@pytest.mark.asyncio
async def test_deactivate_stops_listing_and_blocks_actions(
    client: AsyncClient,
) -> None:
    identity = await admin_identity(client)
    created = await create_condominium_api(client, identity, "To Deactivate")
    scoped = await select_scoped(client, identity, created["id"])

    response = await client.delete(f"/admin/condominiums/{created['id']}", headers=bearer(scoped))
    assert response.status_code == 204

    # Data preserved (still exists)…
    async with SessionLocal() as session:
        record = await session.get(Condominium, created["id"])
    assert record is not None
    assert record.active is False

    # …but no longer in the accessible listing, and selection is blocked.
    listing = await client.get("/auth/condominiums", headers=bearer(identity))
    assert all(c["id"] != created["id"] for c in listing.json())

    blocked = await client.post(
        f"/auth/condominiums/{created['id']}/select",
        headers=bearer(identity),
    )
    assert blocked.status_code == 403


@pytest.mark.asyncio
async def test_non_admin_cannot_create_condominium(client: AsyncClient) -> None:
    await create_person_user(email="notadmin@example.com")
    identity = await login_identity(client, "notadmin@example.com")

    response = await client.post(
        "/admin/condominiums",
        headers=bearer(identity),
        json={"name": "Sneaky Condo"},
    )
    assert response.status_code == 403


# --- Associations ---


@pytest.mark.asyncio
async def test_association_grants_listing_and_scope(client: AsyncClient) -> None:
    identity = await admin_identity(client)
    condominium = await create_condominium_api(client, identity, "Assoc Condo")
    scoped = await select_scoped(client, identity, condominium["id"])

    person_id, user_id = await create_person_user(email="member@example.com")

    response = await client.put(
        f"/admin/condominiums/{condominium['id']}/associations/{user_id}",
        headers=bearer(scoped),
        json={"active": True},
    )
    assert response.status_code == 200
    assert response.json()["active"] is True

    member_identity = await login_identity(client, "member@example.com")
    listing = await client.get("/auth/condominiums", headers=bearer(member_identity))
    assert any(c["id"] == condominium["id"] for c in listing.json())

    scoped_token = await select_scoped(client, member_identity, condominium["id"])
    payload = jwt.decode(scoped_token, SECRET, algorithms=[ALGORITHM])
    assert payload["condominium_id"] == condominium["id"]


@pytest.mark.asyncio
async def test_remove_association_revokes_access(client: AsyncClient) -> None:
    identity = await admin_identity(client)
    condominium = await create_condominium_api(client, identity, "Revoke Assoc")
    scoped = await select_scoped(client, identity, condominium["id"])

    _, user_id = await create_person_user(email="exmember@example.com")
    await client.put(
        f"/admin/condominiums/{condominium['id']}/associations/{user_id}",
        headers=bearer(scoped),
        json={"active": True},
    )

    member_identity = await login_identity(client, "exmember@example.com")
    before = await select_scoped(client, member_identity, condominium["id"])

    removed = await client.delete(
        f"/admin/condominiums/{condominium['id']}/associations/{user_id}",
        headers=bearer(scoped),
    )
    assert removed.status_code == 204

    async with SessionLocal() as session:
        membership = await session.scalar(select(Membership).where(Membership.user_id == user_id))
    assert membership is None

    # The user no longer sees it and renewal is refused.
    listing = await client.get("/auth/condominiums", headers=bearer(member_identity))
    assert all(c["id"] != condominium["id"] for c in listing.json())

    renewal = await client.post(
        f"/auth/condominiums/{condominium['id']}/select",
        headers=bearer(member_identity),
    )
    assert renewal.status_code == 403

    # An already-issued scoped token is blocked by the per-request check.
    data_route = await client.get(
        f"/admin/condominiums/{condominium['id']}/roles",
        headers=bearer(before),
    )
    assert data_route.status_code == 403


@pytest.mark.asyncio
async def test_non_admin_cannot_manage_associations(client: AsyncClient) -> None:
    identity = await admin_identity(client)
    condominium = await create_condominium_api(client, identity, "Assoc Guard")

    _, user_id = await create_person_user(email="operator@example.com")
    async with SessionLocal() as session:
        session.add(Membership(user_id=user_id, condominium_id=condominium["id"], active=True))
        await session.commit()

    operator_identity = await login_identity(client, "operator@example.com")
    scoped = await select_scoped(client, operator_identity, condominium["id"])

    response = await client.put(
        f"/admin/condominiums/{condominium['id']}/associations/1",
        headers=bearer(scoped),
        json={"active": True},
    )
    assert response.status_code == 403
