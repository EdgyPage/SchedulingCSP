"""Deterministic generator for the curated edge-case roster.

Run:  python datasets/build_edge_cases.py

Writes ``datasets/edge_cases.xlsx`` and ``datasets/edge_cases.csv``. The roster packs
every solver edge case into one small, tractable database so expected outputs are
closed-form. See ``datasets/README.md`` for the design and the answer key.
"""

import os

import pandas as pd

TASKS = ["T1", "T2", "T3", "Pool"]


def build_dataframe() -> pd.DataFrame:
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

    return pd.DataFrame(rows, columns=["ID", "Name"] + TASKS)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    df = build_dataframe()
    df.to_excel(os.path.join(here, "edge_cases.xlsx"), index=False)
    df.to_csv(os.path.join(here, "edge_cases.csv"), index=False, lineterminator="\n")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
