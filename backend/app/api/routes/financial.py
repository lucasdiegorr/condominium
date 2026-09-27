"""Financial routes — entries, invoices, manual payments and balance sheet."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_any_permission, require_permission
from app.core.permissions import (
    PERM_BALANCE_SHEET_READ,
    PERM_FINANCIAL_MANAGE,
    PERM_FINANCIAL_READ,
    PERM_FINANCIAL_READ_OWN_UNIT,
    PERM_INVOICES_MANAGE_PAYMENTS,
)
from app.db import get_db
from app.schemas.financial import (
    BalanceSheet,
    EntryCreate,
    EntryView,
    InvoiceGenerate,
    InvoiceView,
    PaymentCreate,
    PaymentView,
)
from app.services import financial_service

router = APIRouter(tags=["financial"])


@router.get("/entries", response_model=list[EntryView])
async def list_entries(
    scope=Depends(require_permission(PERM_FINANCIAL_READ)),
    session: AsyncSession = Depends(get_db),
) -> list[EntryView]:
    return await financial_service.list_entries(session, scope)


@router.post("/entries", response_model=EntryView, status_code=201)
async def create_entry(
    body: EntryCreate,
    scope=Depends(require_permission(PERM_FINANCIAL_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> EntryView:
    return await financial_service.create_entry(
        session,
        scope,
        entry_date=body.date,
        amount=body.amount,
        category_id=body.category_id,
        kind=body.kind,
        description=body.description,
    )


@router.delete("/entries/{entry_id}", status_code=204)
async def delete_entry(
    entry_id: int,
    scope=Depends(require_permission(PERM_FINANCIAL_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> None:
    await financial_service.delete_entry(session, scope, entry_id)
    return None


@router.post("/invoices/generate", response_model=list[InvoiceView])
async def generate_invoices(
    body: InvoiceGenerate,
    scope=Depends(require_permission(PERM_FINANCIAL_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> list[InvoiceView]:
    return await financial_service.generate_invoices(session, scope, body.period)


@router.get("/invoices", response_model=list[InvoiceView])
async def list_invoices(
    scope=Depends(require_any_permission(PERM_FINANCIAL_READ, PERM_FINANCIAL_READ_OWN_UNIT)),
    session: AsyncSession = Depends(get_db),
) -> list[InvoiceView]:
    return await financial_service.list_invoices(session, scope)


@router.post("/invoices/{invoice_id}/payments", response_model=PaymentView, status_code=201)
async def record_payment(
    invoice_id: int,
    body: PaymentCreate,
    scope=Depends(require_permission(PERM_INVOICES_MANAGE_PAYMENTS)),
    session: AsyncSession = Depends(get_db),
) -> PaymentView:
    return await financial_service.record_payment(
        session,
        scope,
        invoice_id,
        amount=body.amount,
        paid_at=body.paid_at,
    )


@router.get("/balance-sheet", response_model=BalanceSheet)
async def balance_sheet(
    period: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    scope=Depends(require_any_permission(PERM_BALANCE_SHEET_READ, PERM_FINANCIAL_READ_OWN_UNIT)),
    session: AsyncSession = Depends(get_db),
) -> BalanceSheet:
    return await financial_service.balance_sheet(session, scope, period)
