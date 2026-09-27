"""API dependencies: identity authentication and condominium scope enforcement."""

from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.core.scope import Scope, UnitLink
from app.core.security import (
    TOKEN_TYPE_IDENTITY,
    TOKEN_TYPE_SCOPED,
    decode_token,
)
from app.db import get_db
from app.models import Condominium, Membership, User

bearer_scheme = HTTPBearer(auto_error=False)


class _Unauthorized(HTTPException):
    def __init__(self, detail: str = "authentication required") -> None:
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def _forbidden(detail: str = "forbidden") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def _extract_token(
    credentials: HTTPAuthorizationCredentials | None,
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _Unauthorized()
    return credentials.credentials


async def current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> int:
    """Require a valid identity token and return the authenticated user id."""
    try:
        payload = decode_token(_extract_token(credentials))
    except jwt.PyJWTError as exc:
        raise _Unauthorized() from exc
    if payload.get("type") != TOKEN_TYPE_IDENTITY:
        raise _Unauthorized()
    try:
        return int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise _Unauthorized() from exc


async def current_global_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    """Require a valid identity token for a user with the global admin flag.

    Used on admin routes that operate outside any particular condominium
    (listing and creating condominiums) — no scope exists yet.
    """
    try:
        payload = decode_token(_extract_token(credentials))
    except jwt.PyJWTError as exc:
        raise _Unauthorized() from exc
    if payload.get("type") != TOKEN_TYPE_IDENTITY:
        raise _Unauthorized()
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise _Unauthorized() from exc

    user = await session.get(User, user_id)
    if user is None or not user.active:
        raise _Unauthorized()
    if not user.is_global_admin:
        raise _forbidden()
    return user


async def current_scope(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> Scope:
    """Require a valid scoped token and an active condominium association.

    For data routes 401 identifies missing/invalid/expired tokens; a valid
    token whose association was revoked responds 403 (design D2, D1).
    """
    try:
        payload = decode_token(_extract_token(credentials))
    except jwt.PyJWTError as exc:
        raise _Unauthorized() from exc

    if payload.get("type") != TOKEN_TYPE_SCOPED:
        raise _Unauthorized()

    try:
        user_id = int(payload["sub"])
        person_id = int(payload["person_id"])
        condominium_id = int(payload["condominium_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise _Unauthorized() from exc

    roles = [str(role) for role in (payload.get("roles") or [])]
    raw_links = payload.get("unit_links") or []
    unit_links = tuple(
        UnitLink(unit_id=int(link["unit_id"]), role=str(link["role"]))
        for link in raw_links
        if isinstance(link, dict) and "unit_id" in link
    )

    user = await session.get(User, user_id)
    if user is None or not user.active:
        raise _Unauthorized()

    # Revalidate the association on every request (immediate revocation).
    if user.is_global_admin:
        condominium = await session.get(Condominium, condominium_id)
        if condominium is None or not condominium.active:
            raise _forbidden("association revoked")
    else:
        membership = await session.scalar(
            select(Membership).where(
                Membership.user_id == user_id,
                Membership.condominium_id == condominium_id,
                Membership.active.is_(True),
            )
        )
        if membership is None:
            raise _forbidden("association revoked")

    return Scope(
        user_id=user_id,
        person_id=person_id,
        condominium_id=condominium_id,
        roles=frozenset(roles),
        unit_links=unit_links,
        is_global_admin=user.is_global_admin,
    )


def require_permission(permission: str) -> Callable:
    """Dependency factory: grant a route only when the scope holds `permission`."""

    async def dependency(scope: Scope = Depends(current_scope)) -> Scope:
        if not scope.has_permission(permission):
            raise _forbidden()
        return scope

    return dependency


async def require_scope_matches(
    condominium_id: int, scope: Scope = Depends(current_scope)
) -> Scope:
    """Dependency: reject when the path condominium differs from the scope.

    Even the global administrator only operates data through the condominium
    they selected — the scope filter stays the single authority (design D2).
    """
    if scope.condominium_id != condominium_id:
        raise _forbidden()
    return scope


async def get_scoped_or_403(
    session: AsyncSession,
    model: type,
    scope: Scope,
    record_id: int,
) -> object:
    """Load a domain record within the scope, raising 403 when absent/out of scope.

    The scope filter makes cross-condominium records indistinguishable from
    missing ones, so no existence is leaked.
    """
    condominium_column: InstrumentedAttribute = model.condominium_id
    record = await session.scalar(
        select(model).where(
            model.id == record_id,
            condominium_column == scope.condominium_id,
        )
    )
    if record is None:
        raise _forbidden()
    return record
