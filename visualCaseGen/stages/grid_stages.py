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
        title="2. Grid",
        description="The second major step in the configuration process is to choose a "
        "resolution, i.e., a collection of grids for each active and data model in the compset. "
        "You may choose to use a standard, out-of-the-box resolution or create a custom one by "
        "mixing and matching readily available model grids. In custom mode, you may also create "
        "new CLM and/or MOM6 grids using the auxiliary tools that come with visualCaseGen.",
        widget=StageWidget(VBox),
        varlist=[cvars["GRID_MODE"]],
    )

    stg_standard_grid = Stage(
        title="Standard Grid",
        description="",
        parent=stg_grid,
        activation_guard=cvars["GRID_MODE"] == "Standard",
    )

    stg_standard_grid_selector = Stage(
        title="Standard Grid Selector",
        description="Please select from the below list of resolutions (collection of model grids). "
        "This list omits the resolutions that are known to be incompatible with the compset you have "
        "chosen in the first step. You may use the search box to further narrow down the list. For "
        "exact matches, you can use double quotes. Otherwise, the search will display all grids "
        "containing one or more of the words in the search box.",
        widget=StageWidget(VBox),
        parent=stg_standard_grid,
        varlist=[cvars["GRID"]],
        auto_set_single_valid_option=False,
    )
