from z3 import String
from z3 import And, Or, Implies
from z3 import Solver, sat, unsat

# dictionary of logic variables corresponding to config variables.
# Currently all logic variables are of type z3.String
lvars = {}

# assertions keeping track of variable assignments. key is varname, value is assignment assertion
asrt_assignments = {}

# assertions for options lists of variables. key is varname, value is options assertion
asrt_options = {}

# relational assertions. key is ASSERTION, value is ERRNAME.
asrt_relationals = {}

def add_variable(varname):
    lvars[varname] = String(varname)

def set_variable_options(varname, options):
    """This method is to be called by ConfigVar instance when its options are assigned."""
    asrt_options[varname] = Or([lvars[varname]==opt for opt in options])

def add_relational_assertions(assertions_setter):
    new_assertions = assertions_setter(lvars)

    # Check if any assertion has been provided multiple times.
    # If not, update the relational_assertions_dict to include new assertions (simplified).
    for asrt in new_assertions:
        if asrt in asrt_relationals:
            raise ValueError("Versions of assertion encountered multiple times: {}".format(asrt))
    asrt_relationals.update(new_assertions)

    # Check if newly added relational assertions are satisfiable:
    s = Solver()
    s.add(list(asrt_assignments.values()))
    s.add(list(asrt_options.values()))
    s.add(list(asrt_relationals.keys()))
    if s.check() == unsat:
        raise RuntimeError("Relational assertions not satisfiable!")

def _is_option(varname, value):
    """ Checks if a value is in the list of options of a var."""

    if varname in asrt_options:
        s = Solver()
        s.add(asrt_options[varname])
        return s.check(lvars[varname]==value) == sat
    else:
        return True # the variable has no options defined.

def _check_assignment(varname, value):
    """ This is to be called by add_assignment method only. It checks whether an
    assignment is satisfiable."""

    # first, check if the value is an option of var
    if not _is_option(varname, value):
        raise ValueError("Invalid value for {} = {}".format(varname, value))

    # now, check if the value satisfies all assertions

    # first add all assertions including the assignment being checked but excluding the relational
    # assignments because we will pop the relational assertions if the solver is unsat
    s = Solver()
    s.add(list(asrt_assignments.values()))
    s.add(list(asrt_options.values()))
    s.add(lvars[varname]==value)

    # now push and temporarily add relational assertions
    s.push()
    s.add(list(asrt_relationals.keys()))

    if s.check() == unsat:
        s.pop()
        for asrt in asrt_relationals:
            s.add(asrt)
            if s.check() == unsat:
                raise AssertionError('{}={} violates assertion:"{}"'.
                    format(varname,value,asrt_relationals[asrt]))

    return True

def add_assignment(varname, value):
    """ Adds an assignment to the logic solver. To be called by ConfigVar value setters only."""
    var = lvars[varname]
    if _check_assignment(varname, value):
        asrt_assignments[varname] = var==value

