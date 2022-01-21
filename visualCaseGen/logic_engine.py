from z3 import And, Or, Implies

# Auxiliary definitions of logic expression shorthands
def In(var, value_list):
    """Expression to check whether the value of a variable is in a given list."""
    return Or([var==value for value in value_list])