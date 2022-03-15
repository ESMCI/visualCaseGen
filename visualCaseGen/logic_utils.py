""" This module includes some logical operator and type definitions to be used to specify relational assertions."""

from z3 import Or
from z3 import If as z3_If
from collections import namedtuple

# The When clause used to specify conditional assertions
When = namedtuple("When", "antecedent consequent")

def In(var, value_list):
    """Expression to check whether the value of a variable is in a given list."""
    return Or([var==value for value in value_list])

def MinVal(varlist):
    """Given a numeric varlist, returns the variable with minimum value."""
    min_val = varlist[0]
    for val in varlist[1:]:
        min_val = z3_If(val < min_val, val, min_val)
    return min_val

def MaxVal(varlist):
    """Given a numeric varlist, returns the variable with maximum value."""
    max_val = varlist[0]
    for val in varlist[1:]:
        max_val = z3_If(val > max_val, val, max_val)
    return max_val