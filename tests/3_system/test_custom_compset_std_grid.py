#!/usr/bin/env python3

import pytest
import shutil
import os
from pathlib import Path
import tempfile
import time

from ProConPy.config_var import ConfigVar, cvars
from ProConPy.stage import Stage
from ProConPy.csp_solver import csp
from visualCaseGen.cime_interface import CIME_interface
from visualCaseGen.initialize_configvars import initialize_configvars
from visualCaseGen.initialize_widgets import initialize_widgets
from visualCaseGen.initialize_stages import initialize_stages
from visualCaseGen.specs.options import set_options
from visualCaseGen.specs.relational_constraints import get_relational_constraints
from visualCaseGen.custom_widget_types.mom6_bathy_launcher import MOM6BathyLauncher
from visualCaseGen.custom_widget_types.case_creator_widget import CaseCreatorWidget
from tests.utils import safe_create_case


# do not show logger output
import logging

logger = logging.getLogger()
logger.setLevel(logging.CRITICAL)

base_temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "temp"))


def test_custom_compset_std_grid():
    """Configure a custom compset with a standard grid: 2000_DATM%JRA_SLND_CICE%PRES_MOM6_SROF_SGLC_WW3. Progress through the stages
    until the launch stage is reached."""

    ConfigVar.reboot()
    Stage.reboot()
    cime = CIME_interface()
    initialize_configvars(cime)
    initialize_widgets(cime)
    initialize_stages(cime)
    set_options(cime)
    csp.initialize(cvars, get_relational_constraints(cvars), Stage.first())

    # At initialization, the first stage should be enabled
    assert Stage.first().enabled
    cvars['COMPSET_MODE'].value = 'Custom'

    # CCOMPSET_MODE is the only variable in the first stage, so assigning a value to it should disable the first stage
    assert not Stage.first().enabled
    
    # The next stge is Custom Component Set, whose first child is Model Time Period
    assert Stage.active().title.startswith('Time Period')
    cvars['INITTIME'].value = '1850'

    cvars['COMP_OCN'].value = "mom"
    cvars['COMP_ICE'].value = "sice"
    cvars['COMP_ATM'].value = "cam"
    cvars['COMP_ROF'].value = "mosart"
    cvars['COMP_LND'].value = "clm"
    cvars['COMP_WAV'].value = "swav"
    cvars['COMP_GLC'].value = "sglc"


    assert Stage.active().title.startswith('Component Physics')

    cvars['COMP_ATM_PHYS'].value = "CAM60"
    cvars['COMP_LND_PHYS'].value = "CLM60"

    assert Stage.active().title.startswith('Component Options')

    cvars['COMP_ATM_OPTION'].value = "1PCT"
    cvars['COMP_LND_OPTION'].value = "BGC"
    cvars['COMP_OCN_OPTION'].value = "(none)"
    cvars['COMP_ICE_OPTION'].value = "(none)"
    cvars['COMP_ROF_OPTION'].value = "(none)"

    assert Stage.active().title.startswith('2. Grid')

    cvars['GRID_MODE'].value = 'Standard'
    cvars['GRID'].value = 'f09_t232'

    assert Stage.active().title.startswith('3. Launch')
    launch_stage = Stage.active()

    with tempfile.TemporaryDirectory(dir=base_temp_dir) as temp_case_path:
        pass    # immediately remove the random temporary directory,
                # which will become the caseroot directory below

    cvars["CASEROOT"].value = temp_case_path

    case_creator = launch_stage._widget._main_body.children[-1]
    assert isinstance(case_creator, CaseCreatorWidget)

    cvars["PROJECT"].value = "12345"

    # *Click* the create_case button
    safe_create_case(cime.srcroot, case_creator)
    
    # sleep for a bit to allow the case to be created
    time.sleep(5)
            
    # remove the caseroot directory
    shutil.rmtree(temp_case_path)


