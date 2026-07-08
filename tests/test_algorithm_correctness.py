"""Algorithm-correctness regression harness for the CSP solver.

The problem is exponential, so every expected output here comes from a scenario whose
answer is closed-form / hand-countable (see datasets/README.md for the answer key).

Correctness is gated on EXACT solution counts + structural invariants. Performance is
gated on the deterministic node count (Schedule.nodes, stable for a fixed seed) with a
generous ceiling -- improvements are allowed, blow-ups are caught. Wall-clock is only
reported, never asserted tightly, so the suite doesn't flake across machines.
"""

import importlib.util
import json
import os
import time
import tracemalloc
from math import comb

import pytest

import constraints as c
import io_adapters as ia
import schedule as s

SEED = 1337
_DATASETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "datasets")
_EDGE_XLSX = os.path.join(_DATASETS, "edge_cases.xlsx")
_EDGE_CSV = os.path.join(_DATASETS, "edge_cases.csv")


@pytest.fixture(scope="module")
def roster():
    with open(_EDGE_XLSX, "rb") as fh:
        employees, tasks = ia.parse_roster_xlsx(fh.read())
    return employees, tasks


def _signature(solution):
    """Canonical identity of a solution: sorted (task, sorted employee IDs)."""
    return tuple(sorted(
        (task, tuple(sorted(str(emp.id) for emp in emps)))
        for task, emps in solution.items()
    ))


def _solve(employees, minimums, max_length):
    sched = s.Schedule(employees, c.Constraints(minimums), max_length, seed=SEED)
    start = time.perf_counter()
    sched.populateAssignments()
    elapsed_ms = (time.perf_counter() - start) * 1000
    return sched, elapsed_ms


# name, minimums [T1,T2,T3,Pool], maxLength, expected_count, node_ceiling
SCENARIOS = [
    ("S1_feasible_zero_qual",  [1, 1, 1, 0], 1000, 13,          150),
    ("S2_infeasible",          [1, 1, 4, 0], 10,   0,           10),
    ("S3_all_qual_used",       [2, 0, 0, 0], 1000, 3,           50),
    ("S4_explosion_exhaustive",[0, 0, 0, 3], 1000, comb(10, 3), 500),
]


@pytest.mark.parametrize(
    "name,minimums,max_length,expected_count,node_ceiling",
    SCENARIOS, ids=[row[0] for row in SCENARIOS],
)
def test_scenario(roster, capsys, name, minimums, max_length, expected_count, node_ceiling):
    employees, tasks = roster
    sched, elapsed_ms = _solve(employees, minimums, max_length)
    solutions = sched.validSchedules

    with capsys.disabled():  # always show the timing line, even without -s
        print(f"\n  [{name}] count={len(solutions)} nodes={sched.nodes} elapsed={elapsed_ms:.1f}ms")

    # --- correctness -------------------------------------------------------
    assert len(solutions) == expected_count, \
        f"{name}: expected {expected_count} solutions, got {len(solutions)}"

    signatures = [_signature(sol) for sol in solutions]
    assert len(set(signatures)) == len(signatures), f"{name}: duplicate solutions found"

    for sol in solutions:
        for i, task in enumerate(tasks):
            assert len(sol[task]) == minimums[i], \
                f"{name}: task {task} has {len(sol[task])} != target {minimums[i]}"
        unassigned_ids = {emp.id for emp in sol["Unassigned"]}
        # Employees 1 and 2 are approved for nothing -> must never be placed.
        assert {1, 2} <= unassigned_ids, f"{name}: a zero-qualification employee was placed"

    # --- performance guard (deterministic for a fixed seed) ----------------
    assert sched.nodes <= node_ceiling, \
        f"{name}: node count {sched.nodes} exceeded ceiling {node_ceiling} (perf regression)"


def test_all_qualified_employees_are_usable(roster):
    """S3: the AllQual employees (3, 4) must actually be assignable to a task."""
    employees, tasks = roster
    sched, _ = _solve(employees, [2, 0, 0, 0], 1000)
    for sol in sched.validSchedules:
        t1_ids = {emp.id for emp in sol["T1"]}
        assert t1_ids & {3, 4}, "expected an all-qualified employee to be used in T1"


def test_csv_and_xlsx_rosters_are_identical():
    """The two committed edge-case files must describe the same roster."""
    with open(_EDGE_XLSX, "rb") as fh:
        emp_x, tasks_x = ia.parse_roster_xlsx(fh.read())
    with open(_EDGE_CSV, "rb") as fh:
        emp_c, tasks_c = ia.parse_roster_csv(fh.read())
    assert tasks_x == tasks_c
    assert [(str(e.id), e.name, e.taskStatuses) for e in emp_x] == \
           [(str(e.id), e.name, e.taskStatuses) for e in emp_c]


def test_committed_dataset_matches_builder(roster, tmp_path):
    """The committed edge_cases files must match what build_edge_cases.py produces now."""
    employees, tasks = roster
    path = os.path.join(_DATASETS, "build_edge_cases.py")
    spec = importlib.util.spec_from_file_location("build_edge_cases", path)
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)

    regen = tmp_path / "regen.csv"
    builder.build_dataframe().to_csv(regen, index=False, lineterminator="\n")
    emp_r, tasks_r = ia.parse_roster_csv(regen.read_bytes())

    assert tasks_r == tasks == builder.TASKS
    assert [(str(e.id), e.name, e.taskStatuses) for e in emp_r] == \
           [(str(e.id), e.name, e.taskStatuses) for e in employees]


@pytest.mark.xfail(
    strict=True, raises=TypeError,
    reason="streaming solutions to disk under memory pressure is not implemented yet",
)
def test_disk_spill_bounds_memory(roster, tmp_path):
    """Specification for the future 'spill solutions to disk' feature (S5).

    Scenario [0,0,0,5] yields C(10,5)=252 solutions. The proposed API keeps RAM bounded
    by streaming completed solutions to disk once an in-memory cap is exceeded, instead
    of retaining all of them. This test is xfail(strict) until that exists: today the
    unknown kwargs raise TypeError; once implemented it should pass, and the resulting
    XPASS (strict) will fail the suite, prompting removal of this marker.
    """
    employees, _ = roster
    spill_path = tmp_path / "solutions.jsonl"
    expected = comb(10, 5)  # 252

    tracemalloc.start()
    sched = s.Schedule(
        employees, c.Constraints([0, 0, 0, 5]), 100_000,
        seed=SEED, spill_path=str(spill_path), max_in_memory=16,
    )
    sched.populateAssignments()
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()

    lines = spill_path.read_text().strip().splitlines()
    assert len(lines) == expected                                  # all solutions persisted
    signatures = {json.dumps(json.loads(line), sort_keys=True) for line in lines}
    assert len(signatures) == expected                             # no duplicates lost/added
    assert peak < 16 * 50_000                                      # RAM bounded, not O(total)
