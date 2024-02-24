import logging
from ipywidgets import VBox, HBox, Tab

from ProConPy.config_var import cvars
from ProConPy.stage import Stage
from ProConPy.out_handler import handler as owh
from visualCaseGen.custom_widget_types.stage_widget import StageWidget

logger = logging.getLogger("\t" + __name__.split(".")[-1])


@owh.out.capture()
def initialize_grid_stages(cime):
    """Initialize the stages for grid configuration."""

    stg_grid = Stage(
        title="Step 2: Grid",
        description="Select the grid",
        widget=StageWidget(VBox),
        varlist=[cvars["GRID_MODE"]],
    )

    stg_standard_grid = Stage(
        title="Standard Grid",
        description="Select from the list of predefined grids",
        parent=stg_grid,
        activation_constr=cvars["GRID_MODE"] == "Standard",
    )

    stg_standard_grid_selector = Stage(
        title="Standard Grid Selector",
        description="Select the standard grid",
        widget=StageWidget(VBox),
        parent=stg_standard_grid,
        varlist=[cvars["GRID"]],
    )
