# Design Decisions & Trade-offs

## Salary history via append-only rows, not an audit log
Every salary change is a new row in `salaries` with an `effective_date`, rather than an
`employees.salary` column overwritten in place plus a separate audit table. This makes
history a first-class query (`SELECT * FROM salaries WHERE employee_id = ? ORDER BY
effective_date DESC`) instead of something reconstructed from logs, and it's what the
"salary history timeline" and "reason for change" requirements need directly.

## Denormalized current salary on `employees`
The employee list and the insights dashboard both need "current salary" for up to 10,000
rows at once. Computing that per-request (latest `salaries` row per employee, joined
across the whole table) is a correlated subquery over 10k rows on every page load and
every dashboard refresh. Instead, `employees.current_salary_amount` /
`_currency` / `_id` are written once, in the same transaction, whenever a new salary row
is inserted. `salaries` stays the single source of truth for history; the denormalized
columns are a read-optimization, not a second source of truth. Trade-off accepted: writes
to salary are slightly more complex (must update two tables atomically); reads stay fast
at scale without needing a materialized view or cache layer.

## Money stored as `DECIMAL(12,2)`, not float or integer minor units
Float is ruled out outright — binary floating point can't represent amounts like `0.1`
exactly, and small rounding errors compound across aggregates (avg/median salary across
thousands of rows). That leaves integer minor units (e.g. storing cents as `8500050`) or
a fixed-point `DECIMAL` column. `DECIMAL(12,2)` via SQLAlchemy's `Numeric` type was chosen
over minor units: both are exact, but minor units require a divide/multiply-by-100 (or
per-currency scale) conversion at every read, write, form, and CSV import boundary in the
codebase. `DECIMAL` stores and displays the amount directly with no conversion layer,
which matters more here than the arithmetic-heavy guarantees minor units are designed
for (this system stores and displays salary figures; it doesn't run compounding
calculations on them). Currency is still stored alongside every amount so display
formatting and reporting only ever operate within a single currency at a time.

## No live currency conversion
Salaries are stored and displayed in their original currency. Aggregates (avg/median by
department, country) are computed within a currency, not converted to a single reporting
currency. Cross-currency "org-wide average salary" is explicitly not offered in v1 — doing
that correctly requires a live FX rate source and a decision about which date's rate to
use, which is out of scope. This is called out directly on the dashboard rather than
silently producing a misleading blended number.

## Department & country as plain indexed strings, constrained via UI dropdown
Normalizing `department`/`country` into their own tables would guarantee referential
integrity and support things like renaming a department in one place. For v1 the list of
departments and countries is small, fixed by the seed script, and doesn't need admin CRUD
of its own — so plain indexed TEXT columns were chosen to avoid two extra tables and two
extra sets of endpoints for no functional gain yet.

The real risk with plain strings is data drift through the UI — nothing stops
`"Engineering"`, `"engineering "`, and `"Eng"` from being treated as three different
departments once manual entry is involved, which would silently fragment the dashboard's
grouping. Rather than accepting that risk or building full lookup tables to prevent it,
the create/edit employee form restricts department and country to a dropdown of known
values (seeded canonical list) instead of free text — this gets most of the data-integrity
benefit of normalization without the schema and endpoint overhead. If department/country
management becomes a real feature in its own right (e.g. HR needs to add/rename
departments through the UI), this is a straightforward migration: add the lookup tables,
backfill FKs from the existing string values, without touching `salaries` at all.

## Soft delete via `status`, not row deletion
Employees are marked `inactive` rather than deleted, because deleting an employee row
would either cascade-delete their entire salary history (losing data the org may need for
compliance/reporting) or leave orphaned `salaries` rows. `status` also matches how HR
actually thinks about this — someone who leaves the org isn't erased from the record.

## Auth: JWT access token only, no refresh token flow
Login issues a single JWT with a moderate expiry (e.g. 60–120 minutes); there's no
refresh-token/rotation flow in v1. This keeps the auth surface small while still
delivering real multi-user login and route protection. Trade-off: users re-authenticate
after the token expires instead of being silently refreshed — acceptable for an internal
HR tool, and a refresh-token flow is a contained addition later since `get_current_user`
is the single seam all authorization already flows through.

## Single `hr_admin` role now, `role` column reserved for tiering later
All authenticated users currently get identical permissions. The `role` column exists on
`users` from day one specifically so that adding a second role (e.g. read-only Viewer) is
a matter of checking `user.role` inside the existing `get_current_user`-derived context,
not restructuring how authorization is wired through the app.

## Integer autoincrement primary keys, not UUIDs
Simpler joins, smaller indexes, and no coordination need — this is a single-instance app,
not a distributed or multi-tenant system where UUIDs would earn their keep. Revisit if
the system ever needs to merge data from multiple independently-seeded instances.

## Gender and other demographic fields excluded from the v1 schema
The core insights dashboard (headcount/salary by department and country) doesn't require
them. A pay-equity cut by gender is listed as a possible enhancement, not core scope; if
undertaken, it's a single additive column plus migration on `employees`, not a schema
redesign — deferred rather than built speculatively into the base schema.
