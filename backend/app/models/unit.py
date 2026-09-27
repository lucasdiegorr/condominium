"""Unit, parking spot and member link (person x unit) models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.person import Person


class Unit(Base):
    """A condominium unit — broader than an apartment (apartment, commercial, other)."""

    __tablename__ = "units"
    __table_args__ = (
        UniqueConstraint("condominium_id", "code", name="uq_unit_code_per_condominium"),
        Index("ix_units_condominium_id", "condominium_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    condominium_id: Mapped[int] = mapped_column(
        ForeignKey("condominiums.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(100))  # f"{block}-{number}" when block present
    number: Mapped[str] = mapped_column(String(50))
    block: Mapped[str | None] = mapped_column(String(50))
    unit_type: Mapped[str] = mapped_column(String(30), default="apartment")
    fraction: Mapped[str] = mapped_column(Numeric(12, 6))  # ideal fraction, percentage (0, 100]
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    parking_spots: Mapped[list[ParkingSpot]] = relationship(
        back_populates="unit", cascade="all, delete-orphan"
    )
    member_links: Mapped[list[MemberLink]] = relationship(
        back_populates="unit", cascade="all, delete-orphan"
    )


class ParkingSpot(Base):
    """A parking spot (identifier + type) tied to a unit of the same condominium."""

    __tablename__ = "parking_spots"
    __table_args__ = (
        UniqueConstraint(
            "condominium_id", "identifier", name="uq_parking_identifier_per_condominium"
        ),
        Index("ix_parking_spots_condominium_id", "condominium_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    condominium_id: Mapped[int] = mapped_column(
        ForeignKey("condominiums.id", ondelete="CASCADE"), index=True
    )
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("units.id", ondelete="SET NULL"))
    identifier: Mapped[str] = mapped_column(String(50))
    spot_type: Mapped[str] = mapped_column(String(30), default="uncovered")  # covered|uncovered

    unit: Mapped[Unit | None] = relationship(back_populates="parking_spots")


class MemberLink(Base):
    """Resident roster entry: a person linked to a unit as condomino (owner) or inquilino (tenant)."""

    __tablename__ = "member_links"
    __table_args__ = (
        UniqueConstraint("person_id", "unit_id", "role", name="uq_member_link"),
        Index("ix_member_links_unit_id", "unit_id"),
        Index("ix_member_links_person_id", "person_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), index=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(30))  # condomino | inquilino
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    person: Mapped[Person] = relationship(back_populates="member_links")
    unit: Mapped[Unit] = relationship(back_populates="member_links")
