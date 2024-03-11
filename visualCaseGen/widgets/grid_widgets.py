import logging
import ipywidgets as widgets
from ipyfilechooser import FileChooser
from pathlib import Path
from ProConPy.config_var import cvars

from visualCaseGen.custom_widget_types.multi_checkbox import MultiCheckbox

logger = logging.getLogger("\t" + __name__.split(".")[-1])

description_width = "160px"


def initialize_grid_widgets(cime):
    """Construct the grid widgets for the case configurator."""

    cv_grid_mode = cvars["GRID_MODE"]
    cv_grid_mode.widget = widgets.ToggleButtons(
        description="Configuration Mode:",
        layout={"display": "flex", "width": "max-content", "padding": "10px"},
        style={"button_width": "100px", "description_width": description_width},
        disabled=False,
    )

    initialize_standard_grid_widgets(cime)
    initialize_custom_grid_widgets(cime)

def initialize_standard_grid_widgets(cime):
    # Standard grid options
    cv_grid = cvars["GRID"]
    cv_grid.widget = MultiCheckbox(
        description="Grid:",
        allow_multi_select=False,
    )
    cv_grid.valid_opt_char = chr(int("27A4", base=16))

def initialize_custom_grid_widgets(cime):

    default_path = Path.home() 
    if cime.cime_output_root is not None:
        if (p := Path(cime.cime_output_root)).exists():
            default_path = p
    
    cv_custom_grid_path = cvars["CUSTOM_GRID_PATH"]
    cv_custom_grid_path.widget = FileChooser(
        path=default_path,
        filename="",
        title="Specify a new directory for custom grid files to be generated:",
        show_only_dirs=True,
        new_only=True,
        filename_placeholder="Enter new directory name",
        layout={'width': '90%', 'margin': '10px'},
    )


