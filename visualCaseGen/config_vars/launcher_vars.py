"""Module to define and register ConfigVars"""

import logging
from ProConPy.out_handler import handler as owh
from ProConPy.config_var import cvars
from ProConPy.config_var_str import ConfigVarStr
from ProConPy.config_var_int import ConfigVarInt

logger = logging.getLogger("\t" + __name__.split(".")[-1])


@owh.out.capture()
def initialize_launcher_variables(cime):

    ConfigVarStr("CASEROOT") # Path where the case will be created
    ConfigVarStr(
        "MACHINE",
        default_value = cime.machine,
    )
    ConfigVarStr("PROJECT", widget_none_val="") # Project ID for the machine
    ConfigVarStr("CASE_CREATOR_STATUS", widget_none_val="") # a status variable to prevent the completion of the stage
    ConfigVarInt("NINST", default_value=1) # Number of model instances (Currently, can only be controlled in the backend,
                                           # particularly when visualCaseGen is used as an external library)