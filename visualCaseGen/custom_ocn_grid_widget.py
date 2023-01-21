import os
import logging
import ipywidgets as widgets
import nbformat as nbf
from datetime import datetime
from IPython.display import display, Javascript
import xarray as xr

from visualCaseGen.config_var import cvars
from visualCaseGen.OutHandler import handler as owh
from ipyfilechooser import FileChooser
from visualCaseGen.dialog import alert_error

logger = logging.getLogger(__name__)

button_width = '100px'
descr_width = '140px'

class CustomOcnGridWidget(widgets.VBox):

    def __init__(self,ci):

        super().__init__()
        #    layout={'padding':'15px','display':'flex','flex_flow':'column','align_items':'flex-start'}
        #)

        self.ci = ci

        self._cvars = [\
            cvars['OCN_GRID_EXTENT'],
            cvars['OCN_GRID_CONFIG'],
            cvars['OCN_TRIPOLAR_N'],
            cvars['OCN_CYCLIC_X'],
            cvars['OCN_CYCLIC_Y'],
            cvars['OCN_AXIS_UNITS'],
            cvars['OCN_NX'],
            cvars['OCN_NY'],
            cvars['OCN_LENX'],
            cvars['OCN_LENY'],
        ]

        self._construct_mom_grid_widgets()
        self._construct_observances()

    def _update_ocn_mesh_mode(self, change):

        selection = change['new']

        if selection == None:
            # reset and disable variables
            for var in self._cvars:
                var.value = None
                if var.has_options_spec():
                    var.refresh_options()
                var.widget.layout.display = 'none'

            # hide and reset mom6_supergrid_in
            self.mom6_supergrid_in.layout.display = 'none'
            self.mom6_supergrid_in.reset()
            self.mom6_topog_in.layout.display = 'none'
            self.mom6_topog_in.reset()
            self.btn_launch_mom6_bathy.layout.display = 'none'

        elif selection == "Modify an existing grid":

            # reset and disable variables
            for var in self._cvars:
                var.value = None
                if var.has_options_spec():
                    var.refresh_options()
                var.widget.layout.display = 'none'

            # display mom6_supergrid_in and mom6_topog_in
            self.mom6_supergrid_in.layout.display = 'flex'
            self.mom6_topog_in.layout.display = 'flex'
            self.btn_launch_mom6_bathy.layout.display = 'flex'

            # display other required configs:
            cyclic_x = cvars['OCN_CYCLIC_X']
            cyclic_x.widget.layout.display = ''
            cyclic_y = cvars['OCN_CYCLIC_Y']
            cyclic_y.widget.layout.display = ''
            tripolar_n = cvars['OCN_TRIPOLAR_N']
            tripolar_n.widget.layout.display = ''


        elif selection == "Start from scratch":
            # enable variables
            for var in self._cvars:
                var.widget.layout.display = ''

            # hide and reset mom6_supergrid_in
            self.mom6_supergrid_in.layout.display = 'none'
            self.mom6_supergrid_in.reset()
            self.mom6_topog_in.layout.display = 'none'
            self.mom6_topog_in.reset()
            # hide tripolar options, this is not yet supported in midas
            tripolar_n = cvars['OCN_TRIPOLAR_N']
            tripolar_n.widget.layout.display = 'none'
            tripolar_n.value = None

            self.btn_launch_mom6_bathy.layout.display = 'flex'

        else:
            raise RuntimeError("Unknown selection")

    def refresh_btn_launch_mom6_bathy(self, change):

        if self.tbtn_ocn_mesh_mode.value == 'Start from scratch':    
            if any([cvar.value is None and cvar.name != 'OCN_TRIPOLAR_N' for cvar in self._cvars]):
                self.btn_launch_mom6_bathy.disabled = True
            else:
                self.btn_launch_mom6_bathy.disabled = False
        elif self.tbtn_ocn_mesh_mode.value == 'Modify an existing grid':    
            required_vars = [
                self.mom6_supergrid_in,
                cvars['OCN_CYCLIC_X'],
                cvars['OCN_CYCLIC_Y'],
                cvars['OCN_TRIPOLAR_N'],
            ] 
            if any([var.value is None for var in required_vars]):
                self.btn_launch_mom6_bathy.disabled = True
            else:
                self.btn_launch_mom6_bathy.disabled = False
        else:
            raise RuntimeError("Unknown Ocn Mesh Mode selection")


    def _construct_observances(self):

        self.tbtn_ocn_mesh_mode.observe(
            self._update_ocn_mesh_mode,
            names='value',
            type='change'
        )

        for cvar in self._cvars:
            cvar.observe(
                self.refresh_btn_launch_mom6_bathy,
                names='value',
                type='change'
            )

        self.mom6_supergrid_in.observe(
            self.refresh_btn_launch_mom6_bathy,
            names='value',
            type='change'
        )

        self.btn_launch_mom6_bathy.on_click(
            self.launch_mom6_bathy
        )


    def _construct_mom_grid_widgets(self):

        # From existing grid? -----------------------------
        self.tbtn_ocn_mesh_mode = widgets.ToggleButtons(
            description='Ocean mesh:',
            options=['Start from scratch', 'Modify an existing grid'],
            value=None,
            layout={'width':'max-content', 'padding':'20px'}, # If the items' names are long
            disabled=False
        )
        self.tbtn_ocn_mesh_mode.style.button_width = '200px'
        self.tbtn_ocn_mesh_mode.style.description_width = '100px'

        # Read ocn supergrid file
        self.mom6_supergrid_in = FileChooser(
            path=os.getcwd(),
            filename='',
            title='<b>Original MOM6 supergrid file:</b>',
            show_hidden=True,
            select_default=True,
            show_only_dirs=False,
            filter_pattern="*.nc",
            existing_only=True,
            layout=widgets.Layout(width='600px', padding='10px', left='40px', display='none',
                flex_flow='column', align_items='flex-start')
        )
        # Read ocn topog file
        self.mom6_topog_in = FileChooser(
            path=os.getcwd(),
            filename='',
            title='<b>Original MOM6 topography file (optional):</b>',
            show_hidden=True,
            select_default=True,
            show_only_dirs=False,
            filter_pattern="*.nc",
            existing_only=True,
            layout=widgets.Layout(width='600px', padding='10px', left='40px', display='none',
                flex_flow='column', align_items='flex-start')
        )

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

        # OCN_TRIPOLAR_N -----------------------------
        cv_ocn_tripolar_n = cvars['OCN_TRIPOLAR_N']
        cv_ocn_tripolar_n.widget = widgets.ToggleButtons(
            description='Tripolar?',
            layout={'display':'none', 'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        cv_ocn_tripolar_n.widget.style.button_width = button_width
        cv_ocn_tripolar_n.widget.style.description_width = descr_width

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

        self.btn_launch_mom6_bathy = widgets.Button(
            description = 'Launch mom6_bathy',
            disabled = True,
            tooltip = "When ready, click this button to launch the mom6_bathy tool to further customize the MOM6 grid.",
            #icon = 'terminal',
            button_style='success', # 'success', 'info', 'warning', 'danger' or ''
            layout=widgets.Layout(display='none', width='170px', align_items='center'),
        )


        self._mom6_widgets = [
            self.tbtn_ocn_mesh_mode,
            self.mom6_supergrid_in,
            self.mom6_topog_in,
            cv_ocn_grid_extent.widget,
            cv_ocn_grid_config.widget,
            cv_ocn_cyclic_x.widget,
            cv_ocn_cyclic_y.widget,
            cv_ocn_tripolar_n.widget,
            cv_ocn_axis_units.widget,
            cv_ocn_nx.widget,
            cv_ocn_ny.widget,
            cv_ocn_lenx.widget,
            cv_ocn_leny.widget,
            widgets.HBox([],layout={'height':'20px'}),
            widgets.VBox([self.btn_launch_mom6_bathy], layout={'align_items':'center', 'width':'700px'}),
        ]


    @owh.out.capture()
    def launch_mom6_bathy(self, b):

        nx = cvars['OCN_NX'].value
        ny = cvars['OCN_NY'].value
        config = cvars['OCN_GRID_CONFIG'].value
        axis_units = cvars['OCN_AXIS_UNITS'].value
        lenx = cvars['OCN_LENX'].value
        leny = cvars['OCN_LENY'].value
        cyclic_x = cvars['OCN_CYCLIC_X'].value
        cyclic_y = cvars['OCN_CYCLIC_X'].value
        tripolar_n = cvars['OCN_TRIPOLAR_N'].value

        supergrid_path = self.mom6_supergrid_in.value
        topog_path = self.mom6_topog_in.value

        if self.tbtn_ocn_mesh_mode.value == 'Modify an existing grid':    

            from mom6_bathy.mom6grid import mom6grid
            from mom6_bathy.mom6bathy import mom6bathy

            # Check supergrid

            if supergrid_path is None:
                alert_error("Specify a MOM6 supergrid file path")
                return None

            try:
                supergrid_ds = xr.open_dataset(supergrid_path)
                mom6grid.check_supergrid(supergrid_ds)
            except Exception as e:
                logger.error(str(e))
                alert_error("Error occured while attempting to read supergrid file. See error log in Help tab below.")
                self.mom6_supergrid_in.reset()
                return None

            # Check topography file
            if topog_path is not None:
                try:
                    xr.open_dataset(topog_path)
                except Exception as e:
                    alert_error("Error occured while attempting to read topography file. See error log in Help tab below.")
                    self.mom6_topog_in.reset()
                    return None

        # Step 1 : Create a new notebook:
        # an example grid name
        grid_name = "simple_1v1"
        datestamp = f'{datetime.now().strftime("%Y%m%d")}'

        # Jupyter notebook object
        nb = nbf.v4.new_notebook()
        nb['cells'] = [
            nbf.v4.new_markdown_cell(
                "# mom6_bathy\n"
                "This notebook is auto-generated by visualCaseGen GUI. "
                "Please review and execute all of the cells below to finalize your custom MOM6 grid."
            ),
            nbf.v4.new_markdown_cell(
                "## 1. Import mom6_bathy"
            ),
            nbf.v4.new_code_cell(
                "%%capture\n"
                "from mom6_bathy.mom6grid import mom6grid\n"
                "from mom6_bathy.mom6bathy import mom6bathy"
            ),
            nbf.v4.new_markdown_cell(
                "## 2. Create horizontal grid\n"
            )]

        if self.tbtn_ocn_mesh_mode.value == 'Start from scratch':    
            nb['cells'].extend([
                nbf.v4.new_code_cell(
                f"""grd = mom6grid(
                nx         = {nx},         # Number of grid points in x direction
                ny         = {ny},          # Number of grid points in y direction
                config     = "{config}", # Grid configuration. Valid values: 'cartesian', 'mercator', 'spherical'
                axis_units = "{axis_units}",   # Grid axis units. Valid values: 'degrees', 'm', 'km'
                lenx       = {lenx},        # grid length in x direction, e.g., 360.0 (degrees)
                leny       = {leny},        # grid length in y direction
                cyclic_x   = {cyclic_x},
                cyclic_y   = {cyclic_y},
                )
                """
                ),
            ])
        elif self.tbtn_ocn_mesh_mode.value == 'Modify an existing grid':    
            nb['cells'].append(
                nbf.v4.new_code_cell(
                f"""grd = mom6grid.from_supergrid(
                "{supergrid_path}",
                cyclic_x   = {cyclic_x},
                cyclic_y   = {cyclic_y},
                tripolar_n   = {tripolar_n},
                )
                """
                )
            )
        else:
            raise RuntimeError("Unknown Ocn Mesh Mode selection")

        nb['cells'].append(
            nbf.v4.new_markdown_cell(
                "## 3. Configure bathymetry\n"
            )
        )

        if topog_path is None or self.tbtn_ocn_mesh_mode.value != 'Modify an existing grid':
            nb['cells'].extend([
                nbf.v4.new_markdown_cell(
                    "***mom6_bathy*** provides several idealized bathymetry options and customization methods. "
                    "Below, we show how to specify the simplest bathymetry configuration, a flat bottom. "
                    "Customize it as you see fit. See mom6_bathy documentation and example notebooks on how to "
                    "create custom bathymetries. "
                ),
                nbf.v4.new_code_cell(
                    "# Instantiate the bathymetry object\n"
                    "bathy = mom6bathy(grd, min_depth = 10.0)"
                ),
                nbf.v4.new_code_cell(
                    "# Set the bathymetry to be a flat bottom with a uniform depth of 2000m\n"
                    "bathy.set_flat(D=2000.0)"
                )
            ])
        else: # topog_path is not None
            nb['cells'].extend([
                nbf.v4.new_code_cell(
                    "# Instantiate the bathymetry object\n"
                    "bathy = mom6bathy(grd,\n"
                    "    min_depth = 10.0)  # NOTE: update min_depth as you see fit."
                ),
            nbf.v4.new_code_cell(
                    "# Set bathymetry via an existing topog file:\n"
                    f'bathy.set_depth_via_topog_file("{topog_path}")'
                ),
            ])

        nb['cells'].extend([
            nbf.v4.new_code_cell(
                "bathy.depth.plot()"
            ),
            nbf.v4.new_code_cell(
                "# Manually modify the bathymetry\n"
                "%matplotlib ipympl\n"
                "from mom6_bathy.depth_modifier import DepthModifier\n"
                "DepthModifier(bathy)"
            ),
            nbf.v4.new_markdown_cell(
                "## 4. Save the grid and bathymetry files"
            ),
            nbf.v4.new_code_cell(
                '# First, specify a unique name for your new grid, e.g.:\n'
                f'grid_name = "{grid_name}"\n\n'
                '# Save MOM6 supergrid file:\n'
                f'grd.to_netcdf(supergrid_path = f"./ocean_grid_{{grid_name}}_{datestamp}.nc")\n\n'
                '# Save MOM6 topography file:\n'
                f'bathy.to_topog(f"./ocean_topog_{{grid_name}}_{datestamp}.nc")\n\n'
                '# Save ESMF mesh file:\n'
                f'bathy.to_ESMF_mesh(f"./ESMF_mesh_{{grid_name}}_{datestamp}.nc")'
            ),
            nbf.v4.new_markdown_cell(
                "## 5. Print MOM6 runtime parameters\n\n"
                "The final step of creating a new MOM6 grid and bathymetry files is to determine "
                "the relevant MOM6 runtime parameters. To do so, simply run the "
                "`print_MOM6_runtime_params` method of bathy to print out the grid and bathymetry "
                "related MOM6 runtime parameters."
            ),
            nbf.v4.new_code_cell(
                'bathy.print_MOM6_runtime_params()'
            ),
            nbf.v4.new_markdown_cell(
                "This section conludes all of the `mom6_bathy steps.` After having executed all of the "
                "cells above, you can switch back to the visualCaseGen GUI to finalize your experiment "
                "configuration."
            ),
        ])

        nb_filename = f'mom6_bathy_notebook_{datetime.now().strftime("%Y%m%d_%H%M%S")}.ipynb'
        with open(nb_filename, 'w') as f:
            nbf.write(nb, f)
            nb_filepath = os.path.realpath(f.name)

        logger.info(f"Generated a new mom6_bathy notebook at {nb_filepath}")

        # Step 2 : Launch the notebook
        js = f"""
            var curr_url = window.location.href.split('/')
            var new_url = curr_url[0] + '//'
            for (var i = 1; i < curr_url.length - 1; i++) {{
                console.log(curr_url[i], new_url)
                new_url += curr_url[i] + '/'
            }}
            new_url += "{nb_filename}"
            window.open(new_url)
        """
        display(Javascript(js))


    def reset_vars(self):

        # reset all custom ocn grid vars
        for var in self._cvars:
            var.value = None
        for var in self._cvars:
            if var.has_options_spec():
                display = var.widget.layout.display
                var.refresh_options()
                var.widget.layout.display = display # refreshing options turns the display on,
                                                    # so turn it off if it was turned off.

        # reset values of custom ocn grid widgets (that aren't defined as ConfigVar instances)
        self.tbtn_ocn_mesh_mode.value = None
        self.mom6_supergrid_in.reset()
        self.mom6_topog_in.reset()


    def construct(self):

        comp_ocn = cvars['COMP_OCN'].value

        if comp_ocn == "mom":
            self.title = "MOM6 Grid"
            self.children = self._mom6_widgets
        else:
            self.title = "ERROR"
            self.children = [widgets.Label(f"ERROR: unsupported ocn component {comp_ocn} for custom grid feature")]
