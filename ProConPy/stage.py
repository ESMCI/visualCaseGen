"""A module to represent a configuration stage where the user can set a number of
parameters, of type ConfigVar, to configure the system."""

import itertools
import logging
from z3 import BoolRef

from ProConPy.csp_solver import csp
from ProConPy.out_handler import handler as owh
from ProConPy.dev_utils import DEBUG

logger = logging.getLogger("\t" + __name__.split(".")[-1])


class Stage:
    """A class to represent a configuration stage where the user can set a number of
    parameters, of type ConfigVar, to configure the system.

    Only a single stage can be active at a time.
    A stage is deemed complete when all the parameters in the variable list are set.

    Stage precedence and sequencing rules:
    - A stage can have a previous stage or a parent stage, but not both.
    - A stage can have a next stage and/or child stage.
    - A stage cannot be its own previous stage or its own ancestor. These relationships must be fully acyclic.
    - A next stage gets activated as soon as the previous stage is completed.
    - A child stage gets activated if the parent stage is completed and the activation constraint is satisfied.
    - Only one activation constraint must evaluate to True in a list of child stages.
    """

    # Top level stages, i.e., stages that have no parent stage
    _top_level = []

    # Rank of the current stage. This is used to keep track of order in which the Stages are enabled.
    _current_rank = 0

    # List of stages in the order they are completed. To be used for reverting to the previous stage.
    _completed_stages = []

    def __init__(
        self,
        title: str,
        description: str,
        widget=None,
        varlist: list = [],
        parent: "Stage" = None,
        activation_constr=None,
        hide_when_inactive=True,
        auto_set_single_valid_option=True,
    ):

        if parent is None:  # This is a top-level stage
            assert (
                activation_constr is None
            ), "A top-level stage cannot have an activation constraint."
            Stage._top_level.append(self)

        else:  # This is a child stage, i.e., it has a parent stage
            assert isinstance(
                parent, Stage
            ), "The parent stage must be an instance of the Stage class."

            if parent.has_children():
                if parent.has_guarded_children():
                    assert activation_constr is not None, (
                        f"Attempted to add a child stage, {title}, with no activation constraint to a parent stage, "
                        + f"{parent}, that has child(ren) with activation constraints."
                    )
                    assert activation_constr is True or isinstance(
                        activation_constr, BoolRef
                    ), f"The activation constraint of the child stage, {title} must be a z3.BoolRef or True."
                else:
                    assert activation_constr is None, (
                        f"Attempted to add a child stage, {title}, with activation constraint to a parent stage, "
                        + f"{parent}, that has child(ren) with no activation constraints."
                    )

            parent._children.append(self)

        self._title = title
        self._description = description
        self._varlist = varlist
        self._parent = parent
        self._activation_constr = activation_constr
        self._children = []  # to be appended by the child stage(s) (if any)
        self._status = "inactive"
        self._hide_when_inactive = hide_when_inactive
        self._auto_set_single_valid_option = auto_set_single_valid_option

        if self.is_guarded():
            assert (
                widget is None
            ), f'The guarded "{self._title}" stage cannot have a widget.'
            assert (
                len(varlist) == 0
            ), f'The guarded "{self._title}" stage cannot have a variable list.'
        else:
            assert (
                widget is not None
            ), f'The unguarded "{self._title}" stage must have a widget.'
            # todo assert len(varlist) > 0, f'The unguarded "{self._title}" stage must have a non-empty variable list.'

        self._widget = widget
        if self._widget is not None:
            self._widget.stage = self

        # set _prev and _next stages to be used in fast retrieval of adjacent stages:
        self._prev = None
        self._next = None
        if parent is None and len(Stage._top_level) > 1:
            self._prev = Stage._top_level[-2]
            self._prev._next = self
        if parent is not None and len(parent._children) > 1:
            self._prev = parent._children[-2]
            self._prev._next = self

        self._construct_observances()

        # Enable the first stage and disable the rest
        if self.is_first():
            self._enable()
        else:
            self._disable()

    def __str__(self):
        return self._title

    @classmethod
    def first(cls):
        """Class method that returns the first stage of the stage hierarchy."""
        return cls._top_level[0]

    @classmethod
    def top_level(cls):
        """Class method that returns the top-level stages."""
        return cls._top_level

    def is_first(self):
        return Stage._top_level[0] is self

    def has_children(self):
        return len(self._children) > 0

    def has_guarded_children(self):
        return any([child._activation_constr is not None for child in self._children])

    def is_guarded(self):
        return self._activation_constr is not None

    def check_for_cyclic_relations(self):
        # TODO: Implement a check for cyclic relations, probably in the CSP module and not here.
        pass

    def _construct_observances(self):
        for var in self._varlist:
            var.observe(
                self._on_value_change,
                names="value",
                type="change",
            )

    def is_complete(self):
        """Check if the stage is complete."""
        return all([var.value is not None for var in self._varlist])

    def _on_value_change(self, change):
        """This method is called when the value of a ConfigVar in the varlist changes.
        When all the ConfigVars in the varlist are set, the stage is deemed complete."""
        if self.is_complete():
            logger.debug("Stage <%s> is complete.", self._title)
            self._proceed()

    def _proceed(self):
        """End this stage and move on to the following stage. This may be a child stage or the next stage.
        If no child or next stage is found, backtrack to an ancestor stage that has a next stage.
        """
        self._disable()

        Stage._completed_stages.append(self)
        Stage._current_rank += 1

        stage_to_enable = None

        if self.has_children():
            # Determine the child stage to enable
            child = self._determine_child_to_enable()
            stage_to_enable = child

            # Display the child stage and its subsequent stages by appending them to the current stage's widget
            self._widget.append_child_stages(first_child=child)

        elif self._next is not None:
            stage_to_enable = self._next

        else:
            # No subsequent stage found. Backtrack.
            stage_to_enable = self._backtrack()

        if stage_to_enable is None:
            logger.info("SUCCESS: All stages are complete.")
            return

        # Proceed the csp solver before enabling the next stage
        csp.proceed()

        # Enable the following stage
        stage_to_enable._enable()

    def _backtrack(self):
        """While attempting to proceed, recursively backtrack until a stage that has a next stage
        is found. When such a stage is found, return its next stage for activation. If
        no such stage is found, return None to indicate that the stage tree is complete.

        Returns
        -------
        Stage or None
            The next stage to activate, if found. Otherwise, None.
        """

        if self._prev is not None:
            return self._prev._backtrack()

        elif self._parent is not None:
            if self._parent._next is not None:
                return self._parent._next
            else:
                return self._parent._backtrack()

        return None  # The stage tree is complete

    def _determine_child_to_enable(self):
        """Determine the child stage to activate."""
        child_to_activate = None

        if self.has_guarded_children():
            # If there are guarded children, evaluate the guards, i.e., activation constraints
            # and select the child to activate. Only one child can be activated at a time.
            for child in self._children:
                logger.debug(
                    "Checking activation constraint of child stage %s: %s",
                    child,
                    child._activation_constr,
                )
                if csp.check_expression(child._activation_constr) is True:
                    assert (
                        child_to_activate is None
                    ), "Only one child stage can be activated at a time."
                    child_to_activate = child
        else:
            # If there are no guarded children, the first child is activated.
            # Note the remaining children will be activated in sequence by their siblings.
            child_to_activate = self._children[0]

        assert (
            child_to_activate is not None
        ), "At least one child stage must be activated."

        # If the child to activate is guarded, recursively determine the child to enable
        if child_to_activate.is_guarded():
            return child_to_activate._determine_child_to_enable()

        return child_to_activate

    def _disable(self):
        """Deactivate the stage, preventing the user from setting the parameters in the varlist."""
        logger.debug("Disabling stage %s.", self._title)
        if self._widget is not None:
            self._widget.disabled = True

    @owh.out.capture()
    def _enable(self):
        """Activate the stage, allowing the user to set the parameters in the varlist."""

        logger.info("Enabling stage %s.", self._title)
        if self._widget is not None:
            self._widget.disabled = False

        # Set the rank of the ConfigVars in the stage
        for var in self._varlist:
            var._rank = Stage._current_rank

        # if the stage doesn't have any ConfigVars, it is already complete
        if len(self._varlist) == 0:
            self._proceed()

        # Check if any ConfigVars in the newly enabled stage have exactly one valid option.
        # If so, set their values to those options.
        if self._auto_set_single_valid_option:
            for var in self._varlist:
                if var.has_options():
                    svo = Stage.single_valid_option(var)
                    if svo is not None:
                        var.value = svo

    @staticmethod
    def single_valid_option(var):
        """Check if a ConfigVar has exactly one valid option. If so, return that option.

        Parameters
        ----------
        var : ConfigVar
            The ConfigVar to check.

        Returns
        -------
        str or None
            The single valid option if it exists, otherwise None.
        """
        valid_opts = []
        for opt, validity in var._options_validities.items():
            if validity is True:
                valid_opts.append(opt)
                if len(valid_opts) == 2:
                    break  # there are more than one valid options. No need to check further.
        if len(valid_opts) == 1:
            return valid_opts[0]
        return None

    def subsequent_siblings(self):
        """Return a list of subsequent sibling stages"""
        subsequent_siblings = []
        stage = self
        while stage._next is not None:
            subsequent_siblings.append(stage._next)
            stage = stage._next
        return subsequent_siblings

    def reset(self, b=None):
        """Reset the stage.

        Parameters
        ----------
        b : Button, optional
            The button that triggered the reset.
        """

        for var in self._varlist:
            if var.value is not None:
                var.value = None

        if DEBUG is True:
            assert (
                len(csp._assignment_assertions) == 0
            ), "The assignment assertions list is not empty."
            assert (
                len(csp._options_assertions) == 0 or self.is_first()
            ), "The options assertions list is not empty."

    @owh.out.capture()
    def revert(self, b=None):
        """Reset the stage and go back to the previous stage (if any).

        Parameters
        ----------
        b : Button, optional
            The button that triggered the revert.
        """
        Stage._current_rank -= 1
        self.reset()
        if len(Stage._completed_stages) == 0:
            logger.info("No stage to revert to.")
        else:
            stage_to_enable = Stage._completed_stages.pop()
            logger.info("Reverting to stage %s.", stage_to_enable._title)
            self._disable()
            csp.revert()
            stage_to_enable._enable()
