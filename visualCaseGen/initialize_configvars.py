"""Module to define and register ConfigVars"""

import logging
from ProConPy.out_handler import handler as owh
from ProConPy.csp_solver import csp
from ProConPy.config_var import ConfigVar
from ProConPy.config_var_str import ConfigVarStr

logger = logging.getLogger('\t'+__name__.split('.')[-1])

def initialize_configvars(cime):
    """Initialize all ConfigVar instances and register them with the CSP solver."""
    logger.debug("Initializing ConfigVars...")

    initialize_compset_variables(cime)

@owh.out.capture()
def initialize_compset_variables(cime):

    ConfigVarStr('COMPSET_MODE')

    ConfigVarStr('INITTIME')

    for comp_class in cime.comp_classes:
        ConfigVarStr('COMP_'+str(comp_class))
        ConfigVarStr('COMP_{}_PHYS'.format(comp_class), always_set=True)


    ConfigVarStr('GRID_MODE')