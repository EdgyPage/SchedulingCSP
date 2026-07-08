"""Input parsers and output serializers that bridge the pure solver to the web layer.

Inputs (Excel upload, CSV upload, or a web form) all converge to the same internal
shape: ``(list[Employee], list[task_name])``. Outputs are produced in-memory (no disk
writes) as JSON tables, an Excel workbook, or a CSV -- suitable for returning directly
from an HTTP handler.

Expected roster layout (xlsx/csv): an ``ID`` column, a ``Name`` column, and one column
per task whose cell is truthy when the employee is approved for that task.
"""

import io
from datetime import datetime

import pandas as pd

from employee import Employee

ID_COL = "ID"
NAME_COL = "Name"
_OUTPUT_COLUMNS = ["Name", "ID", "Function"]


# --- helpers ----------------------------------------------------------------

def _to_bool(value) -> bool:
    """Normalize a spreadsheet/form cell to a real bool (handles NaN, 1/0, 'x', etc.)."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if value != value:  # NaN
            return False
        return value != 0
    return str(value).strip().lower() in {
        "true", "t", "yes", "y", "1", "x", "approved", "checked",
    }


def _approved_to_statuses(approved, task_names) -> list[bool]:
    """Accept approvals as a name-subset list, a flag list, or a {task: flag} mapping."""
    if isinstance(approved, dict):
        return [_to_bool(approved.get(t, False)) for t in task_names]
    approved = list(approved)
    all_strings = all(isinstance(a, str) for a in approved)
    if not all_strings and len(approved) == len(task_names):
        return [_to_bool(a) for a in approved]
    approved_set = {str(a) for a in approved}
    return [t in approved_set for t in task_names]


# --- input parsers ----------------------------------------------------------

def parse_roster_dataframe(df: pd.DataFrame):
    columns = list(df.columns)
    missing = [col for col in (ID_COL, NAME_COL) if col not in columns]
    if missing:
        raise ValueError(f"Roster is missing required column(s): {', '.join(missing)}")
    task_names = [col for col in columns if col not in (ID_COL, NAME_COL)]
    if not task_names:
        raise ValueError("Roster has no task columns.")
    employees = []
    for _, row in df.iterrows():
        statuses = [_to_bool(row[task]) for task in task_names]
        employees.append(Employee(row[ID_COL], str(row[NAME_COL]), list(task_names), statuses))
    return employees, task_names


def parse_roster_xlsx(file_bytes: bytes):
    return parse_roster_dataframe(pd.read_excel(io.BytesIO(file_bytes)))


def parse_roster_csv(file_bytes: bytes):
    return parse_roster_dataframe(pd.read_csv(io.BytesIO(file_bytes)))


def parse_roster_form(payload: dict):
    task_names = list(payload["tasks"])
    if not task_names:
        raise ValueError("At least one task is required.")
    employees = []
    for entry in payload["employees"]:
        statuses = _approved_to_statuses(entry.get("approved", []), task_names)
        employees.append(Employee(entry["id"], str(entry["name"]), list(task_names), statuses))
    return employees, task_names


# --- output serializers -----------------------------------------------------

def _schedule_to_rows(assignment: dict) -> list[dict]:
    rows = []
    for task, employees in assignment.items():
        for employee in employees:
            rows.append({"Name": employee.name, "ID": employee.id, "Function": task})
    return rows


def schedules_to_json(schedules: list[dict]) -> list[list[dict]]:
    """Convert internal ``{task: [Employee]}`` schedules to JSON-serializable tables."""
    return [_schedule_to_rows(assignment) for assignment in schedules]


def results_to_xlsx_bytes(results: list[list[dict]]) -> bytes:
    """One workbook, one sheet per schedule. ``results`` is the schedules_to_json shape."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        if not results:
            pd.DataFrame(columns=_OUTPUT_COLUMNS).to_excel(
                writer, index=False, sheet_name="Schedule_1")
        for i, table in enumerate(results, start=1):
            pd.DataFrame(table, columns=_OUTPUT_COLUMNS).to_excel(
                writer, index=False, sheet_name=f"Schedule_{i}")
    return buffer.getvalue()


def results_to_csv_bytes(results: list[list[dict]]) -> bytes:
    """Single CSV; a leading ``Schedule`` column distinguishes each schedule."""
    rows = []
    for i, table in enumerate(results, start=1):
        for row in table:
            rows.append({"Schedule": i, **row})
    df = pd.DataFrame(rows, columns=["Schedule"] + _OUTPUT_COLUMNS)
    return df.to_csv(index=False).encode("utf-8")


def write_schedules_to_excel_files(schedules: list[dict], filePath: str = "") -> list[str]:
    """Legacy/local convenience: write one .xlsx file per schedule to disk."""
    paths = []
    for i, assignment in enumerate(schedules, start=1):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = f"{filePath}_Schedule_{i}_{timestamp}.xlsx"
        pd.DataFrame(_schedule_to_rows(assignment), columns=_OUTPUT_COLUMNS).to_excel(
            path, index=False)
        paths.append(path)
    return paths
