# Salary Management Software

Web-based salary management for ACME's HR Manager. It replaces spreadsheet-based salary
tracking for 10,000 employees across multiple countries.

## Docs
- [`docs/requirements.md`](docs/requirements.md): scope, in/out of scope, and why
- [`docs/planning.md`](docs/planning.md): feature backlog and build order
- [`docs/schema.md`](docs/schema.md): data model
- [`docs/decisions.md`](docs/decisions.md): architecture trade-offs

## Structure
```
backend/    FastAPI app, SQLAlchemy models, Alembic migrations, tests
frontend/   React (Vite) app
seed/       Seed script for 10,000 employees and demo users
shared/     Canonical reference data shared by the app and seed script
docs/       Requirements, planning, schema, and decisions
```

## Running Locally

### Without Docker

In PowerShell, create the backend virtual environment and install the dependencies:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt
Copy-Item .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The default `DATABASE_URL` is a SQLite database at `backend/salary_management.db`.
Set `DATABASE_URL`, `jwt_secret`, `jwt_algorithm`, `jwt_expiry_minutes`, and
`CORS_ORIGINS` in `backend/.env` to override them. `CORS_ORIGINS` accepts a comma-separated
list of allowed frontend origins. Do not use the placeholder JWT secret outside local work.

In a second terminal, start the Vite frontend:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Set `VITE_API_BASE_URL=http://localhost:8000` in `frontend/.env`. Vite embeds this
variable when it builds the app, so restart the Vite process after changing it.

To populate the local database after applying migrations:

```powershell
cd backend
python ..\seed\seed.py
```

### With Docker and PostgreSQL

Docker Compose runs the API against PostgreSQL, applies Alembic migrations before Uvicorn
starts, and makes the API available at `http://localhost:8000`:

```powershell
docker compose up --build
```

The PostgreSQL data is stored in the named `postgres_data` volume. To stop the stack:

```powershell
docker compose down
```

To run the backend suite against that Compose PostgreSQL service:

```powershell
docker compose --profile test run --rm backend-test
docker compose down
```

The test service resets its own PostgreSQL schema before each test. Do not point
`TEST_DATABASE_URL` at a database containing data you need to retain.

## Deployment

### Backend on Render

1. Push this repository to a Git provider and create a Render **Web Service** from it.
2. Leave Render's root directory at the repository root and set the Dockerfile path to
   `backend/Dockerfile`. The Docker build needs the root context to copy `shared/`.
3. Leave Render's default `PORT` setting in place. The container binds Uvicorn to
   `0.0.0.0:$PORT` (Render supplies `10000` by default).
4. Create a PostgreSQL database. Render Postgres works well for a single-provider setup;
   Neon is a practical free-tier alternative. Copy its connection URL into the backend
   service's `DATABASE_URL` environment variable, replacing a leading `postgresql://` with
   `postgresql+psycopg://` for this application's installed driver.
5. Set these backend environment variables in Render:

```text
DATABASE_URL=postgresql+psycopg://...
jwt_secret=<a long, random secret>
jwt_algorithm=HS256
jwt_expiry_minutes=90
CORS_ORIGINS=https://<your-vercel-project>.vercel.app
```

The image entrypoint runs `alembic upgrade head` before starting the API, so a fresh
database receives the schema automatically. Use a persistent PostgreSQL instance; free
service filesystems are ephemeral and are not suitable for the SQLite default.
Set Render's health-check path to `/health`.

### Frontend on Vercel

1. Import the same repository into Vercel and set its **Root Directory** to `frontend`.
2. Use build command `npm run build` and output directory `dist` (the Vite defaults).
3. Set `VITE_API_BASE_URL` to the public HTTPS URL of the deployed Render backend, with
   no trailing slash, for both Preview and Production environments.
4. Redeploy after changing `VITE_API_BASE_URL`; Vite reads it at build time and writes it
   into the static `dist/` output.

After Vercel gives you the public URL, update the backend's `CORS_ORIGINS` setting with it
and redeploy the backend. If you add a custom frontend domain later, add that HTTPS origin
to `CORS_ORIGINS` too, then redeploy.

### Public-demo security note

The app requires a login for employee and salary data, but v1 intentionally permits public
registration and grants every registered account the `hr_admin` role. It is suitable for a
portfolio/demo deployment with synthetic seed data. Do not load real compensation data into
a public deployment until registration is restricted to invitations or an organization
identity provider and the auth hardening noted in `docs/decisions.md` is complete.

## Status

The core API, frontend, data seed, import flow, and deployment configuration are present.
See [`docs/planning.md`](docs/planning.md) for the product roadmap.
