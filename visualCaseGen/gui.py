import logging
import ipywidgets as widgets

from visualCaseGen.OutHandler import handler as owh
from visualCaseGen.cime_interface import CIME_interface
from visualCaseGen.gui_create_custom import GUI_create_custom
from visualCaseGen.gui_create_predefined import GUI_create_predefined
from visualCaseGen.gui_preliminaries import GUI_preliminaries
from visualCaseGen.header_widget import HeaderWidget

logger = logging.getLogger(__name__)

class GUI(widgets.VBox):

    @owh.out.capture()
    def on_mode_selection(self, b):
        """This is called when either Predefined or Custom mode is selected."""

        loadbar = widgets.FloatProgress(
            value=0.0,
            min=0,
            max=10.0,
            description='Loading',
            bar_style='info',
            style={'bar_color': '#00ff00'},
            orientation='horizontal'
        )

        self.children = [loadbar,]

        ci = CIME_interface("nuopc", loadbar)
        if b.description == "Predefined":
            self.header.value = "<p style='font-size:120%'><b><font color='dimgrey'>{}</b></p>".format("visualCaseGen - Predefined Mode")
            self.create_case_dialog = [self.menubar, GUI_create_predefined(ci).construct(),]
        elif b.description == "Custom":
            self.header.value = "<p style='font-size:120%'><b><font color='dimgrey'>{}</b></p>".format("visualCaseGen - Custom Mode")
            self.create_case_dialog = [self.menubar, GUI_create_custom(ci).construct(),]
        
        self.children = self.create_case_dialog

    def on_reset_click(self, b):
        """Called when the reset button is clicked"""
        self.children = [self.welcome_dialog.construct(),]

    def on_help_click(self, b):
        self.children = [
            widgets.HBox([HeaderWidget(value='Help'), self.btn_return]
                ,layout={'display':'flex', 'justify_content':'space-between'}),
            self.help_description,
            widgets.HBox([self.verbose_widget, self.btn_clear_log]
                ,layout={'display':'flex', 'justify_content':'flex-end'}),
            owh.out
        ]
    
    def on_return_click(self, b):
        if self.create_case_dialog is not None:
            self.children = self.create_case_dialog
        else:
            self.children = [self.welcome_dialog.construct(),] 

    @owh.out.capture()
    def on_verbose_change(self, change):
        if change['type'] == 'change' and change['name'] == 'value':
            new_verbose = change['new']
            owh.out.clear_output()
            if new_verbose=='On (slow)':
                logger.info("Verbose Mode On")
                logging.getLogger().setLevel(logging.DEBUG)
            elif new_verbose=='Off':
                logger.info("Verbose Mode Off")
                logging.getLogger().setLevel(logging.INFO)

    def clear_log(self, b):
        owh.out.clear_output()

    def construct_observances(self):
        self.welcome_dialog.btn_predefined.on_click(self.on_mode_selection)
        self.welcome_dialog.btn_custom.on_click(self.on_mode_selection)
        self.btn_reset.on_click(self.on_reset_click)
        self.btn_help.on_click(self.on_help_click)
        self.btn_return.on_click(self.on_return_click)
        self.verbose_widget.observe(self.on_verbose_change)
        self.btn_clear_log.on_click(self.clear_log)


    def init_menubar_widgets(self):

        self.header = widgets.HTML('<b>visualCaseGen</b>')

        self.btn_help = widgets.Button(
            description='Help',
            button_style='info',
            icon='bug',
            layout = {'width':'100px'},
        )

        self.btn_reset = widgets.Button(
            description='Reset',
            button_style='danger', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Reset',
            icon='undo',
            layout = {'width':'100px'},
        )

        self.menubar = widgets.HBox([
                self.header,
                widgets.HBox([self.btn_help, self.btn_reset,])
        ], layout={'display':'flex', 'justify_content':'space-between'})
    
    def init_help_dialog_widgets(self):

        self.btn_return = widgets.Button(
            description='Return',
            disabled=False,
            button_style='danger',
            icon='chevron-left',
            layout = {'width':'100px'}
        ) 

        self.verbose_widget = widgets.Dropdown(
            options=['On (slow)', 'Off'],
            tooltips=['Turn on the verbose GUI logging. This significantly slows down the GUI.',
                      '(Default) Minimal logging. This improves the responsiveness of the GUI.'],
            value='Off',
            layout={'width': 'max-content'}, # If the items' names are long
            description='Verbose GUI log:',
            disabled=False
        )
        self.verbose_widget.style.description_width = '150px'

        self.btn_clear_log = widgets.Button(
            description='Clear Log',
            disabled=False,
            button_style='warning',
            icon='broom',
            layout = {'width':'100px'}
        )

        self.help_description = widgets.HTML(value = """
        For bug reporting or assistance requests, please send an email to altuntas@ucar.edu<br>
        with a description of the error or issue and include the log messages provided below.
            """
        )

    @owh.out.capture()
    def __init__(self):

        logger.info("Displaying visualCaseGen GUI")

        self.welcome_dialog = GUI_preliminaries()
        self.create_case_dialog = None
        self.init_menubar_widgets()
        self.init_help_dialog_widgets()

        super().__init__(children = [self.welcome_dialog.construct()], 
                         layout={'border':'1px solid lightgray', 'width':'830px', 'padding':'10px'})

        self.construct_observances()
