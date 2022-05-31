import logging
from z3 import SeqRef, main_ctx, Z3_mk_const, to_symbol, StringSort
from traitlets import HasTraits, Any, default, validate

from visualCaseGen.logic import logic, Layer
from visualCaseGen.OutHandler import handler as owh
from visualCaseGen.dev_utils import RunError

logger = logging.getLogger("\t" + __name__.split(".")[-1])


class ConfigVar(SeqRef, HasTraits):
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

    def __init__(
        self, name, widget_none_val=None,
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
        """

        # Check if the variable has already been defined
        if name in ConfigVar.vdict:
            raise RuntimeError(f"Attempted to re-define ConfigVar instance {name}.")

        # Check if instantiation is allowed:
        if ConfigVar._lock is True:
            raise RuntimeError(
                f"Attempted to define a new ConfigVar {name}, but instantiation is not allowed anymore."
            )

        # z3 context
        ctx = main_ctx()

        # Instantiate the super class, i.e., a Z3 constant
        if isinstance(self.value, str):
            # Below instantiation mimics String() definition in z3.py
            super().__init__(
                Z3_mk_const(ctx.ref(), to_symbol(name, ctx), StringSort(ctx).ast), ctx
            )
        else:
            raise NotImplementedError

        # Initialize name
        self.name = name

        # Set initial value to None. This means that derived class value traits must be initialized
        # with the following argument: allow_none=True
        self.value = None

        self._widget = None

        # Null value of the widget. Typically is None, but may be an emptly tuple too.
        self._widget_none_val = widget_none_val

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

    def has_options(self):
        """The base ConfigVar class doesn't have options( i.e., finite domains), but the derived class may."""
        return False

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
