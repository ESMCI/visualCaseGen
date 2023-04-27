import os
import re
from pathlib import Path
import subprocess
import ipywidgets as widgets

from ipyfilechooser import FileChooser

class CreateCaseWidget(widgets.VBox):

    def __init__(self,ci,layout=widgets.Layout()):

        super().__init__(layout=layout)

        self.compset = None
        self.grid = None
        self.ci = ci

        default_case_dir = self.ci.cime_output_root
        if default_case_dir is None:
            default_case_dir = Path(self.ci.cimeroot).parent.parent.as_posix()

        self.casepath = FileChooser(
            path=default_case_dir,
            filename='',
            title='<b>Select New Case Path:</b>',
            show_hidden=True,
            new_only=True,
            filename_placeholder='Enter case name',
            layout=widgets.Layout(width='700px', padding='10px')
        )

        self.machines = widgets.Dropdown(
            options=self.ci.machines,
            value=self.ci.machine,
            layout={'width': 'max-content'}, # If the items' names are long
            description='Machine:',
            disabled= (self.ci.machine is not None)
        )
        self.machines.style.description_width = '105px'
        self.machines.layout.visibility = 'visible' if self.ci.machine is None else 'hidden'
        self.machine_validity = widgets.Valid(
            value=self.ci.machine is not None,
            readout="Invalid Machine!",
            layout=widgets.Layout(display='none')
            )
        self.machine_validity.layout.visibility = 'visible' if self.ci.machine is None else 'hidden'

        self.case_create =  widgets.Button(
            description='Create new case',
            disabled=True,
            button_style='success', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Run the create_newcase command.',
            icon='terminal',
            layout=widgets.Layout(height='30px')
        )

        self.dry_run =  widgets.Button(
            description='Show command',
            disabled=True,
            button_style='info', # 'success', 'info', 'warning', 'danger' or ''
            tooltip="Print the create_newcase command, but don't run it.",
            icon='',
            layout=widgets.Layout(height='30px')
        )

        self.output = widgets.Output(
            layout={'border': '1px solid silver'}
        )

        self.children = [self.casepath,
                         widgets.HBox([self.machines, self.machine_validity]),
                         widgets.HBox([self.case_create, self.dry_run],
                                     layout= widgets.Layout(display='flex',justify_content='flex-end')),
                         self.output
                        ]

        self.casepath.observe(self._on_casepath_change)
        self.casepath.observe(self._on_validity_change)
        self.machines.observe(self._on_machine_change)
        self.machine_validity.observe(self._on_validity_change)
        self.dry_run.on_click(self._dry_run_method)
        self.case_create.on_click(self._case_create_method)

    def enable(self, compset, grid):
        self.compset = compset
        self.grid = grid
        self.output.clear_output()

    def disable(self, clear_output=True):
        self.casepath.reset()
        self.case_create.disabled = True
        self.dry_run.disabled = True
        self.machine_validity.layout.display = 'none'
        if clear_output:
            self.output.clear_output()

    def _on_casepath_change(self, change):
        if change['type'] == 'change' and change['name'] == 'value':
            new_casepath_in = change['new']

            is_valid_path = False

            if new_casepath_in not in [None, '']:
                new_casepath = Path(new_casepath_in)
                new_casedir = new_casepath.parent
                # check if the user has write permissions:
                if os.access(new_casedir.as_posix(), os.W_OK):
                    is_valid_path = True
                else:
                    #todo: when create case button is clicked, throw an error if no write access 
                    print(f"ERROR: no write access in {new_casedir.as_posix()}")


            if is_valid_path:
                self.machine_validity.layout.display = ''
            else:
                self.machine_validity.layout.display = 'none'


    def _on_machine_change(self, change):
        if change['type'] == 'change' and change['name'] == 'value':
            new_machine = change['new'].strip()
            if new_machine == '':
                self.machine_validity.value = False
                #todo: when create case button is clicked, throw an error if machine is not selected 
            else:
                self.machine_validity.value = True

    def _on_validity_change(self, change):
        if change['type'] == 'change' and change['name'] == 'value':
            if self.casepath.value not in [None, '']  and self.machine_validity.value is True:
                self.case_create.disabled = False
                self.dry_run.disabled = False
            else:
                self.case_create.disabled = True
                self.dry_run.disabled = True

    def _dry_run_method(self, b):
        self.output.clear_output()
        casepath = Path(self.casepath.value)
        if not casepath.is_absolute():
            casepath = Path(Path.home(), self.casepath.value)
        with self.output:
            cmd = "{}/scripts/create_newcase --res {} --compset {} --case {} --machine {} --run-unsupported".format(
            self.ci.cimeroot,
            self.grid,
            self.compset,
            casepath,
            self.machines.value)
            print(cmd)

    def _case_create_method(self, b):
        self.output.clear_output()
        casepath = Path(self.casepath.value)
        if not casepath.is_absolute():
            casepath = Path(Path.home(), self.casepath.value)
        with self.output:
            cmd = "{}/scripts/create_newcase --res {} --compset {} --case {} --machine {} --run-unsupported".format(
            self.ci.cimeroot,
            self.grid,
            self.compset,
            casepath,
            self.machines.value)
            print("Running cmd: {}".format(cmd))
            runout = subprocess.run(cmd, shell=True, capture_output=True)
            if runout.returncode == 0:
                #print("\n{}".format(runout.stdout.decode('UTF-8')))
                print("\nSUCCESS: Case created at {} ".format(casepath))
                self.disable(clear_output=False)
            else:
                print(runout.stdout)
                print("ERROR: {} ".format(runout.stderr))
