import os
import re
from pathlib import Path
import subprocess
import ipywidgets as widgets
from datetime import datetime

os.environ['NUMEXPR_MAX_THREADS'] = '8'
import xarray as xr

class ReadMeshFile(widgets.VBox):

    def __init__(self, comp_name, layout=widgets.Layout()):

        super().__init__(layout=layout)

        self._comp_name = comp_name

        self.filepath = widgets.Textarea(
            value='',
            placeholder='Type an existing mesh file path',
            description=f'Path to {comp_name} mesh file:',
            layout=widgets.Layout(height='40px', width='600px')
        )
        self.filepath.style.description_width = '180px'

        self.filepath_validity = widgets.Valid(
            value=False,
            readout="Type an existing directory!",
            layout=widgets.Layout(width='400px')
            )

        self.output = widgets.Output(
            layout={'border': '1px solid silver'}
        )

        self.children = [self.filepath,
                         widgets.HBox([self.filepath_validity],
                                     layout= widgets.Layout(display='flex',justify_content='flex-end')),
                         self.output
                        ]

        self.filepath.observe(
            self._on_filepath_change,
            names = 'value',
            type = 'change'
            )


    def _on_filepath_change(self, change):
        new_filepath_in = change['new'].strip()
        is_valid_path = False
        self.output.clear_output()

        if new_filepath_in == '':
            self.filepath_validity.readout = "Enter a valid mesh path"
        else:

            # obtain the absolute path
            if os.path.isabs(new_filepath_in):
                new_filepath = Path(new_filepath_in)
            else:
                new_filepath = Path(Path.home(), new_filepath_in)

            # first check if given dir is actually an existing file.
            if new_filepath.is_file() and new_filepath.as_posix() != '.':
                # now, check if it is a netcdf file:
                if not new_filepath.as_posix().endswith('.nc'):
                    self.filepath_validity.readout = 'Not a valid netcdf file'
                else:
                    #mesh_ds = xr.open_dataset(new_filepath.as_posix())
                    try:
                        mesh_ds = xr.open_dataset(new_filepath.as_posix())
                        is_valid_path = True
                        with self.output:
                            print("Successfully read the mesh file.")
                    except:
                        self.filepath_validity.readout = 'Cannot read the file'
            else:
                self.filepath_validity.readout = 'Not a valid netcdf file'

        if self.filepath_validity.value != is_valid_path:
            self.filepath_validity.value = is_valid_path

    def _save_method(self, b):
        self.output.clear_output()
        datestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        filename = f"grid_reqs_{self._comp_name}_{datestamp}.json"
        filepath = Path(self.filepath.value, filename)
        if not filepath.is_absolute():
            filepath = Path(Path.home(), self.filepath.value)

        '''
        grid_reqs = {
            'nx': self._invoking_vars["OCN_NX"].value,
            'ny': self._invoking_vars["OCN_NY"].value,
            'config': self._invoking_vars["OCN_GRID_CONFIG"].value,
            'axis_units': self._invoking_vars["OCN_AXIS_UNITS"].value,
            'lenx': self._invoking_vars["OCN_LENX"].value,
            'leny': self._invoking_vars["OCN_LENY"].value,
            'cyclic_x': self._invoking_vars["OCN_CYCLIC_X"].value,
            'cyclic_y': self._invoking_vars["OCN_CYCLIC_Y"].value,
        }
        '''

        with self.output:
            print(f"> Saving file: {filepath}")
            import json
            with open(filepath, 'w') as grid_reqs_file:
                json.dump(grid_reqs, grid_reqs_file)

            print(
                f"> Done!\n"
                f"> In a new notebook session with the mom6_bathy kernel, run the following command: \n\n"
                f"from mom6_bathy.mom6grid import mom6grid \n"
                f"grd = mom6grid.from_json('{filepath}') \n"
            )
