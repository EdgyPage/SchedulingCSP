"""Backtracking CSP solver that assigns employees to tasks.

This module is pure and importable: it performs no disk writes and no stdout
printing. Build a :class:`Schedule`, call :meth:`populateAssignments`, then read
:attr:`validSchedules` -- a list of ``{task_name: [Employee, ...]}`` dicts, one per
valid schedule found.

The search is bounded: it stops as soon as ``maxLength`` schedules are found, and
(optionally) when a wall-clock ``time_budget_s`` or ``max_nodes`` limit is reached,
returning whatever it found so far. That guarantees a response regardless of input
size, which matters when this runs behind a web request.
"""

import heapq
import random
import time

import employee as e
import constraints as c
from scoring import rank_key

# Safety backstop for the relaxed close search when the caller sets no budget at all
# (the web layer always passes a time budget; direct solve() calls may not).
_CLOSE_DEFAULT_NODE_CAP = 1_000_000


class Schedule:
    def __init__(self, employeesToAssign: list[e.Employee], constraints: c.Constraints,
                 maxLength: int, *, seed=None, time_budget_s: float | None = None,
                 max_nodes: int | None = None):
        self._rng = random.Random(seed)
        self.tasks = employeesToAssign[0].tasks
        self.taskAssignments = None            # setter ignores the value; builds empty buckets
        self._task_keys = list(self._taskAssignments.keys())
        self.constraints = constraints
        self._validSchedules = []
        self._schedule_signatures = set()
        self.maxLength = maxLength
        # _initialEmployees must hold ALL employees (including anyone approved for zero
        # tasks) so findUnassignedEmployees can sweep them into 'Unassigned' at the end.
        self._initialEmployees = list(employeesToAssign)
        self.employeesToAssign = employeesToAssign   # bucketed working list (qualified only)
        self.maxPossibleAssignment = employeesToAssign
        # runtime budget
        self._time_budget_s = time_budget_s
        self._max_nodes = max_nodes
        self._deadline = None
        self._nodes = 0
        self._cache_tests()

    @property
    def maxLength(self):
        return self._maxLength

    @maxLength.setter
    def maxLength(self, value):
        if value >= 1:
            self._maxLength = value
        else:
            raise ValueError('Max Length is not valid input!')

    @property
    def tasks(self):
        return self._tasks

    @tasks.setter
    def tasks(self, tasks):
        self._tasks = tasks

    @property
    def validSchedules(self):
        return self._validSchedules

    @property
    def nodes(self):
        """Search nodes visited during the last populateAssignments() run.

        Deterministic for a fixed seed; used by the test harness as a stable
        performance signal instead of flaky wall-clock timing.
        """
        return self._nodes

    @property
    def constraints(self):
        return self._constraints

    @constraints.setter
    def constraints(self, constraints):
        self._constraints = constraints

    def __repr__(self):
        return str(self.taskAssignments)

    @property
    def taskAssignments(self):
        return self._taskAssignments

    @taskAssignments.setter
    def taskAssignments(self, value):
        # The argument only signals "(re)initialize"; the buckets are derived from
        # self.tasks. Index 0 is the catch-all 'Unassigned' bucket.
        self._taskAssignments = {'Unassigned': []} | {task: [] for task in self.tasks}

    @property
    def employeesToAssign(self):
        return self._employeesToAssign

    @employeesToAssign.setter
    def employeesToAssign(self, employees):
        num_tasks = len(employees[0].taskStatuses)
        # Bucket by number of approved tasks. Size is num_tasks + 1 so an employee
        # approved for *every* task (numApprovedTasks == num_tasks) has a slot.
        buckets = [[] for _ in range(num_tasks + 1)]
        for employee in employees:
            buckets[employee.numApprovedTasks].append(employee)
        for bucket in buckets:
            self._rng.shuffle(bucket)
        # Most-constrained-first ordering (fewest approvals first). Bucket 0 holds
        # employees approved for nothing -- they can't be placed, so drop them from
        # the working list; they resurface in 'Unassigned' via findUnassignedEmployees.
        self._employeesToAssign = [emp for bucket in buckets[1:] for emp in bucket]

    @property
    def maxPossibleAssignment(self):
        return self._maxPossibleAssignment

    @maxPossibleAssignment.setter
    def maxPossibleAssignment(self, employees):
        maxAssignments = {key: 0 for key in self._task_keys}
        for employee in employees:
            for index in employee.indexApprovedTasks:
                maxAssignments[self._task_keys[index]] += 1
        self._maxPossibleAssignment = maxAssignments

    def findUnassignedEmployees(self):
        assigned = set()
        for key, value in self.taskAssignments.items():
            if key != 'Unassigned':
                assigned.update(value)
        return list(set(self._initialEmployees) - assigned)

    def adjustMaxPossible(self, employee: e.Employee, increment: bool):
        change = 1 if increment else -1
        for index in employee.indexApprovedTasks:
            self._maxPossibleAssignment[self._task_keys[index]] += change

    # --- constraint tests -------------------------------------------------------

    def partialTestDecorator(func):
        func.isPartialTest = True
        return func

    def fullTestDecorator(func):
        func.isFullTest = True
        return func

    @partialTestDecorator
    def testLengthPartial(self):
        """Prune branches where a task has already exceeded its target headcount."""
        for i, (key, value) in enumerate(self.taskAssignments.items()):
            if key == 'Unassigned':
                continue
            if self.constraints.taskMins[i] < len(value):
                return False
        return True

    @partialTestDecorator
    def testTaskMins(self):
        """Prune branches where the remaining talent pool can't reach a task's min."""
        for i, (key, value) in enumerate(self.taskAssignments.items()):
            if key == 'Unassigned':
                continue
            taskMin = self.constraints.taskMins[i]
            talentPool = len(value) + self.maxPossibleAssignment[key]
            if talentPool < taskMin and taskMin != float('inf'):
                return False
        return True

    @fullTestDecorator
    def testLengthFull(self):
        """A schedule is complete only when every task hits its target exactly."""
        for i, (key, value) in enumerate(list(self.taskAssignments.items())[1:]):
            if self.constraints.taskMins[i + 1] != len(value):
                return False
        return True

    def _cache_tests(self):
        """Discover the decorated constraint methods once instead of on every node."""
        self._partial_tests = []
        self._full_tests = []
        for name in dir(self):
            method = getattr(self, name)
            if not callable(method):
                continue
            if getattr(method, 'isPartialTest', False):
                self._partial_tests.append(method)
            elif getattr(method, 'isFullTest', False):
                self._full_tests.append(method)

    def partialTest(self):
        return all(test() for test in self._partial_tests)

    def fullTest(self):
        return all(test() for test in self._full_tests)

    # --- search -----------------------------------------------------------------

    @staticmethod
    def _signature(assignment):
        """Order-independent identity of an assignment, for de-duplication."""
        return tuple(sorted(
            (key, tuple(sorted(str(emp.id) for emp in emps)))
            for key, emps in assignment.items()
        ))

    def createCompleteAssignment(self):
        assignment = dict(self.taskAssignments)
        assignment['Unassigned'] = self.findUnassignedEmployees()
        signature = self._signature(assignment)
        if signature in self._schedule_signatures:
            return
        self._schedule_signatures.add(signature)
        # Shallow-copy each task list; Employee objects are not mutated during the
        # search, so a deepcopy is unnecessary (and much slower).
        self._validSchedules.append({task: list(emps) for task, emps in assignment.items()})

    def _budget_exceeded(self):
        if self._deadline is not None and time.monotonic() >= self._deadline:
            return True
        if self._max_nodes is not None and self._nodes >= self._max_nodes:
            return True
        return False

    def findAssignments(self, employees: list[e.Employee]):
        if self._budget_exceeded():
            return
        self._nodes += 1
        if len(self._validSchedules) >= self.maxLength:
            return
        if self.fullTest():
            self.createCompleteAssignment()
            return

        for i in range(len(employees)):
            if len(self._validSchedules) >= self.maxLength or self._budget_exceeded():
                return
            employee = employees[i]
            remaining = employees[i + 1:]
            # indexApprovedTasks[0] is always 0 ('Unassigned'); skip it and try each
            # task the employee is actually approved for.
            for j in employee.indexApprovedTasks[1:]:
                key = self._task_keys[j]
                self.taskAssignments[key].append(employee)
                self.adjustMaxPossible(employee, False)
                if self.partialTest():
                    self.findAssignments(remaining)
                self.taskAssignments[key].pop()
                self.adjustMaxPossible(employee, True)

    def populateAssignments(self):
        if self._time_budget_s is not None:
            self._deadline = time.monotonic() + self._time_budget_s
        self.findAssignments(self.employeesToAssign)
        return self._validSchedules

    # --- closest-schedule search (runs only when no exact schedule exists) -------

    def search_close(self, top_n, metric_fn, relaxed):
        """Find up to ``top_n`` maximal assignments closest to the ideal coverage.

        ``metric_fn(coverage, ideal) -> distance`` ranks candidates (smaller = closer).
        ``relaxed=False`` (Fast) keeps the exact search's ``testTaskMins`` pruning, so it
        never blows up; ``relaxed=True`` (Thorough) drops it and instead prunes by a score
        branch-and-bound. The search runs on its own node counter so the exact-search perf
        signal (``Schedule.nodes``) is untouched. Returns a list of
        ``(assignment, coverage, distance)`` ordered closest-first.
        """
        # Reset the working state (defensive: it is already clean after a full search).
        self.taskAssignments = None
        self.maxPossibleAssignment = self._initialEmployees

        self._close_top_n = max(1, top_n)
        self._close_metric = metric_fn
        self._close_relaxed = relaxed
        self._close_ideal = list(self.constraints.taskMins[1:])
        self._close_heap = []          # min-heap on a reversed key => root is the worst kept
        self._close_sigs = set()
        self._close_tiebreak = 0
        self._close_nodes = 0
        self._close_max_nodes = self._max_nodes if self._max_nodes is not None \
            else _CLOSE_DEFAULT_NODE_CAP
        # Fresh deadline: the exact pass may already have spent the original budget.
        if self._time_budget_s is not None:
            self._deadline = time.monotonic() + self._time_budget_s

        self._search_close(0)

        payloads = [entry[1] for entry in self._close_heap]
        payloads.sort(key=lambda p: p[3])          # by rank tuple, closest first
        return [(assignment, coverage, distance)
                for (assignment, coverage, distance, _rank) in payloads]

    def _close_budget_exceeded(self):
        if self._deadline is not None and time.monotonic() >= self._deadline:
            return True
        return self._close_nodes >= self._close_max_nodes

    def _search_close(self, idx):
        if self._close_budget_exceeded():
            return
        self._close_nodes += 1
        # Thorough-mode branch-and-bound: abandon a subtree whose best possible completion
        # can't out-rank the worst candidate already kept (reuses the maxPossible pool
        # bound). This is what replaces testTaskMins as the search's real bound.
        if self._close_relaxed and self._heap_full() and not self._can_improve():
            return
        employees = self.employeesToAssign
        if idx >= len(employees):
            self._record_close()
            return
        employee = employees[idx]
        placed_any = False
        for j in employee.indexApprovedTasks[1:]:
            key = self._task_keys[j]
            if len(self.taskAssignments[key]) >= self.constraints.taskMins[j]:
                continue                               # task already at its target (cap)
            self.taskAssignments[key].append(employee)
            self.adjustMaxPossible(employee, False)
            if self._close_relaxed or self.testTaskMins():
                placed_any = True
                self._search_close(idx + 1)
            self.taskAssignments[key].pop()
            self.adjustMaxPossible(employee, True)
            if self._close_budget_exceeded():
                return
        if not placed_any:
            # Employee can't be placed now (every approved task is full or pruned); bench
            # them and continue. Their tasks only get fuller, so the leaf stays maximal.
            self._search_close(idx + 1)

    def _heap_full(self):
        return len(self._close_heap) >= self._close_top_n

    def _can_improve(self):
        """Could the best completion reachable from here beat the worst kept candidate?

        Optimistic: assume every task fills to its target from its remaining pool (ignores
        that employees are shared, so it never under-estimates coverage). Admissible for
        the L1 metric; a strong heuristic for cosine.
        """
        best_cov = []
        for k in range(1, len(self._task_keys)):
            key = self._task_keys[k]
            ceiling = len(self.taskAssignments[key]) + self.maxPossibleAssignment[key]
            best_cov.append(min(self.constraints.taskMins[k], ceiling))
        best_rank = (self._close_metric(best_cov, self._close_ideal), -sum(best_cov))
        worst_rank = self._close_heap[0][1][3]
        return best_rank < (worst_rank[0], worst_rank[1])

    def _record_close(self):
        coverage = [len(self.taskAssignments[self._task_keys[k]])
                    for k in range(1, len(self._task_keys))]
        covered = sum(coverage)
        if covered == 0:
            return                                     # nothing placed -> not worth showing
        assignment = dict(self.taskAssignments)
        assignment['Unassigned'] = self.findUnassignedEmployees()
        signature = self._signature(assignment)
        if signature in self._close_sigs:
            return
        self._close_sigs.add(signature)
        distance = self._close_metric(coverage, self._close_ideal)
        self._close_tiebreak += 1
        rank = rank_key(distance, covered, self._close_tiebreak)
        snapshot = {task: list(emps) for task, emps in assignment.items()}
        payload = (snapshot, coverage, distance, rank)
        # Reversed key makes heap[0] the WORST kept, so heappushpop evicts it.
        reversed_key = (-rank[0], -rank[1], -rank[2])
        if len(self._close_heap) < self._close_top_n:
            heapq.heappush(self._close_heap, (reversed_key, payload))
        else:
            heapq.heappushpop(self._close_heap, (reversed_key, payload))

    def writeAssignmentsToExcel(self, filePath: str = ''):
        """Convenience for local/notebook use: write one .xlsx per schedule to disk.

        Web callers should use the in-memory serializers in ``io_adapters`` instead.
        """
        from io_adapters import write_schedules_to_excel_files
        write_schedules_to_excel_files(self._validSchedules, filePath)
