import logging
import ipywidgets as widgets

from ProConPy.out_handler import handler as owh
from visualCaseGen.gui_case_configurator import GUI_case_configurator
from visualCaseGen.gui_help_dialog import GUI_help_dialog

logger = logging.getLogger('\t'+__name__.split('.')[-1])

class GUI(widgets.VBox):
    """The main GUI class. This class contains two components:
         1. menubar: title, help button, reset button, return button
         2. main body: at startup, the main body is the case configuration wizard. if the user
            clicks the help button on menubar, the main body switches to the help dialog."""
    
    @owh.out.capture()
    def __init__(self):
        logger.info("Constructing visualCaseGen GUI")

        self.construct_menubar_widgets()
        self.construct_main_body()

        super().__init__(
            children = [
                self.menubar,
                self.main_body
            ],
            layout = {'border':'1px solid lightgray', 'width':'830px', 'padding':'10px', 'display':'flex'}
        )

    def construct_menubar_widgets(self):

        self.header = widgets.HTML(
            value = "<p style='font-size:120%'><b><font color='dimgrey'>{}</b></p>".format("visualCaseGen")
        )

        self.btn_help = widgets.Button(
            description='Help',
            button_style='info',
            icon='bug',
            layout = {'width':'100px'},
        )
        self.btn_help.on_click(self.on_help_click)

        self.btn_reset = widgets.Button(
            description='Reset',
            button_style='danger', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Reset',
            icon='undo',
            layout = {'width':'100px', 'display':'none'},
        )

        self.btn_return = widgets.Button(
            description='Return',
            disabled=False,
            button_style='danger',
            icon='chevron-left',
            layout = {'width':'100px', 'display':'none'}
        ) 
        self.btn_return.on_click(self.on_return_click)

        self.menubar = widgets.HBox(
            children = [
                self.header,
                widgets.HBox([self.btn_help, self.btn_reset, self.btn_return])
            ], 
            layout={'display':'flex', 'justify_content':'space-between'})

    def on_help_click(self, b):
        # switch to help dialog
        self.help_body.layout.display = 'flex'
        self.case_config_body.layout.display = 'none'
        # In menubar, hide help and reset buttons. Instead, show return button.
        self.btn_help.layout.display = 'none'
        self.btn_reset.layout.display = 'none'
        self.btn_return.layout.display = ''

    
    def on_return_click(self, b):
        # switch to case configurator dialog
        self.help_body.layout.display = 'none'
        self.case_config_body.layout.display = 'flex'
        # In menubar, hide return button. Instead, show help and reset buttons.
        self.btn_return.layout.display = 'none'
        self.btn_help.layout.display = ''
        self.btn_reset.layout.display = ''

    def construct_main_body(self):
        self.case_config_body = GUI_case_configurator()
        self.help_body = GUI_help_dialog()

        self.main_body = widgets.VBox(
            children = [
                self.case_config_body,
                self.help_body
            ],
        )