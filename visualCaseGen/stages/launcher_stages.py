import logging
from ipywidgets import VBox, HBox, Tab

from ProConPy.config_var import cvars
from ProConPy.stage import Stage
from ProConPy.out_handler import handler as owh
from visualCaseGen.custom_widget_types.stage_widget import StageWidget

logger = logging.getLogger("\t" + __name__.split(".")[-1])


@owh.out.capture()
def initialize_launcher_stages(cime):
    """Initialize the stages for the case launcher."""

    stg_launch = Stage(
        title="Step 3: Launch",
        description="Create and set up the case",
        widget=StageWidget(VBox),
        varlist=[],
    )
