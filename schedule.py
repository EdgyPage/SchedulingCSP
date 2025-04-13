import employee as e
import constraints as c
import random as r
import copy

class Schedule:
     def __init__(self, employeesToAssign: list[e.Employee], constraints: c.Constraints):
         self.employeesToAssign = employeesToAssign
         self.taskAssignments = employeesToAssign[0].taskStatuses
         self.constraints = constraints
 
     @property
     def constraints(self):
          return self._constraints
     
     @constraints.setter
     def constraints(self, constraints):
          self._constraints = constraints
 
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
     def taskAssignments(self, taskStatuses):
         amountOfApprovals = len(taskStatuses) + 1
         taskAssignments = {f'task{i}' : [] for i in range(amountOfApprovals)}
         self._taskAssignments = taskAssignments
 
     @property
     def employeesToAssign(self):
          return self._employeesToAssign
        
     @employeesToAssign.setter
     def employeesToAssign(self, employees):
         tasks = employees[0].taskStatuses
         employeeList = [[] for l in range(len(tasks))]
         for employee in employees:
                 numApprovals = employee.numApprovedTasks
                 employeeList[numApprovals].append(employee)
         for innerList in employeeList:
              r.shuffle(innerList)
         employeeList = [employee for innerList in employeeList for employee in innerList]
         self._employeesToAssign = employeeList
     
     def partialTestDecorator(func):
          func.isPartialTest = True
          return func
     
     def fullTestDecorator(func):
          func.isFullTest = True
          return func

     @partialTestDecorator
     def testLengthPartial(self):
          flag = True
          for i, value in enumerate((self.taskAssignments.values())):
               if self.constraints.taskMins[i] < len(value):
                    flag = False
                    return flag
          return flag
     
     @fullTestDecorator
     def testLengthFull(self):
          flag = True
          for i, value in enumerate(list(self.taskAssignments.values())[1:]):
               if self.constraints.taskMins[i+1] != len(value):
                    flag = False
                    return flag
          return flag

     def partialTest(self):
          results = {}
          for name in dir(self):
               method = getattr(self, name)
               if callable(method) and getattr(method, 'isPartialTest', False):
                    results[name] = method()
          for key, value in results.items():
               if value == False:
                    return False
          return True
          
     def fullTest(self):
          results = {}
          for name in dir(self):
               method = getattr(self, name)
               if callable(method) and getattr(method, 'isFullTest', False):
                    results[name] = method()
          for key, value in results.items():
               if value == False:
                    return False
          return True
      
     def findAssignment(self, employees: list[e.Employee], validSchedules: list):
         print(f"Recursing with {len(employees)} employees left.")
         if len(validSchedules) == 10:
              return
         
         if self.fullTest():
               validSchedules.append(copy.deepcopy(self))
               return
         flag = True

         for i in range(len(employees)):
               employee = employees[i]
               if i == len(employees)-1:
                    updateEmployees = []
               else:
                    updateEmployees = employees[i+1:]
               if employee.numApprovedTasks == 0:
                    key = list(self.taskAssignments.keys())[0]
                    self.taskAssignments[key].append(employee)
                    self.taskAssignments[key] = list(dict.fromkeys(self.taskAssignments[key]))
                    if self.fullTest():
                         validSchedules.append(copy.deepcopy(self))
                    continue

               for j in employee.indexApprovedTasks[1:]:
                         key = list(self.taskAssignments.keys())[j]
                         self.taskAssignments[key].append(employee)
                         if self.partialTest():
                              self.findAssignment(updateEmployees, validSchedules)
                         self.taskAssignments[key].pop()

                         if key == list(self.taskAssignments.keys())[-1]:
                              flag = False

               if not flag:
                    break
                         
         


     
