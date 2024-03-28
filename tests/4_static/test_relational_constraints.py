import pytest

from z3 import And, Not, Implies, Or, Solver, sat, unsat

from ProConPy.config_var import ConfigVar, cvars
from ProConPy.config_var import cvars
from ProConPy.csp_solver import csp
from ProConPy.stage import Stage

from visualCaseGen.cime_interface import CIME_interface
from visualCaseGen.initialize_configvars import initialize_configvars
from visualCaseGen.initialize_widgets import initialize_widgets
from visualCaseGen.initialize_stages import initialize_stages
from visualCaseGen.specs.options import set_options
from visualCaseGen.specs.relational_constraints import get_relational_constraints


def test_initial_satisfiability():
    """Check that the relational constraints are satisfiable"""
    ConfigVar.reboot()
    Stage.reboot()
    cime = CIME_interface()
    initialize_configvars(cime)
    initialize_widgets(cime) 
    initialize_stages(cime) 
    set_options(cime)
    relational_constraints_dict = get_relational_constraints(cvars)
    csp.initialize(cvars, relational_constraints_dict, Stage.first())

    # check that relational constraints are satisfiable
    s = Solver()
    s.add([k for k in relational_constraints_dict.keys()])
    assert s.check() != unsat, "Relational constraints are not satisfiable."

    # check that initial options are all satisfiable
    for varname, var in cvars.items():
        if var.has_options():
            s.add(Or([var == opt for opt in var.options]))
            assert s.check() != unsat, f"Initial options for {varname} are not satisfiable."
        elif var._options_spec:
            opts = var._options_spec()
            if opts[0] is not None:
                s.add(Or([var == opt for opt in opts]))
                assert s.check() != unsat, f"Initial options_spec for {varname} are not satisfiable."

    # check that all initial options are satisfiable in some combination
    for varname, var in cvars.items():
        opts = []
        if var.has_options():
            opts = var.options
        elif var._options_spec:
            opts = var._options_spec()[0] or []
        for opt in opts:
            assert s.check(var == opt) == sat, f"Initial option {opt} for {varname} is not satisfiable."


def test_constraint_redundancy():
    """Check to see if any of the relational constraints is redundant
    i.e., already implied by the preceding constraints."""

    ConfigVar.reboot()
    Stage.reboot()
    cime = CIME_interface()
    initialize_configvars(cime)
    initialize_widgets(cime) 
    initialize_stages(cime) 
    set_options(cime)
    relational_constraints_dict = get_relational_constraints(cvars)
    csp.initialize(cvars, relational_constraints_dict, Stage.first())

    constraints = [constr for constr, _ in relational_constraints_dict.items()]

    for i in range(1,len(constraints)):
        constraint = constraints[i]
        s = Solver()
        if s.check(Not(Implies(And(constraints[:i]), constraint))) == unsat:
            raise AssertionError(f'Constraint "{constraint}" is redundant.')

def test_err_msg_repetition():
    """Check if any error messages are repeated in the relational constraints."""

    relational_constraints = get_relational_constraints(cvars)

    err_msg_list = [err_msg for _, err_msg in relational_constraints.items()]
    err_msg_set = set(err_msg_list)

    # If any error message is repeated, find out which ones are repeated and raise an AssertionError
    if len(err_msg_list) != len(err_msg_set):
        count = {err_msg: 0 for err_msg in err_msg_set}
        for err_msg in err_msg_list:
            count[err_msg] += 1
        repeated_err_msgs = {err_msg: count[err_msg] for err_msg in err_msg_set if count[err_msg] > 1}
        raise AssertionError(f"Error messages are repeated: {repeated_err_msgs}")


if __name__ == "__main__":
    test_initial_satisfiability()