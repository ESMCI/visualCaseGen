"""Module to define and register ConfigVars"""

import logging
from ProConPy.out_handler import handler as owh
from ProConPy.config_var import cvars
from ProConPy.config_var_str import ConfigVarStr
from ProConPy.config_var_str_ms import ConfigVarStrMS

logger = logging.getLogger("\t" + __name__.split(".")[-1])


@owh.out.capture()
def initialize_grid_variables(cime):

    ConfigVarStrMS("GRID")

    # component grids
    ConfigVarStr("MASK_GRID")
    for comp_class in cime.comp_classes:
        ConfigVarStr(f"{comp_class}_GRID")
