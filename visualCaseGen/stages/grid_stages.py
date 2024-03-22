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
from visualCaseGen.custom_widget_types.clm_modifier_launcher import MeshMaskModifierLauncher, FsurdatModifierLauncher

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

    stg_custom_preexisting_ocn_grid = Stage(
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
        parent=stg_custom_preexisting_ocn_grid,
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

    stg_new_ocn_grid._widget.children += (MOM6BathyLauncher(),)

    stg_custom_lnd_grid_mode = Stage(
        title="Land Grid Mode",
        description="Determine whether to use a standard land grid or modify an existing land grid.",
        widget=StageWidget(VBox),
        parent=stg_custom_grid,
        varlist=[cvars["LND_GRID_MODE"]],
    )

    stg_standard_custom_lnd_grid_guard = Stage(
        title="Custom Standard Land Grid",
        description="",
        parent=stg_custom_lnd_grid_mode,
        activation_guard=cvars["LND_GRID_MODE"] == "Standard",
    )

    stg_standard_custom_lnd_grid = Stage(
        title="Land Grid",
        description="If the land component is not CLM, then the land grid is set to be set to the "
        "atmosphere grid.",
        widget=StageWidget(VBox),
        parent=stg_standard_custom_lnd_grid_guard,
        varlist=[cvars["CUSTOM_LND_GRID"]],
    )

    stg_custom_new_lnd_grid = Stage(
        title="Custom New Land Grid",
        description="",
        parent=stg_custom_lnd_grid_mode,
        activation_guard=cvars["LND_GRID_MODE"] == "Modified",
    )

    stg_base_lnd_grid = Stage(
        title="Base Land Grid",
        description="Select a base CLM grid. In the following stages, you will be able to modify the "
        "base land mask and surface data.",
        widget=StageWidget(VBox),
        parent=stg_custom_new_lnd_grid,
        varlist=[cvars["CUSTOM_LND_GRID"]],
    )

    stg_custom_clm_grid_with_mom = Stage(
        title="Parent of Mesh Mask tage",
        description="",
        parent=stg_base_lnd_grid,
        activation_guard=cvars["COMP_OCN"] == "mom",
    )

    stg_fsurdat_modifier_no_mom = Stage(
        title="Surface Data Modifier",
        description="The fsurdat modifier tool is used to modify the surface data file. ",
        widget=StageWidget(VBox),
        parent=stg_custom_clm_grid_with_mom,
        varlist=[
            cvars["INPUT_FSURDAT"],
            cvars["FSURDAT_AREA_SPEC"],
            cvars["FSURDAT_IDEALIZED"],
            cvars["LND_DOM_PFT"],
            cvars["LND_SOIL_COLOR"],
            cvars["LND_STD_ELEV"],
            cvars["LND_MAX_SAT_AREA"],
            cvars["LND_INCLUDE_NONVEG"],
            cvars["FSURDAT_MOD_STATUS"]
        ],
    )
    fsurdat_modifier_launcher = FsurdatModifierLauncher(cime.srcroot)
    stg_fsurdat_modifier_no_mom._widget.children += (
        cvars["FSURDAT_MATRIX"]._widget,
        fsurdat_modifier_launcher
    )

    stg_custom_clm_grid_no_mom = Stage(
        title="Branch for creating custom CLM grids when MOM6 is not selected.",
        description="",
        parent=stg_base_lnd_grid,
        activation_guard=cvars["COMP_OCN"] != "mom",
    )

    stg_mesh_mask_modifier = Stage(
        title="Mesh Mask Modifier",
        description="No active ocean component is selected, so the mesh mask modifier tool must "
        "be utilized to determine the land mask. Configure the mesh mask modifier tool as follows. "
        "Firstly, a land mesh file containing the coordinates of the land domain must be provided. "
        "If found, this will be auto-filled to a default mesh path. The second field is another land "
        "mask file that contains the final land mask. This file must be created by the user beforehand. "
        "You may then specify the variable and dimension names of latitude and longitude in the mask file. "
        "Finally, specify the output file name to be generated by the mesh_mask_modifier tool.",
        widget=StageWidget(VBox),
        parent=stg_custom_clm_grid_no_mom,
        varlist=[
            cvars["INPUT_MASK_MESH"],
            cvars["LAND_MASK"],
            cvars["LAT_VAR_NAME"],
            cvars["LON_VAR_NAME"],
            cvars["LAT_DIM_NAME"],
            cvars["LON_DIM_NAME"],
            cvars["MESH_MASK_MOD_STATUS"],
        ],
    )
    stg_mesh_mask_modifier._widget.children += (MeshMaskModifierLauncher(cime.srcroot),)

    stg_fsurdat_modifier = Stage(
        title="Surface Data Modifier",
        description="The fsurdat modifier tool is used to modify the surface data file. ",
        widget=StageWidget(VBox),
        parent=stg_custom_clm_grid_no_mom,
        varlist=[
            cvars["INPUT_FSURDAT"],
            cvars["FSURDAT_AREA_SPEC"],
            cvars["FSURDAT_IDEALIZED"],
            cvars["LND_DOM_PFT"],
            cvars["LND_SOIL_COLOR"],
            cvars["LND_STD_ELEV"],
            cvars["LND_MAX_SAT_AREA"],
            cvars["LND_INCLUDE_NONVEG"],
            cvars["FSURDAT_MOD_STATUS"]
        ],
    )
    stg_fsurdat_modifier._widget.children += (
        cvars["FSURDAT_MATRIX"]._widget,
        fsurdat_modifier_launcher
    )


    