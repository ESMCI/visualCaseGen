#!/usr/bin/env python3

from visualCaseGen.config_var import ConfigVar, cvars
from visualCaseGen.init_configvars import init_configvars
from visualCaseGen.cime_interface import CIME_interface
from visualCaseGen.logic_utils import When
from specs.relational_assertions import relational_assertions_setter
from specs.options_specs import OptionsSpec, get_options_specs
from z3 import Solver, Implies, sat, unsat

ci = CIME_interface("nuopc")

def main():
    print("Running visualCaseGen static check")
    init_configvars(ci)

    # Static Solver
    s = Solver()

    # Add relational assertions
    relational_assertions_dict = relational_assertions_setter(cvars)
    relational_assertions_list = list(relational_assertions_dict.keys())
    for asrt in relational_assertions_list:
        if isinstance(asrt, When):
            s.add(Implies(asrt.antecedent, asrt.consequent))
        else:
            s.add(asrt)


    # Add options (domain) specifications
    get_options_specs(cvars, ci)
    for varname, var in cvars.items():
        if hasattr(var, 'options_spec'):
            assertions = var.options_spec.get_options_assertions()
            for asrt in assertions:
                s.add(asrt)


    # Check that assertions are satisfiable
    print("check 1: relational and optional assertions satisfiable?...")
    if s.check() == sat:
        print("\tok")
    else:
        raise RuntimeError("Assertions not satisfiable")

    # Check that all options of all variables are part of at least one solution
    print("check 2: All options satisfiable?...")
    all_options_sat = True
    for varname, var in cvars.items():
        if hasattr(var, 'options_spec'):
            options = var.options_spec.get_options()
            for opt in options:
                if s.check(var==opt) == unsat:
                    print("NOT SATISFIABLE:", var, opt)
                    all_options_sat = False
                    break
    if all_options_sat:
        print("\tok")

    


if __name__ == '__main__':
    main()