import os
import logging
from pathlib import Path
import subprocess
import shutil
from xml.etree.ElementTree import SubElement
import xml.etree.ElementTree as ET
import xarray as xr

from ProConPy.config_var import cvars
from visualCaseGen.custom_widget_types.mom6_bathy_launcher import MOM6BathyLauncher
from visualCaseGen.custom_widget_types.dummy_output import DummyOutput
from visualCaseGen.custom_widget_types.case_tools import xmlchange, run_case_setup, append_user_nl

COMMENT = "\033[01;96m"  # bold, cyan
SUCCESS = "\033[1;32m"  # bold, green
ERROR = "\033[1;31m"  # bold, red
RESET = "\033[0m"
BPOINT = "\u2022"


class CaseCreator:
    """The base class for CaseCreatorWidget. Here, backend functionalities are implemented."""

    def __init__(self, cime, output=None, allow_xml_override=False):
        """Initialize CaseCreator object.

        Parameters
        ----------
        cime : CIME
            The CIME instance.
        output : Output, optional
            The output widget to use for displaying log messages.
        allow_xml_override : bool, optional
            If True, allow overwriting existing entries in CESM xml files such as modelgrid_aliases_nuopc.xml
            and component_grids_nuopc.xml. If False, raise an error if an entry with the same name already exists.
        """

        self._cime = cime
        self._out = DummyOutput() if output is None else output
        self._allow_xml_override = allow_xml_override

    def revert_launch(self, do_exec=True):
        """This function is called when the case creation fails. It reverts the changes made
        to the ccs_config xml files."""

        mg = "ccs_config/modelgrid_aliases_nuopc.xml"
        if (Path(self._cime.srcroot) / f"{mg}.orig").exists():
            shutil.move(
                Path(self._cime.srcroot) / f"{mg}.orig",
                Path(self._cime.srcroot) / f"{mg}"
            )
        cg = "ccs_config/component_grids_nuopc.xml"
        if (Path(self._cime.srcroot) / f"{cg}.orig").exists():
            shutil.move(
                Path(self._cime.srcroot) / f"{cg}.orig",
                Path(self._cime.srcroot) / f"{cg}"
            )

    def _remove_orig_xml_files(self):
        """This function is called when the case creation and modification process is successful.
        It removes the backup xml files created before modifying the ccs_config xml files."""

        mg = "ccs_config/modelgrid_aliases_nuopc.xml"
        if (Path(self._cime.srcroot) / f"{mg}.orig").exists():
            os.remove(Path(self._cime.srcroot) / f"{mg}.orig")
        cg = "ccs_config/component_grids_nuopc.xml"
        if (Path(self._cime.srcroot) / f"{cg}.orig").exists():
            os.remove(Path(self._cime.srcroot) / f"{cg}.orig")

    def _is_non_local(self):
        """Check if the case is being created on a machine different from the one
        that runs visualCaseGen."""
        return (
            self._cime.machine is not None
            and self._cime.machine != cvars["MACHINE"].value
        )

    def _final_checks(self):
        """Perform final checks before attempting to create the case."""

        caseroot = cvars["CASEROOT"].value
        if caseroot is None:
            raise RuntimeError("No case directory and name specified yet.")
        if Path(caseroot).exists():
            raise RuntimeError(f"Case directory {caseroot} already exists.")
        elif cvars["MACHINE"].value is None:
            raise RuntimeError("No machine specified yet.")
        elif (
            cvars["PROJECT"].value in [None, ""]
            and self._cime.project_required.get(cvars["MACHINE"].value, False) is True
        ):
            raise RuntimeError("No project specified yet.")

    def create_case(self, do_exec):
        """Create and configure the case by running the necessary tools.

        Parameters
        ----------
        cime : CIME
            The CIME instance.
        do_exec : bool, optional
            If True, print and execute the commands. If False, only print them
        """

        self._out.clear_output()

        # Perform final checks before creating the case:
        self._final_checks()

        # Determine compset:
        if cvars["COMPSET_MODE"].value == "Standard":
            compset = cvars["COMPSET_ALIAS"].value
        elif cvars["COMPSET_MODE"].value == "Custom":
            with self._out:
                print(f"{COMMENT}{cvars["COMPSET_LNAME"].value}{RESET}\n")
            compset = cvars["COMPSET_LNAME"].value
        else:
            raise RuntimeError(f"Unknown compset mode: {cvars['COMPSET_MODE'].value}")

        # Determine and check caseroot:
        caseroot = Path(cvars["CASEROOT"].value)
        if not caseroot.is_absolute():
            caseroot = Path.home() / caseroot
        if not os.access(caseroot.parent.as_posix(), os.W_OK):
            raise RuntimeError(
                f"Cannot write to {caseroot}. Please choose another directory."
            )

        # Determine resolution:
        if cvars["GRID_MODE"].value == "Standard":
            resolution = cvars["GRID"].value
        elif cvars["GRID_MODE"].value == "Custom":
            resolution = Path(cvars["CUSTOM_GRID_PATH"].value).name
        else:
            raise RuntimeError(f"Unknown grid mode: {cvars['GRID_MODE'].value}")

        # Begin case creation:
        with self._out:
            print(f"{COMMENT}Creating case...{RESET}\n")

        # First, update ccs_config xml files to add custom grid information if needed:
        self._update_ccs_config(do_exec)

        # Run create_newcase
        self._run_create_newcase(caseroot, compset, resolution, do_exec)

        # Navigate to the case directory:
        with self._out:
            print(f"{COMMENT}Navigating to the case directory:{RESET}\n")
            print(f"cd {caseroot}\n")

        # Apply case modifications, e.g., xmlchanges and user_nl changes
        self._apply_all_xmlchanges(do_exec)

        # Run case.setup
        run_case_setup(do_exec, self._is_non_local(), self._out)

        # Apply user_nl changes
        self._apply_all_namelist_changes(do_exec)

        # Clean up:
        if do_exec:
            self._remove_orig_xml_files()
            cvars["CASE_CREATOR_STATUS"].value = "OK"
            with self._out:
                caseroot = cvars["CASEROOT"].value
                print(
                    f"{SUCCESS}Case created successfully at {caseroot}.{RESET}\n\n"
                    f"{COMMENT}To further customize, build, and run the case, "
                    f"navigate to the case directory in your terminal. To create "
                    f"another case, restart the notebook.{RESET}\n"
                )

    def _update_ccs_config(self, do_exec):
        """Update the modelgrid_aliases and component_grids xml files with custom grid
        information if needed. This function is called before running create_newcase."""

        # If Custom grid is selected, update modelgrid_aliases and component_grids xml files:
        if cvars["GRID_MODE"].value == "Standard":
            return
        else:
            assert (
                cvars["GRID_MODE"].value == "Custom"
            ), f"Unknown grid mode: {cvars['GRID_MODE'].value}"

        # check if custom grid path exists:
        ocn_grid_mode = cvars["OCN_GRID_MODE"].value
        lnd_grid_mode = cvars["LND_GRID_MODE"].value
        custom_grid_path = Path(cvars["CUSTOM_GRID_PATH"].value)
        if not custom_grid_path.exists():
            if ocn_grid_mode != "Standard" or lnd_grid_mode != "Standard":
                raise RuntimeError(f"Custom grid path {custom_grid_path} does not exist.")

        ocn_grid = None
        if ocn_grid_mode == "Standard":
            ocn_grid = cvars["CUSTOM_OCN_GRID"].value
        elif ocn_grid_mode in ["Modify Existing", "Create New"]:
            ocn_grid = cvars["CUSTOM_OCN_GRID_NAME"].value
        else:
            raise RuntimeError(f"Unknown ocean grid mode: {ocn_grid_mode}")
        if ocn_grid is None:
            raise RuntimeError("No ocean grid specified.")

        self._update_modelgrid_aliases(custom_grid_path, ocn_grid, do_exec)
        self._update_component_grids(custom_grid_path, ocn_grid, ocn_grid_mode, do_exec)

    def _update_modelgrid_aliases(self, custom_grid_path, ocn_grid, do_exec):
        """Update the modelgrid_aliases xml file with custom resolution information.
        This function is called before running create_newcase.

        Parameters
        ----------
        custom_grid_path : Path
            The path to the custom grid directory.
        ocn_grid : str
            The name of the custom ocean grid.
        do_exec : bool
            If True, execute the commands. If False, only print them.
            """

        resolution_name = custom_grid_path.name

        # Component grid names:
        atm_grid = cvars["CUSTOM_ATM_GRID"].value
        lnd_grid = cvars["CUSTOM_LND_GRID"].value
        # modelgrid_aliases xml file that stores resolutions:
        srcroot = self._cime.srcroot
        ccs_config_root = Path(srcroot) / "ccs_config"
        assert (
            ccs_config_root.exists()
        ), f"ccs_config_root {ccs_config_root} does not exist."
        modelgrid_aliases_xml = ccs_config_root / "modelgrid_aliases_nuopc.xml"
        assert (
            modelgrid_aliases_xml.exists()
        ), f"modelgrid_aliases_xml {modelgrid_aliases_xml} does not exist."
        modelgrid_aliases_xml = modelgrid_aliases_xml.as_posix()

        # confirm that modelgrid_aliases xml file is writeable:
        if not os.access(modelgrid_aliases_xml, os.W_OK):
            raise RuntimeError(f"Cannot write to {modelgrid_aliases_xml}.")

        # log the modification of modelgrid_aliases.xml:
        with self._out:
            print(
                f'{BPOINT} Updating ccs_config/modelgrid_aliases_nuopc.xml file to include the new '
                f'resolution "{resolution_name}" consisting of the following component grids.\n'
                f' atm grid: "{atm_grid}", lnd grid: "{lnd_grid}", ocn grid: "{ocn_grid}".\n'
            )

        # Read in xml file and generate grids object file:
        parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
        grids_tree = ET.parse(modelgrid_aliases_xml, parser=parser)
        grids_root = grids_tree.getroot()

        # Check if a resp;iton with the same name already exists. If so, remove it or raise an error
        # depending on the value of self._allow_xml_override:
        for resolution in grids_root.findall("model_grid"):
            if resolution.attrib["alias"] == resolution_name:
                if self._allow_xml_override:
                    grids_root.remove(resolution)
                else:
                    raise RuntimeError(
                        f"Resolution {resolution_name} already exists in modelgrid_aliases."
                    )

        # Create new resolution entry in xml file:
        new_resolution = SubElement(
            grids_root,
            "model_grid",
            attrib={"alias": resolution_name},
        )

        # Add component grids to resolution entry:
        new_atm_grid = SubElement(
            new_resolution,
            "grid",
            attrib={"name": "atm"},
        )
        new_atm_grid.text = atm_grid

        new_lnd_grid = SubElement(
            new_resolution,
            "grid",
            attrib={"name": "lnd"},
        )
        new_lnd_grid.text = lnd_grid

        new_ocnice_grid = SubElement(
            new_resolution,
            "grid",
            attrib={"name": "ocnice"},
        )
        new_ocnice_grid.text = ocn_grid

        if not do_exec:
            return

        # back up modelgrid_aliases.xml in case case creation fails:
        shutil.copy(
            Path(self._cime.srcroot) / "ccs_config/modelgrid_aliases_nuopc.xml",
            Path(self._cime.srcroot) / "ccs_config/modelgrid_aliases_nuopc.xml.orig",
        )

        # update modelgrid_aliases.xml to include new resolution:
        ET.indent(grids_tree)
        grids_tree.write(modelgrid_aliases_xml, encoding="utf-8", xml_declaration=True)

    def _update_component_grids(
        self, custom_grid_path, ocn_grid, ocn_grid_mode, do_exec
    ):
        """Update the component_grids xml file with custom ocnice grid information.
        This function is called before running create_newcase.

        Parameters
        ----------
        custom_grid_path : Path
            The path to the custom grid directory.
        ocn_grid : str
            The name of the custom ocean grid.
        ocn_grid_mode : str
            The ocean grid mode. It can be "Standard", "Modify Existing", or "Create New".
        do_exec : bool
            If True, execute the commands. If False, only print them.
        """

        if ocn_grid_mode == "Create New":
            ocn_dir = custom_grid_path / "ocnice"
            assert ocn_dir.exists(), f"Ocean grid directory {ocn_dir} does not exist."

            ocn_mesh = (
                ocn_dir / f"ESMF_mesh_{ocn_grid}_{cvars['MB_ATTEMPT_ID'].value}.nc"
            )
            assert ocn_mesh.exists(), f"Ocean mesh file {ocn_mesh} does not exist."

            # component_grids xml file that stores resolutions:
            srcroot = self._cime.srcroot
            ccs_config_root = Path(srcroot) / "ccs_config"
            assert (
                ccs_config_root.exists()
            ), f"ccs_config_root {ccs_config_root} does not exist."
            component_grids_xml = ccs_config_root / "component_grids_nuopc.xml"
            assert (
                component_grids_xml.exists()
            ), f"component_grids_xml {component_grids_xml} does not exist."
            component_grids_xml = component_grids_xml.as_posix()

            # confirm that component_grids xml file is writeable:
            if not os.access(component_grids_xml, os.W_OK):
                raise RuntimeError(f"Cannot write to {component_grids_xml}.")

            # log the modification of component_grids.xml:
            with self._out:
                print(
                    f'{BPOINT} Updating ccs_config/component_grids_nuopc.xml file to include '
                    f'newly generated ocean grid "{ocn_grid}" with the following properties:\n'
                    f' nx: {cvars["OCN_NX"].value}, ny: {cvars["OCN_NY"].value}.'
                    f' ocean mesh: {ocn_mesh}.{RESET}\n'
                )

            # Read in xml file and generate component_grids object file:
            parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
            domains_tree = ET.parse(component_grids_xml, parser=parser)
            # ET.indent(domains_tree, space="  ", level=0)
            domains_root = domains_tree.getroot()

            # Check if a domain with the same name already exists. If so, remove it or raise an error
            # depending on the value of self._allow_xml_override:
            for domain in domains_root.findall("domain"):
                if domain.attrib["name"] == ocn_grid:
                    if self._allow_xml_override:
                        domains_root.remove(domain)
                    else:
                        raise RuntimeError(
                            f"Ocean grid {ocn_grid} already exists in component_grids."
                        )

            # Create new domain entry in xml file:
            new_domain = SubElement(
                domains_root,
                "domain",
                attrib={"name": ocn_grid},
            )

            nx = SubElement(
                new_domain,
                "nx",
            )
            nx.text = str(cvars["OCN_NX"].value)

            ny = SubElement(
                new_domain,
                "ny",
            )
            ny.text = str(cvars["OCN_NY"].value)

            mesh = SubElement(
                new_domain,
                "mesh",
            )
            mesh.text = ocn_mesh.as_posix()

            desc = SubElement(
                new_domain,
                "desc",
            )
            desc.text = f"New ocean grid {ocn_grid} generated by mom6_bathy"

            if not do_exec:
                return

            shutil.copy(
                Path(self._cime.srcroot) / "ccs_config/component_grids_nuopc.xml",
                Path(self._cime.srcroot) / "ccs_config/component_grids_nuopc.xml.orig",
            )

            # write to xml file:
            ET.indent(domains_tree)
            domains_tree.write(
                component_grids_xml, encoding="utf-8", xml_declaration=True
            )

    def _run_create_newcase(self, caseroot, compset, resolution, do_exec):
        """Run CIME's create_newcase tool to create a new case instance.

        Parameters
        ----------
        caseroot : Path
            The path to the new case directory.
        compset : str
            The compset to use for the new case.
        resolution : str
            The resolution to use for the new case.
        do_exec : bool
            If True, execute the commands. If False, only print them.
        """

        # Determine machine:
        machine = cvars["MACHINE"].value

        # create new case command:
        cmd = (
            f"{self._cime.cimeroot}/scripts/create_newcase "
            + f"--compset {compset} "
            + f"--res {resolution} "
            + f"--case {caseroot} "
            + f"--machine {machine} "
            + "--run-unsupported "
        )

        # append project id if needed:
        if project := cvars["PROJECT"].value:
            cmd += f"--project {project} "

        # append number of model instances if needed:
        ninst = 1 if cvars["NINST"].value is None else cvars["NINST"].value
        if ninst != 1:
            cmd += f"--ninst {ninst} "

        # append --nonlocal if needed:
        if self._is_non_local():
            cmd += "--non-local "

        # log the command:
        with self._out:
            print(
                f"{COMMENT}Running the create_newcase tool with the following command:{RESET}\n"
            )
            print(f"{cmd}\n")

        # Run the create_newcase command:
        if do_exec:
            runout = subprocess.run(cmd, shell=True, capture_output=True)
            with self._out:
                if runout.returncode == 0:
                    print(f"{COMMENT}The create_newcase command was successful.{RESET}\n")
                else:
                    print(f"{ERROR}Error creating case.{RESET}\n")
                    print(f"{runout.stderr}\n")
            if runout.returncode != 0:
                raise RuntimeError("Error creating case.")

    def _apply_all_xmlchanges(self, do_exec):

        lnd_grid_mode = cvars["LND_GRID_MODE"].value
        if lnd_grid_mode == "Modified":
            if cvars["COMP_OCN"].value != "mom":
                with self._out:
                    print(f"{COMMENT}Apply custom land grid xml changes:{RESET}\n")

                # TODO: instead of xmlchanges, these changes should be made via adding the new lnd domain mesh to
                # component_grids_nuopc.xml and modelgrid_aliases_nuopc.xml (just like how we handle new ocean grids)

                # lnd domain mesh
                xmlchange("LND_DOMAIN_MESH", cvars["INPUT_MASK_MESH"].value, do_exec, self._is_non_local(), self._out)

                # mask mesh (if modified)
                base_lnd_grid = cvars["CUSTOM_LND_GRID"].value
                custom_grid_path = Path(cvars["CUSTOM_GRID_PATH"].value)
                lnd_dir = custom_grid_path / "lnd"
                modified_mask_mesh = lnd_dir / f"{base_lnd_grid}_mesh_mask_modifier.nc" # TODO: the way we get this filename is fragile
                assert modified_mask_mesh.exists(), f"Modified mask mesh file {modified_mask_mesh} does not exist."
                xmlchange("MASK_MESH", modified_mask_mesh, do_exec, self._is_non_local(), self._out)
        else:
            assert lnd_grid_mode in [None, "", "Standard"], f"Unknown land grid mode: {lnd_grid_mode}"

        # Set NTASKS based on grid size. e.g. NX * NY < max_pts_per_core
        num_points = int(cvars["OCN_NX"].value) * int(cvars["OCN_NY"].value)
        cores = CaseCreator._calc_cores_based_on_grid(num_points)
        with self._out:
            print(f"{COMMENT}Apply NTASK grid xml changes:{RESET}\n")
            xmlchange("NTASKS_OCN",cores, do_exec, self._is_non_local(), self._out)

    @staticmethod
    def _calc_cores_based_on_grid( num_points, min_points_per_core = 32, max_points_per_core = 800):
        """Calculate the number of cores based on the grid size."""


        cores = 128 # Start from 128 which is the default 128 cores per node in derecho
        iteration_amount = 16
        pts_per_core = num_points/float(cores)
        
        while pts_per_core > max_points_per_core:
            cores = cores + iteration_amount
            pts_per_core = num_points/cores

        while pts_per_core < min_points_per_core and cores > iteration_amount: # Don't let cores get below iteration amount
            cores = cores - iteration_amount
            pts_per_core = num_points/cores


        return cores

    def _apply_user_nl_changes(self, model, var_val_pairs, do_exec, comment=None, log_title=True):
        """Apply changes to a given user_nl file."""
        append_user_nl(model, var_val_pairs, do_exec, comment, log_title, self._out)

    def _apply_all_namelist_changes(self, do_exec):
        """Apply all the necessary user_nl changes to the case.

        Parameters
        ----------
        caseroot : Path
            The path to the case directory.
        do_exec : bool
            If True, execute the commands. If False, only print them.
        """

        # If standard grid is selected, no modifications are needed:
        grid_mode = cvars["GRID_MODE"].value
        if grid_mode == "Standard":
            return  # no modifications needed for standard grid
        else:
            assert grid_mode == "Custom", f"Unknown grid mode: {grid_mode}"

        self._apply_mom_namelist_changes(do_exec)
        self._apply_cice_namelist_changes(do_exec)
        self._apply_clm_namelist_changes(do_exec)

    def _apply_mom_namelist_changes(self, do_exec):
        """Apply all necessary changes to user_nl_mom and user_nl_cice files."""

        ocn_grid_mode = cvars["OCN_GRID_MODE"].value
        if ocn_grid_mode == "Standard":
            return # no modifications needed for standard ocean grid
        elif ocn_grid_mode == "Modify Existing":
            raise NotImplementedError("Modify Existing Ocean Grid not yet implemented.")
        else:
            assert (
                ocn_grid_mode == "Create New"
            ), f"Unknown ocean grid mode: {ocn_grid_mode}"

        supergrid_file_path = MOM6BathyLauncher.supergrid_file_path()
        topo_file_path = MOM6BathyLauncher.topo_file_path()
        vgrid_file_path = MOM6BathyLauncher.vgrid_file_path()
        ocn_grid_path = MOM6BathyLauncher.get_custom_ocn_grid_path()

        # read in min and max depth from the MOM6 topo file:
        ds_topo = xr.open_dataset(topo_file_path)
        min_depth = ds_topo.attrs["min_depth"]
        max_depth = ds_topo.attrs["max_depth"]

        # number of vertical levels:
        nk = len(xr.open_dataset(vgrid_file_path).dz)

        # Determine timesteps based on the grid resolution (assuming coupling frequency of 1800.0 sec):
        res_x = float(cvars['OCN_LENX'].value) / int(cvars["OCN_NX"].value)
        res_y = float(cvars['OCN_LENY'].value) / int(cvars["OCN_NY"].value)
        dt = 600.0 * min(res_x,res_y) # A 1-deg grid should have ~600 sec tstep (a safe value)
        # Make sure 1800.0 is a multiple of dt and dt is a power of 2 and/or 3:
        dt = min((1800.0 / n for n in [2**i * 3**j for i in range(10) for j in range(6)] if 1800.0 % n == 0), key=lambda x: abs(dt - x))
        # Try setting dt_therm to dt*4, or dt*3, or  dt*3, depending on whether 1800.0 becomes a multiple of dt:
        dt_therm = dt * 4 if 1800.0 % (dt*4) == 0 else dt * 3 if 1800.0 % (dt * 3) == 0 else dt * 2 if 1800.0 % (dt * 2) == 0 else dt

        # apply custom MOM6 grid changes:
        self._apply_user_nl_changes(
            "mom",
            [
                ("INPUTDIR", ocn_grid_path),
                ("TRIPOLAR_N", "False"),
                ("REENTRANT_X", cvars["OCN_CYCLIC_X"].value),
                ("REENTRANT_Y", "False"), # todo
                ("NIGLOBAL", cvars["OCN_NX"].value),
                ("NJGLOBAL", cvars["OCN_NY"].value),
                ("GRID_CONFIG", "mosaic"),
                ("GRID_FILE", supergrid_file_path.name),
                ("TOPO_CONFIG", "file"),
                ("TOPO_FILE", topo_file_path.name),
                ("MAXIMUM_DEPTH", max_depth),
                ("MINIMUM_DEPTH", min_depth),
                ("NK", nk),
                ("COORD_CONFIG", "none"),
                ("ALE_COORDINATE_CONFIG", f"FILE:{vgrid_file_path.name}"),
                ("REGRIDDING_COORDINATE_MODE", "Z*"),
            ],
            do_exec,
            comment="Custom Horizonal Grid, Topography, and Vertical Grid",
        )

        self._apply_user_nl_changes(
            "mom",
            [
                ("DT", str(dt)),
                ("DT_THERM", str(dt_therm)),
            ],
            do_exec,
            comment="Timesteps (based on grid resolution)",
            log_title=False,
        )

        # Set MOM6 Initial Conditions parameters:
        if cvars["OCN_IC_MODE"].value == "Simple":
            self._apply_user_nl_changes(
                "mom",
                [
                    ("TS_CONFIG", "fit"),
                    ("T_REF", cvars["T_REF"].value),
                    ("FIT_SALINITY", "True"),
                ],
                do_exec,
                comment="Simple Initial Conditions",
                log_title=False,
            )
        elif cvars["OCN_IC_MODE"].value == "From File":
            # First, copy the initial conditions file to INPUTDIR:
            temp_salt_z_init_file = Path(cvars["TEMP_SALT_Z_INIT_FILE"].value)
            if temp_salt_z_init_file.as_posix() == "TBD":
                pass # do nothing: TEMP_SALT_Z_INIT_FILE can only be set to TBD when visualCaseGen
                        # is used as an external tool by another application, in which case setting
                        # TEMP_SALT_Z_INIT_FILE to TBD is a signal from the external application that
                        # the initial conditions will be handled by the application itself.
            else:
                # Copy the initial conditions file to INPUTDIR:
                if temp_salt_z_init_file.name not in [f.name for f in ocn_grid_path.glob("*.nc")]:
                    shutil.copy(temp_salt_z_init_file, ocn_grid_path / temp_salt_z_init_file.name)
                # Apply the user_nl changes:
                self._apply_user_nl_changes(
                    "mom",
                    [
                        ("INIT_LAYERS_FROM_Z_FILE", "True"),
                        ("TEMP_SALT_Z_INIT_FILE", temp_salt_z_init_file.name),
                        ("Z_INIT_FILE_PTEMP_VAR", cvars["IC_PTEMP_NAME"].value),
                        ("Z_INIT_FILE_SALT_VAR", cvars["IC_SALT_NAME"].value),
                    ],
                    do_exec,
                    comment="Initial Conditions from File",
                    log_title=False,
                )
        else:
            raise RuntimeError(f"Unknown ocean initial conditions mode: {cvars['OCN_IC_MODE'].value}")

    def _apply_cice_namelist_changes(self, do_exec):
        """Apply all necessary changes to user_nl_cice file."""

        ocn_grid_mode = cvars["OCN_GRID_MODE"].value
        if ocn_grid_mode == "Standard":
            return # no modifications needed for standard ocean grid

        comp_ice = cvars["COMP_ICE"].value
        if not comp_ice.startswith("cice"):
            return

        cice_grid_file_path = MOM6BathyLauncher.cice_grid_file_path()
        self._apply_user_nl_changes(
            "cice",
            [
                ("grid_format", '"nc"'),
                ("grid_file", f'"{cice_grid_file_path}"'),
                ("kmt_file", f'"{cice_grid_file_path}"'),
            ],
            do_exec,
        )

    def _apply_clm_namelist_changes(self, do_exec):
        """Apply all necessary changes to user_nl_clm file."""

        lnd_grid_mode = cvars["LND_GRID_MODE"].value
        if lnd_grid_mode == "Standard":
            return
        assert lnd_grid_mode == "Modified", f"Unknown land grid mode: {lnd_grid_mode}"

        # TODO: below way of getting the modified fsurdat file path is fragile
        base_lnd_grid = cvars["CUSTOM_LND_GRID"].value
        custom_grid_path = Path(cvars["CUSTOM_GRID_PATH"].value)
        lnd_dir = custom_grid_path / "lnd"
        modified_fsurdat = lnd_dir / f"{base_lnd_grid}_fsurdat_modifier.nc"
        assert modified_fsurdat.exists(), f"Modified fsurdat file {modified_fsurdat} does not exist."

        # fsurdat:
        user_nl_clm_changes = [
            ("fsurdat", f'"{modified_fsurdat}"'),
        ]

        inittime = cvars["INITTIME"].value
        if inittime is None:
            inittime = cvars["COMPSET_LNAME"].value.split("_")[0]

        # For transient runs, we need to:
        #  - set check_dynpft_consistency to .false.
        #  - set flanduse_timeseries
        if inittime == "HIST" or "SSP" in inittime:

            flanduse_timeseries_path = self._cime.clm_flanduse[base_lnd_grid]
            assert flanduse_timeseries_path is not None, f"Land use timeseries file for {base_lnd_grid} not found."
            assert Path(flanduse_timeseries_path).exists(), f"Land use timeseries file {flanduse_timeseries_path} does not exist."

            user_nl_clm_changes.extend([
                ("check_dynpft_consistency", ".false."),
                #TODO:("flanduse_timeseries", f'"{flanduse_timeseries_path}"'),
                # as of cesm2_3alpha17b, there is an issue with flanduse_timeseries:
                # cft dimensions included in clm namelist xml files don't match the dimensions that clm expects: 64 vs 2.
            ])

        self._apply_user_nl_changes("clm", user_nl_clm_changes, do_exec)
