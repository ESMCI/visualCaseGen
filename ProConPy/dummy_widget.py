""" A module for Dummy Display items (Widget and Layout) to be used as placeholders until real
items are ready and assigned."""

from traitlets import HasTraits, Any


class DummyWidget(HasTraits):
    """A dummy class to be used as a placeholder. By default, all ConfigVar widgets are set to
    a DummyWidget instance at initialization. A ConfigVar widget is typically reassigned to an
    actual widget when it is ready.
    """

    value = Any()
    options = Any(
        (),
        help="Iterable of values, (label, value) pairs, or a mapping of {label: value} pairs "
        "that the user can select.",
    )

    def __init__(self, value=None, options=None, description="DummyWidget"):
        self.description = description
        self.set_trait("value", value)
        if options:
            self.set_trait("options", options)
        self.layout = DummyLayout()
        self.tooltips = ()


class DummyLayout:
    """A dummy layout class to be used within DummyWidget."""

    def __init__(self):
        self.visibility = "hidden"
