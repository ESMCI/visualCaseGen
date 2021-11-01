import os
import re
from pathlib import Path
import subprocess
import ipywidgets as widgets

class CreateCaseWidget(widgets.VBox):

    def __init__(self,ci,layout=widgets.Layout()):

        super().__init__(layout=layout)

        self.compset = None
        self.grid = None
        self.ci = ci
        self._default_case_dir = Path(self.ci.cimeroot).parent.parent.as_posix()

        self.casepath = widgets.Textarea(
            value='',
            placeholder='Type case name',
            description='Case name:',
            disabled=True,
            layout=widgets.Layout(height='40px', width='590px')
        )
        self.casepath.style.description_width = '105px'
        self.casepath_validity = widgets.Valid(
            value=False,
            readout="Empty casename!",
            layout=widgets.Layout(display='none')
            )
        self.machines = widgets.Dropdown(
            options=self.ci.machines,
            value=self.ci.machine,
            layout={'width': 'max-content'}, # If the items' names are long
            description='Machine:',
            disabled= (self.ci.machine is not None)
        )
        self.machines.style.description_width = '105px'
        self.machine_validity = widgets.Valid(
            value=self.ci.machine is not None,
            readout="Invalid Machine!",
            layout=widgets.Layout(display='none')
            )

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

        self.children = [widgets.HBox([self.casepath, self.casepath_validity]),
                         widgets.HBox([self.machines, self.machine_validity]),
                         widgets.HBox([self.case_create, self.dry_run],
                                     layout= widgets.Layout(display='flex',justify_content='flex-end')),
                         self.output
                        ]

        self.casepath.observe(self._on_casename_change)
        self.machines.observe(self._on_machine_change)
        self.casepath_validity.observe(self._on_validity_change)
        self.machine_validity.observe(self._on_validity_change)
        self.dry_run.on_click(self._dry_run_method)
        self.case_create.on_click(self._case_create_method)

    def enable(self, compset, grid):
        self.casepath.disabled = False
        self.casepath_validity.layout.display = ''
        self.compset = compset
        self.grid = grid
        self.output.clear_output()

    def disable(self, clear_output=True):
        self.casepath.disabled = True
        self.casepath.value = ''
        self.case_create.disabled = True
        self.dry_run.disabled = True
        self.casepath_validity.layout.display = 'none'
        self.machine_validity.layout.display = 'none'
        if clear_output:
            self.output.clear_output()

    def _on_casename_change(self, change):
        if change['type'] == 'change' and change['name'] == 'value':
            new_casepath_in = change['new'].strip()

            if new_casepath_in == '':
                self.casepath_validity.readout = "Empty casename!"
            else:

                # obtanin the absolute path
                if os.path.isabs(new_casepath_in):
                    new_casepath = Path(new_casepath_in)
                else:
                    new_casepath = Path(Path.home(), new_casepath_in)
                is_valid_path = False

                # check if the parent directory is valid
                new_casedir = new_casepath.parent
                # first check if given dir is actually an existing directory.
                if new_casedir.is_dir() and new_casedir.as_posix() != '.':
                    # now, check if the user has write permissions:
                    if os.access(new_casedir.as_posix(), os.W_OK):
                        is_valid_path = True
                    else:
                        self.casepath_validity.readout = 'Invalid case path'
                else:
                    self.casepath_validity.readout = 'Invalid case path!'

                if is_valid_path:
                    is_valid_path = False # temporarily set to False. Will be reset to True if casename is valid.
                    if new_casepath.exists():
                        if Path(new_casepath, 'env_case.xml').exists():
                            self.casepath_validity.readout = 'Case exists!'
                        else:
                            self.casepath_validity.readout = 'Path exists!'
                    else:
                        new_casename = new_casepath.name
                        if bool(re.match('^[a-zA-Z0-9\.\-_%]+$', new_casename)) is False:
                            self.casepath_validity.readout = 'Invalid case name!'
                        else:
                            is_valid_path = True

                if is_valid_path:
                    self.machine_validity.layout.display = ''
                else:
                    self.machine_validity.layout.display = 'none'

                if self.casepath_validity.value != is_valid_path:
                    self.casepath_validity.value = is_valid_path

    def _on_machine_change(self, change):
        if change['type'] == 'change' and change['name'] == 'value':
            new_machine = change['new'].strip()
            if new_machine == '':
                self.machine_validity.value = False
                self.casepath_validity.readout = "Select machine!"
            else:
                self.machine_validity.value = True

    def _on_validity_change(self, change):
        if change['type'] == 'change' and change['name'] == 'value':
            if self.casepath_validity.value is True and self.machine_validity.value is True:
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
