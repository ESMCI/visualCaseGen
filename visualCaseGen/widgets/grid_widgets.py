import logging
from ipywidgets import ToggleButtons, Text
from ipyfilechooser import FileChooser
from pathlib import Path
from ProConPy.config_var import cvars

from visualCaseGen.custom_widget_types.multi_checkbox import MultiCheckbox
from visualCaseGen.custom_widget_types.disabled_text import DisabledText

logger = logging.getLogger("\t" + __name__.split(".")[-1])

description_width = "160px"


def initialize_grid_widgets(cime):
    """Construct the grid widgets for the case configurator."""

    cv_grid_mode = cvars["GRID_MODE"]
    cv_grid_mode.widget = ToggleButtons(
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
        title="Specify a directory and a new grid name:",
        new_only=True,
        filename_placeholder="Enter new grid name",
        layout={'width': '90%', 'margin': '10px'},
    )

    cv_custom_atm_grid = cvars["CUSTOM_ATM_GRID"]
    cv_custom_atm_grid.widget = MultiCheckbox(
        description="Custom ATM Grid:",
        allow_multi_select=False,
    )

    cv_custom_ocn_grid_mode = cvars["OCN_GRID_MODE"]
    cv_custom_ocn_grid_mode.widget = ToggleButtons(
        description="Ocean Grid Mode:",
        layout={"display": "flex", "width": "max-content", "padding": "10px"},
        style={"button_width": "140px", "description_width": description_width},
    )

    cv_custom_ocn_grid = cvars["CUSTOM_OCN_GRID"]
    cv_custom_ocn_grid.widget = MultiCheckbox(
        description="Custom Ocean Grid:",
        allow_multi_select=False,
    )

    cv_ocn_grid_extent = cvars["OCN_GRID_EXTENT"]
    cv_ocn_grid_extent.widget = ToggleButtons(
        description="Grid Extent:",
        layout={"display": "flex", "left":"30px", "width": "max-content", "padding": "5px"},
        style={"button_width": "100px", "description_width": "125px"},
    )

    cv_ocn_cyclic_x = cvars["OCN_CYCLIC_X"]
    cv_ocn_cyclic_x.widget = ToggleButtons(
        description="Zonally Reentrant:",
        layout={"display": "flex", "left":"30px", "width": "max-content", "padding": "5px"},
        style={"button_width": "100px", "description_width": "125px"},
    )

    cv_ocn_nx = cvars["OCN_NX"]
    cv_ocn_nx.widget = Text(
        description="Number of Cells in X direction:",
        layout={"width": "370px", "padding": "5px"},
        style={"description_width": "250px"},
    )

    cv_ocn_ny = cvars["OCN_NY"]
    cv_ocn_ny.widget = Text(
        description="Number of Cells in Y direction:",
        layout={"width": "370px", "padding": "5px"},
        style={"description_width": "250px"},
    )

    cv_ocn_lenx = cvars["OCN_LENX"]
    cv_ocn_lenx.widget = Text(
        description="Grid Length in X direction (degrees):",
        layout={"width": "370px", "padding": "5px"},
        style={"description_width": "250px"},
    )

    cv_ocn_leny = cvars["OCN_LENY"]
    cv_ocn_leny.widget = Text(
        description="Grid Length in Y direction (degrees):",
        layout={"width": "370px", "padding": "5px"},
        style={"description_width": "250px"},
    )

    cv_custom_ocn_grid_name = cvars["CUSTOM_OCN_GRID_NAME"]
    cv_custom_ocn_grid_name.widget = Text(
        description="Custom Ocean Grid Name:",
        layout={"width": "370px", "padding": "5px"},
        style={"description_width": "250px"},
    )

    cv_mom6_bathy_stat = cvars["MOM6_BATHY_STATUS"]
    cv_mom6_bathy_stat.widget = DisabledText(
        value = '',
        disabled = True, 
        description="mom6_bathy status:",
        placeholder = "Incomplete",
        layout={"width": "300px", "padding": "5px", "align_self": "flex-end"},
        style={"description_width": "150px", "background":"lightgray", "text_color":"white"},
    )