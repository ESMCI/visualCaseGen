import logging
from ipywidgets import VBox, HBox, Tab

from ProConPy.config_var import cvars
from ProConPy.stage import Stage
from ProConPy.out_handler import handler as owh
from visualCaseGen.custom_widget_types.stage_widget import StageWidget
from visualCaseGen.stages.compset_stages import initialize_compset_stages
from visualCaseGen.stages.grid_stages import initialize_grid_stages
from visualCaseGen.stages.launcher_stages import initialize_launcher_stages

logger = logging.getLogger("\t" + __name__.split(".")[-1])


@owh.out.capture()
def initialize_stages(cime):
    """Initialize the stages for the case configurator."""

    logger.debug("Initializing stages...")
    initialize_compset_stages(cime)
    initialize_grid_stages(cime)
    initialize_launcher_stages(cime)
