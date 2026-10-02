# Condominium Management

Web platform to manage **multiple condominiums**: units, residents,
vehicles/pets, common-area bookings and financial record-keeping — for
síndicos, owners and tenants.

## Capabilities

- **Multi-tenancy**: every domain record belongs to a condominium; all data
  access flows through a central scope filter.
- **Roles per condominium**: functions (síndico, conselho) and unit links
  (condômino, inquilino). A global administrator can operate inside any
  condominium.
- **Residents**: a person may exist without a login; user accounts are linked
  to a person. A unit link guarantees an active association (membership).
- **Units**: ideal fraction (rateio) for expense allocation, parking spots.
- **Vehicles & pets**: registered to residents; residents manage only their own.
- **Common-area bookings**: simple reservations — no payment, no approval flow.
- **Financial record-keeping**: chart of accounts, income/expense entries,
  ideal-fraction allocation, monthly invoices per unit, manual payment status,
  balance sheet. **Payments are recorded, never executed** (no boleto/PIX or
  bank integration — explicit non-goal).

## Stack

- **Backend**: Python FastAPI + SQLAlchemy (async) + Alembic + PyJWT
- **Frontend**: React + Vite + TypeScript (i18n — English default; Brazilian
  Portuguese only in the translation catalog)
- **Database**: PostgreSQL 16
- **Deployment**: Docker Compose (`postgres` / `backend` / `frontend`)

## Security model

Two-stage JWT:

1. `POST /auth/login` returns only an **identity token**.
2. `GET /auth/condominiums` lists the associations; `POST /auth/condominiums/{id}/select`
   exchanges the identity token for a short-lived **scoped token** carrying
   `condominium_id` + roles.

The condominium list is never returned at login, and selecting a condominium
the user is not a member of responds 403 without revealing its existence.

## Repository layout

```
backend/    FastAPI application (app/), Alembic migrations, tests
frontend/   React + Vite application (src/)
openspec/   OpenSpec change specs (planning source of truth)
```

## Quick start (Docker Compose)

Prerequisites: Docker with the Compose plugin.

```bash
cp .env.example .env
docker compose up --build
```

- **Frontend**: http://localhost:8080
- **API docs**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health

On startup the backend runs `alembic upgrade head` and applies idempotent
seeds (default roles, bootstrap administrator, suggested financial
categories). The bootstrap administrator uses the `SEED_ADMIN_*` variables
(first run only).

## Local development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
```

Requires a running PostgreSQL and a `DATABASE_URL`. Apply migrations and start:

```bash
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

Run the test suite (needs the database available):

```bash
pytest
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The dev server proxies `/api/*` to `http://localhost:8000` (see
`vite.config.ts`). Production build + type check:

```bash
npm run build
```

## Environment variables

| Variable | Default | Description |
| --- | --- | --- |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `cond` / `cond_pass` / `condominium` | PostgreSQL credentials (compose) |
| `DATABASE_URL` | `postgresql+asyncpg://cond:cond_pass@postgres:5432/condominium` | Backend database URL |
| `JWT_SECRET` | `change-me-in-production` | **Change in production** |
| `JWT_ALGORITHM` | `HS256` | Token signing algorithm |
| `IDENTITY_TOKEN_TTL_MINUTES` | `60` | Identity token lifetime |
| `SCOPED_TOKEN_TTL_MINUTES` | `20` | Scoped token lifetime |
| `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` | `admin@example.com` / `admin123456` | Bootstrap administrator (first run) |
| `VITE_API_BASE_URL` | `/api` | Frontend API base path (behind the nginx proxy) |

## Roles

| Code | Meaning | Scope |
| --- | --- | --- |
| `sindico` | Building manager | Per condominium (function) |
| `conselho` | Fiscal/deliberative council | Per condominium (function) |
| `condomino` | Owner linked to a unit | Per unit |
| `inquilino` | Tenant linked to a unit | Per unit |
| `global_admin` | Platform administrator | Any condominium |

## Documentation

- **Planning & specs**: `openspec/changes/condominium-management/`
  (`proposal.md`, `specs/`, `design.md`, `tasks.md`)
- **API**: interactive docs at `/docs` (OpenAPI)
