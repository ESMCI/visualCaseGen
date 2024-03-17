"""This module contains the StageRank class, which is used to represent the rank of a stage in an execution trace."""


class StageRank:
    """Class to represent a stage rank. Note that a lower rank represents earlier stages, and thus,
    variables with higher precedence."""


    def __init__(self, value):
        assert (
            isinstance(value, int) or value is None
        ), "value must be an integer or None"
        self._value = value

    def __eq__(self, other):
        """Return True if the value of this rank is equal to the value of the other rank. Otherwise, return False.
        Note that this custom method is necessary because comparing integers to None will raise a TypeError.
        """
        if self._value is None:
            return other._value is None
        elif other._value is None:
            return False
        else:
            return self._value == other._value

    def __lt__(self, other):
        """Compare the values of two ranks: In StageRank comparison, None is considered the highest rank."""
        if self._value is None:
            return False
        elif other._value is None:
            return True
        else:
            return self._value < other._value

    def __le__(self, other):
        return self < other or self == other

    def __ge__(self, other):
        return other <= self

    def __gt__(self, other):
        return other < self

    def is_none(self):
        """Return True if the rank is None. Otherwise, return False."""
        return self._value is None
