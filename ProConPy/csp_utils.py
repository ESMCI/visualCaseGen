""" This module includes some logical operator and type definitions to be used to specify relational constraints."""

from z3 import BoolRef, Or
from z3 import If as z3_If


###todo:remove class While:
###todo:remove     """A When object is a logical clause that is used to specify hierarchical relational assertions,
###todo:remove     where antecedent is the precondition and consequent is the assertion to be checked iff antecedent
###todo:remove     evaulates to True."""
###
###todo:remove     def __init__(self, antecedent, consequent):
###todo:remove         assert isinstance(
###todo:remove             antecedent, BoolRef
###todo:remove         ), "The antecedent of When clause must be of type BoolRef"
###todo:remove         assert isinstance(
###todo:remove             consequent, BoolRef
###todo:remove         ), "The consequent of When clause must be of type BoolRef"
###todo:remove         self.antecedent = antecedent
###todo:remove         self.consequent = consequent
###
###todo:remove     def __getitem__(self, key):
###todo:remove         """Return the antecedent (key==0) or the consequent (key==1)"""
###todo:remove         if key == 0:
###todo:remove             return self.antecedent
###todo:remove         elif key == 1:
###todo:remove             return self.consequent
###todo:remove         else:
###todo:remove             raise IndexError


def In(var, value_list):
    """Expression to check whether the value of a variable is in a given list."""
    return Or([var == value for value in value_list])


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
