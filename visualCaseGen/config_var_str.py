import logging
from visualCaseGen.dummy_widget import DummyWidget
from visualCaseGen.OutHandler import handler as owh
import visualCaseGen.logic_engine as logic
from visualCaseGen.config_var_base import ConfigVarBase
from z3 import SeqRef, main_ctx, Z3_mk_const, to_symbol, StringSort
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

        if self.has_options() and new_val in self._options:
            if self._options_validities[new_val] == True:
                logic.register_assignment(self, new_val, check_sat=False)
            else:
                raise AssertionError(self._error_messages[new_val])
        else:
            logic.register_assignment(self, new_val, check_sat=True)

        # update widget value
        self._widget.value = self._widget_none_val if new_val is None else self.valid_opt_char+' '+new_val 

        # finally, inform all related vars about this value change by calling their _update_options
        # this will update options validities.
        for var in self._related_vars:
            if var.has_options():
                var._update_options()
        
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
            logger.critical("ERROR: %s", self._error_messages[new_val])
            from IPython.display import display, HTML
            js = "<script>alert('ERROR: {}');</script>".format(
                self._error_messages[new_val]
            )
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