import logging
import ipywidgets as widgets

from visualCaseGen.gui_compset_section import GUI_compset_section

logger = logging.getLogger('\t'+__name__.split('.')[-1])

class GUI_case_configurator(widgets.VBox):
    
    def __init__(self):

        super().__init__(
            children = [
                GUI_compset_section()
            ]
        )
