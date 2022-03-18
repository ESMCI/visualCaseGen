import logging
from visualCaseGen.OutHandler import handler as owh
from visualCaseGen.logic_utils import When, MinVal, MaxVal

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
    # list of constraint hypergraph layers
    layers = []

    invoker_lock = False

    @classmethod
    def reset(cls):
        cls.layers = []
        Layer.reset()

    @classmethod
    def _initialize_layers(cls, new_assertions, options_setters, vdict):
        """Determines constraint hypergraph layer indices of assertions and variables appearing in those assertions."""

        if len(cls.layers) > 0:
            raise RuntimeError("Relational assertions must be registered before assignment assertions.")

        # layer index solver:
        lis = Solver()

        layer_indices = {}

        # First, take into account the relational assertions (both ordinary and preconditional)
        for asrt in new_assertions:
            # Ordinary constraints
            if isinstance(asrt, BoolRef):

                asrt_vars = [vdict[var.sexpr()] for var in z3util.get_vars(asrt)]
                for var in asrt_vars:
                    layer_indices[var] = Int("LayerIdx{}".format(var))
                if len(asrt_vars)>1:
                    li_var_0 = layer_indices[asrt_vars[0]] # layer index of 0.th assertion variable
                    for i in range(1,len(asrt_vars)):
                        li_var_i = layer_indices[asrt_vars[i]] # layer index of i.th assertion variable
                        lis.add(li_var_0 == li_var_i)

            # Preconditional constraints
            elif isinstance(asrt, When):

                antecedent_vars = [vdict[var.sexpr()] for var in z3util.get_vars(asrt.antecedent)]
                consequent_vars = [vdict[var.sexpr()] for var in z3util.get_vars(asrt.consequent)]

                for a_var in antecedent_vars:
                    layer_indices[a_var] = Int("LayerIdx{}".format(a_var))
                    for c_var in consequent_vars:
                        layer_indices[c_var] = Int("LayerIdx{}".format(c_var))
                        lis.add(layer_indices[a_var] < layer_indices[c_var])

            else:
                raise RuntimeError("Unsupported relational assertion encountered.")

        if lis.check() == unsat:
            raise RuntimeError("Error in relational variable hierarchy. Make sure to use preconditioned "\
                "relationals (i.e., When() operators) in a consistent manner. Preconditioned relationals dictate "\
                "variable hierarchy such that variables appearing in antecedent have higher hierarchies "\
                "than those appearing in consequent. See constraint hierarchy graph documentation for more info.")

        # After having taken into account the relational assertions, impose the layerconstraints due to
        # the options dependencies:
        for os in options_setters:
            if os.has_inducing_vars():
                layer_indices[os.var] = Int("LayerIdx{}".format(os.var))
                for inducing_var in os.inducing_vars:
                    layer_indices[inducing_var] = Int("LayerIdx{}".format(inducing_var))
                    lis.add(layer_indices[os.var] > layer_indices[inducing_var])

        if lis.check() == unsat:
            raise RuntimeError("Error in relational variable hierarchy after registering options dependencies. "\
                "Make sure to use preconditioned "\
                "relationals (i.e., When() operators) in a consistent manner. Preconditional relationals dictate "\
                "variable hierarchy such that variables appearing in antecedent have higher hierarchies "\
                "than those appearing in consequent. See constraint hierarchy graph documentation for more info.")

        # now that we have confirmed the feasibilty of the layer constraints, minimize the number of layers:
        Logic._minimize_n_layers(layer_indices, lis)
        layer_index_model = lis.model()

        # cast layer_indices values to integers:
        for var in layer_indices:
            layer_indices[var] = layer_index_model[layer_indices[var]].as_long()

        # get a set of layer indices and initialize Layer instances:
        layer_index_vals = sorted(set(layer_indices.values()))
        n_layer_index_vals = len(layer_index_vals)
        normalization = {layer_index_vals[i]: i for i in range(n_layer_index_vals)}
        cls.layers = [ Layer(i) for i in range(n_layer_index_vals)]

        # normalize layer indices. Also turn variable layer indices into lists so as to allow variables
        # to have multiple layer indices. This is needed when a variable is connected to other layers via
        # preconditional relational assertions. The first index, however, is the primary layer that the
        # variable belongs to.
        for var in layer_indices:
            idx = normalization[layer_indices[var]]
            var.add_layer(cls.layers[idx])
            cls.layers[idx].vars.append(var)

    @staticmethod
    def _minimize_n_layers(layer_indices, lis):

        minimizing_constraint = None
        layer_indices_list = list(layer_indices.values())
        layer_index_max = MaxVal(layer_indices_list)
        layer_index_min = MinVal(layer_indices_list)
        for layer_range in range(2,100):
            if lis.check( (layer_index_max-layer_index_min) == layer_range ) == sat:
                minimizing_constraint = (layer_index_max-layer_index_min) == layer_range
                break

        if minimizing_constraint is None:
            raise RuntimeError("Relational and options constraints resulted in more than a hundred constraint "
            "hypergraph layers, which indicates a likely error in the constraints specification. Exiting...")

        lis.add(minimizing_constraint)
        lis.check()

    @classmethod
    def _register_relational_assertions(cls, new_assertions, vdict):

        # finally, set layer indices of assertions:
        for asrt in new_assertions:
            # Ordinary assertions
            if isinstance(asrt, BoolRef):
                asrt_vars = [vdict[var.sexpr()] for var in z3util.get_vars(asrt)]
                asrt.layer = asrt_vars[0].major_layer
                asrt.layer.relational_assertions[asrt] = new_assertions[asrt]
            # Preconditined constraints
            elif isinstance(asrt, When):
                antecedent = asrt.antecedent
                consequent = asrt.consequent
                antecedent_vars = [vdict[var.sexpr()] for var in z3util.get_vars(antecedent)]
                consequent_vars = [vdict[var.sexpr()] for var in z3util.get_vars(consequent)]
                idx= max([c_var.major_layer.idx for c_var in consequent_vars])
                asrt.layer = cls.layers[idx]
                asrt.layer.relational_assertions[Implies(antecedent, consequent)] = new_assertions[asrt]

                # add the layer index to antecedent vars' layer indices
                for a_var in antecedent_vars:
                    if asrt.layer not in a_var.layers:
                        a_var.add_layer(asrt.layer)
                    if a_var not in cls.layers[idx].ghost_vars:
                        cls.layers[idx].ghost_vars.append(a_var)
            else:
                raise RuntimeError("Encountered unknown relational assertion type: {}".format(asrt))

    @classmethod
    def _gen_constraint_hypergraph(cls, new_assertions, options_setters, vdict):
        """ Given a dictionary of relational assertions, generates the constraint hypergraph. This method
        also sets the related_vars and child_vars_rlt properties of variables appearing in relational assertions."""

        cls.chg = nx.Graph()

        # Nodes:
        for layer in cls.layers:
            for var in layer.vars:
                cls.chg.add_node(var, li=layer.idx, type="V") # V: variable node

        # Edges and Hyperedges due to relational assertions:
        for asrt in new_assertions:

            # Ordinary assertions
            if isinstance(asrt, BoolRef):

                asrt_vars = {vdict[var.sexpr()] for var in z3util.get_vars(asrt)}
                for var in asrt_vars:
                    var.related_vars.update(asrt_vars - {var})

                # add ordinary assertion node
                cls.chg.add_node(asrt, li=asrt.layer.idx, type="U") # U: ordinary relational assertion

                # add edge from variable to asrt
                for var in asrt_vars:
                    cls.chg.add_edge(var, asrt)

            # preconditional constraints
            elif isinstance(asrt, When):

                antecedent_vars = {vdict[var.sexpr()] for var in z3util.get_vars(asrt.antecedent)}
                consequent_vars = {vdict[var.sexpr()] for var in z3util.get_vars(asrt.consequent)}

                # add preconditional assertion node
                cls.chg.add_node(asrt, li=asrt.layer.idx, type="C") # C: preconditional relational assertion

                for a_var in antecedent_vars:
                    # add edge from var to asrt
                    cls.chg.add_edge(a_var, asrt) # higher var to assertion

                    # todo: consider making child_vars_rlt of type set
                    a_var.child_vars_rlt.extend([var for var in consequent_vars if var not in a_var.child_vars_rlt])

                for c_var in consequent_vars:
                    # add edge from var to asrt
                    cls.chg.add_edge(c_var, asrt) # lower var to assertion

        # Edges and hyperedges due to options setters:
        for os in options_setters:
            if os.has_inducing_vars():
                idx = os.var.major_layer.idx
                hyperedge_str = '{} options setter'.format(os.var)
                cls.chg.add_node(hyperedge_str, li=idx, type="O")

                for inducing_var in os.inducing_vars:
                    cls.chg.add_edge(inducing_var, hyperedge_str)
                    inducing_var.child_vars_opt.add(os.var)

                cls.chg.add_edge(hyperedge_str, os.var)

        # Check if newly added relational assertions are sat:
        #todo s = Solver()
        #todo cls._apply_assignment_assertions(s)
        #todo cls._apply_options_assertions(s)
        #todo cls._apply_relational_assertions(s)
        #todo if s.check() == unsat:
        #todo     raise RuntimeError("Relational assertions not satisfiable!")

    @classmethod
    def register_interdependencies(cls, relational_assertions_setter, options_setters, vdict):

        for layer in cls.layers:
            if len(layer.relational_assertions)>0:
                raise RuntimeError("Attempted to call register_interdependencies method multiple times.")

        # Obtain all new assertions including preconditionals and ordinary assertions
        relational_assertions = relational_assertions_setter(vdict)

        cls._initialize_layers(relational_assertions, options_setters, vdict)
        cls._register_relational_assertions(relational_assertions, vdict)
        cls._gen_constraint_hypergraph(relational_assertions, options_setters, vdict)

    @classmethod
    def register_assignment(cls, var, new_value):
        logger.debug("Registering %s=%s assignment with the logic engine.", var.name, new_value)

        for layer in var.layers:
            layer.asrt_assignments.pop(var, None)
            if new_value is not None:
                layer.asrt_assignments[var] = var==new_value

    @classmethod
    def register_options(cls, var, new_opts):
        logger.debug("Registering options of %s with the logic engine", var.name)

        for layer in var.layers:
            layer.asrt_options[var] = Or([var==opt for opt in new_opts])
            layer.asrt_assignments.pop(var, None)

    @classmethod
    def check_assignment(cls, var, new_value):
        var.major_layer.check_assignment(var, new_value)

    @classmethod
    def get_options_validities(cls, var):
        return var.major_layer.get_options_validities(var)

    @classmethod
    def retrieve_error_msg(cls, var, value):
        """Given a failing assignment, retrieves the error message associated with the relational assertion
        leading to unsat."""
        return var.major_layer.retrieve_error_msg(var, value)

    @classmethod
    def notify_related_vars(cls, invoker_var):
        """ When a variable value gets (re-)assigned, this method is called to notify the related variables that
        may be affected by the value assignment"""

        if Logic.invoker_lock is True:
            return # the root invoker is not this variable, so return
        Logic.invoker_lock = True

        logger.debug("Evaluating options validities of related variables of %s", invoker_var.name)

        # layer index of invoker var
        idx = invoker_var.major_layer.idx

        # indices of layers that may need to be notified:
        relevant_layer_indices = range(idx, len(cls.layers))

        # running lists of affected vars for each layer
        affected_vars = {rli:[] for rli in relevant_layer_indices}
        affected_vars[idx] = list(invoker_var.related_vars)

        # record variables whose options are to be updated due to the value change of invoker_var:
        for child_var_opt in invoker_var.child_vars_opt:
            child_layer = child_var_opt.major_layer
            child_layer.vars_refresh_opts.add(child_var_opt)

        # also record child vars that may be affected by invoker_var's value change:
        for child_var_rlt in invoker_var.child_vars_rlt:
            child_li = child_var_rlt.major_layer.idx
            if child_var_rlt not in affected_vars[child_li]:
                affected_vars[child_li].append(child_var_rlt)

        for rli in relevant_layer_indices:
            cls.layers[rli].sweep(affected_vars)

        Logic.invoker_lock = False # After having traversed the entire chg, release the invoker lock.

class Layer():
    """ A class that encapsulate constraint hypergraph layer properties. """

    _indices = set()

    def __init__(self, idx):

        if not isinstance(idx, int):
            raise RuntimeError("Layer indices must be of type integer")
        if idx in Layer._indices:
            raise RuntimeError("A layer with idx {} alread instantiated".format(idx))
        Layer._indices.add(idx)

        # layer index
        self.idx = idx
        # variables that appear in this layer
        self.vars = []
        # variables that don't appear in this var but connected to this var via preconditinal assertions
        self.ghost_vars = []
        # assertions keeping track of variable assignments. key is var, value is assignment assertion
        self.asrt_assignments = dict()
        # assertions for options lists of variables. key is var, value is options assertion
        self.asrt_options = dict()
        # relational assertions appearing in this layer
        self.relational_assertions = dict()

        # set of variables whose options are to be updated
        self.vars_refresh_opts = set()

    @classmethod
    def reset(cls):
        cls._indices = set()

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

    def sweep(self, affected_vars):

        some_options_changed = len(self.vars_refresh_opts) > 0
        some_relational_impact = len(affected_vars[self.idx]) > 0

        if not (some_options_changed or some_relational_impact):
            return

        if some_options_changed is True:
            for var in self.vars_refresh_opts:
                var.run_options_setter()

                for child_var_opt in var.child_vars_opt:
                    child_layer = child_var_opt.major_layer
                    child_layer.vars_refresh_opts.add(child_var_opt)
                for child_var_rlt in var.child_vars_rlt:
                    child_li = child_var_rlt.major_layer.idx
                    if child_var_rlt not in affected_vars[child_li]:
                        affected_vars[child_li].append(child_var_rlt)

            self.vars_refresh_opts = set() # reset

        if not some_relational_impact:
            return

        s = Solver()
        self._apply_options_assertions(s)
        self._apply_relational_assertions(s)

        # Recursively check the related variables whose options validities have changed.
        # Also keep a record of child variables that may have been affected. Those will be
        # checked by subsequent layers.
        ivar = 0
        while len(affected_vars[self.idx]) > ivar:
            var = affected_vars[self.idx][ivar]
            if var.has_options():
                s.push()
                self._apply_assignment_assertions(s, exclude_varname=var.name)
                new_validities = {opt: s.check(var==opt)==sat for opt in var._options}
                s.pop()
                if new_validities != var._options_validities:
                    logger.debug("%s options validities changed.", var.name)
                    var.update_options_validities(new_validities=new_validities)

                    # extend the list of affected vars of this layer
                    affected_vars[self.idx] += [var_other for var_other in var.related_vars if var_other not in affected_vars[self.idx]]

                    # also include child vars that may be affected by options validity change of var:
                    for child_var_rlt in var.child_vars_rlt:
                        child_li = child_var_rlt.major_layer.idx
                        if child_var_rlt not in affected_vars[child_li]:
                            affected_vars[child_li].append(child_var_rlt)
            else:
                logger.debug("Variable %s has no options.", var.name)

            ivar += 1


logic = Logic()