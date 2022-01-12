from z3 import *

class LogicEngine():

    # solver that encapsulate all asertions. Checks must be always be made over this solver
    s_universal = Solver()
    # solver that encapsulates assignments
    s_assignments = Solver()
    # solver that encapsulates assertions due to options list of each variable
    s_options_list = Solver()
    # solver that encapsulates relational assertions
    s_relational = Solver() 

    relational_assertions_dict = {}
    vars = {}

    def __init__(self):
        pass

    @classmethod
    def add_variable(cls, varname):
        """This method is to be called by all ConfigVar constructor."""
        LogicEngine.vars[varname] = String(varname)

    @classmethod
    def set_variable_options(cls, varname, options):
        """This method is to be called by ConfigVar instance when its options are assigned."""
        cls.s_options_list.add(
            Or([cls.vars[varname]==opt for opt in options])
        )
        cls.s_universal.add(
            Or([cls.vars[varname]==opt for opt in options])
        )
    
    @classmethod
    def add_relational_assertions(cls, assertions_setter):
        new_assertions = assertions_setter(cls.vars)

        # Check if any assertion has been provided multiple times.
        # If not, update the relational_assertions_dict to include new assertions (simplified). 
        for asrt in new_assertions:
            if asrt in cls.relational_assertions_dict: 
                raise ValueError("Versions of assertion encountered multiple times: {}".format(asrt))
        cls.relational_assertions_dict.update(new_assertions)

        # Update the solvers
        cls.s_relational.add([asrt for asrt in new_assertions])
        cls.s_universal.add([asrt for asrt in new_assertions])

        # Check if global solver is sat
        if cls.s_universal.check() == unsat:
            raise RuntimeError("Relational assertions not satisfiable!") 
        #print(cls.s_universal.model())

    @classmethod
    def _check_assignment(cls, varname, value):
        """ This is to be called by add_assignment method only. It checks whether an
        assignment is satisfiable."""

        var = cls.vars[varname]

        if cls.s_universal.check(var==value) == unsat:

            # first, check if unsat is due to non-existent option
            if cls.s_options_list.check(var==value) == unsat:
                raise ValueError("Invalid value for {} = {}".format(varname, value))

            # next, check if failure is due to a relational constraint
            s_temp = Solver()
            s_temp.add(var==value)
            s_temp.add(cls.s_options_list.assertions()) # add all options constraints
            s_temp.add(cls.s_assignments.assertions()) # add all previous assignments
            for asrt in cls.s_relational.assertions():
                s_temp.add(asrt)
                if s_temp.check() == unsat:
                    raise AssertionError('{}={} violates assertion:"{}"'.
                        format(varname,value,cls.relational_assertions_dict[asrt]))

        return True

    @classmethod
    def add_assignment(cls, varname, value):
        """ Adds an assignment to the logic solver. To be called by ConfigVar value setters only."""
        cls._check_assignment(varname, value)
        var = cls.vars[varname]
        cls.s_universal.add(var==value)
        cls.s_assignments.add(var==value)
        
