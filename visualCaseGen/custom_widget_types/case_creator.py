import os
import logging
from ipywidgets import VBox, HBox, Button, Output, Text
from pathlib import Path
import subprocess
import time
import shutil
from xml.etree.ElementTree import SubElement
import xml.etree.ElementTree as ET
import xarray as xr

from ProConPy.out_handler import handler as owh
from ProConPy.config_var import cvars
from ProConPy.dialog import alert_error
from visualCaseGen.custom_widget_types.mom6_bathy_launcher import MOM6BathyLauncher

COMMENT = "\033[01;96m"  # bold, cyan
SUCCESS = "\033[1;32m"  # bold, green
ERROR = "\033[1;31m"  # bold, red
RESET = "\033[0m"
BPOINT = "\u2022"


class CaseCreator(VBox):
    """A widget for creating a new case and applying initial modifications to it."""

    def __init__(self, cime, **kwargs):
        """Initialize the CaseCreator widget."""

        super().__init__(**kwargs)

        # A reference to the CIME instance
        self._cime = cime

        self._txt_project = Text(
            description="Project ID:",
            layout={"width": "250px", "margin": "10px"},  # If the items' names are long
            style={"description_width": "80px"},
        )

        cvars["CASEROOT"].observe(
            self._on_caseroot_change, names="value", type="change"
        )
        cvars["MACHINE"].observe(self._on_machine_change, names="value", type="change")

        self._btn_create_case = Button(
            description="Create Case",
            layout={"width": "160px", "margin": "5px"},
            button_style="success",
        )
        self._btn_create_case.on_click(self._create_case)

        self._btn_show_commands = Button(
            description="Show Commands",
            layout={"width": "160px", "margin": "5px"},
        )
        self._btn_show_commands.on_click(self._create_case)

        self._out = Output()

        self.children = [
            self._txt_project,
            HBox(
                [self._btn_create_case, self._btn_show_commands],
                layout={"display": "flex", "justify_content": "center"},
            ),
            self._out,
        ]

    @property
    def disabled(self):
        return super().disabled

    @disabled.setter
    def disabled(self, value):
        # disable/enable all children
        self._btn_create_case.disabled = value
        self._btn_show_commands.disabled = value
        self._txt_project.disabled = value
        if cvars["CASE_CREATOR_STATUS"].value != "OK":
            # clear only if the case creator wasn't completed
            self._out.clear_output()

    def _on_caseroot_change(self, change):
        """This function is called when the caseroot changes. It resets the output widget."""
        self._out.clear_output()

    def _on_machine_change(self, change):
        """This function is called when the machine changes. It resets the output widget.
        It also shows/hides the project ID text box based on whether the machine requires
        a project ID."""
        new_machine = change["new"]
        self._txt_project.value = ""
        project_required = self._cime.project_required.get(new_machine, False)
        if project_required:
            self._txt_project.layout.display = "flex"
        else:
            self._txt_project.layout.display = "none"
        self._out.clear_output()

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

    def _create_case(self, b=None):
        """The main function that creates the case and applies initial modifications to it.
        This function is called when the "Create Case" button or the "Show Commands" button
        is clicked.
        
        Parameters
        ----------
        b : Button
            The button that was clicked.
        """
        
        # Determine if the commands should be printed or executed:
        do_exec = b is not self._btn_show_commands

        self._out.clear_output()
        try:
            self._final_checks()
            self._do_create_case(do_exec)
        except Exception as e:
            with owh.out:
                alert_error(str(e))
            with self._out:
                print(f"{ERROR}{str(e)}{RESET}")
            self.revert_launch(do_exec)
            return

        if do_exec is True:
            # Set the case creator status to OK and thus complete all stages.
            # Remove the backup xml files
            self._remove_orig_xml_files()
            with owh.out:
                cvars["CASE_CREATOR_STATUS"].value = "OK"
            with self._out:
                caseroot = cvars["CASEROOT"].value
                print(
                    f"{SUCCESS}Case created successfully at {caseroot}.{RESET}\n\n"
                    f"{COMMENT}To further customize, build, and run the case, "
                    f"navigate to the case directory in your terminal. To create "
                    f"another case, restart the notebook.{RESET}\n"                   
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
            self._txt_project.value.strip() == ""
            and self._cime.project_required.get(cvars["MACHINE"].value, False) is True
        ):
            raise RuntimeError("No project specified yet.")

    def _do_create_case(self, do_exec):
        """Create and configure the case by running the necessary tools.

        Parameters
        ----------
        cime : CIME
            The CIME instance.
        do_exec : bool, optional
            If True, print and execute the commands. If False, only print them
        """

        # Determine compset:
        if cvars["COMPSET_MODE"].value == "Standard":
            compset = cvars["COMPSET_ALIAS"].value
        elif cvars["COMPSET_MODE"].value == "Custom":
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
        self._apply_xmlchanges(caseroot, do_exec)

        # Run case.setup
        self._run_case_setup(caseroot, do_exec)

        # Apply user_nl changes
        self._appy_user_nl_changes(caseroot, do_exec)


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

        # check if resolution is already in xml file:
        for resolution in grids_root.findall("model_grid"):
            if resolution.attrib["alias"] == resolution_name:
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

            # check if domain is already in xml file:
            for domain in domains_root.findall("domain"):
                if domain.attrib["name"] == ocn_grid:
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
        if self._txt_project.value.strip() != "":
            cmd += f"--project {self._txt_project.value.strip()} "

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

    def _apply_xmlchanges(self, caseroot, do_exec):

        def exec_xmlchange(var, val):

            cmd = f"./xmlchange {var}={val}"
            if self._is_non_local() is True:
                cmd += " --non-local"
            with self._out:
                print(f"{cmd}\n")

            if not do_exec:
                return

            runout = subprocess.run(cmd, shell=True, capture_output=True, cwd=caseroot)
            if runout.returncode != 0:
                raise RuntimeError(f"Error running {cmd}.")

        lnd_grid_mode = cvars["LND_GRID_MODE"].value
        if lnd_grid_mode == "Modified":
            if cvars["COMP_OCN"].value != "mom":
                with self._out:
                    print(f"{COMMENT}Apply custom land grid xml changes:{RESET}\n")

                # TODO: instead of xmlchanges, these changes should be made via adding the new lnd domain mesh to
                # component_grids_nuopc.xml and modelgrid_aliases_nuopc.xml (just like how we handle new ocean grids)

                # lnd domain mesh
                exec_xmlchange("LND_DOMAIN_MESH", cvars["INPUT_MASK_MESH"].value)

                # mask mesh (if modified)
                base_lnd_grid = cvars["CUSTOM_LND_GRID"].value
                custom_grid_path = Path(cvars["CUSTOM_GRID_PATH"].value)
                lnd_dir = custom_grid_path / "lnd"
                modified_mask_mesh = lnd_dir / f"{base_lnd_grid}_mesh_mask_modifier.nc" # TODO: the way we get this filename is fragile
                assert modified_mask_mesh.exists(), f"Modified mask mesh file {modified_mask_mesh} does not exist."
                exec_xmlchange("MASK_MESH", modified_mask_mesh)
        else:
            assert lnd_grid_mode in [None, "", "Standard"], f"Unknown land grid mode: {lnd_grid_mode}"
            
    def _run_case_setup(self, caseroot, do_exec):
        """Run the case.setup script to set up the case instance.
        
        Parameters
        ----------
        caseroot : Path
            The path to the case directory.
        do_exec : bool
            If True, execute the commands. If False, only print them.    
        """

        # Run ./case.setup
        cmd = "./case.setup"
        if self._is_non_local():
            cmd += " --non-local"
        with self._out:
            print(
                f"{COMMENT}Running the case.setup script with the following command:{RESET}\n"
            )
            print(f"{cmd}\n")
        if do_exec:
            runout = subprocess.run(cmd, shell=True, capture_output=True, cwd=caseroot)
            if runout.returncode != 0:
                raise RuntimeError(f"Error running {cmd}.")

    def _apply_user_nl(self, user_nl_filename, var_val_pairs, do_exec):
        """Apply changes to a given user_nl file.
        
        Parameters
        ----------
        user_nl_filename : str
            The name of the user_nl file to modify.
        var_val_pairs : list of tuples
            A list of tuples, where each tuple contains a variable name and its value.
        do_exec : bool
            If True, execute the commands. If False, only print them.
        """

        # confirm var_val_pairs is a list of tuples:
        assert isinstance(var_val_pairs, list)
        assert all(isinstance(pair, tuple) for pair in var_val_pairs)

        with self._out:
            print(f"{COMMENT}Adding parameter changes to {user_nl_filename}:{RESET}\n")
            for var, val in var_val_pairs:
                print(f"  {var} = {val}")
            print("")
        if not do_exec:
            return
        caseroot = cvars["CASEROOT"].value
        with open(Path(caseroot) / user_nl_filename, "a") as f:
            for var, val in var_val_pairs:
                f.write(f"{var} = {val}\n")


    def _appy_user_nl_changes(self, caseroot, do_exec):
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

        self._apply_user_nl_mom_changes(do_exec)
        self._apply_user_nl_cice_changes(do_exec)
        self._apply_user_nl_clm_changes(do_exec)

    def _apply_user_nl_mom_changes(self, do_exec):
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
        supergrid_file_name = supergrid_file_path.name
        topo_file_path = MOM6BathyLauncher.topo_file_path()
        topo_file_name = topo_file_path.name
        ocn_grid_path = MOM6BathyLauncher.get_custom_ocn_grid_path()

        # read in min and max depth from the MOM6 topo file:
        ds_topo = xr.open_dataset(topo_file_path)
        min_depth = ds_topo.attrs["min_depth"]
        max_depth = ds_topo.attrs["max_depth"]

        # apply custom MOM6 grid changes:
        self._apply_user_nl(
            "user_nl_mom",
            [
                ("INPUTDIR", ocn_grid_path),
                ("TRIPOLAR_N", "False"),
                ("REENTRANT_X", cvars["OCN_CYCLIC_X"].value),
                ("REENTRANT_Y", "False"), # todo
                ("NIGLOBAL", cvars["OCN_NX"].value),
                ("NJGLOBAL", cvars["OCN_NY"].value),
                ("GRID_CONFIG", "mosaic"),
                ("TOPO_CONFIG", "file"),
                ("MAXIMUM_DEPTH", max_depth),
                ("MINIMUM_DEPTH", min_depth),
                ("DT", "900"),  # TODO: generalize this
                ("NK", "20"),  # TODO: generalize this
                ("COORD_CONFIG", "none"),
                ("REGRIDDING_COORDINATE_MODE", "Z*"),
                ("ALE_COORDINATE_CONFIG", "UNIFORM"),
                ("TS_CONFIG", "fit"),
                ("T_REF", 5.0),  # TODO: generalize this
                ("FIT_SALINITY", "True"),
                ("GRID_FILE", supergrid_file_name),
                ("TOPO_FILE", topo_file_name),
            ],
            do_exec,
        )

    def _apply_user_nl_cice_changes(self, do_exec):
        """Apply all necessary changes to user_nl_cice file."""

        ocn_grid_mode = cvars["OCN_GRID_MODE"].value
        if ocn_grid_mode == "Standard":
            return # no modifications needed for standard ocean grid

        comp_ice = cvars["COMP_ICE"].value
        if not comp_ice.startswith("cice"):
            return

        cice_grid_file_path = MOM6BathyLauncher.cice_grid_file_path()
        self._apply_user_nl(
            "user_nl_cice",
            [
                ("grid_format", '"nc"'),
                ("grid_file", f'"{cice_grid_file_path}"'),
                ("kmt_file", f'"{cice_grid_file_path}"'),
            ],
            do_exec,
        )

    def _apply_user_nl_clm_changes(self, do_exec):
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

        self._apply_user_nl("user_nl_clm", user_nl_clm_changes, do_exec)
        
