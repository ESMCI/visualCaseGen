from visualCaseGen.config_var import ConfigVar, cvars
from visualCaseGen.config_var_str import ConfigVarStr
from visualCaseGen.config_var_str_ms import ConfigVarStrMS
from visualCaseGen.config_var_compset import ConfigVarCompset
from visualCaseGen.cime_interface import CIME_interface
from visualCaseGen.logic_utils import When
from specs.relational_assertions import relational_assertions_setter
from specs.gen_options_specs import OptionsSpec, gen_options_specs
from z3 import Solver, Implies, sat, unsat

ci = CIME_interface("nuopc")

def init_configvars():

    ConfigVarStr('INITTIME')
    for comp_class in ci.comp_classes:
        ConfigVarStr('COMP_'+str(comp_class))
        ConfigVarStr('COMP_{}_PHYS'.format(comp_class), always_set=True)
        ConfigVarStrMS('COMP_{}_OPTION'.format(comp_class), always_set=True)
        ConfigVarStr('{}_GRID'.format(comp_class))
    ConfigVarCompset("COMPSET", always_set=True)
    ConfigVarStr('MASK_GRID')
    cv_grid = ConfigVarStrMS('GRID')


def main():
    print("Running visualCaseGen static check")
    init_configvars()

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
    gen_options_specs(cvars, ci)
    for varname, var in cvars.items():
        if hasattr(var, 'options_spec'):
            assertions = OptionsSpec.get_options_assertions(var)
            for asrt in assertions:
                s.add(asrt)


    # Check that assertions are satisfiable
    if s.check() == sat:
        print("check 1: assertions satisfiable")
    else:
        raise RuntimeError("Assertions not satisfiable")

    # Check that all options of all variables are part of at least one solution
    for varname, var in cvars.items():
        if hasattr(var, 'options_spec'):
            if isinstance(var.options_spec.opts, tuple):
                for opt in var.options_spec.opts[0]:
                    if s.check(var==opt) == unsat:
                        print("NOT SATISFIABLE:", var, opt)
            if isinstance(var.options_spec.opts, dict):
                for proposition, opts in var.options_spec.opts.items():
                    for opt in opts[0]:
                        if s.check(var==opt) == unsat:
                            print("NOT SATISFIABLE:", var, opt)
    


if __name__ == '__main__':
    main()