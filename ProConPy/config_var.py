import logging
from traitlets import HasTraits, Any, default, validate

from ProConPy.out_handler import handler as owh
from ProConPy.csp_solver import csp
from ProConPy.options_spec import OptionsSpec
from ProConPy.dummy_widget import DummyWidget
from ProConPy.dev_utils import ProConPyError, DEBUG
from ProConPy.stage import Stage
from ProConPy.stage_rank import StageRank


logger = logging.getLogger(f"  {__name__.split('.')[-1]}")


class ConfigVar(HasTraits):
    """
    A class to represent configuration variable instances.

    Attributes
    ----------
    vdict : dict
        Dictionary of class instances where keys correspond to instance names.
        Should not be modified or overriden.
    value : Trait
        The value trait of each ConfigVar object.
    widget
        The frontend representation of the variable instance.
        The user can view and change the value of variable
        trough the widget.
    """

    # Dictionary of instances. This should not be modified or overriden in derived classes.
    vdict = {}

    # Trait
    value = Any()

    # If _lock is True, no more ConfigVar instances may be constructed.
    _lock = False

    # characters used in widgets to designate option validities.
    # (If the instance has a finite set of options.)
    _invalid_opt_char = chr(int("274C", base=16))
    _valid_opt_char = chr(int("200B", base=16))

    def __init__(self, name, default_value=None, widget_none_val=None, hide_invalid=False):
        """
        ConfigVar constructor.

        Parameters
        ----------
        name : str
            Name of the variable. Must be unique.
        default_value: callable|any
            Default value of the variable. If callable, the default value is the result of the callable.
            If configured so, the stage(s) that include this variable will use this value as the initial
            value when enabled and if the default value is valid.
        widget_none_val
            Null value for the variable widget. Typically set to None, but for some widget types,
            e.g., those that can have multiple values, this may be set to ().
        hide_invalid:
            If True, the widget displays only the valid options.
        """

        # Check if the variable has already been defined
        if name in ConfigVar.vdict:
            raise RuntimeError(f"Attempted to re-define ConfigVar instance {name}.")

        # Check if instantiation is allowed:
        if ConfigVar._lock is True:
            raise RuntimeError(
                f"Attempted to define a new ConfigVar {name}, but instantiation is not allowed anymore."
            )

        # Initialize name
        self.name = name

        # CSP solver instance that this variable is associated with
        assert (
            not csp.initialized
        ), f"Cannot introduce new variable {self.name} after CSP solver is initialized."

        # Set initial value to None. This means that derived class value traits must be initialized
        # with the following argument: allow_none=True
        self.value = None

        # Default value 
        self._default_value = default_value

        self._widget_none_val = widget_none_val
        self._widget = DummyWidget(value=widget_none_val)

        # The rank of a ConfigVar indicates the order of the Stage it belongs to. The lower 
        # the rank, the earlier the Stage is in the sequence of Stages and thus the higher 
        # the precedence of the ConfigVar in CSP solver. The rank is set when the stage the
        # ConfigVar belongs to is enabled. If a ConfigVar belongs to multiple stages, its rank
        # depends on which execution trace is being followed.
        self._rank = StageRank(None)

        # properties for instances that have finite options
        self._options = []
        self._options_validities = {}
        self._options_spec = None
        self._dependent_vars = (
            set()
        )  # ConfigVar instances whose options depend on the value of this instance
        self._related_vars = (
            set()
        )  # ConfigVar instances in the same relational constraints as this instance
        self._is_guard_var = False  # True if this variable appears in the guard of any Stage
        self._hide_invalid = hide_invalid

        # Finally, Observe value to call _post_value_change method after every value change.
        self.observe(self._post_value_change, names="value", type="change")

        # Record this newly created instance in the class member storing instances
        ConfigVar.vdict[name] = self
        logger.debug("ConfigVar %s created.", self.name)

    @classmethod
    def reboot(cls):
        """Reset the ConfigVar class to its initial state. This is useful for testing purposes
        and should not be used in production."""
        # Pop all items from the vdict. (Instead of assigning vdict to a new dict, we pop all items
        # so that we still use the same dict object and that cvars still points to current vdict.)
        while len(cls.vdict) > 0:
            cls.vdict.popitem()
        # reset the CSP solver as well
        csp.reboot()

    def _post_value_change(self, change):
        """If new value is valid, this method is called automatically right after self.value is set.
        However, note that this method doesn't get called if the new value is the same as old value.
        """

        new_val = change["new"]

        logger.debug("Post value change %s=%s", self.name, new_val)

        # update displayed widget values:
        self._update_widget_value()

        # register the assignment with the CSP solver
        csp.register_assignment(self, new_val)

    @classmethod
    def exists(cls, varname):
        """Check if a variable name is already defined.

        Parameters
        ----------
        varname : str
            Variable name to be checked
        """
        return varname in cls.vdict

    @classmethod
    def lock(cls):
        """After all ConfigVar instances are initialized, this class method must be called to prevent
        any additional ConfigVar declarations and to allow the CSP Solver module to determine interdepencies.
        """

        # Make sure some variables are instantiated.
        if len(ConfigVar.vdict) == 0:
            raise ProConPyError("No variables defined yet, so cannot lock ConfigVar")

        # Lock in the ConfigVar instances before determining the interdependencies
        ConfigVar._lock = True

    @default("value")
    def _default_value(self):
        """The default value of all ConfigVar instances are None."""
        return None

    @property
    def widget_none_val(self):
        """None value for the widget of this ConfigVar."""
        return self._widget_none_val

    @property
    def description(self):
        """Description of the variable to be displayed in widget."""
        return self._widget.description

    def has_options(self):
        """Returns True if options have been assigned for this variable."""
        return len(self._options) > 0

    def has_dependent_vars(self):
        """Returns True if there are dependent variables, i.e., variables whose
        options depend on the value of this variable."""
        return len(self._dependent_vars) > 0

    def has_related_vars(self):
        """Returns True if there are related variables, i.e, variables that are
        involved in the same relational constraints as this variable."""
        return len(self._related_vars) > 0

    @property
    def rank(self):
        """The rank of the variable. If None, the stage(s) the variable belongs to hasn't been enabled yet."""
        return self._rank
    
    @rank.setter
    def rank(self, new_rank):
        """Set the rank of the variable. This method is called by the Stage class when the stage is enabled."""
        assert isinstance(new_rank, StageRank), "new_rank must be a StageRank"
        assert new_rank.is_none() or self._rank.is_none() or new_rank == self._rank, \
            "Cannot change the rank of a ConfigVar before resetting it."
        self._rank = new_rank

    @property
    def is_guard_var(self):
        """Returns True if this variable appears in the guard of any Stage."""
        return self._is_guard_var
    
    @is_guard_var.setter
    def is_guard_var(self, value):
        if self._is_guard_var is True:
            assert value is True, "Cannot change is_guard_var from True to False"
        self._is_guard_var = value
    
    @property
    def is_aux_var(self):
        """Returns True if this variable is an auxiliary variable of the current stage."""
        return Stage.active() is not None and Stage.active().rank == self._rank and self._widget.disabled is True

    @property
    def options(self):
        """The list of options of the variable. If empty, the variable has an infinite domain."""
        return self._options

    @options.setter
    def options(self, new_options):
        """Set variable options. In doing so, also register the options with the CSP solver
        and update options validities (which entail updating the widget options list as well).

        Parameters
        ----------
        new_options: list|set
            list of new options
        """

        logger.debug("Assigning a list of options for ConfigVar %s", self.name)
        assert isinstance(
            new_options, (list, set, tuple)
        ), f"Unexpected new_options type: {type(new_options)}"
        self._options = new_options
        csp.register_options(self, new_options)
        self.update_options_validities()

    @property
    def options_spec(self):
        """The options specification of the variable."""
        return self._options_spec

    @options_spec.setter
    def options_spec(self, new_options_spec):
        """Set the options specification of the variable. In doing so, also register the options with the CSP solver
        and update options validities (which entail updating the widget options list as well).

        Parameters
        ----------
        new_options_spec: OptionsSpec
            The new options specification
        """
        assert isinstance(
            new_options_spec, OptionsSpec
        ), "new_options_spec must be an OptionsSpec instance"
        assert all(
            isinstance(arg, ConfigVar) for arg in new_options_spec._args
        ), "all OptionsSpec args must be config_vars"
        self._options_spec = new_options_spec

        for arg in new_options_spec._args:
            arg._dependent_vars.add(self)

    def update_options_validities(self):
        """This method updates options validities, and displayed widget options.
        If needed, value is also updated according to the options update.

        Returns
        -------
        bool
            True if the validities have changed, False otherwise.
        """

        old_widget_value = self._widget.value
        old_validities = self._options_validities

        # First, update self._options_validities.
        self._options_validities = csp.get_options_validities(self)

        # check if options list have changed since the last time validities were updated
        options_changed = old_validities.keys() != self._options_validities.keys()
        validities_changed = options_changed or (
            old_validities != self._options_validities
        )

        # If no change has occurred, return.
        if not (options_changed or validities_changed):
            logger.debug(
                "ConfigVar %s options or validities unchanged. Not updating widget",
                self.name,
            )
            return  # neither the validities nor the options have changed, so return.
        elif options_changed:
            logger.debug("ConfigVar %s options changed. Updating widget", self.name)
        else:
            logger.debug("ConfigVar %s validities changed. Updating widget", self.name)

        # After updating the internal options validities, refresh widget options list.
        self._refresh_widget_options()

        # Finally, update the value if necessary.
        if options_changed:
            if self.value is not None:
                # reset the value to ensure that _post_value_change() gets called
                # when options change, but the first valid option happens to be the
                # same as the old value (from a different list of options)
                self.value = None

        else:  # options list not changed
            # Only the validities have changed, so no need to change the value.
            # But the widget value must be re-set to the old value since its options list have
            # changed due to the validity change.
            if DEBUG is True:
                try:
                    self._widget.value = old_widget_value
                except KeyError:
                    raise ProConPyError(
                        f"Old widget value {old_widget_value} not an option anymore. Options: {self._widget.options}"
                    )
            else:
                self._widget.value = old_widget_value

        return validities_changed

    def _refresh_widget_options(self):
        """Refresh the widget options list based on information in the current self._options_validities."""

        # Update the displayed options list
        if self._hide_invalid is True:
            self._widget.options = tuple(
                f"{self._valid_opt_char} {opt}"
                for opt in self._options
                if self._options_validities[opt]
            )
        else:
            self._widget.options = tuple(
                (
                    f"{self._valid_opt_char} {opt}"
                    if self._options_validities[opt] is True
                    else f"{self._invalid_opt_char} {opt}"
                )
                for opt in self._options
            )

        # If the (internal) value is None, make sure widget value is None too, because the above
        # widget options assignment might have set the widget value to the first value.
        if self.value is None:
            self.widget.value = self.widget_none_val

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

    def get_first_valid_option(self):
        """Returns the first valid value from the list of options of this ConfigVar instance."""
        for opt in self._options:
            if self._options_validities[opt] is True:
                return opt
        return None

    @property
    def default_value(self):
        """The default value of the variable."""
        if callable(self._default_value):
            return self._default_value()
        return self._default_value
    
    @default_value.setter
    def default_value(self, new_default_value):
        """Set the default value of the variable.
        
        Parameters
        ----------
        new_default_value: callable|any
            The new default value of the variable. 
            If callable, the default value is the result of the callable.
        """
        self._default_value = new_default_value

    @property
    def widget(self):
        """Returns a reference of the widget instance."""
        return self._widget

    @widget.setter
    def widget(self, new_widget):
        """The user can view and change the value of this variable through the (GUI) widget."""
        old_widget = self._widget
        self._widget = new_widget
        if self.has_options():
            self._widget.options = old_widget.options
            self._widget.tooltips = old_widget.tooltips
        self._widget.value = old_widget.value

        # unobserve old widget frontend
        old_widget.unobserve(
            self._process_frontend_value_change, names="_property_lock", type="change"
        )

        # observe new widget frontend
        self._widget.observe(
            self._process_frontend_value_change,
            names="_property_lock",  # instead of 'value', use '_property_lock' to capture frontend changes only
            type="change",
        )

    @validate("value")
    def _validate_value(self, proposal):
        """This method is called automatially to verify that the new value is valid.
        Note that this method is NOT called if the new value is None."""
        raise NotImplementedError(
            "This method must be implemented in the derived class"
        )

    def _update_widget_value(self):
        """This methods gets called by _post_value_change and other methods to update the
        displayed widget value whenever the internal value changes. In other words, this
        method propagates backend value change to frontend."""
        raise NotImplementedError(
            "This method must be implemented in the derived class"
        )

    def _process_frontend_value_change(self, change):
        """This is an observe method that gets called automatically after each widget value change.
        This method translates the widget value change to ConfigVar value change and ensures the
        widget value and the actual value are synched. In other words, this method propagates
        user-invoked frontend value change to backend."""
        raise NotImplementedError(
            "This method must be implemented in the derived class"
        )


# An alias for the ConfigVar instances dictionary
cvars = ConfigVar.vdict
