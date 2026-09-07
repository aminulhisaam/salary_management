# Requirements — Employee Salary Management Software

## Goal
This document defines the requirements for a web-based salary management system for
ACME's HR Manager, who currently manages salary data for 10,000 employees across
multiple countries using spreadsheets. The system replaces that process, allowing the
HR Manager to manage salary data directly and to answer questions about how the org
pays people — not just store records.

## Primary User
HR Manager. Multiple HR users have their own accounts; all authenticated users share the
same permission level in v1 (see "Out of Scope" for the reasoning behind not tiering
roles yet).

## In Scope
**Authentication**
- Multi-user login (email + password), JWT-based session
- Every authenticated user is an HR Manager with identical permissions — no tiered roles in v1
- Every employee/salary endpoint requires a valid logged-in user

**Core data management**
- Employee records: name, email, department, country, job title, level/band, hire date, status
- Salary records per employee, with effective date and reason (hire / promotion / adjustment) —
  this produces a full compensation history rather than just a current value
- Create / edit employees and salary records
- List view: paginated, searchable, filterable (department, country, band)
- Employee detail view: profile + current salary + full salary history timeline

**Answering "how does the org pay people"**
- Insights dashboard: headcount and average/median salary by department and by country,
  salary band distribution, min/max ranges
- Filterable query view (e.g. "employees in Engineering, India, paid above X")

**Engineering**
- Seed script generating 10,000 realistic employees + salary records
- Automated tests around core business logic (salary CRUD, filtering, aggregation)
- Config-driven setup so the same codebase runs locally (SQLite) and can be redeployed to
  a free-tier host with a database swap (Postgres) via env var only — no code changes
- CSV bulk import for employees/salaries
- Fully deployed, publicly accessible instance, plus a demo video

## Out of Scope (v1) — and why
- **Role-based permission tiers** (e.g. read-only Viewer vs Admin) — deferred. Every
  authenticated user gets the same HR-admin permissions in v1. The user model carries a
  `role` field from day one, so tiering can be added later without a rewrite.
- **Self-service password reset / email verification flows** — treated as auth-hardening
  work outside the core assessment scope. A basic login/register is enough to demonstrate
  real multi-user access control.
- **Payroll disbursement / bank integration** — this is a system of record, not a payment
  processor. Actually paying people is a separate, much larger system, not built here.
- **Live currency conversion** — salary is stored with its currency code as-is, with no FX
  conversion or normalization to a single reporting currency in v1. Cross-currency
  aggregate comparisons are called out as a known limitation rather than solved here.
- **Employee self-service view** — only the HR Manager persona is built for v1. An
  employee read-only view is a natural extension, but it introduces a second permission
  surface that is not taken on yet.

## Key Assumptions
- One employee has exactly one active salary at a time, plus a full history of past records.
- The org structure is flat enough to model as department + country per employee, with no
  nested org-chart / manager hierarchy in v1.
- Fields beyond the above (e.g. gender, performance rating) are decided during schema
  design, only if they materially help the insights dashboard, and documented there
  rather than fixed in advance.

## Success Criteria
- Only authenticated HR users can access employee/salary data; unauthenticated requests
  are rejected
- The HR Manager can find any employee's current and historical pay within a few clicks
- The HR Manager can answer "how are we paying department/country X" without opening Excel
- The app performs acceptably against the full 10,000-employee dataset (paginated lists,
  indexed filters, dashboard queries return quickly)
- The same codebase runs locally out of the box and can be pointed at a free-tier host
  with only environment/config changes
- The system is fully functional end-to-end: deployed, seeded, tested, and demoable
