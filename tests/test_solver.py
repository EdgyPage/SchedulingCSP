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
        function_by_id = {row["ID"]: row["Function"] for row in table}
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
