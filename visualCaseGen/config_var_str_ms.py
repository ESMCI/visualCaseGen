import logging
from visualCaseGen.dummy_widget import DummyWidget
from visualCaseGen.OutHandler import handler as owh
from visualCaseGen.config_var import ConfigVar
from visualCaseGen.dev_utils import RunError
from visualCaseGen.dialog import alert_error
from visualCaseGen.logic import logic
from traitlets import HasTraits, Unicode, default, validate

logger = logging.getLogger('\t'+__name__.split('.')[-1])

class ConfigVarStrMS(ConfigVar):
    """ ConfigVar type with widget value of type Tuple of strings and ConfigVar value of type String. 
    
    self._widget.value  : values, each preceded by a validity char. (Tuple of Strings -- Trait)
    self.value:         : values, NOT preceded by a char. (A single String that joins multiple vals by '%')
    """

    # trait
    value = Unicode(allow_none=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, widget_none_val=())

    @validate('value')
    def _validate_value(self, proposal):
        new_vals = proposal['value'] # values, NOT preceded by a char. (A single String joined by '%'!) 
        logger.debug("Assigning value %s=%s", self.name, new_vals)

        assert isinstance(new_vals, str), "New values must be of type string joined by '%'"

        # confirm the value validity
        if self.has_options():
            for new_val in new_vals.split('%'):
                if new_val not in self._options:
                    raise RunError("Value {} not found in {} options list: {}".format(new_val, self.name, self.options))
                if self._options_validities[new_val] == False:
                    err_msg = logic.retrieve_error_msg(self, new_val)
                    raise AssertionError(self._error_messages[new_val])
        else:
            logic.check_assignment(self, new_vals)

        # finally, set self.value by returning new_vals
        return new_vals

    @owh.out.capture()
    def _update_widget_value(self):
        if self.value is None:
            self._widget.value = self._widget_none_val
        else:
            self._widget.value = tuple(self.valid_opt_char+' '+val for val in self.value.split('%'))

    @owh.out.capture()
    def _process_frontend_value_change(self, change):
        if change['old'] == {}:
            return # frontend-triggered change not finalized yet
        
        # first check if valid selection
        new_widget_vals = change['owner'].value 

        if new_widget_vals == self._widget_none_val and self._always_set is True:
            # Attempted to set the value to None while always_set property is True.
            # Revert the frontend change by calling _update_widget_value and return.
            self._update_widget_value()
            return

        logger.info("Frontend changing %s widget value to %s", self.name, new_widget_vals)

        for new_widget_val in new_widget_vals:
            new_val_validity_char = new_widget_val[0] 
            new_val = new_widget_val[1:].strip()

            # if an invalid selection, display error message and set widget value to old value
            if self.has_options() and new_val_validity_char == self.invalid_opt_char:
                err_msg = logic.retrieve_error_msg(self, new_val)
                logger.critical("ERROR: %s", err_msg)
                alert_error(err_msg)
            
                # set to old value:

                if self.value is None:
                    self._widget.value = self._widget_none_val
                else:
                    self._widget.value = tuple('{} {}'.format(self.valid_opt_char, val) for val in self.value.split('%'))
                return

        if self._widget.value == self._widget_none_val:
            self.value = None
        else:
            self.value = '%'.join([val[1:].strip() for val in self._widget.value])