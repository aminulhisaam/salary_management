# Schema Design

Three tables cover v1: `users` (auth), `employees` (profile + current-state), and
`salaries` (append-only compensation history). Departments and countries are plain
indexed string columns rather than separate lookup tables — see decisions.md.

## `users`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | autoincrement |
| email | TEXT, UNIQUE, INDEXED | login identifier |
| hashed_password | TEXT | bcrypt via passlib |
| role | TEXT | default `"hr_admin"`; reserved for future tiering |
| created_at | TIMESTAMP | |

## `employees`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | autoincrement |
| employee_code | TEXT, UNIQUE | human-readable id, e.g. `EMP-00001`, generated at seed/create time |
| first_name | TEXT | |
| last_name | TEXT | |
| email | TEXT, UNIQUE | |
| department | TEXT, INDEXED | plain string, not FK; UI restricts entry to a dropdown — see decisions.md |
| country | TEXT, INDEXED | plain string, not FK; UI restricts entry to a dropdown — see decisions.md |
| job_title | TEXT | |
| band | TEXT, INDEXED | level/grade, e.g. `L1`–`L7` |
| hire_date | DATE | |
| status | TEXT | `active` / `inactive` — see "soft delete" in decisions.md |
| current_salary_amount | DECIMAL(12,2) | denormalized amount — see decisions.md |
| current_salary_currency | TEXT | denormalized ISO 4217 code |
| current_salary_id | INTEGER, FK → salaries.id | pointer to the row backing the two fields above |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

## `salaries`
Append-only. A row is never edited or deleted after creation — every change to pay is a
new row, which is what gives the system its history for free.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | autoincrement |
| employee_id | INTEGER, FK → employees.id, INDEXED | |
| amount | DECIMAL(12,2) | fixed-point, exact — see decisions.md |
| currency | TEXT | ISO 4217 code, e.g. `USD`, `INR` |
| effective_date | DATE, INDEXED | when this amount takes effect |
| reason | TEXT | `hire` / `promotion` / `adjustment` / `correction` |
| created_by | INTEGER, FK → users.id | which HR user entered it |
| created_at | TIMESTAMP | |

Composite index on `(employee_id, effective_date DESC)` — every "current salary" and
"history timeline" query filters by employee and orders by date.

## Derived data
- **Current salary**: the `salaries` row with the latest `effective_date <= today` for an
  employee. Written once to `employees.current_salary_*` whenever a new salary row is
  inserted, so the list view never computes this per-row across 10,000 employees at
  request time.
- **Dashboard aggregates** (headcount, avg/median salary, band distribution by
  department/country): computed on `employees.current_salary_amount` directly — this is
  exactly why the denormalized column exists, since without it every aggregate query
  would need a correlated subquery per employee against `salaries`.
