import os
import logging
import ipywidgets as widgets
import subprocess
import time
import tempfile
import xarray as xr

from visualCaseGen.config_var import cvars
from visualCaseGen.OutHandler import handler as owh

from ipyfilechooser import FileChooser

logger = logging.getLogger(__name__)

button_width = '100px'
descr_width = '150px'

class CustomLndGridWidget(widgets.VBox):

    def __init__(self,ci,sdb):

        super().__init__()

        self.ci = ci
        self.sdb = sdb

        self._cvars = [\
            cvars['LND_DOM_PFT'],
            cvars['LND_SOIL_COLOR'],
            cvars['LND_MAX_SAT_AREA'],
            cvars['LND_STD_ELEV'],
        ]

        self._construct_clm_grid_selector()
        self._construct_clm_mesh_mask_modifier_widgets()
        self._construct_clm_fsurdat_widgets()
        self._construct_observances()


    def update_landmask_file_2(self, change):
        """To be used for syncing landmask_file and landmask_file2 widgets only within observances."""
        self.landmask_file_2.value = change['new']

    def refresh_lnd_specify_area(self, change):

        # First, handle the display of coordinate textboxes
        if change['new'] == 'via corner coords':
            self.lnd_lat_1.layout.display='flex'
            self.lnd_lat_2.layout.display='flex'
            self.lnd_lon_1.layout.display='flex'
            self.lnd_lon_2.layout.display='flex'
        elif change['new'] == 'via mask file' or change['new'] is None:
            self.lnd_lat_1.layout.display='none'
            self.lnd_lat_2.layout.display='none'
            self.lnd_lon_1.layout.display='none'
            self.lnd_lon_2.layout.display='none'
        else:
            raise RuntimeError(f"Unknown land specification selection {change['new']}")

        # Second, handle the display of landmask file textbox
        if change['new'] == 'via corner coords' or change['new'] is None:
            self.landmask_file_2.layout.display='none'
        elif change['new'] == 'via mask file':
            self.landmask_file_2.layout.display='flex'

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
                landmask_val = self.landmask_file.value
                self.landmask_file_2.value = landmask_val if landmask_val else ''
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
            new_mesh_path = self.ci.get_domain_properties(new_hgrid)['mesh']
            assert os.path.exists(new_mesh_path)
        except:
            new_mesh_path = ''
        if cvars['COMP_OCN'].value != "mom" and new_mesh_path:
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

        if new_fsurdat_in_path:
            self.fsurdat_in.value = new_fsurdat_in_path

    def _construct_observances(self):

        for widget in self._clm_mesh_mask_modifier_widgets_grp:
            widget.observe(
                self.refresh_btn_run_mesh_mask_modifier,
                names='value',
                type='change'
            )

        for widget in self._clm_fsurdat_widgets_grp1 + [self.landmask_file_2]:
            widget.observe(
                self.refresh_btn_run_fsurdat_modifier,
                names='value',
                type='change'
            )
        self.btn_run_mesh_mask_modifier.on_click(
            self.run_mesh_mask_modifier
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

        self.btn_run_fsurdat_modifier.on_click(
            self.run_fsurdat_modifier
        )

        self.landmask_file.observe(
            self.enable_preview_landmask,
            names='value',
            type='change'
        )

        self.btn_preview_landmask.on_click(
            self.preview_landmask
        )

        self.landmask_file_2.observe(
            self.enable_preview_mod_lnd_props,
            names='value',
            type='change'
        )

        self.btn_preview_mod_lnd_props.on_click(
            self.preview_mod_lnd_props
        )

    def enable_preview_landmask(self, change):
        new_landmask_path = change['new']

        self.out_preview_landmask.clear_output()
        if new_landmask_path not in ['', None] and os.path.exists(new_landmask_path):
            self.btn_preview_landmask.layout.display = 'flex'
        else:
            self.btn_preview_landmask.layout.display = 'none'

    def enable_preview_mod_lnd_props(self, change):
        landmask_path_2 = change['new']

        self.out_preview_mod_lnd_props.clear_output()
        if landmask_path_2 not in ['', None] and os.path.exists(landmask_path_2):
            self.btn_preview_mod_lnd_props.layout.display = 'flex'
        else:
            self.btn_preview_mod_lnd_props.layout.display = 'none'

    def preview_landmask(self, b):
        self.btn_preview_landmask.layout.display = 'none'
        landmask_path = self.landmask_file.value
        with self.out_preview_landmask:
            if landmask_path in ['', None] or not os.path.exists(landmask_path):
                print("ERROR: couldn't find the landmask file.")
                return
            ds = xr.open_dataset(landmask_path)
            fieldname = 'landmask'
            if fieldname not in ds:
                print(f"ERROR: couldn't find the '{fieldname}' field in {landmask_path}.")
                return
            import matplotlib.pyplot as plt
            im = plt.imshow(ds[fieldname].data)
            plt.gca().invert_yaxis()
            plt.colorbar(im, fraction=0.025)
            plt.show()

    def preview_mod_lnd_props(self, b):
        self.btn_preview_mod_lnd_props.layout.display = 'none'
        landmask_path_2 = self.landmask_file_2.value
        with self.out_preview_mod_lnd_props:
            if landmask_path_2 in ['', None] or not os.path.exists(landmask_path_2):
                print("ERROR: couldn't find the landmask file.")
                return
            ds = xr.open_dataset(landmask_path_2)
            fieldname = 'mod_lnd_props'
            if fieldname not in ds:
                print(f"ERROR: couldn't find the '{fieldname}' field in {landmask_path_2}.")
                return
            import matplotlib.pyplot as plt
            im = plt.imshow(ds[fieldname].data)
            plt.gca().invert_yaxis()
            plt.colorbar(im, fraction=0.025)
            plt.show()

    def refresh_btn_run_mesh_mask_modifier(self, change):
        if any([var.value in [None, ''] for var in self._clm_mesh_mask_modifier_widgets_grp ]):
            self.btn_run_mesh_mask_modifier.disabled = True
        else:
            self.btn_run_mesh_mask_modifier.disabled = False

    def refresh_btn_run_fsurdat_modifier(self, change):
        if all(var.value not in [None, ''] for var in self._clm_fsurdat_widgets_grp1) and \
            (   self.lnd_specify_area.value == 'via corner coords' or
                (self.lnd_specify_area.value == 'via mask file' and self.landmask_file_2.value not in [None, ''])
            ):
            self.btn_run_fsurdat_modifier.disabled = False
        else:
            self.btn_run_fsurdat_modifier.disabled = True

    @owh.out.capture()
    def run_mesh_mask_modifier(self, b):

        self.btn_run_mesh_mask_modifier.disabled = True

        mesh_mask_modifier_path = os.path.join(self.ci.srcroot,
            "components","clm","tools","modify_input_files","mesh_mask_modifier")

        if not os.path.exists(mesh_mask_modifier_path):
            raise RuntimeError("Cannot find mesh_mask_modifier tool!!!")

        cfg = tempfile.NamedTemporaryFile(mode="w") # create a temp file
        cfg_ = open(cfg.name, 'w') # open it
        cfg_.write(
            f"""
            [modify_input]
            mesh_mask_in = {self.mesh_mask_in.value}
            mesh_mask_out = {self.mesh_mask_out.value}
            landmask_file = {self.landmask_file.value}
            lat_dimname = {self.lat_dimname.value}
            lon_dimname = {self.lon_dimname.value}
            lat_varname = {self.lat_varname.value}
            lon_varname = {self.lon_varname.value}
            """
        )
        cfg_.close()

        proc = subprocess.Popen(
            f"{mesh_mask_modifier_path} {cfg.name}",
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True)

        self.mesh_mask_modifier_output.layout.border = '1px solid silver'
        with self.mesh_mask_modifier_output:
            print("Running mesh_mask_modifier. This may take a while.")
            print("Please wait!")
            while proc.poll() is None:
                time.sleep(1)
                print('.', end='')

            stdout, stderr = proc.communicate()

            print("\nDone.")
            if stdout:
                print(stdout)
            if stderr:
                if os.path.exists(self.mesh_mask_out.value):
                    print(f"The mask mesh file has been created at {self.mesh_mask_out.value},"
                          " but the process encountered the following error/warning messages:")
                else:
                    print("ERROR: couldn't generate the mask mesh file!")
                print(stderr)
            elif os.path.exists(self.mesh_mask_out.value):
                print(f"The output mesh mask file was successfully generated at {self.mesh_mask_out.value}")

        # record mesh_mask_modifier settings that will be needed by the create case widget
        self.sdb.update({'mesh_mask_modifier':{
            'mesh_mask_in' : self.mesh_mask_in.value,
            'mesh_mask_out' : self.mesh_mask_out.value
        }})

        # Clean up
        self.mesh_mask_modifier_output.layout.border = ''
        cfg.close() # remove the temp file
        self.btn_run_mesh_mask_modifier.disabled = False

    @owh.out.capture()
    def run_fsurdat_modifier(self, b):

        self.btn_run_fsurdat_modifier.disabled = True

        fsurdat_modifier_path = os.path.join(self.ci.srcroot,
            "components","clm","tools","modify_input_files","fsurdat_modifier")

        if not os.path.exists(fsurdat_modifier_path):
            raise RuntimeError("Cannot find fsurdat_modifier tool!!!")

        cfg = tempfile.NamedTemporaryFile(mode="w",
            delete=False) # todo: set delete tu True
        cfg_ = open(cfg.name, 'w') # open it


        lai_str = ' '.join(str(w.value) for w in self.lai_widgets)
        sai_str = ' '.join(str(w.value) for w in self.sai_widgets)
        hgt_top_str = ' '.join(str(w.value) for w in self.hgt_top_widgets)
        hgt_bot_str = ' '.join(str(w.value) for w in self.hgt_bot_widgets)

        set_val = lambda val : str(val) if val not in [None, ''] else 'UNSET'

        write_str = f"""
            [modify_fsurdat_basic_options]
            fsurdat_in = {self.fsurdat_in.value}
            fsurdat_out = {self.fsurdat_out.value}
            idealized = {self.lnd_idealized.value}
            process_subgrid_section = False
            process_var_list_section = False
            lnd_lat_1 = {self.lnd_lat_1.value}
            lnd_lat_2 = {self.lnd_lat_2.value}
            lnd_lon_1 = {self.lnd_lon_1.value}
            lnd_lon_2 = {self.lnd_lon_2.value}
            landmask_file = {set_val(self.landmask_file_2.value)}
            lat_dimname = UNSET
            lon_dimname = UNSET
            dom_pft = {set_val(self.lnd_dom_pft.value)}
            evenly_split_cropland = False
            lai = {lai_str}
            sai = {sai_str}
            hgt_top = {hgt_top_str}
            hgt_bot = {hgt_bot_str}
            soil_color = {set_val(self.lnd_soil_color.value)}
            std_elev = {set_val(self.std_elev.value)}
            max_sat_area = {set_val(self.max_sat_area.value)}
            include_nonveg = {self.include_nonveg.value}

        """

        cfg_.write(write_str)
        cfg_.close()

        proc = subprocess.Popen(
            f"{fsurdat_modifier_path} {cfg.name}",
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True)

        self.fsurdat_output.layout.border = '1px solid silver'
        with self.fsurdat_output:
            print("Running fsurdat_modifier. This may take a while.")
            print("Please wait!")
            while proc.poll() is None:
                time.sleep(1)
                print('.', end='')

            stdout, stderr = proc.communicate()

            print("\nDone.")
            if stdout:
                print(stdout)
            if stderr:
                if os.path.exists(self.fsurdat_out.value):
                    print(f"The fsurdat output file has been created at {self.fsurdat_out.value},"
                          " but the process encountered the following error/warning messages:")
                else:
                    print("ERROR: couldn't generate the fsurdat file!")
                print(stderr)
            elif os.path.exists(self.fsurdat_out.value):
                print(f"The output fsurdat file was successfully generated at {self.fsurdat_out.value}")

        # record fsurdat_modifier settings that will be needed by the create case widget
        self.sdb.update({'fsurdat_modifier':{
            'fsurdat_out': self.fsurdat_out.value
        }})

        # Clean up
        self.fsurdat_out.layout.border = ''
        cfg.close() # remove the temp file
        self.btn_run_fsurdat_modifier.disabled = False

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

        self.mesh_mask_in = FileChooser(
            path=os.getcwd(),
            filename='',
            title='<b>Input Mask Mesh:</b>',
            show_hidden=True,
            select_default=True,
            show_only_dirs=False,
            filter_pattern="*.nc",
            existing_only=True,
            layout=widgets.Layout(width='700px', padding='10px')
        )

        self.landmask_file = FileChooser(
            path=os.getcwd(),
            filename='',
            title='<b>Land mask (pre-generated by user):</b>',
            show_hidden=True,
            select_default=True,
            show_only_dirs=False,
            filter_pattern="*.nc",
            existing_only=True,
            layout=widgets.Layout(width='700px', padding='10px')
        )

        self.btn_preview_landmask = widgets.Button(
            description = 'Preview landmask',
            tooltip = "Click this button to preview the landmask field.",
            #icon = 'magnifying-glass',
            layout=widgets.Layout(display='none', left='50px'),
        )

        self.out_preview_landmask = widgets.Output()

        self.lat_varname = widgets.Textarea(
            value='lsmlat',
            description='<b>Latitude var. name:</b>',
            description_allow_html=True,
            layout=widgets.Layout(height='40px', width='600px')
        )
        self.lat_varname.style.description_width = descr_width

        self.lon_varname = widgets.Textarea(
            value='lsmlon',
            description='<b>Longitude var. name:</b>',
            description_allow_html=True,
            layout=widgets.Layout(height='40px', width='600px')
        )
        self.lon_varname.style.description_width = descr_width

        self.lat_dimname = widgets.Textarea(
            value='lsmlat',
            description='<b>Latitude dim. name:</b>',
            description_allow_html=True,
            layout=widgets.Layout(height='40px', width='600px')
        )
        self.lat_dimname.style.description_width = descr_width

        self.lon_dimname = widgets.Textarea(
            value='lsmlon',
            description='<b>Longitude dim. name:</b>',
            description_allow_html=True,
            layout=widgets.Layout(height='40px', width='600px')
        )
        self.lon_dimname.style.description_width = descr_width

        self.mesh_mask_out = FileChooser(
            path=os.getcwd(),
            filename='',
            title='<b>Output mask mesh:</b>',
            show_hidden=True,
            select_default=True,
            show_only_dirs=False,
            filter_pattern="*.nc",
            new_only=True,
            layout=widgets.Layout(width='700px', padding='10px')
        )

        self.btn_run_mesh_mask_modifier = widgets.Button(
            description = 'Run mesh_mask_modifier',
            disabled = True,
            tooltip = "When ready, click this button to run the mesh_mask_modifier tool.",
            icon = 'terminal',
            button_style='success', # 'success', 'info', 'warning', 'danger' or ''
            layout=widgets.Layout(width='250px', align_items='center'),
        )

        self.mesh_mask_modifier_output = widgets.Output(
            layout={'border': '1px solid silver'}
        )

        self._clm_mesh_mask_modifier_widgets_grp = [
            self.mesh_mask_in,
            self.landmask_file,
            self.lat_varname,
            self.lon_varname,
            self.lat_dimname,
            self.lon_dimname,
            self.mesh_mask_out,
        ]

        self._clm_mesh_mask_modifier_widgets = widgets.VBox([
            self.mesh_mask_in,
            self.landmask_file,
            self.btn_preview_landmask,
            self.out_preview_landmask,
            self.lat_varname,
            self.lon_varname,
            self.lat_dimname,
            self.lon_dimname,
            self.mesh_mask_out,
        ],
        layout={'padding':'5px','display':'flex','flex_flow':'column','align_items':'flex-start'})

    def _construct_clm_fsurdat_widgets(self):

        self.fsurdat_in = FileChooser(
            path=os.getcwd(),
            filename='',
            title='<b>Input Surface Dataset:</b>',
            show_hidden=True,
            select_default=True,
            show_only_dirs=False,
            filter_pattern="*.nc",
            existing_only=True,
            layout=widgets.Layout(width='700px', padding='10px')
        )

        self.fsurdat_out = FileChooser(
            path=os.getcwd(),
            filename='',
            title='<b>Output Surface Dataset:</b>',
            show_hidden=True,
            select_default=True,
            show_only_dirs=False,
            filter_pattern="*.nc",
            new_only=True,
            layout=widgets.Layout(width='700px', padding='10px')
        )

        self.lnd_idealized = widgets.ToggleButtons(
            description='Idealized?',
            options=['True', 'False'],
            value='False',
            layout={'display':'flex','width':'max-content'}, # If the items' names are long
            disabled=False
        )
        self.lnd_idealized.style.description_width = '180px'
        self.lnd_idealized.style.button_width = '200px'

        self.lnd_specify_area = widgets.ToggleButtons(
            description='Specify area of customization',
            options=['via corner coords', 'via mask file'],
            value=None,
            layout={'display':'flex','width':'max-content'}, # If the items' names are long
            disabled=False
        )
        self.lnd_specify_area.style.description_width = '180px'
        self.lnd_specify_area.style.button_width = '200px'

        self.lnd_lat_1= widgets.FloatText(
            -90.0,
            description='Southernmost latitude for rectangle:',
            layout={'display':'none', 'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        self.lnd_lat_1.style.description_width = '300px'

        self.lnd_lat_2 = widgets.FloatText(
            90.0,
            description='Northernmost latitude for rectangle:',
            layout={'display':'none', 'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        self.lnd_lat_2.style.description_width = '300px'

        self.lnd_lon_1 = widgets.FloatText(
            0.0,
            description='Westernmost longitude for rectangle:',
            layout={'display':'none', 'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        self.lnd_lon_1.style.description_width = '300px'

        self.lnd_lon_2 = widgets.FloatText(
            360.0,
            description='Easternmost longitude for rectangle:',
            layout={'display':'none', 'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        self.lnd_lon_2.style.description_width = '300px'

        # this is a dubplicate of self.landmask_file if mesh_mask_modifier section is on:
        self.landmask_file_2 = widgets.Textarea(
            value='',
            placeholder='Type a new path',
            description='Land mask (by user):',
            layout=widgets.Layout(display='none',height='40px', width='600px'),
        )
        self.landmask_file_2.style.description_width = descr_width

        self.btn_preview_mod_lnd_props = widgets.Button(
            description = 'Preview mod_lnd_props',
            tooltip = "Click this button to preview the mod_lnd_props field.",
            layout=widgets.Layout(display='none', left='50px'),
        )

        self.out_preview_mod_lnd_props = widgets.Output()

        self.lnd_dom_pft = cvars['LND_DOM_PFT']
        self.lnd_dom_pft.widget = widgets.Text(
            description='PFT/CFT',
            layout={'display':'flex', 'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        self.lnd_dom_pft.widget.style.description_width = '200px'

        self.lnd_soil_color = cvars['LND_SOIL_COLOR']
        self.lnd_soil_color.widget = widgets.Text(
            description='Soil color (between 0-20)',
            layout={'display':'flex', 'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        self.lnd_soil_color.widget.style.description_width = '200px'

        self.std_elev = cvars['LND_STD_ELEV']
        self.std_elev.widget = widgets.Text(
            description='Std. dev. of elevation',
            layout={'display':'flex', 'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        self.std_elev.widget.style.description_width = '200px'

        self.max_sat_area = cvars['LND_MAX_SAT_AREA']
        self.max_sat_area.widget = widgets.Text(
            description='Max fraction of saturated area',
            layout={'display':'flex', 'width': 'max-content'}, # If the items' names are long
            disabled=False
        )
        self.max_sat_area.widget.style.description_width = '200px'

        self.include_nonveg = widgets.ToggleButtons(
            description='Include non-vegetation land units?',
            options=['True', 'False'],
            tooltips=['landunits unchanged if True', 'landunits set to 0 if False'],
            value='True',
            layout={'display':'flex','width':'max-content'}, # If the items' names are long
            disabled=False
        )
        self.include_nonveg.style.description_width = '180px'
        self.include_nonveg.style.button_width = '200px'

        cw = '50px'
        gridbox_items = [widgets.Label(label, layout=widgets.Layout(width=cw)) for label in \
            ['var.', 'Jan.', 'Feb.', 'Mar.', 'Apr.', 'May.', 'Jun.', 'Jul.', 'Aug.', 'Sep.', 'Oct.', 'Nov.', 'Dec.']]

        self.lai_widgets = [widgets.FloatText('3',layout=widgets.Layout(width=cw)) for i in range(12)]
        gridbox_items.append(widgets.Label('LAI', layout=widgets.Layout(width=cw)))
        gridbox_items.extend(self.lai_widgets)

        self.sai_widgets = [widgets.FloatText('1',layout=widgets.Layout(width=cw)) for i in range(12)]
        gridbox_items.append(widgets.Label('SAI', layout=widgets.Layout(width=cw)))
        gridbox_items.extend(self.sai_widgets)

        self.hgt_top_widgets = [widgets.FloatText('1',layout=widgets.Layout(width=cw)) for i in range(12)]
        gridbox_items.append(widgets.Label('hgt_top', layout=widgets.Layout(width=cw)))
        gridbox_items.extend(self.hgt_top_widgets)

        self.hgt_bot_widgets = [widgets.FloatText('0.5',layout=widgets.Layout(width=cw)) for i in range(12)]
        gridbox_items.append(widgets.Label('hgt_bot', layout=widgets.Layout(width=cw)))
        gridbox_items.extend(self.hgt_bot_widgets)

        self.fsurdat_gridbox = widgets.GridBox(gridbox_items,
            layout=widgets.Layout(grid_template_columns=f"repeat(13, {cw})",width='665px',padding='5px'))

        self.btn_run_fsurdat_modifier = widgets.Button(
            description = 'Run fsurdat_modifier',
            disabled = True,
            tooltip = "When ready, click this button to run the fsurdat_modifier tool.",
            icon = 'terminal',
            button_style='success', # 'success', 'info', 'warning', 'danger' or ''
            layout=widgets.Layout(width='250px', align_items='center'),
        )

        self.fsurdat_output = widgets.Output(
            layout={'border': '1px solid silver'}
        )

        self._clm_fsurdat_widgets = widgets.VBox([
            self.fsurdat_in,
            self.lnd_specify_area,
            self.lnd_lat_1,
            self.lnd_lat_2,
            self.lnd_lon_1,
            self.lnd_lon_2,
            self.landmask_file_2,
            self.btn_preview_mod_lnd_props,
            self.out_preview_mod_lnd_props,
            self.lnd_idealized,
            self.lnd_dom_pft.widget,
            self.lnd_soil_color.widget,
            self.std_elev.widget,
            self.max_sat_area.widget,
            self.include_nonveg,
            self.fsurdat_gridbox,
            self.fsurdat_out,
            self.fsurdat_output
        ])

        # these must all be set for the run fsurdat button to be enabled
        self._clm_fsurdat_widgets_grp1 = [
            self.fsurdat_in,
            self.fsurdat_out,
            self.lnd_idealized,
            self.lnd_specify_area,
            #self.lnd_dom_pft.widget,
            #self.lnd_soil_color.widget,
            #self.std_elev,
            #self.max_sat_area,
            self.include_nonveg
        ]

    def reset_vars(self):

        # reset all custom lnd grid vars
        for var in self._cvars:
            var.value = None
        for var in self._cvars:
            if var.has_options_spec():
                display = var.widget.layout.display
                var.refresh_options()
                var.widget.layout.display = display # refreshing options turns the display on,
                                                    # so turn it off if it was turned off.

        # reset clm grid selector
        self.drp_clm_grid.value = None

        # reset mesh mask modifier widgets (that aren't defined as ConfigVar instances)
        self.mesh_mask_in.reset()
        self.landmask_file.reset()
        self.lat_varname.value = 'lsmlat'
        self.lon_varname.value = 'lsmlon'
        self.lat_dimname.value = 'lsmlat'
        self.lon_dimname.value = 'lsmlon'
        self.mesh_mask_out.reset()

        # reset values of custom lnd grid widgets (that aren't defined as ConfigVar instances)
        # reset fsurdat_in variables
        self.fsurdat_in.reset()
        self.fsurdat_out.reset()
        self.lnd_idealized.value = 'False'
        self.lnd_specify_area.value = None
        self.lnd_lat_1.value = -90.0
        self.lnd_lat_2.value = 90.0
        self.lnd_lon_1.value = 0.0
        self.lnd_lon_2.value = 360.0
        self.landmask_file_2.value = ''
        self.landmask_file_2.disabled = False
        self.include_nonveg.value = 'True'

    def construct(self):

        comp_ocn = cvars['COMP_OCN'].value
        comp_lnd = cvars['COMP_LND'].value

        children = []

        if comp_lnd == "clm":
            self.title = "CLM Grid..."

            children.append(
                widgets.HTML(
                    value=" <b>Base CLM grid</b><br> Select a base land grid from the following menu. You can then customize its fsurdat specification in the below dialogs.",
                )
            )

            children.append(self.drp_clm_grid)

            if comp_ocn != "mom":
                children.append(widgets.HTML('<hr>')) # horizontal line

                children.append(
                    widgets.HTML(
                        value=""" <b>mesh_mask_modifier</b><br>
                            No active ocean component is selected, so the mesh_mask_modifier tool must be utilized. Fill in the 
                            below fields to configure the mesh_mask modifier tool. Note that the input mask mesh will be 
                            auto-filled to a default mesh path (if found), but the land mask file is user-generated and so its
                            path must be provided by the user. Lat/Lon variable and dimension names should correspond to what is 
                            found in the land mask file. See the following link for instructions for how to find a default land mask:
                            <a href="https://www.cesm.ucar.edu/models/simple/coupled/land" target="_blank" rel="noreferrer noopener"><u>https://www.cesm.ucar.edu/models/simple/coupled/land</u></a> <br>
                            """
                    )
                )

                children.append(self._clm_mesh_mask_modifier_widgets)
                children.append(self.btn_run_mesh_mask_modifier)
                children.append(self.mesh_mask_modifier_output)

            children.append(widgets.HTML('<hr>')) # horizontal line
            children.append(
                widgets.HTML(
                    value=" <b>fsurdat_modifier</b><br> Set the following configuration variables to determine the CLM surface dataset.",
                )
            )

            children.append(self._clm_fsurdat_widgets)
            children.append(self.btn_run_fsurdat_modifier)

        elif comp_lnd in ['dlnd', 'slnd']:
            self.title = "NotImplemented"
            pass

        else:
            self.title = "ERROR"
            children = [widgets.Label(f"ERROR: unsupported lnd component {comp_lnd} for custom grid feature")]


        self.children = children