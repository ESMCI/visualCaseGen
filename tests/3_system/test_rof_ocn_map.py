#!/usr/bin/env python3

import pytest
import os
import tempfile

from ProConPy.config_var import ConfigVar, cvars
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

base_temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "temp"))

def configure_for_rof_map(compset_alias):
    """This function configures a standard compset with custom grids suitable for testing
    the runoff to ocean mapping generator."""

    ConfigVar.reboot()
    Stage.reboot()
    cime = CIME_interface()
    initialize_configvars(cime)
    initialize_widgets(cime)
    initialize_stages(cime)
    set_options(cime)
    csp.initialize(cvars, get_relational_constraints(cvars), Stage.first())

    assert os.path.exists(base_temp_dir), "temp testing directory does not exist"

    # At initialization, the first stage should be enabled
    assert Stage.first().enabled
    cvars["COMPSET_MODE"].value = "Standard"

    # COMPSET_MODE is the only variable in the first stage, so assigning a value to it should disable the first stage
    assert not Stage.first().enabled

    # The next stage is Custom Component Set, whose first child is Model Time Period
    assert Stage.active().title.startswith("Support Level")
    cvars["SUPPORT_LEVEL"].value = "All"

    # Apply filters
    for comp_class in cime.comp_classes:
        cvars[f"COMP_{comp_class}_FILTER"].value = "any"

    ## Pick a standard compset
    cvars["COMPSET_ALIAS"].value = compset_alias

    # Create a custom grid
    assert Stage.active().title.startswith("2. Grid")
    cvars["GRID_MODE"].value = "Custom"

    # Set the custom grid path
    assert Stage.active().title.startswith("Custom Grid")

def test_standard_rof_to_ocn_mapping():
    """This test configures a case with a standard runoff to ocean mapping for a custom resolution"""

    configure_for_rof_map("C_JRA")

    assert Stage.active().title.startswith("Custom Grid")

    with tempfile.TemporaryDirectory(dir=base_temp_dir) as temp_grid_path:

        cvars["CUSTOM_GRID_PATH"].value = temp_grid_path
        # since this is a JRA run, the atmosphere grid must automatically be set to TL319
        assert cvars["CUSTOM_ATM_GRID"].value == "TL319"

        # Set the custom ocean grid mode
        assert Stage.active().title.startswith("Ocean")
        cvars["OCN_GRID_MODE"].value = "Standard"

        assert Stage.active().title.startswith("Ocean Grid")
        cvars["CUSTOM_OCN_GRID"].value = "tx2_3v2"

        # Land Grid and Runoff grid should be set automatically
        assert Stage.active().title.startswith("Runoff to Ocean Mapping")

        # Currently, smoothing parameters should be unset
        assert cvars["ROF_OCN_MAPPING_RMAX"].value is None, "ROF_OCN_MAPPING_RMAX should be None"
        assert cvars["ROF_OCN_MAPPING_FOLD"].value is None, "ROF_OCN_MAPPING_FOLD should be None"

        # *Click* "Use Standard Map" button
        runoffMappingGenerator = Stage.active()._widget._supplementary_widgets[0]
        runoffMappingGenerator._btn_use_standard.click()

        map_status = cvars["ROF_OCN_MAPPING_STATUS"].value
        assert map_status == "Standard", f"ROF_OCN_MAPPING_STATUS should be 'Standard', but got: {map_status}"

        # revert stage
        assert Stage.active().title.startswith("3. Launch")
        Stage.active().revert()
        assert Stage.active().title.startswith("Runoff to Ocean Mapping")

# WARNING: for this test to run successfully, MPI must be available. As such, this test
# cannot be run through the derecho login nodes.
@pytest.mark.slow
def test_custom_rof_to_ocn_mapping():
    """This test configures a case with a custom runoff to ocean mapping for a custom resolution"""

    configure_for_rof_map('C_IAF')

    assert Stage.active().title.startswith("Custom Grid")

    with tempfile.TemporaryDirectory(dir=base_temp_dir) as temp_grid_path:

        cvars["CUSTOM_GRID_PATH"].value = temp_grid_path
        # since this is a JRA run, the atmosphere grid must automatically be set to TL319
        assert cvars["CUSTOM_ATM_GRID"].value == "T62"

        # Set the custom ocean grid mode
        assert Stage.active().title.startswith("Ocean")
        cvars["OCN_GRID_MODE"].value = "Standard"

        assert Stage.active().title.startswith("Ocean Grid")
        cvars["CUSTOM_OCN_GRID"].value = "tx2_3v2"

        # Land Grid and Runoff grid should be set automatically
        assert Stage.active().title.startswith("Runoff to Ocean Mapping")

        # Currently, smoothing parameters should be unset
        assert cvars["ROF_OCN_MAPPING_RMAX"].value is None, "ROF_OCN_MAPPING_RMAX should be None"
        assert cvars["ROF_OCN_MAPPING_FOLD"].value is None, "ROF_OCN_MAPPING_FOLD should be None"

        # *Click* the Generate New Map button
        runoffMappingGenerator = Stage.active()._widget._supplementary_widgets[0]
        runoffMappingGenerator._btn_generate_new.click()

        # After clicking the button, the smoothing parameters should be set to suggested values
        assert cvars["ROF_OCN_MAPPING_RMAX"].value is not None, "ROF_OCN_MAPPING_RMAX should have been set to a suggested value"
        assert cvars["ROF_OCN_MAPPING_FOLD"].value is not None, "ROF_OCN_MAPPING_FOLD should have been set to a suggested value"

        # *Click* the Run mapping generator button
        runoffMappingGenerator._btn_run_generate.click()

        map_status = cvars["ROF_OCN_MAPPING_STATUS"].value
        assert map_status.startswith("CUSTOM:"), f"ROF_OCN_MAPPING_STATUS should indicate a custom mapping, but got: {map_status}"
        map_paths = map_status.split("CUSTOM:")[1]
        nn_map_path, nnsm_map_path = map_paths.split(",")

        # check if the mapping file was actually created
        assert os.path.isfile(nn_map_path), f"Nearest neighbor map file was not created at {nn_map_path}"
        assert os.path.isfile(nnsm_map_path), f"Smoothed map file was not created at {nnsm_map_path}"

        assert Stage.active().title.startswith("3. Launch")

if __name__ == "__main__":
    test_standard_rof_to_ocn_mapping()
    test_custom_rof_to_ocn_mapping()
    print("All tests passed!")
