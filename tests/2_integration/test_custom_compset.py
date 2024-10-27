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
        configure_custom_compset()
        elapsed = time.time() - start

        r = 2.0

        # Ensure that the elapsed time does not grow too much with each iteration
        print(f"Elapsed time: {elapsed:.3f}")
        assert elapsed < r * min_elapsed, f"Elapsed time {elapsed} exceeds {r} * min_elapsed {r * min_elapsed}"
        min_elapsed = min(min_elapsed, elapsed)

        # Revert back to the first stage
        revert_to_first_stage()

def configure_custom_compset():
    """Configure a custom compset: 2000_DATM%JRA_SLND_CICE%PRES_MOM6_SROF_SGLC_WW3. Progress through the stages
    until the standard grid selector stage is reached."""
    # At initialization, the first stage should be enabled
    assert Stage.first().enabled
    cvars['COMPSET_MODE'].value = 'Custom'

    # CCOMPSET_MODE is the only variable in the first stage, so assigning a value to it should disable the first stage
    assert not Stage.first().enabled
    
    # The next stge is Custom Component Set, whose first child is Model Time Period
    assert Stage.active().title.startswith('Time Period')
    cvars['INITTIME'].value = '2000'

    # Set components
    assert Stage.active().title.startswith('Components')
    cvars['COMP_ATM'].value = "datm"
    cvars['COMP_LND'].value = "slnd"
    cvars['COMP_ICE'].value = "cice"
    
    # Meanwhile, attempt to set a value that violates a constraint, and confirm that
    # the value is set back to the previous value after the exception is raised.
    with pytest.raises(ConstraintViolation):
        cvars['COMP_LND'].value = "clm"
    assert cvars['COMP_LND'].value == "slnd"

    cvars['COMP_OCN'].value = "mom"
    cvars['COMP_ROF'].value = "srof"
    cvars['COMP_GLC'].value = "sglc"
    cvars['COMP_WAV'].value = "ww3"

    # All COMP_ variables have been set, so the next stage is Component Physics. However,
    # all the variables in this stage have only a single allowed value, so the Component
    # Physics stage should be automatically completed. The next stage is Component Options.
    assert Stage.active().title.startswith('Component Options')
    cvars['COMP_ATM_OPTION'].value = "JRA"
    cvars['COMP_OCN_OPTION'].value = "(none)"
    cvars['COMP_ICE_OPTION'].value = "PRES"

    # check if COMPSET_LNAME is set to the correct value
    assert cvars['COMPSET_LNAME'].value == "2000_DATM%JRA_SLND_CICE%PRES_MOM6_SROF_SGLC_WW3"

    # The remaining COMP_?_OPTIONS variables have single available options only, so all 
    # COMP_?_OPTIONS variables have been set, so the next stage is Grid:
    assert Stage.active().title.startswith('2. Grid')
    cvars['GRID_MODE'].value = 'Standard'
    assert Stage.active().title.startswith('Standard Grid')

    # change of mind, revert and pick new components
    Stage.active().revert()
    assert Stage.active().title.startswith('2. Grid')
    Stage.active().revert()
    assert Stage.active().title.startswith('Component Options')
    Stage.active().revert()
    assert Stage.active().title.startswith('Component Physics')
    Stage.active().revert()
    assert Stage.active().title.startswith('Components')

    Stage.active().reset()

    cvars['COMP_ATM'].value = "cam"
    with pytest.raises(ConstraintViolation):
        cvars['COMP_LND'].value = "cam" # cam is not a valid value for COMP_LND
    cvars['COMP_LND'].value = "clm"
    cvars['COMP_ROF'].value = "mosart"

    with pytest.raises(ConstraintViolation):
        cvars['COMP_ROF'].value = "drof"
    cvars['COMP_ROF'].value = "mosart"

    with pytest.raises(ConstraintViolation):
        cvars['COMP_LND'].value = "slim"
    assert cvars['COMP_LND'].value == "clm"

    cvars['COMP_OCN'].value = "docn"
    cvars['COMP_ICE'].value = "cice"
    cvars['COMP_GLC'].value = "sglc"
    cvars['COMP_WAV'].value = "dwav"

    # All COMP_ variables have been set, so the next stage is Component Physics
    cvars['COMP_ATM_PHYS'].value = "CAM60"
    cvars['COMP_LND_PHYS'].value = "CLM50"

    # All COMP_?_PHYS variables have been set, so the next stage is Component Options
    cvars['COMP_ATM_OPTION'].value = "(none)"
    with pytest.raises(ConstraintViolation):
        cvars['COMP_LND_OPTION'].value = "(none)"
    cvars['COMP_LND_OPTION'].value = "SP"
    cvars['COMP_ICE_OPTION'].value = "PRES"
    cvars['COMP_OCN_OPTION'].value = "DOM"
    cvars['COMP_WAV_OPTION'].value = "(none)"
    cvars['COMP_ROF_OPTION'].value = "FLOOD"

    for comp_class in ['ATM', 'LND', 'ICE', 'OCN', 'ROF', 'GLC', 'WAV']:
        if cvars[f"COMP_{comp_class}_OPTION"].value is None:
            print(f"COMP_{comp_class}_OPTION is None")

    assert Stage.active().title.startswith('2. Grid')
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