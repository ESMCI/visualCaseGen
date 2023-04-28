import os
import shutil
from pathlib import Path
import subprocess
import ipywidgets as widgets

from visualCaseGen.sdb import SDB
from visualCaseGen.cime_interface import Case
from ipyfilechooser import FileChooser

class CreateCaseWidget(widgets.VBox):

    def __init__(self, ci, session_id=None, layout=widgets.Layout()):

        super().__init__(layout=layout)

        self.compset = None
        self.grid = None
        self.ci = ci
        self.session_id = session_id

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
        self.casepath.disable()

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
        self.machines.observe(self._on_machine_change)
        self.dry_run.on_click(self._dry_run_method)
        self.case_create.on_click(self._case_create_method)

    def enable(self, compset, grid):
        self.compset = compset
        self.grid = grid
        self.casepath.enable()
        self.output.clear_output()

    def disable(self, clear_output=True):
        self.casepath.disable()
        self.dry_run.disabled = True
        self.machine_validity.layout.display = 'none'
        if clear_output:
            self.output.clear_output()

    def _on_casepath_change(self, change):
        if change['type'] == 'change' and change['name'] == 'value':
            new_casepath_in = change['new']
            if new_casepath_in not in [None, '']:
                self.machine_validity.layout.display = ''
            else:
                self.machine_validity.layout.display = 'none'
            self._refresh_case_create_button()


    def _on_machine_change(self, change):
        if change['type'] == 'change' and change['name'] == 'value':
            new_machine = change['new'].strip()
            if new_machine == '':
                self.machine_validity.value = False
            else:
                self.machine_validity.value = True
            self._refresh_case_create_button()

    def _refresh_case_create_button(self):
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

        # Make sure all MOM6 custom grid files are generated (if MOM6 is active and in custom grid mode)
        if self.session_id is not None:

            if 'MOM6' in self.compset and self.grid == 'custom':
                d = SDB(self.session_id).get_data()
                if any([entry not in d for entry in ['mesh_path', 'supergrid_path', 'topog_path', 'runtime_params']]):
                    with self.output:
                        print("ERROR: MOM6 custom grid has not been constructed yet. Make sure all mom6_bathy steps are completed.")
                        return
            
        # check if machine is selected
        if self.machines.value in [None, '']:
            with self.output:
                print("ERROR: machine is invalid")
                return

        # check if user has write access
        if not os.access(casepath.parent.as_posix(), os.W_OK):
            with self.output:
                print(f"ERROR: no write access in {casepath.parent.as_posix()}")
                return

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
                return
    
        self._apply_mods(casepath)
        

    def _apply_mods(self, casepath):

        if self.session_id is None:
            return # No xmlchange or user_nl change is needed
        d = SDB(self.session_id).get_data()
        

        # xmlchange commands
        if "mesh_path" in d:
            with self.output:
                print("\n Running xmlchange commands (if any needed)...")
                cmd = f"./xmlchange OCN_DOMAIN_MESH={d['mesh_path']}" 
                print(cmd)
                runout = subprocess.run(cmd, shell=True, capture_output=True, cwd=casepath)
                if runout.returncode == 0:
                    print(f"\nsuccess: {runout.stdout}")
                else:
                    print(f"{runout.stdout}\nERROR: {runout.stderr}")
                    return

        case = Case(casepath)
        rundir = case.get_value('RUNDIR')

        # run case.setup
        with self.output:
            print("\n Running ./case.setup ...")
            runout = subprocess.run('./case.setup', shell=True, capture_output=True, cwd=casepath)
            if runout.returncode == 0:
                print(f"\nsuccess: {runout.stdout}")
            else:
                print(f"{runout.stdout}\nERROR: {runout.stderr}")
                return

        # write to user_nl_mom
        with self.output:
            print("\n Updating user_nl_mom (if needed) ...")
            if 'runtime_params' in d:
                with open(os.path.join(casepath,'user_nl_mom'), 'a') as f:
                    for key, val in d['runtime_params'].items():
                        f.write(f"{key} = {val}\n")



        # copy input files
        if "supergrid_path" in d:
            assert "topog_path" in d, "Cannot find MOM6 topo file directory while attempting to modify the case"
            assert "runtime_params" in d, "Cannot find MOM6 the necessary MOM6 runtime input params while attempting to modify the case"

            with self.output:
                print("\n Copying input files...")

            try:
                inputdir = os.path.join(rundir, d['runtime_params']['INPUTDIR'])
                if not os.path.exists(inputdir):
                    os.mkdir(inputdir)
            
                shutil.copy(d['supergrid_path'], inputdir)
                shutil.copy(d['topog_path'], inputdir)
            except:
                with self.output:
                    print("ERROR: encountered error while attempting to copy input files. exiting...")
            

        with self.output:
            print("done.")


