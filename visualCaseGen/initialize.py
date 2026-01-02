import logging

from ProConPy.config_var import ConfigVar, cvars
from ProConPy.stage import Stage
from ProConPy.csp_solver import csp
from visualCaseGen.cime_interface import CIME_interface
from visualCaseGen.initialize_configvars import initialize_configvars
from visualCaseGen.initialize_widgets import initialize_widgets
from visualCaseGen.initialize_stages import initialize_stages
from visualCaseGen.specs.options import set_options
from visualCaseGen.specs.relational_constraints import get_relational_constraints

logger = logging.getLogger('\t'+__name__.split('.')[-1])


def initialize(cesmroot=None):
    """Initialize the visualCaseGen system by setting up configuration variables, stages, and widgets.

    Parameters:
    -----------
    cesmroot : str, optional
        The path to the CESM root directory. If not provided, it will be determined automatically.
    
    Returns:
    --------
    cime : CIME_interface
        An instance of the CIME_interface class, initialized with the provided CESM root directory.
    """

    logger.info("Initializing the visualCaseGen system...")

    ConfigVar.reboot()
    Stage.reboot()
    cime = CIME_interface(cesmroot=cesmroot)
    initialize_configvars(cime)
    initialize_widgets(cime)
    initialize_stages(cime)
    set_options(cime)
    csp.initialize(cvars, get_relational_constraints(cvars), Stage.first())

    return cime