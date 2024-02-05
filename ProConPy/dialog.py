"""A module consisting of functions to display error and warning messages."""

# TODO: this is a ProConPy module and so should not have IPython (Jupyter) dependency
from IPython.display import display, HTML


def alert_warning(msg):
    """Display a warning message.

    Parameters:
    -----------
    msg : str
        Warning message to be displayed
    """

    js = f"""<script>alert("WARNING: {msg} ");</script>"""
    display(HTML(js))


def alert_error(msg):
    """Display an error message.

    Parameters:
    -----------
    msg : str
        Error message to be displayed
    """

    js = f"<script>alert('ERROR: {msg}');</script>"
    display(HTML(js))
