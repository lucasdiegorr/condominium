"""Shared test helpers — users, people, condominiums and scoped tokens.

All CPFs generated here are valid (check digits computed), so they pass any
CPF validation added later without colliding with the seeded administrator.
"""

import itertools

from httpx import AsyncClient

from app.core.security import hash_password
from app.db import SessionLocal
from app.models import Person, User

_cpf_base = itertools.count(903704891)


def _cpf_check_digit(base: str) -> str:
    def calc(digits: str) -> str:
        total = sum(int(d) * w for d, w in zip(digits, range(len(digits) + 1, 1, -1), strict=False))
        rest = total % 11
        return str(0 if rest < 2 else 11 - rest)

    check_10 = calc(base)
    check_11 = calc(base + check_10)
    return base + check_10 + check_11


def unique_cpf() -> str:
    return _cpf_check_digit(str(next(_cpf_base)))


async def create_person_user(
    *,
    email: str,
    password: str = "secret123",
    name: str = "Test Person",
    cpf: str | None = None,
    active: bool = True,
) -> tuple[int, int]:
    """Create a person + user account (direct DB insert). Returns (person_id, user_id)."""
    async with SessionLocal() as session:
        person = Person(name=name, cpf=cpf or unique_cpf(), email_contact=email)
        user = User(
            email=email,
            password_hash=hash_password(password),
            active=active,
            person=person,
        )
        session.add(user)
        await session.commit()
        return person.id, user.id


async def create_person_only(*, name: str = "Resident", cpf: str | None = None) -> int:
    """Create a person WITHOUT a login (resident who never accesses the system)."""
    async with SessionLocal() as session:
        person = Person(name=name, cpf=cpf or unique_cpf())
        session.add(person)
        await session.commit()
        return person.id


async def login_identity(client: AsyncClient, email: str, password: str = "secret123") -> str:
    response = await client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["token"]


async def select_scoped(client: AsyncClient, identity: str, condominium_id: int) -> str:
    response = await client.post(
        f"/auth/condominiums/{condominium_id}/select",
        headers={"Authorization": f"Bearer {identity}"},
    )
    assert response.status_code == 200, response.text
    return response.json()["token"]


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def create_condominium_api(
    client: AsyncClient, identity: str, name: str, address: str | None = None
) -> dict:
    response = await client.post(
        "/admin/condominiums",
        headers=bearer(identity),
        json={"name": name, "address": address},
    )
    assert response.status_code == 201, response.text
    return response.json()
