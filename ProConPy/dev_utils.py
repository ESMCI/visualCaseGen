"""Module containing development utilities, includin a debug flag that enables runtime checks."""

import cProfile

profiler = cProfile.Profile()

# debug flag, turns on some checks during runtime
DEBUG = True

MODE = "dynamic"  # or "static"


class ProConPyError(Exception):
    """ProConPy Error class that can display the assignment history that led to the error."""

    def __init__(self, message="", csp=None):
        self.message = message
        if csp is not None:
            print(
                "A ProConPy error encountered. Here is the variable assignment that led to the error:"
            )
            for assignment in csp.assignment_history:
                print(assignment)
        super().__init__(self.message)

class ConstraintViolation(Exception):
    """Error that signals a CSP constraint violation."""

    def __init__(self, message=""):
        self.message = message
        super().__init__(self.message)

def is_integer(s):
    """Returns true if the given string s is an integer number."""
    ss = s.strip()
    return ss.isdigit() or (ss[0] == "-" and ss[1:].isdigit())


def is_number(s):
    """Returns true if the given string s is a number."""
    try:
        float(s)
    except ValueError:
        return False
    return True
