# Planning — Feature Backlog & Build Order

## Stack
- Backend: FastAPI (Python), SQLite for local dev, Postgres-ready via a `DATABASE_URL`
  env var — enables local development without infra overhead while keeping a hosted
  deploy a config change rather than a rewrite.
- Auth: `passlib[bcrypt]` for password hashing, `python-jose` for issuing/verifying JWTs.
- Frontend: React (Vite) + a component library selected at build time (shadcn/ui or MUI),
  to avoid hand-rolling table/pagination/form components at this scale.
- ORM: SQLAlchemy (async) + Alembic for migrations, to keep the SQLite→Postgres swap clean.
- Testing: pytest + httpx on the backend, React Testing Library on the frontend.
- Containerization: Docker for both services from the start, so a free-tier deploy
  (Render/Fly.io for the API, Vercel for the frontend) is close to copy-paste rather than
  something figured out at the end.

## Auth posture for v1
Real multi-user auth, with a single role for everyone:
- `users` table: id, email (unique), hashed_password, role (default `"hr_admin"`), created_at
- `POST /auth/register`, `POST /auth/login` (returns a JWT access token)
- A single FastAPI dependency (`get_current_user`) decodes the JWT and loads the user;
  every employee/salary/analytics route depends on it. Authorization is centralized here
  rather than via inline role checks per route, so role tiering later is a change to this
  one place, not a rewrite of every endpoint.
- Frontend: login/register pages, an auth context holding the token (in-memory + httpOnly
  cookie refresh vs localStorage decided at build time), and a protected route wrapper
  that redirects unauthenticated users to `/login`.

## Feature Backlog
The assignment calls for fully functional, end-to-end software, so the backlog below is
treated as the full build target rather than split by time constraints. Items are grouped
by dependency order and by how core they are to the HR-Manager persona, not by "nice to
have."

### Core platform
- [ ] Schema: `users`, `employees`, `salaries` (history via effective_date), indexes on
      `employee_id`, `department`, `country`
- [ ] Auth: register, login (JWT), `get_current_user` dependency guarding all
      employee/salary/analytics routes; frontend login page + protected routes
- [ ] Seed script: 10,000 employees, realistic department/country/band distribution,
      deterministic (fixed random seed); plus a small set of seed HR users for login/demo
- [ ] Config-driven DB connection (env var), Docker for backend + frontend
- [ ] requirements.md, planning.md, decisions.md committed as artifacts

### Employee & salary management
- [ ] Employee list: paginated, search by name/email, filter by department/country/band
- [ ] Employee detail: profile + current salary + salary history timeline
- [ ] Create/edit employee
- [ ] Add salary record (a new effective-dated entry, never an overwrite)
- [ ] CSV bulk import for employees/salaries

### Answering "how does the org pay people"
- [ ] Insights dashboard: headcount & avg/median salary by department and country, band
      distribution, min/max
- [ ] Filter/query builder UI on top of the dashboard (compose multiple filters)

### Quality & delivery
- [ ] Unit/integration tests written alongside each backend feature, not batched at the end
- [ ] Deployed public URL (Render/Fly + Vercel)
- [ ] Demo video

### Enhancements beyond core scope
Kept separate from the core backlog because they extend the product beyond what the brief
strictly asks for, not because of time pressure — built once the core system is solid and
demonstrably correct.
- [ ] Natural-language question box → translated to a filtered query (LLM-backed)
- [ ] Pay-equity cut (e.g. avg salary by gender, if that field is added)
- [ ] Role tiering (Admin vs read-only Viewer), building on the existing `role` field

## Fields still to finalize during schema design (Step 5)
Beyond the core fields in requirements.md, gender, performance rating, and a
manager/reporting line are evaluated at schema time and added only if they materially
improve the insights dashboard. Whatever is added — or deliberately left out — is
documented in decisions.md.

## Build sequencing
Following the phase/step plan laid out for the assessment:
Phase 0 (this doc + requirements.md) → Phase 1 (schema + decisions.md) →
Phase 2 (scaffold → seed → backend CRUD → analytics endpoints → frontend
list/detail/dashboard) → Phase 3 (test pass) → Phase 4 (deploy, video, README,
AI-usage log).
