import employee as e

class Schedule:
    def __init__(self, taskMins: list[int], unassignedEmployees: list[e.Employee]):
        self._taskAssignments = {
            'task1': [],
            'task2': [],
            'task3': [],
            'task4': [],
            'task5': [],
            'task6': [],
            'task7': []
        }

        self._unassignedEmployees = unassignedEmployees

        @unassignedEmployees.setter
        def unassignedEmployees(self, employees):
            
            for employee in employees:
                    pass