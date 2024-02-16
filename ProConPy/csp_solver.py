from z3 import Solver, sat, unsat, BoolRef
from z3 import Implies
from z3 import BoolRef
from z3 import z3util


class CspSolver:
    """A Z3-based (C)onstraint (S)atisfaction (P)roblem Solver Module"""

    def __init__(self):
        self._initialized = False
        self._assignment_history = []

    def initialize(self, cvars, relational_constraints):
        """Initialize the CSP solver with relational constraints."""

        assert not self._initialized, "CspSolver is already initialized."
        assert isinstance(relational_constraints, dict), (
            "relational_constraints must be a dictionary where keys are the z3 boolean expressions "
            + "corresponding to the constraints and values are error messages to be displayed when "
            + "the constraint is violated."
        )

        self._construct_hypergraph(cvars, relational_constraints,  None)
        # TODO continue from here

        self._initialized = True

    def _construct_hypergraph(self, cvars, relational_constraints, options_specs):
        """Construct a hypergraph from:
        (1) relational constraints
        (2) options specs
        (3) functional dependencies
        """

        self.hgraph = {}

        # (1) relational constraints

        for constr in relational_constraints:

            # conventional constraints
            if isinstance(constr, BoolRef):
                constr_vars = [cvars[var.sexpr()] for var in z3util.get_vars(constr)]

                # edges from constraints to variables
                self.hgraph[constr] = constr_vars

                # edges from variables to constraints
                for var in constr_vars:
                    if var not in self.hgraph:
                        self.hgraph[var] = []
                    self.hgraph[var].append(constr)

            ###todo:remove elif isinstance(constr, While):

            ###todo:remove     # antecedent
            ###todo:remove     antecedent_vars = [
            ###todo:remove         cvars[var.sexpr()] for var in z3util.get_vars(constr.antecedent)
            ###todo:remove     ]
            ###todo:remove     consequent_vars = [
            ###todo:remove         cvars[var.sexpr()] for var in z3util.get_vars(constr.consequent)
            ###todo:remove     ]

            ###todo:remove     # Transform While clause into conventional Implies clause
            ###todo:remove     constr_implies = Implies(constr.antecedent, constr.consequent)

            ###todo:remove     # edges from antecedent vars to constraints
            ###todo:remove     for var in antecedent_vars:
            ###todo:remove         if var not in self.hgraph:
            ###todo:remove             self.hgraph[var] = []
            ###todo:remove         self.hgraph[var].append(constr_implies)

            ###todo:remove     # edges from constraints to consequent vars. Note: no edges from constraints to
            ###todo:remove     # antecedent vars because antecedent vars are not affected by the constraint
            ###todo:remove     self.hgraph[constr_implies] = consequent_vars

            else:
                raise ValueError(f"Unknown constraint type: {constr}")


    @property
    def initialized(self):
        return self._initialized

    @property
    def assignment_history(self):
        return self._assignment_history

    def reset(self):
        self._assignment_history = []
        pass  # todo

    def check_assignment(self, var, new_value):
        assert (
            self._initialized
        ), "Must finalize initialization before CspSolver can operate."

        # TODO: raise ConstraintViolation if assignment is invalid
        # TODO: raise ConstraintViolation if assignment is invalid
        # TODO: raise ConstraintViolation if assignment is invalid

        pass  # todo

    def check_expression(self, expr):
        """Check if the given expression is satisfiable."""
        assert (
            self._initialized
        ), 'Must finalize initialization before CspSolver can operate.'
        assert (
            isinstance(expr, BoolRef)
        ), f'expr "{expr}" must be a z3 boolean expression.'
        
        # todo: Correct below implementation
        s = Solver()
        s.add(expr)
        return s.check() == sat

    def retrieve_error_msg(self, var, new_value):

        return "Blablabla"
        pass  # todo

    def register_assignment(self, var, new_value):
        pass  # todo

    def register_options(self, var, new_options):
        pass  # todo

    def get_options_validities(self, var):
        # todo
        # return {opt: True for opt in var._options}
        return {opt: opt != "Custom" for opt in var._options}

    def refresh_options_validities(self):
        pass  # todo

    def designate_affected_vars(self):
        pass  # todo


csp = CspSolver()
