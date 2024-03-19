import re
from ProConPy.config_var import cvars
from ProConPy.options_spec import OptionsSpec
from ProConPy.dev_utils import ConstraintViolation
from ProConPy.csp_solver import csp


def set_launcher_options(cime):

    cv_machine = cvars["MACHINE"]
    cv_machine.options = cime.machines
