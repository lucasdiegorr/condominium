"""Person model — the physical person record, independent of any login."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.member_models import MemberLink
    from app.models.user import User
    from app.models.vehicle_pet import Pet, Vehicle


class Person(Base):
    """A physical person (name, unique CPF, contact). May exist without a user account."""

    __tablename__ = "people"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    cpf: Mapped[str] = mapped_column(String(11), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(30))
    email_contact: Mapped[str | None] = mapped_column(String(254))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User | None] = relationship(back_populates="person", uselist=False)
    member_links: Mapped[list[MemberLink]] = relationship(
        back_populates="person", cascade="all, delete-orphan"
    )
    vehicles: Mapped[list[Vehicle]] = relationship(back_populates="resident")
    pets: Mapped[list[Pet]] = relationship(back_populates="resident")
