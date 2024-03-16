"""Module to define and register ConfigVars"""

import logging
from ProConPy.out_handler import handler as owh
from ProConPy.config_var import cvars
from ProConPy.config_var_str import ConfigVarStr

logger = logging.getLogger("\t" + __name__.split(".")[-1])


@owh.out.capture()
def initialize_launcher_variables(cime):

    ConfigVarStr("CASEROOT") # Path where the case will be created
    ConfigVarStr(
        "MACHINE",
        default_value = cime.machine,
    )
    ConfigVarStr(
        "PROJECT",
        widget_none_val="",
    )
