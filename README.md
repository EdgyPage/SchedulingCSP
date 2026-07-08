# SchedulingCSP

## Overview
A small constraint-satisfaction-problem (CSP) solver that assigns employees to tasks based
on which tasks they are trained/approved for. Given a per-task target headcount, it searches
for schedules in which **every task is filled by exactly its target number** of employees;
anyone left over is placed in `Unassigned`.

Employees are defined by an ID, a name, and a boolean "approved for this task?" flag per task.

## Modules
- `employee.py` / `constraints.py` — domain models.
- `schedule.py` — the pure backtracking solver (`Schedule`). No disk/stdout side effects.
  The search is bounded by `maxLength` and optional `time_budget_s` / `max_nodes`, so it always
  returns (best-effort) even on large inputs.
- `solver.py` — `solve(employees, minimums, max_schedules, *, time_budget_s, max_nodes, seed)`,
  the one-call entrypoint returning JSON-ready schedules.
- `io_adapters.py` — parse rosters from Excel/CSV/form (JSON), and serialize results to
  JSON tables, an Excel workbook, or CSV (all in-memory).
- `app.py` — FastAPI service exposing the solver (see below).

## Library usage
```python
import io_adapters as ia
from solver import solve

employees, tasks = ia.parse_roster_xlsx(open("EmployeeDatabase.xlsx", "rb").read())
result = solve(employees, minimums=[60, 5, 1, 3, 2, 1, 2], max_schedules=10, seed=0)
# result == {"count": 10, "schedules": [[{"Name","ID","Function"}, ...], ...]}
```
`main.ipynb` still works as before (`Schedule(...).populateAssignments()` /
`writeAssignmentsToExcel(prefix)`).

## Web API
Roster layout: an `ID` column, a `Name` column, then one column per task (truthy = approved).

- `POST /api/solve` — solve from form data (JSON body: `tasks`, `employees`, `minimums`, …).
- `POST /api/solve/file` — solve from an uploaded `.xlsx`/`.csv` (`minimums` as a JSON array field).
- `POST /api/export?format=xlsx|csv` — download already-computed schedules as a file.

Run locally:
```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

## Deployment
Designed to run as a **single persistent web service** (e.g. a Render web service), which has
no serverless request-timeout cliff — long CSP runs finish instead of being cut off. A built
frontend placed at `frontend/dist` is served from the same app (one URL, no CORS). The
`time_budget_s` option is the backstop so responses stay bounded.

## Development
```bash
pip install -r requirements-dev.txt
pytest
```
