import logging
import ipywidgets as widgets

logger = logging.getLogger(__name__)

class GUI_preliminaries():

    def __init__(self):

        self.config_mode = widgets.ToggleButtons(
            options=['Predefined', 'Build Custom'],
            tooltips=['Select from configurations predefined within CESM.',
                      'Allows maximum flexibility. For advanced users and breakthrough applications.'],
            value="Build Custom",
            #description='mode:',
            disabled=False,
            layout = {'height':'60px','left':'-10px'}
        )
        self.config_mode.style.button_width='160px'
        self.config_mode.style.description_width = '0px'
        self.config_mode.style.font_weight = 'bold'

        self.confirm_prelim_widget = widgets.Button(
            description='Confirm',
            disabled=False,
            button_style='', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Confirm',
            icon='check',
            layout = {'width':'100px'},
        )

        self.reset_prelim_widget = widgets.Button(
            description='Reset',
            disabled=True,
            button_style='danger', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Reset',
            icon='undo',
            layout = {'width':'100px'},
        )

    def construct(self):

        hbx_basics = widgets.VBox([
            widgets.HTML(value="""
                <p style='text-align:center;font-size:140%'><b><i>Welcome to visualCaseGen!</i></b></p>
                <p style='text-align:center'>
                In <b>Predefined</b> mode, you can choose from configurations already defined in CESM.<br>
                In <b>Build Custom</b> mode, you can build your own configuration (subject to constraints).<br>
                Select your desired mode and hit <b>Confirm</b> to start creating your CESM case.</p>
            """, layout={'left':'-10px'}),
            widgets.VBox([self.config_mode], layout={'display':'flex','align_items':'center', 'margin':'10px'}),
            widgets.VBox([
                widgets.HBox([self.confirm_prelim_widget, self.reset_prelim_widget])],
                layout={'align_items':'flex-end'})
        ])
        #hbx_basics.layout.border = '2px dotted lightgray'

        return hbx_basics
