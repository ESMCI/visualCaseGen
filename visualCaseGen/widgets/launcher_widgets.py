import logging
import ipywidgets as widgets
from pathlib import Path
from ipyfilechooser import FileChooser


from ProConPy.config_var import cvars
from visualCaseGen.custom_widget_types.disabled_text import DisabledText

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
        title="Select a case root (full path and name):",
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
        layout={'width': '260px', 'margin': '10px'}, # If the items' names are long
        style={'description_width': '80px'},
    )

    cv_project = cvars["PROJECT"]
    cv_project.widget = widgets.Text(
        description='Project ID:',
        layout={'width': '260px', 'margin': '10px'},
        style={'description_width': '80px'},
    )

    cv_case_creator_status = cvars["CASE_CREATOR_STATUS"]
    cv_case_creator_status.widget = DisabledText(value = '',)