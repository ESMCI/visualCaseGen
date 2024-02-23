import logging
from ipywidgets import VBox, HBox, Tab, HTML, Button

from ProConPy.out_handler import handler as owh

bg_color_light =  '#afc7e360'
bg_color_dark =  '#afc7e3'
font_color_dark = '#012169'

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
        self._stage = None # Reference to the stage object that this widget represents. To be set by the stage object.
        super().__init__(
            layout={
                "border": "1px solid lightgray",
                "margin": "12px",
                "padding": "0px",
            },
            **kwargs,
        )

    def _update_top_bar_title(self, title_prefix='', font_color='gray', background_color=bg_color_light):
        """Update the title of the top bar."""
        self._top_bar_title.value = """
        <i style="background-color: {}; color: white; display: block; width: 100%; height: 100%;"><b><font color='{}'>&nbsp&nbsp{} {}</b></i>
        """.format(
            background_color,
            font_color,
            title_prefix,
            self._title
        )

    def _gen_top_bar_title(self, font_color='dimgrey'):
        """Generate the title of the top bar."""
        self._top_bar_title = HTML(
            value = '',
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
        button_width = "160px"
        self._btn_info = Button(
            description="Info",
            icon="info",
            tooltip="Show a brief information about this stage.",
            layout={'display':'none', 'width': button_width},
            style={'button_color':bg_color_dark, 'text_color':font_color_dark,}# 'font_weight':'bold'},
        )
        self._btn_defaults = Button(
            description="Defaults",
            tooltip="Set all (remaining) options to their default values.",
            icon="gear",
            layout={'display':'none', 'width': button_width},
            style={'button_color':bg_color_dark, 'text_color':font_color_dark,}# 'font_weight':'bold'},
        )
        self._btn_reset = Button(
            description="Reset",
            icon="rotate-right",
            tooltip="Reset all selections in this stage.",
            layout={'display':'none', 'width': button_width},
            style={'button_color':bg_color_dark, 'text_color':font_color_dark,}# 'font_weight':'bold'},
        )
        self._btn_reset.on_click(self.stage.reset)

        self._btn_revert = Button(
            description="Revert",
            icon="arrow-up",
            tooltip="Reset this stage and go back to the previous stage.",
            layout={'display':'none', 'width': button_width},
            style={'button_color':bg_color_dark, 'text_color':font_color_dark,}# 'font_weight':'bold'},
        )
        ###todo self._btn_revert.on_click(self.stage.revert)

        self._top_bar = HBox([
            self._top_bar_title,
            self._btn_info,
            self._btn_defaults,
            self._btn_reset,
            self._btn_revert,
            ])

    def _gen_main_body(self, children):
        """Generate the main body of the StageWidget. This method is called whenever the children attribute is set."""
        return self._main_body_type(
            children=children,
            layout={
                "margin": "6px 0px 6px 0px",
            },)

    def __setattr__(self, name, value):
        """Override the __setattr__ method to handle the children attribute."""
        if name == "children":
            if len(value) > 0 and value[0] is self._top_bar:
                value = value[1:]
            self._main_body = self._gen_main_body(children=value)
            super().__setattr__(
                name,
                (
                    self._top_bar,
                    self._main_body,
                ),
            )
        else:
            super().__setattr__(name, value)
    


    @property
    def stage(self):
        return self._stage
    
    @stage.setter
    def stage(self, value):
        self._stage = value
        self._title = value._title
        self._gen_top_bar()

    @property
    def disabled(self):
        return self._disabled

    @disabled.setter
    def disabled(self, value):
        if value is True:
            # Disable the stage
            logger.debug("Disabling stage widget %s...", self._title)
            self.layout.border_left = "4px solid lightgray"
            self._update_top_bar_title(font_color = 'gray', background_color = bg_color_light)
            self._btn_info.layout.display = 'none'
            self._btn_defaults.layout.display = 'none'
            self._btn_reset.layout.display = 'none'
            self._btn_revert.layout.display = 'none'
            if self._main_body:
                if len(self._main_body.children)>0 and any([child.value in [None,()] for child in self._main_body.children]):
                    self._main_body.layout.display = 'none'
        else:
            # Enable the stage
            logger.debug("Enabling stage widget %s...", self._title)
            self.layout.border_left = "4px solid #A8C700"
            self._update_top_bar_title(title_prefix='&#9658', font_color=font_color_dark, background_color=bg_color_dark)
            if self._main_body:
                self._btn_info.layout.display = ''
                self._btn_defaults.layout.display = ''
                self._btn_reset.layout.display = ''
                self._btn_revert.layout.display = ''
                self._main_body.layout.display = 'flex'
        self._disabled = value
        for child in self._main_body.children:
            child.disabled = value
    

    @owh.out.capture()
    def reset(self):
        """Reset the stage."""
        logger.debug(f"Resetting stage {self._title}...")
        self._stage.reset()
        self._main_body.children = self._stage._gen_main_body(children=())
        self.disabled = False