/**
 * Client-side mirror of the backend permission matrix (`backend/app/core/permissions.py`).
 *
 * UI visibility only — the backend remains the enforcement point. Sections and
 * actions are shown/hidden based on the roles carried by the scoped token.
 */

export const ROLES = {
  SINDICO: "sindico",
  CONSELHO: "conselho",
  CONDOMINO: "condomino",
  INQUILINO: "inquilino",
  GLOBAL_ADMIN: "global_admin",
} as const;

export const perm = {
  UNITS_MANAGE: "units.manage",
  UNITS_READ: "units.read",
  RESIDENTS_MANAGE: "residents.manage",
  RESIDENTS_READ: "residents.read",
  VEHICLES_MANAGE: "vehicles.manage",
  VEHICLES_READ: "vehicles.read",
  VEHICLES_SELF: "vehicles.self",
  PETS_MANAGE: "pets.manage",
  PETS_READ: "pets.read",
  PETS_SELF: "pets.self",
  COMMON_AREAS_MANAGE: "common_areas.manage",
  COMMON_AREAS_READ: "common_areas.read",
  BOOKINGS_MANAGE: "bookings.manage",
  BOOKINGS_READ: "bookings.read",
  BOOKINGS_SELF: "bookings.self",
  FINANCIAL_MANAGE: "financial.manage",
  FINANCIAL_READ: "financial.read",
  FINANCIAL_READ_OWN_UNIT: "financial.read_own_unit",
  CHART_ACCOUNTS_MANAGE: "chart_accounts.manage",
  INVOICES_MANAGE_PAYMENTS: "invoices.manage_payments",
  BALANCE_SHEET_READ: "balance_sheet.read",
  ROLES_MANAGE: "roles.manage",
  MEMBERSHIPS_MANAGE: "memberships.manage",
  USERS_MANAGE: "users.manage",
  CONDOMINIUMS_MANAGE: "condominiums.manage",
} as const;

export type Permission = (typeof perm)[keyof typeof perm];

const ALL: readonly Permission[] = Object.values(perm);

/** Role → permissions, matching the backend ROLE_PERMISSIONS matrix. */
export const ROLE_PERMISSIONS: Readonly<Record<string, readonly Permission[]>> = {
  [ROLES.SINDICO]: [
    perm.UNITS_MANAGE, perm.UNITS_READ,
    perm.RESIDENTS_MANAGE, perm.RESIDENTS_READ,
    perm.VEHICLES_MANAGE, perm.VEHICLES_READ, perm.VEHICLES_SELF,
    perm.PETS_MANAGE, perm.PETS_READ, perm.PETS_SELF,
    perm.COMMON_AREAS_MANAGE, perm.COMMON_AREAS_READ,
    perm.BOOKINGS_MANAGE, perm.BOOKINGS_READ, perm.BOOKINGS_SELF,
    perm.FINANCIAL_MANAGE, perm.FINANCIAL_READ,
    perm.CHART_ACCOUNTS_MANAGE, perm.INVOICES_MANAGE_PAYMENTS, perm.BALANCE_SHEET_READ,
  ],
  [ROLES.CONSELHO]: [
    perm.UNITS_READ,
    perm.RESIDENTS_READ,
    perm.VEHICLES_READ,
    perm.PETS_READ,
    perm.COMMON_AREAS_READ,
    perm.BOOKINGS_READ,
    perm.FINANCIAL_READ,
    perm.BALANCE_SHEET_READ,
  ],
  [ROLES.CONDOMINO]: [
    perm.UNITS_READ,
    perm.VEHICLES_SELF,
    perm.PETS_SELF,
    perm.COMMON_AREAS_READ,
    perm.BOOKINGS_READ, perm.BOOKINGS_SELF,
    perm.FINANCIAL_READ_OWN_UNIT,
  ],
  [ROLES.INQUILINO]: [
    perm.UNITS_READ,
    perm.VEHICLES_SELF,
    perm.PETS_SELF,
    perm.COMMON_AREAS_READ,
    perm.BOOKINGS_READ, perm.BOOKINGS_SELF,
    perm.FINANCIAL_READ_OWN_UNIT,
  ],
  [ROLES.GLOBAL_ADMIN]: ALL,
};

/** True when at least one of the user's roles grants the permission. */
export function rolesGrant(roles: readonly string[], permission: Permission): boolean {
  return roles.some((role) => ROLE_PERMISSIONS[role]?.includes(permission) ?? false);
}
