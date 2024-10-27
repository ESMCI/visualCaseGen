#!/usr/bin/env python3

import time
import pytest

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

def test_custom_compset_configuration():
    ConfigVar.reboot()
    Stage.reboot()
    cime = CIME_interface()
    initialize_configvars(cime)
    initialize_widgets(cime) 
    initialize_stages(cime) 
    set_options(cime)
    csp.initialize(cvars, get_relational_constraints(cvars), Stage.first())

    min_elapsed = 1e6
    for i in range(3):
        # Configure a custom compset
        start = time.time()
        configure_standard_compset(cime)
        elapsed = time.time() - start

        # Ensure that the elapsed time does not grow too much with each iteration
        print(f"Elapsed time: {elapsed:.3f}")
        assert elapsed < 1.5 * min_elapsed, f"Elapsed time {elapsed} exceeds 1.5 * min_elapsed {1.5 * min_elapsed}"
        min_elapsed = min(min_elapsed, elapsed)

        # Revert back to the first stage
        revert_to_first_stage()

def configure_standard_compset(cime):
    # At initialization, the first stage should be enabled
    assert Stage.first().enabled
    cvars['COMPSET_MODE'].value = 'Standard'
    assert not Stage.first().enabled
    
    ## ATTEMPT 1/3: Pick a standard compset
    # The next stage is Custom Component Set, whose first child is Model Time Period
    assert Stage.active().title.startswith('Support Level')
    cvars['SUPPORT_LEVEL'].value = 'All'

    # Apply filters
    for comp_class in cime.comp_classes:
        cvars[f"COMP_{comp_class}_FILTER"].value = "any"

    ## Pick a standard compset
    cvars['COMPSET_ALIAS'].value = "BLT1850"

    # Generate standard grids list (but don't select any yet)
    cvars['GRID_MODE'].value = 'Standard'

    ## ATTEMPT 2/3: Change of mind, revert and pick a supported compset
    Stage.active().revert()
    assert Stage.active().title.startswith('2. Grid')
    Stage.active().revert()
    assert Stage.active().title.startswith('Standard Compsets')
    Stage.active().revert()
    assert Stage.active().title.startswith('Models to Include')
    Stage.active().revert()
    assert Stage.active().title.startswith('Support Level')

    cvars['SUPPORT_LEVEL'].value = 'Supported'
    cvars['COMPSET_ALIAS'].value = "F2000climo"
    # Check if COMPSET_LNAME is set accordingly:
    assert cvars['COMPSET_LNAME'].value == '2000_CAM60_CLM50%SP_CICE%PRES_DOCN%DOM_MOSART_SGLC_SWAV'

    # Generate standard grids list (but don't select any yet)
    cvars['GRID_MODE'].value = 'Standard'

    ## ATTEMPT 3/3: Change of mind again, revert and pick a supported compset
    Stage.active().revert()
    assert Stage.active().title.startswith('2. Grid')
    Stage.active().revert()
    assert Stage.active().title.startswith('Supported compsets')
    Stage.active().revert()
    assert Stage.active().title.startswith('Support Level')

    cvars['SUPPORT_LEVEL'].value = 'All'
    cvars['COMP_ATM_FILTER'].value = 'cam'
    cvars['COMP_LND_FILTER'].value = 'clm'
    Stage.active().set_vars_to_defaults() # Set all remaining filters to 'any'
    cvars['COMPSET_ALIAS'].value = "FW1850"

    ## Generate standard grids list (but don't select any yet)
    cvars['GRID_MODE'].value = 'Standard'
    
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