"""Scope — the per-request condominium context injected by `current_scope`.

Every domain data route receives a Scope and MUST use it to filter all queries
by condominium (multi-tenancy guarantee, design D2).
"""

from dataclasses import dataclass, field

from app.core.permissions import permissions_for


@dataclass(frozen=True)
class UnitLink:
    """A unit link the user's person holds in the scoped condominium."""

    unit_id: int
    role: str


@dataclass(frozen=True)
class Scope:
    user_id: int
    person_id: int
    condominium_id: int
    roles: frozenset[str] = field(default_factory=frozenset)
    unit_links: tuple[UnitLink, ...] = ()
    is_global_admin: bool = False

    _permissions: frozenset[str] | None = field(default=None, compare=False, repr=False)

    def permissions(self) -> frozenset[str]:
        if self._permissions is None:
            object.__setattr__(self, "_permissions", permissions_for(self.roles))
        return self._permissions

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions()

    @property
    def linked_unit_ids(self) -> frozenset[int]:
        return frozenset(link.unit_id for link in self.unit_links)

    def has_unit_link(self, unit_id: int) -> bool:
        return unit_id in self.linked_unit_ids
