import logging
from visualCaseGen.dummy_widget import DummyWidget
import visualCaseGen.logic_engine as logic
from z3 import SeqRef, main_ctx, Z3_mk_const, to_symbol, StringSort

logger = logging.getLogger(__name__)

class ConfigVarStr(SeqRef):
    
    # dictionary of instances
    vdict = {}
    
    # characters used in user interface to designate option validities
    invalid_opt_char = chr(int("274C",base=16))
    valid_opt_char = chr(int("2713",base=16))

    def __init__(self, name, value=None, options=None, ctx=None, never_unset=False, none_val=None):

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
        self._none_val = none_val
        self._value = value or self._none_val
        self._options = options
        self._never_unset = never_unset # once the widget value is set, don't unset it
        self._widget = DummyWidget()
        self._related_vars = set() # set of variables to be informed when a value change occurs
        self._options_validities = {}
        self._error_messages = []

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

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_val):

        if new_val == self._none_val:
            logic.set_null(self)
        elif self.has_options() and new_val in self.options:
            if self._options_validities[new_val] == True:
                logic.add_assignment(self, new_val, check_sat=False)
            else:
                raise AssertionError(self._error_messages[new_val])
        else:
            logic.add_assignment(self, new_val, check_sat=True)

        if new_val == self._none_val:
            self._widget.value = self._none_val
        else:
            self._widget.value = self.valid_opt_char+' '+new_val

        self._value = new_val

        # finally, inform all related vars about this value change by calling their _update_option_validities
        for var in self._related_vars:
            if var.has_options():
                var._update_option_validities(var.options)

    def is_none(self):
        return self.value == self._none_val

    @property
    def options(self):
        return self._options

    @options.setter
    def options(self, new_opts):
        logger.debug("Updating the options of ConfigVarStr %s", self.name)
        assert isinstance(new_opts, (list,set))
        ##todo: validate new options here
        logic.set_variable_options(self, new_opts)
        self._update_option_validities(new_opts)
        self._widget.options = tuple(
            '{} {}'.format(self.valid_opt_char, opt) if self._options_validities[opt] \
            else '{} {}'.format(self.invalid_opt_char, opt) for opt in new_opts)
        self.value = self._none_val
        self._options = new_opts

    def has_options(self):
        return self.options != None

    def add_related_vars(self, new_vars):
        self._related_vars.update(new_vars)

    def _update_option_validities(self, opts):
        self._options_validities, self._error_messages = logic.get_options_validities(self, opts)
