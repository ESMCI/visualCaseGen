import logging
from visualCaseGen.dummy_widget import DummyWidget
from visualCaseGen.OutHandler import handler as owh
from visualCaseGen.config_var_base import ConfigVarBase, logic
from traitlets import HasTraits, Unicode, default, validate

logger = logging.getLogger(__name__)

class ConfigVarStr(ConfigVarBase):
    """ ConfigVar type with widget value of type String and ConfigVar value of type String.
    
    self._widget.value  : value preceded by a validity char. (of type String -- Trait)
    self.value:         : value NOT preceded by a validity char. (of type String -- Trait)
    """
    
    # trait
    value = Unicode(allow_none=True)

    @validate('value')
    def _validate_value(self, proposal):
        new_val = proposal['value']
        if new_val == self.value:
            return new_val # no value change, so return at this point

        if self.has_options() and new_val in self._options:
            if self._options_validities[new_val] == False:
                err_msg = logic.retrieve_error_msg(self, new_val)
                raise AssertionError(err_msg)
            logic.add_assignment(self, new_val, check_sat=False)
        else:
            logic.add_assignment(self, new_val, check_sat=True)

        # update widget value
        self._widget.value = self._widget_none_val if new_val is None else self.valid_opt_char+' '+new_val 

        # finally, set self.value by returning new_vals
        return new_val

    @owh.out.capture()
    def _process_frontend_value_change(self, change):
        if change['old'] == {}:
            return # frontend-triggered change not finalized yet
        
        # first check if valid selection
        new_widget_val = change['owner'].value 
        new_val_validity_char = new_widget_val[0] 
        new_val = new_widget_val[1:].strip()

        # if an invalid selection, display error message and set widget value to old value
        if self.has_options() and new_val_validity_char == self.invalid_opt_char:
            err_msg = logic.retrieve_error_msg(self, new_val)
            logger.critical("ERROR: %s", err_msg)
            from IPython.display import display, HTML
            js = "<script>alert('ERROR: {}');</script>".format(err_msg)
            display(HTML(js))
            
            # set to old value:
            self._widget.value = self._widget_none_val if self.value is None else '{} {}'\
                .format(self.valid_opt_char, self.value)
            return
        else:

            if new_val == self._widget_none_val:
                self.value = None
            else:
                self.value = new_val