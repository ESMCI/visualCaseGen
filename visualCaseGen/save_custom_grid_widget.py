import os
import re
from pathlib import Path
import subprocess
import ipywidgets as widgets
from datetime import datetime

class SaveCustomGrid(widgets.VBox):

    def __init__(self, comp_name, invoking_vars, layout=widgets.Layout()):

        super().__init__(layout=layout)

        self._comp_name = comp_name
        self._invoking_vars = invoking_vars

        self.filedir = widgets.Textarea(
            value='',
            placeholder='Type an existing directory',
            description='Save custom grid config to:',
            disabled=True,
            layout=widgets.Layout(height='40px', width='600px')
        )
        self.filedir.style.description_width = '180px'

        self.filedir_validity = widgets.Valid(
            value=False,
            readout="Type an existing directory!",
            layout=widgets.Layout(width='400px')
            )

        self.save_button =  widgets.Button(
            description='Save',
            disabled=True,
            button_style='success', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='When ready, save the custom grid file',
            icon='floppy-disk',
            layout=widgets.Layout(height='30px')
        )

        self.output = widgets.Output(
            layout={'border': '1px solid silver'}
        )

        self.children = [widgets.HBox([self.filedir]),
                         widgets.HBox([self.save_button, self.filedir_validity],
                                     layout= widgets.Layout(display='flex',justify_content='flex-end')),
                         self.output
                        ]

        self.filedir.observe(
            self._on_filedir_change,
            names = 'value',
            type = 'change'
            )
        self.filedir_validity.observe(
            self._on_validity_change,
            names = 'value',
            type = 'change'
            )
        self.save_button.on_click(self._save_method)

        for varname, var in self._invoking_vars.items():
            var.observe(
                self._turn_on_off,
                names='value',
                type='change'
            )
        self._turn_on_off(None)
    
    def _turn_on_off(self,change):
        if any([var.value is None for varname, var in self._invoking_vars.items()]):
            self.disable()
        else:
            self.enable()


    def enable(self):
        self.filedir.disabled = False
        self.filedir_validity.readout = "Enter a valid directory!"
        self.output.clear_output()

    def disable(self, clear_output=True):
        self.filedir.disabled = True
        self.filedir.value = ''
        self.save_button.disabled = True
        self.filedir_validity.readout= 'Set all grid options!'
        self.output.clear_output()

    def _on_filedir_change(self, change):
        new_filedir_in = change['new'].strip()
        is_valid_dir = False

        if new_filedir_in == '':
            self.filedir_validity.readout = "Enter a valid directory!"
        else:

            # obtain the absolute path
            if os.path.isabs(new_filedir_in):
                new_filedir = Path(new_filedir_in)
            else:
                new_filedir = Path(Path.home(), new_filedir_in)

            # check if the directory is valid
            # first check if given dir is actually an existing directory.
            if new_filedir.is_dir() and new_filedir.as_posix() != '.':
                # now, check if the user has write permissions:
                if os.access(new_filedir.as_posix(), os.W_OK):
                    is_valid_dir = True
                else:
                    self.filedir_validity.readout = 'No write access!'
            else:
                self.filedir_validity.readout = 'Invalid directory!'

        if self.filedir_validity.value != is_valid_dir:
            self.filedir_validity.value = is_valid_dir

    def _on_validity_change(self, change):
        if self.filedir_validity.value is True:
            self.save_button.disabled = False
        else:
            self.save_button.disabled = True

    def _save_method(self, b):
        self.output.clear_output()
        datestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        filename = f"grid_reqs_{self._comp_name}_{datestamp}.json"
        filepath = Path(self.filedir.value, filename)
        if not filepath.is_absolute():
            filepath = Path(Path.home(), self.filepath.value)

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
