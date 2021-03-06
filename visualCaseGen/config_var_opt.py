import logging

from visualCaseGen.config_var import ConfigVar
from visualCaseGen.dummy_widget import DummyWidget
from visualCaseGen.logic import logic, Layer
from visualCaseGen.OutHandler import handler as owh
from visualCaseGen.dev_utils import debug, RunError

logger = logging.getLogger("\t" + __name__.split(".")[-1])


class ConfigVarOpt(ConfigVar):

    # characters used in user interface to designate option validities
    _invalid_opt_char = chr(int("274C", base=16))
    _valid_opt_char = chr(int("2713", base=16))

    def __init__(
        self,
        name,
        widget_none_val=None,
        always_set=False,
        hide_invalid=False,
    ):
        """
        ConfigVarOpt constructor. A specification of ConfigVar base class for
        variables with a finite set of options (domain).

        Parameters
        ----------
        name : str
            Name of the variable. Must be unique.
        widget_none_val
            None value for the variable widget. Typically set to None, but for some widget types,
            e.g., those that can have multiple values, this must be set to ().
        always_set : bool
            If True and if the variable has options, then the first valid option is set as
            the value unless the user picks another value.
        hide_invalid:
            If True, the widget displays only the valid options.
        """

        super().__init__(name, widget_none_val)

        # Temporarily set private members options and value to None. These will be
        # updated with special property setter below.
        self._options = []
        self._options_spec = None

        # Initialize all other private members
        self._options_validities = {}
        self._error_messages = []
        self._widget_none_val = widget_none_val
        self._widget = DummyWidget(value=widget_none_val)
        self._always_set = always_set  # if a ConfigVar instance with options, make sure a value is always set
        self._hide_invalid = hide_invalid

    @property
    def always_set(self):
        """True if this ConfigVar instance should always be set to value."""
        return self._always_set

    @property
    def options(self):
        "The domain of the variable. If None, the variable has an infinite domain."
        return self._options

    @options.setter
    def options(self, new_options):
        logger.debug("Assigning the options of ConfigVar %s", self.name)
        assert isinstance(new_options, (list, set))
        logic.register_options(self, new_options)
        self._options = new_options
        self.update_options_validities(options_changed=True)
        logger.debug("Done assigning the options of ConfigVar %s", self.name)

    def assign_options_spec(self, options_spec):
        self._options_spec = options_spec

    def refresh_options(self, new_options=None, new_tooltips=None):
        """ This should only be called for variables whose options depend on other variables
        and are preset by the OptionsSetter mechanism."""

        if new_options is None:
            new_options, new_tooltips = self._options_spec()

        if new_options is not None:
            self.options = new_options
            if new_tooltips is not None:
                self.tooltips = new_tooltips
            self._widget.layout.visibility = "visible"
            self._widget.disabled = False

    @property
    def tooltips(self):
        """Tooltips, i.e., descriptions of options."""
        return self._widget.tooltips

    @tooltips.setter
    def tooltips(self, new_tooltips):

        if self._hide_invalid is True:
            self._widget.tooltips = [
                new_tooltips[i]
                for i, opt in enumerate(self._options)
                if self._options_validities[opt] is True
            ]
        else:
            self._widget.tooltips = new_tooltips

    def has_options(self):
        """Returns True if options have been assigned for this variable."""
        return len(self._options)>0

    def has_options_spec(self):
        """Returns True if an OptionsSpec object has been assigned for this variable."""
        return self._options_spec is not None

    def update_options_validities(self, new_validities=None, options_changed=False):
        """ This method updates options validities, and displayed widget options.
        If needed, value is also updated according to the options update."""

        old_widget_value = self._widget.value
        old_validities = self._options_validities

        if new_validities is None:
            if self.is_relational():
                self._options_validities = logic.get_options_validities(self)
            else:
                self._options_validities = {opt: True for opt in self._options}
        else:
            self._options_validities = new_validities

        if (not options_changed) and self._options_validities == old_validities:
            return  # no change in validities or options

        logger.debug(
            "Updated options validities of %s. Now updating widget.", self.name
        )

        if self._hide_invalid is True:
            self._widget.options = tuple(
                f"{self._valid_opt_char} {opt}"
                for opt in self._options
                if self._options_validities[opt]
            )
        else:
            self._widget.options = tuple(
                f"{self._valid_opt_char} {opt}"
                if self._options_validities[opt] is True
                else f"{self._invalid_opt_char} {opt}"
                for opt in self._options
            )

        if options_changed:
            # if options have changed, then the value must be updated.
            if self._always_set is True:
                self.value = None  # reset the value to ensure that _post_value_change() gets called
                # when options change, but the first valid option happens to be the
                # same as the old value (from a different list of options)
                self.value = self.get_first_valid_option()
            elif self.value is not None:
                self.value = None

        else:
            # Only the validities have changed, so no need to change the value.
            # But the widget value must be re-set to the old value since its options have changed
            # due to the validity change.
            if debug is True:
                try:
                    self._widget.value = old_widget_value
                except KeyError:
                    raise RunError(
                        f"Old widget value {old_widget_value} not an option anymore. Options: {self._widget.options}"
                    )
            else:
                self._widget.value = old_widget_value

        Layer.designate_affected_vars(self, designate_opt_children=options_changed)

    def get_first_valid_option(self):
        """Returns the first valid value from the list of options of this ConfigVar instance."""
        for opt in self._options:
            if self._options_validities[opt] is True:
                return opt
        return None
