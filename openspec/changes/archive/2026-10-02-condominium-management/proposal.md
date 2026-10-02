## Why

Brazilian condominiums still manage residents, parking spots, common-area bookings and financial control with spreadsheets and paper records. No centralized platform exists today, in this project, to serve **multiple condominiums** with a flexible role model (síndico, conselho, condômino, inquilino) and resident self-service. This change lays the foundation (v1) of this product: a multi-condominium web application with a FastAPI backend, React frontend, PostgreSQL and Docker Compose deployment.

## What Changes

- **New multi-condominium product**: a platform where a user can belong to several condominiums, with roles defined **per condominium**.
- **Person ≠ User model**: the physical person is the record (CPF, name, contact) and may exist without a login; the user is the access account (e-mail + password) linked to a person.
- **Per-condominium role model** with two distinct groups: **functions** (síndico, conselho — condominium level) and **unit links** (condômino, inquilino — unit level). The administrator screen manages roles uniformly (role → unit selection when applicable).
- **Two-stage JWT authentication**: login returns only the identity token; condominium listing is a dedicated endpoint filtered by the user's associations; condominium selection issues a **scoped token** containing `condominium_id` and roles. All data routes require the scoped token and validate the scope — the login response exposes nothing about condominiums (attack-surface mitigation).
- **RBAC with permission matrix**: global system administrator with full access (can operate and maintain data in any condominium), síndico in charge of day-to-day operation, condômino/inquilino with self-service restricted to their own universe (own bookings, own vehicles/pets, financial consultation of their own unit).
- **Units (broader than apartments)**: registration of condominium units with ideal fraction and parking spots tied to units.
- **Residents, vehicles and pets**: a vehicle is registered with **responsible resident + unit** (owner and tenant can use the spot); a pet is linked to the resident.
- **Simple common-area booking**: common areas registered + bookings with time-conflict checking and status — no payment or approval flow (future evolution).
- **Finance level 2 (no execution)**: per-condominium configurable chart of accounts, expense and income entries, allocation by ideal fraction, monthly invoice per unit with paid/pending/overdue status (manual payment record) and balance sheet. The system **keeps** the information; execution (bank slips/PIX, accounting) is external.
- **Stack and deployment**: FastAPI backend (Python), React frontend, PostgreSQL, JWT; everything packaged with Docker and orchestrated by Docker Compose.
- **Public page**: only the login screen; every other page requires authentication.
- **Language and internationalization**: API endpoints and pages are in English; user interface strings support internationalization (i18n) through a translation catalog — **Brazilian Portuguese appears only in the translation files (pt-BR)**.

## Capabilities

### New Capabilities

- `user-auth`: two-stage JWT authentication (identity → condominium selection → scoped token), route protection, login page as the only public route.
- `access-control`: per-condominium roles (functions × unit links), per-role permission matrix, global administrator, role management screen.
- `condominium-management`: condominium registration and maintenance, user ↔ condominium association (N:N).
- `people`: registration of physical persons, user accounts (person ≠ user), unit links (condômino/inquilino).
- `unit-management`: condominium units with ideal fraction and tied parking spots.
- `vehicles-pets`: vehicle registration (resident + unit) and pets (resident).
- `common-area-scheduling`: common areas and bookings with time-conflict checking and status.
- `financial`: chart of accounts, expense/income entries, allocation by ideal fraction, per-unit invoices, payment recording and balance sheet.

### Modified Capabilities

None — the repository has no existing specs (new product).

## Impact

- **Repository**: complete scaffold — `backend/` (FastAPI), `frontend/` (React), `docker-compose.yml`, initialization scripts.
- **Backend (FastAPI)**: `auth` routes (login, condominiums, scope selection), SQLAlchemy models, Alembic migrations, authentication and RBAC dependencies, seeds for default roles.
- **Frontend (React)**: login screen (only public), condominium selection, screens per role (admin, síndico, resident self-service), scoped-session state management and an i18n layer (English UI by default; only the translation catalog holds Brazilian Portuguese).
- **Database (PostgreSQL)**: multi-tenant schema centered on `condominium_id`; tables for persons, users, associations, units, parking spots, common areas, bookings, vehicles, pets, chart of accounts, entries, invoices.
- **Security**: two-stage JWT, scope validation by `condominium_id` on all routes, RBAC matrix.
- **Documentation**: all generated documentation is written in English.
- **Dependencies**: Python (FastAPI, SQLAlchemy, Alembic, PyJWT, pydantic), Node/React (Vite), PostgreSQL 16, Docker.
