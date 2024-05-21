"""Module to find combined reasons leading to a violation of constraints in visualCaseGen."""

from ProConPy.config_var import ConfigVar, cvars
from ProConPy.stage import Stage
from ProConPy.dev_utils import ConstraintViolation
from ProConPy.csp_solver import csp
from visualCaseGen.cime_interface import CIME_interface
from visualCaseGen.initialize_configvars import initialize_configvars
from visualCaseGen.initialize_widgets import initialize_widgets
from visualCaseGen.initialize_stages import initialize_stages
from visualCaseGen.specs.options import set_options
from visualCaseGen.specs.relational_constraints import get_relational_constraints

import random


def initialize(cime):
    """Initializes visualCaseGen"""
    ConfigVar.reboot()
    Stage.reboot()
    initialize_configvars(cime)
    initialize_widgets(cime)
    initialize_stages(cime)
    set_options(cime)
    csp.initialize(cvars, get_relational_constraints(cvars), Stage.first())


def set_preliminary_vars():
    """Sets the preliminary variables to move on to the Components stage"""
    cvars["COMPSET_MODE"].value = "Custom"
    cvars["INITTIME"].value = "2000"
    assert Stage.active().title.startswith("Components")


def valid_options(var):
    """Returns the valid options for a ConfigVar"""
    return [opt for opt in var.options if var._options_validities[opt] is True]


def main(ntrial=10, nselect=5, minreason=3):
    """Main function for the script. It generates random component selections and checks for
    combined reasons leading to a violation. If a selection leads to a violation of a minimum
    number of combined reasons (constraints), the selection histoary and the constraints are printed.

    Parameters
    ----------
    ntrial : int
        Number of trials to run
    nselect : int
        Number of selections to make in each trial
    minreason : int
        Minimum number of reasons leading to a violation to print the error message
    """

    cime = CIME_interface()
    initialize(cime)
    set_preliminary_vars()
    comps = [f"COMP_{cc}" for cc in cime.comp_classes]
    comps = [
        "COMP_ATM",
        "COMP_LND",
        "COMP_ICE",
        "COMP_OCN",
        "COMP_ROF",
        "COMP_GLC",
        "COMP_WAV",
    ]
    comps = ["COMP_ATM", "COMP_LND", "COMP_ICE", "COMP_OCN", "COMP_ROF", "COMP_WAV"]

    for i in range(ntrial):
        print(f"Trial {i+1}/{ntrial}")
        Stage.active().reset()
        hist = []
        for s in range(nselect):
            comp = random.choice(comps)
            new_value = random.choice(valid_options(cvars[comp]))
            # remove past assignment if exists:
            hist = [h for h in hist if h[0] != comp]
            hist.append((comp, new_value))
            if cvars[comp].value != new_value:
                cvars[comp].value = new_value

            for comp_other in set(comps) - set([comp]):
                var = cvars[comp_other]
                for option in var.options:
                    if var._options_validities[option] is False:
                        err_msg = csp.retrieve_error_msg(var, option)
                        nreason = (
                            err_msg.count(".") - 1
                        )  # number of reasons leading to the violation
                        if nreason >= minreason:
                            print("------------------------------------------------")
                            print(f"Error message for {var.name} = {option}:")
                            print(err_msg)
                            print(f"Hist: {hist}")


if __name__ == "__main__":
    main()
