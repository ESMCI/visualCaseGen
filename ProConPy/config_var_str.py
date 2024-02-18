import logging
from traitlets import Unicode, validate
from z3 import SeqRef, main_ctx, Z3_mk_const, to_symbol, StringSort

from ProConPy.out_handler import handler as owh
from ProConPy.dev_utils import ConstraintViolation
from ProConPy.config_var import ConfigVar
from ProConPy.csp_solver import csp
from ProConPy.dialog import alert_error

logger = logging.getLogger(f"  {__name__.split('.')[-1]}")


class ConfigVarStr(ConfigVar, SeqRef):
    """A derived ConfigVar class with value of type String. Each instance can have a single
    string or None as its value.

    self._widget.value  : value preceded by a validity char. (of type String -- Trait)
    self.value:         : value NOT preceded by a validity char. (of type String -- Trait)
    """

    # trait
    value = Unicode(allow_none=True)

    def __init__(self, name, *args, **kwargs):

        # Initialize the ConfigVar super class
        ConfigVar.__init__(self, name, *args, **kwargs)

        # Initialize the SeqRef super class, i.e., a Z3 string
        # Below initialization mimics String() definition in z3.py
        ctx = main_ctx()
        SeqRef.__init__(
            self, Z3_mk_const(ctx.ref(), to_symbol(name, ctx), StringSort(ctx).ast), ctx
        )

    @validate("value")
    def _validate_value(self, proposal):
        """This method is called automatially to verify that the new value is valid.
        Note that this method is NOT called if the new value is None."""

        new_val = proposal["value"]
        logger.debug("Validating %s=%s", self.name, new_val)

        # confirm the value validity. If not valid, the below call will raise an exception.
        csp.check_assignment(self, new_val)

        # finally, set self.value by returning new_vals
        logger.debug("Validation done. Assigning %s=%s", self.name, new_val)
        return new_val

    @owh.out.capture()
    def _update_widget_value(self):
        """This methods gets called by _post_value_change and other methods to update the
        displayed widget value whenever the internal value changes. In other words, this
        method propagates backend value change to frontend."""

        logger.debug("Updating widget value %s=%s", self.name, self.value)

        if self.value is None:
            self._widget.value = self._widget_none_val
        elif self.has_options():
            self._widget.value = self._valid_opt_char + " " + self.value
        else:
            raise NotImplementedError  # the variable has infinite domain

    @owh.out.capture()
    def _process_frontend_value_change(self, change):
        """This is an observe method that gets called automatically after each widget value change.
        This method translates the widget value change to internal value change and ensures the
        widget value and the actual value are synched. In other words, this method propagates
        user-invoked frontend value change to backend."""

        if change["old"] == {}:
            return  # frontend-triggered change not finalized yet

        if self.has_options():
            # first check if valid selection
            new_widget_val = change["owner"].value
            new_val = new_widget_val[1:].strip()

            if new_widget_val == self._widget_none_val and self._always_set is True:
                # Attempted to set the value to None while always_set property is True.
                # Revert the frontend change by calling _update_widget_value and return.
                self._update_widget_value()
                return

            logger.info(
                "Frontend changing %s widget value to %s", self.name, new_widget_val
            )

            try:
                if new_val == self._widget_none_val:
                    self.value = None
                else:
                    self.value = new_val
            except ConstraintViolation as err:
                # inform the user that the selection is invalid
                logger.critical("ERROR: %s", err.message)
                alert_error(err.message)

                # set widget to old value
                self._widget.value = (
                    self._widget_none_val
                    if self.value is None
                    else f"{self._valid_opt_char} {self.value}"
                )

        else:
            raise NotImplementedError  # the variable has infinite domain
