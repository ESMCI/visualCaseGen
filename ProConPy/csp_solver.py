import logging
from z3 import Solver, Optimize, sat, unsat, Or
from z3 import BoolRef, Int
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
        self._checked_assignment = None
        # ^ A record of the current assignment being processed. This is used
        # as a hand-shake mechanism between check_assignment and register_assignment.

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
        to proceed/revert to a following/previous stage. Resetting the solver turned out to
        be more efficient than the initial approach of using push/pop to manage the solver.
        """
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

        # Determine variable ranks and ensure variable precedence is consistent
        self._determine_variable_ranks(first_stage, cvars)

        # Construct constraint hypergraph and add constraints to solver
        self._process_relational_constraints(cvars)

        # Having read in the constraints, update validities of variables that have options:
        for var in cvars.values():
            if var.has_options():
                var.update_options_validities()

        self._initialized = True
        logger.info("CspSolver initialized.")

    def _determine_variable_ranks(self, stage, cvars):
        """Determine the ranks of the variables. The ranks are determined by checking the
        consistency of the variable precedence. The precedence of the variables is determined by
        the order in which the variables are assigned in the stage tree. The lower the rank, the
        higher the precedence."""

        # Solver to check if a consistent ranking of variables is possible
        s = Solver()

        # Instantiate temporary rank variables for each config variable to determine their ranks
        [Int(f"{var}_rank") for var in cvars]

        # The maximum rank
        max_rank = Int("max_rank")

        while stage is not None:

            varlist = stage._varlist
            assert len(varlist) > 0, "Stage has no variables."

            curr_rank = Int(f"{varlist[0]}_rank")

            # All ranks must be nonnegative and less than or equal to the maximum rank
            s.add([0 <= curr_rank, curr_rank <= max_rank])

            # All stage vars must have the same rank
            for var in varlist[1:]:
                s.add(curr_rank == Int(f"{var}_rank"))

            # The next stage in stage tree (via full DFS traversal)
            dfs_next_stage = stage.get_next(full_dfs=True)
            if dfs_next_stage is None:
                break
            elif dfs_next_stage.has_condition():
                condition = dfs_next_stage._condition
                # Skip the guard and move on to its first child as the next stage
                dfs_next_stage = dfs_next_stage.get_next(full_dfs=True)
                # Now, process the guard variables.
                if isinstance(condition, BoolRef):
                    guard_vars = [
                        cvars[var.sexpr()] for var in z3util.get_vars(condition)
                    ]
                    for guard_var in guard_vars:
                        # Mark guard variables
                        guard_var.is_guard_var = True
                        # All guard variables must have a lower rank than the variables in the next stage:
                        s.add(
                            Int(f"{guard_var}_rank")
                            < Int(f"{dfs_next_stage._varlist[0]}_rank")
                        )

            # Find out the stage that would follow the current stage in an actual run.
            true_next_stage = dfs_next_stage
            if not (
                stage.is_sibling_of(dfs_next_stage)
                or stage.is_ancestor_of(dfs_next_stage)
            ):
                ancestor = stage._parent
                while ancestor is not None:
                    if (not ancestor.has_condition()) and ancestor._right is not None:
                        true_next_stage = ancestor._right
                        break
                    ancestor = ancestor._parent

            # All variables in the current stage must have a lower rank than the variables in the (true) next stage:
            s.add(curr_rank < Int(f"{true_next_stage._varlist[0]}_rank"))

            for aux_var in stage._aux_varlist:
                # All auxiliary variables must have a higher rank than the variables in the current stage:
                s.add(curr_rank < Int(f"{aux_var}_rank"))
                # All auxiliary variables must have a lower rank than the variables in the (true) next stage:
                s.add(
                    Int(f"{aux_var}_rank") < Int(f"{true_next_stage._varlist[0]}_rank")
                )

            # Check if the current stage is consistent
            if s.check() == unsat:
                raise RuntimeError("Inconsistent variable ranks encountered.")

            # continue dfs traversal:
            stage = dfs_next_stage

        # Also take options dependencies into account
        for var in cvars.values():
            for dependent_var in var._dependent_vars:
                s.add(Int(f"{var}_rank") < Int(f"{dependent_var}_rank"))
        if s.check() == unsat:
            raise RuntimeError(
                "Inconsistent variable ranks encountered due to options dependencies."
            )

        # Now minimize the maximum rank (This is optional and can be removed if performance becomes an issue)
        opt = Optimize()
        opt.add(s.assertions())
        opt.minimize(max_rank)
        opt.check()
        model = opt.model()

        for var in cvars:
            try:
                cvars[var].rank = model.eval(Int(f"{var}_rank")).as_long()
            except AttributeError:
                # This variable is not contained by any stage. Set its rank to max_rank + 1
                cvars[var].rank = model.eval(Int("max_rank")).as_long() + 1

    def _process_relational_constraints(self, cvars):
        """Process the relational constraints to construct a constraint graph and add constraints
        to the solver. The constraint graph is a directed graph where the nodes are the variables
        and the edges are (one or more) relational constraints that connect the variables.
        """

        # constraint graph
        self._cgraph = {var: set() for var in cvars.values()}

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

            # add constraint to the solver
            self._solver.add(constr)

            constr_vars = {cvars[var.sexpr()] for var in z3util.get_vars(constr)}

            for var in constr_vars:
                self._cgraph[var].update(
                    set(
                        var_other
                        for var_other in constr_vars
                        if var_other is not var and var_other.rank >= var.rank
                    )
                )

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
        if var.value == new_value:
            logger.debug("Assignment is the same as the current value. Returning.")
            return

        # Sanity checks
        assert self._initialized, "Must finalize initialization to check assignments."
        assert (
            self._checked_assignment is None
        ), "A check/register cycle is in progress."
        assert new_value is not None, "None is always a valid assignment."

        # Depending on the domain of the variable, check the assignment
        if var.has_options():
            self._check_assignment_of_finite_domain_var(var, new_value)
        else:
            self._check_assignment_of_infinite_domain_var(var, new_value)

        # Record the currently checked assignment for registration
        self._checked_assignment = (var, new_value)

    def _check_assignment_of_finite_domain_var(self, var, new_value):
        """Check the assignment of a variable with a finite domain to a new value. The check
        is simply done by looking up the validity of the new value in the options_validities
        of the variable.  This method is called by check_assignment when the variable being
        assigned has options."""

        if var._value_delimiter is None:
            if (validity := var._options_validities.get(new_value)) is False:
                raise ConstraintViolation(self.retrieve_error_msg(var, new_value))
            if validity is None:
                raise ConstraintViolation(f"{new_value} not an option for {var}")
        else:
            new_values = new_value.split(var._value_delimiter)
            for new_val in new_values:
                if (validity := var._options_validities.get(new_val)) is False:
                    raise ConstraintViolation(self.retrieve_error_msg(var, new_val))
                if validity is None:
                    raise ConstraintViolation(f"{new_val} not an option for {var}")

    def _check_assignment_of_infinite_domain_var(self, var, new_value):
        """Check the assignment of a variable with an infinite domain to a new value. The check
        is done by applying the assignment assertions and the options assertions to the solver
        and checking the satisfiability of the solver. If the assignment is invalid, a
        ConstraintViolation is raised with an error message that explains the reason for the
        invalid assignment. This method is called by check_assignment when the variable being
        assigned has no options."""

        with self._solver as s:

            # apply all the assignments at current stage except for the variable being assigned.
            self.apply_assignment_assertions(s, exclude_var=var)

            # apply all current options assertions for variables that are not dependent on the variable being assigned.
            self.apply_options_assertions(s, exclude_vars=var._dependent_vars)

            # apply the assignment assertion for the variable being assigned.
            s.add(var == new_value)

            if s.check() == unsat:
                raise ConstraintViolation(self.retrieve_error_msg(var, new_value))

            # Now, remove old assignment assertion for good. This is to make sure that no conflict occurs
            # with the new assignment assertion when the new options_spec are called and they themselves call
            # csp methods, e.g., check_assignments, that rely on self._assignment_assertions.
            self._assignment_assertions.pop(var, None)

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
                    f"Your current configuration settings have created infeasible options for future settings. "
                    "Please reset or revise your selections."
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
            msg = f"Invalid assignment of {var} to {new_value}."
            if len(error_messages) == 1:
                msg += f" Reason: {error_messages[0]}"
            else:
                msg += " Reasons:"
                for i, err_msg in enumerate(error_messages):
                    msg += f" {i+1}: {err_msg}."
                msg = msg.replace("..", ".")
            return msg

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
        if new_value is not None:
            assert self._checked_assignment == (
                var,
                new_value,
            ), "The assignment to be registered does not match the latest checked assignment."
            # Handshake complete. Reset the checked assignment:
            self._checked_assignment = None

        if not (var.has_dependent_vars() or self._cgraph[var] or var.is_guard_var):
            logger.debug("%s has no dependent or related variables. Returning.", var)
            return

        assert (
            not self._tlock.is_locked()
        ), "Traversal lock is acquired. Cannot register assignment."

        with self._tlock:  # acquire the lock to detect recursive traversal of constraint hypergraph

            # Register the assignment, except when the assignment is None
            # or the variable has no dependent variables.
            if self._cgraph[var] or var.is_guard_var:
                if new_value is not None:
                    self._assignment_assertions[var] = var == new_value
                else:
                    self._assignment_assertions.pop(var, None)

            # Update the options of the dependent variables
            self._update_options_of_dependent_vars(var, new_value)

            # refresh the options validities of affected variables
            self._refresh_options_validities(var)

            # record the assignment
            self._assignment_history.append((var, new_value))

    @staticmethod
    def _update_options_of_dependent_vars(var, new_value):
        """Update the options of variables in new_options_and_tooltips. This method is called
        after a variable is assigned to a new value. The new options are determined by the
        options specs of the variables whose options depend on the variable being assigned.

        Parameters
        ----------
        var : ConfigVar
            The variable whose assignment triggers the update of the options of dependent variables.
        new_value : any
            The new value of the variable.
        """

        if new_value is None:
            new_options_and_tooltips = {
                dependent_var: (None, None) for dependent_var in var._dependent_vars
            }
        else:
            new_options_and_tooltips = {}
            for dependent_var in var._dependent_vars:
                new_options, new_tooltips = dependent_var._options_spec()

                new_options_and_tooltips[dependent_var] = (
                    new_options,
                    new_tooltips,
                )
            # Note: For variables with infinite domain, the options_spec methods are called both
            # within check_assignment and register_assignment. This doesn't appear to lead to
            # noticeable performance issues, but it may be worth revisiting in the future.

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

    def _refresh_options_validities(self, var):
        """Traverse the constraint graph to refresh the options validities of all possibly affected
        variables by the assignment of the given variable.

        Parameters
        ----------
        var : ConfigVar
            The variable whose assignment triggers the refresh of the options validities of other variables.
        """

        # Queue of variables to be visited
        queue = [neig for neig in self._cgraph[var] if neig.has_options()]

        # Set of all variables that have been queued
        queued = {var} | set(queue)

        # Traverse the constraint graph to refresh the options validities of all possibly affected variables
        while queue:

            # Pop the first variable from the queue
            var = queue.pop(0)
            logger.debug("Refreshing options validities of %s.", var)

            # Update the validities of the variable and extend the queue if necessary
            validities_changed = var.update_options_validities()
            if validities_changed:
                extension = [
                    neig
                    for neig in self._cgraph[var]
                    if neig.has_options() and neig not in queued
                ]
                queue.extend(extension)
                queued.update(extension)

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
