import logging
import ipywidgets as widgets
from visualCaseGen.visualCaseGen.DummyWidget import DummyWidget
from visualCaseGen.visualCaseGen.OutHandler import handler as owh

logger = logging.getLogger(__name__)

class ConfigVar():

    """
    CESM Configuration variable, e.g., COMP_OCN xml variable.
    """

    # a collective dictionary of ConfigVars
    vdict = dict()

    # to be set by CompliancesHandler constructor
    compliances = None

    def __init__(self, name):
        if name in ConfigVar.vdict:
            logger.warning("ConfigVar {} already created.".format(name))
        self.name = name
        self._has_options = False
        self._widget = DummyWidget()
        self._val_validity_obs_on = False
        ConfigVar.vdict[name] = self
        logger.debug("ConfigVar {} created.".format(self.name))

    def reset():
        logger.debug("Resetting ConfigVar vdict.")
        ConfigVar.vdict = dict()

    def exists(varname):
        """ Check if a variable is already defined."""
        return varname in ConfigVar.vdict

    @property
    def value(self):
        assert self._widget != None, "Cannot determine value for "+self.name+". Associated widget not initialized."
        return self._widget.value

    @property
    def assertions(self):
        return self.compliances.assertions(self.name)

    @value.setter
    def value(self, val):
        self._widget.value = val

    @property
    def widget(self):
        raise RuntimeError("Cannot access widget property from outside the ConfigVar class")

    @widget.setter
    def widget(self, widget):
        self._widget = widget
        self._widget.parentCV = self

    def get_widget_property(self, property_name):
        getattr(self._widget, property_name)

    def set_widget_properties(self, property_dict):
        assert isinstance(property_dict, dict)
        for key, val in property_dict.items():
            assert key != "options", "Must set widget options via .options setter"
            assert key != "value", "Must set widget value via .value setter"
            setattr(self._widget, key, val)

    @property
    def widget_style(self):
        return self._widget.style

    @widget_style.setter
    def widget_style(self, style):
        self._widget.style = style

    @property
    def widget_layout(self):
        return self._widget.layout

    @widget_layout.setter
    def widget_layout(self, layout):
        self._widget.layout = layout

    @property
    def description(self):
        return self._widget.description

    def observe(self, *args, **kwargs):
        return self._widget.observe(*args, **kwargs)

    #def display(self):
    #    try:
    #        return self._widget._ipython_display_()
    #    except AttributeError:
    #        return self._widget._repr_mimebundle_()

