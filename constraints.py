class Constraints:
    def __init__(self, taskMins: list[int]):
        self.taskMins = taskMins

    @property
    def taskMins(self):
        return self._taskMins

    @taskMins.setter
    def taskMins(self, mins: list[int]):
        # Index 0 corresponds to the 'Unassigned' bucket, which has no minimum.
        # Build from a fresh copy so the setter never aliases the caller's list.
        self._taskMins = [float('inf')] + list(mins)