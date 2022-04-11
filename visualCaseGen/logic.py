import logging
from visualCaseGen.OutHandler import handler as owh
from visualCaseGen.logic_utils import When, MinVal, MaxVal
from visualCaseGen.dev_utils import debug, assignment_history, RunError
from visualCaseGen.dialog import alert_warning

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
        assignment_history.clear()
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
        if n_layer_index_vals==0:
            cls.layers = [ Layer(0)]
        else:
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
        if len(layer_indices_list)==0:
            return

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
                asrt.layer.add_relational_assertion(asrt, new_assertions[asrt])

            # Preconditined constraints
            elif isinstance(asrt, When):
                antecedent = asrt.antecedent
                consequent = asrt.consequent
                antecedent_vars = [vdict[var.sexpr()] for var in z3util.get_vars(antecedent)]
                consequent_vars = [vdict[var.sexpr()] for var in z3util.get_vars(consequent)]
                idx= max([c_var.major_layer.idx for c_var in consequent_vars])
                asrt.layer = cls.layers[idx]
                asrt.layer.add_relational_assertion(Implies(antecedent, consequent), new_assertions[asrt])

                # add the layer index to antecedent vars' layer indices
                for a_var in antecedent_vars:
                    if asrt.layer not in a_var.layers:
                        a_var.add_layer(asrt.layer)
                    if a_var not in cls.layers[idx].ghost_vars:
                        cls.layers[idx].ghost_vars.append(a_var)
            else:
                raise RuntimeError("Encountered unknown relational assertion type: {}".format(asrt))

        # finally, seal relational assertions of all layers:
        for layer in cls.layers:
            layer.seal_relational_assertions()


    @classmethod
    def _gen_constraint_hypergraph(cls, new_assertions, options_setters, vdict):
        """ Given a dictionary of relational assertions, generates the constraint hypergraph. This method
        also sets the relational vars properties of variables appearing in relational assertions."""

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
                    var.peer_vars_relational.update(asrt_vars - {var})

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

                    # todo: consider making child_vars_relational of type set
                    a_var.child_vars_relational.update(consequent_vars)

                for c_var in consequent_vars:
                    c_var.peer_vars_relational.update(consequent_vars - {c_var})
                    c_var.parent_vars_relational.update(antecedent_vars)

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
                    inducing_var.child_vars_options.add(os.var)

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
            if len(layer._relational_assertions)>0:
                raise RuntimeError("Attempted to call register_interdependencies method multiple times.")

        # Obtain all new assertions including preconditionals and ordinary assertions
        _relational_assertions = relational_assertions_setter(vdict)

        cls._initialize_layers(_relational_assertions, options_setters, vdict)
        cls._register_relational_assertions(_relational_assertions, vdict)
        cls._gen_constraint_hypergraph(_relational_assertions, options_setters, vdict)

    @classmethod
    def register_assignment(cls, var, new_value):
        logger.debug("Registering %s=%s assignment with the logic engine.", var.name, new_value)

        for layer in var.layers:
            layer.add_asrt_assignment(var, new_value)

    @classmethod
    def register_options(cls, var, new_opts):
        logger.debug("Registering options of %s with the logic engine", var.name)

        for layer in var.layers:
            layer.add_asrt_option(var, new_opts)

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
    def traverse_layers(cls, invoker_var):
        """ When a variable value gets (re-)assigned, this method is called to notify the related variables that
        may be affected by the value assignment"""

        if Logic.invoker_lock is True:
            return # the root invoker is not this variable, so return
        Logic.invoker_lock = True

        # record the assignment of invoker var in the assignment_history list
        assignment_history.append((invoker_var.name, invoker_var.value))

        logger.debug("Traversing the constraint hypergraph layers due to invoker variable %s", invoker_var.name)

        # loop over relevant layers and sweep them:
        for idx in range(invoker_var.major_layer.idx, len(cls.layers)):
            cls.layers[idx].sweep(invoker_var)

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
        self._asrt_assignments = dict()
        # assertions for options lists of variables. key is var, value is options assertion
        self._asrt_options = dict()
        # relational assertions appearing in this layer
        self._relational_assertions = dict()
        # a flag to designate whether the addition of relational assertions complete. If so, 
        # optional and assignment assertions may start to be added.
        self._relational_assertions_sealed = False

        # Set of variables whose options validities are to be updated only.
        # These are variables whose neighbors went through either a value change or an options validities change
        self.vars_refresh_validities = list()
        # set of variables whose options are to be updated.
        # These are variables who are options children of variables whose values are changed.
        self.vars_refresh_options = set()

        # a z3 solver instance that includes optional and relational assertions. This solver should be used 
        # whenever possible so as to improve performance
        self._solver = Solver()

    @classmethod
    def reset(cls):
        cls._indices = set()
    
    def add_asrt_assignment(self, var, new_value):
            self._asrt_assignments.pop(var, None)
            if new_value is not None:
                self._asrt_assignments[var] = var==new_value
    
    def add_asrt_option(self, var, new_opts):
        self._asrt_options[var] = Or([var==opt for opt in new_opts])
        self._asrt_assignments.pop(var, None)
        self._solver.pop()
        self._solver.push()
        self._apply_options_assertions(self._solver)

    def add_relational_assertion(self, asrt, err_msg):
        self._relational_assertions[asrt] = err_msg
    
    def seal_relational_assertions(self):
        if self._relational_assertions_sealed:
            raise RuntimeError("Relational assertions already sealed.")
        self._solver = Solver()
        self._apply_relational_assertions(self._solver)
        self._solver.push()
        self._relational_assertions_sealed = True

    def _apply_assignment_assertions(self, solver, exclude_var=None):
        """ Adds all current assignment assertions to a given solver instance.
        The optional exclude_var argument may be used to exclude a given variable """

        if exclude_var is None:
            solver.add([self._asrt_assignments[var] for var in self._asrt_assignments])
        else:
            solver.add([self._asrt_assignments[var] for var in self._asrt_assignments if var is not exclude_var])

    def _apply_options_assertions(self, solver):
        """ Adds all of the current options assertions to a given solver instance."""
        solver.add([self._asrt_options[var] for var in self._asrt_options])

    def _apply_relational_assertions(self, solver, assert_and_track=False):
        """ Adds all of the relational assertions to a given solver instance """

        if assert_and_track is True:
            for asrt in self._relational_assertions:
                solver.assert_and_track(asrt, self._relational_assertions[asrt])
        else:
            solver.add(list(self._relational_assertions))

    @staticmethod
    def designate_affected_vars(var, designate_opt_children=True):
        """ Given a variable whose options or value has changed, designate its neighbors and children
        as variables whose options/validities are to be potentially updated."""

        major_layer = var.major_layer
        major_layer.vars_refresh_validities.extend(
            [var_other for var_other in var.peer_vars_relational if var_other not in major_layer.vars_refresh_validities]            
        )

        # update set of child vars whose validities are to be refreshed:
        for child_var_rlt in var.child_vars_relational:
            child_layer = child_var_rlt.major_layer
            if child_var_rlt not in child_layer.vars_refresh_validities:
                child_layer.vars_refresh_validities.append(child_var_rlt)

        # update set of variables whose options are to be updated due to the value change of this var:
        if designate_opt_children:
            for child_var_opt in var.child_vars_options:
                child_layer = child_var_opt.major_layer
                child_layer.vars_refresh_options.add(child_var_opt)

    def get_options_validities(self, var):
        self._solver.push()
        self._apply_assignment_assertions(self._solver, exclude_var=var)
        new_validities = {opt: self._solver.check(var==opt)==sat for opt in var._options}
        self._solver.pop()
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
                self._solver.push()
                self._apply_assignment_assertions(self._solver, exclude_var=var)
                status = self._solver.check(var==new_value)==sat
                self._solver.pop()

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
        self._apply_assignment_assertions(s, exclude_var=var)
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

    def sweep(self, invoker_var):

        if invoker_var.major_layer is self:
            self._sweep_major_layer(invoker_var)
        else:
            self._sweep_subsq_layer(invoker_var)
    
    def _sweep_major_layer(self, invoker_var):

        some_relational_impact = lambda: len(self.vars_refresh_validities) > 0
        if not some_relational_impact():
            return

        ivar = 0
        while len(self.vars_refresh_validities) > ivar:
            var = self.vars_refresh_validities[ivar]
            ivar += 1
            if var.has_options():

                # Determine new validities
                self._solver.push()
                self._apply_assignment_assertions(self._solver, exclude_var=var)
                new_validities = {opt: self._solver.check(var==opt)==sat for opt in var._options}
                self._solver.pop()

                # Confirm at least one options is valid
                if debug:
                    if not any(new_validities.values()):
                        raise RunError("All new options validities are false for {}".format(var.name))
                
                # If validities changed, update the validities property of var.
                if new_validities != var._options_validities:
                    logger.debug("%s options validities changed.", var.name)
                    if var.value is not None and new_validities[var.value] == False:
                        raise RunError("The {}={} assignment is no longer valid after {}={} assignment!".\
                            format(var.name, var.value, invoker_var.name, invoker_var.value))
                    var.update_options_validities(new_validities=new_validities)
        
        self.vars_refresh_validities.clear()

    
    def _sweep_subsq_layer(self, invoker_var):

        some_options_changed = lambda: len(self.vars_refresh_options) > 0
        some_relational_impact = lambda: len(self.vars_refresh_validities) > 0

        if not (some_options_changed() or some_relational_impact()):
            return
    
        s = Solver()

        # Add all existing relational assertions:
        self._apply_relational_assertions(s)

        # Add existing optional assertions for variables whose options will not change due to invoker_var value change.
        for var in self._asrt_options:
            if var not in self.vars_refresh_options:
                s.add([self._asrt_options[var]])
        if debug:
            if s.check() == unsat:
                raise RunError("Layer not feasible when old optional and relational assertions are applied")
        
        # Apply assignments of ghost variables:
        for ghost_var in self.ghost_vars:
            if ghost_var.value is not None:
                s.add(ghost_var==ghost_var.value)
        if debug:
            if s.check() == unsat:
                raise RunError("The {}={} assignment led to an infeasible subsequent layer.".format(invoker_var.name, invoker_var.value))

        # Add new optional assertions of variables whose options are to change due to invoker_var value change
        new_options_and_tooltips = {}
        for var in self.vars_refresh_options:
            new_options, new_tooltips = var._options_setter()
            new_options_and_tooltips[var] = new_options, new_tooltips
            if new_options is not None:
                new_validities = {opt: s.check(var==opt)==sat for opt in new_options }

                if not any(new_validities.values()):
                    raise RunError("{}={} not feasible! All new options validities are false for {}".\
                        format(invoker_var.name, invoker_var.value, var.name))
                    # todo (1): revert invoker variable assignment here
                    # todo (2): or, maybe, just throw a fatal error and instruct users submit an error report?
                    # todo (3): in the planned static analyzer, make sure to introduce checks that would catch this error
            
                s.add( Or([var==opt for opt in new_options]) )

        # --- Reaching here means that the layer is feasible, however some old variable assignments may not be feasible anymore.

        # Find variable assignments that are not feasible anymore and set those variables to None. This is to make sure
        # that new options may be set without ending up with an infeasible layer solver. Meanwhile, add all feasible variable
        # assignments to the solver if variable options remain the same.
        reset_variables = set() # variables whose value are to be reset because their values are not feasible anymore
        asrt_assignments_temp = dict() # a temporary dict of assertions of assignments that are still feasible
        for var in self.vars:
            if var.value is not None and var not in self.vars_refresh_options:
                if s.check(var==var.value)==sat:
                    asrt_assignments_temp[var] = var==var.value
                else:
                    var.value = None
                    reset_variables.add(var)
        
        if some_options_changed() is True:

            # Remove old optional assertions of variables whose options are to change:
            for var in self.vars_refresh_options:
                self._asrt_options.pop(var, None)

            # We are finally ready to apply the options changes
            for var in self.vars_refresh_options:
                var.refresh_options(*new_options_and_tooltips[var])
                if var.value is not None:
                    asrt_assignments_temp[var] = var==var.value

        self.vars_refresh_options.clear()

        # refresh validities
        ivar = 0
        while len(self.vars_refresh_validities) > ivar:
            var = self.vars_refresh_validities[ivar]
            ivar += 1 
            if var.has_options():
                # Determine new validities
                s.push()
                s.add([asrt_assignments_temp[asg_var] for asg_var in asrt_assignments_temp if var is not asg_var])
                new_validities = {opt: s.check(var==opt)==sat for opt in var._options}
                s.pop()

                # Confirm at least one options is valid
                if debug:
                    if not any(new_validities.values()):
                        raise RunError("All new options validities are false for {}".format(var.name))

                # If validities changed, update the validities property of var.
                if new_validities != var._options_validities:
                    logger.debug("%s options validities changed.", var.name)
                    if var.value is not None and new_validities[var.value] == False:
                        raise RunError("The {}={} assignment is no longer valid after {}={} assignment!".\
                            format(var.name, var.value, invoker_var.name, invoker_var.value))
                    var.update_options_validities(new_validities=new_validities)
        self.vars_refresh_validities.clear()

        # set values of reset_variables, if need be
        for var in reset_variables:
            if var.value is None and var.always_set is True:
                var.value = var.get_first_valid_option()

        # refresh validities again if need be. 
        ivar = 0
        while len(self.vars_refresh_validities) > ivar:
            var = self.vars_refresh_validities[ivar]
            ivar += 1 
            if var.has_options():
                # Determine new validities
                s.push()
                s.add([asrt_assignments_temp[asg_var] for asg_var in asrt_assignments_temp if var is not asg_var])
                new_validities = {opt: s.check(var==opt)==sat for opt in var._options}
                s.pop()

                # Confirm at least one options is valid
                if debug:
                    if not any(new_validities.values()):
                        raise RunError("All new options validities are false for {}".format(var.name))

                # If validities changed, update the validities property of var.
                if new_validities != var._options_validities:
                    logger.debug("%s options validities changed.", var.name)
                    if var.value is not None and new_validities[var.value] == False:
                        raise RunError("The {}={} assignment is no longer valid after {}={} assignment!".\
                            format(var.name, var.value, invoker_var.name, invoker_var.value))
                    var.update_options_validities(new_validities=new_validities)
        self.vars_refresh_validities.clear()

        # finally, inform the user about the indirect value changes occured in this layer
        # due to the invoker value change:
        if len(reset_variables)>0:
            msg = "{}={} assignment led to the following change(s) in dependent variable(s):"\
                .format(invoker_var.name, invoker_var.value)
            for var in reset_variables:
                msg += "  {}={}".format(var.name,var.value)
            alert_warning(msg)

logic = Logic()