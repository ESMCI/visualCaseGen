#!/usr/bin/env python3

import time
import pytest
import os
from pathlib import Path

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


# do not show logger output
import logging
logger = logging.getLogger()
logger.setLevel(logging.CRITICAL)

temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'temp'))

def test_custom_compset_configuration():
    ConfigVar.reboot()
    Stage.reboot()
    cime = CIME_interface()
    initialize_configvars(cime)
    initialize_widgets(cime) 
    initialize_stages(cime) 
    set_options(cime)
    csp.initialize(cvars, get_relational_constraints(cvars), Stage.first())

    start = time.time()
    configure_standard_compset(cime)
    configure_custom_clm_grid(cime)
    elapsed = time.time() - start

    # Ensure that the elapsed time does not grow too much with each iteration
    print(f"Elapsed time: {elapsed:.3f}")

def configure_standard_compset(cime):
    # At initialization, the first stage should be enabled
    assert Stage.first().enabled
    cvars['COMPSET_MODE'].value = 'Standard'

    # CCOMPSET_MODE is the only variable in the first stage, so assigning a value to it should disable the first stage
    assert not Stage.first().enabled
    
    # The next stge is Custom Component Set, whose first child is Model Time Period
    assert Stage.active().title.startswith('Support Level')
    cvars['SUPPORT_LEVEL'].value = 'All'

    # Apply filters
    for comp_class in cime.comp_classes:
        cvars[f"COMP_{comp_class}_FILTER"].value = "any"

    ## Pick a standard compset
    cvars['COMPSET_ALIAS'].value = "F2000climo"

def configure_custom_clm_grid(cime):

    assert Stage.active().title.startswith('2. Grid')
    cvars['GRID_MODE'].value = 'Custom'

    # custom grid path
    assert Stage.active().title.startswith('Custom Grid Generator')
    custom_grid_path = Path(temp_dir) / "custom_grid_b"
    cvars['CUSTOM_GRID_PATH'].value = str(custom_grid_path)

    
def revert_to_first_stage():
    # Revert back to the first stage
    while Stage.active() != Stage.first():
        Stage.active().revert()
    
    # Reset the first stage
    assert Stage.first().enabled
    Stage.first().reset()


if __name__ == "__main__":
    test_custom_compset_configuration()
    print("All tests passed!")