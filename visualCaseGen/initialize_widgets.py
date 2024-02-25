import logging

from visualCaseGen.widgets.initialize_compset_widgets import initialize_compset_widgets
from visualCaseGen.widgets.initialize_grid_widgets import initialize_grid_widgets

logger = logging.getLogger("\t" + __name__.split(".")[-1])

description_width = "160px"

def initialize_widgets(cime):
    """Construct all widgets for the case configurator."""

    initialize_compset_widgets(cime)
    initialize_grid_widgets(cime)
