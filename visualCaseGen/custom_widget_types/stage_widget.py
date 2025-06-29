import logging
from ipywidgets import VBox, HBox, Tab, HTML, Button
import itertools

from ProConPy.out_handler import handler as owh
from ProConPy.dialog import alert_warning, alert_info
from ProConPy.stage_stat import StageStat

bg_color_light = "#9DB3CC70"
bg_color_dark = "#9DB3CC"
font_color_dark = "#00174B"
active_left_border_color = "#A8C700"

logger = logging.getLogger("\t" + __name__.split(".")[-1])


class StageWidget(VBox):
    """A specialized VBox widget for a stage in the case configurator."""

    def __init__(self, main_body_type=VBox, supplementary_widgets=[], add_ok_button=False, title="", layout={}, **kwargs):
        """Initialize the StageWidget.

        Parameters
        ----------
        main_body_type : VBox, HBox, or Tab
            The type of the main body of the StageWidget.
        supplementary_widgets : list
            A list of supplementary widgets to be added to the StageWidget.
        add_ok_button : bool
            Whether to add an OK button to the StageWidget. Defaults to False.
        title : str
            The title of the StageWidget.
        layout : dict
            The layout of the StageWidget.
        **kwargs
            Additional keyword arguments.

        Raises
        ------
        AssertionError
            If main_body_type is not VBox, HBox, or Tab.
        """
        assert main_body_type in [
            VBox,
            HBox,
            Tab,
        ], "StageWidget main_body_type must be VBox, HBox, or Tab"
        assert isinstance(
            supplementary_widgets, (list, tuple)
        ), "StageWidget supplementary_widgets must be a list"
        self._main_body_type = main_body_type
        self._title = title
        self._main_body = self._main_body_type()
        self._supplementary_widgets = supplementary_widgets
        self._top_bar = HBox([])
        self._stage = None  # Reference to the stage object that this widget represents. To be set by the stage object.
        super().__init__(
            layout={
                "border": "1px solid lightgray",
                "margin": "12px 8px 12px 12px",
                "padding": "0px",
            },
            **kwargs,
        )
        self.children = (
            self._top_bar,
            self._main_body,
        )

        self._ok_button = None  # OK button, if added
        if add_ok_button:
            self._ok_button = Button(
                description="OK",
                icon="check",
                tooltip="Confirm the selections in this stage.",
                layout={"width": "100px", "align_self": "center"},
                style={"button_color": bg_color_dark, "text_color": font_color_dark},
            )
            self._ok_button.on_click(self.attempt_to_proceed)

    def _update_top_bar_title(
        self, title_prefix="", font_color="gray", background_color=bg_color_light
    ):
        """Update the title of the top bar."""
        self._top_bar_title.value = """
        <i style="background-color: {}; color: white; display: block; width: 100%; height: 100%;"><b><font color='{}'>&nbsp&nbsp{} {}</b></i>
        """.format(
            background_color, font_color, title_prefix, self._title
        )

    def _gen_top_bar_title(self, font_color="dimgrey"):
        """Generate the title of the top bar."""
        self._top_bar_title = HTML(
            value="",
            layout={
                "display": "flex",
                "justify_content": "center",
                "width": "100%",
            },
        )
        self._update_top_bar_title(font_color)

    def _gen_top_bar(self):
        """Generate the top bar of the StageWidget."""
        self._gen_top_bar_title()
        button_width = "190px"

        # A temporary list to hold the buttons of the top bar
        top_bar_buttons = []

        # Info button, always visible
        self._btn_info = Button(
            description="Info",
            icon="info",
            tooltip="Show a brief information about this stage.",
            layout={"display": "none", "width": button_width},
            style={"button_color": bg_color_dark, "text_color": font_color_dark},
        )

        @owh.out.capture()
        def _on_btn_info_click(b):
            alert_info(self._stage.description)

        self._btn_info.on_click(_on_btn_info_click)
        top_bar_buttons.append(self._btn_info)

        # Defaults button, visible only if defaults specified
        self._btn_defaults = None
        btn_defaults_needed = self._stage._auto_set_default_value is False and all(
            [var.default_value is not None for var in self._stage._varlist]
        )
        if btn_defaults_needed:
            self._btn_defaults = Button(
                description="Defaults",
                tooltip="Set all (remaining) options to their default values.",
                icon="gear",
                layout={"display": "none", "width": button_width},
                style={"button_color": bg_color_dark, "text_color": font_color_dark},
            )
            self._btn_defaults.on_click(self._stage.set_vars_to_defaults)
            top_bar_buttons.append(self._btn_defaults)

        # Reset button, visible only if stage is PARTIAL
        self._btn_reset = Button(
            description="Reset",
            icon="rotate-right",
            tooltip="Reset all selections in this stage.",
            layout={"display": "none", "width": button_width},
            style={"button_color": bg_color_dark, "text_color": font_color_dark},
        )
        self._btn_reset.on_click(self._stage.reset)
        top_bar_buttons.append(self._btn_reset)

        # Revert button, visible only if stage is not first
        self._btn_revert = None
        if not self._stage.is_first():
            self._btn_revert = Button(
                description="Revert",
                icon="arrow-up",
                tooltip="Reset this stage and go back to the previous stage.",
                layout={"display": "none", "width": button_width},
                style={"button_color": bg_color_dark, "text_color": font_color_dark},
            )
            self._btn_revert.on_click(self._stage.revert)
            top_bar_buttons.append(self._btn_revert)

        # Proceed button, always visible
        self._btn_proceed = Button(
            description="Proceed",
            icon="arrow-down",
            tooltip="Move to the next stage if all the variables in this stage are set.",
            layout={"display": "none", "width": button_width},
            style={"button_color": bg_color_dark, "text_color": font_color_dark},
        )
        self._btn_proceed.on_click(self.attempt_to_proceed)
        top_bar_buttons.append(self._btn_proceed)

        self._top_bar.children = [self._top_bar_title] + top_bar_buttons

    def _set_main_body_children(self, first_child=None):
        """Set the children of the main body of the StageWidget. If a first_child is provided,
        it will be added to the main body, followed by all its siblings to the right."""

        main_body_children = [var.widget for var in self._stage._varlist]
        if self._supplementary_widgets:
            main_body_children.extend(self._supplementary_widgets)
        if self._ok_button:
            main_body_children.append(self._ok_button)
        if first_child:
            main_body_children.append(first_child._widget)
            main_body_children.extend(stage._widget for stage in first_child.siblings_to_right())
        self._main_body.children = tuple(main_body_children)

    def _refresh_main_body(self):
        """Generate the main body of the StageWidget. This method is called whenever the children attribute is set.
        """

        old_display = ""
        if self._main_body:
            old_display = self._main_body.layout.display

        self._set_main_body_children()

        self._main_body.layout = {
            "display": old_display,
            "margin": "0px",
        }

    def add_child_stages(self, first_child):
        """Append a child stage and all its siblings to the main body, which, by default,
        has the widgets of the varlist only, but may be extended to include the StageWidget
        instances of child stages.

        Parameters
        ----------
        first_child : Stage
            The first child stage to append.
        """
        self._set_main_body_children(first_child)
    
    def remove_child_stages(self):
        """Remove all child stages from the main body, leaving only the widgets of the varlist and supplementary widgets."""
        self._set_main_body_children()

    @property
    def stage(self):
        return self._stage

    @stage.setter
    def stage(self, value):
        assert self._stage is None, "StageWidget can only be assigned to one stage."
        self._stage = value
        self._title = value._title
        self._gen_top_bar()
        # Set the children attribute. This will actually set the children of the StageWidget
        # to the top bar and the main body, and the main body's children to the widgets of the
        # variables in the stage.
        self._refresh_main_body()
        # Observe StageStat
        self._stage.observe(self._on_stage_status_change, names="status", type="change")
        self._on_stage_status_change(
            {"old": StageStat.INACTIVE, "new": self._stage.status}
        )

    def _on_stage_status_change(self, change):
        """Handle the change of the stage status."""

        old_state = change["old"]
        new_state = change["new"]

        if new_state == StageStat.INACTIVE or new_state == StageStat.SEALED:
            if old_state != StageStat.SEALED:
                self._disable()
        else:
            if old_state == StageStat.INACTIVE or old_state == StageStat.SEALED:
                self._enable()
            self._update_btn_reset(old_state, new_state)


    def _disable(self):
        """Disable the entire stage widget."""
        logger.debug("Disabling stage widget %s...", self._title)

        self.layout.border_left = "4px solid lightgray"

        # Disable top bar
        self._update_top_bar_title(font_color="gray", background_color=bg_color_light)
        self._btn_info.layout.display = "none"
        if self._btn_defaults:
            self._btn_defaults.layout.display = "none"
        self._btn_reset.layout.display = "none"
        if self._btn_revert:
            self._btn_revert.layout.display = "none"
        self._btn_proceed.layout.display = "none"

        # Disable main body and all its children
        if self._main_body:
            if any([var.value is None for var in self._stage._varlist]):
                # this is an incomplete stage to be completed in the future, so make it invisible now
                self._main_body.layout.display = "none"

            for child in self._main_body.children:
                child.disabled = True

    def _enable(self):
        """Enable the entire stage widget, excet for the reset button, which is enabled
        by the _update_btn_reset method if necessary."""
        logger.debug("Enabling stage widget %s...", self._title)
        self.layout.border_left = "5px solid " + active_left_border_color

        # Enable top bar
        self._update_top_bar_title(
            title_prefix="&#9658",
            font_color=font_color_dark,
            background_color=bg_color_dark,
        )
        self._btn_info.layout.display = ""
        if self._btn_defaults:
            self._btn_defaults.layout.display = ""
        if self._btn_revert:
            self._btn_revert.layout.display = ""
        self._btn_proceed.layout.display = ""

        # Enable main body and all its children
        if self._main_body:
            self._main_body.layout.display = "flex"
            for child in self._main_body.children:
                child.disabled = False

    def _update_btn_reset(self, old_state, new_state):
        """Update the reset button based on the old and new stage status."""
        if new_state == StageStat.PARTIAL:
            if self._btn_reset.layout.display == "none":
                self._btn_reset.layout.display = ""
        elif old_state == StageStat.SEALED and new_state == StageStat.COMPLETE:
            self._btn_reset.layout.display = ""
        else:
            self._btn_reset.layout.display = "none"

    @owh.out.capture()
    def attempt_to_proceed(self, b):
        """Attempt to proceed to the next stage. If the stage is complete, the next stage is
        enabled; otherwise, the user is informed about the variables that are not set yet.

        Parameters
        ----------
        b : Button
            The button that triggers this method.
        """
        if self._stage.status == StageStat.COMPLETE:
            self._stage._proceed()
        else:
            alert_warning(
                "Please complete all of the variables in this stage first. Remaining variable(s): "
                + ", ".join(
                    [var.name for var in self._stage._varlist if var.value is None]
                )
            )

    @owh.out.capture()
    def reset(self):
        """Reset the stage."""
        logger.debug(f"Resetting stage {self._title}...")
        self._stage.reset()
        self._stage._refresh_main_body()
