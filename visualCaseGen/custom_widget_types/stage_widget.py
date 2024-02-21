from ipywidgets import VBox, HBox, Tab, HTML


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
        self._gen_top_bar_title()
        self._gen_top_bar()
        self._main_body = self._gen_main_body(children=())
        super().__init__(
            layout={
                "border": "1px solid lightgray",
                "margin": "12px",
                "padding": "0px",
            },
            **kwargs,
        )

    def _gen_top_bar(self):
        """Generate the top bar of the StageWidget."""
        self._top_bar = HBox([self._top_bar_title])

    def _gen_main_body(self, children):
        """Generate the main body of the StageWidget. This method is called whenever the children attribute is set."""
        return self._main_body_type(children=children)

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
    
    def _update_top_bar_title(self, font_color='gray', background_color='#C0C0C060'):
        self._top_bar_title.value = """
        <i style="background-color: {}; color: white; display: block; width: 100%; height: 100%;"><b><font color='{}'>&nbsp&nbsp{}</b></i>
        """.format(
            background_color,
            font_color,
            self._title
        )


    def _gen_top_bar_title(self, font_color='dimgrey'):
        self._top_bar_title = HTML(
            value = '',
            layout={
                "display": "flex",
                "justify_content": "center",
                "width": "100%",
            },
        )
        self._update_top_bar_title(font_color)

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        self._title = value
        self._update_top_bar_title()

    @property
    def disabled(self):
        return self._disabled

    @disabled.setter
    def disabled(self, value):
        if value is True:
            self.layout.border_left = "5px solid lightgray"
            self._update_top_bar_title(font_color = 'gray', background_color = '#C3D7EE60')
        else:
            self.layout.border_left = "5px solid #A8C700"
            self._update_top_bar_title(font_color = '#012169', background_color = '#C3D7EE')
        self._disabled = value
        for child in self._main_body.children:
            child.disabled = value