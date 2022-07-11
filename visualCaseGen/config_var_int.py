import logging
from traitlets import Int, validate
from z3 import ArithRef, main_ctx, Z3_mk_const, to_symbol, IntSort

from visualCaseGen.OutHandler import handler as owh
from visualCaseGen.config_var_opt import ConfigVarOpt
from visualCaseGen.dialog import alert_error
from visualCaseGen.logic import logic

logger = logging.getLogger("\t" + __name__.split(".")[-1])


class ConfigVarInt(ConfigVarOpt, ArithRef):
    """A derived ConfigVar class with value of type Int.
    """

    # trait
    value = Int(allow_none=True)

    def __init__(self, name, *args, **kwargs):

        # Initialize the ConfigVarOpt super class
        ConfigVarOpt.__init__(self, name, *args, **kwargs)

        # Initialize the ArithRef super class, i.e., a Z3 int
        # Below initialization mimics Int() definition in z3.py
        ctx = main_ctx()
        ArithRef.__init__(
                self, 
                Z3_mk_const(ctx.ref(), to_symbol(name, ctx), IntSort(ctx).ast),
                ctx
            )

    @validate("value")
    def _validate_value(self, proposal):
        """This method is called automatially to verify that the new value is valid.
        Note that this method is NOT called if the new value is None."""

        new_val = proposal["value"]
        logger.debug("Assigning value %s=%s", self.name, new_val)

        # confirm the value validity
        if new_val in self._options:
            if self._options_validities[new_val] is False:
                err_msg = logic.retrieve_error_msg(self, new_val)
                raise AssertionError(err_msg)
        else:
            logic.check_assignment(self, new_val)

        # finally, set self.value by returning new_vals
        return new_val

    @owh.out.capture()
    def _update_widget_value(self):
        """This methods gets called by _post_value_change and other methods to update the
        displayed widget value whenever the internal value changes. In other words, this
        method propagates backend value change to frontend."""
        raise NotImplementedError

    @owh.out.capture()
    def _process_frontend_value_change(self, change):
        """This is an observe method that gets called automatically after each widget value change.
        This method translates the widget value change to internal value change and ensures the
        widget value and the actual value are synched. In other words, this method propagates
        user-invoked frontend value change to backend."""
        raise NotImplementedError
