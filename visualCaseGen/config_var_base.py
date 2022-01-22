import logging
from visualCaseGen.dummy_widget import DummyWidget
from visualCaseGen.OutHandler import handler as owh

from z3 import SeqRef, main_ctx, Z3_mk_const, to_symbol, StringSort
from z3 import And, Or, Implies, is_implies, is_not
from z3 import Solver, sat, unsat
from z3 import z3util

from traitlets import HasTraits, Any, default, validate, List

logger = logging.getLogger(__name__)

class Logic():
    """Container for logic data"""
    # assertions keeping track of variable assignments. key is varname, value is assignment assertion
    asrt_assignments = dict()
    # assertions for options lists of variables. key is varname, value is options assertion
    asrt_options = dict()
    # relational assertions. key is ASSERTION, value is ERRNAME.
    asrt_relationals = dict()
    # variables that appear in relational assertions
    relational_vars = set()
logic = Logic()

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
        logic.asrt_assignments = dict()
        logic.asrt_options = dict()
        logic.asrt_relationals = dict()
        logic.relational_vars = set()

    @staticmethod
    def exists(varname):
        """Check if a variable is already defined."""
        return varname in ConfigVarBase.vdict

    @classmethod
    def add_relational_assertions(cls, assertions_setter):
        new_assertions = assertions_setter(cls.vdict)

        # Check if any assertion has been provided multiple times.
        # If not, update the relational_assertions_dict to include new assertions (simplified).
        for asrt in new_assertions:
            if asrt in logic.asrt_relationals:
                raise ValueError("Versions of assertion encountered multiple times: {}".format(asrt))
        logic.asrt_relationals.update(new_assertions)

        # Update the set of relational variables
        for asrt in new_assertions:
            logic.relational_vars.update( {cls.vdict[var.sexpr()] for var in z3util.get_vars(asrt)} )

        # Check if newly added relational assertions are satisfiable:
        s = Solver()
        s.add(list(logic.asrt_assignments.values()))
        s.add(list(logic.asrt_options.values()))
        s.add(list(logic.asrt_relationals.keys()))
        if s.check() == unsat:
            raise RuntimeError("Relational assertions not satisfiable!")

    def _is_sat_assignment(self, value):
        """ This is to be called by register_assignment method only. It checks whether an
        assignment is satisfiable."""

        if self.has_options():
            if value not in self.options:
                err_msg = '{} not an option for {}'.format(value, self.name)
                return False, err_msg

        # now, check if the value satisfies all assertions

        # first add all assertions including the assignment being checked but excluding the relational
        # assignments because we will pop the relational assertions if the solver is unsat
        s = Solver()
        s.add(list(logic.asrt_assignments.values()))
        s.add(list(logic.asrt_options.values()))
        s.add(self==value)

        # now push and temporarily add relational assertions
        s.push()
        s.add(list(logic.asrt_relationals.keys()))

        if s.check() == unsat:
            s.pop()
            for asrt in logic.asrt_relationals:
                s.add(asrt)
                if s.check() == unsat:
                    err_msg = '{}={} violates assertion:"{}"'.format(self.name,value,logic.asrt_relationals[asrt])
                    return False, err_msg

        return True, ''


    def _register_assignment(self, value, check_sat=True):

        # first check if this is a null assignment, in which case remove assignment assertion
        # for the variable and return.
        if value is None:
            logic.asrt_assignments.pop(self.name, None)
            return

        # pop old assignment if exists:
        old_assignment = logic.asrt_assignments.pop(self.name, None)

        # check if assignment is satisfiable.
        proceed = True
        if check_sat:
            proceed, msg = self._is_sat_assignment(value)

        # add the assignment to the assignments dictionary
        if proceed == False:
            # reinsert old assignment and raise error
            if old_assignment is not None:
                logic.asrt_assignments[self.name] = old_assignment
            raise AssertionError(msg)
        else:
            logic.asrt_assignments[self.name] = self==value

    def _retrieve_error_msg(self, value):
        """Given a failing assignment, retrieves the error message associated with the relational assertion
        leading to unsat."""

        s = Solver()
        s.add([logic.asrt_assignments[varname] for varname in logic.asrt_assignments.keys() if varname != self.name])
        s.add(list(logic.asrt_options.values()))

        # first, confirm the assignment is unsat
        if s.check( And( And(list(logic.asrt_relationals.keys())), self==value )) == sat:
            raise RuntimeError("_retrieve_error_msg method called for a satisfiable assignment")
        
        for asrt in logic.asrt_relationals:
            s.add(asrt)
            if s.check(self==value) == unsat:
                return '{}={} violates assertion:"{}"'.format(self.name, value, logic.asrt_relationals[asrt])

        return '{}={} violates multiple assertions.'.format(self.name, value)


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
        logger.debug("Updating the options of ConfigVarBase %s", self.name)
        assert isinstance(new_opts, (list,set))
        logic.asrt_options[self.name] = Or([self==opt for opt in new_opts])
        self._update_options(new_opts=new_opts)
    
    @property
    def tooltips(self):
        return self._widget.tooltips

    @tooltips.setter
    def tooltips(self, new_tooltips):
        self._widget.tooltips = new_tooltips

    def has_options(self):
        return self._options is not None

    @staticmethod
    def _update_all_options_validities():
        """ When a variable value gets (re-)assigned, this method is called the refresh options validities of all
        other variables that may be affected."""
        
        s = Solver()
        s.add(list(logic.asrt_options.values()))
        s.add(list(logic.asrt_relationals.keys())) 

        for var in logic.relational_vars:
            if var.has_options():
                s.push()
                s.add([logic.asrt_assignments[varname] for varname in logic.asrt_assignments if varname != var.name ])
                checklist = [var==opt for opt in var.options]
                res = s.consequences([], checklist)
                assert res[0] == sat, "_update_all_options_validities called for an unsat assignment!"

                new_validities = {opt:True for opt in var.options}
                for implication in res[1]:
                    consequent = implication.arg(1)
                    if is_not(consequent):
                        invalid_val_str = consequent.arg(0).arg(1).as_string() #todo: generalize this for non-string vars
                        new_validities[invalid_val_str] = False
                if new_validities != var._options_validities:
                    var._update_options(new_validities=new_validities)
                s.pop()
        
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
            s = Solver()
            s.add(list(logic.asrt_options.values()))
            s.add(list(logic.asrt_relationals.keys()))
            s.add([logic.asrt_assignments[varname] for varname in logic.asrt_assignments.keys() if varname != self.name])
            self._options_validities = {opt: s.check(self==opt)==sat for opt in self._options}
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
