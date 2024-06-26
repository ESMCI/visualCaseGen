import logging
from traitlets import Float
from z3 import ArithRef, main_ctx, Z3_mk_const, to_symbol, RealSort

from ProConPy.out_handler import handler as owh
from ProConPy.dev_utils import ConstraintViolation, is_number
from ProConPy.config_var import ConfigVar
from ProConPy.dialog import alert_error

logger = logging.getLogger(f"  {__name__.split('.')[-1]}")


class ConfigVarReal(ConfigVar, ArithRef):
    """A derived ConfigVar class with value of type Real. Note that, as far as the
    csp_solver is concerned, the value of this class is a z3 Real. However, the
    value trait is Float.
    """

    # trait
    value = Float(allow_none=True)

    def __init__(self, name, *args, **kwargs):

        # Initialize the ConfigVar super class
        ConfigVar.__init__(self, name, *args, **kwargs, widget_none_val="")

        # Initialize the ArithRef super class, i.e., a Z3 Real
        # Below initialization mimics Real() definition in z3.py
        ctx = main_ctx()
        ArithRef.__init__(
                self,
                Z3_mk_const(ctx.ref(), to_symbol(name, ctx), RealSort(ctx).ast),
                ctx
            )

    @owh.out.capture()
    def _update_widget_value(self):
        """This methods gets called by _post_value_change and other methods to update the
        displayed widget value whenever the internal value changes. In other words, this
        method propagates backend value change to frontend."""

        logger.debug("Updating widget value %s=%s", self.name, self.value)

        if self.value is None:
            self._widget.value = self._widget_none_val
        elif self.has_options():
            self._widget.value = self._valid_opt_char + " " + str(self.value)
        else:
            self._widget.value = str(self.value)

    @owh.out.capture()
    def _process_frontend_value_change(self, change):
        """This is an observe method that gets called automatically after each widget value change.
        This method translates the widget value change to internal value change and ensures the
        widget value and the actual value are synched. In other words, this method propagates
        user-invoked frontend value change to backend."""

        if change["old"] == {}:
            return  # frontend-triggered change not finalized yet

        new_val = change["owner"].value

        # remove the validity char from the new_val if it exists
        if self.has_options():
            new_val = new_val[1:].strip()

        logger.info("Frontend changing %s widget value to %s", self.name, new_val)

        try:
            if new_val == self._widget_none_val:
                self.value = None
            else:
                if not is_number(new_val):
                    alert_error(f"Must enter an integer for {self.name}.")
                    self._widget.value = self.widget_none_val if self.value is None else str(self.value)
                    return

                self.value = float(new_val)
        except ConstraintViolation as err:
            # inform the user that the selection is invalid
            logger.critical("ERROR: %s", err.message)
            alert_error(err.message)

            # set widget to old value
            self._widget.value = (
                self._widget_none_val
                if self.value is None
                else (
                    f"{self._valid_opt_char} {self.value}"
                    if self.has_options()
                    else str(self.value)
                )
            )
       
    @ConfigVar.widget.setter
    def widget(self, new_widget):
        # first call the parent widget setter:
        ConfigVar.widget.fset(self, new_widget)
        # now, set continuous_update property to false because otherwise all keystrokes
        # will call the _process_frontend_value_change method
        self._widget.continuous_update = False
