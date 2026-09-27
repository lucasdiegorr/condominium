## Context

See proposal.md - Why and What Changes for motivation and scope. The repository is empty (new product) — this document defines the technical foundation: FastAPI backend, React frontend, PostgreSQL and Docker Compose deployment. The product decisions (role matrix, person ≠ user, finance level 2, simple bookings) are consolidated in the proposal and the specs; this document covers the "how".

## Goals / Non-Goals

**Goals:**
- Layered backend architecture (routes → services → repositories) that supports incremental evolution.
- Multi-condominium scoping as a cross-cutting guarantee: every domain data query and write goes through `condominium_id`.
- Security by default: short-lived scoped tokens, responses 401/403 without leaking information about other condominiums.
- A data model faithful to the decisions: person ≠ user, functions × unit links, vehicle = resident + unit, pet = resident.
- Delivery packaged in containers (postgres, backend, frontend) via Docker Compose.
- All generated documentation and code written in English; Brazilian Portuguese exists only in the UI translation catalog (pt-BR).

**Non-Goals:**
- Payment execution (bank slips, PIX, bank integration) — explicit product decision.
- Notifications (e-mail/push) — future evolution.
- Booking approval and payment flows for common areas.
- Full accounting (books, formal DRE reporting) — the scope is the balance sheet.

## Decisions

### D1: Two-stage JWT authentication (identity → scope)
Two token types:
- **Identity token**: issued at login (e-mail + password), carries only the user identity; used for the condominium listing and scope selection.
- **Scoped token**: issued at `POST /auth/condominiums/{id}/select` after validating the association in the database; carries `condominium_id`, `user_id` and the user's roles in that condominium. Short TTL (15–30 min); renewal revalidates associations and roles in the database.

Alternatives considered: a single token carrying the association list — rejected because it would expose the condominium list in the login response (the attack vector identified by the product) and widen the attack surface unnecessarily. The two-stage split keeps every data route dependent on explicit association validation.

### D2: Multi-tenancy by `condominium_id` with a central dependency
Every domain data table carries `condominium_id` (with composite indexes `(condominium_id, ...)`). In FastAPI, a `current_condominium` dependency validates the scoped token, checks the active association and injects the scope into routes; domain repositories receive the scope as a mandatory parameter. Centralizing the filter is the main mitigation against the "forgotten filter" mistake — the classic multi-tenancy failure.

### D3: Person ≠ user
Tables `people` (name, unique CPF, contact) and `users` (unique e-mail, hashed password, active), with an optional one-to-one person → user relation. Residents are registered as persons and may never log in. Resident registration (condômino/inquilino unit link) is done by the síndico; accounts and roles are managed by the administrator.

### D4: Associations and roles (functions × unit links)
- `member_links` (person × unit): the residents roster — condômino/inquilino links on the unit. Residents can exist without a user account.
- `memberships` (user × condominium): base access association; enables condominium listing and selection.
- `membership_roles`: user functions in the condominium (síndico, conselho), condominium level.
- When assigning a unit link to a user (for example, the administrator creates "condômino" for user X in condominium Y), the roles service also guarantees the `membership` — without it the user cannot select the condominium. For a resident without an account, only the `member_link` is registered.
- The scoped token carries the combined roles: functions (via `membership_roles`) + links (via `member_links` of the user's person).
- The **permission matrix** is code (role → permissions mapped in the backend), validated declaratively and testably. The global administrator receives full permission when operating inside a condominium.

### D5: Financial model (level 2, no execution)
`account_categories` (chart of accounts, type expense/income) → `entries` (financial entries) → allocation proportional to the ideal fraction → monthly `invoices` per unit (due amount) → `payments` (status paid/pending/overdue, manual recording). The balance sheet is derived from aggregate queries (expenses × incomes per category, period result, per-unit summary). No integration with payment channels.

### D6: Common-area bookings
`common_areas` + `bookings` (start, end, status reserved/cancelled). Overlap checking is atomic: an exclusion constraint in PostgreSQL (`EXCLUDE USING gist` with `tstzrange` and `area_id` with the equality operator) or, if the extension is unavailable, a serializable transaction plus verification. Kept simple: no payment and no approval (as declared in the specs).

### D7: Implementation stack
- Backend: Python/FastAPI + SQLAlchemy (async) + Alembic + PyJWT; strong password hashing (bcrypt or argon2); validation with Pydantic.
- Frontend: React + Vite with an i18n layer and an English interface, managing the scoped token and the roles to show/hide fields according to the role; UI strings always come from the translation catalog, never hardcoded.
- Language: API endpoints and pages in English (e.g., `/auth/condominiums/...`); the user interface supports i18n with English as the default language and **Brazilian Portuguese only in the translation files (pt-BR)**; all generated documentation is written in English.
- Database: PostgreSQL 16.
- Deployment: Docker Compose (postgres, backend, frontend); migrations applied at backend startup.

### D8: Migrations and seeds
Alembic for schema evolution. Initial seeds: default roles (síndico, conselho, condômino, inquilino), bootstrap administrator user, and a set of suggested financial categories (maintenance, security, cleaning, workers) created per condominium.

## Risks / Trade-offs

- [Forgotten `condominium_id` filter in some query] → Centralized filter in the `current_condominium` dependency + integration tests per capability covering cross-condominium access.
- [Scoped token with stale roles (role changed after issuance)] → Short TTL + revalidation of association/roles on renewal; sensitive operations may re-check the database.
- [Unbalanced ideal-fraction totals (units registered incrementally)] → Write-time validation (sum ≤ 100%) and allocation normalized by the effectively registered total.
- [Booking race (two simultaneous reservations for the same slot)] → PostgreSQL exclusion constraint / serializable transaction.
- [Costly per-unit balance sheet as the volume grows] → Composite indexes `(condominium_id, period)` and dedicated aggregate queries.

## Migration Plan

- **v1 deploy**: `docker compose up` → postgres starts → backend runs `alembic upgrade head` (entrypoint) and seeds → frontend served from the static build (or dev server in development).
- **Rollback**: `alembic downgrade -1`; previous backend versions stay compatible with the schema; data preserved.
- **Future evolution** (refresh authentication, notifications, executable billing) enters as new OpenSpec changes without breaking the existing specs.

## Open Questions

- **Conselho**: role present in the catalog with read permissions; council operation (approvals, minutes) may mature in a future change without altering the model.
- **Password recovery**: "forgot password" flow (reset e-mail) is undefined; it can be added later without changing the current authentication spec, which covers only login.
- **Notifications**: deferred by explicit product decision.
