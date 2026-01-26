"""A module to represent a configuration stage where the user can set a number of
parameters, of type ConfigVar, to configure the system."""

import logging
from z3 import BoolRef
from traitlets import HasTraits, UseEnum

from ProConPy.dev_utils import ConstraintViolation
from ProConPy.csp_solver import csp
from ProConPy.out_handler import handler as owh
from ProConPy.dev_utils import DEBUG
from ProConPy.stage_stat import StageStat

logger = logging.getLogger("\t" + __name__.split(".")[-1])


class Node:
    """A class to represent a node in the stage hierarchy tree. A node can be a stage or a guard.
    The node can have children and a parent. The node can have a condition that must be satisfied
    for the node to be enabled. The node can have a left and right sibling."""

    # Top level nodes, i.e., nodes that have no parent
    _top_level = []

    # Set of titles of all the nodes in the stage tree
    _titles = set()

    def __init__(self, title, parent=None, condition=None):
        """Initialize a node.

        Parameters
        ----------
        title : str
            The title of the node.
        parent : Node, optional
            The parent node of the node.
        condition : z3.BoolRef, optional
            The logical condition that must be satisfied for the node to be enabled.
        """

        if title in Node._titles:
            raise ValueError(f"The title {title} is already used.")
        Node._titles.add(title)

        self._title = title
        self._children = []
        self._parent = parent
        self._condition = condition

        if self._parent is None:
            Node._top_level.append(self)
        else:
            assert isinstance(
                self._parent, Node
            ), "The parent node must be an instance of the Node class."
            parent._children.append(self)

        # set _left and _right nodes to be used in fast retrieval of adjacent nodes:
        self._left = None
        self._right = None
        if parent is None and len(Node._top_level) > 1:
            self._left = Node._top_level[-2]
            self._left._right = self
        if parent is not None and len(parent._children) > 1:
            self._left = parent._children[-2]
            self._left._right = self

    def __str__(self):
        return self._title

    @classmethod
    def reboot(cls):
        """Class method to reset the Node class so that it can be re-initialized.
        This is useful for testing purposes and need not be utilized in production."""
        cls._top_level = []
        cls._titles.clear()

    @classmethod
    def first(cls):
        """Class method that returns the first top-level node"""
        return cls._top_level[0]

    @classmethod
    def top_level(cls):
        """Class method that returns the list of top-level nodes."""
        return cls._top_level

    def is_first(self):
        """Return True if the node is the first top-level node."""
        return Node._top_level[0] is self

    def has_children(self):
        """Return True if the node has children."""
        return len(self._children) > 0

    def has_condition(self):
        """Return True if the node has an associated condition."""
        return self._condition is not None

    def children_have_conditions(self):
        """Return True if any of the children of the node have conditions."""
        return any([child.has_condition() for child in self._children])
    
    def is_sibling_of(self, node):
        """Return True if the node is a sibling of the given node."""
        return self._parent is node._parent
    
    def is_descendant_of(self, other):
        """Return True if the node is a descendant of the given other node."""
        node = self
        while (node := node._parent) is not None:
            if node is other:
                return True
        return False
    
    def is_ancestor_of(self, other):
        """Return True if the node is an ancestor of the given other node."""
        return other.is_descendant_of(self)

    @property
    def title(self):
        return self._title

    def siblings_to_right(self):
        """Return a list of the right siblings of the node."""
        right_siblings = []
        stage = self
        while stage._right is not None:
            right_siblings.append(stage._right)
            stage = stage._right
        return right_siblings

    def check_condition(self):
        """Check if the condition of the node is satisfied."""
        logger.debug("Checking condition of %s: %s", self._title, self._condition)
        return csp.check_expression(self._condition)

    def get_next(self, full_dfs=False):
        """Return the next node in the stage tree. This method must be implemented in the subclass
        since the retrieval of the next node depends on the type of the node.

        Parameters
        ----------
        full_dfs : bool
            If True, visit all the nodes in the stage tree. Otherwise, skip nodes (and its children)
            whose conditions are not satisfied."""

        raise NotImplementedError(
            "The get_next method must be implemented in the subclass."
        )


class Guard(Node):
    """A class to represent a guard node in the stage hierarchy tree. A guard node is a node that
    has a condition that must be satisfied for the node (and its children) to be visited.
    """

    def __init__(self, title, parent, condition):
        """Initialize a guard.

        Parameters
        ----------
        title : str
            The title of the guard.
        parent : Stage
            The parent stage of the guard.
        condition : z3.BoolRef
            The logical guard expression."""

        assert (
            isinstance(condition, BoolRef) or condition is True
        ), "The guard expression must be a z3.BoolRef."
        assert isinstance(
            parent, Stage
        ), "The parent must be an instance of the Stage class."

        if parent.has_children():
            assert (
                parent.children_have_conditions()
            ), f"The {title} guard's siblings must all be guards."

        super().__init__(title, parent)
        self._condition = condition

    def get_next(self, full_dfs=None):
        """Return the next node in the stage tree, which is always the first child for a guard node."""
        return self._children[0]


class Stage(Node, HasTraits):
    """A class to represent configuration stages where the user can set a number of parameters, of type
    ConfigVar, to configure the system. Only a single stage can be active at a time. A stage is deemed
    complete when all the parameters in the variable list are set.

    Stage precedence and sequencing rules:
    - A stage can have parent/child stages and left/right siblings.
    - A stage cannot be its own previous stage or its own ancestor. These relationships must be fully acyclic.
    - The next stage gets activated as soon as the current stage is complete.
    - A child stage gets activated if the parent stage is completed and its guard is satisfied.
    - Only one guard must evaluate to True among the children of a parent stage.
    """

    status = UseEnum(StageStat, default_value=StageStat.INACTIVE)

    # List of stages in the order they are completed. To be used for reverting to the previous stage.
    _completed_stages = []

    # The currently active stage
    _active_stage = None

    def __init__(
        self,
        title: str,
        description: str,
        widget=None,
        varlist: list = [],
        aux_varlist: list = [],
        parent: "Stage" = None,
        hide_when_inactive=True,
        auto_proceed=True,
        auto_set_default_value=True,
        auto_set_valid_option=True,
    ):
        """Initialize a stage.

        Parameters
        ----------
        title : str
            The title of the stage.
        description : str
            The description of the stage.
        widget : optional
            The container widget to display the stage's variables
        varlist : list, optional
            The list of variables to be set in the stage.
        aux_varlist : list, optional
            The list of auxiliary variables that are not directly set by the user. These
            variables are used to track the state of the stage.
        parent : Stage, optional
            The parent stage of the stage.
        hide_when_inactive : bool, optional
            If True, hide the stage when it is disabled.
        auto_proceed : bool, optional
            If True, automatically proceed to the next stage when the stage is complete.
        auto_set_default_value : bool, optional
            If True, automatically set the default value of the variables in the stage.
            when the stage is enabled.
        auto_set_valid_option : bool, optional
            If True, automatically set the value of the variables in the stage to the
            valid option if the variable has only one valid option.
        """

        if parent is not None:  # This is a child stage, i.e., it has a parent stage
            if parent.has_children():
                assert not parent.children_have_conditions(), (
                    f"Attempted to add a child stage, {title}, to a parent stage, "
                    + f"{parent}, that has guards as children."
                )

        assert (
            widget is not None
        ), f'The "{title}" stage must have a widget.'
        assert isinstance(
            varlist, list
        ), f'The "{title}" stage must have a variable list.'
        assert (
            len(varlist) > 0
        ), f'The "{title}" stage must have a non-empty variable list.'

        super().__init__(title, parent)

        self._description = description
        self._varlist = varlist
        self._aux_varlist = aux_varlist
        self._disabled = None
        self._hide_when_inactive = hide_when_inactive
        self._auto_proceed = auto_proceed
        self._auto_set_default_value = auto_set_default_value
        self._auto_set_valid_option = auto_set_valid_option

        self._construct_observances()

        # Enable the first stage and disable the rest
        self._disabled = None
        if self.is_first():
            self._enable()
        else:
            self._disable()

        # Set the widget of the stage
        self._widget = widget
        if self._widget is not None:
            self._widget.stage = self

    @classmethod
    def reboot(cls):
        """Class method to reset the Stage class so that it can be re-initialized.
        This is useful for testing purposes and should not be utilized in production."""
        Node.reboot()
        cls._completed_stages = []
        cls._active_stage = None
        # todo: remove all instances of Stage

    @classmethod
    def active(cls):
        """Class method that returns the active stage."""
        return cls._active_stage

    @classmethod
    def proceed(cls):
        """Class method to proceed the active stage."""
        cls._active_stage._proceed()

    @property
    def description(self):
        return self._description

    @property
    def enabled(self):
        return not self._disabled

    def _construct_observances(self):
        for var in self._varlist:
            var.observe(
                self._on_value_change,
                names="value",
                type="change",
            )

    def _on_value_change(self, change):
        """This method is called when the value of a ConfigVar in the varlist changes.
        When all the ConfigVars in the varlist are set, the stage is deemed complete."""
        self.refresh_status()
        if self.enabled and self.status == StageStat.COMPLETE:
            logger.debug("Stage <%s> is complete.", self._title)
            if self._auto_proceed is True:
                self._proceed()

    def _proceed(self):
        """End this stage and move on to the next stage. This may be a child stage, the right sibling,
        or the right sibling of an ancestor stage (in that order). If no next stage is found, the stage
        tree traversal is complete."""

        self._disable()

        Stage._completed_stages.append(self)

        next_stage = self.get_next()

        if next_stage is None:
            logger.info("SUCCESS: All stages are complete.")
            return

        # Display the child stage and its siblings by appending them to the current stage's widget
        if self.has_children() and next_stage.is_descendant_of(self):
            self._widget.add_child_stages(first_child=next_stage)

        # Proceed the csp solver before enabling the next stage
        csp.proceed()

        # Enable the next stage
        next_stage._enable()

    def get_next(self, full_dfs=False):
        """Determine the next stage to visit during a stage tree traversal. Note that the next stage may
        be the first child, the right sibling, or the right sibling of the closest ancestor who has an
        unvisited right sibling.

        Parameters
        ----------
        full_dfs : bool
            If True, visit all the stages in the stage tree. Otherwise, skip stages whose guards
            are not satisfied.

        Returns
        -------
        Stage or None
            The next stage to visit, if found. Otherwise, None.
        """

        # First try to get a child stage to enable
        if (child_to_enable := self._get_child_to_enable(full_dfs)) is not None:
            return child_to_enable

        # No child stage to enable. Try to get the right sibling.
        if self._right is not None:
            return self._right

        # No child or right sibling. Backtrack to find the next stage.
        ancestor = self._parent
        while ancestor is not None:
            if ancestor._right is not None and (
                full_dfs or not ancestor.has_condition()
            ):
                return ancestor._right
            else:
                ancestor = ancestor._parent
        return None

    def _get_child_to_enable(self, full_dfs):
        """Determine the child stage to activate.

        Parameters
        ----------
        full_dfs : bool
            If True, visit all the stages in the stage tree. Otherwise, skip stages whose guards
            are not satisfied."""
        
        if self.has_children() is False:
            return None

        child_to_activate = None

        if self.children_have_conditions() and not full_dfs:
            # Children are guards. Pick the child whose condition is satisfied.
            for child in self._children:
                if child.check_condition() is True:
                    assert (
                        child_to_activate is None
                    ), "Only one child stage can be activated at a time."
                    child_to_activate = child
            
            if child_to_activate is None:
                # No child guard's condition is satisfied.
                # Let the caller handle this case (by backtracking).
                return None
        else:
            # If children are not guards, the first child is activated.
            # Note the remaining children will be activated in sequence by their siblings.
            child_to_activate = self._children[0]

        # If the child to activate is a Guard, return it's first child
        if child_to_activate.has_condition():
            child_to_activate = child_to_activate._children[0]

        return child_to_activate

    def refresh_status(self):
        """Update the status of the stage based on the disabled flag and variables being set or not."""
        some_vals_set = False
        some_vals_unset = False
        for var in self._varlist:
            if var.value is None:
                some_vals_unset = True
                if some_vals_set:
                    break
            else:
                some_vals_set = True
                if some_vals_unset:
                    break

        if some_vals_set:
            if some_vals_unset:
                self.status = (
                    StageStat.INACTIVE if self._disabled else StageStat.PARTIAL
                )
            else:
                self.status = StageStat.SEALED if self._disabled else StageStat.COMPLETE
        else:
            self.status = StageStat.INACTIVE if self._disabled else StageStat.FRESH

    def _disable(self):
        """Deactivate the stage, preventing the user from setting the parameters in the varlist."""
        logger.debug("Disabling stage %s.", self._title)
        if self._disabled is not None:
            assert (
                self._disabled is False
            ), f"Attempted to disable an already disabled stage: {self._title}"
            assert Stage._active_stage is self, "The active stage is not this stage."
            Stage._active_stage = None

        self._disabled = True
        self.refresh_status()

    @owh.out.capture()
    def _enable(self):
        """Activate the stage, allowing the user to set the parameters in the varlist."""

        logger.info("Enabling stage %s.", self._title)
        assert (
            self._disabled is not False
        ), f"Attempted to enable an already enabled stage: {self._title}"
        assert Stage._active_stage is None, "Another stage is already active."

        Stage._active_stage = self
        self._disabled = False
        self.refresh_status()

        # if the stage doesn't have any ConfigVars, it is already complete
        if len(self._varlist) == 0:
            self._proceed()

        # If a default vaulue is assigned, set the value of the ConfigVar to the default value
        # Otherwise, set the value of the ConfigVar to the valid option if there is only one.
        if self._auto_set_default_value is True:
            self.set_vars_to_defaults()
        if self._auto_set_valid_option is True:
            self.set_vars_to_single_valid_option()

    def set_vars_to_defaults(self, b=None):
        """Set the value of the ConfigVars to their default values (if valid).

        Parameters
        ----------
        b : Button, optional
            The button that triggered the setting of the default values."""

        for var in self._varlist:
            if var.value is None and (dv := var.default_value) is not None:
                try:
                    var.value = dv
                except ConstraintViolation:
                    logger.debug(
                        "The default value of the variable %s is not valid.", var.name
                    )
                    var.value = None

    def set_vars_to_single_valid_option(self):
        """Set the value of the ConfigVars to the valid option in their options list if there is only one."""
        for var in self._varlist:
            if var.value is None and var.has_options():
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
        self.reset()
        if len(Stage._completed_stages) == 0:
            logger.info("No stage to revert to.")
        else:
            previous_stage = Stage._completed_stages.pop()
            logger.info("Reverting to stage %s.", previous_stage._title)
            self._disable()
            csp.revert()
            # If the stage to enable has guards as children, remove them from the widget
            if previous_stage.has_children():
                previous_stage._widget.remove_child_stages()
            previous_stage._enable()
