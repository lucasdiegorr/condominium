"""Idempotent database seed.

Creates:
- the bootstrap global administrator (person + user, `is_global_admin`), and
- the suggested financial categories for every existing condominium (new
  condominiums receive them at creation time).

Default roles (sindico, conselho, condomino, inquilino) do not need seeding:
they are codes validated by the permission matrix (`app.core.permissions`).
"""

import asyncio
import logging

from sqlalchemy import select

from app.config import get_settings
from app.core.security import hash_password
from app.db import SessionLocal
from app.models import AccountCategory, Condominium, Person, User

logger = logging.getLogger(__name__)

# (name, kind) suggested chart-of-accounts entries (design D8).
SUGGESTED_CATEGORIES: list[tuple[str, str]] = [
    ("maintenance", "expense"),
    ("security", "expense"),
    ("cleaning", "expense"),
    ("workers", "expense"),
    ("extra fees", "income"),
]

# Well-known valid CPF used for the seeded administrator account.
SEED_ADMIN_CPF = "11144477735"


async def _run() -> None:
    settings = get_settings()

    async with SessionLocal() as session:
        # 1. Bootstrap global administrator.
        existing = await session.scalar(select(User).where(User.email == settings.seed_admin_email))
        if existing is None:
            cpf_exists = await session.scalar(select(Person).where(Person.cpf == SEED_ADMIN_CPF))
            if cpf_exists is None:
                person = Person(
                    name="System Administrator",
                    cpf=SEED_ADMIN_CPF,
                    email_contact=settings.seed_admin_email,
                )
                user = User(
                    email=settings.seed_admin_email,
                    password_hash=hash_password(settings.seed_admin_password),
                    is_global_admin=True,
                    person=person,
                )
                session.add(user)
                logger.info("Seeded bootstrap administrator %s", settings.seed_admin_email)
            else:
                logger.warning(
                    "Seed administrator CPF already used by another person; skipping admin"
                )
        else:
            logger.info("Bootstrap administrator already present; skipping")

        # 2. Suggested financial categories per condominium.
        condominiums = (await session.scalars(select(Condominium))).all()
        for condominium in condominiums:
            existing_kinds = {
                (c.name, c.kind)
                for c in (
                    await session.scalars(
                        select(AccountCategory).where(
                            AccountCategory.condominium_id == condominium.id
                        )
                    )
                ).all()
            }
            for name, kind in SUGGESTED_CATEGORIES:
                if (name, kind) not in existing_kinds:
                    session.add(
                        AccountCategory(condominium_id=condominium.id, name=name, kind=kind)
                    )
                    logger.info(
                        "Seeded category %s (%s) for condominium %s", name, kind, condominium.id
                    )

        await session.commit()


def run() -> None:
    """Synchronous entry point used by `python -m app.seed` and startup scripts."""
    asyncio.run(_run())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
