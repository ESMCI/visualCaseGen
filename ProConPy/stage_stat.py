"""This module contains the StageStat enumeration to represent the status of a stage based whether the 
stage is enabled and whether the variables set or not."""
import enum


class StageStat(enum.Enum):
    """An enumeration to represent the status of a stage based whether the stage is enabled and
    whether the variables set or not."""

    INACTIVE = 0 # The stage is not activated yet. Some variables may be set to values.
    FRESH = 1 # The stage is active. No variables have been set to values.
    PARTIAL = 2 # The stage is active. Some but not all variables have been set.
    COMPLETE = 3 # The stage is active. All variables have been set, or no variables are in the stage. 
    SEALED = 4 # The completed stage is sealed (disabled). All variables have been set, or no variables are in the stage.

