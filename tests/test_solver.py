import employee as e
import constraints as c
import schedule as s
from solver import solve

TASKS = ["A", "B", "C"]


def make_emp(emp_id, name, approved_flags):
    return e.Employee(emp_id, name, list(TASKS), list(approved_flags))


def test_employee_approved_for_all_tasks_does_not_crash():
    # Bug 1: the bucket list was one slot too short, so an employee approved for
    # every task raised IndexError during Schedule construction.
    emps = [
        make_emp(1, "all", [True, True, True]),
        make_emp(2, "b", [False, True, False]),
    ]
    sched = s.Schedule(emps, c.Constraints([1, 1, 0]), 1)
    assert sched is not None


def test_zero_approval_employee_lands_in_unassigned():
    # Bug 2: employees approved for no task were silently dropped from output.
    emps = [
        make_emp(1, "qual", [True, False, False]),
        make_emp(2, "nobody", [False, False, False]),
    ]
    result = solve(emps, [1, 0, 0], max_schedules=1)
    assert result["count"] >= 1
    for table in result["schedules"]:
        function_by_id = {row["ID Alias"]: row["Function"] for row in table}
        assert function_by_id.get(2) == "Unassigned"


def test_employee_setter_is_idempotent():
    # Bug 5: re-assigning taskStatuses used to double the counters.
    emp = make_emp(1, "x", [True, False, True])
    assert emp.numApprovedTasks == 2
    assert emp.indexApprovedTasks == [0, 1, 3]

    emp.taskStatuses = [True, False, True]
    assert emp.numApprovedTasks == 2
    assert emp.indexApprovedTasks == [0, 1, 3]


def test_schedules_hit_exact_minimums():
    emps = [
        make_emp(1, "a", [True, False, False]),
        make_emp(2, "b", [True, True, False]),
        make_emp(3, "c", [False, True, True]),
        make_emp(4, "d", [False, False, True]),
    ]
    minimums = [1, 1, 1]
    result = solve(emps, minimums, max_schedules=5, seed=0)
    assert result["count"] >= 1
    for table in result["schedules"]:
        counts = {t: 0 for t in TASKS}
        for row in table:
            if row["Function"] in counts:
                counts[row["Function"]] += 1
        assert [counts[t] for t in TASKS] == minimums


def test_time_budget_returns_without_error():
    # Larger fixture, tiny budget: must return promptly with best-effort results.
    emps = [make_emp(i, f"e{i}", [True, True, True]) for i in range(20)]
    result = solve(emps, [3, 3, 3], max_schedules=100, time_budget_s=0.05, seed=0)
    assert result["count"] >= 0
    assert result["count"] <= 100


# --- closest-schedule feedback on failure -----------------------------------

def test_infeasible_returns_diagnostics_and_closest():
    # C needs 3 but only employee 3 can do it -> pool shortfall.
    emps = [
        make_emp(1, "a", [True, False, False]),
        make_emp(2, "b", [False, True, False]),
        make_emp(3, "c", [False, False, True]),
    ]
    result = solve(emps, [1, 1, 3], max_schedules=5, seed=0)
    assert result["count"] == 0 and result["schedules"] == []

    reasons = {r["task"]: r for r in result["infeasibility"]["reasons"]}
    assert reasons["C"]["needed"] == 3
    assert reasons["C"]["available"] == 1
    assert reasons["C"]["short"] == 2

    schedules = result["closest"]["schedules"]
    distances = [s["distance"] for s in schedules]
    assert distances == sorted(distances)              # ranked closest-first
    top = schedules[0]
    assert top["coverage"] == [1, 1, 1]                # best achievable staffing
    assert top["shortfall"] == [0, 0, 2]
    assert top["covered"] == 3 and top["target_total"] == 5
    # Every employee appears exactly once across the exported table.
    ids = sorted(row["ID Alias"] for row in top["table"])
    assert ids == [1, 2, 3]


def test_feasible_result_has_no_closest_or_infeasibility():
    emps = [make_emp(i, "x", [True, True, True]) for i in (1, 2, 3)]
    result = solve(emps, [1, 1, 1], max_schedules=5, seed=0)
    assert result["count"] >= 1
    assert "closest" not in result
    assert "infeasibility" not in result


def test_modes_fast_thorough_auto():
    # C is pool-short (needs 2, only employee 3 can do it) -> fast prunes it at the root.
    emps = [
        make_emp(1, "a", [True, False, False]),
        make_emp(2, "b", [False, True, False]),
        make_emp(3, "c", [False, False, True]),
    ]
    mins = [1, 1, 2]
    fast = solve(emps, mins, seed=0, mode="fast")
    thorough = solve(emps, mins, seed=0, mode="thorough")
    auto = solve(emps, mins, seed=0, mode="auto")

    assert "closest" not in fast                                    # pruned -> nothing to show
    assert thorough["closest"]["schedules"][0]["coverage"] == [1, 1, 1]
    assert auto["closest"]["mode"] == "thorough"                    # escalated past empty fast
    assert auto["closest"]["schedules"][0]["coverage"] == [1, 1, 1]


def test_fast_mode_handles_contention():
    # All-qualified trio, target [2,2,0]: each task is reachable, so fast (which keeps the
    # feasibility pruning) still finds near-misses without escalating.
    emps = [make_emp(i, "x", [True, True, False]) for i in (1, 2, 3)]
    result = solve(emps, [2, 2, 0], seed=0, mode="fast")
    assert result["count"] == 0
    assert result["closest"]["mode"] == "fast"
    assert result["closest"]["schedules"]


def test_metric_parameter_is_threaded_and_ranks_by_it():
    emps = [
        make_emp(1, "a", [True, False, True]),
        make_emp(2, "b", [False, True, True]),
        make_emp(3, "c", [False, False, True]),
        make_emp(4, "d", [False, False, True]),
    ]
    for metric in ("cosine", "l1"):
        result = solve(emps, [1, 1, 6], max_schedules=5, seed=0, mode="thorough", metric=metric)
        assert result["closest"]["metric"] == metric
        distances = [s["distance"] for s in result["closest"]["schedules"]]
        assert distances == sorted(distances)          # ranked by the chosen metric


def test_close_schedules_are_deduplicated():
    emps = [make_emp(i, "x", [True, True, False]) for i in (1, 2, 3)]   # 3 employees do A,B
    result = solve(emps, [2, 2, 0], max_schedules=20, seed=0, mode="thorough")
    seen = set()
    for s in result["closest"]["schedules"]:
        signature = tuple(sorted((row["ID Alias"], row["Function"]) for row in s["table"]))
        assert signature not in seen
        seen.add(signature)


def test_close_search_respects_budget_and_cap():
    # 20 all-qualified employees, 30 requested slots -> understaffed; a tiny budget must
    # return promptly with at most max_schedules candidates and no explosion.
    emps = [make_emp(i, f"e{i}", [True, True, True]) for i in range(20)]
    result = solve(emps, [10, 10, 10], max_schedules=8, time_budget_s=0.05, seed=0, mode="thorough")
    assert result["count"] == 0
    if "closest" in result:
        assert len(result["closest"]["schedules"]) <= 8
