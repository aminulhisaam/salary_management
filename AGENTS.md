# AGENTS.md

Instructions for any coding agent (Codex) working in this repo. Read this before making
changes — it points to the planning docs and states constraints that are already decided,
so they shouldn't be re-litigated mid-build.

## What this is
Web-based salary management software for ACME's HR Manager — replaces spreadsheet-based
salary tracking for 10,000 employees across multiple countries. Full detail is in `docs/`,
not repeated here.

## Read these first, in order
1. `docs/requirements.md` — scope: what's in, what's deliberately out, and why
2. `docs/planning.md` — feature backlog and the build order to follow
3. `docs/schema.md` — the `users` / `employees` / `salaries` tables, columns, indexes
4. `docs/decisions.md` — the reasoning behind every non-obvious schema/architecture call

If a task seems to conflict with something in these docs, flag it and ask rather than
silently deviating — these were decided deliberately, not defaults left unexamined.

## Stack (already chosen — do not re-propose alternatives)
- Backend: FastAPI (Python), SQLAlchemy (async) + Alembic, SQLite locally via
  `DATABASE_URL` env var (Postgres-ready without code changes)
- Auth: `passlib[bcrypt]` for hashing, `python-jose` for JWT — real multi-user login,
  single `hr_admin` role for all users in v1 (see `decisions.md`)
- Frontend: React + Vite, component library TBD at build time (shadcn/ui or MUI)
- Testing: pytest + httpx (backend), React Testing Library (frontend)
- Lint/format: ruff + black (backend, config in `backend/pyproject.toml`), oxlint +
  Prettier (frontend, config in `frontend/`)

## Hard constraints — implement as specified, don't redesign
- **Money**: `DECIMAL(12,2)`, never float. Currency stored alongside every amount.
- **Salary history**: append-only rows in `salaries`, keyed by `effective_date`. Never
  update or delete a salary row in place — a change is always a new row.
- **Current salary**: denormalized onto `employees.current_salary_amount` /
  `_currency` / `_id`, written in the same transaction as every `salaries` insert. This
  is a read-performance optimization for the 10k-row list/dashboard — `salaries` remains
  the source of truth for history.
- **Department/country**: plain indexed `TEXT` columns, not FK'd lookup tables. The
  create/edit employee form must constrain these to a dropdown of known values (not
  free text) — this is the data-integrity mitigation instead of full normalization.
- **Auth**: single JWT access token, no refresh-token flow in v1. Every
  employee/salary/analytics route depends on one `get_current_user` dependency —
  centralize authorization there, not per-route inline checks.
- **No currency conversion**: aggregates are computed within a currency, never blended
  across currencies into one number.
- **Soft delete**: employees are marked `status = inactive`, never row-deleted.

## Build order
Follow `docs/planning.md`'s sequencing. Current repo state: scaffolding and lint config
are done (see git log). Next: backend models & migrations (`schema.md` → SQLAlchemy
models → Alembic initial migration), then seed script, then backend CRUD + tests, then
analytics endpoints, then frontend (list → detail → dashboard), then a test-coverage
pass, then deploy + demo video + README.

Do not jump ahead to frontend work before the backend endpoints it depends on exist and
are tested.

## Commit discipline
One feature (or one clearly-scoped chunk of one) per commit, tests included in the same
commit as the code they test — not batched into a separate "add tests" commit at the
end. Commit messages: short imperative summary line, blank line, bullet detail if useful.
This mirrors the existing commits (`git log --oneline`) — keep that pattern.

## Running things locally
```
# backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload

# frontend
cd frontend && npm install && npm run dev
```
Lint: `ruff check .` + `black --check .` (backend), `npm run lint` (frontend).
Tests: `pytest` (backend), `npm test` (frontend, once tests exist).

## What not to do
- Don't add role tiering, currency conversion, or an employee self-service view — these
  are explicitly out of scope for v1 per `requirements.md`.
- Don't switch money storage to float or integer minor units — `decisions.md` explains
  why `DECIMAL(12,2)` was chosen.
- Don't normalize department/country into lookup tables without discussing it first —
  it's a deliberate scope trade-off, not an oversight.
