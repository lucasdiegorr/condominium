"""Financial record-keeping within a condominium scope (financial spec).

Record-keeping only — NEVER executes charges (no bank slips, no PIX, no
integration with payment channels). Expenses are allocated per unit by ideal
fraction; monthly invoices reflect allocations minus period credits; payments
are recorded manually; the balance sheet consolidates the period.
"""

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.permissions import (
    PERM_FINANCIAL_READ,
    PERM_FINANCIAL_READ_OWN_UNIT,
)
from app.core.scope import Scope
from app.models import AccountCategory, Entry, EntryAllocation, Invoice, Payment, Unit

CENT = Decimal("0.01")


def _money(value: Decimal) -> str:
    """Format a Decimal as exactly two decimal places (e.g. '54.00')."""
    return f"{value:.2f}"


def _error(status_code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail=detail)


def _period_range(period: str) -> tuple[date, date]:
    year, month = (int(part) for part in period.split("-"))
    start = date(year, month, 1)
    next_start = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, next_start


def _period_month_after(period: str) -> date:
    year, month = (int(part) for part in period.split("-"))
    if month == 12:
        return date(year + 1, 1, 10)
    return date(year, month + 1, 10)


def _paid_total(invoice: Invoice) -> Decimal:
    return sum((payment.amount for payment in invoice.payments), Decimal("0"))


def _effective_status(invoice: Invoice, today: date | None = None) -> str:
    if invoice.status == "paid":
        return "paid"
    paid = _paid_total(invoice)
    if paid >= invoice.amount:
        return "paid"
    today = today or date.today()
    if invoice.due_date < today:
        return "overdue"
    return "pending"


# --- Chart of accounts ---


async def _category_in_scope(
    session: AsyncSession, scope: Scope, category_id: int
) -> AccountCategory:
    category = await session.scalar(
        select(AccountCategory).where(
            AccountCategory.id == category_id,
            AccountCategory.condominium_id == scope.condominium_id,
        )
    )
    if category is None:
        raise _error(status.HTTP_403_FORBIDDEN, "category not in this condominium")
    return category


async def list_chart(session: AsyncSession, scope: Scope) -> list[dict]:
    categories = (
        await session.scalars(
            select(AccountCategory)
            .where(AccountCategory.condominium_id == scope.condominium_id)
            .order_by(AccountCategory.kind, AccountCategory.name)
        )
    ).all()
    return [{"id": cat.id, "name": cat.name, "kind": cat.kind} for cat in categories]


async def create_category(
    session: AsyncSession,
    scope: Scope,
    *,
    name: str,
    kind: str,
) -> dict:
    existing = await session.scalar(
        select(AccountCategory).where(
            AccountCategory.condominium_id == scope.condominium_id,
            AccountCategory.name == name,
        )
    )
    if existing is not None:
        raise _error(status.HTTP_409_CONFLICT, "category name already exists")
    category = AccountCategory(condominium_id=scope.condominium_id, name=name, kind=kind)
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return {"id": category.id, "name": category.name, "kind": category.kind}


async def update_category(
    session: AsyncSession,
    scope: Scope,
    category_id: int,
    *,
    name: str | None,
    kind: str | None,
) -> dict:
    category = await _category_in_scope(session, scope, category_id)
    if name is not None:
        duplicate = await session.scalar(
            select(AccountCategory).where(
                AccountCategory.condominium_id == scope.condominium_id,
                AccountCategory.name == name,
                AccountCategory.id != category_id,
            )
        )
        if duplicate is not None:
            raise _error(status.HTTP_409_CONFLICT, "category name already exists")
        category.name = name
    if kind is not None:
        category.kind = kind
    await session.commit()
    return {"id": category.id, "name": category.name, "kind": category.kind}


# --- Entries ---


async def _active_units(session: AsyncSession, scope: Scope) -> list[Unit]:
    return (
        await session.scalars(
            select(Unit)
            .where(
                Unit.condominium_id == scope.condominium_id,
                Unit.active.is_(True),
            )
            .order_by(Unit.id)
        )
    ).all()


def _allocate_shares(amount: Decimal, units: list[Unit]) -> list[tuple[int, Decimal]]:
    """Split `amount` among units by ideal fraction; rounding drift goes to the
    largest share so the sum of allocations equals the entry amount exactly."""
    shares = [
        (
            unit.id,
            (amount * _as_decimal(unit.fraction) / Decimal(100)).quantize(
                CENT, rounding=ROUND_HALF_UP
            ),
        )
        for unit in units
    ]
    drift = amount - sum(share for _, share in shares)
    if drift != 0 and shares:
        largest = max(range(len(shares)), key=lambda i: shares[i][1])
        shares[largest] = (shares[largest][0], shares[largest][1] + drift)
    return shares


def _as_decimal(value: Decimal | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


async def list_entries(session: AsyncSession, scope: Scope) -> list[dict]:
    entries = (
        await session.scalars(
            select(Entry)
            .where(Entry.condominium_id == scope.condominium_id)
            .options(selectinload(Entry.category))
            .order_by(Entry.date.desc(), Entry.id.desc())
        )
    ).all()
    return [
        {
            "id": entry.id,
            "date": entry.date,
            "kind": entry.kind,
            "amount": _money(entry.amount),
            "description": entry.description,
            "category_id": entry.category_id,
            "category_name": entry.category.name,
        }
        for entry in entries
    ]


async def create_entry(
    session: AsyncSession,
    scope: Scope,
    *,
    entry_date: date,
    amount: Decimal,
    category_id: int,
    kind: str,
    description: str | None,
) -> dict:
    category = await _category_in_scope(session, scope, category_id)
    if category.kind != kind:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"category is of kind '{category.kind}', not '{kind}'",
        )

    entry = Entry(
        condominium_id=scope.condominium_id,
        category_id=category_id,
        kind=kind,
        date=entry_date,
        amount=amount,
        description=description,
        created_by_user_id=scope.user_id,
    )
    session.add(entry)
    await session.flush()

    if kind == "expense":
        units = await _active_units(session, scope)
        for unit_id, share in _allocate_shares(amount, units):
            session.add(EntryAllocation(entry_id=entry.id, unit_id=unit_id, amount=share))

    await session.commit()
    return {
        "id": entry.id,
        "date": entry.date,
        "kind": entry.kind,
        "amount": _money(entry.amount),
        "description": entry.description,
        "category_id": entry.category_id,
        "category_name": category.name,
    }


async def delete_entry(session: AsyncSession, scope: Scope, entry_id: int) -> None:
    entry = await session.scalar(
        select(Entry).where(
            Entry.id == entry_id,
            Entry.condominium_id == scope.condominium_id,
        )
    )
    if entry is None:
        raise _error(status.HTTP_404_NOT_FOUND, "entry not found")
    await session.delete(entry)  # allocations cascade
    await session.commit()


# --- Invoices ---


async def generate_invoices(session: AsyncSession, scope: Scope, period: str) -> list[dict]:
    start, end = _period_range(period)
    units = await _active_units(session, scope)

    expense_entries = (
        await session.scalars(
            select(Entry)
            .where(
                Entry.condominium_id == scope.condominium_id,
                Entry.kind == "expense",
                Entry.date >= start,
                Entry.date < end,
            )
            .options(selectinload(Entry.allocations))
        )
    ).all()
    income_total = (
        await session.scalar(
            select(func.coalesce(func.sum(Entry.amount), 0)).where(
                Entry.condominium_id == scope.condominium_id,
                Entry.kind == "income",
                Entry.date >= start,
                Entry.date < end,
            )
        )
    ) or Decimal("0")
    income_total = _as_decimal(income_total)

    allocations: dict[int, Decimal] = {}
    for entry in expense_entries:
        for allocation in entry.allocations:
            allocations[allocation.unit_id] = allocations.get(
                allocation.unit_id, Decimal("0")
            ) + _as_decimal(allocation.amount)

    due_date = _period_month_after(period)
    generated: list[Invoice] = []
    for unit in units:
        if unit.id not in allocations and income_total == 0:
            continue  # nothing to invoice
        allocated = allocations.get(unit.id, Decimal("0"))
        credit = (income_total * _as_decimal(unit.fraction) / Decimal(100)).quantize(
            CENT, rounding=ROUND_HALF_UP
        )
        due = max(Decimal("0"), allocated - credit)

        existing = await session.scalar(
            select(Invoice).where(
                Invoice.condominium_id == scope.condominium_id,
                Invoice.unit_id == unit.id,
                Invoice.period == period,
            )
        )
        if existing is not None:
            if existing.status != "paid":
                existing.amount = due
                existing.status = "pending"
            generated.append(existing)
        else:
            invoice = Invoice(
                condominium_id=scope.condominium_id,
                unit_id=unit.id,
                period=period,
                due_date=due_date,
                amount=due,
                status="pending",
            )
            session.add(invoice)
            generated.append(invoice)
    await session.commit()

    fresh = (
        await session.scalars(
            select(Invoice)
            .where(
                Invoice.condominium_id == scope.condominium_id,
                Invoice.period == period,
            )
            .options(selectinload(Invoice.unit), selectinload(Invoice.payments))
            .order_by(Invoice.unit_id)
        )
    ).all()
    return [_invoice_view(invoice) for invoice in fresh]


async def _invoice_or_403(session: AsyncSession, scope: Scope, invoice_id: int) -> Invoice:
    invoice = await session.scalar(
        select(Invoice)
        .where(
            Invoice.id == invoice_id,
            Invoice.condominium_id == scope.condominium_id,
        )
        .options(selectinload(Invoice.unit), selectinload(Invoice.payments))
    )
    if invoice is None:
        raise _error(status.HTTP_403_FORBIDDEN, "invoice not in this condominium")
    return invoice


def _invoice_view(invoice: Invoice) -> dict:
    return {
        "id": invoice.id,
        "unit_id": invoice.unit_id,
        "unit_code": invoice.unit.code,
        "period": invoice.period,
        "due_date": invoice.due_date,
        "amount": _money(invoice.amount),
        "paid": _money(_paid_total(invoice)),
        "status": _effective_status(invoice),
    }


async def list_invoices(session: AsyncSession, scope: Scope) -> list[dict]:
    query = (
        select(Invoice)
        .where(Invoice.condominium_id == scope.condominium_id)
        .options(selectinload(Invoice.unit), selectinload(Invoice.payments))
    )
    if scope.has_permission(PERM_FINANCIAL_READ_OWN_UNIT) and not scope.has_permission(
        PERM_FINANCIAL_READ
    ):
        query = query.where(Invoice.unit_id.in_(scope.linked_unit_ids or {-1}))
    invoices = (await session.scalars(query.order_by(Invoice.period.desc()))).all()
    return [_invoice_view(invoice) for invoice in invoices]


async def record_payment(
    session: AsyncSession,
    scope: Scope,
    invoice_id: int,
    *,
    amount: Decimal,
    paid_at: datetime | None,
) -> dict:
    invoice = await _invoice_or_403(session, scope, invoice_id)
    payment = Payment(
        invoice_id=invoice.id,
        amount=amount,
        paid_at=paid_at,
        recorded_by_user_id=scope.user_id,
    )
    session.add(payment)
    await session.flush()
    if _paid_total(invoice) + amount >= invoice.amount:
        invoice.status = "paid"
    await session.commit()
    await session.refresh(payment)
    return {
        "invoice_id": invoice.id,
        "amount": _money(payment.amount),
        "paid_at": payment.paid_at,
    }


# --- Balance sheet ---


async def balance_sheet(session: AsyncSession, scope: Scope, period: str) -> dict:
    start, end = _period_range(period)
    by_kind = {"expense": [], "income": []}
    totals = {"expense": Decimal("0"), "income": Decimal("0")}
    category_rows = (
        await session.execute(
            select(Entry.kind, Entry.category_id, AccountCategory.name, func.sum(Entry.amount))
            .join(AccountCategory, AccountCategory.id == Entry.category_id)
            .where(
                Entry.condominium_id == scope.condominium_id,
                Entry.date >= start,
                Entry.date < end,
            )
            .group_by(Entry.kind, Entry.category_id, AccountCategory.name)
            .order_by(Entry.kind, AccountCategory.name)
        )
    ).all()
    for kind, _category_id, name, total in category_rows:
        by_kind[kind].append({"category": name, "amount": _money(total)})
        totals[kind] += _as_decimal(total)

    units = (
        await session.scalars(
            select(Unit).where(Unit.condominium_id == scope.condominium_id).order_by(Unit.code)
        )
    ).all()

    if scope.has_permission(PERM_FINANCIAL_READ_OWN_UNIT) and not scope.has_permission(
        PERM_FINANCIAL_READ
    ):
        units = [unit for unit in units if unit.id in scope.linked_unit_ids]
        # Residents see only their own unit's summary — no condo-wide breakdown.
        by_kind["expense"] = []
        by_kind["income"] = []
        totals["expense"] = Decimal("0")
        totals["income"] = Decimal("0")

    invoices = (
        await session.scalars(
            select(Invoice)
            .where(
                Invoice.condominium_id == scope.condominium_id,
                Invoice.period == period,
            )
            .options(selectinload(Invoice.unit), selectinload(Invoice.payments))
        )
    ).all()
    invoices_by_unit = {invoice.unit_id: invoice for invoice in invoices}

    per_unit = []
    for unit in units:
        invoice = invoices_by_unit.get(unit.id)
        if invoice is None:
            per_unit.append(
                {
                    "unit_id": unit.id,
                    "unit_code": unit.code,
                    "billed": "0.00",
                    "paid": "0.00",
                    "pending": "0.00",
                    "delinquent": "0.00",
                }
            )
            continue
        billed = invoice.amount
        paid = _paid_total(invoice)
        status = _effective_status(invoice)
        delinquent = billed - paid if status == "overdue" else Decimal("0")
        pending = billed - paid if status == "pending" else Decimal("0")
        per_unit.append(
            {
                "unit_id": unit.id,
                "unit_code": unit.code,
                "billed": _money(billed),
                "paid": _money(paid),
                "pending": _money(pending),
                "delinquent": _money(delinquent),
            }
        )

    return {
        "period": period,
        "expenses_by_category": by_kind["expense"],
        "incomes_by_category": by_kind["income"],
        "result": _money(totals["income"] - totals["expense"]),
        "per_unit": per_unit,
    }
