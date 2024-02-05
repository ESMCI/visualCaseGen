import logging
import ipywidgets as widgets

from ProConPy.config_var import cvars

logger = logging.getLogger("\t" + __name__.split(".")[-1])


class GUI_compset_section(widgets.VBox):
    """GUI section for constructing the compset which consists of (1) components, (2) component
    physics, and (3) component options, i.e., modifiers. for all component classes."""

    def __init__(self, children=..., **kwargs):

        logger.debug("Constructing GUI compset section")

        self.initialize_widgets()

        super().__init__(children=[cvars["COMPSET_MODE"].widget], **kwargs)

    def initialize_widgets(self):

        cv_compset_mode = cvars["COMPSET_MODE"]
        cv_compset_mode.widget = widgets.ToggleButtons(
            description="Grid Selection Mode:",
            layout={"display": "flex", "width": "max-content", "margin": "15px"},
            disabled=False,
        )
