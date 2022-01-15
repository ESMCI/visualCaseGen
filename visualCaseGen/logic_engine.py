from z3 import String
from z3 import And, Or, Implies
from z3 import Solver, sat, unsat
from z3 import z3util

# assertions keeping track of variable assignments. key is varname, value is assignment assertion
asrt_assignments = {}

# assertions for options lists of variables. key is varname, value is options assertion
asrt_options = {}

# relational assertions. key is ASSERTION, value is ERRNAME.
asrt_relationals = {}

def reset():
    global asrt_assignments, asrt_options, asrt_relationals
    asrt_assignments = {}
    asrt_options = {}
    asrt_relationals = {}


def universal_solver():
    """ Returns a solver instance with all current assertions. """
    s = Solver()
    s.add(list(asrt_assignments.values()))
    s.add(list(asrt_options.values()))
    s.add(list(asrt_relationals.keys()))
    return s

def set_variable_options(var, options):
    """This method is to be called by ConfigVar instance when its options are assigned."""
    asrt_options[var.name] = Or([var==opt for opt in options])

def add_relational_assertions(assertions_setter, cvars):
    new_assertions = assertions_setter(cvars)

    # Check if any assertion has been provided multiple times.
    # If not, update the relational_assertions_dict to include new assertions (simplified).
    for asrt in new_assertions:
        if asrt in asrt_relationals:
            raise ValueError("Versions of assertion encountered multiple times: {}".format(asrt))
    asrt_relationals.update(new_assertions)
    
    # For all ConfigVars in each assertion, add the other ConfigVars as related so
    # that each ConfigVar inform related ConfigVars when a value change occurs.
    for asrt in new_assertions:
        related_cvars = {cvars[var.sexpr()] for var in z3util.get_vars(asrt)}
        for cvar in related_cvars:
            cvar.add_related_vars(related_cvars - {cvar})

    # Check if newly added relational assertions are satisfiable:
    s = Solver()
    s.add(list(asrt_assignments.values()))
    s.add(list(asrt_options.values()))
    s.add(list(asrt_relationals.keys()))
    if s.check() == unsat:
        raise RuntimeError("Relational assertions not satisfiable!")

def _is_sat_assignment(var, value):
    """ This is to be called by add_assignment method only. It checks whether an
    assignment is satisfiable."""

    # first, check if the value is an option of var
    if var.has_options():
        if value not in var.options:
            err_msg = '{} not an option for {}'.format(value, var.name)
            return False, err_msg

    # now, check if the value satisfies all assertions

    # first add all assertions including the assignment being checked but excluding the relational
    # assignments because we will pop the relational assertions if the solver is unsat
    s = Solver()
    s.add(list(asrt_assignments.values()))
    s.add(list(asrt_options.values()))
    s.add(var==value)

    # now push and temporarily add relational assertions
    s.push()
    s.add(list(asrt_relationals.keys()))

    if s.check() == unsat:
        s.pop()
        for asrt in asrt_relationals:
            s.add(asrt)
            if s.check() == unsat:
                err_msg = '{}={} violates assertion:"{}"'.format(var.name,value,asrt_relationals[asrt])
                return False, err_msg

    return True, ''

def get_options_validities(var, options_list):
    n_opts = len(options_list)
    options_validities = {opt:False for opt in options_list}
    error_messages = {opt:'' for opt in options_list}

    s = Solver()
    s.add([asrt_assignments[varname] for varname in asrt_assignments if varname != var.name])
    s.add(list(asrt_options.values()))

    for opt in options_list:
        s.push() # push for relational assignments to be added fully
        s.add(list(asrt_relationals.keys()))
        if s.check(var==opt) == sat:
            options_validities[opt] = True
        else: # unsat
            options_validities[opt] = False
            # now find the assertion causing unsat and get the associated error message
            s.pop() # pop all relational assignments
            s.push() # push for relational assignments to be added incrementally
            for asrt in asrt_relationals:
                s.add(asrt)
                if s.check(var==opt) == unsat:
                    error_messages[opt] = '{}={} violates assertion:"{}"'.format(var.name,opt,asrt_relationals[asrt])
                    break
        s.pop() # pop relational assignments (partially added or full)
    return options_validities, error_messages

def set_null(var):
    """ Removes the assignment assertion of variable, if there is one."""
    if var.name in asrt_assignments:
        asrt_assignments.pop(var.name)

def add_assignment(var, value, check_sat=True):
    """ Adds an assignment to the logic solver. To be called by ConfigVar value setters only."""

    # first pop old assignment if exists:
    old_assignment = asrt_assignments.pop(var.name, None)

    # check if assignment is satisfiable.
    is_ok = True
    if check_sat:
        is_ok, msg = _is_sat_assignment(var, value)

    # add the assignment to the assignments dictionary
    if is_ok == False:
        # reinsert old assignment and raise error
        if old_assignment is not None:
            asrt_assignments[var.name] = old_assignment
        raise AssertionError(msg)
    else:
        # assignment is successful
        asrt_assignments[var.name] = var==value


# Auxiliary definitions of logic expression shorthands
def In(var, value_list):
    """Expression to check whether the value of a variable is in a given list."""
    return Or([var==value for value in value_list])