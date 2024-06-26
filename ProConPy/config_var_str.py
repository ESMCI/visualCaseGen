import logging
import re
from traitlets import Unicode
from z3 import SeqRef, main_ctx, Z3_mk_const, to_symbol, StringSort

from ProConPy.out_handler import handler as owh
from ProConPy.dev_utils import ConstraintViolation
from ProConPy.config_var import ConfigVar
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

    def __init__(self, name, *args, word_only=False, **kwargs):

        # If word_only is True, single words containing alphanumeric characters, underscore, and backslash are allowed.
        self._word_only = word_only

        # Initialize the ConfigVar super class
        ConfigVar.__init__(self, name, *args, **kwargs)

        # Initialize the SeqRef super class, i.e., a Z3 string
        # Below initialization mimics String() definition in z3.py
        ctx = main_ctx()
        SeqRef.__init__(
            self, Z3_mk_const(ctx.ref(), to_symbol(name, ctx), StringSort(ctx).ast), ctx
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
            self._widget.value = self._valid_opt_char + " " + self.value
        else:
            if self.is_aux_var is True:
                # No need to update widget values of aux vars
                self._widget.value = self._widget_none_val  
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

        # remove the validity char from the new_val if it exists
        if self.has_options():
            new_val = new_val[1:].strip()

        logger.info("Frontend changing %s widget value to %s", self.name, new_val)

        try:
            if self._word_only and new_val != self._widget_none_val:
                is_word_only = bool(re.match(r"^[a-zA-Z0-9_/]*$", new_val))
                # confirm the value is a single word containing alphanumeric characters, underscore, and backslash
                if not is_word_only:
                    alert_error(f"Must enter a single word containing alphanumeric characters, underscore, and backslash.")
                    self._widget.value = self.widget_none_val if self.value is None else str(self.value)
                    return

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
                else (
                    f"{self._valid_opt_char} {self.value}"
                    if self.has_options()
                    else self.value
                )
            )
