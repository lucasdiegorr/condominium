"""Authentication routes — two-stage JWT (identity token -> scoped token)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id
from app.core.security import create_identity_token
from app.db import get_db
from app.models import User
from app.schemas.auth import (
    CondominiumBrief,
    LoginRequest,
    LoginResponse,
    ScopedTokenResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

GENERIC_401 = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_db)) -> LoginResponse:
    """Authenticate by e-mail/password and return ONLY the identity token."""
    user = await auth_service.authenticate_user(session, body.email, body.password)
    if user is None:
        raise GENERIC_401
    return LoginResponse(token=create_identity_token(user.id))


@router.get("/condominiums", response_model=list[CondominiumBrief])
async def list_condominiums(
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_db),
) -> list[CondominiumBrief]:
    """List only the condominiums the identity has an active association with."""
    user = await session.get(User, user_id)
    if user is None or not user.active:
        raise GENERIC_401
    condominiums = await auth_service.list_available_condominiums(session, user)
    return [CondominiumBrief.model_validate(c) for c in condominiums]


@router.post("/condominiums/{condominium_id}/select", response_model=ScopedTokenResponse)
async def select_condominium(
    condominium_id: int,
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_db),
) -> ScopedTokenResponse:
    """Validate the association and issue a scoped token (condominium + roles)."""
    user = await session.get(User, user_id)
    if user is None or not user.active:
        raise GENERIC_401
    if not await auth_service.has_active_association(session, user, condominium_id):
        # 403 without revealing whether the condominium exists.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    token = await auth_service.issue_scoped_token(session, user, condominium_id)
    return ScopedTokenResponse(token=token)
