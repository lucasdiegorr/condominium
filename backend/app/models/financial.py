"""Financial models — record-keeping only (no payment execution).

Chart of accounts, entries, allocation by ideal fraction, per-unit invoices
and manual payment records. Explicit NON-goal: issuing bank slips / PIX or
integrating with payment channels.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.unit import Unit


class AccountCategory(Base):
    """A chart-of-accounts entry, configurable per condominium (expense or income)."""

    __tablename__ = "account_categories"
    __table_args__ = (
        UniqueConstraint("condominium_id", "name", name="uq_account_category_per_condominium"),
        Index("ix_account_categories_condominium_id", "condominium_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    condominium_id: Mapped[int] = mapped_column(
        ForeignKey("condominiums.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(20))  # expense | income
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    entries: Mapped[list[Entry]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )


class Entry(Base):
    """A financial entry (expense or income) scoped to a condominium."""

    __tablename__ = "entries"
    __table_args__ = (
        Index("ix_entries_condominium_period", "condominium_id", "date"),
        Index("ix_entries_category_id", "category_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    condominium_id: Mapped[int] = mapped_column(
        ForeignKey("condominiums.id", ondelete="CASCADE"), index=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("account_categories.id", ondelete="RESTRICT")
    )
    kind: Mapped[str] = mapped_column(String(20))  # expense | income (denormalized)
    date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    description: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    category: Mapped[AccountCategory] = relationship(back_populates="entries")
    allocations: Mapped[list[EntryAllocation]] = relationship(
        back_populates="entry", cascade="all, delete-orphan"
    )


class EntryAllocation(Base):
    """Per-unit share of a financial entry, proportional to the ideal fraction (for expenses)."""

    __tablename__ = "entry_allocations"
    __table_args__ = (
        UniqueConstraint("entry_id", "unit_id", name="uq_entry_allocation_unit"),
        Index("ix_entry_allocations_unit_id", "unit_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("entries.id", ondelete="CASCADE"), index=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id", ondelete="CASCADE"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    entry: Mapped[Entry] = relationship(back_populates="allocations")
    unit: Mapped[Unit] = relationship()


class Invoice(Base):
    """Monthly per-unit invoice derived from allocated expenses and period credits."""

    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("condominium_id", "unit_id", "period", name="uq_invoice_unit_period"),
        Index("ix_invoices_period", "condominium_id", "period"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    condominium_id: Mapped[int] = mapped_column(
        ForeignKey("condominiums.id", ondelete="CASCADE"), index=True
    )
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id", ondelete="CASCADE"))
    period: Mapped[str] = mapped_column(String(7))  # YYYY-MM
    due_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|paid|overdue
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    unit: Mapped[Unit] = relationship()
    payments: Mapped[list[Payment]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )


class Payment(Base):
    """Manual payment record for an invoice."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    recorded_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    invoice: Mapped[Invoice] = relationship(back_populates="payments")
