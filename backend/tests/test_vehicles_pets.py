"""Integration tests for vehicles and pets (vehicles-pets spec, chapter 8).

Covers: resident self-service (own records only), síndico/administrator
whole-condominium management, resident-belongs-to-scope rule, unique plate per
condominium and pets linked to the resident.
"""

import itertools

import pytest
from conftest import ADMIN_EMAIL, ADMIN_PASSWORD
from httpx import AsyncClient

from tests.helpers import (
    bearer,
    create_condominium_api,
    create_person_user,
    login_identity,
    role_scoped_token,
    select_scoped,
)

_resident_counter = itertools.count(1)


async def condo_and_sindico(client: AsyncClient, name: str = "VP Condo") -> tuple[int, str]:
    admin = await login_identity(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    condominium = await create_condominium_api(client, admin, name)
    sindico = await role_scoped_token(
        client, condominium["id"], "sindico", "sindico-vp@example.com"
    )
    return condominium["id"], sindico


async def make_resident(
    client: AsyncClient,
    condo_id: int,
    sindico: str,
    name: str,
    role: str = "condomino",
) -> tuple[str, int, int]:
    """Create a person+user with a unit link; return (scoped token, person_id, unit_id)."""
    local = name.lower().replace(" ", "-")
    unique_email = f"{local}-{next(_resident_counter)}@example.com"
    person_id, _ = await create_person_user(email=unique_email, name=name)
    unit = (
        await client.post(
            "/units",
            headers=bearer(sindico),
            json={"number": name.replace(" ", ""), "fraction": "5"},
        )
    ).json()
    response = await client.post(
        f"/residents/{person_id}/links",
        headers=bearer(sindico),
        json={"role": role, "unit_id": unit["id"]},
    )
    assert response.status_code == 201, response.text
    identity = await login_identity(client, unique_email, "secret123")
    token = await select_scoped(client, identity, condo_id)
    return token, person_id, unit["id"]


@pytest.fixture
async def vp_scope(client: AsyncClient) -> tuple[int, str]:
    return await condo_and_sindico(client)


# --- Vehicle self-service ---


@pytest.mark.asyncio
async def test_resident_registers_own_vehicle(
    client: AsyncClient, vp_scope: tuple[int, str]
) -> None:
    condo_id, sindico = vp_scope
    resident, person_id, unit_id = await make_resident(client, condo_id, sindico, "Ana")

    created = await client.post(
        "/vehicles",
        headers=bearer(resident),
        json={"plate": "abc1d23", "model": "Sedan", "color": "Blue", "unit_id": unit_id},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["plate"] == "ABC1D23"  # normalized
    assert body["resident_id"] == person_id
    assert body["resident_name"] == "Ana"

    # A resident must be linked to the unit they register against.
    blocked = await client.post(
        "/vehicles",
        headers=bearer(resident),
        json={"plate": "XYZ9A88", "model": "Car", "unit_id": 999999},
    )
    assert blocked.status_code == 403


@pytest.mark.asyncio
async def test_resident_cannot_touch_another_person_vehicle(
    client: AsyncClient, vp_scope: tuple[int, str]
) -> None:
    condo_id, sindico = vp_scope
    ana, ana_id, ana_unit = await make_resident(client, condo_id, sindico, "Ana")
    bruno, _, bruno_unit = await make_resident(client, condo_id, sindico, "Bruno")

    created = (
        await client.post(
            "/vehicles",
            headers=bearer(ana),
            json={"plate": "ABC2D34", "model": "Hatch", "unit_id": ana_unit},
        )
    ).json()

    listing = await client.get("/vehicles", headers=bearer(bruno))
    assert any(v["id"] == created["id"] for v in listing.json()) is False

    edit = await client.patch(
        f"/vehicles/{created['id']}",
        headers=bearer(bruno),
        json={"model": "Stolen"},
    )
    assert edit.status_code == 403

    delete = await client.delete(f"/vehicles/{created['id']}", headers=bearer(bruno))
    assert delete.status_code == 403


@pytest.mark.asyncio
async def test_duplicate_plate_per_condominium(
    client: AsyncClient, vp_scope: tuple[int, str]
) -> None:
    condo_id, sindico = vp_scope
    ana, _, ana_unit = await make_resident(client, condo_id, sindico, "Ana")
    bruno, _, bruno_unit = await make_resident(client, condo_id, sindico, "Bruno")

    first = await client.post(
        "/vehicles",
        headers=bearer(ana),
        json={"plate": "ABC3D45", "model": "One", "unit_id": ana_unit},
    )
    assert first.status_code == 201
    duplicate = await client.post(
        "/vehicles",
        headers=bearer(bruno),
        json={"plate": "ABC3D45", "model": "Two", "unit_id": bruno_unit},
    )
    assert duplicate.status_code == 409


@pytest.mark.asyncio
async def test_same_plate_allowed_in_another_condominium(client: AsyncClient) -> None:
    condo_a, sindico_a = await condo_and_sindico(client, "Plate A")
    ana, _, ana_unit = await make_resident(client, condo_a, sindico_a, "Ana")

    condo_b, sindico_b = await condo_and_sindico(client, "Plate B")
    beto, _, beto_unit = await make_resident(client, condo_b, sindico_b, "Beto")

    first = await client.post(
        "/vehicles",
        headers=bearer(ana),
        json={"plate": "ABC4D56", "model": "One", "unit_id": ana_unit},
    )
    assert first.status_code == 201
    second = await client.post(
        "/vehicles",
        headers=bearer(beto),
        json={"plate": "ABC4D56", "model": "Two", "unit_id": beto_unit},
    )
    assert second.status_code == 201


# --- Síndico management ---


@pytest.mark.asyncio
async def test_sindico_registers_vehicle_for_any_resident(
    client: AsyncClient, vp_scope: tuple[int, str]
) -> None:
    condo_id, sindico = vp_scope
    _, person_id, _ = await make_resident(client, condo_id, sindico, "Ana")
    unit = (await client.get("/units", headers=bearer(sindico))).json()[0]

    created = await client.post(
        "/vehicles",
        headers=bearer(sindico),
        json={
            "plate": "ABC5D67",
            "model": "SUV",
            "resident_id": person_id,
            "unit_id": unit["id"],
        },
    )
    assert created.status_code == 201, created.text

    missing_ids = await client.post(
        "/vehicles",
        headers=bearer(sindico),
        json={"plate": "ABC6D78", "model": "No IDs"},
    )
    assert missing_ids.status_code == 422


@pytest.mark.asyncio
async def test_sindico_cannot_register_for_outsider(
    client: AsyncClient, vp_scope: tuple[int, str]
) -> None:
    condo_id, sindico = vp_scope
    outsider, _ = await create_person_user(email=f"outsider-{condo_id}@example.com")
    unit = (
        await client.post(
            "/units",
            headers=bearer(sindico),
            json={"number": "OS1", "fraction": "5"},
        )
    ).json()

    response = await client.post(
        "/vehicles",
        headers=bearer(sindico),
        json={
            "plate": "ABC7D89",
            "model": "Van",
            "resident_id": outsider,
            "unit_id": unit["id"],
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_conselho_reads_but_cannot_create(
    client: AsyncClient, vp_scope: tuple[int, str]
) -> None:
    condo_id, sindico = vp_scope
    ana, _, ana_unit = await make_resident(client, condo_id, sindico, "Ana")
    await client.post(
        "/vehicles",
        headers=bearer(ana),
        json={"plate": "ABC8D90", "model": "One", "unit_id": ana_unit},
    )

    conselho = await role_scoped_token(client, condo_id, "conselho", "conselho-vp@example.com")
    listing = await client.get("/vehicles", headers=bearer(conselho))
    assert listing.status_code == 200
    assert len(listing.json()) == 1  # síndico/conselho see the whole condominium

    creation = await client.post(
        "/vehicles", headers=bearer(conselho), json={"plate": "ABC9E01", "model": "No"}
    )
    assert creation.status_code == 403


# --- Pets ---


@pytest.mark.asyncio
async def test_resident_pet_self_service(client: AsyncClient, vp_scope: tuple[int, str]) -> None:
    condo_id, sindico = vp_scope
    ana, ana_id, _ = await make_resident(client, condo_id, sindico, "Ana")
    bruno, _, _ = await make_resident(client, condo_id, sindico, "Bruno")

    created = await client.post(
        "/pets",
        headers=bearer(ana),
        json={"name": "Rex", "species": "dog", "breed": "Golden"},
    )
    assert created.status_code == 201, created.text
    assert created.json()["resident_id"] == ana_id

    updated = await client.patch(
        f"/pets/{created.json()['id']}",
        headers=bearer(ana),
        json={"name": "Rex II"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Rex II"

    # Ana sees only her own pet; Bruno cannot edit it.
    ana_listing = await client.get("/pets", headers=bearer(ana))
    assert len(ana_listing.json()) == 1
    edit = await client.patch(
        f"/pets/{created.json()['id']}",
        headers=bearer(bruno),
        json={"name": "Mine Now"},
    )
    assert edit.status_code == 403


@pytest.mark.asyncio
async def test_sindico_registers_pet_for_resident(
    client: AsyncClient, vp_scope: tuple[int, str]
) -> None:
    condo_id, sindico = vp_scope
    _, person_id, _ = await make_resident(client, condo_id, sindico, "Ana")

    created = await client.post(
        "/pets",
        headers=bearer(sindico),
        json={"name": "Miau", "species": "cat", "resident_id": person_id},
    )
    assert created.status_code == 201, created.text
    assert created.json()["resident_name"] == "Ana"
