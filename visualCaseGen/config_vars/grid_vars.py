"""Module to define and register ConfigVars"""

import os
import logging
from pathlib import Path
from ProConPy.out_handler import handler as owh
from ProConPy.config_var import cvars
from ProConPy.config_var_str import ConfigVarStr
from ProConPy.config_var_str_ms import ConfigVarStrMS
from ProConPy.config_var_int import ConfigVarInt
from ProConPy.config_var_real import ConfigVarReal

logger = logging.getLogger("\t" + __name__.split(".")[-1])


@owh.out.capture()
def initialize_grid_variables(cime):

    ConfigVarStr("GRID_MODE")  # Standard or Custom

    initialize_standard_grid_variables(cime)
    initialize_custom_grid_variables(cime)


def initialize_standard_grid_variables(cime):

    ConfigVarStrMS("GRID")

    # component grids
    ConfigVarStr("MASK_GRID")
    for comp_class in cime.comp_classes:
        ConfigVarStr(f"{comp_class}_GRID")


def initialize_custom_grid_variables(cime):

    # The path where all custom grid input files are stored
    ConfigVarStr("CUSTOM_GRID_PATH")

    # A preexisting ATM grid picked for custom grid
    ConfigVarStrMS("CUSTOM_ATM_GRID", default_value="0.9x1.25")

    # Custom ocean grid variables
    ConfigVarStr("OCN_GRID_MODE")  # Standard, Modify Existing, Create New

    ConfigVarStr(
        "CUSTOM_OCN_GRID_NAME", widget_none_val="", word_only=True
    )  # name of the new ocean grid
    ConfigVarStrMS("CUSTOM_OCN_GRID")  # Standard ocean grid picked for the custom grid
    ConfigVarStr("OCN_GRID_EXTENT")  # global or regional
    ConfigVarStr("OCN_CYCLIC_X")
    ConfigVarInt("OCN_NX")  # number of cells in x-direction
    ConfigVarInt("OCN_NY")  # number of cells in y-direction
    ConfigVarReal("OCN_LENX")  # grid length in x-direction
    ConfigVarReal("OCN_LENY")  # grid length in y-direction
    ConfigVarStr('MB_ATTEMPT_ID') # latest mom6_bathy attempt id (auxiliary variable)
    ConfigVarStr(
        "MOM6_BATHY_STATUS", widget_none_val=""
    )  # a status variable to prevent the completion of the stage

    # Ocean initial conditions
    ConfigVarStr("OCN_IC_MODE")  # "Simple" or "From File"
    ConfigVarReal("T_REF")  # Reference temperature for "Simple" mode
    ConfigVarStr("TEMP_SALT_Z_INIT_FILE") # Path to the initial temperature and salinity file
    ConfigVarStr("IC_PTEMP_NAME", widget_none_val="") # Name of the potential temperature variable in the i.c. file
    ConfigVarStr("IC_SALT_NAME", widget_none_val="") # Name of the salinity variable in the initial i.c. file

    # Select a base CLM grid.
    ConfigVarStr("LND_GRID_MODE")  # Standard, Modified
    ConfigVarStrMS(
        "CUSTOM_LND_GRID",
        default_value="0.9x1.25"
    )  # A preexisting land grid picked for the custom grid

    # Auto-fill the INPUT_MASK_MESH variable based on the CUSTOM_LND_GRID variable
    def default_input_mask_mesh():
        """Update INPUT_MASK_MESH default value based on CUSTOM_LND_GRID and iff LND_GRID_MODE is Modified"""

        custom_lnd_grid = cvars["CUSTOM_LND_GRID"].value
        if (
            custom_lnd_grid is not None
            and (domain := cime.domains["lnd"].get(custom_lnd_grid, None)) is not None
        ):
            mesh_path = domain.mesh
            if "DIN_LOC_ROOT" in mesh_path and cime.din_loc_root:
                mesh_path = mesh_path.replace(
                    "$DIN_LOC_ROOT", cime.din_loc_root
                ).replace("${DIN_LOC_ROOT}", cime.din_loc_root)
            if os.path.exists(mesh_path):
                return mesh_path
        return None

    ConfigVarStr("INPUT_MASK_MESH", default_value=default_input_mask_mesh)

    # Land mask file
    ConfigVarStr("LAND_MASK")

    # Lat/lon variable and dimension names:
    ConfigVarStr("LAT_VAR_NAME", word_only=True, default_value="lats", widget_none_val="")
    ConfigVarStr("LON_VAR_NAME", word_only=True, default_value="lons", widget_none_val="")
    ConfigVarStr("LAT_DIM_NAME", word_only=True, default_value="lsmlat", widget_none_val="")
    ConfigVarStr("LON_DIM_NAME", word_only=True, default_value="lsmlon", widget_none_val="")
    ConfigVarStr("MESH_MASK_MOD_STATUS", widget_none_val="") # a status variable to prevent the completion of the stage prematurely


    # fsurdat variables

    def default_input_fsurdat():
        """Default value setter for the INPUT_FSURDAT variable based on the 
        CUSTOM_LND_GRID variable and the INITTIME variable."""

        inittime = cvars["INITTIME"].value
        if inittime is None:
            inittime = cvars["COMPSET_LNAME"].value.split("_")[0]

        custom_lnd_grid = cvars["CUSTOM_LND_GRID"].value

        if inittime == "HIST" or "SSP" in inittime:
            # for HIST and SSP runs, it's ok to use 1850 fsurdat data (slevis)
            inittime = "1850"

        if inittime in cime.clm_fsurdat and custom_lnd_grid in cime.clm_fsurdat[inittime]:
            fsurdat_path = cime.clm_fsurdat[inittime][custom_lnd_grid]
            if fsurdat_path[0] == "\n":
                fsurdat_path = fsurdat_path[1:]
            if Path(fsurdat_path).exists():
                return fsurdat_path
            elif cime.din_loc_root and (fpath := Path(cime.din_loc_root, fsurdat_path)).exists():
                return str(fpath)
        return None

    ConfigVarStr("INPUT_FSURDAT", default_value=default_input_fsurdat)  # path to the initial fsurdat file


    def default_fsurdat_area_spec():
        land_mask = cvars["LAND_MASK"].value
        if land_mask is not None and Path(land_mask).exists():
            return f'mask_file:{land_mask}'
        return None

    ConfigVarStr("FSURDAT_AREA_SPEC", default_value=default_fsurdat_area_spec) # corner coordinates or mask file

    ConfigVarStr("FSURDAT_IDEALIZED")

    ConfigVarInt("LND_DOM_PFT")
    ConfigVarInt("LND_SOIL_COLOR")
    ConfigVarReal("LND_STD_ELEV")
    ConfigVarReal("LND_MAX_SAT_AREA")
    ConfigVarStr("LND_INCLUDE_NONVEG")
    ConfigVarStr("FSURDAT_MATRIX")  # a matrix of LAI, SAI, hgt_top, hgt_bot values
                                    # Note: this var isn't a part of any of the stages.
    ConfigVarStr("FSURDAT_MOD_STATUS", widget_none_val="") # a status variable to prevent the completion of the stage prematurely

