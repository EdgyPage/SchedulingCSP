"""Single-service FastAPI app: solver API + (optionally) the built frontend.

Deploy as one persistent web service (e.g. a Render web service) so long CSP runs
aren't cut off by a serverless timeout. If a built frontend exists at
``frontend/dist`` it is served from this same app, so there is one URL and no CORS
to manage in production.

    uvicorn app:app --host 0.0.0.0 --port 8000
"""

import json
import os

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import io_adapters
from solver import solve

app = FastAPI(title="SchedulingCSP")

# Permissive CORS is only needed for local dev (frontend on a different port). In the
# single-service production layout the frontend is served from this app, same origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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


def _validate_minimums(minimums, task_names):
    if len(minimums) != len(task_names):
        raise HTTPException(
            status_code=400,
            detail=f"Expected {len(task_names)} minimums (one per task), got {len(minimums)}.",
        )


@app.post("/api/solve")
def solve_from_form(req: SolveRequest):
    """Solve from form-entered data (JSON body)."""
    try:
        employees, task_names = io_adapters.parse_roster_form(req.model_dump())
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _validate_minimums(req.minimums, task_names)
    result = solve(
        employees, req.minimums, req.max_schedules,
        time_budget_s=req.time_budget_s, seed=req.seed,
    )
    return {"tasks": task_names, **result}


@app.post("/api/solve/file")
async def solve_from_file(
    file: UploadFile = File(...),
    minimums: str = Form(...),
    max_schedules: int = Form(10),
    time_budget_s: float | None = Form(None),
    seed: int | None = Form(None),
):
    """Solve from an uploaded roster (.xlsx or .csv). ``minimums`` is a JSON array."""
    content = await file.read()
    name = (file.filename or "").lower()
    try:
        if name.endswith(".csv"):
            employees, task_names = io_adapters.parse_roster_csv(content)
        elif name.endswith((".xlsx", ".xls")):
            employees, task_names = io_adapters.parse_roster_xlsx(content)
        else:
            raise HTTPException(status_code=400, detail="Upload a .xlsx or .csv file.")
        mins = json.loads(minimums)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _validate_minimums(mins, task_names)
    result = solve(
        employees, mins, max_schedules,
        time_budget_s=time_budget_s, seed=seed,
    )
    return {"tasks": task_names, **result}


@app.post("/api/export")
def export(req: ExportRequest, format: str = "xlsx"):
    """Serialize already-computed schedules to a downloadable file."""
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


# Serve the built frontend from this same service if present. Mounted last so it does
# not shadow the /api routes. Until a frontend is built, expose a simple health route.
_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(_FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=_FRONTEND_DIR, html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return {
            "status": "ok",
            "message": "SchedulingCSP API. POST /api/solve (form JSON) or "
                       "/api/solve/file (upload), then /api/export?format=xlsx|csv.",
        }
