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
from visualCaseGen.custom_widget_types.mom6_bathy_launcher import MOM6BathyLauncher
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

def construct_standard_f2000_compset(cime):
    """This auxiliary function initializes the system constructs a standard F2000climo compset."""

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
    cvars["COMPSET_ALIAS"].value = "F2000climo"

def construct_custom_f2000_compset():
    """This auxiliary function initializes the system constructs a custom F2000 compset."""

    assert os.path.exists(base_temp_dir), "temp testing directory does not exist"

    # At initialization, the first stage should be enabled
    assert Stage.first().enabled
    cvars["COMPSET_MODE"].value = "Custom"

    assert Stage.active().title.startswith("Time Period")
    cvars["INITTIME"].value = "2000"

    assert Stage.active().title.startswith("Components")
    cvars["COMP_ATM"].value = "cam"
    cvars["COMP_LND"].value = "clm"
    cvars["COMP_ICE"].value = "cice"
    cvars["COMP_OCN"].value = "docn"
    cvars["COMP_ROF"].value = "mosart"
    cvars["COMP_GLC"].value = "cism"
    cvars["COMP_WAV"].value = "swav"

    assert Stage.active().title.startswith("Component Physics")
    cvars["COMP_ATM_PHYS"].value = "CAM60"
    cvars["COMP_LND_PHYS"].value = "CLM50"
    cvars["COMP_GLC_PHYS"].value = "CISM2"

    assert Stage.active().title.startswith("Component Options")
    cvars["COMP_ATM_OPTION"].value = "(none)"
    cvars["COMP_LND_OPTION"].value = "SP"
    cvars["COMP_ICE_OPTION"].value = "PRES"
    cvars["COMP_OCN_OPTION"].value = "DOM"
    cvars["COMP_ROF_OPTION"].value = "(none)"
    cvars["COMP_GLC_OPTION"].value = "NOEVOLVE"

def construct_standard_blt1850(cime):
    """Construct a standard BLT1850 case."""
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
            cvars[f"COMP_{comp_class}_FILTER"].value = "mom"
        else:
            cvars[f"COMP_{comp_class}_FILTER"].value = "any"

    ## Pick a standard compset
    cvars["COMPSET_ALIAS"].value = "BLT1850"


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

        cvars["PROJECT"].value = "12345"

        # *Click* the create_case button
        safe_create_case(cime.srcroot, case_creator)
        
        # sleep for a bit to allow the case to be created
        time.sleep(9)
        
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

        cvars["PROJECT"].value = "12345"

        # *Click* the create_case button
        safe_create_case(cime.srcroot, case_creator)
        
        # sleep for a bit to allow the case to be created
        time.sleep(5)
        
        # remove the caseroot directory
        shutil.rmtree(temp_case_path)

def construct_custom_res_from_new_mom6_grid_modified_clm_grid(cime):
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

        assert Stage.active().title.startswith("Ocean Grid Mode")
        cvars["OCN_GRID_MODE"].value = "Create New"

        # Set the custom ocean grid properties
        assert Stage.active().title.startswith("Custom Ocean")
        cvars["OCN_GRID_EXTENT"].value = "Global"
        cvars["OCN_CYCLIC_X"].value = "True"
        cvars["OCN_NX"].value = 60
        cvars["OCN_NY"].value = 30
        cvars["OCN_LENX"].value = 360.0
        cvars["OCN_LENY"].value = 160.0
        cvars["CUSTOM_OCN_GRID_NAME"].value = "custom_ocn_grid"

        # now launch the mom6_bathy notebook

        mom6_bathy_launcher_widget = Stage.active()._widget._main_body.children[-1]
        assert isinstance(mom6_bathy_launcher_widget, MOM6BathyLauncher)

        # After setting all the required parameters, the launch button should be enabled
        assert mom6_bathy_launcher_widget._btn_launch_mom6_bathy.disabled is False

        # *Click* the launch button
        mom6_bathy_launcher_widget._on_btn_launch_clicked(b=None)

        # The confirm button should be visible:
        assert (
            mom6_bathy_launcher_widget._btn_confirm_completion.layout.display != "none"
        )

        # now, programmatically run the notebook
        import nbformat
        from nbconvert.preprocessors import ExecutePreprocessor, CellExecutionError

        # find the only mom6_bathy_*.ipynb file in the mom6_bathy_notebooks directory
        ocn_grid_name = cvars['CUSTOM_OCN_GRID_NAME'].value
        nb_files = list(Path("mom6_bathy_notebooks").glob(f"mom6_bathy_{ocn_grid_name}*.ipynb"))
        assert len(nb_files) == 1, "Expected only one mom6_bathy notebook file"
        nb_path = nb_files[0]

        with open(nb_path, "r") as f:
            nb = nbformat.read(f, as_version=4)
            ep = ExecutePreprocessor(timeout=600, kernel_name="python3")
            try:
                ep.preprocess(nb, {"metadata": {"path": str(nb_path.parent)}})
            except CellExecutionError:
                msg = f"Error executing the notebook {nb_path}"
                print(msg)
                raise

        # confirm completion:
        Stage.active()._proceed()

        assert Stage.active().title.startswith("Land Grid Mode")
        cvars["LND_GRID_MODE"].value = "Modified"

        assert Stage.active().title.startswith("Base Land Grid")
        cvars["CUSTOM_LND_GRID"].value = "4x5"

        assert Stage.active().title.startswith("fsurdat")
        assert cvars["INPUT_FSURDAT"].value is not None, "INPUT_FSURDAT should be auto-filled"
        cvars["FSURDAT_AREA_SPEC"].value = "mask_file:/glade/work/altuntas/cesm.input/vcg/mask_fillIO_f45.nc"
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

        cvars["PROJECT"].value = "12345"

        # *Click* the create_case button
        safe_create_case(cime.srcroot, case_creator)
        
        # sleep for a bit to allow the case to be created
        time.sleep(5)
                
        # remove mom6_bathy notebook belonging to the test_grid:
        os.remove(nb_path)
        
        # remove the caseroot directory
        shutil.rmtree(temp_case_path)


def test_std_f2000_custom_res_standard_comp_grid():
    """Test the standard F2000climo compset with a custom resolution consisting of
    standard comp grids: f09"""

    cime = initialize_vcg()
    construct_standard_f2000_compset(cime)
    construct_custom_res_from_std_grids(cime)

@pytest.mark.slow
def test_std_f2000_modified_clm_grid():
    """Test the standard F2000climo compset with a custom resolution based on 4x5 but
    including modified land mask and fsurdat datasets."""

    cime = initialize_vcg()
    machine = cime.machine
    if machine not in ["derecho", "casper"]:
        pytest.skip("This test is only for the derecho and casper machines")

    construct_standard_f2000_compset(cime)
    construct_custom_res_from_modified_clm_grid(cime)

@pytest.mark.slow
def test_custom_f2000_modified_clm_grid():
    """Test custom F2000climo compset with a custom resolution including based on 4x5 but
    including modified land mask and fsurdat datasets."""

    cime = initialize_vcg()
    machine = cime.machine
    if machine not in ["derecho", "casper"]:
        pytest.skip("This test is only for the derecho and casper machines")

    construct_custom_f2000_compset()
    construct_custom_res_from_modified_clm_grid(cime)

@pytest.mark.slow
def test_custom_f2000_new_mom6_grid_modified_clm_grid():
    """Test custom F2000climo compset with a custom resolution including a new MOM6 grid
    and 4x5-based modified land mask and fsurdat datasets."""

    cime = initialize_vcg()
    machine = cime.machine
    if machine not in ["derecho", "casper"]:
        pytest.skip("This test is only for the derecho and casper machines")

    construct_standard_blt1850(cime)
    construct_custom_res_from_new_mom6_grid_modified_clm_grid(cime)

if __name__ == "__main__":
    test_std_f2000_custom_res_standard_comp_grid()
    test_std_f2000_modified_clm_grid()
    test_custom_f2000_modified_clm_grid()
    test_custom_f2000_new_mom6_grid_modified_clm_grid()
    print("All tests passed!")
