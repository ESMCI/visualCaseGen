from ipywidgets import Widget
from ProConPy.config_var import ConfigVar

def frontend_change(cvar, new_val):
    """This method simulates a frontend value change for a widget. It is useful for testing purposes."""

    assert isinstance(cvar, ConfigVar), "cvar must be an instance of ConfigVar"
    widget = cvar._widget
    assert isinstance(widget, Widget), "widget must be an instance of ipywidgets.Widget"

    widget.value = new_val

    # acquire and release the lock to simulate a frontend change
    widget._property_lock = {"value": widget.value}
    widget._property_lock = {}