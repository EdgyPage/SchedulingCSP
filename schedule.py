import employee as e
import constraints as c
import random as r
import copy

class Schedule:
     def __init__(self, employeesToAssign: list[e.Employee], constraints: c.Constraints, maxLength : int):
         self.taskAssignments = employeesToAssign[0].taskStatuses
         self.employeesToAssign = employeesToAssign
         self.constraints = constraints
         self._validSchedules = []
         self.maxLength = maxLength
         self._initialEmployees = self.employeesToAssign
         self.maxPossibleAssignment = employeesToAssign

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
     def validSchedules(self):
          return self._validSchedules

     @property
     def constraints(self):
          return self._constraints
     
     @constraints.setter
     def constraints(self, constraints):
          self._constraints = constraints
 
     def __repr__(self):
          return str(self.taskAssignments)
     
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
                 if numApprovals == 0:
                      key = list(self.taskAssignments.keys())[0]
                      self.taskAssignments[key].append(employee)
                 else:
                      employeeList[numApprovals].append(employee)
         for innerList in employeeList:
              r.shuffle(innerList)
         employeeList = [employee for innerList in employeeList for employee in innerList]
         self._employeesToAssign = employeeList
     
     def assignUnqualifiedEmployees(self):
          unqualified = []
          for employee in self.employeesToAssign:
               if employee.numApprovedTasks == 0:
                    key = list(self.taskAssignments.keys())[0]
                    self.taskAssignments[key].append(employee)
                    unqualified.append(employee)
          for employee in unqualified:
               self.employeesToAssign.remove(employee)

     def findUnassignedEmployees(self):
          assigned = set()
          for key, value in self.taskAssignments.items():
               if key != 'Unassigned':
                    assigned.update(value)
          unassigned = list(set(self._initialEmployees) - assigned)
          return unassigned

     def partialTestDecorator(func):
          func.isPartialTest = True
          return func
     
     def fullTestDecorator(func):
          func.isFullTest = True
          return func

     @partialTestDecorator
     def testLengthPartial(self):
          flag = True
          for i, (key, value) in enumerate((self.taskAssignments.items())):
               if key == 'Unassigned':
                    continue
               elif self.constraints.taskMins[i] < len(value):
                    flag = False
                    return flag
          return flag
     
     @partialTestDecorator
     def testTaskMins(self):
          flag = True
          for i, (key, value) in enumerate(self.taskAssignments.items()):
               if key == 'Unassigned':
                    continue
               taskMin = self.constraints.taskMins[i]
               talentPool = (len(value) + self.maxPossibleAssignment[key])
               if talentPool < taskMin and taskMin != float('inf'):
                    flag = False
                    return flag
          return flag   

     @fullTestDecorator
     def testLengthFull(self):
          flag = True
          for i, (key, value) in enumerate(list(self.taskAssignments.items())[1:]):
               if key == 'Unassigned':
                    continue
               if self.constraints.taskMins[i+1] != len(value):
                    flag = False
                    return flag
          return flag

     def adjustMaxPossible(self, employee: e.Employee, increment: bool):
          keys = list(self.taskAssignments.keys())
          if increment:
               change = 1
          else:
               change = -1
          for index in employee.indexApprovedTasks:
               self.maxPossibleAssignment[keys[index]] += change

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
     
     def createCompleteAssignment(self):
          self.taskAssignments['Unassigned'] = self.findUnassignedEmployees()
          self.validSchedules.append(copy.deepcopy(self.taskAssignments))

     @property
     def maxPossibleAssignment(self):
          return self._maxPossibleAssignment

     @maxPossibleAssignment.setter
     def maxPossibleAssignment(self, employees):
          keys = list(self.taskAssignments.keys())
          maxAssignments = {key: 0 for key in keys}
          for employee in employees:
               for index in employee.indexApprovedTasks:
                    key = list(self.taskAssignments.keys())[index]
                    maxAssignments[key] += 1
          self._maxPossibleAssignment = maxAssignments


     def findAssignments(self, employees: list[e.Employee]):
         #print(f"Recursing with {len(employees)} employees left.")
         if len(self.validSchedules) == self.maxLength:
              return
         
         if self.fullTest():
               self.createCompleteAssignment()
               self.ensureUniqueAssignments()
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
                         self.createCompleteAssignment()
                         self.ensureUniqueAssignments()
                    continue

               for j in employee.indexApprovedTasks[1:]:
                         key = list(self.taskAssignments.keys())[j]
                         self.taskAssignments[key].append(employee)
                         self.adjustMaxPossible(employee, False)
                         if self.partialTest():
                              self.findAssignments(updateEmployees)
                         self.taskAssignments[key].pop()
                         self.adjustMaxPossible(employee, True)

                         if key == list(self.taskAssignments.keys())[-1]:
                              flag = False

               if not flag:
                    break

     def ensureUniqueAssignments(self):
          list_of_dicts = self.validSchedules
          # Convert to a normalized hashable form
          def dict_to_tuple_unordered_lists(d):
              return tuple(sorted((k, tuple(sorted(v))) for k, v in d.items()))
          # Make a set of the hashable representations
          set_of_dicts = set(dict_to_tuple_unordered_lists(d) for d in list_of_dicts)

          # Optionally, convert back to dicts (if needed)
          unique_dicts = [dict((k, list(v)) for k, v in t) for t in set_of_dicts]
     
          self._validSchedules = unique_dicts

     def populateAssignments(self):
          self.assignUnqualifiedEmployees()
          self.findAssignments(self.employeesToAssign)
         


     
