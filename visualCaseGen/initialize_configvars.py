"""Module to define and register ConfigVars"""

import logging
from ProConPy.config_var_str import ConfigVarStr
from visualCaseGen.config_vars.compset_vars import initialize_compset_variables
from visualCaseGen.config_vars.grid_vars import initialize_grid_variables
from visualCaseGen.config_vars.launcher_vars import initialize_launcher_variables

logger = logging.getLogger("\t" + __name__.split(".")[-1])


def initialize_configvars(cime):
    """Initialize all ConfigVar instances and so register them with the CSP solver."""
    logger.debug("Initializing ConfigVars...")

    initialize_compset_variables(cime)
    initialize_grid_variables(cime)
    initialize_launcher_variables(cime)
