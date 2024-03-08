import logging
import ipywidgets as widgets
from pathlib import Path
from ipyfilechooser import FileChooser


from ProConPy.config_var import cvars

logger = logging.getLogger("\t" + __name__.split(".")[-1])

description_width = "160px"


def initialize_launcher_widgets(cime):
    """Construct the grid widgets for the case configurator."""

    default_case_dir = cime.cime_output_root
    if default_case_dir is None:
        default_case_dir = Path(cime.cimeroot).parent.parent.as_posix()

    cv_caseroot = cvars["CASEROOT"]
    cv_caseroot.widget = FileChooser(
        path=default_case_dir,
        filename="",
        title="Select a case path and a case name:",
        show_hidden=True,
        new_only=True,
        filename_placeholder="Enter new case name",
        layout={'width': '90%', 'margin': '10px'}
    )

    cv_machine = cvars["MACHINE"]
    #if cime.machine is not None:
    #    cv_machine.value = cime.machine
    cv_machine.widget = widgets.Dropdown(
        description='Machine:',
        layout={'width': 'max-content', 'margin': '10px'}, # If the items' names are long
        style={'description_width': 'max-content'},
    )

    # A dummy variable with an undispayed widget to prevent the users from setting it
    # and so to stop the Launcher stage from completing.
    cv_doors = cvars["DOORSTOP"]
    cv_doors.widget = widgets.Label(
        value="",
        layout={'height':'5px', 'visibility': 'hidden'}
    )
