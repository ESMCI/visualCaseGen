import logging
from z3 import Solver, sat, unsat, BoolRef
from z3 import Implies, And, Or
from z3 import BoolRef
from z3 import z3util

from ProConPy.dev_utils import ConstraintViolation
from ProConPy.csp_utils import TraversalLock
from ProConPy.out_handler import handler as owh

logger = logging.getLogger(f"  {__name__.split('.')[-1]}")


class CspSolver:
    """A Z3-based (C)onstraint (S)atisfaction (P)roblem Solver Module"""

    def __init__(self):
        self.reboot()

    def reboot(self):
        """Reset the CSP solver instance so that it can be re-initialized.
        This is useful for testing purposes and should not be utilized in production
        (except when it is called from within the __init__ method)."""
        self._initialized = False
        self._assignment_history = []
        self._solver = Solver()
        self._assignment_assertions = {}
        self._past_assignment_assertions = []
        self._options_assertions = {}
        self._past_options_assertions = []
        self._tlock = TraversalLock()

    @owh.out.capture()
    def proceed(self):
        """This method is called by Stage when the current stage is completed and the next
        stage (if any) is to be started. This should be the only place in this class where
        assignment and options assertions are permanently applied (although they may be
        dropped later if the user goes back to a previous stage)."""

        logger.debug("Proceeding the CSP solver...")

        # Record the recent assignment and options assertions
        self._past_assignment_assertions.append(self._assignment_assertions)
        self._past_options_assertions.append(self._options_assertions)

        # Clean the current assignment and options assertions for the next stage
        self._assignment_assertions = {}
        self._options_assertions = {}

        # Finally, refresh the solver
        self._refresh_solver()

    @owh.out.capture()
    def revert(self):
        """This method is called by Stage when the user wants to revert to the previous stage.
        This method reverts the solver to the state it was in at the end of the previous stage.
        """
        logger.debug("Reverting the CSP solver...")
        self._assignment_assertions = self._past_assignment_assertions.pop()
        self._options_assertions = self._past_options_assertions.pop()
        self._refresh_solver()


    def _refresh_solver(self):
        """Reset the solver and (re-)apply the relational constraints, the past assignment
        assertions, and the past options assertions. This method is called when the user wants
        to proceed/revert to a subsequent/previous stage. Resetting the solver turned out to
        be more efficient than the initial approach of using push/pop to manage the solver."""
        self._solver.reset()
        self._solver.add([asrt for asrt, _ in self._relational_constraints.items()])
        for scope in self._past_assignment_assertions:
            self._solver.add([asrt for _, asrt in scope.items()])
        for scope in self._past_options_assertions:
            self._solver.add([asrt for _, asrt in scope.items()])


    def initialize(self, cvars, relational_constraints, first_stage):
        """Initialize the CSP solver with relational constraints. The relational constraints are
        the constraints that are derived from the relationships between the variables. The
        relational constraints are used to determine the validity of variable options.

        Parameters
        ----------
        cvars : dict
            A dictionary of ConfigVar instances where the keys are the sexprs of the variables.
        relational_constraints : dict
            A dictionary where the keys are the z3 boolean expressions corresponding to the
            constraints and the values are error messages to be displayed when the constraint is
            violated.
        first_stage : Stage
            The first top-level stage of the stage tree.
        """

        assert not self._initialized, "CspSolver is already initialized."
        assert isinstance(relational_constraints, dict), (
            "relational_constraints must be a dictionary where keys are the z3 boolean expressions "
            + "corresponding to the constraints and values are error messages to be displayed when "
            + "the constraint is violated."
        )

        # Store the relational constraints
        self._relational_constraints = relational_constraints

        # Construct constraint hypergraph and add constraints to solver
        self._construct_hypergraph(cvars)

        # Traverse stage tree
        self._traverse_stages(first_stage, 0, cvars)

        # Having read in the constraints, update validities of variables that have options:
        for var in cvars.values():
            if var.has_options():
                var.update_options_validities()

        self._initialized = True
        logger.info("CspSolver initialized.")

    def _construct_hypergraph(self, cvars):
        """Construct a hypergraph from:
        (1) relational constraints
        (2) options specs
        (3) functional dependencies
        """

        self.hgraph = {}
        self.vars2constraints = {}

        # (1) relational constraints

        warn = (
            "The relational_constraints must be a dictionary where keys are the z3 boolean expressions "
            "corresponding to the constraints and values are error messages to be displayed when "
            "the constraint is violated."
        )

        for constr in self._relational_constraints:

            assert isinstance(constr, BoolRef), (
                warn + f"The key {constr} is not a z3 boolean expression."
            )
            assert isinstance(self._relational_constraints[constr], str), (
                warn
                + f"The value {self._relational_constraints[constr]} is not a string."
            )

            # add constraint to solver
            self._solver.add(constr)

            constr_vars = [cvars[var.sexpr()] for var in z3util.get_vars(constr)]

            for var in constr_vars:
                var._related_vars.update(set(constr_vars) - {var})
                if var not in self.vars2constraints:
                    self.vars2constraints[var] = []
                self.vars2constraints[var].append(constr)

            # edges from constraints to variables
            self.hgraph[constr] = constr_vars

            # edges from variables to constraints
            for var in constr_vars:
                if var not in self.hgraph:
                    self.hgraph[var] = []
                self.hgraph[var].append(constr)

    def _traverse_stages(self, stage, rank, cvars):
        """Recursive depth-first traversal of the stage tree to check for variable priority conflicts
        and to determine which of the variables appear in guards of the stages."""

        # set rank
        stage.rank = rank

        logger.info("Traversing stage: %s, rank: %s", stage, rank)

        # set the ranks of the variables
        for var in stage._varlist:
            var.add_rank(stage.rank)

        # flag variables that appear in guards
        if stage.is_guarded():
            assert stage.has_children(), (
                f"The stage {stage} is guarded but has no children."
            )

            guard = stage._activation_guard
            if isinstance(guard, BoolRef):
                guard_vars = [cvars[var.sexpr()] for var in z3util.get_vars(guard)]
                for var in guard_vars:
                    var.is_guard_var = True


        # move on to the next stage
        if stage.has_children():
            self._traverse_stages(stage._children[0], rank+1, cvars)
        elif stage._next is not None:
            self._traverse_stages(stage._next, rank+1, cvars)
        else:
            subsequent_stage = stage.backtrack(visit_all=True)
            if subsequent_stage is not None:
                self._traverse_stages(subsequent_stage, rank+1, cvars)
    
    @property
    def initialized(self):
        """Return True if the CSP solver is initialized."""
        return self._initialized

    @property
    def assignment_history(self):
        """Return the history of ConfigVar assignments made by the user."""
        return self._assignment_history

    def check_assignment(self, var, new_value):
        """Check if the given value is a valid assignment for the given variable. The assignment
        is checked by applying the assignment assertions and the options assertions to the solver.

        Parameters
        ----------
        var : ConfigVar
            The variable being assigned.
        new_value : any
            The new value of the variable.

        Raises
        ------
        ConstraintViolation : If the assignment is invalid.
        """

        logger.debug("Checking assignment of %s to %s", var, new_value)
        assert (
            self._initialized
        ), "Must finalize initialization before CspSolver can operate."

        # None is always a valid assignment
        if new_value is None:
            return

        if var.has_options():
            try:
                if var._options_validities[new_value] is False:
                    raise ConstraintViolation(self.retrieve_error_msg(var, new_value))
            except KeyError:
                raise ConstraintViolation(f"{new_value} not an option for {var}")
        else:  # variable has no finite list of options
            self._do_check_assignment(var, new_value)

    def _do_check_assignment(self, var, new_value):
        """Check if the given value is a valid assignment for the given variable. The assignment
        is checked by applying the assignment assertions and the options assertions to the solver.
        Also, return the new options and tooltips for the dependent variables to avoid recomputation.

        Parameters
        ----------
        var : ConfigVar
            The variable being assigned.
        new_value : any
            The new value of the variable.

        Returns
        -------
        dict
            A dictionary with the dependent variables as keys and the new options and tooltips as values.

        Raises
        ------
        ConstraintViolation : If the assignment is invalid.
        """

        with self._solver as s:

            # apply all the assignments at current stage except for the variable being assigned.
            self.apply_assignment_assertions(s, exclude_var=var)

            # apply all current options assertions for variables that are not dependent on the variable being assigned.
            self.apply_options_assertions(s, exclude_vars=var._dependent_vars)

            # apply the assignment assertion for the variable being assigned.
            if new_value is not None:
                s.add(var == new_value)

            # todo: below intermediate check is likely redundant.
            if s.check() == unsat:
                raise ConstraintViolation(self.retrieve_error_msg(var, new_value))

            # determine new options for dependent variables and temporarily apply the options assertions
            new_options_and_tooltips = {}
            for dependent_var in var._dependent_vars:
                new_options, new_tooltips = dependent_var._options_spec()

                new_options_and_tooltips[dependent_var] = (
                    new_options,
                    new_tooltips,
                )
                if new_options is not None:
                    s.add(Or([dependent_var == opt for opt in new_options]))

            if s.check() == unsat:
                # The new value for the variable being assigned led to infeasible options for dependent variables.
                # Set variable value to None, and raise an exception.
                var.value = None
                raise ConstraintViolation(
                    f"Your current configuration settings have created infeasible options for future settings. "\
                    "Please reset or revise your selections."
                )

        return new_options_and_tooltips

    def check_assignments(self, assignments):
        """Check multiple assignments at once. This method is more efficient than calling
        check_assignment() multiple times because it applies the assignment assertions and the
        options assertions to the solver only once.

        Parameters
        ----------
        assignments : tuple of (ConfigVar, any)
            A tuple of (variable, value) pairs to be checked for validity.

        Raises
        ------
        ConstraintViolation : If any of the assignments is invalid.
        """

        logger.debug("Checking multiple assignments...")
        assert (
            self._initialized
        ), "Must finalize initialization before CspSolver can operate."

        assignments = tuple(a for a in assignments if a[1] is not None)
        vars = [var for var, _ in assignments]
        assignment_assertions = And([var == new_value for var, new_value in assignments])

        with self._solver as s:
            self.apply_assignment_assertions(s, exclude_vars=vars)
            self.apply_options_assertions(s, exclude_vars=vars)
            if s.check(assignment_assertions) == unsat:
                raise ConstraintViolation(
                    f"The assignments led to infeasible options for dependent variable(s). "
                )

    def check_expression(self, expr):
        """Check if the given z3 BoolRef expression is satisfiable.

        Parameters
        ----------
        expr : BoolRef
            The z3 boolean expression to be checked for satisfiability.

        Returns
        -------
        bool
            True if the expression is satisfiable, False otherwise.
        """

        logger.debug("Checking expression: %s", expr)
        assert (
            self._initialized
        ), "Must finalize initialization before CspSolver can operate."
        assert isinstance(
            expr, BoolRef
        ), f'expr "{expr}" must be a z3 boolean expression.'

        with self._solver as s:
            self.apply_assignment_assertions(s)
            self.apply_options_assertions(
                s
            )  # todo: this may not be necessary because options assertions are for variables of future stages
            return s.check(expr) == sat

    def retrieve_error_msg(self, var, new_value):
        """Retrieve an error message for the given assignment of the given variable to the given
        value. The error message is retrieved by applying the assignment assertions and the options
        assertions to the solver and then retrieving the unsatisfiable core of the solver.

        Parameters
        ----------
        var : ConfigVar
            The variable being assigned.
        new_value : any
            The new value of the variable.

        Returns
        -------
        str
            The error message for the given assignment of the given variable to the given value.
        """

        # TODO: this method can be made more efficient both in terms of time and space complexity.
        # e.g., by removing the need for keeping track of past assignment and options assertions
        # and perhaps by using the "Consequences" feature of Z3. Another thing to try is to
        # utilize assert_and_track() method at initialization when adding relational constraints
        # to self._solver and thus not having to create a brand new solver instance for each call
        # to this method.

        with Solver() as s:
            s.set(":core.minimize", True)
            # apply past assertions
            for stage in self._past_assignment_assertions:
                s.add([asrt for _, asrt in stage.items()])
            for stage in self._past_options_assertions:
                s.add([asrt for _, asrt in stage.items()])
            # apply current assertions
            self.apply_assignment_assertions(s, exclude_var=var)
            self.apply_options_assertions(s)
            s.add(var == new_value)

            # apply relational constraints
            for constr in self._relational_constraints:
                s.assert_and_track(constr, self._relational_constraints[constr])

            if s.check() == sat:
                raise RuntimeError(
                    f"The assertion {var} == {new_value} is satisfiable, "
                    + "so cannot retrieve an error message."
                )

            error_messages = [str(err_msg) for err_msg in s.unsat_core()]
            return f'Invalid assignment of {var} to {new_value}. Reason(s): {". ".join(error_messages)}'

    def register_assignment(self, var, new_value):
        """Register the assignment of the given variable to the given value. The assignment is
        registered to the temporary assertions container, and the permanent application of the
        assertions is done when the stage is completed and the next stage is to be started.

        Parameters
        ----------
        var : ConfigVar
            The variable being assigned.
        new_value : any
            The new value of the variable.

        Raises
        ------
        ConstraintViolation : If the assignment is invalid.
        """

        logger.debug(f"Registering assignment of {var} to {new_value}.")

        if not (var.has_dependent_vars() or var.has_related_vars() or var.is_guard_var):
            logger.debug("%s has no dependent or related variables. Returning.", var)
            return

        if self._tlock.is_locked():
            # Traversal lock is acquired, so return without doing anything. This happens when
            # the assignment of a variable triggers the assignment of another variable from within this function.
            logger.debug(
                "Traversal lock is already acquired. Returning without doing anything."
            )
            return

        with self._tlock:  # acquire the lock to prevent recursive traversal of constraint hypergraph

            # First, confirm that assignment is indeed valid and doesn't lead to infeasibilities in future stages.
            # Also, get the new options and tooltips for the dependent variables to avoid recomputation.
            new_options_and_tooltips = self._do_check_assignment(var, new_value)

            # Aassignment is feasible. Register the assignment, except when the assignment is None
            # or the variable has no dependent variables.
            if var.has_related_vars() or var.is_guard_var:
                if new_value is not None:
                    self._assignment_assertions[var] = var == new_value
                else:
                    self._assignment_assertions.pop(var, None)

            # Update the options of the dependent variables
            self._update_options_of_dependent_vars(new_options_and_tooltips)

            # refresh the options validities of affected variables
            self._refresh_options_validities(var)

            # record the assignment
            self._assignment_history.append((var, new_value))

    @staticmethod
    def _update_options_of_dependent_vars(new_options_and_tooltips):
        """Update the options of variables in new_options_and_tooltips. This method is called
        after a variable is assigned to a new value. The new options are determined by the
        options specs of the variables whose options depend on the variable being assigned.

        Parameters
        ----------
        new_options_and_tooltips : dict
            A dictionary with the dependent variables as keys and the new options and tooltips as values.
        """

        for dependent_var, (
            new_options,
            new_tooltips,
        ) in new_options_and_tooltips.items():
            if new_options is not None:
                dependent_var.options = new_options
                dependent_var.tooltips = new_tooltips
            else:
                dependent_var.options = []
                dependent_var.tooltips = []

    @staticmethod
    def _refresh_options_validities(var):
        """Traverse the hypergraph to refresh the options validities of all affected variables
        by the assignment of the given variable.

        Parameters
        ----------
        var : ConfigVar
            The variable whose assignment is to be refreshed.
        """

        # Refresh the options validities of affected variables:
        visited = set()

        # a lambda function to determine if a neighboring variable should be refreshed
        do_refresh = (
            lambda var, neig: neig.has_options()
            and neig not in visited
            and var.max_rank <= neig.min_rank
        )

        vars_to_refresh = [neig for neig in var._related_vars if do_refresh(var, neig)]
        while len(vars_to_refresh) > 0:
            neig = vars_to_refresh.pop(0)
            logger.debug(f"Refreshing options validities of {neig}.")
            visited.add(neig)

            # update the validities of the neighboring (affected) variable and extend the list
            # of variables to refresh to include the affected variables of the neighboring variable.
            if neig.update_options_validities() is True:  # validities have changed
                vars_to_refresh.extend(
                    [
                        neig_neig
                        for neig_neig in neig._related_vars
                        if do_refresh(neig, neig_neig)
                    ]
                )

    def apply_assignment_assertions(self, solver, exclude_var=None, exclude_vars=None):
        """Apply the assignment assertions to the given solver. The assignment assertions are
        the assertions that are made for the current stage. The assignment assertions are added
        to the temporary assertions container, and the permanent application of the assertions
        is done when the stage is completed and the next stage is to be started.

        Parameters
        ----------
        solver : Solver
            The solver to which the assignment assertions are to be applied.
        exclude_var : ConfigVar
            A variable for which the assignment assertions are not to be applied.
        exclude_vars : list or set
            A list or set of variables for which the assignment assertions are not to be applied.
        """

        assert (
            exclude_var is None or exclude_vars is None
        ), "Cannot provide both exclude_var and exclude_vars."

        if exclude_vars:
            solver.add(
                [
                    asrt
                    for var, asrt in self._assignment_assertions.items()
                    if not any(exclude_var is var for exclude_var in exclude_vars)
                ]
            )
        else:
            solver.add(
                [
                    asrt
                    for var, asrt in self._assignment_assertions.items()
                    if var is not exclude_var
                ]
            )

    def apply_options_assertions(self, solver, exclude_vars=[]):
        """Apply the options assertions to the given solver. The options assertions are the
        assertions that are determined at the current stage but are the options for the variables
        of the future stages. The options assertions are added to the temporary assertions container
        and the permanent application of the assertions is done when the stage is completed and the
        next stage is to be started.

        Parameters
        ----------
        solver : Solver
            The solver to which the options assertions are to be applied.
        exclude_vars : list or set
            A list or set of variables for which the options assertions are not to be applied.
        """
        solver.add(
            [
                asrt
                for var, asrt in self._options_assertions.items()
                if not any(exclude_var is var for exclude_var in exclude_vars)
            ]
        )

    def register_options(self, var, new_options):
        """Register the new options for the given variable. The registry is made to the temporary
        assertions container, and the permanent application of the assertions is done when the stage
        is completed and the next stage is to be started."""
        if new_options is not None and len(new_options) > 0:
            self._options_assertions[var] = Or([var == opt for opt in new_options])
        else:
            self._options_assertions.pop(var, None)

    def get_options_validities(self, var):
        """Get the validities of the options of the given variable. The validities are determined
        by checking the satisfiability of the assignment assertions with the variable being assigned
        to each of its options. The validities are returned as a dictionary with the options as keys
        and the validities as values.

        Parameters
        ----------
        var : ConfigVar
            The variable whose options are to be checked for validity.

        Returns
        -------
        dict
            A dictionary with the options as keys and the new validities as values.
        """
        with self._solver as s:
            self.apply_assignment_assertions(s, exclude_var=var)
            self.apply_options_assertions(
                s, exclude_vars=[var]
            )  # todo: this may not be necessary because options assertions are for variables of future stages
            new_validities = {opt: s.check(var == opt) == sat for opt in var._options}
        return new_validities


csp = CspSolver()

# TODO: Potential optimization for the future:
# 1, For a given variable, remove its options assertions from the solver when the variable is assigned to a new value.
#   (but save the options assertions in a temporary container in case the assignment is reverted. Think,
#   for instance, about the COMPSET_ALIAS variable assigned in "Standard compset" track. It usually has a huge list of options).
