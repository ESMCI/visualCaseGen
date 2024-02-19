import logging
from z3 import Solver, sat, unsat, BoolRef
from z3 import Implies, Or
from z3 import BoolRef
from z3 import z3util

from ProConPy.dev_utils import ConstraintViolation

logger = logging.getLogger(f"  {__name__.split('.')[-1]}")


class CspSolver:
    """A Z3-based (C)onstraint (S)atisfaction (P)roblem Solver Module"""

    def __init__(self):
        self._initialized = False
        self._assignment_history = []
        self._solver = Solver()  # Main solver
        self._assignment_assertions = {}  # assignment assertions for the current stage
        self._past_assignment_assertions = (
            []
        )  # assignment assertions for the past stages
        self._options_assertions = {}  # options assertions for the current stage
        self._past_options_assertions = []  # options assertions for the past stages
        self._traversal_lock = False

    def progress(self):
        """This method is called by Stage when the current stage is completed and the next
        stage (if any) is to be started. This should be the only place in this class where
        assignment and options assertions are permanently applied (although they may be
        dropped later if the user goes back to a previous stage)."""

        # record the assignment and options assertions to be used when retrieving error messages
        self._past_assignment_assertions.append(self._assignment_assertions)

        # apply all current assignment assertions:
        for _, asrt in self._assignment_assertions.items():
            self._solver.add(asrt)
        self._assignment_assertions = (
            {}
        )  # clear the assignment assertions for the next stage

        # record the options assertions to be used when retrieving error messages
        self._past_options_assertions.append(self._options_assertions)

        # apply all current options assertions:
        for _, asrt in self._options_assertions.items():
            self._solver.add(asrt)
        self._options_assertions = {}  # clear the options assertions for the next stage

        # add a new scope to seal the assertions determined at the currently completed stage.
        self._solver.push()

    def initialize(self, cvars, relational_constraints):
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

    @property
    def initialized(self):
        """Return True if the CSP solver is initialized."""
        return self._initialized

    @property
    def assignment_history(self):
        """Return the history of ConfigVar assignments made by the user."""
        return self._assignment_history

    def reset(self):
        self._assignment_history = []
        pass  # todo

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

        if new_value is None:
            return

        if var.has_options():
            try:
                if var._options_validities[new_value] is False:
                    raise ConstraintViolation(self.retrieve_error_msg(var, new_value))
            except KeyError:
                raise ConstraintViolation(f"{new_value} not an option for {var}")
        else:  # variable has no finite list of options
            with self._solver as s:
                self.apply_assignment_assertions(s, exclude_var=var)
                self.apply_options_assertions(
                    s
                )  # todo: this may not be necessary because options assertions are for variables of future stages
                if s.check(var == new_value) != sat:
                    raise ConstraintViolation(self.retrieve_error_msg(var, new_value))

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
            return f'Invalid assignment of {var} to {new_value}. Reason(s): {", ".join(error_messages)}'

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

        # Below lock ensures that this method is not called recursively from within itself
        # (which can happen if the assignment of a variable triggers the assignment of another variable.)
        if self._traversal_lock is True:
            return
        self._traversal_lock = True

        # First, confirm that assignment is indeed valid and doesn't lead to infeasibilities in future stages
        new_options_and_tooltips = {}
        with self._solver as s:

            # apply all the assignments at current stage except for the variable being assigned.
            self.apply_assignment_assertions(s, exclude_var=var)

            # apply the assignment assertion for the variable being assigned.
            s.add(var == new_value)

            # todo: below intermediate check is likely redundant.
            if s.check() == unsat:
                raise ConstraintViolation(self.retrieve_error_msg(var, new_value))

            # apply all current options assertions for variables that are not dependent on the variable being assigned.
            self.apply_options_assertions(s, exclude_vars=var._dependent_vars)

            # determine new options for dependent variables and temporarily apply the options assertions
            for dependent_var in var._dependent_vars:
                new_options, new_tooltips = dependent_var._options_spec()

                if new_options is not None:
                    new_options_and_tooltips[dependent_var] = (
                        new_options,
                        new_tooltips,
                    )
                    s.add(Or([dependent_var == opt for opt in new_options]))

            if s.check() == unsat:
                logger.info("The new value {new_value} for {var} led to infeasible options for dependent variable(s). "
                    + f"Please choose a different value for {var}. Current assertions in the solver are:")
                for asrt in s.assertions():
                    print(str(asrt)+',')
                raise ConstraintViolation(
                    f"The new value {new_value} for {var} led to infeasible options for dependent variable(s). "
                    + f"Please choose a different value for {var}."
                )

        # Getting here means that the assignment is feasible. Now, indeed register the assignment:
        self._assignment_assertions[var] = var == new_value

        # Having confirmed the feasibility of the assignment, update the options of the dependent variables
        self._update_options_of_dependent_vars(new_options_and_tooltips)

        # refresh the options validities of affected variables
        self._refresh_options_validities(var)

        # record the assignment
        self._assignment_history.append((var, new_value))

        # release the lock
        self._traversal_lock = False

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
            and var._rank <= neig._rank
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

    def apply_assignment_assertions(self, solver, exclude_var=None):
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
        """
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
                if var not in exclude_vars
            ]
        )

    def register_options(self, var, new_options):
        """Register the new options for the given variable. The registry is made to the temporary
        assertions container, and the permanent application of the assertions is done when the stage
        is completed and the next stage is to be started."""
        self._options_assertions[var] = Or([var == opt for opt in new_options])

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
