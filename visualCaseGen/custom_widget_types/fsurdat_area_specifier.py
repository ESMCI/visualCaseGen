from ipywidgets import VBox, ValueWidget, ToggleButtons, BoundedFloatText
from traitlets import Unicode, validate, observe
from pathlib import Path

from ipyfilechooser import FileChooser

class FsurdatAreaSpecifier(VBox, ValueWidget):
    """A widget to specify the area of customization for the fsurdat file. The area can be specified
    either via corner coordinates or via a land mask file."""

    value = Unicode(help="String value", allow_none=True).tag(sync=True)

    def __init__(self, value=None, disabled=False, **kwargs):
        """Create a new FsurdatAreaSpecifier widget.
        
        Parameters
        ----------
        value : str, optional
            The initial value of the widget. If None, the widget will be initialized with no value.
        disabled : bool, optional
            Whether the widget is disabled.
        **kwargs
            Additional keyword arguments to be passed to the parent class (VBox).
        """

        super().__init__(**kwargs)

        self._disabled = disabled

        self._south = BoundedFloatText(
            value=-90.0, min=-90.0, max=90.0,
            description="Southernmost latitude for rectangle:",
            layout={"display": "none", "width": "350px", "margin": "5px"},
            style={"description_width": "260px"},
        )
        self._north = BoundedFloatText(
            value=90.0, min=-90.0, max=90.0,
            description="Northernmost latitude for rectangle:",
            layout={"display": "none", "width": "350px", "margin": "5px"},
            style={"description_width": "260px"},
        )
        self._west = BoundedFloatText(
            value=0.0, min=-360.0, max=360.0,
            description="Westernmost longitude for rectangle:",
            layout={"display": "none", "width": "350px", "margin": "5px"},
            style={"description_width": "260px"},
        )
        self._east = BoundedFloatText(
            value=360.0, min=-360.0, max=360.0,
            description="Easternmost longitude for rectangle:",
            layout={"display": "none", "width": "350px", "margin": "5px"},
            style={"description_width": "260px"},
        )

        self._land_mask_file_path = FileChooser(
            filename="",
            title="Land mask file designating the area of customization:",
            existing_only=True,
            filename_placeholder="Enter an existing land mask filename",
            filter_pattern="*.nc",
            layout={"display":"none", "width": "90%", "margin": "5px", "left": "20px"},
        )
            
        self._mode_selector = ToggleButtons(
            value=None,
            options=["Via corner coordinates", "Via mask file"],
            description_allow_html=True,
            description="&#9658; Specify area of customization:",
            layout={"display": "flex", "width": "max-content", "margin": "10px"},
            style={"button_width": "max-content", "description_width": "initial"},
        )

        self.children = [
            self._mode_selector,
            self._south,
            self._north,
            self._west,
            self._east,
            self._land_mask_file_path
        ]

        self._mode_selector_lock = False

        # observances

        for coord in [self._south, self._north, self._west, self._east]:
            coord.observe(self._on_coord_change, names="value", type="change")
        
        self._land_mask_file_path.observe(self._on_mask_file_change, names="_property_lock", type="change")

        self._mode_selector.observe(self._on_mode_change, names="_property_lock", type="change")

        self._propagate_disabled_flag(self._disabled)

        self.set_trait("value", None)

    def _on_mode_change(self, change):
        """Handle a change of the mode selector value via the frontend."""

        if change["old"] == {}:
            return  # frontend-triggered change not finalized yet

        new_mode = self._mode_selector.value
        self._change_mode(new_mode)
        self.update_value(new_mode)

    def _change_mode(self, new_mode):
        """Change the mode of the widget to the specified mode."""

        if new_mode == "Via corner coordinates":
            self._south.layout.display = ""
            self._north.layout.display = ""
            self._west.layout.display = ""
            self._east.layout.display = ""
            self._land_mask_file_path.layout.display = "none"
        else:
            if new_mode == "Via mask file":
                self._land_mask_file_path.layout.display = ""
            elif new_mode is None:
                self._land_mask_file_path.layout.display = "none"
            else:
                raise ValueError(f"Unknown mode: {new_mode}")
            self._south.layout.display = "none"
            self._north.layout.display = "none"
            self._west.layout.display = "none"
            self._east.layout.display = "none"
    
    def update_value(self, new_mode):
        """Update the value of the widget based on the specified mode."""
        if new_mode == "Via corner coordinates":
            self.value = f"coords:{self._south.value},{self._north.value},{self._west.value},{self._east.value}"
        else:
            self._mode_selector_lock=True
            self.value = None
            self._mode_selector_lock=False
    
    def _on_coord_change(self, change):
        """Update the value of the widget based on the change of a corner coordinate."""
        self.value = f"coords:{self._south.value},{self._north.value},{self._west.value},{self._east.value}"

    def _on_mask_file_change(self, change):
        """Update the value of the widget based on the change of the land mask file."""
        if change["old"] == {}:
            return  # frontend-triggered change not finalized yet

        new_path = self._land_mask_file_path.value
        if new_path is None:
            self.value = None
        else:
            new_val = f"mask_file:{new_path}"
            self.value = new_val
    
    @validate("value")
    def _validate_value(self, proposal):
        new_val = proposal["value"]
        if new_val is None:
            pass #todo
        elif new_val.startswith("mask_file:"):
            # check if the file exists:
            if not Path(new_val[len("mask_file:"):]).exists():
                raise ValueError(f"File does not exist: {new_val[len('mask_file:'):]}")
        elif new_val.startswith("coords:"):
            coords = new_val[len("coords:"):]
            try:
                south, north, west, east = map(float, coords.split(","))
                if not -90 <= south <= 90:
                    raise ValueError(f"Invalid southernmost latitude: {south}")
                if not -90 <= north <= 90:
                    raise ValueError(f"Invalid northernmost latitude: {north}")
                if not -360 <= west <= 360:
                    raise ValueError(f"Invalid westernmost longitude: {west}")
                if not -360 <= east <= 360:
                    raise ValueError(f"Invalid easternmost longitude: {east}")
            except ValueError as e:
                raise ValueError(f"Invalid coordinates: {coords}") from e
        else:
            raise ValueError(f"Unknown value: {new_val}")
        
        return proposal["value"]

    @observe("value")
    def _on_backend_value_change(self, change):
        new_val = change["new"]
        if new_val is None:
            self._land_mask_file_path.value = None
            if self._mode_selector_lock is False:
                self._mode_selector.value = None
                self._change_mode(None)
        elif new_val.startswith("mask_file:"):
            self._mode_selector.value = "Via mask file"
            self._land_mask_file_path.value = new_val[len("mask_file:"):]
            self._change_mode("Via mask file")
        elif new_val.startswith("coords:"):
            self._mode_selector.value = "Via corner coordinates"
            coords = new_val[len("coords:"):]
            assert coords.count(",") == 3
            self._south.value, self._north.value, self._west.value, self._east.value = map(float, coords.split(","))
            self._change_mode("Via corner coordinates")
        else:
            raise ValueError(f"Unknown value: {new_val}")

        self._signal_value_to_backend()


    def _signal_value_to_backend(self):
        """Signal the value to the backend by acquiring and releasing the property lock.
        This method should be called whenever a value change is ready to be sent to the backend.
        """
        # acquire lock
        self._property_lock = {"value": self.value}
        # release lock
        self._property_lock = {}
        

    @property
    def disabled(self):
        return self._disabled

    @disabled.setter
    def disabled(self, value):
        self._propagate_disabled_flag(value)
    
    def _propagate_disabled_flag(self, value):
        self._mode_selector.disabled = value
        self._south.disabled = value
        self._north.disabled = value
        self._west.disabled = value
        self._east.disabled = value
        self._land_mask_file_path.disabled = value
        self._disabled = value