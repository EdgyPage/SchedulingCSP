import os
import sys

# Make the top-level modules (employee, constraints, schedule, ...) importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
