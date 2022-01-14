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

    def __init__(self, name, ctx=None, never_unset=False, none_val=None):

        # Check if the variable has already been defined 
        if name in self.vdict:
            raise RuntimeError("Attempted to re-define ConfigVarStr instance {}.".format(name))
        
        # Instantiate the super class, i.e., a string constant based on SeqRef
        # (Below instantiation mimics String() definition in z3.py)
        if ctx==None:
            ctx = main_ctx()
        super().__init__(Z3_mk_const(ctx.ref(), to_symbol(name, ctx), StringSort(ctx).ast), ctx)

        # Instantiate members
        self.name = name
        self._never_unset = never_unset # once the widget value is set, don't unset it
        self._none_val = none_val
        self._has_options = False
        self._widget = DummyWidget()
        
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
        return self._widget.value

    @value.setter
    def value(self, val):
        logic.add_assignment(self, val)
        self._widget.value = val

    def is_none(self):
        return self._widget.value == self._none_val

    @property
    def options(self):
        return [option[1:].strip() for option in self._widget.options]

    @options.setter
    def options(self, opts):
        """Assigns the options displayed in the widget."""

        logger.debug("Updating the options of ConfigVarStr %s", self.name)
        self._has_options = True

        logic.set_variable_options(self, opts)

        # First, update to new options
        #todo self._unobserve_value_validity()
        self._widget.options = tuple('{} {}'.format(self.valid_opt_char, opt) for opt in opts)
        self._widget.value = self._none_val
        # Second, update options validities
        #todo self.update_options_validity()

        # If requested, pick the first valid value:
        #todo if self._never_unset is True and self._widget.value==self._none_val:
        #todo     self._set_value_to_first_valid_opt()

        #todo self._observe_value_validity()


    def has_options(self):
        return self._has_options
