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
from visualCaseGen.custom_widget_types.clm_modifier_launcher import MeshMaskModifierLauncher, FsurdatModifierLauncher
from visualCaseGen.custom_widget_types.case_creator import CaseCreator
from tests.utils import safe_create_case


# do not show logger output
import logging

logger = logging.getLogger()
logger.setLevel(logging.CRITICAL)

base_temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "temp"))


def initialize_vcg():
    """This auxiliary function initializes the system and returns a CIME_interface object."""

    ConfigVar.reboot()
    Stage.reboot()
    cime = CIME_interface()
    initialize_configvars(cime)
    initialize_widgets(cime)
    initialize_stages(cime)
    set_options(cime)
    csp.initialize(cvars, get_relational_constraints(cvars), Stage.first())
    return cime

def construct_standard_fhist_compset(cime):
    """This auxiliary function initializes the system constructs a standard FHIST compset."""

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
        if comp_class == "LND":
            cvars[f"COMP_{comp_class}_FILTER"].value = "clm"
        elif comp_class == "OCN":
            cvars[f"COMP_{comp_class}_FILTER"].value = "docn"
        else:
            cvars[f"COMP_{comp_class}_FILTER"].value = "any"

    ## Pick a standard compset
    cvars["COMPSET_ALIAS"].value = "FHIST"

def construct_custom_fhist_compset():
    """This auxiliary function initializes the system constructs a custom FHIST compset."""

    assert os.path.exists(base_temp_dir), "temp testing directory does not exist"

    # At initialization, the first stage should be enabled
    assert Stage.first().enabled
    cvars["COMPSET_MODE"].value = "Custom"

    assert Stage.active().title.startswith("Time Period")
    cvars["INITTIME"].value = "HIST"

    assert Stage.active().title.startswith("Components")
    cvars["COMP_ATM"].value = "cam"
    cvars["COMP_LND"].value = "clm"
    cvars["COMP_ICE"].value = "cice"
    cvars["COMP_OCN"].value = "docn"
    cvars["COMP_ROF"].value = "mosart"
    cvars["COMP_GLC"].value = "sglc"
    cvars["COMP_WAV"].value = "swav"

    assert Stage.active().title.startswith("Component Physics")
    cvars["COMP_ATM_PHYS"].value = "CAM60"
    cvars["COMP_LND_PHYS"].value = "CLM50"

    assert Stage.active().title.startswith("Component Options")
    cvars["COMP_ATM_OPTION"].value = "(none)"
    cvars["COMP_LND_OPTION"].value = "SP"
    cvars["COMP_ICE_OPTION"].value = "PRES"
    cvars["COMP_OCN_OPTION"].value = "DOM"
    cvars["COMP_ROF_OPTION"].value = "(none)"


def construct_custom_res_from_std_grids(cime):
    """This auxiliary function constructs a custom resolution from standard comp grids: 
    atm: f09, lnd: f09, ocn: f09 """

    # Create a custom grid
    assert Stage.active().title.startswith("2. Grid")
    cvars["GRID_MODE"].value = "Custom"

    # Set the custom grid path
    assert Stage.active().title.startswith("Custom Grid")

    with tempfile.TemporaryDirectory(dir=base_temp_dir) as temp_grid_path:

        cvars["CUSTOM_GRID_PATH"].value = temp_grid_path

        # Set CAM grid
        cvars["CUSTOM_ATM_GRID"].value = "0.9x1.25"

        # Since the ocean component is DOCN, we should directly skip to the land grid stage
        assert Stage.active().title.startswith("Land Grid Mode")
        cvars["LND_GRID_MODE"].value = "Standard"

        assert Stage.active().title.startswith("Land Grid")
        cvars["CUSTOM_LND_GRID"].value = "0.9x1.25"

        assert Stage.active().title.startswith("3. Launch")
        launch_stage = Stage.active()

        with tempfile.TemporaryDirectory(dir=base_temp_dir) as temp_case_path:
            pass    # immediately remove the random temporary directory,
                    # which will become the caseroot directory below

        cvars["CASEROOT"].value = temp_case_path

        case_creator = launch_stage._widget._main_body.children[-1]
        assert isinstance(case_creator, CaseCreator)

        case_creator._txt_project.value = "12345"

        # *Click* the create_case button
        safe_create_case(cime.srcroot, case_creator)
        
        # sleep for a bit to allow the case to be created
        time.sleep(15)
        
        # remove the caseroot directory
        shutil.rmtree(temp_case_path)


def construct_custom_res_from_modified_clm_grid(cime):
    """This auxiliary function constructs a custom resolution from 4x5 com grids but
    with modified lnd mask and fsurdat datasets"""

    # Create a custom grid
    assert Stage.active().title.startswith("2. Grid")
    cvars["GRID_MODE"].value = "Custom"

    # Set the custom grid path
    assert Stage.active().title.startswith("Custom Grid")

    with tempfile.TemporaryDirectory(dir=base_temp_dir) as temp_grid_path:

        cvars["CUSTOM_GRID_PATH"].value = temp_grid_path

        # Set CAM grid
        cvars["CUSTOM_ATM_GRID"].value = "4x5"

        # Since the ocean component is DOCN, we should directly skip to the land grid stage
        assert Stage.active().title.startswith("Land Grid Mode")
        cvars["LND_GRID_MODE"].value = "Modified"

        assert Stage.active().title.startswith("Base Land Grid")
        cvars["CUSTOM_LND_GRID"].value = "4x5"

        assert Stage.active().title.startswith("Mesh Mask Modifier")
        assert cvars["INPUT_MASK_MESH"].value is not None, "INPUT_MASK_MESH should be auto-filled"
        cvars["LAND_MASK"].value = "/glade/work/altuntas/cesm.input/vcg/mask_fillIO_f45.nc"
        cvars["LAT_VAR_NAME"].value = "lats"
        cvars["LON_VAR_NAME"].value = "lons"
        cvars["LAT_DIM_NAME"].value = "lsmlat"
        cvars["LON_DIM_NAME"].value = "lsmlon"

        mesh_mask_modifier_launcher = Stage.active()._widget._main_body.children[-1]
        assert isinstance(mesh_mask_modifier_launcher, MeshMaskModifierLauncher)

        # click the "Run Mesh Mask Modifier" button
        mesh_mask_modifier_launcher._on_launch_clicked(b=None)

        assert Stage.active().title.startswith("fsurdat")
        assert cvars["INPUT_FSURDAT"].value is not None, "INPUT_FSURDAT should be auto-filled"
        assert cvars["FSURDAT_AREA_SPEC"].value.startswith("mask_file:"), "FSURDAT_AREA_SPEC should be auto-filled"
        cvars["FSURDAT_IDEALIZED"].value = "True"
        cvars["LND_DOM_PFT"].value = 14
        cvars["LND_SOIL_COLOR"].value = 10
        cvars["LND_STD_ELEV"].value = 0.0
        cvars["LND_MAX_SAT_AREA"].value = 0.0
        cvars["LND_INCLUDE_NONVEG"].value = "True"
        assert cvars["FSURDAT_MATRIX"]._widget.value is not None, "FSURDAT_MATRIX should be auto-filled"

        fsurdat_modifier_launcher = Stage.active()._widget._main_body.children[-1]
        assert isinstance(fsurdat_modifier_launcher, FsurdatModifierLauncher)

        # click the "Run Surface Data Modifier" button
        fsurdat_modifier_launcher._on_launch_clicked(b=None)

        assert Stage.active().title.startswith("3. Launch")
        launch_stage = Stage.active()

        with tempfile.TemporaryDirectory(dir=base_temp_dir) as temp_case_path:
            pass    # immediately remove the random temporary directory,
                    # which will become the caseroot directory below

        cvars["CASEROOT"].value = temp_case_path

        case_creator = launch_stage._widget._main_body.children[-1]
        assert isinstance(case_creator, CaseCreator)

        case_creator._txt_project.value = "12345"

        # *Click* the create_case button
        safe_create_case(cime.srcroot, case_creator)
        
        # sleep for a bit to allow the case to be created
        time.sleep(5)
        
        # remove the caseroot directory
        shutil.rmtree(temp_case_path)

def test_std_fhist_custom_res_standard_comp_grid():
    """Test the standard FHIST compset with a custom resolution consisting of
    standard comp grids: f09"""

    cime = initialize_vcg()
    construct_standard_fhist_compset(cime)
    construct_custom_res_from_std_grids(cime)

@pytest.mark.slow
def test_std_fhist_modified_clm_grid():
    """Test the standard FHIST compset with a custom resolution based on 4x5 but
    including modified land mask and fsurdat datasets."""

    cime = initialize_vcg()
    machine = cime.machine
    if machine not in ["derecho", "casper"]:
        pytest.skip("This test is only for the derecho and casper machines")

    construct_standard_fhist_compset(cime)
    construct_custom_res_from_modified_clm_grid(cime)

@pytest.mark.slow
def test_custom_fhist_modified_clm_grid():
    """Test custom FHIST compset with a custom resolution including based on 4x5 but
    including modified land mask and fsurdat datasets."""

    cime = initialize_vcg()
    machine = cime.machine
    if machine not in ["derecho", "casper"]:
        pytest.skip("This test is only for the derecho and casper machines")

    construct_custom_fhist_compset()
    construct_custom_res_from_modified_clm_grid(cime)

if __name__ == "__main__":
    test_std_fhist_custom_res_standard_comp_grid()
    test_std_fhist_modified_clm_grid()
    test_custom_fhist_modified_clm_grid()
    print("All tests passed!")
