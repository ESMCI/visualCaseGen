""" This module includes some logical operator and type definitions to be used to specify relational constraints."""

from z3 import BoolRef, Or
from z3 import If as z3_If


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


class TraversalLock:
    """A context manager to prevent recursive traversal of the constraint hypergraph of CSP solver."""

    def __init__(self):
        """Initializes the lock."""
        self._locked = False

    def __enter__(self):
        """Acquires the lock."""
        if self._locked:
            raise RuntimeError("Attempted to acquire a locked TraversalLock.")
        self._locked = True

    def __exit__(self, *args):
        """Releases the lock."""
        if self._locked is False:
            raise RuntimeError("Attempted to release an unlocked TraversalLock.")
        self._locked = False

    def __bool__(self):
        """Returns the current state of the lock."""
        return self._locked
    
    def is_locked(self):
        """Returns the current state of the lock."""
        return self._locked
