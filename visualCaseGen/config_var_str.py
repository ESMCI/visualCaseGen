import logging
from visualCaseGen.dummy_widget import DummyWidget
from visualCaseGen.OutHandler import handler as owh
import visualCaseGen.logic_engine as logic
from z3 import SeqRef, main_ctx, Z3_mk_const, to_symbol, StringSort
from traitlets import HasTraits, Any, default, validate

logger = logging.getLogger(__name__)

class ConfigVarStr(SeqRef, HasTraits):
    
    # dictionary of instances
    vdict = {}
    
    # characters used in user interface to designate option validities
    invalid_opt_char = chr(int("274C",base=16))
    valid_opt_char = chr(int("2713",base=16))

    # trait
    value = Any()

    def __init__(self, name, value=None, options=None, tooltips=(), ctx=None, always_set=False, none_val=None):

        # Check if the variable has already been defined 
        if name in self.vdict:
            raise RuntimeError("Attempted to re-define ConfigVarStr instance {}.".format(name))
        
        # Instantiate the super class, i.e., a string constant based on SeqRef
        # (Below instantiation mimics String() definition in z3.py)
        if ctx==None:
            ctx = main_ctx()
        super().__init__(Z3_mk_const(ctx.ref(), to_symbol(name, ctx), StringSort(ctx).ast), ctx)

        # Initialize members
        self.name = name

        # Temporarily set private members options and value to None. These will be 
        # updated with special property setter below.
        self._options = None
        self._value = None

        # Initialize all other private members
        self._related_vars = set() # set of variables to be informed when a value change occurs
        self._options_validities = {}
        self._error_messages = []
        self._none_val = none_val
        self._always_set = always_set # if a ConfigVarStr instance with options, make sure a value is always set
        self._widget = DummyWidget()
        self._widget.tooltips = tooltips

        # Now call property setters of options and value
        if options is not None:
            self.options = options
        self.value = value

        # Record this newly created instance in the class member storing instances
        self.vdict[name] = self
        logger.debug("ConfigVarStr %s created.", self.name)

    @classmethod
    def reset(cls):
        cls.vdict = {}

    @classmethod
    def exists(cls, varname):
        """Check if a variable is already defined."""
        return varname in cls.vdict

    @default('value')
    def _default_value(self):
        return self._none_val

    @validate('value')
    def _validate_value(self, proposal):
        new_val = proposal['value']

        if new_val == self._none_val:
            logic.set_null(self)
        elif self.has_options() and new_val in self._options:
            if self._options_validities[new_val] == True:
                logic.add_assignment(self, new_val, check_sat=False)
            else:
                raise AssertionError(self._error_messages[new_val])
        else:
            logic.add_assignment(self, new_val, check_sat=True)

        # update widget value
        self._widget.value = new_val if new_val==self._none_val else self.valid_opt_char+' '+new_val 

        # update internal value
        self._value = new_val

        # finally, inform all related vars about this value change by calling their _update_options
        # this will update options validities.
        for var in self._related_vars:
            if var.has_options():
                var._update_options()
        
        return new_val

    @property
    def none_val(self):
        return self._none_val

    def is_none(self):
        return self.value == self._none_val

    @property
    def options(self):
        return self._options

    @options.setter
    def options(self, new_opts):
        logger.debug("Updating the options of ConfigVarStr %s", self.name)
        assert isinstance(new_opts, (list,set))
        logic.set_variable_options(self, new_opts)
        self._update_options(new_opts)
    
    @property
    def tooltips(self):
        return self._widget.tooltips

    @tooltips.setter
    def tooltips(self, new_tooltips):
        self._widget.tooltips = new_tooltips

    def has_options(self):
        return self._options is not None

    def add_related_vars(self, new_vars):
        self._related_vars.update(new_vars)

    def _update_options(self, new_opts=None):
        """ This method updates options, validities, and displayed widget options.
        If needed, value is also updated according to the options update."""

        # check if validities are being updated only, while options remain the same
        validity_change_only = new_opts is None or new_opts == self._options
        old_widget_value = self._widget.value
        old_validities = self._options_validities

        if not validity_change_only:
            self._options = new_opts

        self._options_validities, self._error_messages = logic.get_options_validities(self, self._options)

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
    
    @owh.out.capture()
    def _process_frontend_value_change(self, change):
        if change['old'] == {}:
            return # frontend-triggered change not finalized yet
        
        # first check if valid selection
        new_widget_val = change['owner'].value 
        new_val_validity_char = new_widget_val[0] 
        new_val = new_widget_val[1:].strip()

        # if an invalid selection, display error message and set widget value to old value
        if self.has_options() and new_val_validity_char == self.invalid_opt_char:
            logger.critical("ERROR: %s", self._error_messages[new_val])
            from IPython.display import display, HTML
            js = "<script>alert('ERROR: {}');</script>".format(
                self._error_messages[new_val]
            )
            display(HTML(js))
            
            # set to old value:
            self._widget.value = self._value if self._value==self._none_val else '{} {}'\
                .format(self.valid_opt_char, self._value)
            return
        else:
            self.value = new_val