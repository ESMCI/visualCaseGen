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


def test_custom_mom6_grid():
    """This test configures a case with a custom MOM6 grid using the MOM6BathyLauncher widget
    and attempts to create the CESM case."""

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
    cvars["COMPSET_ALIAS"].value = "G_JRA"

    # Create a custom grid
    assert Stage.active().title.startswith("2. Grid")
    cvars["GRID_MODE"].value = "Custom"

    # Set the custom grid path
    assert Stage.active().title.startswith("Custom Grid")

    with tempfile.TemporaryDirectory(dir=base_temp_dir) as temp_grid_path:

        cvars["CUSTOM_GRID_PATH"].value = temp_grid_path
        # since this is a JRA run, the atmosphere grid must automatically be set to TL319
        assert cvars["CUSTOM_ATM_GRID"].value == "TL319"

        # Set the custom ocean grid mode
        assert Stage.active().title.startswith("Ocean")
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

        # *Click* the confirm button
        mom6_bathy_launcher_widget._on_btn_confirm_completion_clicked(b=None)

        # Since the notebook wasn't fully executed, we should remain in the same stage
        assert Stage.active().title.startswith("Custom Ocean")

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

        assert Stage.active().title.startswith("New Ocean Grid Initial Conditions")
        cvars["OCN_IC_MODE"].value = "Simple"
        
        assert Stage.active().title.startswith("Simple Initial Conditions")
        cvars["T_REF"].value = 10.0

        # Since land grid gets set automatically, we should be in the Launch stage:
        assert Stage.active().title.startswith("3. Launch")
        launch_stage = Stage.active()

        with tempfile.TemporaryDirectory(dir=base_temp_dir) as temp_case_path:
            pass    # immediately remove the random temporary directory,
                    # which will become the caseroot directory below

        cvars["CASEROOT"].value = temp_case_path

        case_creator = launch_stage._widget._main_body.children[-1]
        assert isinstance(case_creator, CaseCreatorWidget)

        cvars["PROJECT"].value = "12345"

        try:
            # *Click* the create_case button
            safe_create_case(cime.srcroot, case_creator)

            # sleep for a bit to allow the case to be created
            time.sleep(15)
        
        except RuntimeError as e:
            if "not ported" in str(e):
                print("CESM is not ported to the current machine. Skipping case creation.")
            else:
                # If the error is not related to machine porting, raise it
                raise e

        # remove mom6_bathy notebook belonging to the test_grid:
        if os.path.exists(nb_path):
            os.remove(nb_path)

        # remove the caseroot directory
        if os.path.exists(temp_case_path):
            shutil.rmtree(temp_case_path)


if __name__ == "__main__":
    test_custom_mom6_grid()
    print("All tests passed!")
