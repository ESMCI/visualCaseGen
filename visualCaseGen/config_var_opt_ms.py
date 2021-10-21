import logging
import ipywidgets as widgets
from .dummy_widget import DummyWidget
from .checkbox_multi_widget import CheckboxMultiWidget
from .config_var import ConfigVar
from .OutHandler import handler as owh

logger = logging.getLogger(__name__)

class ConfigVarOptMS(ConfigVar):

    invalid_opt_icon = chr(int("274C",base=16))
    valid_opt_icon = chr(int("2713",base=16))

    def __init__(self, name, always_set=False, never_unset=False, none_val=()):
        super().__init__(name, none_val)
        self._has_options = True
        self._options_validity = []
        self._error_msgs = []
        self._always_set = always_set # the widget must always have a set value
        self._never_unset = never_unset or always_set # once the widget value is set, don't unset it

    def is_supported_widget(self):
        return isinstance(self._widget, (widgets.SelectMultiple, CheckboxMultiWidget) )

    @property
    def value(self):
        assert self._widget is not None, "Cannot determine value for "+self.name+". Associated widget not initialized."
        if self._widget.value == self._none_val:
            return ''
        return '%'.join([val[1:].strip() for val in self._widget.value])

    @value.setter
    def value(self, val):
        if val != self._none_val:
            if isinstance(val, str):
                if val not in self.options:
                    raise ValueError("{} is an invalid option for {}. Valid options: {}"\
                        .format(val, self.name, self.options))
                assert val.split()[0] in [self.invalid_opt_icon, self.valid_opt_icon], \
                    "ConfigVarOptMS value must always have a status icon"
                self._widget.value = tuple(val.split('%'))
            else:
                assert isinstance(val, tuple)
                self._widget.value = val

    def value_status(self):
        if self._widget.value == self._none_val:
            return True
        return all(val.split()[0] == self.valid_opt_icon for val in self._widget.value)

    @ConfigVar.widget.setter
    def widget(self, widget):
        """Assigns the widget. Options of the passed in widget are assumed to be NOT preceded by status icons."""
        orig_widget_val = widget.value
        self._widget = widget
        self._widget.options = tuple('{}  {}'.format(self.valid_opt_icon, opt) for opt in widget.options)
        if orig_widget_val == self._none_val:
            self._widget.value = self._none_val
        else:
            self._widget.value = tuple('{}  {}'.format(self.valid_opt_icon, val) for val in list(orig_widget_val))
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

        logger.debug("Updating the options of ConfigVarOptMS %s", self.name)

        # First, update to new options
        self._unobserve_value_validity()
        self._widget.options = tuple('{}  {}'.format(self.valid_opt_icon, opt) for opt in opts)
        self._widget.value = self._none_val
        # Second, update options validities
        self.update_options_validity()

        # If requested, pick the first valid value:
        if self._never_unset is True and self._widget.value==self._none_val:
            self._set_value_to_first_valid_opt()

        self._observe_value_validity()

    def is_valid_option(self, val):
        """ConfigVarOptMS-specific check for whether a value/option is valid."""
        if val in (None, self._none_val):
            return True
        if isinstance(val, str):
            if val[0] == self.valid_opt_icon:
                return True
            if val[0] == self.invalid_opt_icon:
                return False
            raise RuntimeError("Cannot determine ConfigVarOptMS value validity: {}".format(val))
        else:
            assert isinstance(val, tuple), "Unknown val type for ConfigVarOptMS. Val:{}, Type:{}".format(val,type(val))
            return all(v[0] == self.valid_opt_icon for v in val)

    @property
    def tooltips(self):
        if isinstance(self._widget, CheckboxMultiWidget):
            return self._widget.tooltips
        raise NotImplementedError

    @tooltips.setter
    def tooltips(self, tooltips):
        if isinstance(self._widget, CheckboxMultiWidget):
            self._widget.tooltips = tooltips
        else:
            raise NotImplementedError

    @owh.out.capture()
    def _options_sans_validity(self):
        return [option[1:].strip() for option in self._widget.options]

    @owh.out.capture()
    def _get_options_validity_icons(self):
        return [self.valid_opt_icon if valid else self.invalid_opt_icon for valid in self._options_validity]

    def _set_value_to_first_valid_opt(self, inform_related_vars=True):
        for option in self._widget.options:
            if self.is_valid_option(option):
                self._unobserve_value_validity()
                self._widget.value = (option,)
                self._observe_value_validity()
                if inform_related_vars:
                    for assertion in self.assertions:
                        for var_other in set(assertion.variables)-{self.name}:
                            if ConfigVar.vdict[var_other]._has_options:
                                ConfigVar.vdict[var_other].update_options_validity()
                return
        if len(self._widget.options)>0:
            logger.error("Couldn't find any valid option for %s", self.name)

    @owh.out.capture()
    def _observe_value_validity(self):
        if (not self._val_validity_obs_on) and (self.compliances is not None) and len(self.assertions)>0:
            logger.debug("Observing value validity for ConfigVarOptMS %s", self.name)
            self._widget.observe(
                self._check_selection_validity,
                names='value',
                type='change')
            self._val_validity_obs_on = True

    @owh.out.capture()
    def _unobserve_value_validity(self):
        if self._val_validity_obs_on and (self.compliances is not None) and len(self.assertions)>0:
            logger.debug("Unobserving value validity for ConfigVarOptMS %s", self.name)
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
        if self.compliances is None:
            return

        # If this method is called due to a change in an observed widget,
        # check if the options of this ConfigVarOptMS need to be updated yet.
        if change is not None:
            if change['old'] == {}:
                logger.debug("Change in owner not finalized yet. Do nothing for ConfigVarOptMS %s", self.name)
                return
            logger.debug("change: %s", change)
            owner_cv = change['owner'].parentCV
            owner_val = change['owner'].value
            if not owner_cv.is_valid_option(owner_val):
                logger.debug("Invalid selection at change owner. Do nothing for observing ConfigVarOptMS %s", self.name)
                return

        logger.debug("Updating option validities of ConfigVarOptMS %s", self.name)

        assert self.is_supported_widget(), "ConfigVarOptMS {} widget is not supported yet.".format(self.name)

        self._options_validity = [True]*len(self._widget.options)
        self._error_msgs = ['']*len(self._widget.options)

        options_sans_validity = self._options_sans_validity()

        for i, option in enumerate(options_sans_validity):

            def _instance_val_getter(cv_name):
                val = ConfigVar.vdict[cv_name].value
                if val is None:
                    val = "None"
                return val
            def _instance_val_getter_opt(cv_name):
                if cv_name == self.name:
                    return option
                val = ConfigVar.vdict[cv_name].value
                if val is None:
                    val = "None"
                return val

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
            tuple('{}  {}'.format(options_validity_icons[i], options_sans_validity[i]) \
                for i in range(len(options_sans_validity)))

        if self._widget.options == new_widget_options:
            logger.debug("No validity changes in %s", self.name)
            return # no change in options validity

        logger.debug("Validity changes in the options of ConfigVarOptMS %s", self.name)

        old_val = self._widget.value
        old_val_idx = None
        if old_val != self._none_val:
            old_val_idx = self._widget.index

        self._unobserve_value_validity()
        self._widget.options = new_widget_options
        self._widget.value = self._none_val # this is needed here to prevent a weird behavior:
                     # in absence of this, widget selection clears for
                     # some reason

        if old_val != self._none_val and all(self._options_validity[ix] is True for ix in old_val_idx):
            self._widget.index = old_val_idx
        if self._widget.value == self._none_val and self._never_unset:
            self._set_value_to_first_valid_opt()

        self._observe_value_validity()
        logger.debug("Options validity updated for %s", self.name)

    @owh.out.capture()
    def _check_selection_validity(self, change):

        logger.debug("Checking the validity for ConfigVarOptMS %s with value=%s", self.name, self._widget.value)

        if change is not None:
            assert change['name'] == 'value'
            new_val = change['new']
            if new_val == self._none_val:
                if self._always_set:
                    self._set_value_to_first_valid_opt()
            else:
                if self.is_valid_option(new_val):
                    logger.debug("ConfigVarOptMS %s value is valid: %s", self.name, self._widget.value)
                else:
                    invalid_ix = None
                    for ix in self._widget.index:
                        if self._options_validity[ix] is False:
                            invalid_ix = ix
                            break
                    if invalid_ix is None:
                        raise RuntimeError("Couldn't find a value entry with invalid status")
                    logger.critical("ERROR: Invalid selection for %s", self.name)
                    logger.critical(self._error_msgs[invalid_ix])
                    from IPython.display import display, HTML
                    js = "<script>alert('ERROR: Invalid {} selection: {}');</script>".format(
                        self.name,
                        self._error_msgs[invalid_ix]
                    )
                    display(HTML(js))
                    self._widget.value = change['old']
        else:
            raise NotImplementedError
