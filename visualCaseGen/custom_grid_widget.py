import os
import re
import logging
import ipywidgets as widgets
import nbformat as nbf
from datetime import datetime
from IPython.display import display, Javascript

from visualCaseGen.config_var import cvars
from visualCaseGen.save_custom_grid_widget import SaveCustomGrid
from visualCaseGen.read_mesh_file import ReadMeshFile
from visualCaseGen.custom_ocn_grid import CustomOcnGrid
from visualCaseGen.OutHandler import handler as owh

logger = logging.getLogger(__name__)

button_width = '100px'
descr_width = '140px'

class CustomGridWidget(widgets.Tab):

    def __init__(self,ci,layout=widgets.Layout()):

        super().__init__(layout=layout)

        self.ci = ci

        self.description = widgets.HTML(
            "<p style='text-align:left'>In custom grid mode, you can "
            "create new grids for the ocean and/or the land components "
            "by setting the below configuration variables. After having "
            "set all the variables, you can save grid configuration "
            "files to be read in by subsequent tools to further "
            "customize and complete the grids.</p>"
        )

        self._custom_ocn_grid= CustomOcnGrid(self.ci)

        self.custom_lnd_grid_vars = [\
            cvars['LND_LAT_1'],
            cvars['LND_LAT_2'],
            cvars['LND_LON_1'],
            cvars['LND_LON_2'],
            cvars['LND_DOM_PFT'],
            cvars['LND_SOIL_COLOR'],
        ]

        self.horiz_line = widgets.HTML('<hr>')

        self._construct_clm_grid_selector()
        self._construct_clm_mesh_mask_modifier_widgets()
        self._construct_clm_fsurdat_widgets()

        self.construct_observances()
        self.layout.width = '750px'

        self.turn_off() # by default, the display is off.
        self.refresh_display()

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

            ocn_tab = () # first item is tab title, second item is list of widgets
            lnd_tab = () # first item is tab title, second item is list of widgets

            # construct the ocean grid section layout
            if ocn == "mom":
                ocn_tab = ("MOM6 Grid", [self._custom_ocn_grid._mom6_widgets])
            elif ocn in ['docn', 'socn']:
                pass
            else:
                ocn_tab = (
                    "ERROR",
                    [widgets.Label(f"ERROR: unsupported ocn component {ocn} for custom grid feature")]
                )

            if lnd == "clm":

                lnd_tab = ("CLM Grid", [])

                lnd_tab[1].append(
                    widgets.HTML(
                        value=" <b>Base CLM grid</b><br> Select a base land grid from the following menu. You can then customize its fsurdat specification in the below dialogs.",
                    )
                )
                lnd_tab[1].append(
                    self.drp_clm_grid
                )

                if ocn != "mom":
                    lnd_tab[1].append(self.horiz_line)
                    lnd_tab[1].append(
                        widgets.HTML(
                            value=" <b>mesh_mask_modifier</b><br>"
                                "No active ocean component is selected, so the "
                                "mesh_mask_modifier tool must be utilized. Fill in the "
                                "below fields to configure the mesh_mask modifier tool. "
                                "Note that the input mask mesh will be auto-filled to a "
                                "default mesh path (if found), but the land mask file is user-generated "
                                "and so its path must be provided by the user. Lat/Lon variable "
                                "and dimension names should correspond to what is found in the "
                                "land mask file."
                        )
                    )
                    lnd_tab[1].append(self._clm_mesh_mask_modifier_widgets)
                    lnd_tab[1].append(self.btn_run_mesh_mask_modifier)

                lnd_tab[1].append(self.horiz_line)
                lnd_tab[1].append(
                    widgets.HTML(
                        value=" <b>fsurdat_modifier</b><br> Set the following configuration variables to determine the CLM surface dataset.",
                    )
                )
                lnd_tab[1].append(self._clm_fsurdat_widgets)

                lnd_tab[1].append(
                    widgets.Button(
                        description = 'Save .cfg files',
                        #disabled = True,
                        tooltip = "When ready, click this button to save the .cfg files for subsequent execution of land tools.",
                        #icon = 'terminal',
                        button_style='success', # 'success', 'info', 'warning', 'danger' or ''
                        #layout=widgets.Layout(display='none', width='170px', align_items='center'),
                    )
                )

            elif lnd in ['dlnd', 'slnd']:
                pass
            else:
                lnd_tab = (
                    "ERROR",
                    [widgets.Label(f"ERROR: unsupported ocn component {ocn} for custom grid feature")]
                )

            self.children = [widgets.VBox(tab[1]) for tab in [ocn_tab, lnd_tab] if len(tab)>0]
            for i, tab in enumerate([tab for tab in [ocn_tab, lnd_tab] if len(tab)>0]):
                self.set_title(i,tab[0])

            self.reset_vars()

    def update_landmask_file_2(self, change):
        """To be used for syncing landmask_file and landmask_file2 widgets only within observances."""
        self.landmask_file_2.value = change['new']

    def refresh_lnd_specify_area(self, change):

        # First, handle the display of coordinate textboxes
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

        # Second, handle the display of landmask file textbox
        if change['new'] == 'via corner coords' or change['new'] is None:
            self.landmask_file_2.layout.display='none'
        elif change['new'] == 'via mask file':
            self.landmask_file_2.layout.display=''

            if cvars['COMP_OCN'].value == "mom":
                # decouple landmask_file and landmask_file2 and reset landmask_file2 value
                if 'value' in self.landmask_file._trait_notifiers and 'change' in self.landmask_file._trait_notifiers['value'] and\
                self.update_landmask_file_2 in self.landmask_file._trait_notifiers['value']['change']:
                    self.landmask_file.unobserve(
                        self.update_landmask_file_2,
                        names='value',
                        type='change'
                    )
                self.landmask_file_2.value = ''
                self.landmask_file_2.disabled = False
                self.landmask_file_2.placeholder = "Type a new path."
            
            else:
                # couple landmask_file and landmask_file2 and reset landmask_file2 value
                self.landmask_file_2.value = self.landmask_file.value
                self.landmask_file_2.disabled = True
                self.landmask_file_2.placeholder = "Auto-filled from mesh_mask_modifier"
                self.landmask_file.observe(
                    self.update_landmask_file_2,
                    names='value',
                    type='change'
                )
        else:
            raise RuntimeError(f"Unknown land specification selection {change['new']}")

    def update_clm_grid_options(self, change):
        new_inittime = change['new']

        if new_inittime not in [None, '1850', '2000']:
            raise RuntimeError("Unsupported INITTIME for custom clm grid options")

        self.drp_clm_grid.options = list(self.ci.clm_fsurdat[new_inittime].keys())


    def clm_grid_value_changed(self, change):
        new_hgrid = change['new']
        cv_inittime = cvars['INITTIME']

        ## Auto-fill mask mesh
        new_mesh_path = ''
        try:
            new_mesh_path = self.ci.retrieve_mesh_path(new_hgrid)
            assert os.path.exists(new_mesh_path)
        except:
            new_mesh_path = ''
        if cvars['COMP_OCN'].value != "mom":
            self.mesh_mask_in.value = new_mesh_path

        ## Auto-fill fsurdat_in:
        new_fsurdat_in_path = ''
        try:
            new_fsurdat_in_path = os.path.join(
                self.ci.din_loc_root,
                self.ci.clm_fsurdat[cv_inittime.value][new_hgrid].strip()
            )
            assert os.path.exists(new_fsurdat_in_path)
        except:
            new_fsurdat_in_path = ''
        self.fsurdat_in.value = new_fsurdat_in_path

    def construct_observances(self):

        cv_comp_ocn = cvars['COMP_OCN']
        cv_comp_ocn.observe(
            self.refresh_display,
            names='value',
            type='change'
        )

        for widget in self._clm_mesh_mask_modifier_widgets.children:
            widget.observe(
                self.refresh_btn_run_mesh_mask_modifier,
                names='value',
                type='change'
            )
        
        self.btn_run_mesh_mask_modifier.on_click(
            self.run_mesh_mask_modifier
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

        cv_inittime = cvars['INITTIME']
        cv_inittime.observe(
            self.update_clm_grid_options,
            names='value',
            type='change'
        )

        self.drp_clm_grid.observe(
            self.clm_grid_value_changed,
            names='value',
            type='change'
        )


    def refresh_btn_run_mesh_mask_modifier(self, change):
        if any([var.value in [None, ''] for var in self._clm_mesh_mask_modifier_widgets.children ]):
            self.btn_run_mesh_mask_modifier.disabled = True
        else:
            self.btn_run_mesh_mask_modifier.disabled = False

    @owh.out.capture()
    def run_mesh_mask_modifier(self, b):
        pass # TODO

    def _construct_clm_grid_selector(self):

        cv_inittime = cvars['INITTIME']
        if cv_inittime.value not in [None, '1850', '2000']:
            raise RuntimeError(f"Unsupported INITTIME {cv_inittime.value} for custom clm grid options")

        self.drp_clm_grid = widgets.Dropdown(
            options = list(self.ci.clm_fsurdat[cv_inittime.value].keys()),
            description='Base CLM grid:',
            disabled=False,
        )
        self.drp_clm_grid.style.description_width = '100px'

    def _construct_clm_mesh_mask_modifier_widgets(self):

        self.mesh_mask_in = widgets.Textarea(
            value='',
            placeholder='Type an existing mask mesh directory',
            description='Input mask mesh:',
            layout=widgets.Layout(height='40px', width='600px')
        )
        self.mesh_mask_in.style.description_width = descr_width

        self.landmask_file = widgets.Textarea(
            value='',
            placeholder='Type a new path',
            description='Land mask (by user):',
            layout=widgets.Layout(height='40px', width='600px')
        )
        self.landmask_file.style.description_width = descr_width

        self.lat_varname = widgets.Textarea(
            value='lsmlat',
            description='Latitude var. name',
            layout=widgets.Layout(height='40px', width='600px')
        )
        self.lat_varname.style.description_width = descr_width

        self.lon_varname = widgets.Textarea(
            value='lsmlon',
            description='Longitude var. name',
            layout=widgets.Layout(height='40px', width='600px')
        )
        self.lon_varname.style.description_width = descr_width

        self.lat_dimname = widgets.Textarea(
            value='lsmlat',
            description='Latitude dim. name',
            layout=widgets.Layout(height='40px', width='600px')
        )
        self.lat_dimname.style.description_width = descr_width

        self.lon_dimname = widgets.Textarea(
            value='lsmlon',
            description='Longitude dim. name',
            layout=widgets.Layout(height='40px', width='600px')
        )
        self.lon_dimname.style.description_width = descr_width

        self.mesh_mask_out = widgets.Textarea(
            value='',
            placeholder='Type a new path',
            description='Output mask mesh:',
            layout=widgets.Layout(height='40px', width='600px')
        )
        self.mesh_mask_out.style.description_width = descr_width

        self.btn_run_mesh_mask_modifier = widgets.Button(
            description = 'Run mesh_mask_modifier',
            disabled = True,
            tooltip = "When ready, click this button to run the mesh_mask_modifier tool.",
            icon = 'terminal',
            button_style='success', # 'success', 'info', 'warning', 'danger' or ''
            layout=widgets.Layout(width='250px', align_items='center'),
        )

        self._clm_mesh_mask_modifier_widgets = widgets.VBox([
            self.mesh_mask_in,
            self.landmask_file,
            self.lat_varname,
            self.lon_varname,
            self.lat_dimname,
            self.lon_dimname,
            self.mesh_mask_out,
        ],
        layout={'padding':'15px','display':'flex','flex_flow':'column','align_items':'flex-start'})

    def _construct_clm_fsurdat_widgets(self):

        self.fsurdat_in = widgets.Textarea(
            value='',
            placeholder='Type fsurdat input file ',
            description='Input surface dataset',
            layout=widgets.Layout(height='80px', width='600px')
        )
        self.fsurdat_in.style.description_width = '180px'

        self.fsurdat_out = widgets.Textarea(
            value='',
            placeholder='Type fsurdat output file ',
            description='Output surface dataset',
            layout=widgets.Layout(height='80px', width='600px')
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

        # this is a dubplicate of self.landmask_file if mesh_mask_modifier section is on:
        self.landmask_file_2 = widgets.Textarea(
            value='',
            placeholder='Type a new path',
            description='Land mask (by user):',
            layout=widgets.Layout(display='none',height='40px', width='600px'),
        )
        self.landmask_file_2.style.description_width = descr_width

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
            self.landmask_file_2,
            widgets.Label(''),
            lnd_dom_pft.widget,
            lnd_soil_color.widget,
            self.std_elev,
            self.max_sat_area,
            self.include_nonveg,
        ],
        layout={'padding':'15px','display':'flex','flex_flow':'column','align_items':'flex-start'})

    def reset_vars(self):

        # reset all custom lnd grid vars
        for var in self.custom_lnd_grid_vars:
            var.value = None
        for var in self.custom_lnd_grid_vars:
            if var.has_options_spec():
                display = var.widget.layout.display
                var.refresh_options()
                var.widget.layout.display = display # refreshing options turns the display on,
                                                    # so turn it off if it was turned off.
        
        # reset clm grid selector
        self.drp_clm_grid.value = None

        # reset mesh mask modifier widgets (that aren't defined as ConfigVar instances)
        self.mesh_mask_in.value = ''
        self.landmask_file.value = ''
        self.lat_varname.value = 'lsmlat'
        self.lon_varname.value = 'lsmlon'
        self.lat_dimname.value = 'lsmlat'
        self.lon_dimname.value = 'lsmlon'
        self.mesh_mask_out.value = ''

        # reset values of custom lnd grid widgets (that aren't defined as ConfigVar instances)
        # reset fsurdat_in variables
        self.fsurdat_in.value = ''
        self.fsurdat_out.value = ''
        self.lnd_idealized.value = None
        self.lnd_specify_area.value = None
        self.landmask_file_2.value = ''
        self.landmask_file_2.disabled = False
        self.std_elev.value = ''
        self.max_sat_area.value = ''

    def turn_off(self):
        self.layout.display = 'none'
        self._custom_ocn_grid.reset_vars()
        self.reset_vars()

    def turn_on(self):
        self.layout.display = ''
