"""Single-service FastAPI app: solver API + the frontend.

Deploy as one persistent web service (e.g. a Render web service) so long CSP runs
aren't cut off by a serverless timeout. The static UI in ``frontend/`` (or a built
``frontend/dist`` if one is ever produced) is served from this same app, so there is
one URL and no CORS to manage in production.

    uvicorn app:app --host 0.0.0.0 --port 8000

Hardening (see config.py for the knobs):
- every request body is capped (``MAX_UPLOAD_BYTES``);
- roster size, task count, schedule count, and search time are capped server-side,
  so a client can't pin a worker with an unbounded search;
- CPU-bound work runs off the event loop;
- CORS is env-driven; an optional ``API_KEY`` gates the /api routes.
"""

import json
import math
import os

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
import io_adapters
from solver import solve

app = FastAPI(title="SchedulingCSP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.allowed_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def limit_body_size(request, call_next):
    """First-line guard: reject over-large bodies by Content-Length before reading them."""
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > config.MAX_UPLOAD_BYTES:
                return JSONResponse(status_code=413, content={"detail": "Request body too large."})
        except ValueError:
            pass
    return await call_next(request)


def require_api_key(x_api_key: str | None = Header(default=None)):
    """When API_KEY is configured, require a matching X-API-Key header; otherwise open."""
    if config.API_KEY and x_api_key != config.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


class SolveRequest(BaseModel):
    tasks: list[str]
    employees: list[dict]
    minimums: list[float]
    max_schedules: int = 10
    time_budget_s: float | None = None
    seed: int | None = None


class ExportRequest(BaseModel):
    # The schedules_to_json shape: a list of tables, each a list of row dicts.
    schedules: list[list[dict]]


def _validate_inputs(employees, task_names, minimums, max_schedules):
    """Server-side validation shared by every input path. Raises HTTP 400 on violation."""
    if not task_names:
        raise HTTPException(status_code=400, detail="At least one task is required.")
    if len(task_names) > config.MAX_TASKS:
        raise HTTPException(status_code=400, detail=f"Too many tasks (max {config.MAX_TASKS}).")
    if len(employees) > config.MAX_EMPLOYEES:
        raise HTTPException(status_code=400, detail=f"Too many employees (max {config.MAX_EMPLOYEES}).")
    if len(minimums) != len(task_names):
        raise HTTPException(
            status_code=400,
            detail=f"Expected {len(task_names)} minimums (one per task), got {len(minimums)}.",
        )
    for value in minimums:
        if isinstance(value, bool) or not isinstance(value, (int, float)) \
                or not math.isfinite(value) or value < 0:
            raise HTTPException(status_code=400, detail="Each minimum must be a finite number >= 0.")
    if max_schedules < 1:
        raise HTTPException(status_code=400, detail="max_schedules must be >= 1.")


def _run_solver(employees, task_names, minimums, max_schedules, time_budget_s, seed):
    """Validate, clamp to server ceilings, and run the search. CPU-bound."""
    _validate_inputs(employees, task_names, minimums, max_schedules)
    result = solve(
        employees, minimums,
        config.effective_max_schedules(max_schedules),
        time_budget_s=config.effective_time_budget(time_budget_s),
        seed=seed,
    )
    return {"tasks": task_names, **result}


def _parse_upload(filename, content):
    """Parse an uploaded roster into ``(employees, task_names)`` by file extension.

    Shared by /api/solve/file and /api/inspect. CPU/IO-bound (pandas read); callers
    run it in a threadpool. Raises ValueError on an unsupported extension.
    """
    name = (filename or "").lower()
    if name.endswith(".csv"):
        return io_adapters.parse_roster_csv(content)
    if name.endswith((".xlsx", ".xls")):
        return io_adapters.parse_roster_xlsx(content)
    raise ValueError("Upload a .xlsx or .csv file.")


@app.post("/api/solve", dependencies=[Depends(require_api_key)])
def solve_from_form(req: SolveRequest):
    """Solve from form-entered data (JSON body)."""
    # Cheap count checks before building Employee objects for a huge payload.
    if len(req.employees) > config.MAX_EMPLOYEES:
        raise HTTPException(status_code=400, detail=f"Too many employees (max {config.MAX_EMPLOYEES}).")
    if len(req.tasks) > config.MAX_TASKS:
        raise HTTPException(status_code=400, detail=f"Too many tasks (max {config.MAX_TASKS}).")
    try:
        employees, task_names = io_adapters.parse_roster_form(req.model_dump())
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    # Sync endpoint => FastAPI already runs it in a worker thread.
    return _run_solver(
        employees, task_names, req.minimums, req.max_schedules, req.time_budget_s, req.seed,
    )


@app.post("/api/solve/file", dependencies=[Depends(require_api_key)])
async def solve_from_file(
    file: UploadFile = File(...),
    minimums: str = Form(...),
    max_schedules: int = Form(10),
    time_budget_s: float | None = Form(None),
    seed: int | None = Form(None),
):
    """Solve from an uploaded roster (.xlsx or .csv). ``minimums`` is a JSON array."""
    if file.size is not None and file.size > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Uploaded file too large.")
    content = await file.read()
    if len(content) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Uploaded file too large.")
    try:
        mins = json.loads(minimums)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="minimums must be a JSON array.")

    # Parsing and solving are CPU/IO-bound; keep them off the event loop so one
    # heavy request can't stall every other connection.
    try:
        employees, task_names = await run_in_threadpool(_parse_upload, file.filename, content)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return await run_in_threadpool(
        _run_solver, employees, task_names, mins, max_schedules, time_budget_s, seed,
    )


@app.post("/api/inspect", dependencies=[Depends(require_api_key)])
async def inspect_file(file: UploadFile = File(...)):
    """Return the task columns (and employee count) of an uploaded roster.

    The UI calls this first so it can render one target-headcount input per task
    before the user solves. Same upload guards as /api/solve/file.
    """
    if file.size is not None and file.size > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Uploaded file too large.")
    content = await file.read()
    if len(content) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Uploaded file too large.")
    try:
        employees, task_names = await run_in_threadpool(_parse_upload, file.filename, content)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"tasks": task_names, "employee_count": len(employees)}


@app.post("/api/export", dependencies=[Depends(require_api_key)])
def export(req: ExportRequest, format: str = "xlsx"):
    """Serialize already-computed schedules to a downloadable, injection-safe file."""
    if format == "xlsx":
        data = io_adapters.results_to_xlsx_bytes(req.schedules)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "schedules.xlsx"
    elif format == "csv":
        data = io_adapters.results_to_csv_bytes(req.schedules)
        media = "text/csv"
        filename = "schedules.csv"
    else:
        raise HTTPException(status_code=400, detail="format must be 'xlsx' or 'csv'.")
    return Response(
        content=data,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# Serve the frontend from this same service. Mounted last so it never shadows the
# /api routes. Prefer a built SPA output (frontend/dist) if one is ever produced;
# otherwise serve the committed no-build static site (frontend/). Until either exists,
# fall back to a simple JSON health route.
_HERE = os.path.dirname(__file__)
_FRONTEND_DIR = next(
    (d for d in (os.path.join(_HERE, "frontend", "dist"), os.path.join(_HERE, "frontend"))
     if os.path.isfile(os.path.join(d, "index.html"))),
    None,
)
if _FRONTEND_DIR:
    app.mount("/", StaticFiles(directory=_FRONTEND_DIR, html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return {
            "status": "ok",
            "message": "SchedulingCSP API. POST /api/solve (form JSON) or "
                       "/api/solve/file (upload); /api/inspect for task columns; "
                       "then /api/export?format=xlsx|csv.",
        }
