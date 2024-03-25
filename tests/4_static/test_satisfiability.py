import pytest

import z3

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
    s = z3.Solver()
    s.add([k for k in relational_constraints_dict.keys()])
    assert s.check() != z3.unsat, "Relational constraints are not satisfiable."

    # check that initial options are all satisfiable
    for varname, var in cvars.items():
        if var.has_options():
            s.add(z3.Or([var == opt for opt in var.options]))
            assert s.check() != z3.unsat, f"Initial options for {varname} are not satisfiable."
        elif var._options_spec:
            opts = var._options_spec()
            if opts[0] is not None:
                s.add(z3.Or([var == opt for opt in opts]))
                assert s.check() != z3.unsat, f"Initial options_spec for {varname} are not satisfiable."

    # check that all initial options are satisfiable in some combination
    for varname, var in cvars.items():
        opts = []
        if var.has_options():
            opts = var.options
        elif var._options_spec:
            opts = var._options_spec()[0] or []
        for opt in opts:
            assert s.check(var == opt) == z3.sat, f"Initial option {opt} for {varname} is not satisfiable."

if __name__ == "__main__":
    test_initial_satisfiability()