import logging
from visualCaseGen.dummy_widget import DummyWidget
from visualCaseGen.logic import logic
from visualCaseGen.OutHandler import handler as owh

from z3 import SeqRef, main_ctx, Z3_mk_const, to_symbol, StringSort
from traitlets import HasTraits, Any, default, validate, List

logger = logging.getLogger(__name__)

class ConfigVarBase(SeqRef, HasTraits):
    
    # Dictionary of instances. This should not be modified or overriden in derived classes.
    vdict = {}
    
    # characters used in user interface to designate option validities
    invalid_opt_char = chr(int("274C",base=16))
    valid_opt_char = chr(int("2713",base=16))

    # Trait
    value = Any()

    def __init__(self, name, value=None, options=None, tooltips=(), ctx=None, always_set=False, widget_none_val=None):

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

        # Initialize all other private members
        self._options_validities = {}
        self._error_messages = []
        self._related_vars = set() # set of other variables sharing relational assertions with this var.
        self._always_set = always_set # if a ConfigVarBase instance with options, make sure a value is always set
        self._widget_none_val = widget_none_val
        self._widget = DummyWidget(value=widget_none_val)
        self._widget.tooltips = tooltips

        # Now call property setters of options and value
        if options is not None:
            self.options = options

        self.value = value

        # Record this newly created instance in the class member storing instances
        ConfigVarBase.vdict[name] = self
        logger.debug("ConfigVarBase %s created.", self.name)

    @staticmethod
    def reset():
        ConfigVarBase.vdict = dict()
        logic.reset()

    @staticmethod
    def exists(varname):
        """Check if a variable is already defined."""
        return varname in ConfigVarBase.vdict

    @classmethod
    def add_relational_assertions(cls, assertions_setter):
        logic.insert_relational_assertions(assertions_setter, cls.vdict)

    @default('value')
    def _default_value(self):
        return None

    @property
    def widget_none_val(self):
        return self._widget_none_val

    def is_none(self):
        return self.value is None

    @property
    def options(self):
        return self._options

    @options.setter
    def options(self, new_opts):
        logger.debug("Assigning the options of ConfigVarBase %s", self.name)
        assert isinstance(new_opts, (list,set))
        logic.add_options(self, new_opts)
        self._update_options(new_opts=new_opts)
    
    @property
    def tooltips(self):
        return self._widget.tooltips

    @tooltips.setter
    def tooltips(self, new_tooltips):
        self._widget.tooltips = new_tooltips

    def has_options(self):
        return self._options is not None

    def _update_options(self, new_validities=None, new_opts=None):
        """ This method updates options, validities, and displayed widget options.
        If needed, value is also updated according to the options update."""

        # check if validities are being updated only, while options remain the same
        validity_change_only = new_opts is None or new_opts == self._options
        old_widget_value = self._widget.value
        old_validities = self._options_validities

        if not validity_change_only:
            self._options = new_opts

        if new_validities is None:
            self._options_validities = logic.get_options_validities(self)
        else:
            self._options_validities = new_validities

        if validity_change_only and old_validities == self._options_validities:
            return # no change in options or validities
        
        self._widget.options = tuple(
            '{} {}'.format(self.valid_opt_char, opt) if self._options_validities[opt] \
            else '{} {}'.format(self.invalid_opt_char, opt) for opt in self._options)
        
        if validity_change_only:
            self._widget.value = old_widget_value 
        else:
           if self._always_set:
               self._set_to_first_valid_opt() 

    def _set_to_first_valid_opt(self):
        """ Set the value of the instance to the first option that is valid."""
        for opt in self._options:
            if self._options_validities[opt] == True:
                self.value = opt
                break

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
