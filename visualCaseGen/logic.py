import logging
from visualCaseGen.OutHandler import handler as owh

from z3 import And, Or, Not, Implies, is_not
from z3 import Solver, sat, unsat
from z3 import BoolRef, Int
from z3 import z3util
from z3 import If as z3_If
import networkx as nx

import cProfile, pstats
profiler = cProfile.Profile()

logger = logging.getLogger('\t\t'+__name__.split('.')[-1])

class Logic():
    """Container for logic data"""
    # assertions keeping track of variable assignments. key is var, value is assignment assertion
    asrt_assignments = dict()
    # assertions for options lists of variables. key is var, value is options assertion
    asrt_options = dict()
    # relational assertions that are to hold all times. key is ASSERTION, value is ERRNAME.
    asrt_unconditional_relationals = dict()
    # dictionary of all conditional relational assertions
    asrt_conditional_relationals= dict()
    # dictionary of hierarchy levels (of type non-positive integer) for variables.
    hierarchy_levels= dict()

    child_vars = dict()

    # A solver instance that includes options assertions only. This solver is reused within methods to
    # improve the performance.
    so = Solver()

    @classmethod
    def reset(cls):
        cls.asrt_assignments = dict()
        cls.asrt_options = dict()
        cls.asrt_unconditional_relationals = dict()
        cls.asrt_conditional_relationals = dict()
        cls.hierarchy_levels = dict()
        cls.child_vars = dict()
        cls.so.reset()

    @classmethod
    def get_hierarchy_level(cls, var):
        return cls.hierarchy_levels.get(var, 0)

    @classmethod
    def n_hierarchy_levels(cls):
        return len(set(cls.hierarchy_levels.values()))

    @classmethod
    def insert_relational_assertions(cls, assertions_setter, vdict):

        if len(cls.asrt_unconditional_relationals)>0 or len(cls.asrt_conditional_relationals)>0:
            raise RuntimeError("Attempted to call insert_relational_assertions method multiple times.")

        # Obtain all new assertions including conditionals and unconditionals
        new_assertions = assertions_setter(vdict)

        cls._determine_hierarchy_levels(new_assertions, vdict)
        cls._gen_constraint_hypergraph(new_assertions, vdict)
        cls._do_insert_relational_assertions(new_assertions, vdict)

    @classmethod
    def _determine_hierarchy_levels(cls, new_assertions, vdict):
        """Determines hierarchy levels of assertions and variables appearing in those assertions."""

        # hierarchy level solver:
        hl_solver = Solver()

        for asrt in new_assertions:
            # unconditional constraints
            if isinstance(asrt, BoolRef):

                asrt_vars = z3util.get_vars(asrt)
                for var in asrt_vars:
                    cls.hierarchy_levels[var] = Int("HierLev_{}".format(var))
                if len(asrt_vars)>1:
                    hl_var_0 = cls.hierarchy_levels[asrt_vars[0]]
                    for i in range(1,len(asrt_vars)):
                        hl_var_i = cls.hierarchy_levels[asrt_vars[i]]
                        hl_solver.add(hl_var_0 == hl_var_i)

            # conditional constraints
            elif isinstance(asrt, tuple) and len(asrt)==2 and isinstance(asrt[0], BoolRef) and isinstance(asrt[1], BoolRef):

                antecedent_vars = z3util.get_vars(asrt[0])
                consequent_vars = z3util.get_vars(asrt[1])

                for a_var in antecedent_vars:
                    cls.hierarchy_levels[a_var] = Int("HierLev_{}".format(a_var))
                    for c_var in consequent_vars:
                        cls.hierarchy_levels[c_var] = Int("HierLev_{}".format(c_var))
                        hl_solver.add(cls.hierarchy_levels[a_var] > cls.hierarchy_levels[c_var])
            
        if hl_solver.check() == unsat:
            raise RuntimeError("Error in relational variable hierarchy. Make sure to use conditional "\
                "relationals in a consistent manner. Conditional relationals dictate variable hierarchy "\
                "such that variables appearing in antecedent have higher hierarchies than those appearing "\
                "in consequent.")

        hl_model = hl_solver.model()

        # cast cls.hierarchy_levels values to integers:
        for var in cls.hierarchy_levels:
            cls.hierarchy_levels[var] = hl_model[cls.hierarchy_levels[var]].as_long()
        
        # normalize hierarchy levels:
        hl_vals = sorted(set(cls.hierarchy_levels.values()))
        n_hl_vals = len(hl_vals)
        normalization = {hl_vals[i]: i-n_hl_vals+1 for i in range(n_hl_vals)}
        for var in cls.hierarchy_levels:
            cls.hierarchy_levels[var] = normalization[cls.hierarchy_levels[var]]
        
        # finally, set assertion hierarchy levels:
        for asrt in new_assertions:
            # unconditional assertions
            if isinstance(asrt, BoolRef):
                asrt_vars = z3util.get_vars(asrt)
                cls.hierarchy_levels[asrt] = cls.get_hierarchy_level(asrt_vars[0]) 
            # conditional constraints
            elif isinstance(asrt, tuple) and len(asrt)==2 and isinstance(asrt[0], BoolRef) and isinstance(asrt[1], BoolRef):
                consequent_vars = z3util.get_vars(asrt[1])
                min_hl = min([cls.get_hierarchy_level(c_var) for c_var in consequent_vars])
                cls.hierarchy_levels[asrt] = min_hl 


    @classmethod
    def _gen_constraint_hypergraph(cls, new_assertions, vdict):

        cls.chg = nx.Graph()

        for asrt in new_assertions:

            # unconditional assertions
            if isinstance(asrt, BoolRef):

                asrt_vars = z3util.get_vars(asrt)
                hl = cls.get_hierarchy_level(asrt)

                # add variable nodes
                for var in asrt_vars:
                    if var not in cls.chg:
                        cls.chg.add_node(var, hl=hl, hyperedge=False)

                # add unconditional assertion node
                cls.chg.add_node(asrt, hl=hl, hyperedge=True, conditional=False)

                # add edge from variable to asrt
                for var in asrt_vars:
                    cls.chg.add_edge(var, asrt)

            # conditional constraints
            elif isinstance(asrt, tuple) and len(asrt)==2 and isinstance(asrt[0], BoolRef) and isinstance(asrt[1], BoolRef):

                antecedent_vars = z3util.get_vars(asrt[0])
                consequent_vars = z3util.get_vars(asrt[1])

                # add conditional assertion node
                hl = cls.get_hierarchy_level(asrt)
                cls.chg.add_node(asrt, hl=hl, hyperedge=True, conditional=True)

                for a_var in antecedent_vars:
                    # add antecedent variables nodes (if not added already)
                    if a_var not in cls.chg:
                        hl = cls.get_hierarchy_level(a_var)
                        cls.chg.add_node(a_var, hl=hl, hyperedge=False)
                    # add edge from var to asrt
                    cls.chg.add_edge(a_var, asrt) # higher var to assertion

                for c_var in consequent_vars:
                    # add consequent variables's node (if not added already)
                    if c_var not in cls.chg:
                        hl = cls.get_hierarchy_level(c_var)
                        cls.chg.add_node(c_var, hl=hl, hyperedge=False)
                    # add edge from var to asrt
                    cls.chg.add_edge(c_var, asrt) # lower var to assertion


    @classmethod
    def _do_insert_relational_assertions(cls, new_assertions, vdict):
        # Update relational assertions dictionaries of the Logic class:
        for asrt in new_assertions:

            # First, process the unconditional assertions
            if isinstance(asrt, BoolRef):

                # add the new unconditional assertion
                if asrt in cls.asrt_unconditional_relationals:
                    raise ValueError("Versions of assertion encountered multiple times: {}".format(asrt))
                cls.asrt_unconditional_relationals[asrt] = new_assertions[asrt]

                # update related_vars properties of all variables appearing in newly added relational assertion 
                related_vars = {vdict[var.sexpr()] for var in z3util.get_vars(asrt)}
                for var in related_vars:
                    var._related_vars.update(related_vars - {var})

            # Now, process the conditional assertions
            elif isinstance(asrt, tuple) and len(asrt)==2 and isinstance(asrt[0], BoolRef) and isinstance(asrt[1], BoolRef):
                antecedent = asrt[0]
                consequent = asrt[1]
                antecedent_vars =  z3util.get_vars(antecedent)
                consequent_vars =  z3util.get_vars(consequent)

                # add the new conditional assertion
                cls.asrt_conditional_relationals[asrt] = new_assertions[asrt]

                for a_var in antecedent_vars:
                    if a_var not in cls.child_vars:
                        cls.child_vars[a_var] = set()
                    cls.child_vars[a_var].update([vdict[var.sexpr()] for var in consequent_vars])

            else:
                raise RuntimeError("Unsupported assertion encountered: %s" % asrt)

        # Check if newly added relational assertions are sat:
        s = Solver()
        cls._apply_assignment_assertions(s)
        cls._apply_options_assertions(s)
        cls._apply_relational_assertions(s)
        if s.check() == unsat:
            raise RuntimeError("Relational assertions not satisfiable!")

    @classmethod
    def _apply_assignment_assertions(cls, solver, exclude_varname=None, hl=None):
        """ Adds all current assignment assertions to a given solver instance.
        The assignment of a variable may be excluded by providing its name to the optional exclude_varname option. """

        if hl is None:
            if exclude_varname is None:
                solver.add(list(cls.asrt_assignments.values()))
            else:
                solver.add([cls.asrt_assignments[var] for var in cls.asrt_assignments if var.name != exclude_varname])
        else: # hl is NOT None
            if exclude_varname is None:
                solver.add([cls.asrt_assignments[var] for var in cls.asrt_assignments if cls.get_hierarchy_level(var) >= hl])
            else:
                solver.add([cls.asrt_assignments[var] for var in cls.asrt_assignments if var.name != exclude_varname and cls.get_hierarchy_level(var) >= hl])

    @classmethod
    def _apply_options_assertions(cls, solver, hl=None):
        """ Adds all of the current options assertions to a given solver instance."""
        if hl is None:
            solver.add(list(cls.asrt_options.values()))
        else:
            solver.add([cls.asrt_options[var] for var in cls.asrt_options if cls.get_hierarchy_level(var) >= hl])

    @classmethod
    def _apply_relational_assertions(cls, solver, assert_and_track=False, hl=None):
        """ Adds all of the relational assertions to a given solver instance """

        # solver for evaluations the antecedents of conditional relations
        #s_ = Solver()
        #cls._apply_assignment_assertions(s_)
        #cls._apply_options_assertions(s_)

        if assert_and_track is True:
            for asrt in cls.asrt_unconditional_relationals:
                solver.assert_and_track(asrt, cls.asrt_unconditional_relationals[asrt])
            #todo for antecedent, consequent in cls.asrt_conditional_relationals:
            #todo     if s_.check(Not(antecedent)) == unsat:
            #todo         solver.assert_and_track(consequent, cls.asrt_conditional_relationals[antecedent,consequent])
        else:
            solver.add(list(cls.asrt_unconditional_relationals))
            #todo for antecedent, consequent in cls.asrt_conditional_relationals:
            #todo     if s_.check(Not(antecedent)) == unsat:
            #todo         solver.add(consequent)

    @classmethod
    def add_options(cls, var, new_opts):
        cls.asrt_options[var] = Or([var==opt for opt in new_opts])
        cls.so.reset()
        cls._apply_options_assertions(cls.so)

    @classmethod
    def add_assignment(cls, var, new_value, check_sat=True):

        # first, pop the old assignment
        old_assignment = cls.asrt_assignments.pop(var, None)

        logger.debug("Adding %s=%s assignment to the Logic engine.", var.name, new_value)

        status = True
        err_msg = ''

        # check if new new_value is sat. if so, register the new assignment
        if new_value is not None:

            if check_sat:
                logger.debug("Checking whether %s=%s assignment is sat.", var.name, new_value)
                if var.has_options():
                    if new_value not in var.options:
                        status = False
                        err_msg = '{} not an option for {}'.format(new_value, var.name)

                if status is True:
                    # now, check if the value satisfies all assertions

                    # first add all assertions including the assignment being checked but excluding the relational
                    # assignments because we will pop the relational assertions if the solver is unsat
                    cls.so.push()
                    cls._apply_assignment_assertions(cls.so)
                    cls.so.add(var==new_value)
                    cls._apply_relational_assertions(cls.so)
                    _assignment_is_sat = cls.so.check() == sat
                    cls.so.pop()

                    if not _assignment_is_sat:
                        err_msg = cls.retrieve_error_msg(var, new_value)


            if status is False:
                # reinsert old assignment and raise error
                if old_assignment is not None:
                    cls.asrt_assignments[var] = old_assignment
                raise AssertionError(err_msg)
            else:
                cls.asrt_assignments[var] = var==new_value

        logger.debug("Done adding %s=%s assignment to the Logic engine.", var.name, new_value)

        if (old_assignment is not None and new_value == old_assignment.children()[1]):
            return # no value change, so don't evaluate opt validities of others

        cls._eval_opt_validities_of_related_vars(var)

    @classmethod
    def get_options_validities(cls, var):
        cls.so.push()
        cls._apply_relational_assertions(cls.so)
        cls._apply_assignment_assertions(cls.so, exclude_varname=var.name)
        new_validities = {opt: cls.so.check(var==opt)==sat for opt in var._options}
        cls.so.pop()
        return new_validities

    @classmethod
    def _eval_opt_validities_of_related_vars(cls, invoker_var):
        """ When a variable value gets (re-)assigned, this method is called the refresh options validities of
        related variables that may be affected."""
        logger.debug("Evaluating options validities of related variables of %s", invoker_var.name)

        #profiler.enable()

        cls.so.push()
        cls._apply_relational_assertions(cls.so)

        # (ivar==1) First, evaluate if (re-)assignment of self has made an options validities change in its related variables.
        # (ivar>1) Then, recursively check the related variables of related variables whose options validities have changed.
        affected_vars = [invoker_var]+list(invoker_var._related_vars)
        ivar = 1
        while len(affected_vars)>ivar:
            var = affected_vars[ivar]
            if var.has_options():
                cls.so.push()
                cls._apply_assignment_assertions(cls.so, exclude_varname=var.name)
                new_validities = {opt: cls.so.check(var==opt)==sat for opt in var._options}
                cls.so.pop()
                if new_validities != var._options_validities:
                    logger.debug("%s options validities changed.", var.name)
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
        s.set(':core.minimize', True)
        cls._apply_options_assertions(s)
        cls._apply_assignment_assertions(s, exclude_varname=var.name)
        s.add(var==value)

        cls._apply_relational_assertions(s, assert_and_track=True)

        if s.check() == sat:
            raise RuntimeError("_retrieve_error_msg method called for a satisfiable assignment")

        err_msgs = s.unsat_core()
        if len(err_msgs)==1:
            return '{}={} violates assertion:"{}"'.format(var.name, value, err_msgs[0] )
        else:
            err_msgs_joint = '{}={} violates combination of assertions:'.format(var.name, value)
            for i in range(len(err_msgs)):
                err_msgs_joint += ' (Asrt.{}) {}'.format(i+1, err_msgs[i])
            return err_msgs_joint


logic = Logic()