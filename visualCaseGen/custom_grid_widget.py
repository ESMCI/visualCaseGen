import os
import re
from pathlib import Path
import subprocess
import ipywidgets as widgets
from visualCaseGen.config_var import cvars
from visualCaseGen.save_custom_grid_widget import SaveCustomGrid
from visualCaseGen.read_mesh_file import ReadMeshFile

button_width = '100px'
descr_width = '140px'


class CustomGridWidget(widgets.VBox):

    def __init__(self,layout=widgets.Layout()):

        super().__init__(layout=layout)

        description = widgets.HTML(
            "<p style='text-align:left'>In custom grid mode, you can create new grids for the ocean and/or the land components by setting the below configuration variables. After having set all the variables, you can save grid configuration files to be read in by subsequent tools to further customize and complete the grids.</p>"
        )

        self.custom_ocn_grid_vars = [\
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

        self._ocean_grid_section = None

        self.turn_off() # by default, the display is off.

        ocean_grid_section = self._construct_ocn_grid_section()
        land_grid_section = self._construct_lnd_grid_section()
        horiz_line = widgets.HTML('<hr>')

        self.children = [
            description,
            horiz_line,
            ocean_grid_section,
            horiz_line,
            land_grid_section,
        ]

        self.construct_observances()
        self.layout.width = '750px'

    
    def update_from_existing_ocn_mesh(self, change):

        selection = change['new']

        self.save_custom_grid.layout.display = ''

        if selection == "Modify an existing mesh":

            # reset and disable variables
            for var in self.custom_ocn_grid_vars:
                var.value = None
                if var.has_options_spec():
                    var.refresh_options()
                var.widget.layout.display = 'none'
            
            self.read_ocn_mesh_file.layout.display = 'flex'



        elif selection == "Start from scratch":
            # enable variables
            for var in self.custom_ocn_grid_vars:
                var.widget.layout.display = ''
        
            self.read_ocn_mesh_file.layout.display = 'none'
            self.read_ocn_mesh_file.filepath.value = ''

        else:
            raise RuntimeError("Unknown selection")
        
    
    def construct_observances(self):

        self.ocn_mesh_mode.observe(
            self.update_from_existing_ocn_mesh,
            names='value',
            type='change'
        )

    
    def _construct_ocn_grid_section(self):

        header = widgets.HTML(
            value="<u><b>Ocean Grid Settings</b></u>",
        )

        # From existing mesh? -----------------------------
        self.ocn_mesh_mode = widgets.ToggleButtons(
            description='Ocean mesh:',
            options=['Start from scratch', 'Modify an existing mesh'],
            value=None,
            layout={'width':'max-content', 'padding':'20px'}, # If the items' names are long
            disabled=False
        )
        self.ocn_mesh_mode.style.button_width = '200px'
        self.ocn_mesh_mode.style.description_width = '100px'

        # Read ocn mesh file
        self.read_ocn_mesh_file = ReadMeshFile('OCN',
            layout={'padding':'15px','display':'none','flex_flow':'column','align_items':'flex-start'})

        # OCN_GRID_EXTENT -----------------------------
        cv_ocn_grid_extent = cvars['OCN_GRID_EXTENT']
        cv_ocn_grid_extent.widget = widgets.ToggleButtons(
            description='Grid Extent:',
            layout={'display':'none', 'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        cv_ocn_grid_extent.widget.style.button_width = button_width
        cv_ocn_grid_extent.widget.style.description_width = descr_width

        # OCN_GRID_CONFIG -----------------------------
        cv_ocn_grid_config = cvars['OCN_GRID_CONFIG']
        cv_ocn_grid_config.widget = widgets.ToggleButtons(
            description='Grid Config:',
            layout={'display':'none', 'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        cv_ocn_grid_config.widget.style.button_width = button_width
        cv_ocn_grid_config.widget.style.description_width = descr_width

        # OCN_CYCLIC_X -----------------------------
        cv_ocn_cyclic_x = cvars['OCN_CYCLIC_X']
        cv_ocn_cyclic_x.widget = widgets.ToggleButtons(
            description='Zonally reentrant?',
            layout={'display':'none', 'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        cv_ocn_cyclic_x.widget.style.button_width = button_width
        cv_ocn_cyclic_x.widget.style.description_width = descr_width

        # OCN_CYCLIC_Y -----------------------------
        cv_ocn_cyclic_y = cvars['OCN_CYCLIC_Y']
        cv_ocn_cyclic_y.widget = widgets.ToggleButtons(
            description='Meridionally reentrant?',
            layout={'display':'none', 'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        cv_ocn_cyclic_y.widget.style.button_width = button_width
        cv_ocn_cyclic_y.widget.style.description_width = descr_width

        # OCN_AXIS_UNITS -----------------------------
        cv_ocn_axis_units = cvars['OCN_AXIS_UNITS']
        cv_ocn_axis_units.widget = widgets.ToggleButtons(
            description='Axis Units:',
            layout={'display':'none', 'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        cv_ocn_axis_units.widget.style.button_width = button_width
        cv_ocn_axis_units.widget.style.description_width = descr_width

        # OCN_NX -----------------------------
        cv_ocn_nx = cvars['OCN_NX']
        cv_ocn_nx.widget = widgets.Text(
            description='Number of cells in x direction:',
            layout={'display':'none', 'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        cv_ocn_nx.widget.style.button_width = button_width
        cv_ocn_nx.widget.style.description_width = '200px'

        # OCN_NY -----------------------------
        cv_ocn_ny = cvars['OCN_NY']
        cv_ocn_ny.widget = widgets.Text(
            description='Number of cells in y direction:',
            layout={'display':'none', 'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        cv_ocn_ny.widget.style.button_width = button_width
        cv_ocn_ny.widget.style.description_width = '200px'

        # OCN_LENX -----------------------------
        cv_ocn_lenx = cvars['OCN_LENX']
        cv_ocn_lenx.widget = widgets.Text(
            description='Grid length in x direction:',
            layout={'display':'none', 'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        cv_ocn_lenx.widget.style.button_width = button_width
        cv_ocn_lenx.widget.style.description_width = '200px'

        # OCN_LENY -----------------------------
        cv_ocn_leny = cvars['OCN_LENY']
        cv_ocn_leny.widget = widgets.Text(
            description='Grid length in y direction:',
            layout={'display':'none', 'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        cv_ocn_leny.widget.style.button_width = button_width
        cv_ocn_leny.widget.style.description_width = '200px'


        # save custom grid widget
        self.save_custom_grid = SaveCustomGrid('OCN',
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
        layout={'padding':'15px','display':'none','flex_flow':'column','align_items':'flex-start'})

        return widgets.VBox([
            header,
            self.ocn_mesh_mode,
            self.read_ocn_mesh_file,
            cv_ocn_grid_extent.widget,
            cv_ocn_grid_config.widget,
            cv_ocn_cyclic_x.widget,
            cv_ocn_cyclic_y.widget,
            cv_ocn_axis_units.widget,
            cv_ocn_nx.widget,
            cv_ocn_ny.widget,
            cv_ocn_lenx.widget,
            cv_ocn_leny.widget,
            self.save_custom_grid,
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
        for var in self.custom_ocn_grid_vars:
            var.value = None
        for var in self.custom_ocn_grid_vars:
            if var.has_options_spec():
                var.refresh_options()

    def turn_on(self):
        self.layout.display = ''
