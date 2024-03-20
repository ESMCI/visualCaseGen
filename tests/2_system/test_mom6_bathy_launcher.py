#!/usr/bin/env python3

import pytest
import shutil
import os
from pathlib import Path

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


# do not show logger output
import logging
logger = logging.getLogger()
logger.setLevel(logging.CRITICAL)

temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'temp'))

def test_mom6_bathy_launcher():
    ConfigVar.reboot()
    Stage.reboot()
    cime = CIME_interface()
    initialize_configvars(cime)
    initialize_widgets(cime) 
    initialize_stages(cime) 
    set_options(cime)
    csp.initialize(cvars, get_relational_constraints(cvars), Stage.first())

    assert os.path.exists(temp_dir), "temp testing directory does not exist"

    # At initialization, the first stage should be enabled
    assert Stage.first().enabled
    cvars['COMPSET_MODE'].value = 'Standard'

    # COMPSET_MODE is the only variable in the first stage, so assigning a value to it should disable the first stage
    assert not Stage.first().enabled
    
    # The next stage is Custom Component Set, whose first child is Model Time Period
    assert Stage.active().title.startswith('Support Level')
    cvars['SUPPORT_LEVEL'].value = 'All'

    # Apply filters
    for comp_class in cime.comp_classes:
        cvars[f"COMP_{comp_class}_FILTER"].value = "any"

    ## Pick a standard compset
    cvars['COMPSET_ALIAS'].value = "GMOM_JRA"

    # Create a custom grid
    assert Stage.active().title.startswith('2. Grid')
    cvars['GRID_MODE'].value = "Custom"

    # Set the custom grid path
    assert Stage.active().title.startswith('Custom Grid')
    custom_grid_path = Path(temp_dir) / "custom_grid"

    cvars['CUSTOM_GRID_PATH'].value = str(custom_grid_path)

    # since this is a JRA run, the atmosphere grid must automatically be set to TL319
    assert cvars['CUSTOM_ATM_GRID'].value == "TL319"

    # Set the custom ocean grid mode
    assert Stage.active().title.startswith('Ocean')
    cvars['OCN_GRID_MODE'].value = "Create New"

    # Set the custom ocean grid properties
    assert Stage.active().title.startswith('Custom Ocean')
    cvars['OCN_GRID_EXTENT'].value = "Global"
    cvars['OCN_CYCLIC_X'].value = "Yes"
    cvars['OCN_NX'].value = 180
    cvars['OCN_NY'].value = 80
    cvars['OCN_LENX'].value = 360.0
    cvars['OCN_LENY'].value = 160.0
    cvars['CUSTOM_OCN_GRID_NAME'].value = "test_grid"

    # remove all old mom6_bathy *ipynb files in custom_grid_path:
    for file in (custom_grid_path/'ocn').glob("*.ipynb"):
        os.remove(file)

    # now launch the mom6_bathy notebook
    nb_path = Path("mom6_bathy_notebooks") / f"mom6_bathy_{cvars['CUSTOM_OCN_GRID_NAME'].value}.ipynb"
    mom6_bathy_launcher_widget = MOM6BathyLauncher()

    # After setting all the required parameters, the launch button should be enabled
    assert mom6_bathy_launcher_widget._btn_launch_mom6_bathy.disabled is False

    # *Click* the launch button
    mom6_bathy_launcher_widget._on_btn_launch_clicked(b=None)
    
    # The confirm button should be visible:
    assert mom6_bathy_launcher_widget._btn_confirm_completion.layout.display != 'none'

    # *Click* the confirm button
    mom6_bathy_launcher_widget._on_btn_confirm_completion_clicked(b=None)

    # Since the notebook wasn't fully executed, we should remain in the same stage
    assert Stage.active().title.startswith('Custom Ocean')

    # remove mom6_bathy notebook belonging to the test_grid:
    os.remove(nb_path)



if __name__ == "__main__":
    test_mom6_bathy_launcher()
    print("All tests passed!")
