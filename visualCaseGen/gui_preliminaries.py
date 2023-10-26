import logging
import ipywidgets as widgets

logger = logging.getLogger(__name__)

class GUI_preliminaries():

    def __init__(self):

        self.btn_predefined = widgets.Button(
            description = 'Predefined',
            tooltip = 'Select from configurations predefined within CESM.'
        )
        self.btn_custom = widgets.Button(
            description = 'Custom',
            tooltip = 'Allows maximum flexibility. For advanced users and breakthrough applications.'
        )

    def construct(self):

        hbx_basics = widgets.VBox([
            widgets.HTML(value="""
                <p style='text-align:center;font-size:140%'><b><i>Welcome to visualCaseGen!</i></b></p>
                <p style='text-align:center'>
                Select your desired configuration mode below to start creating your CESM case. <br>
                <b>Predefined</b>: Select from predefined CESM component sets and grids. <br>
                <b>Custom</b>: Create custom component sets and grids.<br></p>
            """, layout={'left':'-10px', 'top':'20px'}),
            widgets.VBox([
                widgets.HBox([self.btn_predefined, self.btn_custom])],
                layout={'display':'flex','align_items':'center', 'margin':'30px'}),
        ])
        #hbx_basics.layout.border = '2px dotted lightgray'

        return hbx_basics
