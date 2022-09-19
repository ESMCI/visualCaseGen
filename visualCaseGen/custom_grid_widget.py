import os
import re
import logging
import ipywidgets as widgets
from visualCaseGen.config_var import cvars
from visualCaseGen.save_custom_grid_widget import SaveCustomGrid
from visualCaseGen.read_mesh_file import ReadMeshFile
from visualCaseGen.OutHandler import handler as owh

logger = logging.getLogger(__name__)

button_width = '100px'
descr_width = '140px'

class CustomGridWidget(widgets.VBox):

    def __init__(self,layout=widgets.Layout()):

        super().__init__(layout=layout)

        self.description = widgets.HTML(
            "<p style='text-align:left'>In custom grid mode, you can create new grids for the ocean and/or the land components by setting the below configuration variables. After having set all the variables, you can save grid configuration files to be read in by subsequent tools to further customize and complete the grids.</p>"
        )
        self.horiz_line = widgets.HTML('<hr>')

        self.custom_ocn_grid_vars = [\
            cvars['OCN_GRID_EXTENT'],
            cvars['OCN_GRID_CONFIG'],
            #todo cvars['OCN_TRIPOLAR'],
            cvars['OCN_CYCLIC_X'],
            cvars['OCN_CYCLIC_Y'],
            cvars['OCN_AXIS_UNITS'],
            cvars['OCN_NX'],
            cvars['OCN_NY'],
            cvars['OCN_LENX'],
            cvars['OCN_LENY'],
        ]

        self.custom_lnd_grid_vars = [\
            cvars['LND_LAT_1'],
            cvars['LND_LAT_2'],
            cvars['LND_LON_1'],
            cvars['LND_LON_2'],
            cvars['LND_DOM_PFT'],
            cvars['LND_SOIL_COLOR'],
        ]

        self._construct_mom_grid_widgets()
        self._construct_clm_mesh_mask_modifier_widgets()
        self._construct_clm_fsurdat_widgets()

        self.construct_observances()
        self.layout.width = '750px'

        self.turn_off() # by default, the display is off.
        self.refresh_display()

    
    def update_ocn_mesh_mode(self, change):

        selection = change['new']

        if selection == None:
            # reset and disable variables
            for var in self.custom_ocn_grid_vars:
                var.value = None
                if var.has_options_spec():
                    var.refresh_options()
                var.widget.layout.display = 'none'

            # hide and reset read_ocn_mesh_file 
            self.read_ocn_mesh_file.layout.display = 'none'
            self.read_ocn_mesh_file.filepath.value = ''
            self.btn_launch_mom6_bathy.layout.display = 'none'

        elif selection == "Modify an existing mesh":

            # reset and disable variables
            for var in self.custom_ocn_grid_vars:
                var.value = None
                if var.has_options_spec():
                    var.refresh_options()
                var.widget.layout.display = 'none'
            
            # display read_ocn_mesh_file 
            self.read_ocn_mesh_file.layout.display = 'flex'
            self.btn_launch_mom6_bathy.layout.display = 'flex'

        elif selection == "Start from scratch":
            # enable variables
            for var in self.custom_ocn_grid_vars:
                var.widget.layout.display = ''
        
            # hide and reset read_ocn_mesh_file 
            self.read_ocn_mesh_file.layout.display = 'none'
            self.read_ocn_mesh_file.filepath.value = ''
            self.btn_launch_mom6_bathy.layout.display = 'flex'

        else:
            raise RuntimeError("Unknown selection")
        
    
    def refresh_display(self, change=None):

        ocn = cvars['COMP_OCN'].value
        lnd = cvars['COMP_LND'].value

        # first determine how to align items
        if ocn is None or lnd is None:
            self.layout.align_items = 'center'
        else:
            self.layout.align_items = None

        # now, determine what items to display
        if ocn is None and lnd is None:
            self.children = [widgets.Label("(Custom grid dialogs will appear here after both the OCN and LND components are determined.)")]
        elif ocn is None:
            self.children = [widgets.Label("(Custom grid dialogs will be displayed here after the OCN component is determined.)")]
        elif lnd is None:
            self.children = [widgets.Label("(Custom grid dialogs will be displayed here after the LND component is determined.)")]
        else: # both ocean and lnd is determined.

            children = [self.description, self.horiz_line]

            # construct the ocean grid section layout
            if ocn == "mom":
                children.append(self._mom6_grid_widgets)
                children.append(self.horiz_line)
            elif ocn in ['docn', 'socn']:
                pass
            else:
                children.append(
                    widgets.Label(f"ERROR: unsupported ocn component {ocn} for custom grid feature")
                )

            if lnd == "clm":
                
                children.append(
                    widgets.HTML(
                        value="<u><b>Land Grid Settings</b></u>",
                    )
                )

                if ocn != "mom":
                    children.append(
                        widgets.HTML(
                            value=" <b>mesh_mask_modifier</b><br> Since no active ocean component is selected, the mesh_mask_modifier tool must be used. Fill in the below fields to configure the mesh_mask modifier tools.",
                        )
                    )
                    children.append(self._clm_mesh_mask_modifier_widgets)

                children.append(
                    widgets.HTML(
                        value=" <b>fsurdat_modifier</b><br> Set the following configuration variables to determine the CLM surface dataset.",
                    )
                )
                children.append(self._clm_fsurdat_widgets)
            elif lnd in ['dlnd', 'slnd']:
                pass
            else:
                children.append(
                    widgets.Label(f"ERROR: unsupported ocn component {ocn} for custom grid feature")
                )

            self.children = children


    def refresh_lnd_specify_area(self, change):

        if change['new'] == 'via corner coords':
            self.lnd_lat_1.widget.layout.display=''
            self.lnd_lat_2.widget.layout.display=''
            self.lnd_lon_1.widget.layout.display=''
            self.lnd_lon_2.widget.layout.display=''
        elif change['new'] == 'via mask file' or change['new'] is None:
            self.lnd_lat_1.widget.layout.display='none'
            self.lnd_lat_2.widget.layout.display='none'
            self.lnd_lon_1.widget.layout.display='none'
            self.lnd_lon_2.widget.layout.display='none'
        else:
            raise RuntimeError(f"Unknown land specification selection {change['new']}")


    def construct_observances(self):

        self.tbtn_ocn_mesh_mode.observe(
            self.update_ocn_mesh_mode,
            names='value',
            type='change'
        )

        cv_comp_ocn = cvars['COMP_OCN']
        cv_comp_ocn.observe(
            self.refresh_display,
            names='value',
            type='change'
        )

        for cvar in self.custom_ocn_grid_vars:
            cvar.observe(
                self.refresh_btn_launch_mom6_bathy,
                names='value',
                type='change'
            )


        self.btn_launch_mom6_bathy.on_click(
            self.launch_mom6_bathy
        )

        cv_comp_lnd = cvars['COMP_LND']
        cv_comp_lnd.observe(
            self.refresh_display,
            names='value',
            type='change'
        )

        self.lnd_specify_area.observe(
            self.refresh_lnd_specify_area,
            names='value',
            type='change'
        )
    
    def _construct_mom_grid_widgets(self):

        header = widgets.HTML(
            value="<u><b>Custom MOM6 Grid Settings</b></u>",
        )

        # From existing mesh? -----------------------------
        self.tbtn_ocn_mesh_mode = widgets.ToggleButtons(
            description='Ocean mesh:',
            options=['Start from scratch', 'Modify an existing mesh'],
            value=None,
            layout={'width':'max-content', 'padding':'20px'}, # If the items' names are long
            disabled=False
        )
        self.tbtn_ocn_mesh_mode.style.button_width = '200px'
        self.tbtn_ocn_mesh_mode.style.description_width = '100px'

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

        self.btn_launch_mom6_bathy = widgets.Button(
            description = 'Launch mom6_bathy',
            disabled = True,
            tooltip = "When ready, click this button to launch the mom6_bathy tool to further customize the MOM6 grid.",
            #icon = 'terminal',
            button_style='success', # 'success', 'info', 'warning', 'danger' or ''
            layout=widgets.Layout(display='none', width='170px', align_items='center'),
        )


        self._mom6_grid_widgets = widgets.VBox([
            header,
            self.tbtn_ocn_mesh_mode,
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
            widgets.HBox([],layout={'height':'20px'}),
            widgets.VBox([self.btn_launch_mom6_bathy], layout={'align_items':'center', 'width':'700px'}),
        ],
        layout={'padding':'15px','display':'flex','flex_flow':'column','align_items':'flex-start'})
    
    def refresh_btn_launch_mom6_bathy(self, change):
        if any([cvar.value is None for cvar in self.custom_ocn_grid_vars]):
            self.btn_launch_mom6_bathy.disabled = True
        else:
            self.btn_launch_mom6_bathy.disabled = False


    @owh.out.capture()
    def launch_mom6_bathy(self, b):
        
        # Step 1 : Create a new notebook:
        import nbformat as nbf
        from datetime import datetime
        from IPython.display import display, Javascript

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
            ),
            nbf.v4.new_code_cell(
                """grd = mom6grid(
                nx         = 100,         # Number of grid points in x direction
                ny         = 50,          # Number of grid points in y direction
                config     = "cartesian", # Grid configuration. Valid values: 'cartesian', 'mercator', 'spherical'
                axis_units = "degrees",   # Grid axis units. Valid values: 'degrees', 'm', 'km'
                lenx       = 100.0,        # grid length in x direction, e.g., 360.0 (degrees)
                leny       = 50.0,        # grid length in y direction
                cyclic_x   = "False",     # non-reentrant, rectangular domain
                )
                """
            ),
            nbf.v4.new_markdown_cell(
                "## 3. Configure bathymetry\n"
            ),
            nbf.v4.new_markdown_cell(
                "***mom6_bathy*** provides several idealized bathymetry options and customization methods. "
                "Below, we show how to specify the simplest bathymetry configuration, a flat bottom. "
                "Customize it as you see fit. See mom6_bathy documentation and example notebooks on how to create custom bathymetries. "
            ),
            nbf.v4.new_code_cell(
                "# Instantiate the bathymetry object\n"
                "bathy = mom6bathy(grd, min_depth = 10.0)"
            ),
            nbf.v4.new_code_cell(
                "# Set the bathymetry to be a flat bottom with a uniform depth of 2000m\n"
                "bathy.set_flat(D=2000.0)"
            ),
            nbf.v4.new_code_cell(
                "bathy.depth.plot()"
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
        ]



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


    def _construct_clm_mesh_mask_modifier_widgets(self):

        mesh_mask_in = widgets.Textarea(
            value='',
            placeholder='Type an existing mask mesh directory',
            description='Input mask mesh:',
            layout=widgets.Layout(height='40px', width='600px')
        )
        mesh_mask_in.style.description_width = descr_width

        mesh_mask_out = widgets.Textarea(
            value='',
            placeholder='Type a new path',
            description='Output mask mesh:',
            layout=widgets.Layout(height='40px', width='600px')
        )
        mesh_mask_out.style.description_width = descr_width

        
        landmask_file = widgets.Textarea(
            value='',
            placeholder='Type a new path',
            description='Land mask:',
            layout=widgets.Layout(height='40px', width='600px')
        )
        landmask_file.style.description_width = descr_width

        lat_varname = widgets.Textarea(
            value='lsmlat',
            description='Latitude var. name',
            layout=widgets.Layout(height='40px', width='600px')
        )
        lat_varname.style.description_width = descr_width

        lon_varname = widgets.Textarea(
            value='lsmlon',
            description='Longitude var. name',
            layout=widgets.Layout(height='40px', width='600px')
        )
        lon_varname.style.description_width = descr_width

        lat_dimname = widgets.Textarea(
            value='lsmlat',
            description='Latitude dim. name',
            layout=widgets.Layout(height='40px', width='600px')
        )
        lat_dimname.style.description_width = descr_width

        lon_dimname = widgets.Textarea(
            value='lsmlon',
            description='Longitude dim. name',
            layout=widgets.Layout(height='40px', width='600px')
        )
        lon_dimname.style.description_width = descr_width


        self._clm_mesh_mask_modifier_widgets = widgets.VBox([
            mesh_mask_in,
            mesh_mask_out,
            landmask_file,
            lat_varname,
            lon_varname,
            lat_dimname,
            lon_dimname,
        ],
        layout={'padding':'15px','display':'flex','flex_flow':'column','align_items':'flex-start'})

    def _construct_clm_fsurdat_widgets(self):

        self.fsurdat_in = widgets.Textarea(
            value='',
            placeholder='Type fsurdat input file ',
            description='Input surface dataset',
            layout=widgets.Layout(height='40px', width='600px')
        )
        self.fsurdat_in.style.description_width = '180px'

        self.fsurdat_out = widgets.Textarea(
            value='',
            placeholder='Type fsurdat output file ',
            description='Output surface dataset',
            layout=widgets.Layout(height='40px', width='600px')
        )
        self.fsurdat_out.style.description_width = '180px'
        
        self.lnd_idealized = widgets.ToggleButtons(
            description='Idealized?',
            options=['True', 'False'],
            value=None,
            layout={'width':'max-content'}, # If the items' names are long
            disabled=False
        )
        self.lnd_idealized.style.description_width = '180px'
        self.lnd_idealized.style.button_width = '200px'

        self.lnd_specify_area = widgets.ToggleButtons(
            description='Specify area of customization',
            options=['via corner coords', 'via mask file'],
            value=None,
            layout={'width':'max-content'}, # If the items' names are long
            disabled=False
        )
        self.lnd_specify_area.style.description_width = '180px'
        self.lnd_specify_area.style.button_width = '200px'

        self.lnd_lat_1 = cvars['LND_LAT_1']
        self.lnd_lat_1.widget = widgets.Text(
            description='Southernmost latitude for rectangle:',
            layout={'display':'none', 'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        self.lnd_lat_1.widget.style.description_width = '300px'

        self.lnd_lat_2 = cvars['LND_LAT_2']
        self.lnd_lat_2.widget = widgets.Text(
            description='Northernmost latitude for rectangle:',
            layout={'display':'none', 'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        self.lnd_lat_2.widget.style.description_width = '300px'

        self.lnd_lon_1 = cvars['LND_LON_1']
        self.lnd_lon_1.widget = widgets.Text(
            description='Westernmost longitude for rectangle:',
            layout={'display':'none', 'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        self.lnd_lon_1.widget.style.description_width = '300px'

        self.lnd_lon_2 = cvars['LND_LON_2']
        self.lnd_lon_2.widget = widgets.Text(
            description='Easternmost longitude for rectangle:',
            layout={'display':'none', 'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        self.lnd_lon_2.widget.style.description_width = '300px'

        lnd_dom_pft = cvars['LND_DOM_PFT']
        lnd_dom_pft.widget = widgets.Text(
            description='PFT/CFT',
            layout={'display':'', 'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        lnd_dom_pft.widget.style.description_width = '300px'

        lnd_soil_color = cvars['LND_SOIL_COLOR']
        lnd_soil_color.widget = widgets.Text(
            description='Soil color (between 0-20)',
            layout={'display':'', 'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        lnd_soil_color.widget.style.description_width = '300px'

        self.std_elev = widgets.Text(
            description='Std. dev. of elevation',
            layout={'display':'', 'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        self.std_elev.style.description_width = '300px'

        self.max_sat_area = widgets.Text(
            description='Max saturated area',
            layout={'display':'', 'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        self.max_sat_area.style.description_width = '300px'

        self.include_nonveg = widgets.ToggleButtons(
            description='Include non-vegetation land units?',
            options=['True', 'False'],
            tooltips=['landunits unchanged if True', 'landunits set to 0 if False'],
            value=None,
            layout={'width':'max-content'}, # If the items' names are long
            disabled=False
        )
        self.include_nonveg.style.description_width = '180px'
        self.include_nonveg.style.button_width = '200px'


        self._clm_fsurdat_widgets = widgets.VBox([
            self.fsurdat_in,
            self.fsurdat_out,
            self.lnd_idealized,
            self.lnd_specify_area,
            self.lnd_lat_1.widget,
            self.lnd_lat_2.widget,
            self.lnd_lon_1.widget,
            self.lnd_lon_2.widget,
            widgets.Label(''),
            lnd_dom_pft.widget,
            lnd_soil_color.widget,
            self.std_elev,
            self.max_sat_area,
            self.include_nonveg,
        ],
        layout={'padding':'15px','display':'flex','flex_flow':'column','align_items':'flex-start'})
    
    def turn_off(self):
        self.layout.display = 'none'

        # reset all custom ocn grid vars
        for var in self.custom_ocn_grid_vars:
            var.value = None
        for var in self.custom_ocn_grid_vars:
            if var.has_options_spec():
                var.refresh_options()
                var.widget.layout.display = 'none' # refreshing options turns the display on, so turn it off.
        
        # reset values of custom ocn grid widgets (that aren't defined as ConfigVar instances)
        self.tbtn_ocn_mesh_mode.value = None
        self.read_ocn_mesh_file.value = None

        # reset all custom lnd grid vars
        for var in self.custom_lnd_grid_vars:
            var.value = None
        for var in self.custom_lnd_grid_vars:
            if var.has_options_spec():
                var.refresh_options()
                var.widget.layout.display = 'none' # refreshing options turns the display on, so turn it off.

        # reset values of custom lnd grid widgets (that aren't defined as ConfigVar instances)
        # reset fsurdat_in variables 
        self.fsurdat_in.value = ''
        self.fsurdat_out.value = ''
        self.lnd_idealized.value = None
        self.lnd_specify_area.value = None
        self.std_elev.value = ''
        self.max_sat_area.value = ''

    def turn_on(self):
        self.layout.display = ''
