"""Common area and booking models with atomic overlap prevention."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import TSTZRANGE, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.person import Person
    from app.models.unit import Unit


class CommonArea(Base):
    """A bookable common area of the condominium (name, description, capacity)."""

    __tablename__ = "common_areas"
    __table_args__ = (Index("ix_common_areas_condominium_id", "condominium_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    condominium_id: Mapped[int] = mapped_column(
        ForeignKey("condominiums.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(Text)
    capacity: Mapped[int | None] = mapped_column(Integer)

    bookings: Mapped[list[Booking]] = relationship(
        back_populates="area", cascade="all, delete-orphan"
    )


class Booking(Base):
    """A common-area booking with reserved/cancelled status.

    Overlap is prevented atomically by a PostgreSQL exclusion constraint over the
    generated `period` range (only for `reserved` bookings). Cancelled bookings
    free the time slot. `btree_gist` is required for the equality operator on
    `area_id` inside the GiST index (created in the migration).
    """

    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("end_at > start_at", name="ck_bookings_end_after_start"),
        ExcludeConstraint(
            ("area_id", "="),
            ("period", "&&"),
            name="uq_bookings_no_overlap",
            using="gist",
            where=text("status = 'reserved'"),
        ),
        Index("ix_bookings_condominium_id", "condominium_id"),
        Index("ix_bookings_area_start", "area_id", "start_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    condominium_id: Mapped[int] = mapped_column(
        ForeignKey("condominiums.id", ondelete="CASCADE"), index=True
    )
    area_id: Mapped[int] = mapped_column(
        ForeignKey("common_areas.id", ondelete="CASCADE"), index=True
    )
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("units.id", ondelete="SET NULL"))
    person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id", ondelete="SET NULL"))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="reserved")  # reserved|cancelled
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Generated range used by the exclusion constraint (PostgreSQL only).
    period: Mapped[str] = mapped_column(
        TSTZRANGE,
        Computed("tstzrange(start_at, end_at)", persisted=True),
        comment="Generated tstzrange(start_at, end_at) — enforced by exclusion constraint",
    )

    area: Mapped[CommonArea] = relationship(back_populates="bookings")
    unit: Mapped[Unit | None] = relationship()
    person: Mapped[Person | None] = relationship()
