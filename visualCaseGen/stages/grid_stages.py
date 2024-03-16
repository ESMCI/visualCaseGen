import logging
from ipywidgets import VBox, HBox
from pathlib import Path
import time
import os

from ProConPy.config_var import cvars
from ProConPy.stage import Stage
from ProConPy.out_handler import handler as owh
from visualCaseGen.custom_widget_types.stage_widget import StageWidget
from visualCaseGen.custom_widget_types.mom6_bathy_launcher import MOM6BathyLauncher

logger = logging.getLogger("\t" + __name__.split(".")[-1])


@owh.out.capture()
def initialize_grid_stages(cime):
    """Initialize the stages for grid configuration."""

    stg_grid = Stage(
        title="2. Grid",
        description="The second major step in the configuration process is to choose a "
        "resolution, i.e., a collection of grids for each active and data model in the compset. "
        "You may choose to use a standard, out-of-the-box resolution or create a custom one by "
        "mixing and matching readily available model grids. In custom mode, you may also create "
        "new CLM and/or MOM6 grids using the auxiliary tools that come with visualCaseGen.",
        widget=StageWidget(VBox),
        varlist=[cvars["GRID_MODE"]],
    )

    stg_standard_grid = Stage(
        title="Standard Grid",
        description="",
        parent=stg_grid,
        activation_guard=cvars["GRID_MODE"] == "Standard",
    )

    stg_standard_grid_selector = Stage(
        title="Standard Grid Selector",
        description="Please select from the below list of resolutions (collection of model grids). "
        "This list omits the resolutions that are known to be incompatible with the compset you have "
        "chosen in the first step. You may use the search box to further narrow down the list. For "
        "exact matches, you can use double quotes. Otherwise, the search will display all grids "
        "containing one or more of the words in the search box.",
        widget=StageWidget(VBox),
        parent=stg_standard_grid,
        varlist=[cvars["GRID"]],
        auto_set_valid_option=False,
    )

    stg_custom_grid = Stage(
        title="Custom Grid",
        description="",
        parent=stg_grid,
        activation_guard=cvars["GRID_MODE"] == "Custom",
    )

    stg_custom_grid_selector = Stage(
        title="Custom Grid Generator",
        description="Create a new, custom grid by mixing and matching standard model grids or by "
        "creating new MOM6 and/or CLM grids using the auxiliary tools that come with visualCaseGen. "
        "Before creating the new grid, specify a path where the new grid files will be stored. Also, "
        "specify the grid (resolution) name that will be used to refer to the new grid in the rest of "
        "the configuration process and afterwards.",
        widget=StageWidget(VBox),
        parent=stg_custom_grid,
        varlist=[cvars["CUSTOM_GRID_PATH"]],
    )

    stg_custom_atm_grid = Stage(
        title="Atmosphere Grid",
        description="From the below list of standard atmosphere grids, select one to be used as the "
        "atmosphere grid within the new, custom CESM grid.",
        widget=StageWidget(HBox),
        parent=stg_custom_grid,
        varlist=[cvars["CUSTOM_ATM_GRID"]],
    )

    stg_custom_ocn_grid_mode = Stage(
        title="Ocean Grid Mode",
        description="You have the option to either use a standard ocean grid or, if you picked "
        "MOM6 as the ocean model, create a new ocean grid. If you choose to create a new ocean grid, "
        "you will be prompted to specify the grid extent, resolution, and other parameters. You "
        "will then be directed to a new notebook to create the new grid using the mom6_bathy tool.",
        widget=StageWidget(VBox),
        parent=stg_custom_grid,
        varlist=[cvars["OCN_GRID_MODE"]],
    )

    stg_custom_standard_ocn_grid = Stage(
        title="Custom Standard Ocean Grid",
        description="",
        parent=stg_custom_ocn_grid_mode,
        activation_guard=cvars["OCN_GRID_MODE"] == "Standard",
    )
    
    stg_custom_ocn_grid = Stage(
        title="Ocean Grid",
        description="From the below list of standard ocean grids, select one to be used as the "
        "ocean grid within the new, custom CESM grid.",
        widget=StageWidget(VBox),
        parent=stg_custom_standard_ocn_grid,
        varlist=[cvars["CUSTOM_OCN_GRID"]],
    )

    stg_custom_new_ocn_grid = Stage(
        title="Custom New Ocean Grid",
        description="",
        parent=stg_custom_ocn_grid_mode,
        activation_guard=cvars["OCN_GRID_MODE"] != "Standard",
    )
    
    stg_new_ocn_grid = Stage(
        title="Custom Ocean Grid",
        description="Specify the grid extent, resolution, and other parameters for the new ocean grid. "
        "Once all the parameters are specified, the Launch mom6_bathy button will be enabled. Clicking "
        "the button will launch a new notebook. Execute all the cells in the notebook to create the new "
        "grid. Once all the cells are executed, return to this tab and click the Confirm Completion "
        "button to proceed to the next stage.",
        widget=StageWidget(VBox),
        parent=stg_custom_new_ocn_grid,
        auto_proceed=False,
        varlist=[
            cvars["OCN_GRID_EXTENT"],
            cvars["OCN_CYCLIC_X"],
            cvars["OCN_NX"],
            cvars["OCN_NY"],
            cvars["OCN_LENX"],
            cvars["OCN_LENY"],
            cvars["CUSTOM_OCN_GRID_NAME"],
            cvars["MOM6_BATHY_STATUS"],
        ],
    )

    mom6_bathy_launcher_widget = MOM6BathyLauncher()
    
    stg_new_ocn_grid._widget.children += (mom6_bathy_launcher_widget,)

