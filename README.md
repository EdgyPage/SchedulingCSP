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

employees, tasks = ia.parse_roster_xlsx(open("datasets/EmployeeDatabase.xlsx", "rb").read())
result = solve(employees, minimums=[60, 5, 1, 3, 2, 1, 2], max_schedules=10, seed=0)
# result == {"count": 10, "schedules": [[{"Name","ID","Function"}, ...], ...]}
```
`main.ipynb` still works as before (`Schedule(...).populateAssignments()` /
`writeAssignmentsToExcel(prefix)`).

## Web API
Roster layout: an `ID` column, a `Name` column, then one column per task (truthy = approved).

- `POST /api/solve` — solve from form data (JSON body: `tasks`, `employees`, `minimums`, …).
- `POST /api/solve/file` — solve from an uploaded `.xlsx`/`.csv` (`minimums` as a JSON array field).
- `POST /api/inspect` — return a roster's task columns + employee count (so the UI can build a
  target-per-task form before solving).
- `POST /api/export?format=xlsx|csv` — download already-computed schedules as a file.

Run locally:
```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

## Web UI
A no-build static frontend (plain HTML/CSS/JS in `frontend/`) is served by the same app at `/`.
Open the running service in a browser and:
1. **Upload** an `.xlsx`/`.csv` roster — the task columns are detected via `/api/inspect`.
2. **Set** a target headcount per task plus options (`max_schedules`, optional `time_budget_s`,
   `seed`), then **Solve**.
3. **View** each schedule and **download** the results as `.xlsx` or `.csv`.

The UI sends no auth header, so it assumes the service runs **open** (no `API_KEY` set); the
server-side caps in `config.py` bound every request. To restrict *who* can reach it, use a
platform-level control (e.g. Render password/IP protection) rather than a client-side key.

## Deployment
Designed to run as a **single persistent web service** (e.g. a Render web service), which has
no serverless request-timeout cliff — long CSP runs finish instead of being cut off. The static
frontend in `frontend/` (or a build output at `frontend/dist`) is served from the same app (one
URL, no CORS). The `time_budget_s` option is the backstop so responses stay bounded.

### Render (blueprint)
`render.yaml` describes the service. In the Render dashboard: **New → Blueprint** → connect this
repo → it reads `render.yaml`. The start command binds to Render's injected `$PORT`
(`uvicorn app:app --host 0.0.0.0 --port $PORT`) and `PYTHON_VERSION` is pinned (the code uses
`str | None`, so needs ≥ 3.10).

Environment variables (see `config.py` for the full set):
- `API_KEY` — when set, every `/api/*` request must send a matching `X-API-Key` header. **Leave it
  unset** for the browser UI to work (the page sends no key); the server-side caps still bound every
  request. The `render.yaml` blueprint can auto-generate one (`generateValue: true`) if you instead
  want a locked-down, API-only deployment.
- `ALLOWED_ORIGINS` — comma-separated CORS allowlist; leave unset until a browser frontend exists
  (CORS only affects browser calls, not server-to-server/curl).
- Optional caps: `MAX_EMPLOYEES`, `MAX_TASKS`, `MAX_SCHEDULES`, `MAX_TIME_BUDGET_S`,
  `MAX_UPLOAD_BYTES`. On the free tier (512 MB / shared CPU, spins down when idle) consider
  lowering these for large rosters.

## Development
```bash
pip install -r requirements-dev.txt
pytest
```
