import os
import re
from pathlib import Path
import subprocess
import ipywidgets as widgets
from visualCaseGen.config_var import cvars

button_width = '100px'
descr_width = '100px'

class CustomGridWidget(widgets.VBox):

    def __init__(self,layout=widgets.Layout()):

        super().__init__(layout=layout)

        description = widgets.HTML(
            "<p style='text-align:left'>In custom grid mode, you can create new grids for the ocean and/or the land components.</p>"
        )

        self.turn_off() # by default, the display is off.

        self._ocean_grid_section = None

        ocean_grid_section = self._construct_ocn_grid_section()
        land_grid_section = self._construct_lnd_grid_section()

        self.children = [
            description,
            ocean_grid_section,
            land_grid_section,
        ]

        self.layout.width = '750px'
    
    def _construct_ocn_grid_section(self):

        header = widgets.HTML(
            value="<u><b>Ocean Grid Settings</b></u>",
        )

        cv_ocn_grid_extent = cvars['OCN_GRID_EXTENT']
        cv_ocn_grid_extent.widget = widgets.ToggleButtons(
            description='Grid Extent:',
            layout={'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        cv_ocn_grid_extent.widget.style.button_width = button_width
        cv_ocn_grid_extent.widget.style.description_width = descr_width

        cv_ocn_grid_config = cvars['OCN_GRID_CONFIG']
        cv_ocn_grid_config.widget = widgets.ToggleButtons(
            description='Grid Config:',
            layout={'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        cv_ocn_grid_config.widget.style.button_width = button_width
        cv_ocn_grid_config.widget.style.description_width = descr_width

        return widgets.VBox([
            header,
            cv_ocn_grid_extent.widget,
            cv_ocn_grid_config.widget,
        ],
        layout={'padding':'15px','display':'flex','flex_flow':'column','align_items':'flex-start'})

    def _construct_lnd_grid_section(self):

        header = widgets.HTML(
            value="<u><b>Land Grid Settings</b></u>",
        )

        w = widgets.ToggleButtons(
            description='Grid Config:',
            layout={'width': 'max-content'}, # If the items' names are long
            disabled=False,
            options= ['foo', 'bar', 'baz'],
        )
        w.style.button_width = button_width
        w.style.description_width = descr_width

        return widgets.VBox([
            header,
            w,
        ],
        layout={'padding':'15px','display':'flex','flex_flow':'column','align_items':'flex-start'})
    
    def turn_off(self):
        self.layout.display = 'none'
        
        #todo: also reset configvars

    def turn_on(self):
        self.layout.display = ''
