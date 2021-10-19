import ipywidgets as widgets

class HeaderWidget(widgets.HTML):
    def __init__(self, value):
        super().__init__(
            "<p style='font-size:110%; margin-top:1em'><b><font color='dimgrey'>{}</b></p>".format(value)
        )