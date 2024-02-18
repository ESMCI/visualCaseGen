from z3 import BoolRef
from inspect import signature

class OptionsSpec:

    def __init__(
        self,
        func,
        args = None,
        static_options_expr = None,
    ):
        """
        OptionsSpec is a class to specify the options and tooltips of a config_var.

        Parameters
        ----------
        func : callable
            function to get options and tooltips. The function must return a tuple of two lists.
            The first list is the options, and the second list is the tooltips.
        args : list of configvars
            arguments to pass to func. All arguments must be config_vars. Each time one of these config_vars
            changes, func will be called with the values of these config_vars as arguments.
        static_options_expr : z3.BoolRef
            z3 expression to specify the variable options in static mode. This constaint has no impact in dynamic
            mode, and is only used when static analysis is carried out. To carry out accurate static analysis,
            developrs must ensure that this expression is consistent with the options returned by func. This is 
            used to ensure that the options constraints are properly accounted for when doing static analysis.
            (n dynamic mode, the optinons constraints are automatically set. )
        """

        assert callable(func), "func must be callable"
        self._func = func

        if len(signature(self._func).parameters) > 0:
            assert args is not None, "Must provide args if func has arguments."

        if args is not None:
            assert isinstance(args, (list, tuple)), "args must be a list or tuple"
            assert len(signature(self._func).parameters) == len(args), "func must have the same number of arguments as args"
            self._args = args

            #todo assert static_options_expr is not None, "Must provide static_options_expr if func has arguments."\
            #todo     "This ensures that the options constraints are properly accounted for when doing static analysis."
            #todo assert isinstance(static_options_expr, BoolRef), "static_options_expr must be a z3.BoolRef."
            #todo self._static_options_constraint = static_options_expr
        

    def __call__(self):
        """ Call the function with the current values of the arguments"""

        if any([arg.value is None for arg in self._args]):
            return None, None

        options, tooltips = self._func(*[arg.value for arg in self._args])

        # options must be a list of tuple
        assert isinstance(options, (list, tuple)), "options must be a list or tuple"

        if tooltips is not None:
            assert isinstance(tooltips, (list, tuple)), "tooltips must be a list or tuple"
            #todo:uncomment assert len(options) == len(tooltips), "options and tooltips must have the same length"
        
        return options, tooltips
        
