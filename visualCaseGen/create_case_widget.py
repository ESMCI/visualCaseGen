import os
import shutil
from pathlib import Path
import subprocess
import ipywidgets as widgets

from visualCaseGen.sdb import SDB
from visualCaseGen.cime_interface import Case
from visualCaseGen.config_var import cvars
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
            disabled=True
        )
        self.machines.style.description_width = '105px'

        self.project = widgets.Text(
            description = 'Project ID:',
            value = os.getenv('PROJECT') or '',
            disabled=True
        )
        self.project.style.description_width = '105px'
        self.project.layout.visibility = 'visible' if (self.ci.machine is not None and self.ci.project_required[self.ci.machine] == True) else 'hidden'

        self.case_create =  widgets.Button(
            description='Create new case',
            disabled=True,
            button_style='success', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Run the create_newcase command.',
            icon='terminal',
            layout=widgets.Layout(height='30px')
        )

        self.dry_run =  widgets.Button(
            description='Show commands',
            disabled=True,
            button_style='info', # 'success', 'info', 'warning', 'danger' or ''
            tooltip="Print the commands to create and configure the case.",
            icon='',
            layout=widgets.Layout(height='30px')
        )

        self.output = widgets.Output(
            layout={'border': '1px solid silver'}
        )

        self.children = [self.casepath,
                         self.machines,
                         self.project,
                         widgets.HBox([self.case_create, self.dry_run],
                                     layout= widgets.Layout(display='flex',justify_content='flex-end')),
                         self.output
                        ]

        self.casepath.observe(self._on_casepath_change)
        self.machines.observe(self._on_machine_change)
        self.project.observe(self._on_project_change)
        self.dry_run.on_click(self._dry_run_method)
        self.case_create.on_click(self._case_create_method)

    def enable(self, compset, grid):
        self.compset = compset
        self.grid = grid
        self.casepath.enable()
        self.machines.disabled = False
        self.project.disabled = False
        self.output.clear_output()

    def disable(self, clear_output=True):
        self.casepath.disable()
        self.machines.disabled = True
        self.project.disabled = True
        self.dry_run.disabled = True
        if clear_output:
            self.output.clear_output()

    def reset(self):
        self.casepath.enable()
        self.machines.disabled = False
        self.project.disabled = False

    def _on_casepath_change(self, change):
        if change['type'] == 'change' and change['name'] == 'value':
            self._refresh_case_create_button()


    def _on_machine_change(self, change):
        if change['type'] == 'change' and change['name'] == 'value':
            # no need to call self._refresh_case_create_button because the below assignment of self.project.value will call it.
            new_machine = change['new'].strip()
            self.project.value = ''
            self.project.layout.visibility = 'visible' if (new_machine is not None and self.ci.project_required[new_machine] == True) else 'hidden'

    def _on_project_change(self, change):
        if change['type'] == 'change' and change['name'] == 'value':
            self._refresh_case_create_button()

    def _is_non_local(self):
        '''Returns true if case is being constructed at a machine that is different
           than the machine visualCaseGen is being run.'''
        return self.ci.machine is not None and self.ci.machine != self.machines.value

    def _refresh_case_create_button(self):

        def _ready_to_create():
            if self.casepath.value in [None, '']:
                return False
            if self.machines.value in [None, '']:
                return False
            if self.ci.project_required[self.machines.value] and self.project.value == '':
                return False
            return True

        if _ready_to_create():
            self.case_create.disabled = False
            self.dry_run.disabled = False
        else:
            self.case_create.disabled = True
            self.dry_run.disabled = True

    def _dry_run_method(self, b):
        self._case_create_method(b, do_exec=False)

    def _case_create_method(self, b, do_exec=True):
        self.output.clear_output()
        casepath = Path(self.casepath.value)
        if not casepath.is_absolute():
            casepath = Path(Path.home(), self.casepath.value)

        # Make sure all MOM6 custom grid files are generated (if MOM6 is active and in custom grid mode)
        if self.session_id is not None:

            if self.grid == 'custom' and cvars['COMP_ATM'].value in ['cam', 'datm']:
                custom_atm_grid = cvars['CUSTOM_ATM_GRID'].value
                if custom_atm_grid is None:
                    with self.output:
                        print("ERROR: ATM custom grid has not been selected yet. Make sure all custom grid selections are made.")
                        return

            if 'MOM6' in self.compset and self.grid == 'custom':
                d = SDB(self.session_id).get_data()
                if any([entry not in d for entry in ['mesh_path', 'supergrid_path', 'topog_path', 'mom6_params']]):
                    with self.output:
                        print("ERROR: MOM6 custom grid has not been constructed yet. Make sure all mom6_bathy steps are completed.")
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

            if self.project.value != '':
                cmd += f' --project {self.project.value}'

            if self._is_non_local() is True:
                cmd += ' --non-local'

            print("Run create case command...\n")
            print(f"  > {cmd}")
            if do_exec:
                runout = subprocess.run(cmd, shell=True, capture_output=True)
                if runout.returncode == 0:
                    #print("\n{}".format(runout.stdout.decode('UTF-8')))
                    print("\nSUCCESS: Case created at {} ".format(casepath))
                    self.disable(clear_output=False)
                else:
                    print(runout.stdout)
                    print("ERROR: {} ".format(runout.stderr))
                    return

        self._apply_mods(casepath, do_exec)

        # After a successful case creation, reset and re-enable create_case widget.
        if do_exec:
            self.reset()

    def _apply_mods(self, casepath, do_exec):

        if self.session_id is None:
            return # No xmlchange or user_nl change is needed
        d = SDB(self.session_id).get_data()

        def exec_xmlchange(var, new_val):
            cmd = f"./xmlchange {var}={new_val} "
            if self._is_non_local() is True:
                cmd += ' --non-local'

            print(f'  > {cmd}')
            if do_exec:
                runout = subprocess.run(cmd, shell=True, capture_output=True, cwd=casepath)
                if runout.returncode == 0:
                    pass
                else:
                    print(f"{runout.stdout}\nERROR: {runout.stderr}")
                    return

        # inform user to navigate to casepath
        with self.output:
            print("\nNavigate to the case directory...\n")
            print(f'  > cd {casepath}')

        # xmlchange commands
        with self.output:

            # apply custom ocn/ice grid xml changes
            if 'ocnice_xmlchanges' in d and len(d['ocnice_xmlchanges'])>0:
                print("\nApply custom ocn/ice grid xml changes...\n")
                for var, new_val in d['ocnice_xmlchanges'].items():
                    exec_xmlchange(var, new_val)

            # apply custom ATM grid xml changes
            atm_mesh = 'UNSET'
            if self.grid == 'custom' and cvars['COMP_ATM'].value in ['cam', 'datm']:
                custom_atm_grid = cvars['CUSTOM_ATM_GRID'].value
                if custom_atm_grid is not None:
                    print("\nApply custom atm grid xml changes...\n")
                    atm_mesh = self.ci.get_mesh_filepath(custom_atm_grid)
                    exec_xmlchange('ATM_GRID', custom_atm_grid)
                    exec_xmlchange('ATM_DOMAIN_MESH', atm_mesh)

            # apply custom LND grid xml changes
            if 'mesh_mask_modifier' in d:
                mesh_mask_out = d['mesh_mask_modifier'].get('mesh_mask_out')
                if mesh_mask_out is not None:
                    print("\nApply custom lnd grid xml changes...\n")
                    exec_xmlchange('MASK_MESH', mesh_mask_out)
                    exec_xmlchange('LND_DOMAIN_MESH', mesh_mask_out) # should this actually be set to ATM_DOMAIN_MESH:
                    # Existence of mesh_mask_out in sdb indicates that mesh_mask_modfier has been utilizes, and, thus,
                    # ocn/ince meshes should be set to atm_mesh
                    exec_xmlchange('OCN_DOMAIN_MESH', atm_mesh)
                    exec_xmlchange('ICE_DOMAIN_MESH', atm_mesh)
            elif cvars['COMP_LND'].value == 'clm' and atm_mesh != 'UNSET':
                # if LND_DOMAIN_MESH was not set via mesh_mask_modifier, set it to ATM mesh.
                exec_xmlchange('LND_DOMAIN_MESH', atm_mesh)

            if cvars['COMP_LND'].value:
                exec_xmlchange('CLM_FORCE_COLDSTART', 'True') # TODO :This should be applied based on a condition,
                                                              # possibly set by the user via a widget.

        # run case.setup
        with self.output:
            print("\nRun ./case.setup ...")
            if do_exec:
                cmd = './case.setup'
                if self._is_non_local() is True:
                    cmd += ' --non-local'
                runout = subprocess.run(cmd, shell=True, capture_output=True, cwd=casepath)
                stdout = runout.stdout.decode('UTF-8') if type(runout.stdout) is bytes else runout.stdout
                if runout.returncode == 0:
                    print(f"\nSUCCESS: {stdout}")
                else:
                    stderr = runout.stderr.decode('UTF-8') if type(runout.stderr) is bytes else runout.stderr
                    print(f"{stdout}\nERROR: {stderr}")
                    return

        # user namelist changes
        with self.output:

            # write to user_nl_mom
            if 'mom6_params' in d:
                mom6_params = d['mom6_params']
                mom6_params['GRID_FILE'] = os.path.split(d['supergrid_path'])[1]
                mom6_params['TOPO_FILE'] = os.path.split(d['topog_path'])[1]

                print("\nAdd parameters to user_nl_mom ...\n")
                if do_exec:
                    with open(os.path.join(casepath,'user_nl_mom'), 'a') as f:
                        for key, val in mom6_params.items():
                            f.write(f"{key} = {val}\n")
                for key, val in mom6_params.items():
                    print(f"  {key} = {val}")

            # write to user_nl_cice
            if 'cice_params' in d:
                print("\nAdd parameters to user_nl_cice ...\n")
                if do_exec:
                    with open(os.path.join(casepath,'user_nl_cice'), 'a') as f:
                        for key, val in d['cice_params'].items():
                            f.write(f'{key} = "{val}"\n')
                for key, val in d['cice_params'].items():
                    print(f'  {key} = "{val}"')

            # write to user_nl_clm
            if 'fsurdat_modifier' in d:
                fsurdat_out = d['fsurdat_modifier'].get('fsurdat_out')
                if fsurdat_out is not None:
                    print("\nAdd parameters to user_nl_clm ...\n")
                    if do_exec:
                        with open(os.path.join(casepath,'user_nl_clm'), 'a') as f:
                            f.write(f'fsurdat = "{fsurdat_out}"\n')
                    print(f'fsurdat = "{fsurdat_out}"\n')

        # copy input files
        if "supergrid_path" in d:
            assert "topog_path" in d, "Cannot find MOM6 topo file directory while attempting to modify the case"
            assert "mom6_params" in d, "Cannot find MOM6 the necessary MOM6 runtime input params while attempting to modify the case"

            # temporarily set inputdir for dry run
            inputdir = '${RUNDIR}/INPUTDIR'

            if do_exec:
                # override inputdir with its actual value
                case = Case(casepath, non_local = self._is_non_local())
                rundir = case.get_value('RUNDIR')
                inputdir = os.path.join(rundir, d['mom6_params']['INPUTDIR'])
                try:
                    if not os.path.exists(inputdir):
                        os.mkdir(inputdir)

                    shutil.copy(d['supergrid_path'], inputdir)
                    shutil.copy(d['topog_path'], inputdir)
                except:
                    with self.output:
                        print("ERROR: encountered error while attempting to copy input files. exiting...")

            with self.output:
                print("\nCopy input files...\n")
                print(f"  > cp {d['supergrid_path']} {inputdir}")
                print(f"  > cp {d['topog_path']} {inputdir}")


        with self.output:
            print("\nDone.")


