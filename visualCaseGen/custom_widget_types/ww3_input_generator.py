import logging
from ipywidgets import HBox, VBox, Button, Output

from ProConPy.out_handler import handler as owh
from ProConPy.config_var import cvars
from ProConPy.dialog import alert_warning
from visualCaseGen.custom_widget_types.mom6_forge_launcher import MOM6ForgeLauncher

logger = logging.getLogger("\t" + __name__.split(".")[-1])


class WW3InputGenerator(VBox):
    """Widget to generate the WW3 grid-preprocessor input files from a custom ocean grid.

    When the user opts to use the newly created custom ocean grid as the wave grid (WW3), this
    widget reconstructs the mom6_forge Grid/Topo from the already-saved ocean grid files and
    writes the WW3 ``*.inp`` files into the custom grid's ``ocnice`` directory. Those files are
    later copied into the case RUNDIR by the case creator."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._btn_generate = Button(
            description="Generate WW3 input files",
            button_style="success",
            tooltip="Reconstruct the custom ocean grid and write the WW3 grid-preprocessor input files.",
            layout={"width": "260px", "align_self": "center", "margin": "10px"},
        )
        self._btn_generate.on_click(self.on_btn_generate_clicked)

        self._out = Output()

        self.children = [
            HBox([self._btn_generate], layout={"justify_content": "center"}),
            self._out,
        ]

        # Reset the status when the wave grid mode changes.
        cvars["WAV_GRID_MODE"].observe(self.reset, names="value", type="change")

    @property
    def disabled(self):
        return super().disabled

    @disabled.setter
    def disabled(self, value):
        self._btn_generate.disabled = value

    def reset(self, change=None):
        """Reset the widget output and the WW3_INPUT_STATUS variable."""
        self._out.clear_output()
        cvars["WW3_INPUT_STATUS"].value = None

    @owh.out.capture()
    def on_btn_generate_clicked(self, b):
        """Reconstruct the custom ocean grid/topography and write the WW3 input files."""
        import xarray as xr
        from mom6_forge.grid import Grid
        from mom6_forge.topo import Topo

        cvars["WW3_INPUT_STATUS"].value = None
        self._out.clear_output()

        grid_alias = cvars["CUSTOM_OCN_GRID_NAME"].value
        supergrid_file = MOM6ForgeLauncher.supergrid_file_path()
        topo_file = MOM6ForgeLauncher.topo_file_path()
        ocnice_dir = MOM6ForgeLauncher.get_custom_ocn_grid_path()

        # The custom ocean grid files must already exist (created via the mom6_forge notebook).
        for f in (supergrid_file, topo_file):
            if not f.exists():
                alert_warning(
                    "The custom ocean grid files were not found. Please complete the custom "
                    f"ocean grid stage first. Missing file: {f}"
                )
                return

        try:
            # Disable the widget while the generator runs.
            self.disabled = True
            with self._out:
                # Use the same min_depth the ocean grid was built with so the WW3 land/sea mask
                # matches the ocean mask. mom6_forge persists it as an attribute of the topog
                # file -- the same source the case creator uses for MOM6's MINIMUM_DEPTH -- so
                # this stays correct even if the user edited min_depth in the mom6_forge notebook.
                with xr.open_dataset(topo_file) as ds_topo:
                    if "min_depth" not in ds_topo.attrs:
                        alert_warning(
                            f"The topography file {topo_file} does not record a 'min_depth' "
                            "attribute. Please regenerate the custom ocean grid with mom6_forge."
                        )
                        self.disabled = False
                        return
                    min_depth = float(ds_topo.attrs["min_depth"])
                grid = Grid.from_supergrid(supergrid_file.as_posix())
                topo = Topo.from_topo_file(grid, topo_file.as_posix(), min_depth=min_depth)
                topo.write_ww3_input(ocnice_dir.as_posix(), grid_alias=grid_alias)
                print(f"WW3 input files written to {ocnice_dir} (min_depth={min_depth}).")
            cvars["WW3_INPUT_STATUS"].value = "Complete"
        except Exception as e:
            alert_warning(f"An error occurred while generating the WW3 input files: {e}")
            self.disabled = False
