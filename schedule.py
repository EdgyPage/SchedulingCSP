import employee as e
import constraints as c

class Schedule:
    def __init__(self, employeesToAssign: list[e.Employee], constraints: c.Constraints):
        self._employeesToAssign = employeesToAssign
        self._taskAssignments = employeesToAssign[0].taskStatuses
        self._constraints = constraints

    @property
    def constraints(self):
         return self._constraints

    def __repr__(self):
         return self.taskAssignments
    
    @property
    def getAttributes(self):
         return vars(self)

    def __eq__(self, other):
         flag = True
         if not isinstance(other, Schedule):
              flag = False
              return flag
         selfAttributes = self.getAttributes()
         otherAttributes = other.getAttributes()
         flag = selfAttributes == otherAttributes
         return flag
    
    def __hash__(self):
         hashable = tuple()
         for key, values in self.taskAssignments.items():
              hashable = hashable + (key, )
              for value in values:
                   hashable = hashable + (value,)
         return hash(hashable)

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

    def test():
         pass

    def findAssignment():
         pass
    
