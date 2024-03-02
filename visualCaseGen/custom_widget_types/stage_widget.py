import logging
from ipywidgets import VBox, HBox, Tab, HTML, Button
import itertools

from ProConPy.out_handler import handler as owh
from ProConPy.dialog import alert_warning

bg_color_light = "#9DB3CC70"
bg_color_dark = "#9DB3CC"
font_color_dark = "#00174B"
active_left_border_color = "#A8C700"

logger = logging.getLogger("\t" + __name__.split(".")[-1])


class StageWidget(VBox):
    """A specialized VBox widget for a stage in the case configurator."""

    def __init__(self, main_body_type=VBox, title="", layout={}, **kwargs):
        """Initialize the StageWidget.

        Parameters
        ----------
        main_body_type : VBox, HBox, or Tab
            The type of the main body of the StageWidget.
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
        self._main_body_type = main_body_type
        self._title = title
        self._disabled = False
        self._main_body = self._gen_main_body(children=())
        self._top_bar = HBox([])
        self._stage = None  # Reference to the stage object that this widget represents. To be set by the stage object.
        super().__init__(
            layout={
                "border": "1px solid lightgray",
                "margin": "12px 8px 12px 16px",
                "padding": "0px",
            },
            **kwargs,
        )

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
        self._btn_info = Button(
            description="Info",
            icon="info",
            tooltip="Show a brief information about this stage.",
            layout={"display": "none", "width": button_width},
            style={"button_color": bg_color_dark, "text_color": font_color_dark},
        )
        self._btn_defaults = Button(
            description="Defaults",
            tooltip="Set all (remaining) options to their default values.",
            icon="gear",
            layout={"display": "none", "width": button_width},
            style={"button_color": bg_color_dark, "text_color": font_color_dark},
        )
        self._btn_reset = Button(
            description="Reset",
            icon="rotate-right",
            tooltip="Reset all selections in this stage.",
            layout={"display": "none", "width": button_width},
            style={"button_color": bg_color_dark, "text_color": font_color_dark},
        )
        self._btn_reset.on_click(self._stage.reset)

        self._btn_revert = Button(
            description="Revert",
            icon="arrow-up",
            tooltip="Reset this stage and go back to the previous stage.",
            layout={"display": "none", "width": button_width},
            style={"button_color": bg_color_dark, "text_color": font_color_dark},
        )
        self._btn_revert.on_click(self._stage.revert)

        self._btn_proceed = Button(
            description="Proceed",
            icon="arrow-down",
            tooltip="Move to the next stage if all the variables in this stage are set.",
            layout={"display": "none", "width": button_width},
            style={"button_color": bg_color_dark, "text_color": font_color_dark},
        )
        self._btn_proceed.on_click(self.attempt_to_proceed)

        self._top_bar = HBox(
            [
                self._top_bar_title,
                self._btn_info,
                self._btn_defaults,
                self._btn_reset,
                self._btn_revert,
                self._btn_proceed,
            ]
        )

    def _gen_main_body(self, children):
        """Generate the main body of the StageWidget. This method is called whenever the children attribute is set.

        Parameters
        ----------
        children : list
            The new list of children of the main body.
        """

        return self._main_body_type(
            children=children,
            layout={
                "margin": "0px",
            },
        )

    def __setattr__(self, name, value):
        """Override the __setattr__ method to handle the children attribute so that the widget
        always has two children: the top bar and the main body. Any new children, unless they
        are the top bar or the main body, are added to the main body. If the children attribute
        is set, the top bar and the main body are updated accordingly.

        Parameters
        ----------
        name : str
            The name of the attribute to set.
        value : any
            The value to set the attribute to.
        """

        if name == "children":
            if len(value) > 0 and value[0] is self._top_bar:
                value = value[1:]
            if len(value) > 0 and value[0] is self._main_body:
                value = value[0].children + value[1:]
            self._main_body = self._gen_main_body(children=value)
            super().__setattr__(
                name,
                (
                    self._top_bar,
                    self._main_body,
                ),
            )
        else:
            # For all other attributes, use the default behavior
            super().__setattr__(name, value)

    @property
    def stage(self):
        return self._stage

    @stage.setter
    def stage(self, value):
        self._stage = value
        self._title = value._title
        self._gen_top_bar()
        # Set the children attribute. This will actually set the children of the StageWidget
        # to the top bar and the main body, and the main body's children to the widgets of the
        # variables in the stage.
        self.children = [var.widget for var in self._stage._varlist]

    def append_child_stages(self, first_child):
        """Append a child stage and all its siblings to the main body, which, by default,
        has the widgets of the varlist only, but may be extended to include the StageWidget
        instances of child stages.

        Parameters
        ----------
        first_child : Stage
            The first child stage to append.
        """

        self._main_body.children = tuple(
            itertools.chain(
                [var.widget for var in self._stage._varlist],
                [first_child._widget],
                [stage._widget for stage in first_child.subsequent_siblings()],
            )
        )

    @property
    def disabled(self):
        return self._disabled

    @disabled.setter
    def disabled(self, value):
        """Set the disabled state of the stage widget. if value is True, the stage is disabled;
        otherwise, it is enabled. When the stage gets disabled, the main body is hidden and the
        top bar is updated to reflect the disabled state. When the stage gets enabled, the main
        body is shown and the top bar is updated to reflect the enabled state. When this widget
        is disabled, all of the main body's children are hidden and disabled as well.

        Parameters
        ----------
        value : bool
            The disabled state of the stage widget.
        """

        if value is True:
            # Disable the stage
            logger.debug("Disabling stage widget %s...", self._title)
            self.layout.border_left = "5px solid lightgray"
            self._update_top_bar_title(
                font_color="gray", background_color=bg_color_light
            )
            self._btn_info.layout.display = "none"
            self._btn_defaults.layout.display = "none"
            self._btn_reset.layout.display = "none"
            self._btn_revert.layout.display = "none"
            self._btn_proceed.layout.display = "none"
            if self._main_body:
                if any([var.value is None for var in self._stage._varlist]):
                    # this is an incomplete stage to be completed in the future, so make it invisible now
                    self._main_body.layout.display = "none"
        else:
            # Enable the stage
            logger.debug("Enabling stage widget %s...", self._title)
            self.layout.border_left = "5px solid " + active_left_border_color
            self._update_top_bar_title(
                title_prefix="&#9658",
                font_color=font_color_dark,
                background_color=bg_color_dark,
            )
            if self._main_body:
                self._btn_info.layout.display = ""
                self._btn_defaults.layout.display = ""
                self._btn_reset.layout.display = ""
                self._btn_revert.layout.display = (
                    "" if not self._stage.is_first() else "none"
                )
                self._btn_proceed.layout.display = ""
                self._main_body.layout.display = "flex"

        # Set the disabled state of the stage widget
        self._disabled = value

        # Disable/Enable all variables in the stage
        for var in self._stage._varlist:
            var.widget.disabled = value

    @owh.out.capture()
    def attempt_to_proceed(self, b):
        """Attempt to proceed to the next stage. If the stage is complete, the next stage is
        enabled; otherwise, the user is informed about the variables that are not set yet.

        Parameters
        ----------
        b : Button
            The button that triggers this method.
        """
        if self._stage.completed:
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
        self._main_body.children = self._stage._gen_main_body(children=())
        self.disabled = False
