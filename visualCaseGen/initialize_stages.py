import logging
from ipywidgets import VBox, HBox, Tab

from ProConPy.config_var import cvars
from ProConPy.stage import Stage
from ProConPy.out_handler import handler as owh
from visualCaseGen.custom_widget_types.stage_widget import StageWidget

logger = logging.getLogger("\t" + __name__.split(".")[-1])

description_width = "160px"

@owh.out.capture()
def initialize_stages(cime):
    """Initialize the stages for the case configurator."""

    logger.debug("Initializing stages...")

    stg_compset = Stage(
        title="Step 1: Component Set",
        description="Select the component set and its options",
        widget = StageWidget(VBox),
        varlist = [
            cvars["COMPSET_MODE"]
        ],
    )

    #todo stg_standard_compset = Stage(
    #todo     title="Standard Component Set",
    #todo     description="Select from the list of predefined component sets",
    #todo     widget = VBox(),
    #todo     parent = stg_compset,
    #todo     activation_constr = #todo
    #todo )

    stg_custom_compset = Stage(
        title="Custom Component Set",
        description="Select the custom component set and its options",
        parent = stg_compset,
        activation_constr = cvars["COMPSET_MODE"] == "Custom"
    )

    stg_inittime = Stage(
        title="Model Time Period:",
        description="Select the initialization time",
        widget = StageWidget(VBox),
        parent = stg_custom_compset,
        varlist = [
            cvars["INITTIME"]
        ],
    )

    stg_comp= Stage(
        title="Components",
        description="Select the components",
        widget = StageWidget(HBox),
        parent = stg_custom_compset,
        varlist = [cvars[f"COMP_{comp_class}"] for comp_class in cime.comp_classes]
    )

    stg_comp_phys = Stage(
        title="Component Physics",
        description="Select the component physics",
        widget = StageWidget(HBox),
        parent = stg_custom_compset,
        varlist = [cvars[f"COMP_{comp_class}_PHYS"] for comp_class in cime.comp_classes]
    )

    stg_comp_option = Stage(
        title="Component Options",
        description="Select the component options",
        widget = StageWidget(Tab),
        parent = stg_custom_compset,
        varlist = [cvars[f"COMP_{comp_class}_OPTION"] for comp_class in cime.comp_classes]
    )
    for i, comp_class in enumerate(cime.comp_classes):
        stg_comp_option._widget._main_body.set_title(i, comp_class)

    stg_grid = Stage(
        title="Step 2: Grid",
        description="Select the grid",
        widget = StageWidget(VBox),
        varlist = [
            cvars["GRID_MODE"]
        ],
    )

    stg_launch = Stage(
        title="Step 3: Launch",
        description="Create and set up the case",
        widget = StageWidget(VBox),
        varlist = [],
    )

