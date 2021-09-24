import logging
import ipywidgets as widgets
from visualCaseGen.visualCaseGen.DummyWidget import DummyWidget
from visualCaseGen.visualCaseGen.OutHandler import handler as owh

logger = logging.getLogger(__name__)

invalid_opt_icon = chr(int("274C",base=16)) # Ballot Box with X
valid_opt_icon = chr(int("2713",base=16)) # Ballot Box with X

# it is assumed in this module that icons lenghts are one char.
assert len(invalid_opt_icon)==1 and len(valid_opt_icon)==1

def is_valid_option(val):
    if val == None:
        return True
    val_split = val.split()
    if len(val_split)>=2:
        if val_split[0] == invalid_opt_icon:
            return False
        elif val_split[0] == valid_opt_icon:
            return True
    else:
        raise RuntimeError("Corrupt value passed to is_valid_option(): {}".format(val))

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
        self.has_options = False
        self._widget = DummyWidget()
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
    def widget_description(self):
        return self._widget.description

    def observe(self, *args, **kwargs):
        return self._widget.observe(*args, **kwargs)

    def __repr__(self):
        return self._widget.__repr__()

class ConfigVarOpt(ConfigVar):

    def __init__(self, name, never_unset=False):
        super().__init__(name)
        self.has_options = True
        self.options_validity = []
        self.error_msgs = []
        self.never_unset = never_unset # once the widget value is set, don't unset it

    @property
    def value(self):
        assert self._widget != None, "Cannot determine value for "+self.name+". Associated widget not initialized."
        if self._widget.value!=None and ConfigVarOpt._opt_prefixed_with_status(self._widget.value):
            return self._widget.value[1:].strip()
        else:
            return self._widget.value

    @value.setter
    def value(self, val):
        if (val != None and val !='') and (val not in self.options):
            raise ValueError("{} is an invalid option for {}. Valid options: {}".format(val, self.name, self.options))
        self._widget.value = val

    def value_status(self):
        assert ConfigVarOpt._opt_prefixed_with_status(self._widget.value)
        return self._widget.value == None or self._widget.value[0] == valid_opt_icon

    @ConfigVar.widget.setter
    def widget(self, widget):
        orig_widget_val = widget.value
        self._widget = widget
        self._widget.options = tuple(['{} {}'.format(valid_opt_icon, opt) for opt in widget.options])
        if orig_widget_val == None:
            self._widget.value = None
        else:
            self._widget.value = '{} {}'.format(valid_opt_icon, orig_widget_val)
        self._widget.value_status = self.value_status

    @property
    def options(self):
        return self._widget.options

    @options.setter
    def options(self, opts):
        self._widget.options = opts

    @staticmethod
    def _opt_prefixed_with_status(option):
        """ Returns true if a given option str is prefixed with a status icon.

        Parameters
        ----------
        option: str
            A widget option/value.

        Returns
        -------
        True or False
        """
        return len(option)>0 and option.split()[0] in [invalid_opt_icon, valid_opt_icon]

    @owh.out.capture()
    def options_sans_validity(self):
        return [option[1:].strip() if option.split()[0] in [invalid_opt_icon, valid_opt_icon] else option \
                for option in self._widget.options]


    @staticmethod
    def strip_option_status(option):
        if ConfigVarOpt._opt_prefixed_with_status(option):
            return option[1:].strip()
        else:
            return option

    def is_supported_widget(self):
        return isinstance(self._widget, (widgets.ToggleButtons, widgets.Select, widgets.Dropdown) )

    @owh.out.capture()
    def get_options_validity_icons(self):
        return [valid_opt_icon if valid else invalid_opt_icon for valid in self.options_validity]

    def get_value_index(self):
        if self._widget.value == None:
            return None
        try:
            return self._widget.options.index(self._widget.value)
        except:
            raise RuntimeError("ERROR: couldn't find value in options list")


    def set_value_to_first_valid_opt(self, inform_related_vars=True):
        for option in self._widget.options:
            if is_valid_option(option):
                self._widget.value = option
                if inform_related_vars:
                    for assertion in self.assertions:
                        for var_other in set(assertion.variables)-{self.name}:
                            if isinstance(ConfigVar.vdict[var_other], ConfigVarOpt):
                                ConfigVar.vdict[var_other].update_options_validity()
                return
        logger.error("Couldn't find any valid option for {}".format(self.name))

    @owh.out.capture()
    def observe_value_validity(self):
        if len(self.assertions)>0:
            logger.debug("Observing value validity for ConfigVar {}".format(self.name))
            self._widget.observe(
                self._check_selection_validity,
                names='value',
                type='change')

    @owh.out.capture()
    def unobserve_value_validity(self):
        if len(self.assertions)>0:
            logger.debug("Unobserving value validity for ConfigVar {}".format(self.name))
            self._widget.unobserve(
                self._check_selection_validity,
                names='value',
                type='change')


    @owh.out.capture()
    def update_options_validity(self, change=None):
        """Re-evaluates the validity of widget options and updates option validity icons """

        if isinstance(self._widget, DummyWidget):
            return # no validity update needed

        logger.debug("Updating option validities of ConfigVar {}".format(self.name))

        # If this method is called due to a change in an observed widget,
        # check if the options of this ConfigVar need to be updated yet.
        if change != None:
            if change['old'] == {}:
                logger.debug("Change in owner not finalized yet. Do nothing for ConfigVar {}".format(self.name))
                return
            logger.debug("change: {}".format(change))
            if not is_valid_option(change['owner'].value):
                logger.debug("Invalid selection at change owner. Do nothing for observing ConfigVar {}"\
                    .format(self.name))
                return

        assert self.is_supported_widget(), "ConfigVar {} widget is not supported yet.".format(self.name)

        self.options_validity = [True]*len(self._widget.options)
        self.error_msgs = ['']*len(self._widget.options)

        options_sans_validity = self.options_sans_validity()

        for i in range(len(options_sans_validity)):
            option = options_sans_validity[i]
            assert option.split()[0] not in [valid_opt_icon, invalid_opt_icon]

            def _instance_val_getter(cvName):
                val = ConfigVar.vdict[cvName].value
                if val == None:
                    val = "None"
                return val
            def _instance_val_getter_opt(cvName):
                if cvName == self.name:
                    return option
                val = ConfigVar.vdict[cvName].value
                if val == None:
                    val = "None"
                return val


            status, errMsg = True, ''
            for assertion in self.assertions:
                try:
                    self.compliances.check_assertion(
                        assertion,
                        _instance_val_getter,
                        _instance_val_getter_opt,
                    )
                except AssertionError as e:
                    self.options_validity[i] = False
                    self.error_msgs[i] = "{}".format(e)
                    break

        options_validity_icons = self.get_options_validity_icons()
        new_widget_options = \
            ['{}  {}'.format(options_validity_icons[i], options_sans_validity[i]) \
                for i in range(len(options_sans_validity))]

        if self._widget.options == new_widget_options:
            logger.debug("No validity changes in {}".format(self.name))
            return # no change in options validity
        else:
            logger.debug("Validity changes in the options of ConfigVar {}".format(self.name))

            old_val = self._widget.value
            if old_val:
               old_val_idx = self.get_value_index()

            self.unobserve_value_validity()
            self._widget.options = new_widget_options
            self._widget.value = None # this is needed here to prevent a weird behavior:
                         # in absence of this, widget selection clears for
                         # some reason

            if old_val != None and options_validity_icons[old_val_idx] != invalid_opt_icon:
                self._widget.value = self._widget.options[old_val_idx]
            if self._widget.value == None and self.never_unset:
                self.set_value_to_first_valid_opt()

            self.observe_value_validity()
            logger.debug("Options validity updated for {}".format(self.name))

    @owh.out.capture()
    def update_options(self, new_options=None, tooltips=None):
        """Assigns the options displayed in the widget."""

        logger.debug("Updating the options of ConfigVar {}".format(self.name))

        # First, update to new options
        self.unobserve_value_validity()
        self._widget.options = new_options
        self._widget.value = None
        self.observe_value_validity()

        # Second, update options validities
        self.update_options_validity()

        # If requested, pick the first valid value:
        if self.never_unset==True and self._widget.value==None:
            self.set_value_to_first_valid_opt()

        # Finally, update tooltips
        if tooltips:
            if isinstance(self._widget, widgets.ToggleButtons):
                self._widget.tooltips = tooltips
            else:
                raise NotImplementedError

    @owh.out.capture()
    def _check_selection_validity(self, change):

        logger.debug("Checking the validity for ConfigVar {} with value={}".format(self.name, self._widget.value))

        if change != None:
            assert change['name'] == 'value'
            new_val = change['new']
            if new_val != None and not is_valid_option(new_val):
                new_index = self.get_value_index()
                logger.critical("ERROR: Invalid selection for {}".format(self.name))
                logger.critical(self.error_msgs[new_index])
                from IPython.display import display, HTML, Javascript
                js = "<script>alert('ERROR: Invalid {} selection: {}');</script>".format(
                    self.name,
                    self.error_msgs[new_index]
                )
                display(HTML(js))
                self._widget.value = change['old']
            else:
                logger.debug("ConfigVar {} value is valid: {}".format(self.name, self._widget.value))
        else:
            raise NotImplementedError

class ConfigVarOptM(ConfigVarOpt):
    pass