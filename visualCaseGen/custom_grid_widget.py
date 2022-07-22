import os
import re
from pathlib import Path
import subprocess
import ipywidgets as widgets
from visualCaseGen.config_var import cvars
from visualCaseGen.save_custom_grid_widget import SaveCustomGrid

button_width = '100px'
descr_width = '140px'

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

        # OCN_GRID_EXTENT -----------------------------
        cv_ocn_grid_extent = cvars['OCN_GRID_EXTENT']
        cv_ocn_grid_extent.widget = widgets.ToggleButtons(
            description='Grid Extent:',
            layout={'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        cv_ocn_grid_extent.widget.style.button_width = button_width
        cv_ocn_grid_extent.widget.style.description_width = descr_width

        # OCN_GRID_CONFIG -----------------------------
        cv_ocn_grid_config = cvars['OCN_GRID_CONFIG']
        cv_ocn_grid_config.widget = widgets.ToggleButtons(
            description='Grid Config:',
            layout={'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        cv_ocn_grid_config.widget.style.button_width = button_width
        cv_ocn_grid_config.widget.style.description_width = descr_width

        # OCN_CYCLIC_X -----------------------------
        cv_ocn_cyclic_x = cvars['OCN_CYCLIC_X']
        cv_ocn_cyclic_x.widget = widgets.ToggleButtons(
            description='Zonally reentrant?',
            layout={'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        cv_ocn_cyclic_x.widget.style.button_width = button_width
        cv_ocn_cyclic_x.widget.style.description_width = descr_width

        # OCN_CYCLIC_Y -----------------------------
        cv_ocn_cyclic_y = cvars['OCN_CYCLIC_Y']
        cv_ocn_cyclic_y.widget = widgets.ToggleButtons(
            description='Meridionally reentrant?',
            layout={'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        cv_ocn_cyclic_y.widget.style.button_width = button_width
        cv_ocn_cyclic_y.widget.style.description_width = descr_width

        # OCN_AXIS_UNITS -----------------------------
        cv_ocn_axis_units = cvars['OCN_AXIS_UNITS']
        cv_ocn_axis_units.widget = widgets.ToggleButtons(
            description='Axis Units:',
            layout={'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        cv_ocn_axis_units.widget.style.button_width = button_width
        cv_ocn_axis_units.widget.style.description_width = descr_width

        # OCN_NX -----------------------------
        cv_ocn_nx = cvars['OCN_NX']
        cv_ocn_nx.set_to_a_random_valid_value()
        cv_ocn_nx.widget = widgets.IntText(
            description='Number of cells in x direction:',
            layout={'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        cv_ocn_nx.widget.style.button_width = button_width
        cv_ocn_nx.widget.style.description_width = '200px'

        # OCN_NY -----------------------------
        cv_ocn_ny = cvars['OCN_NY']
        cv_ocn_ny.set_to_a_random_valid_value()
        cv_ocn_ny.widget = widgets.IntText(
            description='Number of cells in y direction:',
            layout={'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        cv_ocn_ny.widget.style.button_width = button_width
        cv_ocn_ny.widget.style.description_width = '200px'

        # OCN_LENX -----------------------------
        cv_ocn_lenx = cvars['OCN_LENX']
        cv_ocn_lenx.set_to_a_random_valid_value()
        cv_ocn_lenx.widget = widgets.FloatText(
            description='Grid length in x direction:',
            layout={'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        cv_ocn_lenx.widget.style.button_width = button_width
        cv_ocn_lenx.widget.style.description_width = '200px'

        # OCN_LENY -----------------------------
        cv_ocn_leny = cvars['OCN_LENY']
        cv_ocn_leny.set_to_a_random_valid_value()
        cv_ocn_leny.widget = widgets.FloatText(
            description='Grid length in y direction:',
            layout={'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        cv_ocn_leny.widget.style.button_width = button_width
        cv_ocn_leny.widget.style.description_width = '200px'


        # save custom grid widget
        save_custom_grid = SaveCustomGrid('OCN',
        {var.name: var for var in [\
            cv_ocn_grid_extent,
            cv_ocn_grid_config,
            cv_ocn_cyclic_x,
            cv_ocn_cyclic_y,
            cv_ocn_axis_units,
            cv_ocn_nx,
            cv_ocn_ny,
            cv_ocn_lenx,
            cv_ocn_leny,
        ]},
        layout={'padding':'15px','display':'flex','flex_flow':'column','align_items':'flex-start'})

        return widgets.VBox([
            header,
            cv_ocn_grid_extent.widget,
            cv_ocn_grid_config.widget,
            cv_ocn_cyclic_x.widget,
            cv_ocn_cyclic_y.widget,
            cv_ocn_axis_units.widget,
            cv_ocn_nx.widget,
            cv_ocn_ny.widget,
            cv_ocn_lenx.widget,
            cv_ocn_leny.widget,
            save_custom_grid,
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

        # reset all custom grid vars
        custom_grid_vars = [\
            cvars['OCN_GRID_EXTENT'],
            cvars['OCN_GRID_CONFIG'],
            cvars['OCN_TRIPOLAR'],
            cvars['OCN_CYCLIC_X'],
            cvars['OCN_CYCLIC_Y'],
            cvars['OCN_AXIS_UNITS'],
            cvars['OCN_NX'],
            cvars['OCN_NY'],
            cvars['OCN_LENX'],
            cvars['OCN_LENY'],
        ]

        for var in custom_grid_vars:
            var.value = None
        for var in custom_grid_vars:
            if var.has_options_spec():
                var.refresh_options()

    def turn_on(self):
        self.layout.display = ''
