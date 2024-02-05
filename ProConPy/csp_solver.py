from z3 import Solver, sat, unsat


class CspSolver:
    """A Z3-based (C)onstraint (S)atisfaction (P)roblem Solver Module"""

    def __init__(self):
        self._operational = False
        self._assignment_history = []
        self.relational_assertions = {}
        self.options_assertions = []

    @property
    def operational(self):
        return self._operational

    @property
    def assignment_history(self):
        return self._assignment_history

    def reset(self):
        self._assignment_history = []
        pass  # todo

    def finalize_initialization(self):
        assert (
            not self._operational
        ), "finalize_initialization called for a CspSolver instance already operational."
        self._operational = True

    def check_assignment(self, var, new_value):
        assert (
            self._operational
        ), "Must finalize initialization before CspSolver can operate."

        # TODO: throw ConstraintError if assignment is invalid
        # TODO: throw ConstraintError if assignment is invalid
        # TODO: throw ConstraintError if assignment is invalid

        pass  # todo

    def retrieve_error_msg(self, var, new_value):
        pass  # todo

    def register_assignment(self, var, new_value):
        pass  # todo

    def register_options(self, var, new_options):
        pass  # todo

    def get_options_validities(self, var):
        # todo
        return {opt: True for opt in var._options}

    def refresh_options_validities(self):
        pass  # todo

    def designate_affected_vars(self):
        pass  # todo


csp = CspSolver()
