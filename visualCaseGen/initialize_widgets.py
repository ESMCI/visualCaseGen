import logging

from visualCaseGen.widgets.compset_widgets import initialize_compset_widgets
from visualCaseGen.widgets.grid_widgets import initialize_grid_widgets
from visualCaseGen.widgets.launcher_widgets import initialize_launcher_widgets

logger = logging.getLogger("\t" + __name__.split(".")[-1])

description_width = "160px"


def initialize_widgets(cime):
    """Construct all widgets for the case configurator."""

    initialize_compset_widgets(cime)
    initialize_grid_widgets(cime)
    initialize_launcher_widgets(cime)
