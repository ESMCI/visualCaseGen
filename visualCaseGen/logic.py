import logging
from visualCaseGen.OutHandler import handler as owh

from z3 import And, Or, Not, Implies, is_not
from z3 import Solver, sat, unsat
from z3 import BoolRef, Int
from z3 import z3util
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
    # dictionary of constraint hypergraph (chg) layer indices for variables.
    layer_indices= dict()

    child_vars = dict()

    @classmethod
    def reset(cls):
        cls.asrt_assignments = dict()
        cls.asrt_options = dict()
        cls.asrt_unconditional_relationals = dict()
        cls.asrt_conditional_relationals = dict()
        cls.layer_indices = dict()
        cls.child_vars = dict()

    @classmethod
    def get_layer_index(cls, var):
        return cls.layer_indices.get(var, 0)

    @classmethod
    def n_layers(cls):
        return len(set(cls.layer_indices.values()))

    @classmethod
    def _determine_chg_layers(cls, new_assertions, vdict):
        """Determines constraint hypergraph layer indices of assertions and variables appearing in those assertions."""

        if len(cls.asrt_assignments) > 0:
            raise RuntimeError("Relational assertions must be registered before assignment assertions.")
        if len(cls.asrt_options) > 0:
            raise RuntimeError("Relational assertions must be registered before options assertions.")

        # layer index solver:
        lis = Solver()

        for asrt in new_assertions:
            # unconditional constraints
            if isinstance(asrt, BoolRef):

                asrt_vars = z3util.get_vars(asrt)
                for var in asrt_vars:
                    cls.layer_indices[var] = Int("LayerIx{}".format(var))
                if len(asrt_vars)>1:
                    li_var_0 = cls.layer_indices[asrt_vars[0]] # layer index of 0.th assertion variable
                    for i in range(1,len(asrt_vars)):
                        li_var_i = cls.layer_indices[asrt_vars[i]] # layer index of i.th assertion variable
                        lis.add(li_var_0 == li_var_i)

            # conditional constraints
            elif isinstance(asrt, tuple) and len(asrt)==2 and isinstance(asrt[0], BoolRef) and isinstance(asrt[1], BoolRef):

                antecedent_vars = z3util.get_vars(asrt[0])
                consequent_vars = z3util.get_vars(asrt[1])

                for a_var in antecedent_vars:
                    cls.layer_indices[a_var] = Int("LayerIx{}".format(a_var))
                    for c_var in consequent_vars:
                        cls.layer_indices[c_var] = Int("LayerIx{}".format(c_var))
                        lis.add(cls.layer_indices[a_var] < cls.layer_indices[c_var])

        if lis.check() == unsat:
            raise RuntimeError("Error in relational variable hierarchy. Make sure to use conditional "\
                "relationals (i.e., When() operators) in a consistent manner. Conditional relationals dictate "\
                "variable hierarchy such that variables appearing in antecedent have higher hierarchies "\
                "than those appearing in consequent. See constraint hierarchy graph documentation for more info.")

        layer_index_model = lis.model()

        # cast cls.layer_indices values to integers:
        for var in cls.layer_indices:
            cls.layer_indices[var] = layer_index_model[cls.layer_indices[var]].as_long()

        # normalize layer indices:
        layer_index_vals = sorted(set(cls.layer_indices.values()))
        n_layer_index_vals = len(layer_index_vals)
        normalization = {layer_index_vals[i]: i for i in range(n_layer_index_vals)}
        for var in cls.layer_indices:
            cls.layer_indices[var] = normalization[cls.layer_indices[var]]

        # finally, set layer indices of assertions:
        for asrt in new_assertions:
            # unconditional assertions
            if isinstance(asrt, BoolRef):
                asrt_vars = z3util.get_vars(asrt)
                cls.layer_indices[asrt] = cls.get_layer_index(asrt_vars[0])
            # conditional constraints
            elif isinstance(asrt, tuple) and len(asrt)==2 and isinstance(asrt[0], BoolRef) and isinstance(asrt[1], BoolRef):
                consequent_vars = z3util.get_vars(asrt[1])
                max_layer_index= max([cls.get_layer_index(c_var) for c_var in consequent_vars])
                cls.layer_indices[asrt] = max_layer_index

    @classmethod
    def _gen_constraint_hypergraph(cls, new_assertions, vdict):

        cls.chg = nx.Graph()

        for asrt in new_assertions:

            # unconditional assertions
            if isinstance(asrt, BoolRef):

                asrt_vars = z3util.get_vars(asrt)
                li = cls.get_layer_index(asrt)

                # add variable nodes
                for var in asrt_vars:
                    if var not in cls.chg:
                        cls.chg.add_node(var, li=li, hyperedge=False)

                # add unconditional assertion node
                cls.chg.add_node(asrt, li=li, hyperedge=True, conditional=False)

                # add edge from variable to asrt
                for var in asrt_vars:
                    cls.chg.add_edge(var, asrt)

            # conditional constraints
            elif isinstance(asrt, tuple) and len(asrt)==2 and isinstance(asrt[0], BoolRef) and isinstance(asrt[1], BoolRef):

                antecedent_vars = z3util.get_vars(asrt[0])
                consequent_vars = z3util.get_vars(asrt[1])

                # add conditional assertion node
                li = cls.get_layer_index(asrt)
                cls.chg.add_node(asrt, li=li, hyperedge=True, conditional=True)

                for a_var in antecedent_vars:
                    # add antecedent variables nodes (if not added already)
                    if a_var not in cls.chg:
                        li = cls.get_layer_index(a_var)
                        cls.chg.add_node(a_var, li=li, hyperedge=False)
                    # add edge from var to asrt
                    cls.chg.add_edge(a_var, asrt) # higher var to assertion

                for c_var in consequent_vars:
                    # add consequent variables's node (if not added already)
                    if c_var not in cls.chg:
                        li = cls.get_layer_index(c_var)
                        cls.chg.add_node(c_var, li=li, hyperedge=False)
                    # add edge from var to asrt
                    cls.chg.add_edge(c_var, asrt) # lower var to assertion

    @classmethod
    def check_assignment(cls, var, new_value):

        status = True
        err_msg = ''

        if new_value is not None:
            logger.debug("Checking whether %s=%s assignment is sat.", var.name, new_value)
            if var.has_options():
                if new_value not in var.options:
                    status = False
                    err_msg = '{} not an option for {}'.format(new_value, var.name)

            if status is True:
                # now, check if the value satisfies all assertions
                s = Solver()
                cls._apply_options_assertions(s, li=cls.get_layer_index(var))
                cls._apply_assignment_assertions(s, li=cls.get_layer_index(var))
                s.add(var==new_value)
                cls._apply_relational_assertions(s)
                status = s.check() == sat

                if status is False:
                    err_msg = cls.retrieve_error_msg(var, new_value)

        if status is False:
            raise AssertionError(err_msg)

    @classmethod
    def get_options_validities(cls, var):
        s = Solver()
        cls._apply_options_assertions(s, li=cls.get_layer_index(var))
        cls._apply_assignment_assertions(s, exclude_varname=var.name, li=cls.get_layer_index(var))
        cls._apply_relational_assertions(s)
        new_validities = {opt: s.check(var==opt)==sat for opt in var._options}
        return new_validities

    @classmethod
    def register_assignment(cls, var, new_value):
        logger.debug("Registering %s=%s assignment with the logic engine.", var.name, new_value)
        old_assignment = cls.asrt_assignments.pop(var, None)
        if new_value is not None:
            cls.asrt_assignments[var] = var==new_value

    @classmethod
    def register_options(cls, var, new_opts):
        logger.debug("Registering options of %s with the logic engine", var.name)
        cls.asrt_options[var] = Or([var==opt for opt in new_opts])
        cls.asrt_assignments.pop(var, None)

    @classmethod
    def register_relational_assertions(cls, assertions_setter, vdict):

        if len(cls.asrt_unconditional_relationals)>0 or len(cls.asrt_conditional_relationals)>0:
            raise RuntimeError("Attempted to call register_relational_assertions method multiple times.")

        # Obtain all new assertions including conditionals and unconditionals
        new_assertions = assertions_setter(vdict)

        cls._determine_chg_layers(new_assertions, vdict)
        cls._gen_constraint_hypergraph(new_assertions, vdict)
        cls._insert_relational_assertions(new_assertions, vdict)

    @classmethod
    def _insert_relational_assertions(cls, new_assertions, vdict):
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
    def _apply_assignment_assertions(cls, solver, exclude_varname=None, li=None):
        """ Adds all current assignment assertions to a given solver instance.
        The assignment of a variable may be excluded by providing its name to the optional exclude_varname option. """

        if li is None:
            if exclude_varname is None:
                solver.add(list(cls.asrt_assignments.values()))
            else:
                solver.add([cls.asrt_assignments[var] for var in cls.asrt_assignments if var.name != exclude_varname])
        else: # li is NOT None
            if exclude_varname is None:
                solver.add([cls.asrt_assignments[var] for var in cls.asrt_assignments if cls.get_layer_index(var) <= li])
            else:
                solver.add([cls.asrt_assignments[var] for var in cls.asrt_assignments if var.name != exclude_varname and cls.get_layer_index(var) <= li])

    @classmethod
    def _apply_options_assertions(cls, solver, li=None):
        """ Adds all of the current options assertions to a given solver instance."""
        if li is None:
            solver.add(list(cls.asrt_options.values()))
        else:
            solver.add([cls.asrt_options[var] for var in cls.asrt_options if cls.get_layer_index(var) <= li])

    @classmethod
    def _apply_relational_assertions(cls, solver, assert_and_track=False, li=None):
        """ Adds all of the relational assertions to a given solver instance """

        # solver for evaluations the antecedents of conditional relations
        s_ = Solver()
        cls._apply_assignment_assertions(s_)
        cls._apply_options_assertions(s_)

        if assert_and_track is True:
            for asrt in cls.asrt_unconditional_relationals:
                solver.assert_and_track(asrt, cls.asrt_unconditional_relationals[asrt])
            for antecedent, consequent in cls.asrt_conditional_relationals:
                if s_.check(Not(antecedent)) == unsat:
                    solver.assert_and_track(consequent, cls.asrt_conditional_relationals[antecedent,consequent])
        else:
            solver.add(list(cls.asrt_unconditional_relationals))
            for antecedent, consequent in cls.asrt_conditional_relationals:
                if s_.check(Not(antecedent)) == unsat:
                    solver.add(consequent)

    @classmethod
    def notify_related_vars(cls, invoker_var):
        """ When a variable value gets (re-)assigned, this method is called to notify the related variables that
        may be affected by the value assignment"""
        logger.debug("Evaluating options validities of related variables of %s", invoker_var.name)

        #profiler.enable()

        s = Solver()
        cls._apply_options_assertions(s, li=cls.get_layer_index(invoker_var))
        cls._apply_relational_assertions(s)

        # (ivar==1) First, evaluate if (re-)assignment of self has made an options validities change in its related variables.
        # (ivar>1) Then, recursively check the related variables of related variables whose options validities have changed.
        affected_vars = [invoker_var]+list(invoker_var._related_vars)
        ivar = 1
        while len(affected_vars)>ivar:
            var = affected_vars[ivar]
            if var.has_options():
                s.push()
                cls._apply_assignment_assertions(s, exclude_varname=var.name, li=cls.get_layer_index(var))
                new_validities = {opt: s.check(var==opt)==sat for opt in var._options}
                s.pop()
                if new_validities != var._options_validities:
                    logger.debug("%s options validities changed.", var.name)
                    var._update_options(new_validities=new_validities)
                    affected_vars += [var_other for var_other in var._related_vars if var_other not in affected_vars]
            ivar += 1

        #profiler.disable()

    @classmethod
    def retrieve_error_msg(cls, var, value):
        """Given a failing assignment, retrieves the error message associated with the relational assertion
        leading to unsat."""

        s = Solver()
        s.set(':core.minimize', True)
        cls._apply_options_assertions(s, li=cls.get_layer_index(var))
        cls._apply_assignment_assertions(s, exclude_varname=var.name, li=cls.get_layer_index(var))
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