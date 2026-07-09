"""High-level entrypoint: employees + minimums in, JSON-ready schedules out.

This is the single function a web handler (or the notebook) should call. It ties
together Constraints, the Schedule search, and the JSON serializer, and performs no
I/O of its own.

When no schedule hits the requested coverage exactly, ``solve`` additionally returns
*why* it's infeasible and a ranked list of the closest achievable schedules (see the
``closest`` key), so the caller can show the user something actionable instead of an
empty result.
"""

from constraints import Constraints
from schedule import Schedule
from io_adapters import schedules_to_json
from scoring import METRICS


def solve(employees, minimums, max_schedules=10, *,
          time_budget_s=None, max_nodes=None, seed=None, metric="cosine", mode="auto"):
    """Run the CSP and return ``{"count": int, "schedules": [[row, ...], ...]}``.

    Each row is ``{"Name", "ID", "Function"}``. The search is bounded by
    ``max_schedules`` and, optionally, ``time_budget_s`` / ``max_nodes``.

    On complete failure (no exact schedule) the result also carries:
      * ``infeasibility`` -- per-task pool shortfalls and a total-headcount check;
      * ``closest`` -- up to ``max_schedules`` nearest schedules ranked by ``metric``
        ("cosine" or "l1"), found via ``mode`` ("auto" | "fast" | "thorough").
    """
    constraints = Constraints(minimums)
    schedule = Schedule(
        employees, constraints, max_schedules,
        seed=seed, time_budget_s=time_budget_s, max_nodes=max_nodes,
    )
    schedule.populateAssignments()
    result = {
        "count": len(schedule.validSchedules),
        "schedules": schedules_to_json(schedule.validSchedules),
    }
    if not schedule.validSchedules:
        result["infeasibility"] = diagnose_feasibility(employees, minimums)
        metric_fn = METRICS.get(metric, METRICS["cosine"])
        close, used_mode = _closest(schedule, max_schedules, metric_fn, mode)
        if close:
            result["closest"] = _build_closest_payload(close, minimums, metric, used_mode)
    return result


def diagnose_feasibility(employees, minimums):
    """Cheap, actionable 'why is this infeasible' report.

    Names every task whose requested headcount exceeds the number of employees approved
    for it, and flags when there simply aren't enough people overall. Catches the obvious
    hopeless cases; subtler interaction infeasibility still shows up in the returned
    ``closest`` coverage/shortfall.
    """
    tasks = employees[0].tasks if employees else []
    approved = [0] * len(minimums)
    for emp in employees:
        for j, ok in enumerate(emp.taskStatuses):
            if j < len(approved) and ok:
                approved[j] += 1
    reasons = [
        {"task": tasks[i] if i < len(tasks) else f"task_{i}",
         "needed": minimums[i], "available": approved[i], "short": minimums[i] - approved[i]}
        for i in range(len(minimums)) if approved[i] < minimums[i]
    ]
    total_needed = sum(minimums)
    return {
        "reasons": reasons,
        "understaffed": total_needed > len(employees),
        "total_needed": total_needed,
        "total_available": len(employees),
    }


def _closest(schedule, top_n, metric_fn, mode):
    """Run the near-miss search per ``mode``; returns ``(candidates, mode_used)``.

    Auto tries the cheap, always-bounded Fast pass first and only escalates to the deeper
    Thorough pass when Fast comes up empty (e.g. a raw pool-shortfall pruned at the root).
    """
    if mode in ("auto", "fast"):
        candidates = schedule.search_close(top_n, metric_fn, relaxed=False)
        if candidates or mode == "fast":
            return candidates, "fast"
    return schedule.search_close(top_n, metric_fn, relaxed=True), "thorough"


def _build_closest_payload(close, minimums, metric, mode):
    target = list(minimums)
    target_total = sum(target)
    tables = schedules_to_json([assignment for assignment, _cov, _dist in close])
    schedules = []
    for (assignment, coverage, distance), table in zip(close, tables):
        schedules.append({
            "table": table,
            "distance": distance,
            "coverage": list(coverage),
            "shortfall": [max(t - c, 0) for t, c in zip(target, coverage)],
            "covered": sum(coverage),
            "target_total": target_total,
        })
    return {
        "metric": metric,
        "mode": mode,
        "target": target,
        "count": len(schedules),
        "schedules": schedules,
    }
