import logging

from ProConPy.out_handler import handler as owh
from ProConPy.config_var_str import ConfigVarStr
from ProConPy.csp_solver import csp
from ProConPy.dialog import alert_error

logger = logging.getLogger(f"  {__name__.split('.')[-1]}")


class ConfigVarStrMS(ConfigVarStr):
    """A derived ConfigVar class with value(s) of type String. Each instance can have one or
    more strings or None as its value.

    self._widget.value  : values, each preceded by a validity char. (Tuple of Strings -- Trait)
    self.value:         : values, NOT preceded by a char. (A single String that joins multiple vals by '%')
    """

    def __init__(self, *args, **kwargs):
        # Set widget_none_val to an empty tuple as opposed to the default, that is None.
        super().__init__(*args, **kwargs, widget_none_val=(), value_delimiter="%")

    @owh.out.capture()
    def _update_widget_value(self):
        """This methods gets called by _post_value_change and other methods to update the
        displayed widget value whenever the internal value changes. In other words, this
        method propagates backend value change to frontend."""

        logger.debug("Updating widget value %s=%s", self.name, self.value)

        if self.value is None:
            self._widget.value = self._widget_none_val
        elif self.has_options():
            self._widget.value = tuple(
                self._valid_opt_char + " " + val for val in self.value.split(self._value_delimiter)
            )
        else:
            # If a ConfigVarStrMS has no options, it must be an aux var of the current stage.
            assert self.is_aux_var is True, \
                f"Encountered a ConfigVarStrMS with no options list that is not an aux var "+\
                "of the current stage: {self.name}"
            # Hence, no need to set the widget value.
            self._widget.value = ()

    @owh.out.capture()
    def _process_frontend_value_change(self, change):
        """This is an observe method that gets called automatically after each widget value change.
        This method translates the widget value change to internal value change and ensures the
        widget value and the actual value are synched. In other words, this method propagates
        user-invoked frontend value change to backend."""

        if change["old"] == {}:
            return  # frontend-triggered change not finalized yet

        if not self.has_options():
            raise NotImplementedError  # the variable has infinite domain

        # first check if valid selection
        new_widget_vals = change["owner"].value

        logger.info(
            "Frontend changing %s widget value to %s", self.name, new_widget_vals
        )

        for new_widget_val in new_widget_vals:
            new_val_validity_char = new_widget_val[0]
            new_val = new_widget_val[1:].strip()

            # if an invalid selection, display error message and set widget value to old value
            if new_val_validity_char == self._invalid_opt_char:
                err_msg = csp.retrieve_error_msg(self, new_val)
                logger.critical("ERROR: %s", err_msg)
                alert_error(err_msg)

                # set to old value:
                if self.value is None:
                    self._widget.value = self._widget_none_val
                else:
                    self._widget.value = tuple(
                        f"{self._valid_opt_char} {val}" for val in self.value.split(self._value_delimiter)
                    )
                return

        if self._widget.value == self._widget_none_val:
            self.value = None
        else:
            self.value = self._value_delimiter.join([val[1:].strip() for val in self._widget.value])
