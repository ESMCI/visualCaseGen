import os
import logging
from ipywidgets import VBox, HBox, Button, Output, Text
from pathlib import Path
import subprocess
import time
import shutil
from xml.etree.ElementTree import SubElement
import xml.etree.ElementTree as ET

from ProConPy.out_handler import handler as owh
from ProConPy.config_var import cvars
from ProConPy.dialog import alert_warning, alert_error

COMMENT = "\033[1;37m"  # bold, light gray
SUCCESS = "\033[1;32m"  # bold, green
ERROR = "\033[1;31m"  # bold, red
RESET = "\033[0m"


class CaseCreator(VBox):
    def __init__(self, cime, **kwargs):

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
        cvars["MACHINE"].observe(
            self._on_machine_change, names="value", type="change"
        )

        self._btn_create_case = Button(
            description="Create Case",
            layout={"width": "160px", "margin": "5px"},
            button_style="success",
        )
        self._btn_create_case.on_click(lambda b: self._create_case(b, do_exec=True))

        self._btn_show_commands = Button(
            description="Show Commands",
            layout={"width": "160px", "margin": "5px"},
        )
        self._btn_show_commands.on_click(lambda b: self._create_case(b, do_exec=False))

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
        if cvars['CASE_CREATOR_STATUS'].value != 'OK':
            # clear only if the case creator wasn't completed
            self._out.clear_output()

    def revert_launch(self, do_exec=True):
        """This function is called when the case creation fails. It reverts the changes made to the
        ccs_config xml files and resets the output widget."""
        self._restore_orig_xml_files()

    def _restore_orig_xml_files(self):
        """When a case creation fails, restore the backup xml files."""
        if (
            orig := (
                Path(self._cime.srcroot) / "ccs_config/modelgrid_aliases_nuopc.xml.orig"
            )
        ).exists():
            shutil.move(orig, Path(self._cime.srcroot) / "ccs_config/modelgrid_aliases_nuopc.xml")
        if (
            orig := (
                Path(self._cime.srcroot) / "ccs_config/component_grids_nuopc.xml.orig"
            )
        ).exists():
            shutil.move(orig, Path(self._cime.srcroot) / "ccs_config/component_grids_nuopc.xml")

    def _on_caseroot_change(self, change):
        self._out.clear_output()

    def _on_machine_change(self, change):
        new_machine = change["new"]
        self._txt_project.value = ""
        project_required = self._cime.project_required.get(new_machine, False)
        if project_required:
            self._txt_project.layout.display = "flex"
        else:
            self._txt_project.layout.display = "none"
        self._out.clear_output()

    def _create_case(self, b, do_exec=True):
        self._out.clear_output()
        try:
            self._final_checks()
            self._do_create_case(do_exec)
        except Exception as e:
            self.error(str(e))
            self.revert_launch(do_exec)
            return

        if do_exec is True:
            # Set the case creator status to OK and thus complete all stages.
            # Remove the backup xml files
            self._remove_orig_xml_files()
            with owh.out:
                cvars['CASE_CREATOR_STATUS'].value = 'OK' 
            with self._out:
                print(f"{COMMENT}To create another case, please restart the notebook.{RESET}\n")
        

    def _remove_orig_xml_files(self):
        """When a case is created successfully, remove the backup xml files."""
        if (
            orig := (
                Path(self._cime.srcroot) / "ccs_config/modelgrid_aliases_nuopc.xml.orig"
            )
        ).exists():
            os.remove(orig)
        if (
            orig := (
                Path(self._cime.srcroot) / "ccs_config/component_grids_nuopc.xml.orig"
            )
        ).exists():
            os.remove(orig)

    @owh.out.capture()
    def error(self, msg):
        alert_error(msg)

    def _final_checks(self):

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
        return True

    def _do_create_case(self, do_exec):
        """Create the case.

        Parameters
        ----------
        cime : CIME
            The CIME instance.
        do_exec : bool, optional
            If True, print and execute the commands. If False, only print them. Default is False.
        """

        # Determine compset:
        if cvars["COMPSET_MODE"].value == "Standard":
            compset = cvars["COMPSET_ALIAS"].value
        elif cvars["COMPSET_MODE"].value == "Custom":
            compset = cvars["COMPSET_LNAME"].value
        else:
            raise RuntimeError(f"Unknown compset mode: {cvars['COMPSET_MODE'].value}")

        # Determine caseroot
        caseroot = Path(cvars["CASEROOT"].value)
        if not caseroot.is_absolute():
            caseroot = Path.home() / caseroot

        # check if the user has write permissions in the specified case directory
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

        # Determine machine:
        machine = cvars["MACHINE"].value
        is_nonlocal = self._cime.machine is not None and self._cime.machine != machine

        with self._out:
            print(f"{COMMENT}Creating case...{RESET}\n")

        # First, update ccs_config xml files to add custom grid information if needed:
        self._update_ccs_config(do_exec)

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
        if is_nonlocal:
            cmd += "--nonlocal "

        # log the command:
        with self._out:
            print(
                f"{COMMENT}Run the create_newcase tool with the following command:{RESET}\n"
            )
            print(f"$ {cmd}\n")

        if do_exec:
            runout = subprocess.run(cmd, shell=True, capture_output=True)
            with self._out:
                if runout.returncode == 0:
                    print(f"{SUCCESS}Case created successfully at {caseroot}.{RESET}\n")
                else:
                    print(f"{ERROR}Error creating case.{RESET}\n")
                    print(f"{runout.stderr}\n")
            if runout.returncode != 0:
                raise RuntimeError("Error creating case.")
                    
                
    def _update_ccs_config(self, do_exec):

        # If Custom grid is selected, update modelgrid_aliases and component_grids xml files:
        if cvars["GRID_MODE"].value == "Standard":
            return
        else:
            assert (
                cvars["GRID_MODE"].value == "Custom"
            ), f"Unknown grid mode: {cvars['GRID_MODE'].value}"

        # check if custom grid path exists:
        custom_grid_path = Path(cvars["CUSTOM_GRID_PATH"].value)
        if not custom_grid_path.exists():
            raise RuntimeError(f"Custom grid path {custom_grid_path} does not exist.")

        ocn_grid = None
        ocn_grid_mode = cvars["OCN_GRID_MODE"].value
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
                f"{COMMENT}Update modelgrid_aliases.xml with resolution {resolution_name}."
                f" Atm grid: {atm_grid}, Lnd grid: {lnd_grid}, Ocn grid: {ocn_grid}.{RESET}\n"
            )

        # Read in xml file and generate grids object file:
        grids_tree = ET.parse(modelgrid_aliases_xml)
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
        grids_tree.write(modelgrid_aliases_xml)

    def _update_component_grids(
        self, custom_grid_path, ocn_grid, ocn_grid_mode, do_exec
    ):

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
                    f"{COMMENT}Update component_grids.xml with ocean grid {ocn_grid}."
                    f" nx: {cvars['OCN_NX'].value}, ny: {cvars['OCN_NY'].value}."
                    f" Ocean mesh: {ocn_mesh}.{RESET}\n"
                )

            # Read in xml file and generate component_grids object file:
            domains_tree = ET.parse(component_grids_xml)
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
            domains_tree.write(component_grids_xml)
