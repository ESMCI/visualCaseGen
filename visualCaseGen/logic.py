import logging
from visualCaseGen.OutHandler import handler as owh

from z3 import And, Or, Not, Implies, is_not
from z3 import Solver, sat, unsat
from z3 import z3util

import cProfile, pstats
profiler = cProfile.Profile()

logger = logging.getLogger(__name__)

class Logic():
    """Container for logic data"""
    # assertions keeping track of variable assignments. key is varname, value is assignment assertion
    asrt_assignments = dict()
    # assertions for options lists of variables. key is varname, value is options assertion
    asrt_options = dict()
    # relational assertions. key is ASSERTION, value is ERRNAME.
    asrt_relationals = dict()
    # all variables that appear in one or more relational assertions
    all_relational_vars = set()

    # A solver instance that includes options assertions only. This solver is reused within methods to
    # improve the performance.
    so = Solver()

    @classmethod
    def reset(cls):
        cls.asrt_assignments = dict()
        cls.asrt_options = dict()
        cls.asrt_relationals = dict()
        cls.all_relational_vars = set()
    
    @classmethod
    def insert_relational_assertions(cls, assertions_setter, vdict):
        new_assertions = assertions_setter(vdict)
        # Check if any assertion has been provided multiple times.
        # If not, update the relational_assertions_dict to include new assertions (simplified).
        for asrt in new_assertions:
            if asrt in cls.asrt_relationals:
                raise ValueError("Versions of assertion encountered multiple times: {}".format(asrt))
        cls.asrt_relationals.update(new_assertions)

        for asrt in new_assertions:
            related_vars = {vdict[var.sexpr()] for var in z3util.get_vars(asrt)}
            cls.all_relational_vars.update(related_vars)
            for var in related_vars:
                var._related_vars.update(related_vars - {var})

        s = Solver()
        s.add(list(cls.asrt_assignments.values()))
        s.add(list(cls.asrt_options.values()))
        s.add(list(cls.asrt_relationals.keys()))
        if s.check() == unsat:
            raise RuntimeError("Relational assertions not satisfiable!")

    @classmethod
    def add_options(cls, var, new_opts):
        cls.asrt_options[var.name] = Or([var==opt for opt in new_opts])
        cls.so = Solver()
        cls.so.add(list(cls.asrt_options.values()))

    @classmethod
    def add_assignment(cls, var, new_value, check_sat=True):

        status = True
        err_msg = ''

        # first, pop the old assignment
        old_assignment = cls.asrt_assignments.pop(var.name, None)

        # check if new new_value is sat. if so, register the new assignment
        if new_value is not None:

            if check_sat:
                if var.has_options():
                    if new_value not in var.options:
                        status = False
                        err_msg = '{} not an option for {}'.format(new_value, var.name)

                if status is True:
                    # now, check if the value satisfies all assertions

                    # first add all assertions including the assignment being checked but excluding the relational
                    # assignments because we will pop the relational assertions if the solver is unsat
                    so.push()
                    so.add(list(cls.asrt_assignments.values()))
                    so.add(var==new_value)

                    # now push and temporarily add relational assertions
                    so.push()
                    so.add(list(cls.asrt_relationals.keys()))

                    if so.check() == unsat:
                        so.pop()
                        for asrt in cls.asrt_relationals:
                            so.add(asrt)
                            if so.check() == unsat:
                                status = False
                                err_msg = '{}={} violates assertion:"{}"'.format(var.name,new_value,cls.asrt_relationals[asrt])
                                break
                    so.pop()

            if status is False:
                # reinsert old assignment and raise error
                if old_assignment is not None:
                    cls.asrt_assignments[var.name] = old_assignment
                raise AssertionError(err_msg)
            else:
                cls.asrt_assignments[var.name] = var==new_value
        
        cls._update_all_options_validities(var)

    @classmethod
    def get_options_validities(cls, var):
        cls.so.push()
        cls.so.add(list(cls.asrt_relationals.keys()))
        cls.so.add([cls.asrt_assignments[varname] for varname in cls.asrt_assignments.keys() if varname != var.name])
        new_validities = {opt: cls.so.check(var==opt)==sat for opt in var._options}
        cls.so.pop()
        return new_validities

    @classmethod
    def _update_all_options_validities(cls, invoker_var):
        """ When a variable value gets (re-)assigned, this method is called the refresh options validities of all
        other variables that may be affected."""
        logger.debug("Updating options validities of ALL relational variables")

        #def __eval_new_validities_consequences(var):
        #    """ This version of __eval_new_validities uses z3.consequences, which is more expensive than the 
        #    below version, __eval_new_validities, so use that instead. Maybe there is a more efficient
        #    way to utilize z3.consequences, so I am keeping it here for now.""" 
        #    cls.so.push()
        #    cls.so.add([cls.asrt_assignments[varname] for varname in cls.asrt_assignments if varname != var.name ])
        #    checklist = [var==opt for opt in var.options]
        #    res = cls.so.consequences([], checklist)
        #    assert res[0] == sat, "_update_all_options_validities called for an unsat assignment!"
        #    new_validities = {opt:True for opt in var.options}
        #    for implication in res[1]:
        #        consequent = implication.arg(1)
        #        if is_not(consequent):
        #            invalid_val_str = consequent.arg(0).arg(1).as_string() #todo: generalize this for non-string vars
        #            new_validities[invalid_val_str] = False
        #    cls.so.pop()
        #    return new_validities

        def __eval_new_validities(var):
            cls.so.push()
            cls.so.add([logic.asrt_assignments[varname] for varname in logic.asrt_assignments if varname != var.name ])
            new_validities = {opt: cls.so.check(var==opt)==sat for opt in var._options}
            cls.so.pop()
            return new_validities

        #profiler.enable()

        cls.so.push()
        cls.so.add(list(cls.asrt_relationals.keys())) 

        # (ivar==1) First, evaluate if (re-)assignment of self has made an options validities change in its related variables.
        # (ivar>1) Then, recursively check the related variables of related variables whose options validities have changed.
        affected_vars = [invoker_var]+list(invoker_var._related_vars)
        ivar = 1
        while len(affected_vars)>ivar:
            var = affected_vars[ivar]
            if var.has_options():
                new_validities = __eval_new_validities(var)
                if new_validities != var._options_validities:
                    var._update_options(new_validities=new_validities)
                    affected_vars += [var_other for var_other in var._related_vars if var_other not in affected_vars]
            ivar += 1
        cls.so.pop()

        #profiler.disable()

    @classmethod
    def retrieve_error_msg(cls, var, value):
        """Given a failing assignment, retrieves the error message associated with the relational assertion
        leading to unsat."""

        s = Solver()
        s.add([logic.asrt_assignments[varname] for varname in logic.asrt_assignments.keys() if varname != var.name])
        s.add(list(logic.asrt_options.values()))

        # first, confirm the assignment is unsat
        if s.check( And( And(list(logic.asrt_relationals.keys())), var==value )) == sat:
            raise RuntimeError("_retrieve_error_msg method called for a satisfiable assignment")
        
        for asrt in logic.asrt_relationals:
            s.add(asrt)
            if s.check(var==value) == unsat:
                return '{}={} violates assertion:"{}"'.format(var.name, value, logic.asrt_relationals[asrt])

        return '{}={} violates multiple assertions.'.format(var.name, value)

logic = Logic()