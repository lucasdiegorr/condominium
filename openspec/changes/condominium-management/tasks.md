## 1. Infrastructure and scaffold

- [x] 1.1 Create monorepo structure: `backend/`, `frontend/`, `docker-compose.yml`, `.env.example`, `README.md`
- [x] 1.2 Define the backend Dockerfile (Python + FastAPI) and an entrypoint that runs `alembic upgrade head`
- [x] 1.3 Define the frontend Dockerfile (static build served by a web server) and `docker-compose.yml` with PostgreSQL 16
- [x] 1.4 FastAPI scaffold: settings (pydantic-settings), app, async database session, `/health` endpoint
- [x] 1.5 React (Vite) scaffold: routing with a public `/login` screen, authenticated-route guard and an i18n layer (translation catalog, English default)

## 2. Data model and migrations (Alembic)

- [x] 2.1 `people` (unique CPF) and `users` (unique e-mail, hashed password) models + migration
- [x] 2.2 `condominiums` + `memberships` (user × condominium) models + migration
- [x] 2.3 Role models: `membership_roles` (functions: síndico, conselho) and `member_links` (person × unit: condômino, inquilino) + migration
- [x] 2.4 `units` (ideal fraction with validation) and `parking_spots` models + migration
- [x] 2.5 `common_areas` and `bookings` with atomic overlap prevention + migration
- [x] 2.6 Financial models `account_categories`, `entries`, `invoices`, `payments` + migration
- [x] 2.7 `vehicles` (unique plate per condominium) and `pets` models + migration
- [x] 2.8 Initial seeds: default roles, bootstrap administrator user, suggested financial categories

## 3. Authentication and session (user-auth)

- [x] 3.1 Endpoint `POST /auth/login`: returns only the identity token, generic 401, blocks inactive users
- [x] 3.2 Endpoint `GET /auth/condominiums`: listing restricted to the user's active associations
- [x] 3.3 Endpoint `POST /auth/condominiums/{id}/select`: validates the association and issues a scoped token (condominium + roles), 403 without leaking existence
- [x] 3.4 `current_condominium` dependency and protection of all data routes (401/403)
- [x] 3.5 Short TTL for scoped tokens with association/role revalidation on renewal
- [x] 3.6 Integration tests for the complete authentication flow (login → listing → selection → negatives)

## 4. RBAC and role administration (access-control)

- [x] 4.1 Centralized permission matrix in the backend (role → declarative permissions)
- [x] 4.2 Administrator role-management endpoints: create/edit/remove `membership_roles` and `member_links` (unit selection for links)
- [x] 4.3 Global administrator operation in any condominium (elevated permissions inside the scope)
- [x] 4.4 Rule: creating a unit link for a user guarantees a `membership`; a resident without an account gets only a `member_link`
- [ ] 4.5 Administrator screen: binding a user/person to roles per condominium (unit selection when applicable)
- [x] 4.6 Permission tests per role (403 for actions outside the role, including function management by the síndico)

## 5. Condominiums (condominium-management)

- [x] 5.1 Condominium CRUD endpoints by the administrator, with deactivation preserving data
- [x] 5.2 User ↔ condominium association endpoints by the administrator
- [x] 5.3 Central `condominium_id` filter applied to all domain repositories
- [x] 5.4 Cross-condominium isolation tests (cross access responds 403 without exposing data)

## 6. Persons and residents (people)

- [x] 6.1 Person registration endpoints (síndico in own condominium; global administrator)
- [x] 6.2 Unit-link endpoints (condômino/inquilino) with multiple links per person and per unit
- [x] 6.3 User account creation linked to a person (unique e-mail)
- [ ] 6.4 Residents screen (listing and registration with links)

## 7. Units and parking spots (unit-management)

- [x] 7.1 Unit CRUD endpoints with ideal-fraction validation (positive and sum ≤ 100%)
- [x] 7.2 Parking-spot endpoints tied to units of the same condominium
- [ ] 7.3 Units and parking spots screen

## 8. Vehicles and pets (vehicles-pets)

- [ ] 8.1 Vehicle endpoints with responsible resident + unit and unique plate per condominium
- [ ] 8.2 Vehicle self-service: residents manage only their own; síndico/administrator the whole condominium
- [ ] 8.3 Pet endpoints linked to the resident with self-service
- [ ] 8.4 Vehicles and pets screens per profile

## 9. Common areas and bookings (common-area-scheduling)

- [ ] 9.1 Common-area endpoints (síndico/administrator)
- [ ] 9.2 Booking endpoints with atomic overlap checking and reserved/cancelled status
- [ ] 9.3 Booking scope: residents only their own; síndico/administrator all
- [ ] 9.4 Booking screen with conflict display and cancellation

## 10. Financial (financial)

- [ ] 10.1 Chart-of-accounts endpoints per condominium (expense/income)
- [ ] 10.2 Expense and income entry endpoints
- [ ] 10.3 Ideal-fraction allocation and monthly invoice generation per unit
- [ ] 10.4 Manual payment recording and paid/pending/overdue status
- [ ] 10.5 Balance sheet: expenses × incomes per category, period result, per-unit summary
- [ ] 10.6 Financial screens scoped by role (síndico operation; resident consultation of their own unit)

## 11. Frontend — application and UX

- [ ] 11.1 Public login and condominium selection flow (scoped token)
- [ ] 11.2 API/state layer with scoped-token propagation, field visibility per role and UI text via i18n (English default; pt-BR only in the translation catalog)
- [ ] 11.3 Síndico operation screens (units, residents, vehicles/pets, bookings, financial)
- [ ] 11.4 Administrator screens (condominiums, users, roles)
- [ ] 11.5 Resident self-service (bookings, own vehicles/pets, financial of their own unit)
- [ ] 11.6 401/403 handling (expired/no scope) redirecting to selection/login

## 12. Integration and deployment

- [ ] 12.1 Docker Compose working end to end (postgres → backend → frontend)
- [ ] 12.2 Automatic migrations at startup with idempotent seeds
- [ ] 12.3 Integration tests of the main flows of each capability
- [ ] 12.4 Documentation (README with setup, environment variables, execution) and final check (`openspec validate`)
