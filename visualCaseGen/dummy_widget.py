class DummyWidget():
    """A dummy class to be used as a placeholder. By default, all ConfigVar widgets are set to a DummyWidget instance
    at initialization. A ConfigVar widget is typically reassigned to an actual widget when it is ready."""

    def __init__(self, value=None, options=None, description="DummyWidget"):
        self.value = value
        self.options = options
        self.description = description

    def observe(*args, **kwargs):
        """A dummy observe method that does nothing. Used as a placeholder"""
        pass
