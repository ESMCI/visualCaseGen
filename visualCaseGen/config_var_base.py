import logging
from visualCaseGen.dummy_widget import DummyWidget
from visualCaseGen.logic import logic, Layer
from visualCaseGen.OutHandler import handler as owh

from z3 import SeqRef, main_ctx, Z3_mk_const, to_symbol, StringSort
from traitlets import HasTraits, Any, default, validate, List

logger = logging.getLogger('\t'+__name__.split('.')[-1])

class ConfigVarBase(SeqRef, HasTraits):

    # Dictionary of instances. This should not be modified or overriden in derived classes.
    vdict = {}

    # characters used in user interface to designate option validities
    invalid_opt_char = chr(int("274C",base=16))
    valid_opt_char = chr(int("2713",base=16))

    # Trait
    value = Any()

    # List of all ConfigVar assignments in chronological order. Used only for debugging purposes
    assignment_history = list()

    def __init__(self, name, value=None, options=None, tooltips=(), ctx=None, widget_none_val=None,
                    always_set=False, hide_invalid=False):

        # Check if the variable has already been defined
        if name in ConfigVarBase.vdict:
            raise RuntimeError("Attempted to re-define ConfigVarBase instance {}.".format(name))

        if ctx==None:
            ctx = main_ctx()

        # Instantiate the super class, i.e., a Z3 constant
        if isinstance(self.value, str):
            # Below instantiation mimics String() definition in z3.py
            super().__init__(Z3_mk_const(ctx.ref(), to_symbol(name, ctx), StringSort(ctx).ast), ctx)
        else:
            raise NotImplementedError

        # Initialize members
        self.name = name

        # Temporarily set private members options and value to None. These will be
        # updated with special property setter below.
        self._options = None
        self._options_setter = None

        # Initialize all other private members
        self._options_validities = {}
        self._error_messages = []
        self._widget_none_val = widget_none_val
        self._widget = DummyWidget(value=widget_none_val)
        self._widget.tooltips = tooltips

        self._always_set = always_set # if a ConfigVarBase instance with options, make sure a value is always set
        self._hide_invalid = hide_invalid

        # variable properties managed by the logic module
        self._layers = []
        self.related_vars = set() # set of other variables sharing relational assertions with this var.
        self.child_vars_opt = set() # set of variables whose options are to be updated when the value of self changes.
        self.child_vars_rlt = [] # set of other variables appearing consequents of preconditional relations that
                               # include self in antecedent.

        # Now call property setters of options and value
        if options is not None:
            self.options = options

        self.value = value

        HasTraits.observe(self, self._post_value_change, names='value', type='change')

        # Record this newly created instance in the class member storing instances
        ConfigVarBase.vdict[name] = self
        logger.debug("ConfigVarBase %s created.", self.name)

    def _post_value_change(self, change):
        """If new value is valid, this method is called automatically right after self.value is set."""

        new_val = change['new']

        # record the assignment in history list
        ConfigVarBase.assignment_history.append((self,self.value,))

        # update displayed widget values:
        self._update_widget_value()

        # register the assignment with the logic engine
        logic.register_assignment(self, new_val)
        Layer.designate_affected_vars(self)

        # traverse over the logic layers and refresh all variables designated as potentially affected
        logic.traverse_layers(self)

    @staticmethod
    def reset():
        ConfigVarBase.vdict = dict()
        ConfigVarBase.assignment_history = list()
        logic.reset()

    @staticmethod
    def exists(varname):
        """Check if a variable is already defined."""
        return varname in ConfigVarBase.vdict

    @classmethod
    def determine_interdependencies(cls, relational_assertions_setter, options_setters):
        logic.register_interdependencies(
            relational_assertions_setter,
            options_setters,
            cls.vdict
        )

    @default('value')
    def _default_value(self):
        return None

    @property
    def widget_none_val(self):
        return self._widget_none_val

    def is_none(self):
        return self.value is None

    @property
    def major_layer(self):
        """Return the layer that this variable belongs to."""
        if len(self._layers) == 0:
            return logic.layers[0]
        else:
            return self._layers[0]

    @property
    def layers(self):
        """Return all layers that this variable appears in."""
        if len(self._layers) == 0:
            return [logic.layers[0]]
        else:
            return self._layers

    def add_layer(self, new_layer):
        if len(self._layers) > 0:
            if new_layer.idx <= self._layers[0].idx:
                raise RuntimeError("Cannot add a secondary chg layer that has higher priority than major layer for var {}"\
                    .format(var.name))
            if new_layer.idx in self._layers:
                raise RuntimeError("Trying to add a layer that is already added to var {}".format(var.name))
        self._layers.append(new_layer)

    @property
    def options(self):
        return self._options

    @options.setter
    def options(self, new_options):
        logger.debug("Assigning the options of ConfigVarBase %s", self.name)
        assert isinstance(new_options, (list,set))
        logic.register_options(self, new_options)
        self._options = new_options
        self.update_options_validities(options_changed=True)
        logger.debug("Done assigning the options of ConfigVarBase %s", self.name)

    def assign_options_setter(self, options_setter, tooltips_setter=None):
        self._options_setter = options_setter

    def run_options_setter(self):
        """ This should only be called for variables whose options depend on other variables
        and are preset by the OptionsSetter mechanism."""

        new_options, new_tooltips = self._options_setter()

        if new_options is not None:
            self.options = new_options
            if new_tooltips is not None:
                self.tooltips = new_tooltips
            self._widget.layout.visibility = 'visible'
            self._widget.disabled = False
        else:
            if self.options is not None:
                raise RuntimeError("Attempted to nullify options list of {}".format(var.name))

    @property
    def tooltips(self):
        return self._widget.tooltips

    @tooltips.setter
    def tooltips(self, new_tooltips):

        if self._hide_invalid is True:
            self._widget.tooltips = [new_tooltips[i] for i, opt in enumerate(self._options) \
                if self._options_validities[opt] is True]
        else:
            self._widget.tooltips = new_tooltips

    def has_options_setter(self):
        """Returns True if an options_setter function has been assigned for this variable."""
        return self._options_setter is not None

    def has_options(self):
        """Returns True if options have been assigned for this variable."""
        return self._options is not None

    def update_options_validities(self, new_validities=None, options_changed=False):
        """ This method updates options validities, and displayed widget options.
        If needed, value is also updated according to the options update."""

        old_widget_value = self._widget.value
        old_validities = self._options_validities

        if new_validities is None:
            self._options_validities = logic.get_options_validities(self)
        else:
            self._options_validities = new_validities

        if (not options_changed) and self._options_validities == old_validities:
            return # no change in validities or options

        logger.debug("Updated options validities of %s. Now updating widget.", self.name)

        if self._hide_invalid is True:
            self._widget.options = tuple(
                '{} {}'.format(self.valid_opt_char, opt) for opt in self._options \
                if self._options_validities[opt])
        else:
            self._widget.options = tuple(
                '{} {}'.format(self.valid_opt_char, opt) if self._options_validities[opt] is True \
                else '{} {}'.format(self.invalid_opt_char, opt) for opt in self._options)

        if options_changed:
            # if options have changed, then the value must be updated.
            if self._always_set is True:
                self.value = self._get_first_valid_option()
            elif self.value is not None:
                self.value = None

        else:
            # Only the validities have changed, so no need to change the value.
            # But the widget value must be re-set to the old value since its options have changed
            # due to the validity change.
            self._widget.value = old_widget_value

        Layer.designate_affected_vars(self, designate_opt_children=options_changed)

    def _get_first_valid_option(self):
        """Returns the first valid value from the list of options of this ConfigVar instance."""
        for opt in self._options:
            if self._options_validities[opt] == True:
                return opt
        return None


    @property
    def widget(self):
        raise RuntimeError("Cannot access widget property from outside the ConfigVar class")

    @widget.setter
    def widget(self, new_widget):
        old_widget = self._widget
        self._widget = new_widget
        if self.has_options():
            self._widget.options = old_widget.options
        self._widget.value = old_widget.value
        self._widget.tooltips = old_widget.tooltips

        # unobserve old widget frontend
        old_widget.unobserve(
            self._process_frontend_value_change,
            names='_property_lock',
            type='change'
        )

        # observe new widget frontend
        self._widget.observe(
            self._process_frontend_value_change,
            names='_property_lock', # instead of 'value', use '_property_lock' to capture frontend changes only
            type='change'
        )

    def set_widget_properties(self, property_dict):
        assert isinstance(property_dict, dict)
        for key, val in property_dict.items():
            assert key != "options", "Must set widget options via .options setter"
            assert key != "value", "Must set widget value via .value setter"
            setattr(self._widget, key, val)

    @property
    def widget_style(self):
        return self._widget.style

    @widget_style.setter
    def widget_style(self, style):
        self._widget.style = style

    @property
    def widget_layout(self):
        return self._widget.layout

    @widget_layout.setter
    def widget_layout(self, layout):
        self._widget.layout = layout

    @property
    def description(self):
        return self._widget.description

    @validate('value')
    def _validate_value(self, proposal):
        raise NotImplementedError("This method must be implemented in the derived class")

    @owh.out.capture()
    def _process_frontend_value_change(self, change):
        raise NotImplementedError("This method must be implemented in the derived class")

    @owh.out.capture()
    def _update_widget_value(self):
        raise NotImplementedError("This method must be implemented in the derived class")
