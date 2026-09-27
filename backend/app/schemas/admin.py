"""Pydantic schemas for administrator operations (roles, condominiums, associations)."""

from pydantic import BaseModel, EmailStr, Field

# --- Roles ---


class FunctionRolesUpdate(BaseModel):
    roles: list[str] = Field(default_factory=list)


class UnitLinkCreate(BaseModel):
    role: str
    unit_id: int


class MembershipRolesView(BaseModel):
    user_id: int
    email: EmailStr | None = None
    person_name: str | None = None
    active: bool
    functions: list[str] = Field(default_factory=list)


class UnitLinkView(BaseModel):
    id: int
    person_id: int
    person_name: str | None = None
    unit_id: int
    unit_code: str | None = None
    role: str


class RoleOverview(BaseModel):
    condominium_id: int
    memberships: list[MembershipRolesView] = Field(default_factory=list)
    unit_links: list[UnitLinkView] = Field(default_factory=list)


# --- Condominiums ---


class CondominiumCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    address: str | None = None


class CondominiumUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    address: str | None = None


class CondominiumView(BaseModel):
    id: int
    name: str
    address: str | None = None
    active: bool = True

    model_config = {"from_attributes": True}


# --- Associations ---


class AssociationUpdate(BaseModel):
    active: bool = True


class AssociationView(BaseModel):
    user_id: int
    email: EmailStr | None = None
    person_name: str | None = None
    active: bool
    functions: list[str] = Field(default_factory=list)
