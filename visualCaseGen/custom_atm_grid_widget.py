import os
import logging
import ipywidgets as widgets

from visualCaseGen.config_var import cvars
from visualCaseGen.OutHandler import handler as owh

logger = logging.getLogger(__name__)

button_width = '100px'
descr_width = '140px'

class CustomAtmGridWidget(widgets.VBox):

    def __init__(self, ci):

        super().__init__()
        self.ci = ci

    def reset_vars(self):
        custom_atm_grid = cvars['CUSTOM_ATM_GRID']
        custom_atm_grid.value = None
        custom_atm_grid.refresh_options()


    def construct(self):
        self.title = "ATM Grid..."
        custom_atm_grid = cvars['CUSTOM_ATM_GRID']
        custom_atm_grid.widget = widgets.ToggleButtons()
        self.children = [
            widgets.HTML(
                """Select an ATM grid from the below list of predefined grids. (Hover over options for grid descriptions)<br>
                Then, proceed to the next tab(s) in this dialog to finalize any remaining custom model grids."""),
            custom_atm_grid.widget]
