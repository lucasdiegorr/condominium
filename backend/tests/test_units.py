"""Integration tests for units and parking spots (unit-management spec, chapter 7)."""

import pytest
from conftest import ADMIN_EMAIL, ADMIN_PASSWORD
from httpx import AsyncClient

from app.db import SessionLocal
from app.models import Vehicle
from tests.helpers import (
    bearer,
    create_condominium_api,
    create_person_user,
    login_identity,
    role_scoped_token,
)


async def unit_scope(client: AsyncClient) -> tuple[int, str]:
    identity = await login_identity(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    condominium = await create_condominium_api(client, identity, "Units Condo")
    sindico = await role_scoped_token(
        client, condominium["id"], "sindico", "sindico-units@example.com"
    )
    return condominium["id"], sindico


async def create_unit_api(
    client: AsyncClient, token: str, number: str, fraction: str, block: str | None = None
) -> dict:
    response = await client.post(
        "/units",
        headers=bearer(token),
        json={"number": number, "block": block, "fraction": fraction},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
async def scope(client: AsyncClient) -> tuple[int, str]:
    return await unit_scope(client)


# --- CRUD ---


@pytest.mark.asyncio
async def test_sindico_creates_unit_with_block_code(
    client: AsyncClient, scope: tuple[int, str]
) -> None:
    condo_id, sindico = scope
    unit = await create_unit_api(client, sindico, "101", "20.000000", block="T")
    assert unit["code"] == "T-101"
    assert unit["unit_type"] == "apartment"
    assert unit["fraction"] == "20.000000"
    assert unit["active"] is True
    assert unit["parking_spots"] == []

    # The number alone produces a bare code.
    plain = await create_unit_api(client, sindico, "202", "10.000000")
    assert plain["code"] == "202"


@pytest.mark.asyncio
async def test_negative_and_zero_fraction_rejected(
    client: AsyncClient, scope: tuple[int, str]
) -> None:
    _, sindico = scope
    for fraction in ("0", "-5"):
        response = await client.post(
            "/units",
            headers=bearer(sindico),
            json={"number": "301", "fraction": fraction},
        )
        assert response.status_code == 422, (fraction, response.text)


@pytest.mark.asyncio
async def test_fraction_sum_cannot_exceed_100(client: AsyncClient, scope: tuple[int, str]) -> None:
    _, sindico = scope
    await create_unit_api(client, sindico, "401", "60.000000")
    await create_unit_api(client, sindico, "402", "40.000000")  # exactly 100

    over = await client.post(
        "/units",
        headers=bearer(sindico),
        json={"number": "403", "fraction": "0.000001"},
    )
    assert over.status_code == 422
    assert "100%" in over.json()["detail"]


@pytest.mark.asyncio
async def test_update_unit_revalidates_fraction(
    client: AsyncClient, scope: tuple[int, str]
) -> None:
    _, sindico = scope
    await create_unit_api(client, sindico, "501", "50.000000")
    other = await create_unit_api(client, sindico, "502", "50.000000")

    # Shrinking leaves room: other drops to 30, then first can grow to 70.
    ok = await client.patch(
        f"/units/{other['id']}",
        headers=bearer(sindico),
        json={"fraction": "30.000000"},
    )
    assert ok.status_code == 200

    first = (await client.get("/units", headers=bearer(sindico))).json()
    first_id = next(u["id"] for u in first if u["number"] == "501")
    grown = await client.patch(
        f"/units/{first_id}",
        headers=bearer(sindico),
        json={"fraction": "70.000000"},
    )
    assert grown.status_code == 200  # 70 + 30 = 100

    # Growing beyond the total is rejected.
    blocked = await client.patch(
        f"/units/{first_id}",
        headers=bearer(sindico),
        json={"fraction": "70.000001"},
    )
    assert blocked.status_code == 422


@pytest.mark.asyncio
async def test_duplicate_unit_code_rejected(client: AsyncClient, scope: tuple[int, str]) -> None:
    _, sindico = scope
    await create_unit_api(client, sindico, "601", "5.000000")
    response = await client.post(
        "/units",
        headers=bearer(sindico),
        json={"number": "601", "fraction": "5.000000"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_conselho_reads_but_cannot_create(
    client: AsyncClient, scope: tuple[int, str]
) -> None:
    condo_id, _ = scope
    conselho = await role_scoped_token(client, condo_id, "conselho", "conselho-units@example.com")
    listing = await client.get("/units", headers=bearer(conselho))
    assert listing.status_code == 200
    creation = await client.post(
        "/units",
        headers=bearer(conselho),
        json={"number": "701", "fraction": "5.000000"},
    )
    assert creation.status_code == 403


@pytest.mark.asyncio
async def test_delete_unit_blocked_when_vehicle_references(
    client: AsyncClient, scope: tuple[int, str]
) -> None:
    condo_id, sindico = scope
    unit = await create_unit_api(client, sindico, "801", "5.000000")
    person_id, _ = await create_person_user(email="car-owner@example.com")

    async with SessionLocal() as session:
        session.add(
            Vehicle(
                condominium_id=condo_id,
                plate="ABC1D23",
                model="Sedan",
                resident_id=person_id,
                unit_id=unit["id"],
            )
        )
        await session.commit()

    response = await client.delete(f"/units/{unit['id']}", headers=bearer(sindico))
    assert response.status_code == 409


# --- Parking spots ---


@pytest.mark.asyncio
async def test_parking_spot_creation_and_scoping(
    client: AsyncClient, scope: tuple[int, str]
) -> None:
    _, sindico = scope
    unit = await create_unit_api(client, sindico, "901", "5.000000")

    created = await client.post(
        f"/units/{unit['id']}/parking",
        headers=bearer(sindico),
        json={"identifier": "P-1", "spot_type": "covered"},
    )
    assert created.status_code == 201, created.text

    # The unit detail now shows the spot.
    detail = (await client.get(f"/units/{unit['id']}", headers=bearer(sindico))).json()
    assert any(spot["identifier"] == "P-1" for spot in detail["parking_spots"])

    # A unit of another condominium is out of scope (403).
    admin = await login_identity(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    other = await create_condominium_api(client, admin, "Foreign Units")
    foreign_unit = await create_unit_api(client, sindico, "111", "5.000000")
    foreign_scoped = await role_scoped_token(
        client, other["id"], "sindico", "sindico-foreign@example.com"
    )
    blocked = await client.post(
        f"/units/{foreign_unit['id']}/parking",  # foreign unit id, but token of `other`
        headers=bearer(foreign_scoped),
        json={"identifier": "P-F", "spot_type": "uncovered"},
    )
    assert blocked.status_code == 403


@pytest.mark.asyncio
async def test_duplicate_parking_identifier_rejected(
    client: AsyncClient, scope: tuple[int, str]
) -> None:
    _, sindico = scope
    unit = await create_unit_api(client, sindico, "1001", "5.000000")
    first = await client.post(
        f"/units/{unit['id']}/parking",
        headers=bearer(sindico),
        json={"identifier": "G-7", "spot_type": "uncovered"},
    )
    assert first.status_code == 201
    duplicate = await client.post(
        f"/units/{unit['id']}/parking",
        headers=bearer(sindico),
        json={"identifier": "G-7", "spot_type": "uncovered"},
    )
    assert duplicate.status_code == 409

    deleted = await client.delete(f"/units/parking/{first.json()['id']}", headers=bearer(sindico))
    assert deleted.status_code == 204
    listing = await client.get("/units/parking", headers=bearer(sindico))
    assert listing.json() == []
