"""Module to define and register ConfigVars"""

import logging
from ProConPy.config_var_str import ConfigVarStr
from visualCaseGen.config_vars.standard_compset_vars import initialize_standard_compset_variables
from visualCaseGen.config_vars.custom_compset_vars import initialize_custom_compset_variables
from visualCaseGen.config_vars.grid_vars import initialize_grid_variables
from visualCaseGen.config_vars.launcher_vars import initialize_launcher_variables

logger = logging.getLogger("\t" + __name__.split(".")[-1])


def initialize_configvars(cime):
    """Initialize all ConfigVar instances and so register them with the CSP solver."""
    logger.debug("Initializing ConfigVars...")

    ConfigVarStr("COMPSET_MODE")
    ConfigVarStr("GRID_MODE")

    initialize_standard_compset_variables(cime)
    initialize_custom_compset_variables(cime)
    initialize_grid_variables(cime)
    initialize_launcher_variables(cime)
