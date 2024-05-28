import logging
from traitlets import Bool
from z3 import BoolRef, main_ctx, Z3_mk_const, to_symbol, BoolSort

from ProConPy.out_handler import handler as owh
from ProConPy.dev_utils import ConstraintViolation
from ProConPy.config_var import ConfigVar
from ProConPy.dialog import alert_error

logger = logging.getLogger(f"  {__name__.split('.')[-1]}")


class ConfigVarBool(ConfigVar, BoolRef):
    """A derived ConfigVar class with value of type Bool.
    """

    # trait
    value = Bool(allow_none=True)

    def __init__(self, name, *args, **kwargs):

        # Initialize the ConfigVar super class
        ConfigVar.__init__(self, name, *args, **kwargs)

        # Initialize the BoolRef super class, i.e., a Z3 bool
        # Below initialization mimics Bool() definition in z3.py
        ctx = main_ctx()
        BoolRef.__init__(
            self,
            Z3_mk_const(ctx.ref(), to_symbol(name, ctx), BoolSort(ctx).ast),
            ctx
        )

        # Set options list (No need to register options by setting .options attribute
        # since the value is a boolean and the options are fixed to True and False)
        self._options = [True, False]
        self.tooltips = ["True", "False"]
        self.update_options_validities()

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
            self._widget.value = self.value

    @owh.out.capture()
    def _process_frontend_value_change(self, change):
        """This is an observe method that gets called automatically after each widget value change.
        This method translates the widget value change to internal value change and ensures the
        widget value and the actual value are synched. In other words, this method propagates
        user-invoked frontend value change to backend."""

        if change["old"] == {}:
            return  # frontend-triggered change not finalized yet

        new_val = change["owner"].value
        if new_val is not self._widget_none_val:
            new_val = new_val[1:].strip()

        logger.info("Frontend changing %s widget value to %s", self.name, new_val)

        # Cast new_val from string to bool
        match new_val:
            case "True":
                new_val = True
            case "False":
                new_val = False
            case self._widget_none_val:
                new_val = None
            case _:
                raise ValueError(f"Invalid value {new_val} for Boolean variable {self.name}")

        try:
            self.value = new_val
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
                    else self.value
                )
            )
