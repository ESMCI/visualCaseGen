import logging
import ipywidgets as widgets

from ProConPy.config_var import cvars
from visualCaseGen.custom_widget_types.checkbox_multi_widget import CheckboxMultiWidget

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

    # Standard grid options
    cv_grid = cvars["GRID"]
    cv_grid.widget = CheckboxMultiWidget(
        description="Grid:",
        allow_multi_select=False,
    )
    cv_grid.valid_opt_char = chr(int("27A4", base=16))
