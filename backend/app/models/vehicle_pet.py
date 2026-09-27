"""Vehicle and pet models linked to residents within a condominium."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.person import Person
    from app.models.unit import Unit


class Vehicle(Base):
    """A vehicle registered with a responsible resident and a unit of the condominium.

    Unique plate per condominium.
    """

    __tablename__ = "vehicles"
    __table_args__ = (
        UniqueConstraint("condominium_id", "plate", name="uq_vehicle_plate_per_condominium"),
        Index("ix_vehicles_resident_id", "resident_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    condominium_id: Mapped[int] = mapped_column(
        ForeignKey("condominiums.id", ondelete="CASCADE"), index=True
    )
    plate: Mapped[str] = mapped_column(String(10))  # normalized, uppercase
    model: Mapped[str] = mapped_column(String(120))
    color: Mapped[str | None] = mapped_column(String(50))
    resident_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="RESTRICT"))
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id", ondelete="RESTRICT"))

    resident: Mapped[Person] = relationship(back_populates="vehicles")
    unit: Mapped[Unit] = relationship()


class Pet(Base):
    """A pet linked to a resident (a person with a link in the condominium)."""

    __tablename__ = "pets"
    __table_args__ = (Index("ix_pets_resident_id", "resident_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    condominium_id: Mapped[int] = mapped_column(
        ForeignKey("condominiums.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    species: Mapped[str] = mapped_column(String(50))
    breed: Mapped[str | None] = mapped_column(String(100))
    resident_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="RESTRICT"))

    resident: Mapped[Person] = relationship(back_populates="pets")
