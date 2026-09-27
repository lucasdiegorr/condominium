"""ORM models — imported by Alembic env and tests to register metadata."""

from app.models.common_area import Booking, CommonArea
from app.models.condominium import Condominium, Membership, MembershipRole
from app.models.financial import (
    AccountCategory,
    Entry,
    EntryAllocation,
    Invoice,
    Payment,
)
from app.models.person import Person
from app.models.unit import MemberLink, ParkingSpot, Unit
from app.models.user import User
from app.models.vehicle_pet import Pet, Vehicle

__all__ = [
    "AccountCategory",
    "Booking",
    "CommonArea",
    "Condominium",
    "Entry",
    "EntryAllocation",
    "Invoice",
    "MemberLink",
    "Membership",
    "MembershipRole",
    "ParkingSpot",
    "Payment",
    "Person",
    "Pet",
    "Unit",
    "User",
    "Vehicle",
]
