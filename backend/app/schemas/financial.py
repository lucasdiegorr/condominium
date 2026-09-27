"""Pydantic schemas for financial record-keeping (financial spec)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

CategoryKind = Literal["expense", "income"]


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    kind: CategoryKind


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    kind: CategoryKind | None = None


class CategoryView(BaseModel):
    id: int
    name: str
    kind: str


class EntryCreate(BaseModel):
    date: date
    amount: Decimal = Field(gt=0)
    category_id: int
    kind: CategoryKind
    description: str | None = None


class EntryView(BaseModel):
    id: int
    date: date
    kind: str
    amount: str
    description: str | None = None
    category_id: int
    category_name: str


class InvoiceGenerate(BaseModel):
    period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")


class InvoiceView(BaseModel):
    id: int
    unit_id: int
    unit_code: str
    period: str
    due_date: date
    amount: str
    paid: str
    status: str


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    paid_at: datetime | None = None


class PaymentView(BaseModel):
    invoice_id: int
    amount: str
    paid_at: datetime | None = None


class CategoryTotal(BaseModel):
    category: str
    amount: str


class UnitSummary(BaseModel):
    unit_id: int
    unit_code: str
    billed: str
    paid: str
    pending: str
    delinquent: str


class BalanceSheet(BaseModel):
    period: str
    expenses_by_category: list[CategoryTotal]
    incomes_by_category: list[CategoryTotal]
    result: str
    per_unit: list[UnitSummary]
