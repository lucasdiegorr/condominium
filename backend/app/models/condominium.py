"""Condominium, membership (user x condominium) and membership roles (functions)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.user import User


class Condominium(Base):
    """A managed condominium — the tenant of all domain data."""

    __tablename__ = "condominiums"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    memberships: Mapped[list[Membership]] = relationship(
        back_populates="condominium", cascade="all, delete-orphan"
    )


class Membership(Base):
    """Base access association between a user and a condominium."""

    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "condominium_id", name="uq_membership_user_condominium"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    condominium_id: Mapped[int] = mapped_column(
        ForeignKey("condominiums.id", ondelete="CASCADE"), index=True
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="memberships")
    condominium: Mapped[Condominium] = relationship(back_populates="memberships")
    roles: Mapped[list[MembershipRole]] = relationship(
        back_populates="membership", cascade="all, delete-orphan"
    )


class MembershipRole(Base):
    """Condominium-level function role (sindico, conselho) of a membership."""

    __tablename__ = "membership_roles"
    __table_args__ = (UniqueConstraint("membership_id", "role", name="uq_membership_role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    membership_id: Mapped[int] = mapped_column(
        ForeignKey("memberships.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(50))  # role code: sindico | conselho

    membership: Mapped[Membership] = relationship(back_populates="roles")

    @property
    def condominium_id(self) -> int:
        return self.membership.condominium_id

    @property
    def user_id(self) -> int:
        return self.membership.user_id
