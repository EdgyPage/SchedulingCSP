import employee as e

class Constraints:
    def __init__(self, taskMins: list[int]):
        self._taskMins = taskMins

    @property
    def taskMins(self):
        return self._taskMins

    @taskMins.setter
    def taskMins(self, mins: list[int]):
        if len(self.taskStatuses) == len(mins):
            self._taskMins = mins
        else:
            raise ValueError('List of task minimums does not equal length of assignable tasks.')