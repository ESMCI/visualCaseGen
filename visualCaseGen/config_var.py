import logging
from traitlets import HasTraits, Any, default, validate

from visualCaseGen.logic import logic, Layer
from visualCaseGen.OutHandler import handler as owh
from visualCaseGen.dev_utils import debug, RunError
from visualCaseGen.dummy_widget import DummyWidget

logger = logging.getLogger("\t" + __name__.split(".")[-1])


class ConfigVar(HasTraits):
    """
    A class to represent CESM configuration (xml) variables to be assigned by the user when creating an experiment.
    Examples include COMP_ATM, COMP_OCN_PHYS, COMP_ICE_OPTIONS, OCN_GRID, COMPSET, etc.

    Attributes
    ----------
    vdict : dict
        Dictionary of class instances where keys correspond to instance names. Should not be modified or overriden.
    value : Trait
        The value trait of each ConfigVar object.
    widget
        The frontend representation of the variable instance. The user can view and change the value of variable
        trough the widget.
    """

    # Dictionary of instances. This should not be modified or overriden in derived classes.
    vdict = {}

    # Trait
    value = Any()

    # If _lock is True, no more ConfigVar instances may be constructed.
    _lock = False

    # characters used in widgets to designate option validities (if the instance has a finite set of options)
    _invalid_opt_char = chr(int("274C", base=16))
    _valid_opt_char = chr(int("2713", base=16))

    def __init__(
        self, name, widget_none_val=None, always_set=False, hide_invalid=False
    ):
        """
        ConfigVar constructor.

        Parameters
        ----------
        name : str
            Name of the variable. Must be unique.
        widget_none_val
            Null value for the variable widget. Typically set to None, but for some widget types,
            e.g., those that can have multiple values, this may be set to ().
        always_set : bool
            If True and if the variable has finite list of options, then the first valid option is
            set as the value unless the user picks another value.
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

        # Set initial value to None. This means that derived class value traits must be initialized
        # with the following argument: allow_none=True
        self.value = None

        self._widget_none_val = widget_none_val
        self._widget = DummyWidget(value=widget_none_val)

        # variable properties managed by the logic module
        self._layers = []
        self.peer_vars_relational = (
            set()
        )  # set of variables sharing relational assertions with this var on same chg layer.
        self.parent_vars_relational = (
            set()
        )  # set of variables appearing in antecedent of When clauses that include self in consequent.
        self.child_vars_relational = (
            set()
        )  # set of variables appearing consequents of When clauses that include self in antecendet.
        self.child_vars_options = (
            set()
        )  # set of variables whose options are to be updated when the value of self changes.

        # properties for instances that have finite options
        self._options = []
        self._options_spec = None
        self._options_validities = {}
        self._always_set = always_set  # if the instance has finite set of options, make sure a value is always set
        self._hide_invalid = hide_invalid

        # Finally, Observe value to call _post_value_change method after every value change. 
        self.observe(self._post_value_change, names="value", type="change")

        # Record this newly created instance in the class member storing instances
        ConfigVar.vdict[name] = self
        logger.debug("ConfigVar %s created.", self.name)

    def _post_value_change(self, change):
        """If new value is valid, this method is called automatically right after self.value is set.
        However, note that this method doesn't get called if the new value is the same as old value."""

        new_val = change["new"]

        # update displayed widget values:
        self._update_widget_value()

        # register the assignment with the logic engine
        logic.register_assignment(self, new_val)
        Layer.designate_affected_vars(self)

        # traverse over the logic layers and refresh all variables designated as potentially affected
        logic.traverse_layers(self)

    @staticmethod
    def reset():
        """Resets the ConfigVar class."""
        ConfigVar.vdict.clear()
        ConfigVar._lock = False
        logic.reset()

    @staticmethod
    def exists(varname):
        """Check if a variable name is already defined.

        Parameters
        ----------
        varname : str
            Variable name to be checked
        """
        return varname in ConfigVar.vdict

    @classmethod
    def lock(cls):
        """After all ConfigVar instances are initialized, this class method must be called to prevent
        any additional ConfigVar declarations and to allow the logic module to determine interdepencies.
        """

        # Make sure some variables are instantiated.
        if len(ConfigVar.vdict) == 0:
            raise RunError("No variables defined yet, so cannot lock ConfigVar")

        # Lock in the ConfigVar instances before determining the interdependencies
        ConfigVar._lock = True

    @default("value")
    def _default_value(self):
        """ The default value of all ConfigVar instances are None. """
        return None

    @property
    def widget_none_val(self):
        """None value for the widget of this ConfigVar."""
        return self._widget_none_val

    @property
    def description(self):
        """Description of the variable to be displayed in widget."""
        return self._widget.description

    @property
    def major_layer(self):
        """Return the constraint hypergraph (chg) layer that this variable belongs to.
        A variable belongs to the layer with the highest priority (lowest idx) in its list of layers."""
        if len(self._layers) == 0:
            return logic.layers[0]
        else:
            return self._layers[0]

    @property
    def layers(self):
        """Return all constraint hypergraph (chg) layers that this variable appears in."""
        if len(self._layers) == 0:
            return [logic.layers[0]]
        else:
            return self._layers

    def add_layer(self, new_layer):
        """Add a constraint hypergraph (chg) layer to the list of layers. The layer the variable belongs to
        must always be added first.

        Parameters
        ----------
        new_layer : Layer
            The constraint hypergraph layer that this variable belongs to or appears in.
        """
        if len(self._layers) > 0:
            if new_layer.idx <= self._layers[0].idx:
                raise RuntimeError(
                    f"Cannot add a secondary chg layer that has higher priority than major layer for var {self.name}"
                )
            if new_layer.idx in self._layers:
                raise RuntimeError(
                    f"Trying to add a layer that is already added to var {self.name}"
                )
        self._layers.append(new_layer)

    def is_none(self):
        """Returns True if value is None"""
        return self.value is None

    def is_relational(self):
        """ Returns True if this variable appears in a relational assertion. If the variable appears only in
        antecedent(s) of When clauses but doesn't appear in any other relational assertions, then it is NOT
        deemed to be relational because its options validities do not depend on other variables."""
        return (
            len(self.peer_vars_relational) > 0 or len(self.parent_vars_relational) > 0
        )

    @property
    def always_set(self):
        """True if this ConfigVar instance should always be set to value."""
        return self._always_set

    def has_options(self):
        """Returns True if options have been assigned for this variable."""
        return len(self._options)>0

    @property
    def options(self):
        "The list of options of the variable. If None, the variable has an infinite domain."
        return self._options

    @options.setter
    def options(self, new_options):
        logger.debug("Assigning the finite list of options of ConfigVar %s", self.name)
        assert isinstance(new_options, (list, set))
        logic.register_options(self, new_options)
        self._options = new_options
        self.update_options_validities(options_changed=True)
        logger.debug("Done assigning the options of ConfigVar %s", self.name)

    def assign_options_spec(self, options_spec):
        self._options_spec = options_spec

    def has_options_spec(self):
        """Returns True if an OptionsSpec object has been assigned for this variable."""
        return self._options_spec is not None
    
    def has_finite_options_list(self):
        return self.has_options_spec() or self.has_options()

    def refresh_options(self, new_options=None, new_tooltips=None):
        """ This should only be called for variables whose options depend on other variables
        and are preset by the OptionsSetter mechanism."""

        if new_options is None:
            new_options, new_tooltips = self._options_spec()

        if new_options is not None:
            self.options = new_options
            if new_tooltips is not None:
                if not isinstance(new_tooltips[0],str):
                    new_tooltips = [str(nt) for nt in new_tooltips]
                self.tooltips = new_tooltips
            self._widget.layout.display = ""
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

        # If the value is None, make sure widget value is None too, because the above
        # widget options assignment might have set the widget value to the first value.
        if self.value is None:
            self.widget.value = self.widget_none_val

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

    @owh.out.capture()
    def _update_widget_value(self):
        """This methods gets called by _post_value_change and other methods to update the
        displayed widget value whenever the internal value changes. In other words, this
        method propagates backend value change to frontend."""
        raise NotImplementedError(
            "This method must be implemented in the derived class"
        )

    @owh.out.capture()
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
