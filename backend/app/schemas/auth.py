"""Pydantic schemas for authentication."""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class LoginResponse(BaseModel):
    """Only the identity token — no condominium/role/user data (attack surface)."""

    token: str
    token_type: str = "bearer"


class CondominiumBrief(BaseModel):
    id: int
    name: str
    address: str | None = None

    model_config = {"from_attributes": True}


class SelectRequest(BaseModel):
    condominium_id: int


class ScopedTokenResponse(BaseModel):
    token: str
    token_type: str = "bearer"
