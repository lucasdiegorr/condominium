# AGENTS.md

## Project status

- Planning-stage repo: **no application code yet**. The v1 plan lives in `openspec/changes/condominium-management/` (`proposal.md`, `specs/`, `design.md`, `tasks.md`). Read them before writing any code — implementation follows the tasks there.
- Product: web platform to manage **multiple condominiums** (units, residents, vehicles/pets, common-area bookings, financial record-keeping) for síndicos, owners and tenants.

## Local setup

- After cloning, run `pre-commit install` once to activate the git hooks (`no-commit-to-branch` blocks commits on `master`/`main`, `openspec validate` runs on every commit, and lint/format checks activate once code exists). Keep hook revisions current with `pre-commit autoupdate`.

## Non-negotiables

- **Every feature MUST start as an OpenSpec change** — use `/opsx-propose`, then implement via `/opsx-apply`, then `/opsx-sync` + `/opsx-archive` when done (skills + commands in `.opencode/`). No ad-hoc features outside an approved change; run `openspec validate <change> --type change` before shipping an artifact.
- **NEVER commit to master directly.** Always work on a branch or worktree (see the `using-git-worktrees` skill); integrate via review/merge.
- **English in all docs and code.** All generated documentation and code (endpoints, pages) are written in English (e.g., `/auth/condominiums/...`). User-facing UI strings MUST go through i18n (translation catalog), and **Brazilian Portuguese appears only in the translation files (pt-BR)** — never hardcode user-visible text in components or write new documentation in Portuguese.
  - Brazilian domain terms (síndico, condômino, inquilino, conselho) appear in English docs as quoted role identifiers; their readable labels live in the i18n catalog.

## Stack (from design.md)

- Backend: Python **FastAPI** + SQLAlchemy (async) + **Alembic** migrations + PyJWT.
- Frontend: **React + Vite** (with i18n layer).
- DB: PostgreSQL 16. Deploy: Docker Compose (postgres/backend/frontend); `alembic upgrade head` runs on backend startup.

## Architecture essentials (details in design.md)

- **JWT in two stages**: login returns only an identity token; data access requires a short-lived *scoped* token per condominium (carries `condominium_id` + roles). Never return the condominium list at login (attack vector); non-membership selection responds 403 without revealing existence.
- **Multi-tenancy**: every domain table carries `condominium_id`; all access flows through a central scope dependency — never query domain data without the scope filter.
- **Person ≠ user**: residents can exist without a login; user accounts are linked to a person.
- **Roles are per condominium**: condominium functions (síndico, conselho) vs unit links (condômino, inquilino). The global admin can operate inside any condominium.
- **Finance is record-keeping only** (entries + rateio by fração ideal + monthly invoices per unit + manual payment status + balance sheet). NEVER implement payment execution (boleto/PIX) or bank integration — this is an explicit non-goal.
- **Common-area bookings are simple**: no payment, no approval flow.
- Domain term: **Unit** (unidade) is broader than apartment and is the entity name used in models/APIs.
