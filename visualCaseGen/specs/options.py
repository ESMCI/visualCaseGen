import re
from ProConPy.config_var import cvars
from ProConPy.options_spec import OptionsSpec
from ProConPy.dev_utils import ConstraintViolation
from ProConPy.csp_solver import csp

from visualCaseGen.specs.compset_options import set_compset_options
from visualCaseGen.specs.grid_options import set_grid_options
from visualCaseGen.specs.launcher_options import set_launcher_options


def set_options(cime):

    set_compset_options(cime)
    set_grid_options(cime)
    set_launcher_options(cime)

