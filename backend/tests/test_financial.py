"""Integration tests for financial record-keeping (financial spec, chapter 10).

Covers: configurable chart of accounts, expense/income entries, ideal-fraction
allocation, monthly invoice generation, manual payments (paid/pending/overdue)
and the balance sheet (síndico full, resident own-unit only). Record-keeping
only — no charge execution is ever triggered.
"""

from decimal import Decimal

import pytest
from conftest import ADMIN_EMAIL, ADMIN_PASSWORD
from httpx import AsyncClient
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import EntryAllocation, Invoice, Payment
from tests.helpers import (
    bearer,
    create_condominium_api,
    create_person_user,
    login_identity,
    role_scoped_token,
    select_scoped,
)


async def fin_scope(client: AsyncClient) -> tuple[int, str, str, int, int, int]:
    """Return (condo_id, sindico, resident token, resident person_id, unit A, unit B)."""
    admin = await login_identity(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    condominium = await create_condominium_api(client, admin, "Finance Condo")
    sindico = await role_scoped_token(
        client, condominium["id"], "sindico", "sindico-fin@example.com"
    )
    unit_a = (
        await client.post(
            "/units",
            headers=bearer(sindico),
            json={"number": "F1", "fraction": "60"},
        )
    ).json()
    unit_b = (
        await client.post(
            "/units",
            headers=bearer(sindico),
            json={"number": "F2", "fraction": "40"},
        )
    ).json()
    person_id, _ = await create_person_user(email=f"owner-fin-{condominium['id']}@example.com")
    link = await client.post(
        f"/residents/{person_id}/links",
        headers=bearer(sindico),
        json={"role": "condomino", "unit_id": unit_a["id"]},
    )
    assert link.status_code == 201, link.text
    identity = await login_identity(
        client, f"owner-fin-{condominium['id']}@example.com", "secret123"
    )
    resident = await select_scoped(client, identity, condominium["id"])
    return condominium["id"], sindico, resident, person_id, unit_a["id"], unit_b["id"]


async def category_id(client: AsyncClient, sindico: str, name: str, kind: str) -> int:
    """Return the category id — reusing the seeded catalog when present."""
    listing = (await client.get("/chart-accounts", headers=bearer(sindico))).json()
    for entry in listing:
        if entry["name"] == name:
            return entry["id"]
    response = await client.post(
        "/chart-accounts",
        headers=bearer(sindico),
        json={"name": name, "kind": kind},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.fixture
async def fin_ctx(client: AsyncClient) -> tuple[int, str, str, int, int, int]:
    return await fin_scope(client)


# --- Chart of accounts (10.1) ---


@pytest.mark.asyncio
async def test_chart_accounts_configurable_per_condominium(
    client: AsyncClient, fin_ctx: tuple[int, str, str, int, int, int]
) -> None:
    _, sindico, _, _, _, _ = fin_ctx
    await category_id(client, sindico, "repairs", "expense")

    duplicate = await client.post(
        "/chart-accounts",
        headers=bearer(sindico),
        json={"name": "repairs", "kind": "expense"},
    )
    assert duplicate.status_code == 409

    listing = await client.get("/chart-accounts", headers=bearer(sindico))
    kinds = {entry["name"]: entry["kind"] for entry in listing.json()}
    # Suggested categories seeded at condominium creation are present.
    assert kinds["maintenance"] == "expense"
    assert kinds["extra fees"] == "income"
    assert kinds["repairs"] == "expense"


@pytest.mark.asyncio
async def test_resident_cannot_alter_chart(
    client: AsyncClient, fin_ctx: tuple[int, str, str, int, int, int]
) -> None:
    _, _, resident, _, _, _ = fin_ctx
    response = await client.post(
        "/chart-accounts",
        headers=bearer(resident),
        json={"name": "hijack", "kind": "expense"},
    )
    assert response.status_code == 403


# --- Entries and allocation (10.2, 10.3) ---


@pytest.mark.asyncio
async def test_expense_entry_allocated_by_ideal_fraction(
    client: AsyncClient, fin_ctx: tuple[int, str, str, int, int, int]
) -> None:
    _, sindico, _, _, unit_a, unit_b = fin_ctx
    maintenance = await category_id(client, sindico, "maintenance", "expense")

    created = await client.post(
        "/entries",
        headers=bearer(sindico),
        json={
            "date": "2026-10-05",
            "amount": "100.00",
            "category_id": maintenance,
            "kind": "expense",
            "description": "Pipes",
        },
    )
    assert created.status_code == 201, created.text

    async with SessionLocal() as session:
        allocations = (
            await session.scalars(
                select(EntryAllocation).where(EntryAllocation.entry_id == created.json()["id"])
            )
        ).all()
        total = (
            await session.scalar(
                select(func.sum(EntryAllocation.amount)).where(
                    EntryAllocation.entry_id == created.json()["id"]
                )
            )
        ) or 0
    by_unit = {a.unit_id: a.amount for a in allocations}
    assert by_unit[unit_a] == Decimal("60.00")
    assert by_unit[unit_b] == Decimal("40.00")
    assert Decimal(total) == Decimal("100.00")


@pytest.mark.asyncio
async def test_income_entry_has_no_allocations(
    client: AsyncClient, fin_ctx: tuple[int, str, str, int, int, int]
) -> None:
    _, sindico, _, _, _, _ = fin_ctx
    income = await category_id(client, sindico, "extra fees", "income")

    created = await client.post(
        "/entries",
        headers=bearer(sindico),
        json={
            "date": "2026-10-06",
            "amount": "10.00",
            "category_id": income,
            "kind": "income",
            "description": "Late fee",
        },
    )
    assert created.status_code == 201, created.text

    async with SessionLocal() as session:
        count = (
            await session.scalar(
                select(func.count())
                .select_from(EntryAllocation)
                .where(EntryAllocation.entry_id == created.json()["id"])
            )
        ) or 0
    assert count == 0


@pytest.mark.asyncio
async def test_entry_kind_must_match_category(
    client: AsyncClient, fin_ctx: tuple[int, str, str, int, int, int]
) -> None:
    _, sindico, _, _, _, _ = fin_ctx
    maintenance = await category_id(client, sindico, "maintenance", "expense")

    mismatch = await client.post(
        "/entries",
        headers=bearer(sindico),
        json={
            "date": "2026-10-07",
            "amount": "5.00",
            "category_id": maintenance,
            "kind": "income",
        },
    )
    assert mismatch.status_code == 422


@pytest.mark.asyncio
async def test_resident_cannot_create_entries(
    client: AsyncClient, fin_ctx: tuple[int, str, str, int, int, int]
) -> None:
    _, sindico, resident, _, _, _ = fin_ctx
    maintenance = await category_id(client, sindico, "maintenance", "expense")

    response = await client.post(
        "/entries",
        headers=bearer(resident),
        json={
            "date": "2026-10-08",
            "amount": "1.00",
            "category_id": maintenance,
            "kind": "expense",
        },
    )
    assert response.status_code == 403


# --- Invoices (10.3) ---


@pytest.mark.asyncio
async def test_monthly_invoices_reflect_allocation_and_credits(
    client: AsyncClient, fin_ctx: tuple[int, str, str, int, int, int]
) -> None:
    _, sindico, _, _, unit_a, unit_b = fin_ctx
    maintenance = await category_id(client, sindico, "maintenance", "expense")
    income = await category_id(client, sindico, "extra fees", "income")

    await client.post(
        "/entries",
        headers=bearer(sindico),
        json={
            "date": "2026-10-05",
            "amount": "100.00",
            "category_id": maintenance,
            "kind": "expense",
        },
    )
    await client.post(
        "/entries",
        headers=bearer(sindico),
        json={"date": "2026-10-06", "amount": "10.00", "category_id": income, "kind": "income"},
    )

    generated = await client.post(
        "/invoices/generate",
        headers=bearer(sindico),
        json={"period": "2026-10"},
    )
    assert generated.status_code == 200, generated.text
    invoices = {inv["unit_id"]: inv for inv in generated.json()}
    # Unit A: 60 (allocation) - 6 (credit share) = 54; Unit B: 40 - 4 = 36.
    assert invoices[unit_a]["amount"] == "54.00"
    assert invoices[unit_b]["amount"] == "36.00"
    assert invoices[unit_a]["status"] == "pending"
    assert invoices[unit_a]["due_date"] == "2026-11-10"  # 10th of next month

    # Regeneration is idempotent (same amounts, no duplicates).
    again = await client.post(
        "/invoices/generate",
        headers=bearer(sindico),
        json={"period": "2026-10"},
    )
    assert again.status_code == 200
    async with SessionLocal() as session:
        rows = (await session.scalars(select(Invoice).where(Invoice.period == "2026-10"))).all()
    assert len(rows) == 2


# --- Manual payments (10.4) ---


@pytest.mark.asyncio
async def test_payment_recording_flips_status_to_paid(
    client: AsyncClient, fin_ctx: tuple[int, str, str, int, int, int]
) -> None:
    _, sindico, _, _, unit_a, _ = fin_ctx
    maintenance = await category_id(client, sindico, "maintenance", "expense")
    await client.post(
        "/entries",
        headers=bearer(sindico),
        json={
            "date": "2026-10-05",
            "amount": "100.00",
            "category_id": maintenance,
            "kind": "expense",
        },
    )
    invoices = (
        await client.post("/invoices/generate", headers=bearer(sindico), json={"period": "2026-10"})
    ).json()
    invoice = next(inv for inv in invoices if inv["unit_id"] == unit_a)

    payment = await client.post(
        f"/invoices/{invoice['id']}/payments",
        headers=bearer(sindico),
        json={"amount": "60.00"},
    )
    assert payment.status_code == 201, payment.text

    async with SessionLocal() as session:
        db_invoice = await session.get(Invoice, invoice["id"])
        db_payments = (
            await session.scalars(select(Payment).where(Payment.invoice_id == invoice["id"]))
        ).all()
    assert db_invoice.status == "paid", (
        f"db status={db_invoice.status} payments={[(p.amount, p.paid_at) for p in db_payments]}"
    )

    listing = await client.get("/invoices", headers=bearer(sindico))
    paid = next(inv for inv in listing.json() if inv["unit_id"] == unit_a)
    assert paid["status"] == "paid"
    assert paid["paid"] == "60.00"


@pytest.mark.asyncio
async def test_pending_becomes_overdue_after_due_date(
    client: AsyncClient, fin_ctx: tuple[int, str, str, int, int, int]
) -> None:
    _, sindico, _, _, unit_a, _ = fin_ctx
    maintenance = await category_id(client, sindico, "maintenance", "expense")
    await client.post(
        "/entries",
        headers=bearer(sindico),
        json={
            "date": "2020-01-05",
            "amount": "100.00",
            "category_id": maintenance,
            "kind": "expense",
        },
    )
    invoices = (
        await client.post("/invoices/generate", headers=bearer(sindico), json={"period": "2020-01"})
    ).json()
    overdue = next(inv for inv in invoices if inv["unit_id"] == unit_a)
    assert overdue["due_date"] == "2020-02-10"
    assert overdue["status"] == "overdue"


# --- Balance sheet (10.5) ---


@pytest.mark.asyncio
async def test_balance_sheet_for_sindico_and_conselho(
    client: AsyncClient, fin_ctx: tuple[int, str, str, int, int, int]
) -> None:
    condo_id, sindico, _, _, unit_a, unit_b = fin_ctx
    maintenance = await category_id(client, sindico, "maintenance", "expense")
    income = await category_id(client, sindico, "extra fees", "income")
    await client.post(
        "/entries",
        headers=bearer(sindico),
        json={
            "date": "2026-10-05",
            "amount": "100.00",
            "category_id": maintenance,
            "kind": "expense",
        },
    )
    await client.post(
        "/entries",
        headers=bearer(sindico),
        json={"date": "2026-10-06", "amount": "10.00", "category_id": income, "kind": "income"},
    )
    await client.post("/invoices/generate", headers=bearer(sindico), json={"period": "2026-10"})

    sheet = (await client.get("/balance-sheet?period=2026-10", headers=bearer(sindico))).json()
    assert sheet["expenses_by_category"] == [{"category": "maintenance", "amount": "100.00"}]
    assert sheet["incomes_by_category"] == [{"category": "extra fees", "amount": "10.00"}]
    assert sheet["result"] == "-90.00"
    by_unit = {entry["unit_id"]: entry for entry in sheet["per_unit"]}
    assert len(by_unit) == 2
    assert by_unit[unit_a]["billed"] == "54.00"
    assert by_unit[unit_a]["pending"] == "54.00"
    assert by_unit[unit_b]["billed"] == "36.00"

    # Conselho may read the balance sheet (read-only permission).
    conselho = await role_scoped_token(client, condo_id, "conselho", "conselho-fin@example.com")
    conselho_view = await client.get("/balance-sheet?period=2026-10", headers=bearer(conselho))
    assert conselho_view.status_code == 200


@pytest.mark.asyncio
async def test_resident_sees_only_own_unit(
    client: AsyncClient, fin_ctx: tuple[int, str, str, int, int, int]
) -> None:
    _, sindico, resident, _, unit_a, _ = fin_ctx
    maintenance = await category_id(client, sindico, "maintenance", "expense")
    await client.post(
        "/entries",
        headers=bearer(sindico),
        json={
            "date": "2026-10-05",
            "amount": "100.00",
            "category_id": maintenance,
            "kind": "expense",
        },
    )
    await client.post("/invoices/generate", headers=bearer(sindico), json={"period": "2026-10"})

    sheet = (await client.get("/balance-sheet?period=2026-10", headers=bearer(resident))).json()
    assert sheet["per_unit"] == [
        {
            "unit_id": unit_a,
            "unit_code": "F1",
            "billed": "60.00",
            "paid": "0.00",
            "pending": "60.00",
            "delinquent": "0.00",
        }
    ]
    # Condo-wide breakdown is hidden from residents.
    assert sheet["expenses_by_category"] == []
    assert sheet["result"] == "0.00"


@pytest.mark.asyncio
async def test_invoices_scope_for_resident(
    client: AsyncClient, fin_ctx: tuple[int, str, str, int, int, int]
) -> None:
    _, sindico, resident, _, unit_a, _ = fin_ctx
    maintenance = await category_id(client, sindico, "maintenance", "expense")
    await client.post(
        "/entries",
        headers=bearer(sindico),
        json={
            "date": "2026-10-05",
            "amount": "100.00",
            "category_id": maintenance,
            "kind": "expense",
        },
    )
    await client.post("/invoices/generate", headers=bearer(sindico), json={"period": "2026-10"})

    listing = await client.get("/invoices", headers=bearer(resident))
    assert [inv["unit_id"] for inv in listing.json()] == [unit_a]
