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
    # dictionary of child variables
    child_vars = dict()
    # list of constraint hypergraph layers
    layers = []

    @classmethod
    def reset(cls):
        cls.child_vars = dict()
        cls.layers = []
        Layer.reset()

    @classmethod
    def _initialize_chg_layers(cls, new_assertions, vdict):
        """Determines constraint hypergraph layer indices of assertions and variables appearing in those assertions."""

        if len(cls.layers) > 0:
            raise RuntimeError("Relational assertions must be registered before assignment assertions.")

        # layer index solver:
        lis = Solver()

        for asrt in new_assertions:
            # unconditional constraints
            if isinstance(asrt, BoolRef):

                asrt_vars = z3util.get_vars(asrt)
                for var in asrt_vars:
                    Layer.indices[var] = Int("LayerIx{}".format(var))
                if len(asrt_vars)>1:
                    li_var_0 = Layer.indices[asrt_vars[0]] # layer index of 0.th assertion variable
                    for i in range(1,len(asrt_vars)):
                        li_var_i = Layer.indices[asrt_vars[i]] # layer index of i.th assertion variable
                        lis.add(li_var_0 == li_var_i)

            # conditional constraints
            elif isinstance(asrt, tuple) and len(asrt)==2 and isinstance(asrt[0], BoolRef) and isinstance(asrt[1], BoolRef):

                antecedent_vars = z3util.get_vars(asrt[0])
                consequent_vars = z3util.get_vars(asrt[1])

                for a_var in antecedent_vars:
                    Layer.indices[a_var] = Int("LayerIx{}".format(a_var))
                    for c_var in consequent_vars:
                        Layer.indices[c_var] = Int("LayerIx{}".format(c_var))
                        lis.add(Layer.indices[a_var] < Layer.indices[c_var])
            
            else:
                raise RuntimeError("Unsupported relational assertion encountered.")

        if lis.check() == unsat:
            raise RuntimeError("Error in relational variable hierarchy. Make sure to use conditional "\
                "relationals (i.e., When() operators) in a consistent manner. Conditional relationals dictate "\
                "variable hierarchy such that variables appearing in antecedent have higher hierarchies "\
                "than those appearing in consequent. See constraint hierarchy graph documentation for more info.")

        layer_index_model = lis.model()

        # cast Layer.indices values to integers:
        for var in Layer.indices:
            Layer.indices[var] = layer_index_model[Layer.indices[var]].as_long()

        # get a set of layer indices and initialize Layer instances:
        layer_index_vals = sorted(set(Layer.indices.values()))
        n_layer_index_vals = len(layer_index_vals)
        normalization = {layer_index_vals[i]: i for i in range(n_layer_index_vals)}
        cls.layers = [ Layer(i) for i in range(n_layer_index_vals)]

        # normalize layer indices. Also turn variable layer indices into lists so as to allow variables
        # to have multiple layer indices. This is needed when a variable is connected to other layers via
        # conditional relational assertions. The first index, however, is the primary layer that the
        # variable belongs to.
        for var in Layer.indices:
            li = normalization[Layer.indices[var]] 
            Layer.indices[var] = [li]
            cls.layers[li].vars.append(var)

        # finally, set layer indices of assertions:
        for asrt in new_assertions:
            # unconditional assertions
            if isinstance(asrt, BoolRef):
                asrt_vars = z3util.get_vars(asrt)
                li = Layer.get_major_index(asrt_vars[0])
                Layer.indices[asrt] = [li]
                cls.layers[li].relational_assertions[asrt] = new_assertions[asrt]
            # conditional constraints
            elif isinstance(asrt, tuple) and len(asrt)==2 and isinstance(asrt[0], BoolRef) and isinstance(asrt[1], BoolRef):
                antecedent_vars = z3util.get_vars(asrt[0])
                consequent_vars = z3util.get_vars(asrt[1])
                li= max([Layer.get_major_index(c_var) for c_var in consequent_vars])
                Layer.indices[asrt] = [li]
                cls.layers[li].relational_assertions[Implies(asrt[0], asrt[1])] = new_assertions[asrt]

                # add the layer index to antecedent vars' layer indices
                for a_var in antecedent_vars:
                    if li not in Layer.indices[a_var]:
                        Layer.indices[a_var].append(li)
                    if a_var not in cls.layers[li].ghost_vars:
                        cls.layers[li].ghost_vars.append(a_var)

    @classmethod
    def _gen_constraint_hypergraph(cls, new_assertions, vdict):

        cls.chg = nx.Graph()

        for asrt in new_assertions:

            # unconditional assertions
            if isinstance(asrt, BoolRef):

                asrt_vars = {vdict[var.sexpr()] for var in z3util.get_vars(asrt)}
                for var in asrt_vars:
                    var._related_vars.update(asrt_vars - {var})

                li = Layer.get_major_index(asrt)

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

                antecedent_vars = {vdict[var.sexpr()] for var in z3util.get_vars(asrt[0])}
                consequent_vars = {vdict[var.sexpr()] for var in z3util.get_vars(asrt[1])}

                # add conditional assertion node
                li = Layer.get_major_index(asrt)
                cls.chg.add_node(asrt, li=li, hyperedge=True, conditional=True)

                for a_var in antecedent_vars:
                    # add antecedent variables nodes (if not added already)
                    if a_var not in cls.chg:
                        li = Layer.get_major_index(a_var)
                        cls.chg.add_node(a_var, li=li, hyperedge=False)
                    # add edge from var to asrt
                    cls.chg.add_edge(a_var, asrt) # higher var to assertion

                    if a_var not in cls.child_vars:
                        cls.child_vars[a_var] = set()
                    cls.child_vars[a_var].update([var for var in consequent_vars])

                for c_var in consequent_vars:
                    # add consequent variables's node (if not added already)
                    if c_var not in cls.chg:
                        li = Layer.get_major_index(c_var)
                        cls.chg.add_node(c_var, li=li, hyperedge=False)
                    # add edge from var to asrt
                    cls.chg.add_edge(c_var, asrt) # lower var to assertion

        # Check if newly added relational assertions are sat:
        #todo s = Solver()
        #todo cls._apply_assignment_assertions(s)
        #todo cls._apply_options_assertions(s)
        #todo cls._apply_relational_assertions(s)
        #todo if s.check() == unsat:
        #todo     raise RuntimeError("Relational assertions not satisfiable!")

    @classmethod
    def register_assignment(cls, var, new_value):
        logger.debug("Registering %s=%s assignment with the logic engine.", var.name, new_value)

        for li in Layer.get_indices(var):
            cls.layers[li].asrt_assignments.pop(var, None)
            if new_value is not None:
                cls.layers[li].asrt_assignments[var] = var==new_value

    @classmethod
    def register_options(cls, var, new_opts):
        logger.debug("Registering options of %s with the logic engine", var.name)

        for li in Layer.get_indices(var):
            cls.layers[li].asrt_options[var] = Or([var==opt for opt in new_opts]) 
            cls.layers[li].asrt_assignments.pop(var, None)

    @classmethod
    def register_relational_assertions(cls, assertions_setter, vdict):

        for layer in cls.layers:
            if len(layer.relational_assertions)>0:
                raise RuntimeError("Attempted to call register_relational_assertions method multiple times.")

        # Obtain all new assertions including conditionals and unconditionals
        new_assertions = assertions_setter(vdict)

        cls._initialize_chg_layers(new_assertions, vdict)
        cls._gen_constraint_hypergraph(new_assertions, vdict)

    @classmethod
    def check_assignment(cls, var, new_value):
        li = Layer.get_major_index(var)
        cls.layers[li].check_assignment(var, new_value)

    @classmethod
    def get_options_validities(cls, var):
        li = Layer.get_major_index(var)
        return cls.layers[li].get_options_validities(var)

    @classmethod
    def retrieve_error_msg(cls, var, value):
        """Given a failing assignment, retrieves the error message associated with the relational assertion
        leading to unsat."""
        li = Layer.get_major_index(var)
        return cls.layers[li].retrieve_error_msg(var, value)

    @classmethod
    def notify_related_vars(cls, invoker_var):
        """ When a variable value gets (re-)assigned, this method is called to notify the related variables that
        may be affected by the value assignment"""
        logger.debug("Evaluating options validities of related variables of %s", invoker_var.name)

        li = Layer.get_major_index(invoker_var) 
        cls.layers[li].notify_related_vars(invoker_var)


class Layer():
    """ A class that encapsulate constraint hypergraph layer properties. """

    # a mapping from variable to its major layer index
    indices= dict()

    def __init__(self, li):
        if not isinstance(li, int):
            raise RuntimeError("Layer indices must be of type integer")

        # layer index
        self.li = li
        # variables that appear in this layer
        self.vars = []
        # variables that don't appear in this var but connected to this var via conditional assertions
        self.ghost_vars = []
        # assertions keeping track of variable assignments. key is var, value is assignment assertion
        self.asrt_assignments = dict()
        # assertions for options lists of variables. key is var, value is options assertion
        self.asrt_options = dict()
        # relational assertions appearing in this layer
        self.relational_assertions = dict()
    
    @classmethod
    def reset(cls):
        cls.indices = dict()
    
    @classmethod
    def get_indices(cls, var):
        return cls.indices.get(var, [0])

    @classmethod
    def get_major_index(cls, var):
        return cls.indices.get(var, [0])[0]

    def _apply_assignment_assertions(self, solver, exclude_varname=None):
        """ Adds all current assignment assertions to a given solver instance.
        The assignment of a variable may be excluded by providing its name to the optional exclude_varname option. """

        if exclude_varname is None:
            solver.add([self.asrt_assignments[var] for var in self.asrt_assignments])
        else:
            solver.add([self.asrt_assignments[var] for var in self.asrt_assignments if var.name != exclude_varname])
    
    def _apply_options_assertions(self, solver):
        """ Adds all of the current options assertions to a given solver instance."""
        solver.add([self.asrt_options[var] for var in self.asrt_options])

    def _apply_relational_assertions(self, solver, assert_and_track=False):
        """ Adds all of the relational assertions to a given solver instance """
        
        if assert_and_track is True:
            for asrt in self.relational_assertions:
                solver.assert_and_track(asrt, self.relational_assertions[asrt])
        else:
            solver.add(list(self.relational_assertions))
        

    def get_options_validities(self, var):
        s = Solver()
        self._apply_options_assertions(s)
        self._apply_assignment_assertions(s, exclude_varname=var.name)
        self._apply_relational_assertions(s)
        new_validities = {opt: s.check(var==opt)==sat for opt in var._options}
        return new_validities
    
    def check_assignment(self, var, new_value):

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
                self._apply_options_assertions(s)
                self._apply_assignment_assertions(s)
                s.add(var==new_value)
                self._apply_relational_assertions(s)
                status = s.check()==sat

                if status is False:
                    err_msg = self.retrieve_error_msg(var, new_value)
        
        if status is False:
            raise AssertionError(err_msg)
    
    def retrieve_error_msg(self, var, value):
        """Given a failing assignment, retrieves the error message associated with the relational assertion
        leading to unsat."""

        s = Solver()
        s.set(':core.minimize', True)
        self._apply_options_assertions(s)
        self._apply_assignment_assertions(s, exclude_varname=var.name)
        s.add(var==value)
        self._apply_relational_assertions(s, assert_and_track=True)

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
    
    def notify_related_vars(self, invoker_var):

        s = Solver()
        self._apply_options_assertions(s)
        self._apply_relational_assertions(s)

        # (ivar==1) First, evaluate if (re-)assignment of self has made an options validities change in its related variables.
        # (ivar>1) Then, recursively check the related variables of related variables whose options validities have changed.
        affected_vars = [invoker_var] + list(invoker_var._related_vars)
        ivar = 1
        while len(affected_vars)>ivar:
            var = affected_vars[ivar]
            if var.has_options():
                s.push()
                self._apply_assignment_assertions(s, exclude_varname=var.name)
                new_validities = {opt: s.check(var==opt)==sat for opt in var._options}
                s.pop()
                if new_validities != var._options_validities:
                    logger.debug("%s options validities changed.", var.name)
                    var._update_options(new_validities=new_validities)
                    affected_vars += [var_other for var_other in var._related_vars if var_other not in affected_vars]
            ivar += 1



logic = Logic()