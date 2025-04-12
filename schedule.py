import employee as e
import constraints as c
import random as r
import copy

class Schedule:
     def __init__(self, employeesToAssign: list[e.Employee], constraints: c.Constraints):
         self._employeesToAssign = employeesToAssign
         self._taskAssignments = self.taskAssignmentSetter(employeesToAssign[0].taskStatuses)
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
     
     #@taskAssignments.setter
     @staticmethod
     def taskAssignmentSetter(taskStatuses):
         amountOfApprovals = len(taskStatuses) + 1
         taskAssignments = {f'task{i}' : [] for i in range(amountOfApprovals)}
         return taskAssignments
 
     @property
     def employeesToAssign(self):
          return self._employeesToAssign
        
     @employeesToAssign.setter
     def employeesToAssign(self, employees):
         employeeList = [[] * (len(employees[0].taskStatuses) + 1)]
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

         if self.fullTest():
               validSchedules.append(copy.deepcopy(self))
               return
         flag = True
         for employee in employees:
               updateEmployees = employees.copy()
               updateEmployees.remove(employee)
               if employee.numApprovedTasks > 0:
                    for i in employee.indexApprovedTasks[1:]:
                         key = list(self.taskAssignments.keys())[i]
                         self.taskAssignments[key].append(employee)
                         if self.partialTest():
                              self.findAssignment(updateEmployees, validSchedules)
                         self.taskAssignments[key].pop()

                         if key == list(self.taskAssignments.keys())[-1]:
                              flag = False

               if not flag:
                    break
                         
               else:
                    key = list(self.taskAssignments.keys())[0]
                    self.taskAssignments[key].append(employee)
                    #self.findAssignment(updateEmployees, validSchedules)
         

     def findAssignmentArchive(self, employees: list[e.Employee], validSchedules: list):
         if len(validSchedules) == 50:
              return
         flag = True
         if employees:
              for employee in employees:
                    updateEmployees = employees[1:]
                    if employee.numApprovedTasks > 0:
                         for i in employee.indexApprovedTasks[1:]:
                              key = list(self.taskAssignments.keys())[i]
                              self.taskAssignments[key].append(employee)
                              if self.partialTest():
                                   if self.fullTest():
                                        validSchedules.append(copy.deepcopy(self))
                                   self.findAssignment(updateEmployees, validSchedules)
                              self.taskAssignments[key].pop()
                              if key == list(self.taskAssignments.keys())[-1]:
                                   flag = False
                    if not flag:
                         break
                    else:
                         key = list(self.taskAssignments.keys())[0]
                         self._taskAssignments[key].append(employee)
                         if self.fullTest():
                              validSchedules.append(copy.deepcopy(self))
                         self.findAssignment(updateEmployees, validSchedules)
         else:
              if self.fullTest():
                    validSchedules.append(copy.deepcopy(self))   

     def findAssignment2(self, employees: list[e.Employee], validSchedules: list):
      if not employees:
          if self.fullTest():
              validSchedules.append(copy.deepcopy(self))
          return
  
      for idx, employee in enumerate(employees):
          updateEmployees = employees[:idx] + employees[idx+1:]
  
          if employee.numApprovedTasks > 0:
              for i in employee.indexApprovedTasks[1:]:  # Skipping the 0th as per your logic
                  key = list(self.taskAssignments.keys())[i]
                  self.taskAssignments[key].append(employee)
  
                  if self.partialTest():
                      if self.fullTest():
                          validSchedules.append(copy.deepcopy(self))
                      self.findAssignment(updateEmployees, validSchedules)
  
                  self.taskAssignments[key].pop()
  
                  if key == list(self.taskAssignments.keys())[-1]:
                      return  # Stop exploring if the last task was tested unsuccessfully
          else:
              # Assign to the default bucket (i.e., not approved for any task)
              key = list(self.taskAssignments.keys())[0]
              self.taskAssignments[key].append(employee)
  
              if self.fullTest():
                  validSchedules.append(copy.deepcopy(self))
  
              self.findAssignment(updateEmployees, validSchedules)
              self.taskAssignments[key].pop()
