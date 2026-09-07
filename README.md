# Salary Management Software

Web-based salary management for ACME's HR Manager — replaces spreadsheet-based salary
tracking for 10,000 employees across multiple countries.

## Docs
- [`docs/requirements.md`](docs/requirements.md) — scope, in/out of scope, and why
- [`docs/planning.md`](docs/planning.md) — feature backlog and build order
- [`docs/schema.md`](docs/schema.md) — data model
- [`docs/decisions.md`](docs/decisions.md) — architecture trade-offs

## Structure
```
backend/    FastAPI app, SQLAlchemy models, tests
frontend/   React (Vite) app
seed/       Seed script for 10,000 employees + demo users
docs/       Requirements, planning, schema, decisions
```

## Running locally
Setup instructions land here as each piece is built — backend first, then frontend,
then the seed script (Phase 2 of the build plan in `docs/planning.md`).

## Status
Repo scaffolding in progress — see `docs/planning.md` for the current backlog.
