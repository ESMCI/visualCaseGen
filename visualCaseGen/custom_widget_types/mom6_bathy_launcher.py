import os
import logging
import uuid
import nbformat as nbf
from IPython.display import display, Javascript
from pathlib import Path
from ipywidgets import VBox, Button, Output

from ProConPy.out_handler import handler as owh
from ProConPy.dialog import alert_warning
from ProConPy.config_var import cvars
from ProConPy.stage import Stage

logger = logging.getLogger("\t" + __name__.split(".")[-1])


class MOM6BathyLauncher(VBox):
    """A widget to create and launch a new mom6_bathy notebook. The widget is enabled when all the
    required parameters for mom6_bathy are set."""

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        cvars['MB_ATTEMPT_ID'].value = None
        self.required_mom6_bathy_vars = [
            cvars["CUSTOM_GRID_PATH"],
            cvars["OCN_GRID_MODE"],
            cvars["OCN_NX"],
            cvars["OCN_NY"],
            cvars["OCN_LENX"],
            cvars["OCN_LENY"],
            cvars["OCN_CYCLIC_X"],
            cvars["CUSTOM_OCN_GRID_NAME"],
        ]

        # observe changes in the required variables
        for var in self.required_mom6_bathy_vars:
            var._widget.observe(self._on_required_var_change, names="_property_lock", type="change")

        # Create the main child widgets: Launcg button, Output, and Confirm button

        self._btn_launch_mom6_bathy = Button(
            description="Launch mom6_bathy",
            button_style="success",
            layout={"width": "160px", "margin": "10px", "align_self": "center"},
        )
        self._btn_launch_mom6_bathy.on_click(self._on_btn_launch_clicked)

        self._out = Output()

        self._btn_confirm_completion = Button(
            description="Confirm completion",
            layout={
                "width": "max-content",
                "margin": "10px",
                "align_self": "center",
                "display": "none",
            },
        )
        self._btn_confirm_completion.on_click(self._on_btn_confirm_completion_clicked)

        self.children = [
            self._btn_launch_mom6_bathy,
            self._out,
            self._btn_confirm_completion,
        ]

    @property
    def disabled(self):
        return super().disabled

    @disabled.setter
    def disabled(self, value):
        self._out.clear_output()
        self._btn_launch_mom6_bathy.disabled = value
        self._btn_confirm_completion.disabled = value

    @staticmethod
    def get_custom_ocn_grid_path():
        """Return the path to the directory where the custom ocean grid files are to be stored."""
        custom_grid_path = cvars["CUSTOM_GRID_PATH"].value
        return Path(custom_grid_path) / "ocnice"

    def _on_required_var_change(self, change):
        """If any of the required variables are changed, reset the attempt id and mom6_bathy_status."""
        self._btn_confirm_completion.layout.display = "none"
        cvars['MB_ATTEMPT_ID'].value = None
        cvars["MOM6_BATHY_STATUS"].value = None
        self._out.clear_output()

    @owh.out.capture()
    def _on_btn_launch_clicked(self, b):
        """Function to launch the mom6_bathy notebook. The function first checks if all the required
        parameters are set. If not, it displays a warning message. If all required parameters are set,
        it generates a new mom6_bathy notebook and opens it in a new tab. The user is then prompted to
        execute the notebook and confirm completion. Once the notebook is executed, the user can click
        the "Confirm completion" button to proceed to the next stage."""

        if any(var.value is None for var in self.required_mom6_bathy_vars):
            remaining_params = [
                var.name for var in self.required_mom6_bathy_vars if var.value is None
            ]
            alert_warning(
                f"Please specify all the required parameters before launching mom6_bathy: {remaining_params}"
            )
            return

        # Reset the attempt_id and mom6_bathy_status
        new_attempt_id = str(uuid.uuid1())[:6]
        cvars['MB_ATTEMPT_ID'].value = new_attempt_id
        cvars["MOM6_BATHY_STATUS"].value = None

        # Determine the path to the new notebook
        custom_ocn_grid_name = cvars["CUSTOM_OCN_GRID_NAME"].value
        nb_path = (
            Path("mom6_bathy_notebooks") / f"mom6_bathy_{custom_ocn_grid_name}_{new_attempt_id}.ipynb"
        )

        # Launch the mom6_bathy notebook
        self._launch_mom6_bathy(nb_path)

        # Display a message to the user in the output widget
        with self._out:
            self._out.clear_output()
            print(
                'Note: Clicking the "Launch mom6_bathy" button generates a new notebook that '
                "should open in a new tab automatically. If not, try manually opening the notebook "
                f"at the following location: {nb_path}. Follow the instructions and run all cells "
                'in the notebook. Once done, click the "Confirm completion" button to proceed.'
            )

        # Display the confirm completion button
        self._btn_confirm_completion.layout.display = ""

    @owh.out.capture()
    def _on_btn_confirm_completion_clicked(self, b):
        """Function to confirm completion of mom6_bathy. The function checks if all the required
        files are created. If so, it confirms completion of mom6_bathy. If not, it displays a
        warning message."""

        custom_ocn_grid_path = MOM6BathyLauncher.get_custom_ocn_grid_path()
        if custom_ocn_grid_path is None:
            alert_warning(
                "No custom_ocn_grid_path found. Cannot confirm completion of mom6_bathy"
            )
            return

        attempt_id = cvars['MB_ATTEMPT_ID'].value
        if attempt_id is None:
            alert_warning(
                "No attempt_id found. Cannot confirm completion of mom6_bathy"
            )
            return

        # required files:
        custom_ocn_grid_name = cvars["CUSTOM_OCN_GRID_NAME"].value

        warning_msg = (
            "Cannot confirm completion of mom6_bathy. Make sure you've executed all "
            + "of the cells in the mom6_bathy notebook. The following file is missing: "
        )

        # See if all required files are created:
        mom6_supergrid_file = MOM6BathyLauncher.supergrid_file_path()
        mom6_topog_file = MOM6BathyLauncher.topo_file_path()
        esmf_mesh_file = MOM6BathyLauncher.esmf_mesh_file_path()
        cice_grid_file = MOM6BathyLauncher.cice_grid_file_path()
        required_files = [mom6_supergrid_file, mom6_topog_file, esmf_mesh_file]
        if "CICE" in cvars["COMP_ICE_PHYS"].value:
            required_files.append(cice_grid_file)

        for file in required_files:
            if not file.exists():
                alert_warning(warning_msg + f"{file}")
                return

        # If all files are found, confirm completion
        logger.info(f"Confirmed completion of mom6_bathy for {custom_ocn_grid_name}")
        cvars["MOM6_BATHY_STATUS"].value = None
        cvars["MOM6_BATHY_STATUS"].value = "Complete"

        # Proceed to the next stage
        Stage.proceed()

    def _launch_mom6_bathy(self, nb_filepath):
        """Generate a new mom6_bathy notebook and open it in a new tab. This method gets called when
        the user clicks the "Launch mom6_bathy" button."""
        nb = MOM6BathyLauncher._create_notebook_object()
        MOM6BathyLauncher._write_notebook(nb, nb_filepath)
        MOM6BathyLauncher._open_notebook_in_browser(nb_filepath)

    @staticmethod
    def _create_notebook_object():
        """Create a mom6_bathy notebook object based on the current values of the required variables.

        Returns
        -------
        nb : nbformat.notebooknode.NotebookNode
            A new notebook object with the required cells to create a new ocean grid and bathymetry.
        """

        ocn_grid_mode = cvars["OCN_GRID_MODE"].value
        nx = cvars["OCN_NX"].value
        ny = cvars["OCN_NY"].value
        lenx = cvars["OCN_LENX"].value
        leny = cvars["OCN_LENY"].value
        cyclic_x = cvars["OCN_CYCLIC_X"].value
        ocn_grid_name = cvars["CUSTOM_OCN_GRID_NAME"].value
        attempt_id = cvars['MB_ATTEMPT_ID'].value

        # if custom_grid_path doesn't exist, create it:
        custom_ocn_grid_path = MOM6BathyLauncher.get_custom_ocn_grid_path()
        os.makedirs(custom_ocn_grid_path, exist_ok=True)

        # Create a new notebook:
        nb = nbf.v4.new_notebook()

        nb["cells"] = [
            nbf.v4.new_markdown_cell(
                "# mom6_bathy\n"
                "This notebook is auto-generated by visualCaseGen. "
                "Please review and execute the cells below to create the new MOM6 grid and bathymetry. "
                "You can modify the cells as needed, unless otherwise noted, to customize the grid "
                "and bathymetry."
            ),
            nbf.v4.new_markdown_cell("## 1. Import mom6_bathy"),
            nbf.v4.new_code_cell(
                "%%capture\n"
                "from mom6_bathy.grid import Grid\n"
                "from mom6_bathy.topo import Topo\n"
                "from mom6_bathy.vgrid import VGrid"
            ),
            nbf.v4.new_markdown_cell("## 2. Create horizontal grid\n"),
        ]

        if ocn_grid_mode == "Create New":
            nb["cells"].extend([
                nbf.v4.new_code_cell(
                f'# Do NOT modify this cell!\n'
                f'grid = Grid(\n'
                f'  nx         = {nx},          # Number of grid points in x direction\n'
                f'  ny         = {ny},          # Number of grid points in y direction\n'
                f'  lenx       = {lenx},        # grid length in x direction (degrees).\n'
                f'  leny       = {leny},        # grid length in y direction (degrees).\n'
                f'  cyclic_x   = {True if cyclic_x == "True" else False},\n'
                f')'
                )
            ])
        elif ocn_grid_mode == "Modify Existing":
            raise NotImplementedError(
                "Modify Existing ocean grid mode is not yet implemented"
            )
        else:
            raise ValueError("Invalid ocean grid mode")

        nb["cells"].append(nbf.v4.new_markdown_cell("## 3. Configure bathymetry\n"))

        if ocn_grid_mode == "Create New":
            nb["cells"].extend(
                [
                    nbf.v4.new_markdown_cell(
                        "***mom6_bathy*** provides several idealized bathymetry options and customization "
                        "methods. Below, we show how to specify the simplest bathymetry configuration, a "
                        "flat bottom. Customize it as you see fit. See mom6_bathy documentation and "
                        "example notebooks on how to create custom bathymetries. "
                    ),
                    nbf.v4.new_code_cell(
                        "# Instantiate the bathymetry object\n"
                        "topo = Topo(grid, min_depth = 10.0)"
                    ),
                    nbf.v4.new_code_cell(
                        "# Set the bathymetry to be a flat bottom with a uniform depth of 2000m\n"
                        "topo.set_flat(D=2000.0)"
                    ),
                ]
            )
        elif ocn_grid_mode == "Modify Existing":
            raise NotImplementedError(
                "Modify Existing ocean grid mode is not yet implemented"
            )
        else:
            raise ValueError("Invalid ocean grid mode")

        nb["cells"].extend(
            [
                nbf.v4.new_code_cell("topo.depth.plot()"),
                nbf.v4.new_code_cell(
                    "# Manually modify the bathymetry\n"
                    "%matplotlib ipympl\n"
                    "from mom6_bathy.topo_editor import TopoEditor\n"
                    "TopoEditor(topo)"
                ),
            ]
        )

        vgrid_cmd = (
            "# Create a vertical grid\n"
            "vgrid = VGrid.hyperbolic(\n"
            "  nk    = 20,             # number of layers \n"
            "  depth = topo.max_depth, # Do NOT modify this argument \n"
            "  ratio = 10.0, # ratio of top to bottom layer thicknesses (=1.0 for uniform layers)\n"
            ")\n"
            "print('layer thicknesses:', vgrid.dz)"
        )

        nb["cells"].extend(
            [
                nbf.v4.new_markdown_cell("## 4. Create vertical grid"),
                nbf.v4.new_code_cell(vgrid_cmd),
            ]
        )

        save_files_cmd = (
            "# Do NOT modify this cell!\n\n"
            "# MOM6 supergrid file.\n"
            f'grid.write_supergrid(f"{custom_ocn_grid_path}/ocean_hgrid_{ocn_grid_name}_{attempt_id}.nc")\n\n'
            "# Save MOM6 topography file:\n"
            f'topo.write_topo(f"{custom_ocn_grid_path}/ocean_topog_{ocn_grid_name}_{attempt_id}.nc")\n\n'
            "# Save MOM6 vertical grid file:\n"
            f'vgrid.write(f"{custom_ocn_grid_path}/ocean_vgrid_{ocn_grid_name}_{attempt_id}.nc")\n\n'
        )

        if "CICE" in cvars["COMP_ICE_PHYS"].value:
            save_files_cmd += (
                "# CICE grid file:\n"
                f'topo.write_cice_grid(f"{custom_ocn_grid_path}/cice_grid.{ocn_grid_name}_{attempt_id}.nc")\n\n'
            )

        save_files_cmd += (
            "# Save ESMF mesh file:\n"
            f'topo.write_esmf_mesh(f"{custom_ocn_grid_path}/ESMF_mesh_{ocn_grid_name}_{attempt_id}.nc")'
        )

        nb["cells"].extend(
            [
                nbf.v4.new_markdown_cell("## 5. Save the grid, bathymetry, and mesh files"),
                nbf.v4.new_code_cell(save_files_cmd),
            ]
        )

        nb["cells"].append(
            nbf.v4.new_markdown_cell(
                "If all cells have been executed successfully, you can return to visualCaseGen and "
                "click the 'Confirm completion' button to proceed to the next stage."
            )
        )

        return nb

    def _write_notebook(nb, nb_filepath):
        """Write the new mom6_bathy notebook to the specified file path. If the directory doesn't
        exist, it is created. The notebook is then written to the file path."""
        os.makedirs(nb_filepath.parent, exist_ok=True)

        with open(nb_filepath, "w") as f:
            nbf.write(nb, f)

        logger.info(f"Generated a new mom6_bathy notebook at {nb_filepath}")

        return nb_filepath

    def _open_notebook_in_browser(nb_filepath):
        """Open the new mom6_bathy notebook in the browser. This function is called after the notebook
        is generated. It opens the notebook in a new tab in the browser."""

        # Open the new notebook in the browser
        js = f"""
            var curr_url = window.location.href.split('/')
            var new_url = curr_url[0] + '//'
            let update_url = true
            for (var i = 1; i < curr_url.length; i++) {{
                console.log(curr_url[i], new_url)
                if (!curr_url[i].endsWith("ipynb")) {{
                    new_url += curr_url[i] + '/'
                }}
                if (curr_url[i] === "tree") {{
                    update_url = false
                }}
            }}
        
            if (update_url === true) {{
                new_url += "tree/"
            }}
        
            new_url += "{nb_filepath}"
            window.open(new_url)
        """
        display(Javascript(js))
    
    @staticmethod
    def nc_file_suffix():
        custom_ocn_grid_name = cvars["CUSTOM_OCN_GRID_NAME"].value
        attempt_id = cvars['MB_ATTEMPT_ID'].value
        return f"{custom_ocn_grid_name}_{attempt_id}.nc"

    @staticmethod
    def supergrid_file_path():
        custom_ocn_grid_path = MOM6BathyLauncher.get_custom_ocn_grid_path()
        return custom_ocn_grid_path / f"ocean_hgrid_{MOM6BathyLauncher.nc_file_suffix()}"
    
    @staticmethod
    def topo_file_path():
        custom_ocn_grid_path = MOM6BathyLauncher.get_custom_ocn_grid_path()
        return custom_ocn_grid_path / f"ocean_topog_{MOM6BathyLauncher.nc_file_suffix()}"

    @staticmethod
    def vgrid_file_path():
        custom_ocn_grid_path = MOM6BathyLauncher.get_custom_ocn_grid_path()
        return custom_ocn_grid_path / f"ocean_vgrid_{MOM6BathyLauncher.nc_file_suffix()}"

    @staticmethod
    def esmf_mesh_file_path():
        custom_ocn_grid_path = MOM6BathyLauncher.get_custom_ocn_grid_path()
        return custom_ocn_grid_path / f"ESMF_mesh_{MOM6BathyLauncher.nc_file_suffix()}"
    
    @staticmethod
    def cice_grid_file_path():
        custom_ocn_grid_path = MOM6BathyLauncher.get_custom_ocn_grid_path()
        return custom_ocn_grid_path / f"cice_grid.{MOM6BathyLauncher.nc_file_suffix()}"
