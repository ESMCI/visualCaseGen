import logging
from traitlets import Float, validate
from z3 import ArithRef, main_ctx, Z3_mk_const, to_symbol, RealSort

from visualCaseGen.OutHandler import handler as owh
from visualCaseGen.config_var import ConfigVar
from visualCaseGen.dialog import alert_error
from visualCaseGen.logic import logic
from visualCaseGen.dev_utils import is_number

logger = logging.getLogger("\t" + __name__.split(".")[-1])


class ConfigVarReal(ConfigVar, ArithRef):
    """A derived ConfigVar class with value of type Real.
    """

    # trait
    value = Float(allow_none=True)

    def __init__(self, name, *args, **kwargs):

        # Initialize the ConfigVar super class
        ConfigVar.__init__(self, name, *args, **kwargs, widget_none_val='')

        # Initialize the ArithRef super class, i.e., a Z3 Real
        # Below initialization mimics Real() definition in z3.py
        ctx = main_ctx()
        ArithRef.__init__(
                self,
                Z3_mk_const(ctx.ref(), to_symbol(name, ctx), RealSort(ctx).ast),
                ctx
            )

    @validate("value")
    def _validate_value(self, proposal):
        """This method is called automatially to verify that the new value is valid.
        Note that this method is NOT called if the new value is None."""

        new_val = proposal["value"]
        logger.debug("Assigning value %s=%s", self.name, new_val)

        # confirm the value validity
        if self.has_finite_options_list():
            raise NotImplementedError
        else:
            logic.check_assignment(self, new_val)

        # finally, set self.value by returning new_vals
        return new_val

    @owh.out.capture()
    def _update_widget_value(self):
        """This methods gets called by _post_value_change and other methods to update the
        displayed widget value whenever the internal value changes. In other words, this
        method propagates backend value change to frontend."""
        self._widget.value = self.widget_none_val if self.value is None else str(self.value)

    @owh.out.capture()
    def _process_frontend_value_change(self, change):
        """This is an observe method that gets called automatically after each widget value change.
        This method translates the widget value change to internal value change and ensures the
        widget value and the actual value are synched. In other words, this method propagates
        user-invoked frontend value change to backend."""

        if change["old"] == {}:
            return  # frontend-triggered change not finalized yet

        if self.has_finite_options_list():
            raise NotImplementedError

        else:
            new_val = change["owner"].value

            if new_val == '':
                self.value = None
                return

            # First check if the string is a number
            if not is_number(new_val):
                alert_error(f"The value {new_val} entered for {self.name} is not a number!")
                # set back to old value:
                self._widget.value = self.widget_none_val if self.value is None else str(self.value)
                return

            # Now, check if the selection is sat
            outcome, err_msg = logic.check_assignment(self, new_val, return_outcome=True)

            if outcome is False:
                logger.critical("ERROR: %s", err_msg)
                alert_error(err_msg)
                # set to old value:
                self._widget.value = self.widget_none_val if self.value is None else str(self.value)
                return

            else:
                self.value = float(new_val)


    @ConfigVar.widget.setter
    def widget(self, new_widget):
        # first call the parent widget setter:
        ConfigVar.widget.fset(self, new_widget)
        # now, set continuous_update property to false because otherwise all keystrokes
        # will call the _process_frontend_value_change method
        self._widget.continuous_update = False
