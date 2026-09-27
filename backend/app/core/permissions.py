"""Permission matrix — role codes and the declarative permissions of each role.

Role codes are stored in the database (membership_roles / member_links) and are
the same identifiers referenced by the specs: sindico, conselho (functions) and
condomino, inquilino (unit links). The readable labels live in the frontend i18n
catalog — never in this module.
"""

from collections.abc import Iterable

# --- Role codes ---
ROLE_SINDICO = "sindico"
ROLE_CONSELHO = "conselho"
ROLE_CONDOMINO = "condomino"
ROLE_INQUILINO = "inquilino"
ROLE_GLOBAL_ADMIN = "global_admin"

FUNCTION_ROLES = frozenset({ROLE_SINDICO, ROLE_CONSELHO})
UNIT_LINK_ROLES = frozenset({ROLE_CONDOMINO, ROLE_INQUILINO})
KNOWN_ROLES = FUNCTION_ROLES | UNIT_LINK_ROLES

# --- Permissions ---
PERM_UNITS_MANAGE = "units.manage"
PERM_UNITS_READ = "units.read"
PERM_RESIDENTS_MANAGE = "residents.manage"
PERM_RESIDENTS_READ = "residents.read"
PERM_VEHICLES_MANAGE = "vehicles.manage"
PERM_VEHICLES_READ = "vehicles.read"
PERM_VEHICLES_SELF = "vehicles.self"
PERM_PETS_MANAGE = "pets.manage"
PERM_PETS_READ = "pets.read"
PERM_PETS_SELF = "pets.self"
PERM_COMMON_AREAS_MANAGE = "common_areas.manage"
PERM_COMMON_AREAS_READ = "common_areas.read"
PERM_BOOKINGS_MANAGE = "bookings.manage"
PERM_BOOKINGS_READ = "bookings.read"
PERM_BOOKINGS_SELF = "bookings.self"
PERM_FINANCIAL_MANAGE = "financial.manage"
PERM_FINANCIAL_READ = "financial.read"
PERM_FINANCIAL_READ_OWN_UNIT = "financial.read_own_unit"
PERM_CHART_ACCOUNTS_MANAGE = "chart_accounts.manage"
PERM_INVOICES_MANAGE_PAYMENTS = "invoices.manage_payments"
PERM_BALANCE_SHEET_READ = "balance_sheet.read"
PERM_ROLES_MANAGE = "roles.manage"
PERM_CONDOMINIUMS_MANAGE = "condominiums.manage"
PERM_MEMBERSHIPS_MANAGE = "memberships.manage"
PERM_USERS_MANAGE = "users.manage"

ALL_PERMISSIONS = frozenset(
    {
        PERM_UNITS_MANAGE,
        PERM_UNITS_READ,
        PERM_RESIDENTS_MANAGE,
        PERM_RESIDENTS_READ,
        PERM_VEHICLES_MANAGE,
        PERM_VEHICLES_READ,
        PERM_VEHICLES_SELF,
        PERM_PETS_MANAGE,
        PERM_PETS_READ,
        PERM_PETS_SELF,
        PERM_COMMON_AREAS_MANAGE,
        PERM_COMMON_AREAS_READ,
        PERM_BOOKINGS_MANAGE,
        PERM_BOOKINGS_READ,
        PERM_BOOKINGS_SELF,
        PERM_FINANCIAL_MANAGE,
        PERM_FINANCIAL_READ,
        PERM_FINANCIAL_READ_OWN_UNIT,
        PERM_CHART_ACCOUNTS_MANAGE,
        PERM_INVOICES_MANAGE_PAYMENTS,
        PERM_BALANCE_SHEET_READ,
        PERM_ROLES_MANAGE,
        PERM_CONDOMINIUMS_MANAGE,
        PERM_MEMBERSHIPS_MANAGE,
        PERM_USERS_MANAGE,
    }
)

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    ROLE_SINDICO: frozenset(
        {
            PERM_UNITS_MANAGE,
            PERM_UNITS_READ,
            PERM_RESIDENTS_MANAGE,
            PERM_RESIDENTS_READ,
            PERM_VEHICLES_MANAGE,
            PERM_VEHICLES_READ,
            PERM_PETS_MANAGE,
            PERM_PETS_READ,
            PERM_COMMON_AREAS_MANAGE,
            PERM_COMMON_AREAS_READ,
            PERM_BOOKINGS_MANAGE,
            PERM_BOOKINGS_READ,
            PERM_BOOKINGS_SELF,
            PERM_FINANCIAL_MANAGE,
            PERM_FINANCIAL_READ,
            PERM_CHART_ACCOUNTS_MANAGE,
            PERM_INVOICES_MANAGE_PAYMENTS,
            PERM_BALANCE_SHEET_READ,
        }
    ),
    ROLE_CONSELHO: frozenset(
        {
            PERM_UNITS_READ,
            PERM_RESIDENTS_READ,
            PERM_VEHICLES_READ,
            PERM_PETS_READ,
            PERM_COMMON_AREAS_READ,
            PERM_BOOKINGS_READ,
            PERM_FINANCIAL_READ,
            PERM_BALANCE_SHEET_READ,
        }
    ),
    ROLE_CONDOMINO: frozenset(
        {
            PERM_UNITS_READ,
            PERM_VEHICLES_SELF,
            PERM_PETS_SELF,
            PERM_COMMON_AREAS_READ,
            PERM_BOOKINGS_READ,
            PERM_BOOKINGS_SELF,
            PERM_FINANCIAL_READ_OWN_UNIT,
        }
    ),
    ROLE_INQUILINO: frozenset(
        {
            PERM_UNITS_READ,
            PERM_VEHICLES_SELF,
            PERM_PETS_SELF,
            PERM_COMMON_AREAS_READ,
            PERM_BOOKINGS_READ,
            PERM_BOOKINGS_SELF,
            PERM_FINANCIAL_READ_OWN_UNIT,
        }
    ),
    ROLE_GLOBAL_ADMIN: ALL_PERMISSIONS,
}


def permissions_for(roles: Iterable[str]) -> frozenset[str]:
    """Combine the permissions of a set of role codes."""
    combined: set[str] = set()
    for role in roles:
        combined |= ROLE_PERMISSIONS.get(role, frozenset())
    return frozenset(combined)


def is_function_role(role: str) -> bool:
    return role in FUNCTION_ROLES or role == ROLE_GLOBAL_ADMIN


def is_unit_link_role(role: str) -> bool:
    return role in UNIT_LINK_ROLES
