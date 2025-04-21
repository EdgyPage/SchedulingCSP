# SchedulingCSP  
## Overview
This repository is a small set of objects that return a schedule list given a file of employees. This is meant to be skeleton code for a functioning constraint satisfaction problem solver.  
Employees are defined by the tasks they are trained on, names, and ID numbers.  The constraint is a list of numbers for which the ideal schedule will have a minimum amount of employees assigned to them.

## Workflow
main.ipynb is a convenient way to run the CSP algorithm after defining a list of minimum assignments for each available task. Complete schedules are written to file, incomplete schedules are not.
