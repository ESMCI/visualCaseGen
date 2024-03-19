"""Module to define and register ConfigVars"""

import logging
from ProConPy.out_handler import handler as owh
from ProConPy.config_var import cvars
from ProConPy.config_var_str import ConfigVarStr
from ProConPy.config_var_str_ms import ConfigVarStrMS
from ProConPy.config_var_int import ConfigVarInt
from ProConPy.config_var_real import ConfigVarReal

logger = logging.getLogger("\t" + __name__.split(".")[-1])


@owh.out.capture()
def initialize_grid_variables(cime):

    ConfigVarStr("GRID_MODE") # Standard or Custom

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
    ConfigVarStrMS("CUSTOM_ATM_GRID")

    # Custom ocean grid variables
    ConfigVarStr("OCN_GRID_MODE") # Standard, Modify Existing, Create New

    ConfigVarStr("CUSTOM_OCN_GRID_NAME", widget_none_val='', word_only=True) # name of the new ocean grid
    ConfigVarStrMS("CUSTOM_OCN_GRID") # Standard ocean grid picked for the custom grid
    ConfigVarStr("OCN_GRID_EXTENT") # global or regional
    ConfigVarStr('OCN_CYCLIC_X')
    ConfigVarInt('OCN_NX') # number of cells in x-direction
    ConfigVarInt('OCN_NY') # number of cells in y-direction
    ConfigVarReal('OCN_LENX') # grid length in x-direction
    ConfigVarReal('OCN_LENY') # grid length in y-direction
    ConfigVarStr('MOM6_BATHY_STATUS', widget_none_val='') # a status variable to prevent the completion of the stage

    # Select a base CLM grid.
    ConfigVarStr("LND_GRID_MODE") # Standard, Modified
    ConfigVarStrMS("CUSTOM_LND_GRID") # A preexisting land grid picked for the custom grid
    ConfigVarStr("INPUT_MASK_MESH")
 

