import logging
from pathlib import Path


from ProConPy.config_var import cvars
from ProConPy.dialog import alert_warning
from ProConPy.out_handler import handler as owh

logger = logging.getLogger("\t" + __name__.split(".")[-1])

@owh.out.capture()
def create_case(b, cime):

    if cvars['CASEROOT'].value is None:
        alert_warning('No case directory and name specified yet.')
    elif cvars['MACHINE'].value is None:
        alert_warning('No machine specified yet.')
    elif cvars['PROJECT'].value is None and cime.project_required[cvars['MACHINE'].value] is True:
        alert_warning('No project specified yet.')


def _do_create_case(cime, show_commands_only=False):
    """Create the case."""

    caseroot = Path(cvars["CASEROOT"].value)
    if not caseroot.is_absolute():
        caseroot = Path.home() / caseroot
    