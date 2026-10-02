/**
 * HTTP client for the Condominium Management API.
 *
 * Two token stages: identity tokens drive /auth/*; scoped tokens drive every
 * domain route. The scoped token is registered module-wide via
 * `setScopedToken` so screens never pass it by hand. A 401 on a scoped call
 * (expired/no-scope) triggers the registered unauthorized handler, which
 * clears the session and redirects (task 11.6).
 */

const BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "/api";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }

  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  get isForbidden(): boolean {
    return this.status === 403;
  }

  get isConflict(): boolean {
    return this.status === 409;
  }
}

// ---------------------------------------------------------------------------
// Scoped-token registration + unauthorized interception (task 11.6)
// ---------------------------------------------------------------------------

let scopedToken: string | null = null;
let unauthorizedHandler: (() => void) | null = null;

/** Register the active scoped token (called by AuthProvider on state change). */
export function setScopedToken(token: string | null): void {
  scopedToken = token;
}

/** Register a handler invoked when a scoped call returns 401 (expired/no scope). */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

// ---------------------------------------------------------------------------
// Scoped JWT decoding (roles drive field visibility — task 11.2)
// ---------------------------------------------------------------------------

export interface ScopedUnitLink {
  unit_id: number;
  role: string;
}

export interface ScopedClaims {
  sub: string;
  person_id: number;
  condominium_id: number;
  roles: string[];
  unit_links: ScopedUnitLink[];
  exp: number;
}

/** Decode the payload of a scoped JWT client-side (UI visibility only). */
export function decodeScopedToken(token: string): ScopedClaims | null {
  try {
    const payload = token.split(".")[1];
    if (!payload) return null;
    let base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    while (base64.length % 4 !== 0) base64 += "=";
    const json = atob(base64);
    return JSON.parse(json) as ScopedClaims;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Request plumbing
// ---------------------------------------------------------------------------

interface RequestOptions extends RequestInit {
  authToken?: string;
}

function extractDetail(detail: unknown): string {
  if (Array.isArray(detail)) {
    // Pydantic validation errors — detail is an array of {loc, msg, ...}.
    return detail.map((item) => String((item as { msg?: unknown })?.msg ?? "")).join("; ");
  }
  return String(detail ?? "");
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  const token = options.authToken ?? scopedToken;
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let detail: unknown = response.statusText;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (body.detail !== undefined) detail = body.detail;
    } catch {
      // Non-JSON error body — keep status text.
    }
    const error = new ApiError(response.status, extractDetail(detail));
    // Expired/no-scope scoped tokens: clear the session and redirect.
    if (error.isUnauthorized && token === scopedToken && unauthorizedHandler) {
      unauthorizedHandler();
    }
    throw error;
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

// ---------------------------------------------------------------------------
// Domain types (mirror the backend response models)
// ---------------------------------------------------------------------------

export interface UnitLinkView {
  id: number;
  person_id: number;
  person_name: string | null;
  unit_id: number;
  unit_code: string | null;
  role: string;
}

export interface PersonView {
  id: number;
  name: string;
  cpf: string;
  phone: string | null;
  email_contact: string | null;
  has_account: boolean;
  links: UnitLinkView[];
}

export interface ParkingSpotView {
  id: number;
  identifier: string;
  spot_type: string;
  unit_id: number | null;
}

export interface UnitView {
  id: number;
  code: string;
  number: string;
  block: string | null;
  unit_type: string;
  fraction: string;
  active: boolean;
  parking_spots: ParkingSpotView[];
}

export interface VehicleView {
  id: number;
  plate: string;
  model: string;
  color: string | null;
  resident_id: number;
  resident_name: string;
  unit_id: number;
  unit_code: string | null;
}

export interface PetView {
  id: number;
  name: string;
  species: string;
  breed: string | null;
  resident_id: number;
  resident_name: string;
}

export interface CommonAreaView {
  id: number;
  name: string;
  description: string | null;
  capacity: number | null;
}

export interface BookingView {
  id: number;
  area_id: number;
  area_name: string | null;
  unit_id: number | null;
  unit_code: string | null;
  person_id: number | null;
  person_name: string | null;
  start_at: string;
  end_at: string;
  status: string;
}

export interface CategoryView {
  id: number;
  name: string;
  kind: string;
}

export interface EntryView {
  id: number;
  date: string;
  kind: string;
  amount: string;
  description: string | null;
  category_id: number;
  category_name: string;
}

export interface InvoiceView {
  id: number;
  unit_id: number;
  unit_code: string;
  period: string;
  due_date: string;
  amount: string;
  paid: string;
  status: string;
}

export interface PaymentView {
  invoice_id: number;
  amount: string;
  paid_at: string | null;
}

export interface CategoryTotal {
  category: string;
  amount: string;
}

export interface UnitSummary {
  unit_id: number;
  unit_code: string;
  billed: string;
  paid: string;
  pending: string;
  delinquent: string;
}

export interface BalanceSheet {
  period: string;
  expenses_by_category: CategoryTotal[];
  incomes_by_category: CategoryTotal[];
  result: string;
  per_unit: UnitSummary[];
}

export interface CondominiumView {
  id: number;
  name: string;
  address: string | null;
  active: boolean;
}

export interface RoleOverview {
  condominium_id: number;
  memberships: AssociationView[];
  unit_links: UnitLinkView[];
}

export interface AssociationView {
  user_id: number;
  email: string | null;
  person_name: string | null;
  active: boolean;
  functions: string[];
}

// ---------------------------------------------------------------------------
// Identity-token scoped calls (login, condominium listing/selection)
// ---------------------------------------------------------------------------

export const identityApi = {
  login(email: string, password: string): Promise<{ token: string }> {
    return request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },
  listCondominiums(identityToken: string): Promise<CondominiumBrief[]> {
    return request("/auth/condominiums", { authToken: identityToken });
  },
  selectCondominium(
    identityToken: string,
    condominiumId: number,
  ): Promise<{ token: string }> {
    return request(`/auth/condominiums/${condominiumId}/select`, {
      method: "POST",
      authToken: identityToken,
    });
  },
  listAllCondominiums(identityToken: string): Promise<CondominiumView[]> {
    return request("/admin/condominiums", { authToken: identityToken });
  },
  createCondominium(
    identityToken: string,
    body: { name: string; address: string | null },
  ): Promise<CondominiumView> {
    return request("/admin/condominiums", {
      method: "POST",
      authToken: identityToken,
      body: JSON.stringify(body),
    });
  },
};

export interface CondominiumBrief {
  id: number;
  name: string;
  address: string | null;
}

// ---------------------------------------------------------------------------
// Scoped-token calls (all domain data)
// ---------------------------------------------------------------------------

export const scopedApi = {
  // units
  listUnits(): Promise<UnitView[]> {
    return request("/units");
  },
  createUnit(body: { number: string; block?: string | null; unit_type?: string; fraction: string }): Promise<UnitView> {
    return request("/units", { method: "POST", body: JSON.stringify(body) });
  },
  updateUnit(unitId: number, body: Partial<{ number: string; block: string | null; unit_type: string; fraction: string; active: boolean }>): Promise<UnitView> {
    return request(`/units/${unitId}`, { method: "PATCH", body: JSON.stringify(body) });
  },
  deleteUnit(unitId: number): Promise<void> {
    return request(`/units/${unitId}`, { method: "DELETE" });
  },
  addParkingSpot(unitId: number, body: { identifier: string; spot_type?: string }): Promise<ParkingSpotView> {
    return request(`/units/${unitId}/parking`, { method: "POST", body: JSON.stringify(body) });
  },
  deleteParkingSpot(spotId: number): Promise<void> {
    return request(`/units/parking/${spotId}`, { method: "DELETE" });
  },

  // residents
  listResidents(): Promise<PersonView[]> {
    return request("/residents");
  },
  createResident(body: { name: string; cpf: string; phone?: string | null; email_contact?: string | null }): Promise<PersonView> {
    return request("/residents", { method: "POST", body: JSON.stringify(body) });
  },
  updateResident(personId: number, body: Partial<{ name: string; phone: string | null; email_contact: string | null }>): Promise<PersonView> {
    return request(`/residents/${personId}`, { method: "PATCH", body: JSON.stringify(body) });
  },
  addResidentLink(personId: number, body: { role: string; unit_id: number }): Promise<PersonView> {
    return request(`/residents/${personId}/links`, { method: "POST", body: JSON.stringify(body) });
  },
  removeResidentLink(personId: number, linkId: number): Promise<PersonView> {
    return request(`/residents/${personId}/links/${linkId}`, { method: "DELETE" });
  },
  createAccount(personId: number, body: { email: string; password: string }): Promise<{ person_id: number; email: string }> {
    return request(`/residents/${personId}/account`, { method: "POST", body: JSON.stringify(body) });
  },

  // vehicles
  listVehicles(): Promise<VehicleView[]> {
    return request("/vehicles");
  },
  createVehicle(body: { plate: string; model: string; color?: string | null; unit_id?: number; resident_id?: number | null }): Promise<VehicleView> {
    return request("/vehicles", { method: "POST", body: JSON.stringify(body) });
  },
  updateVehicle(vehicleId: number, body: Partial<{ model: string; color: string | null }>): Promise<VehicleView> {
    return request(`/vehicles/${vehicleId}`, { method: "PATCH", body: JSON.stringify(body) });
  },
  deleteVehicle(vehicleId: number): Promise<void> {
    return request(`/vehicles/${vehicleId}`, { method: "DELETE" });
  },

  // pets
  listPets(): Promise<PetView[]> {
    return request("/pets");
  },
  createPet(body: { name: string; species: string; breed?: string | null; resident_id?: number | null }): Promise<PetView> {
    return request("/pets", { method: "POST", body: JSON.stringify(body) });
  },
  updatePet(petId: number, body: Partial<{ name: string; species: string; breed: string | null }>): Promise<PetView> {
    return request(`/pets/${petId}`, { method: "PATCH", body: JSON.stringify(body) });
  },
  deletePet(petId: number): Promise<void> {
    return request(`/pets/${petId}`, { method: "DELETE" });
  },

  // common areas
  listCommonAreas(): Promise<CommonAreaView[]> {
    return request("/common-areas");
  },
  createCommonArea(body: { name: string; description?: string | null; capacity?: number | null }): Promise<CommonAreaView> {
    return request("/common-areas", { method: "POST", body: JSON.stringify(body) });
  },
  updateCommonArea(areaId: number, body: Partial<{ name: string; description: string | null; capacity: number | null }>): Promise<CommonAreaView> {
    return request(`/common-areas/${areaId}`, { method: "PATCH", body: JSON.stringify(body) });
  },
  deleteCommonArea(areaId: number): Promise<void> {
    return request(`/common-areas/${areaId}`, { method: "DELETE" });
  },

  // bookings
  listBookings(): Promise<BookingView[]> {
    return request("/bookings");
  },
  createBooking(body: { area_id: number; start_at: string; end_at: string; unit_id: number; person_id?: number | null }): Promise<BookingView> {
    return request("/bookings", { method: "POST", body: JSON.stringify(body) });
  },
  cancelBooking(bookingId: number): Promise<BookingView> {
    return request(`/bookings/${bookingId}/cancel`, { method: "POST" });
  },

  // chart of accounts
  listCategories(): Promise<CategoryView[]> {
    return request("/chart-accounts");
  },
  createCategory(body: { name: string; kind: string }): Promise<CategoryView> {
    return request("/chart-accounts", { method: "POST", body: JSON.stringify(body) });
  },
  updateCategory(categoryId: number, body: Partial<{ name: string; kind: string }>): Promise<CategoryView> {
    return request(`/chart-accounts/${categoryId}`, { method: "PATCH", body: JSON.stringify(body) });
  },

  // financial
  listEntries(): Promise<EntryView[]> {
    return request("/entries");
  },
  createEntry(body: { date: string; amount: string; category_id: number; kind: string; description?: string | null }): Promise<EntryView> {
    return request("/entries", { method: "POST", body: JSON.stringify(body) });
  },
  deleteEntry(entryId: number): Promise<void> {
    return request(`/entries/${entryId}`, { method: "DELETE" });
  },
  generateInvoices(period: string): Promise<InvoiceView[]> {
    return request("/invoices/generate", { method: "POST", body: JSON.stringify({ period }) });
  },
  listInvoices(): Promise<InvoiceView[]> {
    return request("/invoices");
  },
  recordPayment(invoiceId: number, body: { amount: string; paid_at?: string | null }): Promise<PaymentView> {
    return request(`/invoices/${invoiceId}/payments`, { method: "POST", body: JSON.stringify(body) });
  },
  balanceSheet(period: string): Promise<BalanceSheet> {
    return request(`/balance-sheet?period=${encodeURIComponent(period)}`);
  },

  // admin: roles & associations (scoped)
  roleOverview(): Promise<RoleOverview> {
    return request(scopedPath(`/roles`));
  },
  putFunctions(userId: number, roles: string[]): Promise<RoleOverview> {
    return request(scopedPath(`/users/${userId}/functions`), {
      method: "PUT",
      body: JSON.stringify({ roles }),
    });
  },
  addUnitLink(personId: number, body: { role: string; unit_id: number }): Promise<RoleOverview> {
    return request(scopedPath(`/people/${personId}/links`), {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  removeUnitLink(linkId: number): Promise<RoleOverview> {
    return request(scopedPath(`/links/${linkId}`), { method: "DELETE" });
  },
  listAssociations(): Promise<AssociationView[]> {
    return request(scopedPath(`/associations`));
  },
  setAssociation(userId: number, active: boolean): Promise<AssociationView> {
    return request(scopedPath(`/associations/${userId}`), {
      method: "PUT",
      body: JSON.stringify({ active }),
    });
  },
  deleteAssociation(userId: number): Promise<void> {
    return request(scopedPath(`/associations/${userId}`), { method: "DELETE" });
  },

  // admin: condominium updates/deactivation (scoped to the selected condominium)
  updateCondominium(body: Partial<{ name: string; address: string | null }>): Promise<CondominiumView> {
    return request(scopedPath(``), {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  },
  deactivateCondominium(): Promise<void> {
    return request(scopedPath(``), { method: "DELETE" });
  },
};

// The scoped admin endpoints need the active condominium id; kept in sync by
// setScopedToken through AuthProvider.
let currentScope: { condominium_id: number } | null = null;

export function setCurrentScope(scope: { condominium_id: number } | null): void {
  currentScope = scope;
}

/**
 * Scope-dependent paths without an active scope must surface as an
 * unauthenticated error (and redirect flow), never a TypeError.
 */
function scopedPath(suffix: string): string {
  if (!currentScope) {
    throw new ApiError(401, "no active condominium scope");
  }
  return `/admin/condominiums/${currentScope.condominium_id}${suffix}`;
}

export default request;
