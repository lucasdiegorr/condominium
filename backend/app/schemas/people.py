"""Pydantic schemas for persons and residents (people spec)."""

from pydantic import BaseModel, Field

from app.schemas.admin import UnitLinkView


class PersonCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    cpf: str = Field(pattern=r"^\d{11}$")
    phone: str | None = None
    email_contact: str | None = None


class PersonUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = None
    email_contact: str | None = None


class UnitLinkInput(BaseModel):
    role: str
    unit_id: int


class AccountCreate(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)


class AccountView(BaseModel):
    person_id: int
    email: str


class PersonView(BaseModel):
    id: int
    name: str
    cpf: str
    phone: str | None = None
    email_contact: str | None = None
    has_account: bool
    links: list[UnitLinkView] = Field(default_factory=list)
