""" This module includes some logical operator and type definitions to be used to specify relational assertions."""

from z3 import Or
from collections import namedtuple

# The When clause used to specify conditional assertions
When = namedtuple("When", "antecedent consequent")

def In(var, value_list):
    """Expression to check whether the value of a variable is in a given list."""
    return Or([var==value for value in value_list])
