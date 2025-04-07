import employee as e

class Schedule:
    def __init__(self, taskMins: list[int], employeesToAssign: list[e.Employee]):
        self._employeesToAssign = employeesToAssign
        self._taskAssignments = employeesToAssign[0].taskStatuses


    @property
    def taskAssignments(self):
        return self._taskAssignments
    
    @taskAssignments.setter
    def taskAssignments(self, numTasks):
        taskAssignments = {f'task{i}' : [] for i in range(numTasks+1)}
        self._taskAssignments = taskAssignments

    @property
    def employeesToAssign(self):
         return self._employeesToAssign
       
    @employeesToAssign.setter
    def employeesToAssign(self, employees):
        employeeList = [[] * (len(employees[0].taskStatuses) + 1)]
        for employee in employees:
                numApprovals = employee.numApprovedTasks
                employeeList[numApprovals].append(employee)
        self._employeesToAssign = employeeList
                         