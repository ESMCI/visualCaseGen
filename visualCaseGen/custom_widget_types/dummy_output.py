class DummyOutput:
    """ A dummy class to replace the Output widget for when utilizing visualCaseGen as a backend library.
    When this class is used, the print statements will be displayed in the console instead of dedicated
    output widgets."""

    def __init__(self, *args, **kwargs):
        pass

    def clear_output(self):
        pass

    def __enter__(self):
        pass

    def __exit__(self, *args):
        pass
