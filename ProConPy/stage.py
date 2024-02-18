"""A module to represent a configuration stage where the user can set a number of
parameters, of type ConfigVar, to configure the system."""

import logging
from z3 import BoolRef

from ProConPy.csp_solver import csp

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

    def __init__(
        self,
        title: str,
        description: str,
        widget,
        varlist: list = [],
        parent: "Stage" = None,
        activation_constr=None,
        hide_when_inactive=True,
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
                    assert (
                        activation_constr is not None
                    ), f"Attempted to add a child stage, {title}, with no activation constraint to a parent stage, {parent}, that has child(ren) with activation constraints."
                    assert activation_constr is True or isinstance(
                        activation_constr, BoolRef
                    ), f"The activation constraint of the child stage, {title} must be a z3.BoolRef or True."
                else:
                    assert (
                        activation_constr is None
                    ), f"Attempted to add a child stage, {title}, with activation constraint to a parent stage, {parent}, that has child(ren) with no activation constraints."

            parent._children.append(self)

        self._title = title
        self._description = description
        self._varlist = varlist
        self._parent = parent
        self._activation_constr = activation_constr
        self._children = []  # to be appended by the child stage(s) (if any)
        self._status = "inactive"
        self._hide_when_inactive = hide_when_inactive

        self._widget = widget
        self._widget.children = [var.widget for var in varlist]

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

    def is_first(self):
        return Stage._top_level[0] is self

    def has_children(self):
        return len(self._children) > 0

    def has_guarded_children(self):
        return any([child._activation_constr is not None for child in self._children])

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
            self._complete_stage()

    def _complete_stage(self):
        """Disable the stage and hand over control to the next stage."""
        self._disable()
        self._progress()

    def _progress(self):
        """End this stage and move on to the following stage. This may be a child stage or the next stage.
        If no child or next stage is found, backtrack to an ancestor stage that has a next stage.
        """

        Stage._current_rank += 1

        if self.has_children():

            # Determine the child stage to enable
            if self.has_guarded_children():
                child = self._determine_child_to_enable()
            else:
                child = self._children[0]

            # Display the child stage and its subsequent stages
            self._widget.children += tuple(child.level_widgets())

            child._enable()

        elif self._next is not None:
            # Enable the next stage
            self._next._enable()

        else:
            # No subsequent stage found. Backtrack.
            self._backtrack()
        
        # Progress the csp solver too:
        csp.progress()

    def _backtrack(self):
        """Recursively backtrack until a stage that has a next stage is found.
        When such a stage is found, enable its next stage. Otherwise, the stage
        tree is complete."""

        if self._prev is not None:
            self._prev._backtrack()

        elif self._parent is not None:
            if self._parent._next is not None:
                self._parent._next._enable()
            else:
                self._parent._backtrack()

        else:
            logger.debug("SUCCESS: All stages are complete.")

    def _determine_child_to_enable(self):
        """Determine the child stage to activate."""
        child_to_activate = None
        for child in self._children:
            logger.debug("Checking activation constraint of child stage %s: %s", child, child._activation_constr)
            if csp.check_expression(child._activation_constr) is True:
                assert (
                    child_to_activate is None
                ), "Only one child stage can be activated at a time."
                child_to_activate = child

        assert (
            child_to_activate is not None
        ), "At least one child stage must be activated."
        return child_to_activate

    def _disable(self):
        """Deactivate the stage, preventing the user from setting the parameters in the varlist."""
        for var in self._varlist:
            var.widget.disabled = True

    def _enable(self):
        """Activate the stage, allowing the user to set the parameters in the varlist."""

        for var in self._varlist:
            var.widget.disabled = False
            var._rank = Stage._current_rank

        # if the stage doesn't have any ConfigVars, it is already complete
        if len(self._varlist) == 0:
            self._complete_stage()

    def subsequent_stages(self):
        """Return a list of subsequent stages excluding child stages."""
        subsequent_stages = []
        stage = self._next
        while stage is not None:
            subsequent_stages.append(stage)
            stage = stage._next
        return subsequent_stages

    def level_widgets(self):
        """Return a list of widgets including the widget of the stage and its subsequent stages."""
        widgets = [self._widget]
        widgets += [s._widget for s in self.subsequent_stages()]
        return widgets
