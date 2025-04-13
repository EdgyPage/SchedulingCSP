import employee as e

class Constraints:
    def __init__(self, taskMins: list[int]):
        self.taskMins = taskMins

    @property
    def taskMins(self):
        return self._taskMins

    @taskMins.setter
    def taskMins(self, mins: list[int]):
        self._taskMins = [float('inf')] + mins