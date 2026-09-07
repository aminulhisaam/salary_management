# Employee CSV Import Format

Upload a UTF-8 CSV with a header row to `POST /employees/import`. The import validates the
entire file before writing anything: if one row is invalid, no employees or salaries are
created. The response lists every rejected row so the file can be fixed and uploaded again.

| Column | Required | Format |
|---|---|---|
| `employee_code` | Yes | Unique human-readable employee code. |
| `first_name` | Yes | Non-empty text. |
| `last_name` | Yes | Non-empty text. |
| `email` | Yes | Valid, unique email address. |
| `department` | Yes | Exact canonical department name. |
| `country` | Yes | Exact canonical country name. |
| `job_title` | Yes | Non-empty text. |
| `band` | Yes | Exact canonical band (`L1` through `L7`). |
| `hire_date` | Yes | ISO date: `YYYY-MM-DD`. |
| `status` | No | `active` (default) or `inactive`. |
| `salary_amount` | Yes | Positive `DECIMAL(12,2)` value. |
| `salary_currency` | Yes | ISO currency matching the country. |
| `effective_date` | Yes | ISO date: `YYYY-MM-DD`; creates the initial `hire` salary row. |

Canonical values are case-sensitive: use `Engineering`, not `engineering`; use `United
States`, not `US`. The canonical departments, countries, bands, and statuses are shared in
`shared/reference_data.json`, which is also used by the seed script and frontend.

Download or copy [the sample CSV](../seed/employee-import-template.csv) as a starting point.
