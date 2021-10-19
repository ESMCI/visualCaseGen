import os
from pathlib import Path
import subprocess
import ipywidgets as widgets

class CreateCaseWidget(widgets.VBox):

    def __init__(self,ci,layout=widgets.Layout()):

        super().__init__(layout=layout)

        self.compset = None
        self.grid = None
        self.ci = ci

        self.casedir = widgets.Combobox(
            description='Directory:',
            layout=widgets.Layout(width='600px'),
            disabled=True
        )
        self.casedir_validity= widgets.Valid(
            value=False,
            readout="Invalid directory",
            layout=widgets.Layout(display='none')
            )

        self.casename = widgets.Textarea(
            value='',
            placeholder='Type case name',
            description='Case name:',
            disabled=True,
            layout=widgets.Layout(height='40px', width='600px')
        )
        self.casename_validity = widgets.Valid(
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

        self.case_create =  widgets.Button(
            description='Create new case',
            disabled=True,
            button_style='success', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Run the create_newcase command.',
            icon='terminal',
            layout=widgets.Layout(height='30px')
        )

        self.dry_run =  widgets.Button(
            description='Dry run',
            disabled=True,
            button_style='info', # 'success', 'info', 'warning', 'danger' or ''
            tooltip="Print the create_newcase command, but don't run it.",
            icon='',
            layout=widgets.Layout(height='30px')
        )

        self.output = widgets.Output(
            layout={'border': '1px solid silver'}
        )

        self.children = [widgets.HBox([self.casedir, self.casedir_validity]),
                         widgets.HBox([self.casename, self.casename_validity]),
                         self.machines,
                         widgets.HBox([self.case_create, self.dry_run],
                                     layout= widgets.Layout(display='flex',justify_content='center')),
                         self.output
                        ]

        self.casedir.observe(self._on_casedir_change)
        self.casename.observe(self._on_casename_change)
        self.casedir_validity.observe(self._on_validity_change)
        self.casename_validity.observe(self._on_validity_change)
        self.dry_run.on_click(self._dry_run_method)
        self.case_create.on_click(self._case_create_method)

    def enable(self, compset, grid):
        self.casedir.disabled = False
        self.casename.disabled = False
        if self.casedir.value == '':
            self.casedir.value = os.getcwd()
        self.casedir_validity.layout.display = ''
        self.casename_validity.layout.display = ''
        self.compset = compset
        self.grid = grid
        self.output.clear_output()

    def disable(self, clear_output=True):
        self.casedir.disabled = True
        self.casename.disabled = True
        self.casename.value = ''
        self.case_create.disabled = True
        self.dry_run.disabled = True
        self.casedir_validity.layout.display = 'none'
        self.casename_validity.layout.display = 'none'
        if clear_output:
            self.output.clear_output()

    def _on_casedir_change(self, change):
        max_nopts = 30
        if change['type'] == 'change' and change['name'] == 'value':
            new_dir = Path(change['new'])
            is_valid_dir = False

            # first check if given dir is actually an existing directory.
            if new_dir.is_dir() and change['new'].strip() != '':
                # now, check if the user has write permissions:
                if os.access(change['new'], os.W_OK):
                    is_valid_dir = True
                else:
                    self.casedir_validity.readout = 'No write permissions!'
            else:
                self.casedir_validity.readout = 'Directory not found!'

            if is_valid_dir:
                self.casedir_validity.value=True
                self.casename.disabled = False
                self.casename_validity.layout.display = ''
                options = [new_dir.as_posix()]
                for option in list(new_dir.glob('[!.]*')):
                    if Path(new_dir,option).is_dir():
                        options.append(Path(new_dir,option).as_posix())
                    if len(options)>=max_nopts:
                        options = [new_dir.as_posix()]
                        break
                if change['owner'].options != tuple(options):
                    change['owner'].options = options
            else:
                self.casedir_validity.value=False
                self.casename.disabled = True
                self.casename_validity.layout.display = 'none'
                name = new_dir.name
                parent = new_dir.parent
                options = []
                for option in list(parent.glob('{}*'.format(name))):
                    if Path(parent,option).is_dir():
                        options.append(option.as_posix())
                    if len(options)>=max_nopts:
                        options = [parent.as_posix()]
                        break
                if change['owner'].options != tuple(options):
                    change['owner'].options = options

    def _on_casename_change(self, change):
        if change['type'] == 'change' and change['name'] == 'value':
            new_casename = change['new']
            if new_casename.strip() == '':
                self.casename_validity.value = False
                self.casename_validity.readout = "Empty case name!"
            else:
                if Path(self.casedir.value,new_casename).exists():
                    if Path(self.casedir.value,new_casename,'env_case.xml').exists():
                        self.casename_validity.readout = "Case exists!"
                    else:
                        self.casename_validity.readout = "Path exists!"
                    self.casename_validity.value = False
                else:
                    if ' ' in new_casename.strip():
                        self.casename_validity.readout = "Invalid case name!"
                        self.casename_validity.value = False
                    else:
                        self.casename_validity.value = True

    def _on_validity_change(self, change):
        if change['type'] == 'change' and change['name'] == 'value':
            if self.casedir_validity.value is True and self.casename_validity.value is True:
                self.case_create.disabled = False
                self.dry_run.disabled = False
            else:
                self.case_create.disabled = True
                self.dry_run.disabled = True

    def _dry_run_method(self, b):
        self.output.clear_output()
        with self.output:
            casepath = Path(self.casedir.value.strip(), self.casename.value.strip())
            cmd = "{}/scripts/create_newcase --res {} --compset {} --case {} --machine {} --run-unsupported".format(
            self.ci.cimeroot,
            self.grid,
            self.compset,
            casepath,
            self.machines.value)
            print(cmd)

    def _case_create_method(self, b):
        self.output.clear_output()
        with self.output:
            casepath = Path(self.casedir.value.strip(), self.casename.value.strip())
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
