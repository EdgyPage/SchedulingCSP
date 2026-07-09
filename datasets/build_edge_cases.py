"""Deterministic generator for the curated edge-case roster.

Run:  python datasets/build_edge_cases.py

Writes ``datasets/edge_cases.xlsx`` and ``datasets/edge_cases.csv``. The roster packs
every solver edge case into one small, tractable database so expected outputs are
closed-form. See ``datasets/README.md`` for the design and the answer key.

Uses openpyxl + the stdlib csv module (no pandas).
"""

import csv
import os

from openpyxl import Workbook

TASKS = ["T1", "T2", "T3", "Pool"]
COLUMNS = ["ID", "Name"] + TASKS


def build_rows() -> list[dict]:
    """The curated roster as a list of ``{column: value}`` rows."""
    rows = []

    def add(emp_id: int, approved: set):
        row = {"ID": emp_id, "Name": f"Employee {emp_id}"}
        for task in TASKS:
            row[task] = task in approved
        rows.append(row)

    for emp_id in (1, 2):            # NoQual  -> approved for nothing
        add(emp_id, set())
    for emp_id in (3, 4):            # AllQual -> approved for every task
        add(emp_id, set(TASKS))
    add(5, {"T1"})                   # dedicated single-task specialists
    add(6, {"T2"})
    add(7, {"T3"})                   # only exclusive T3 body -> scarce resource
    for emp_id in range(8, 16):      # PoolBlock: 8 interchangeable Pool workers
        add(emp_id, {"Pool"})

    return rows


def write_xlsx(rows: list[dict], path: str) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Roster"
    ws.append(COLUMNS)
    for row in rows:
        ws.append([row[col] for col in COLUMNS])
    wb.save(path)


def write_csv(rows: list[dict], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    rows = build_rows()
    write_xlsx(rows, os.path.join(here, "edge_cases.xlsx"))
    write_csv(rows, os.path.join(here, "edge_cases.csv"))
    # Aligned eyeball dump of what was written.
    widths = {col: max(len(col), *(len(str(r[col])) for r in rows)) for col in COLUMNS}
    print("  ".join(col.ljust(widths[col]) for col in COLUMNS))
    for r in rows:
        print("  ".join(str(r[col]).ljust(widths[col]) for col in COLUMNS))


if __name__ == "__main__":
    main()
