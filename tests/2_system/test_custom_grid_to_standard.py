#!/usr/bin/env python3

import time
import pytest

from ProConPy.config_var import ConfigVar, cvars
from ProConPy.config_var import cvars
from ProConPy.stage import Stage
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
    """Select a standard (supported) compset: F2000climo, then set the grid mode to custom, then revert and
    set the grid mode to standard. This test is to ensure that the csp_solver does not fail when a ConfigVar,
    whose dependent variables call back csp_solver to determine options_spec(), gets reset."""
    ConfigVar.reboot()
    Stage.reboot()
    cime = CIME_interface()
    initialize_configvars(cime)
    initialize_widgets(cime) 
    initialize_stages(cime) 
    set_options(cime)
    csp.initialize(cvars, get_relational_constraints(cvars), Stage.first())

    # (1) Configure the standard supported compset

    # At initialization, the first stage should be enabled
    assert Stage.first().enabled
    cvars['COMPSET_MODE'].value = 'Standard'
    cvars['SUPPORT_LEVEL'].value = 'Supported'
    cvars['COMPSET_ALIAS'].value = 'F2000climo'

    #Check that COMP_???_PHYS is auto-set accordingly when COMPSET_ALIAS is set by the user.
    assert cvars['COMP_ATM_PHYS'].value == "CAM60"
    assert cvars['COMP_LND_PHYS'].value == "CLM50"
    assert cvars['COMP_ICE_PHYS'].value == "CICE"
    assert cvars['COMP_OCN_PHYS'].value == "DOCN"
    assert cvars['COMP_ROF_PHYS'].value == "MOSART"
    assert cvars['COMP_GLC_PHYS'].value == "SGLC"
    assert cvars['COMP_WAV_PHYS'].value == "SWAV"
    # Check that COMP_???_OPTIONs are auto-set accordingly when COMPSET_ALIAS is set by the user.
    assert cvars['COMP_ATM_OPTION'].value == None
    assert cvars['COMP_LND_OPTION'].value == "SP"
    assert cvars['COMP_ICE_OPTION'].value == "PRES"
    assert cvars['COMP_OCN_OPTION'].value == "DOM"

    # (2) Configure the grid

    cvars['GRID_MODE'].value = 'Custom'

    # Change of mind, revert and select standard grid
    Stage.active().revert()

    cvars['GRID_MODE'].value = 'Standard'

    # Previously, this execution trace would have failed due to a bug in the csp_solver:
    # A conflict would have occured in _do_check_assignment() that calls _options_spec() methods
    # of dependent vars. Before doing so, the new assignment assertion for the invoking var would
    # be added to the solver without first removing the old assignment assertion
    # from self._assignment_assertions. This would cause the solver to fail to find a solution
    # due to conflicting assignment assertions for the same var. 

if __name__ == "__main__":
    test_custom_compset_configuration()