"""Module to define and register ConfigVars"""

import logging
from ProConPy.out_handler import handler as owh
from ProConPy.config_var import cvars
from ProConPy.config_var_str import ConfigVarStr
from ProConPy.config_var_str_ms import ConfigVarStrMS

logger = logging.getLogger("\t" + __name__.split(".")[-1])


@owh.out.capture()
def initialize_grid_variables(cime):
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

    # The selected ATM grid in custom grid mode
    ConfigVarStr("CUSTOM_ATM_GRID")

    # Custom ocean grid variables

    ConfigVarStr("CUSTOM_OCN_GRID") # custom ocean grid name
    ConfigVarStr('OCN_CYCLIC_X')

