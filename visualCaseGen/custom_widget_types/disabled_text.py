from ipywidgets import Text


class DisabledText(Text):
    """A Text widget that is always disabled and might never be displayed. This is useful for
    preventing a stage from proceeding by solely relying on the user's input in other
    stage variables. For example, the MOM6_BATHY_STATUS variable is set to '' to prevent
    the completion of the stage until the user runs the MOM6 bathymetry generation tool.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.disabled = True
        self.layout = {"display": "none"}

    def __setattr__(self, name, value):
        if name == "disabled":
            self.layout = {"display": "none"}
            value = True
        elif name == "layout":
            value["display"] = "none"
        super().__setattr__(name, value)

    def force_display(self):
        super().__setattr__("layout", {"display": "", "align_self": "flex-end"})
