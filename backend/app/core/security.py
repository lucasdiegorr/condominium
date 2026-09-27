"""Password hashing (argon2) and JWT creation/decoding."""

from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.config import get_settings

TOKEN_TYPE_IDENTITY = "identity"
TOKEN_TYPE_SCOPED = "scoped"

_password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hash.verify(password, password_hash)
    except Exception:
        return False


def _now() -> datetime:
    return datetime.now(UTC)


def create_identity_token(user_id: int) -> str:
    """Identity JWT — carries only the user identity (login response)."""
    settings = get_settings()
    payload = {
        "sub": str(user_id),
        "type": TOKEN_TYPE_IDENTITY,
        "iat": _now(),
        "exp": _now() + timedelta(minutes=settings.identity_token_ttl_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_scoped_token(
    *,
    user_id: int,
    person_id: int,
    condominium_id: int,
    roles: list[str],
    unit_links: list[dict],
) -> str:
    """Scoped JWT — carries condominium id, user/person ids and roles."""
    settings = get_settings()
    payload = {
        "sub": str(user_id),
        "type": TOKEN_TYPE_SCOPED,
        "person_id": person_id,
        "condominium_id": condominium_id,
        "roles": roles,
        "unit_links": unit_links,
        "iat": _now(),
        "exp": _now() + timedelta(minutes=settings.scoped_token_ttl_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises jwt.PyJWTError on failure."""
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
