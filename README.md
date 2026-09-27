# Condominium Management

Multi-condominium web platform: units, residents, vehicles/pets, common-area
bookings and financial record-keeping for síndicos, owners and tenants.

> Full setup, environment and execution documentation is provided in
> [Chapter 12 of the implementation plan](openspec/changes/condominium-management/tasks.md)
> and finalized in the README as part of task 12.4.

## Stack

- **Backend**: Python FastAPI + SQLAlchemy (async) + Alembic + PyJWT (argon2 password hashing)
- **Frontend**: React + Vite + TypeScript (i18n, English default; pt-BR only in the catalog)
- **Database**: PostgreSQL 16
- **Deployment**: Docker Compose (postgres / backend / frontend)

## Repository layout

```
backend/    FastAPI application (app/), Alembic migrations, tests
frontend/   React + Vite application (src/)
openspec/   OpenSpec changes and specs (source of truth for planning)
```

## Quick start (Docker Compose)

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:8080
- API docs: http://localhost:8000/docs
