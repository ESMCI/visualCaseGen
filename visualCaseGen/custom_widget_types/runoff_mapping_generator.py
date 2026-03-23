import os
from ipywidgets import HBox, VBox, Button, Output, Label
from pathlib import Path

from ProConPy.out_handler import handler as owh
from ProConPy.config_var import cvars
from ProConPy.dialog import alert_warning
from mom6_bathy import mapping
from visualCaseGen.custom_widget_types.mom6_bathy_launcher import MOM6BathyLauncher

class RunoffMappingGenerator(VBox):
    """Widget to generate runoff to ocean mapping for custom grids.
    The widget first checks if there exists a standard mapping between the selected
    runoff grid and the custom ocean grid. If not, it allows the user to generate
    a new mapping using the mom6_bathy mapping module.
    """

    def __init__(self, cime, **kwargs):
        super().__init__(**kwargs)
        self.cime = cime

        self._btn_use_standard = Button(
            description="Use Standard Map",
            disabled=True,
            tooltip="Use the standard mapping files already available for the selected grids.",
        )
        self._btn_use_standard.on_click(self.on_btn_use_standard_clicked)

        self._btn_generate_new = Button(
            description="Generate New Map",
            disabled=False,
            tooltip="Generate a new mapping file using the mom6_bathy mapping module.",
        )
        self._btn_generate_new.on_click(self.on_btn_generate_new_clicked)

        self._out = Output()

        self._btn_run_generate = Button(
            description="Run mapping generator",
            disabled=False,
            button_style="success",
            tooltip="Run the mapping generator with the specified parameters.",
            layout={"width": "260px", "align_self": "center"},
        )
        self._btn_run_generate.on_click(self.on_btn_run_generate_clicked)

        self._generate_new_dialog = VBox([
            cvars["ROF_OCN_MAPPING_RMAX"].widget,
            cvars["ROF_OCN_MAPPING_FOLD"].widget,
            self._btn_run_generate,
            self._out
        ],
        layout={"display": "none"}
        )

        self.children = [
            HBox([
                Label("Select mapping option:"),
                self._btn_use_standard,
                self._btn_generate_new
            ],
            layout={"justify_content": "center", "margin": "10px"}
            ),
            self._generate_new_dialog
        ]

        # Reset the widget when the runoff grid changes
        cvars["CUSTOM_ROF_GRID"].observe(self.reset, names='value', type='change')

    @property
    def disabled(self):
        return super().disabled

    @disabled.setter
    def disabled(self, value):
        self._btn_use_standard.disabled = value or not self.standard_map_exists()
        self._btn_generate_new.disabled = value
        for child in self._generate_new_dialog.children:
            child.disabled = value

    def reset(self, change):
        """Reset all widget children and auxiliary config variables. To be called
        when the runoff grid changes."""
        self._out.clear_output()
        self._generate_new_dialog.layout.display = "none"
        cvars["ROF_OCN_MAPPING_RMAX"].value = None
        cvars["ROF_OCN_MAPPING_FOLD"].value = None

    def standard_map_exists(self):
        """Check if there exists a standard mapping between the selected
        runoff grid and the custom ocean grid.
        """
        if cvars["OCN_GRID_MODE"].value != "Standard":
           return False

        rof_grid = cvars["CUSTOM_ROF_GRID"].value
        ocn_grid = cvars["CUSTOM_OCN_GRID"].value

        if ocn_grid in self.cime.maps[rof_grid]:
            return True

        return False

    @owh.out.capture()
    def on_btn_use_standard_clicked(self, b):
        """Handler for the 'Use Standard Map' button click event.
        Sets the ROF_OCN_MAPPING_STATUS variable to indicate that
        the standard mapping will be used.
        """

        if not self.standard_map_exists():
            alert_warning(
                "No standard mapping exists between the selected runoff grid "
                "and the custom ocean grid. Please generate a new mapping."
            )
            return

        self._out.clear_output()
        self._generate_new_dialog.layout.display = "none"
        cvars["ROF_OCN_MAPPING_STATUS"].value = "Standard"


    def get_rof_grid_and_mesh(self):
        """Return the runoff grid name and mesh path."""

        rof_grid = cvars["CUSTOM_ROF_GRID"].value
        rof_mesh_path = self.cime.get_mesh_path("rof", rof_grid)
        return rof_grid, rof_mesh_path

    def get_ocn_grid_and_mesh(self):
        """Return the ocean grid name and mesh path."""

        ocn_grid_mode = cvars["OCN_GRID_MODE"].value

        match ocn_grid_mode:
            case "Standard":
                ocn_grid = cvars["CUSTOM_OCN_GRID"].value
                ocn_mesh_path = self.cime.get_mesh_path("ocnice", ocn_grid)
            case "Create New":
                ocn_grid = cvars["CUSTOM_OCN_GRID_NAME"].value
                ocn_mesh_path = MOM6BathyLauncher.esmf_mesh_file_path()
            case _:
                assert False, f"Unsupported OCN_GRID_MODE: {ocn_grid_mode}"

        return ocn_grid, ocn_mesh_path

    def on_btn_generate_new_clicked(self, b):
        """Handler for the 'Generate New Map' button click event.
        Sets the ROF_OCN_MAPPING_STATUS variable to indicate that
        a new mapping will be generated.
        """

        cvars["ROF_OCN_MAPPING_STATUS"].value = None
        self._out.clear_output()
        self._generate_new_dialog.layout.display = ""

        rmax = cvars["ROF_OCN_MAPPING_RMAX"].value
        fold = cvars["ROF_OCN_MAPPING_FOLD"].value

        # Suggest default values for RMAX and FOLD if not set
        if rmax is None and fold is None:
            _, ocn_mesh_path = self.get_ocn_grid_and_mesh()
            suggested_rmax, suggested_fold = mapping.get_suggested_smoothing_params(ocn_mesh_path)

            cvars["ROF_OCN_MAPPING_RMAX"].value = suggested_rmax
            cvars["ROF_OCN_MAPPING_FOLD"].value = suggested_fold


    @owh.out.capture()
    def on_btn_run_generate_clicked(self, b):
        """Handler for the 'Run mapping generator' button click event.
        Runs the mapping generator with the specified parameters.
        """

        cvars["ROF_OCN_MAPPING_STATUS"].value = None
        self._out.clear_output()

        rmax = cvars["ROF_OCN_MAPPING_RMAX"].value
        if rmax is None:
            alert_warning("Please specify a valid RMAX value.")
            return

        fold = cvars["ROF_OCN_MAPPING_FOLD"].value
        if fold is None:
            alert_warning("Please specify a valid FOLD value.")
            return

        rof_grid, rof_mesh_path = self.get_rof_grid_and_mesh()
        ocn_grid, ocn_mesh_path = self.get_ocn_grid_and_mesh()

        try:
            # disable the widget ahead of running the mapping generator
            self.disabled = True

            mapping_file_prefix = f"{rof_grid}_to_{ocn_grid}_map"
            output_dir = RunoffMappingGenerator.mapping_dir()

            # Run the mapping generator
            with self._out:
                mapping.gen_rof_maps(
                    rof_mesh_path=rof_mesh_path,
                    ocn_mesh_path=ocn_mesh_path,
                    output_dir=output_dir,
                    mapping_file_prefix=mapping_file_prefix,
                    rmax=rmax,
                    fold=fold
                )
            
            nn_map_filepath = mapping.get_nn_map_filepath(
                mapping_file_prefix=mapping_file_prefix,
                output_dir=output_dir,
            )

            nnsm_map_filepath = mapping.get_smoothed_map_filepath(
                mapping_file_prefix=mapping_file_prefix,
                output_dir=output_dir,
                rmax=rmax,
                fold=fold
            )

            # Set the mapping status to CUSTOM after successful generation
            cvars["ROF_OCN_MAPPING_STATUS"].value = f"CUSTOM:{nn_map_filepath},{nnsm_map_filepath}"

        except Exception as e:
            alert_warning(
                f"An error occurred while generating the mapping: {e}"
            )
            self.disabled = False


    @staticmethod
    def mapping_dir():
        custom_grid_path = cvars["CUSTOM_GRID_PATH"].value
        mapping_dir = Path(custom_grid_path) / "mapping"
        os.makedirs(mapping_dir, exist_ok=True)
        return mapping_dir