"""Integration tests for common areas and bookings (chapter 9).

Covers: area registration by síndico/admin, resident self-service booking,
atomic overlap rejection (exclusion constraint), end-before-start validation,
cancellation freeing the slot, and booking scope rules.
"""

from datetime import UTC, datetime, timedelta

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

TZ = UTC


async def condo_sindico_resident(
    client: AsyncClient, name: str = "Booking Condo"
) -> tuple[int, str, str, int, int]:
    """Return (condo_id, sindico token, resident token, resident person_id, unit_id)."""
    admin = await login_identity(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    condominium = await create_condominium_api(client, admin, name)
    sindico = await role_scoped_token(
        client, condominium["id"], "sindico", "sindico-book@example.com"
    )
    person_id, _ = await create_person_user(email=f"resident-{condominium['id']}@example.com")
    unit = (
        await client.post(
            "/units",
            headers=bearer(sindico),
            json={"number": "B1", "fraction": "10"},
        )
    ).json()
    link = await client.post(
        f"/residents/{person_id}/links",
        headers=bearer(sindico),
        json={"role": "condomino", "unit_id": unit["id"]},
    )
    assert link.status_code == 201, link.text
    residency = await login_identity(
        client, f"resident-{condominium['id']}@example.com", "secret123"
    )
    resident = await select_scoped(client, residency, condominium["id"])
    return condominium["id"], sindico, resident, person_id, unit["id"]


async def make_area(client: AsyncClient, sindico: str, name: str = "Party Room") -> dict:
    response = await client.post(
        "/common-areas",
        headers=bearer(sindico),
        json={"name": name, "description": "For events", "capacity": 30},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
async def bkg_scope(
    client: AsyncClient,
) -> tuple[int, str, str, int, int]:
    return await condo_sindico_resident(client)


# --- Common areas ---


@pytest.mark.asyncio
async def test_sindico_registers_common_area(
    client: AsyncClient, bkg_scope: tuple[int, str, str, int, int]
) -> None:
    _, sindico, _, _, _ = bkg_scope
    area = await make_area(client, sindico, "Swimming Pool")
    assert area["name"] == "Swimming Pool"
    assert area["capacity"] == 30


@pytest.mark.asyncio
async def test_resident_lists_areas_but_cannot_register(
    client: AsyncClient, bkg_scope: tuple[int, str, str, int, int]
) -> None:
    _, sindico, resident, _, _ = bkg_scope
    await make_area(client, sindico)

    listing = await client.get("/common-areas", headers=bearer(resident))
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    creation = await client.post(
        "/common-areas",
        headers=bearer(resident),
        json={"name": "Hijacked Area"},
    )
    assert creation.status_code == 403


# --- Bookings ---


@pytest.mark.asyncio
async def test_resident_books_free_slot(
    client: AsyncClient, bkg_scope: tuple[int, str, str, int, int]
) -> None:
    _, sindico, resident, person_id, unit_id = bkg_scope
    area = await make_area(client, sindico)

    start = datetime(2026, 10, 1, 18, 0, tzinfo=TZ)
    response = await client.post(
        "/bookings",
        headers=bearer(resident),
        json={
            "area_id": area["id"],
            "start_at": start.isoformat(),
            "end_at": (start + timedelta(hours=2)).isoformat(),
            "unit_id": unit_id,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "reserved"
    assert body["person_id"] == person_id
    assert body["area_name"] == "Party Room"


@pytest.mark.asyncio
async def test_overlap_rejected_atomically(
    client: AsyncClient, bkg_scope: tuple[int, str, str, int, int]
) -> None:
    _, sindico, resident, _, unit_id = bkg_scope
    area = await make_area(client, sindico)

    start = datetime(2026, 10, 2, 18, 0, tzinfo=TZ)
    first = await client.post(
        "/bookings",
        headers=bearer(resident),
        json={
            "area_id": area["id"],
            "start_at": start.isoformat(),
            "end_at": (start + timedelta(hours=2)).isoformat(),
            "unit_id": unit_id,
        },
    )
    assert first.status_code == 201

    # Partially overlapping slot in the same area is rejected.
    overlap = await client.post(
        "/bookings",
        headers=bearer(resident),
        json={
            "area_id": area["id"],
            "start_at": (start + timedelta(hours=1)).isoformat(),
            "end_at": (start + timedelta(hours=3)).isoformat(),
            "unit_id": unit_id,
        },
    )
    assert overlap.status_code == 409

    # A different, later slot is accepted.
    later = await client.post(
        "/bookings",
        headers=bearer(resident),
        json={
            "area_id": area["id"],
            "start_at": (start + timedelta(days=1)).isoformat(),
            "end_at": (start + timedelta(days=1, hours=1)).isoformat(),
            "unit_id": unit_id,
        },
    )
    assert later.status_code == 201


@pytest.mark.asyncio
async def test_end_before_start_rejected(
    client: AsyncClient, bkg_scope: tuple[int, str, str, int, int]
) -> None:
    _, sindico, resident, _, unit_id = bkg_scope
    area = await make_area(client, sindico)

    start = datetime(2026, 10, 3, 18, 0, tzinfo=TZ)
    response = await client.post(
        "/bookings",
        headers=bearer(resident),
        json={
            "area_id": area["id"],
            "start_at": start.isoformat(),
            "end_at": (start - timedelta(hours=1)).isoformat(),
            "unit_id": unit_id,
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_resident_cannot_book_foreign_unit(
    client: AsyncClient, bkg_scope: tuple[int, str, str, int, int]
) -> None:
    _, sindico, resident, _, _ = bkg_scope
    area = await make_area(client, sindico)
    # A unit the resident is NOT linked to.
    foreign_unit = (
        await client.post(
            "/units",
            headers=bearer(sindico),
            json={"number": "B2", "fraction": "10"},
        )
    ).json()

    start = datetime(2026, 10, 4, 18, 0, tzinfo=TZ)
    blocked = await client.post(
        "/bookings",
        headers=bearer(resident),
        json={
            "area_id": area["id"],
            "start_at": start.isoformat(),
            "end_at": (start + timedelta(hours=1)).isoformat(),
            "unit_id": foreign_unit["id"],
        },
    )
    assert blocked.status_code == 403


@pytest.mark.asyncio
async def test_sindico_cannot_book_for_outsider(
    client: AsyncClient, bkg_scope: tuple[int, str, str, int, int]
) -> None:
    condo_id, sindico, _, _, unit_id = bkg_scope
    area = await make_area(client, sindico)
    outsider, _ = await create_person_user(email=f"outsider-{condo_id}@example.com")

    start = datetime(2026, 10, 4, 20, 0, tzinfo=TZ)
    response = await client.post(
        "/bookings",
        headers=bearer(sindico),
        json={
            "area_id": area["id"],
            "start_at": start.isoformat(),
            "end_at": (start + timedelta(hours=1)).isoformat(),
            "unit_id": unit_id,
            "person_id": outsider,
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cancellation_frees_the_slot(
    client: AsyncClient, bkg_scope: tuple[int, str, str, int, int]
) -> None:
    _, sindico, resident, _, unit_id = bkg_scope
    area = await make_area(client, sindico)

    start = datetime(2026, 10, 5, 18, 0, tzinfo=TZ)
    booking = (
        await client.post(
            "/bookings",
            headers=bearer(resident),
            json={
                "area_id": area["id"],
                "start_at": start.isoformat(),
                "end_at": (start + timedelta(hours=2)).isoformat(),
                "unit_id": unit_id,
            },
        )
    ).json()

    cancelled = await client.post(f"/bookings/{booking['id']}/cancel", headers=bearer(resident))
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    # The same slot can be booked again once cancelled.
    rebooked = await client.post(
        "/bookings",
        headers=bearer(resident),
        json={
            "area_id": area["id"],
            "start_at": start.isoformat(),
            "end_at": (start + timedelta(hours=2)).isoformat(),
            "unit_id": unit_id,
        },
    )
    assert rebooked.status_code == 201


@pytest.mark.asyncio
async def test_only_owner_or_sindico_cancels(
    client: AsyncClient, bkg_scope: tuple[int, str, str, int, int]
) -> None:
    condo_id, sindico, resident, _, unit_id = bkg_scope
    area = await make_area(client, sindico)
    start = datetime(2026, 10, 6, 18, 0, tzinfo=TZ)
    booking = (
        await client.post(
            "/bookings",
            headers=bearer(resident),
            json={
                "area_id": area["id"],
                "start_at": start.isoformat(),
                "end_at": (start + timedelta(hours=1)).isoformat(),
                "unit_id": unit_id,
            },
        )
    ).json()

    # Another resident cannot cancel it.
    other_person, _ = await create_person_user(email=f"other-{condo_id}@example.com", name="Other")
    other_unit = (
        await client.post(
            "/units", headers=bearer(sindico), json={"number": "B9", "fraction": "10"}
        )
    ).json()
    await client.post(
        f"/residents/{other_person}/links",
        headers=bearer(sindico),
        json={"role": "condomino", "unit_id": other_unit["id"]},
    )
    other_identity = await login_identity(client, f"other-{condo_id}@example.com", "secret123")
    other = await select_scoped(client, other_identity, condo_id)

    blocked = await client.post(f"/bookings/{booking['id']}/cancel", headers=bearer(other))
    assert blocked.status_code == 403

    # The síndico can cancel it.
    ok = await client.post(f"/bookings/{booking['id']}/cancel", headers=bearer(sindico))
    assert ok.status_code == 200
    assert ok.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_conselho_reads_but_cannot_book(
    client: AsyncClient, bkg_scope: tuple[int, str, str, int, int]
) -> None:
    condo_id, sindico, resident, _, unit_id = bkg_scope
    area = await make_area(client, sindico)
    start = datetime(2026, 10, 7, 18, 0, tzinfo=TZ)
    await client.post(
        "/bookings",
        headers=bearer(resident),
        json={
            "area_id": area["id"],
            "start_at": start.isoformat(),
            "end_at": (start + timedelta(hours=1)).isoformat(),
            "unit_id": unit_id,
        },
    )

    conselho = await role_scoped_token(client, condo_id, "conselho", "conselho-book@example.com")
    listing = await client.get("/bookings", headers=bearer(conselho))
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    creation = await client.post(
        "/bookings",
        headers=bearer(conselho),
        json={
            "area_id": area["id"],
            "start_at": (start + timedelta(days=1)).isoformat(),
            "end_at": (start + timedelta(days=1, hours=1)).isoformat(),
            "unit_id": unit_id,
        },
    )
    assert creation.status_code == 403
