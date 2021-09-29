import logging
import ipywidgets as widgets
from visualCaseGen.visualCaseGen.DummyWidget import DummyWidget
from visualCaseGen.visualCaseGen.CheckboxMulti import CheckboxMulti
from visualCaseGen.visualCaseGen.ConfigVar import ConfigVar
from visualCaseGen.visualCaseGen.OutHandler import handler as owh

logger = logging.getLogger(__name__)

invalid_opt_icon = chr(int("274C",base=16)) # Ballot Box with X
valid_opt_icon = chr(int("2713",base=16)) # Ballot Box with X

# it is assumed in this module that icons lenghts are one char.
assert len(invalid_opt_icon)==1 and len(valid_opt_icon)==1

class ConfigVarOptMS(ConfigVar):

    def __init__(self, name, never_unset=False, NoneVal=()):
        super().__init__(name)
        self._has_options = True
        self._options_validity = []
        self._error_msgs = []
        self._never_unset = never_unset # once the widget value is set, don't unset it
        self._NoneVal = NoneVal

    def is_supported_widget(self):
        return isinstance(self._widget, (widgets.SelectMultiple, CheckboxMulti) )

    @property
    def value(self):
        assert self._widget != None, "Cannot determine value for "+self.name+". Associated widget not initialized."
        if self._widget.value == self._NoneVal:
            return ''
        else:
            return '%'.join([val[1:].strip() for val in self._widget.value])

    @value.setter
    def value(self, val):
        if (val != self._NoneVal):
            if isinstance(val, str):
                if (val not in self.options):
                    raise ValueError("{} is an invalid option for {}. Valid options: {}".format(val, self.name, self.options))
                else:
                    assert val.split()[0] in [invalid_opt_icon, valid_opt_icon], \
                        "ConfigVarOptMS value must always have a status icon"
                self._widget.value = tuple(val.split('%'))
            else:
                assert isinstance(val, tuple)
                self._widget.value = val

    def value_status(self):
        if self._widget.value == self._NoneVal:
            return True
        else:
            return all([val.split()[0] == valid_opt_icon for val in self._widget.value])

    @ConfigVar.widget.setter
    def widget(self, widget):
        """Assigns the widget. Options of the passed in widget are assumed to be NOT preceded by status icons."""
        orig_widget_val = widget.value
        self._widget = widget
        self._widget.options = tuple(['{} {}'.format(valid_opt_icon, opt) for opt in widget.options])
        if orig_widget_val == self._NoneVal:
            self._widget.value = self._NoneVal
        else:
            self._widget.value = tuple(['{} {}'.format(valid_opt_icon, val) for val in list(orig_widget_val)])
        self._widget.value_status = self.value_status
        self._widget.parentCV = self
        self._observe_value_validity()

    @property
    def options(self):
        return self._widget.options

    @options.setter
    def options(self, opts):
        """Assigns the options displayed in the widget. Passed in options are assumed to be NOT preceded by status
        icons."""

        logger.debug("Updating the options of ConfigVarOptMS {}".format(self.name))

        # First, update to new options
        self._unobserve_value_validity()
        self._widget.options = tuple(['{} {}'.format(valid_opt_icon, opt) for opt in opts])
        self._widget.value = self._NoneVal
        # Second, update options validities
        self.update_options_validity()

        # If requested, pick the first valid value:
        if self._never_unset==True and self._widget.value==self._NoneVal:
            self._set_value_to_first_valid_opt()

        self._observe_value_validity()

    def is_valid_option(self, val):
        """ConfigVarOptMS-specific check for whether a value/option is valid."""
        if val == None or val == self._NoneVal:
            return True
        elif isinstance(val, str):
            if val[0] == valid_opt_icon:
                return True
            elif val[0] == invalid_opt_icon:
                return False
            else:
                raise RuntimeError("Cannot determine ConfigVarOptMS value validity: {}".format(val))
        else:
            assert isinstance(val, tuple), "Unknown val type for ConfigVarOptMS. Val:{}, Type:{}".format(val,type(val))
            return all([v[0] == valid_opt_icon for v in val])

    @property
    def tooltips(self):
        if isinstance(self._widget, CheckboxMulti):
            return self._widget.tooltips
        else:
            raise NotImplementedError

    @tooltips.setter
    def tooltips(self, tooltips):
        if isinstance(self._widget, CheckboxMulti):
            self._widget.tooltips = tooltips
        else:
            raise NotImplementedError

    @owh.out.capture()
    def _options_sans_validity(self):
        return [option[1:].strip() for option in self._widget.options]

    @owh.out.capture()
    def _get_options_validity_icons(self):
        return [valid_opt_icon if valid else invalid_opt_icon for valid in self._options_validity]

    def _set_value_to_first_valid_opt(self, inform_related_vars=True):
        for option in self._widget.options:
            if self.is_valid_option(option):
                self._widget.value = (option,)
                if inform_related_vars:
                    for assertion in self.assertions:
                        for var_other in set(assertion.variables)-{self.name}:
                            if ConfigVar.vdict[var_other]._has_options:
                                ConfigVar.vdict[var_other].update_options_validity()
                return
        if len(self._widget.options)>0:
            logger.error("Couldn't find any valid option for {}".format(self.name))

    @owh.out.capture()
    def _observe_value_validity(self):
        if (not self._val_validity_obs_on) and self.compliances != None and len(self.assertions)>0:
            logger.debug("Observing value validity for ConfigVarOptMS {}".format(self.name))
            self._widget.observe(
                self._check_selection_validity,
                names='value',
                type='change')
            self._val_validity_obs_on = True

    @owh.out.capture()
    def _unobserve_value_validity(self):
        if self._val_validity_obs_on and self.compliances != None and len(self.assertions)>0:
            logger.debug("Unobserving value validity for ConfigVarOptMS {}".format(self.name))
            self._widget.unobserve(
                self._check_selection_validity,
                names='value',
                type='change')
            self._val_validity_obs_on = False


    @owh.out.capture()
    def update_options_validity(self, change=None):
        """Re-evaluates the validity of widget options and updates option validity icons """

        if isinstance(self._widget, DummyWidget):
            return # no validity update needed
        elif self.compliances == None:
            return

        logger.debug("Updating option validities of ConfigVarOptMS {}".format(self.name))

        # If this method is called due to a change in an observed widget,
        # check if the options of this ConfigVarOptMS need to be updated yet.
        if change != None:
            if change['old'] == {} and not isinstance(change['owner'], CheckboxMulti):
                logger.debug("Change in owner not finalized yet. Do nothing for ConfigVarOptMS {}".format(self.name))
                return
            logger.debug("change: {}".format(change))
            owner_cv = change['owner'].parentCV 
            owner_val = change['owner'].value 
            if not owner_cv.is_valid_option(owner_val):
                logger.debug("Invalid selection at change owner. Do nothing for observing ConfigVarOptMS {}"\
                    .format(self.name))
                return

        assert self.is_supported_widget(), "ConfigVarOptMS {} widget is not supported yet.".format(self.name)

        self._options_validity = [True]*len(self._widget.options)
        self._error_msgs = ['']*len(self._widget.options)

        options_sans_validity = self._options_sans_validity()

        for i in range(len(options_sans_validity)):
            option = options_sans_validity[i]

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
                    self._options_validity[i] = False
                    self._error_msgs[i] = "{}".format(e)
                    break

        options_validity_icons = self._get_options_validity_icons()
        new_widget_options = \
            ['{}  {}'.format(options_validity_icons[i], options_sans_validity[i]) \
                for i in range(len(options_sans_validity))]

        if self._widget.options == tuple(new_widget_options):
            logger.debug("No validity changes in {}".format(self.name))
            return # no change in options validity
        else:
            logger.debug("Validity changes in the options of ConfigVarOptMS {}".format(self.name))

            old_val = self._widget.value
            old_val_idx = None
            if old_val != self._NoneVal:
               old_val_idx = self._widget.index

            self._unobserve_value_validity()
            self._widget.options = new_widget_options
            self._widget.value = self._NoneVal # this is needed here to prevent a weird behavior:
                         # in absence of this, widget selection clears for
                         # some reason

            if old_val != self._NoneVal and all([self._options_validity[ix]==True for ix in old_val_idx]):
                self._widget.index = old_val_idx
            if self._widget.value == self._NoneVal and self._never_unset:
                self._set_value_to_first_valid_opt()

            self._observe_value_validity()
            logger.debug("Options validity updated for {}".format(self.name))

    @owh.out.capture()
    def _check_selection_validity(self, change):

        logger.debug("Checking the validity for ConfigVarOptMS {} with value={}".format(self.name, self._widget.value))

        if change != None:
            assert change['name'] == 'value'
            new_val = change['new']
            if new_val != self._NoneVal and not self.is_valid_option(new_val):
                invalid_ix = None
                for ix in self._widget.index:
                    if self._options_validity[ix] == False:
                        invalid_ix = ix
                        break
                if invalid_ix == None:
                    raise RuntimeError("Couldn't find a value entry with invalid status")
                logger.critical("ERROR: Invalid selection for {}".format(self.name))
                logger.critical(self._error_msgs[invalid_ix])
                from IPython.display import display, HTML, Javascript
                js = "<script>alert('ERROR: Invalid {} selection: {}');</script>".format(
                    self.name,
                    self._error_msgs[invalid_ix]
                )
                display(HTML(js))
                self._widget.value = change['old']
            else:
                logger.debug("ConfigVarOptMS {} value is valid: {}".format(self.name, self._widget.value))
        else:
            raise NotImplementedError