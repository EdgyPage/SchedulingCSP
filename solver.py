"""High-level entrypoint: employees + minimums in, JSON-ready schedules out.

This is the single function a web handler (or the notebook) should call. It ties
together Constraints, the Schedule search, and the JSON serializer, and performs no
I/O of its own.
"""

from constraints import Constraints
from schedule import Schedule
from io_adapters import schedules_to_json


def solve(employees, minimums, max_schedules=10, *,
          time_budget_s=None, max_nodes=None, seed=None):
    """Run the CSP and return ``{"count": int, "schedules": [[row, ...], ...]}``.

    Each row is ``{"Name", "ID", "Function"}``. The search is bounded by
    ``max_schedules`` and, optionally, ``time_budget_s`` / ``max_nodes`` -- when a
    limit is hit it returns whatever valid schedules were found so far.
    """
    constraints = Constraints(minimums)
    schedule = Schedule(
        employees, constraints, max_schedules,
        seed=seed, time_budget_s=time_budget_s, max_nodes=max_nodes,
    )
    schedule.populateAssignments()
    return {
        "count": len(schedule.validSchedules),
        "schedules": schedules_to_json(schedule.validSchedules),
    }
