import logging
from visualCaseGen.dummy_widget import DummyWidget
from visualCaseGen.OutHandler import handler as owh
import visualCaseGen.logic_engine as logic
from visualCaseGen.config_var_base import ConfigVarBase
from z3 import SeqRef, main_ctx, Z3_mk_const, to_symbol, StringSort
from traitlets import HasTraits, Unicode, default, validate

logger = logging.getLogger(__name__)

class ConfigVarStrMS(ConfigVarBase):
    """ ConfigVar type with widget value of type Tuple of strings and ConfigVar value of type String. 
    
    self._widget.value  : values, each preceded by a validity char. (Tuple of Strings -- Trait)
    self._value         : values, NOT preceded by a validity char. (Tuple of Strings -- Data member)
    self.value:         : values, NOT preceded by a char. (A single String! Equivalent to '%'.join(self._value -- Trait)
    """

    def __init__(self, name, value=None, options=None, tooltips=(), ctx=None, always_set=False, widget_none_val=None):
        super().__init__(name, value, options, tooltips, ctx, always_set, widget_none_val=())

    # trait
    value = Unicode(allow_none=True)

    @validate('value')
    def _validate_value(self, proposal):
        new_vals = proposal['value'] # values, NOT preceded by a char. (A single String joined by '%'!) 

        assert isinstance(new_vals, str), "New values must be of type string joined by '%'"
        # check if any new val is an invalid option:
        if has_options():
            for new_val in new_vals.split('%'):
                assert new_val in self._options, "Value not found in options list"
                if self._options_validities[new_val] == False:
                    raise AssertionError(self._error_messages[new_val])

        logic.register_assignment(self, new_vals, check_sat=True)

        # update widget value
        if new_vals is None:
            self._widget.value = self._widget_none_val
        else:
            self._widget.value = (self.valid_opt_char+' '+new_val for new_val in new_vals.split('%'))

        # update internal value
        self._value = new_vals

        # finally, inform all related vars about this value change by calling their _update_options
        # this will update options validities.
        for var in self._related_vars:
            if var.has_options():
                var._update_options()
        
        return new_vals

    @owh.out.capture()
    def _process_frontend_value_change(self, change):
        if change['old'] == {}:
            return # frontend-triggered change not finalized yet
        
        # first check if valid selection
        new_widget_vals = change['owner'].value 
        for new_widget_val in new_widget_vals:
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

                if self._value is None:
                    self._widget.value = self._widget_none_val
                else:
                    self._widget.value = ('{} {}'.format(self.valid_opt_char, val) for val in self._value)
                return

        if self._widget.value == self._widget_none_val:
            self.value = None
        else:
            self.value = '%'.join([val[1:].strip() for val in self._widget.value])