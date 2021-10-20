import logging
import ipywidgets as widgets

from visualCaseGen.visualCaseGen import OutHandler
from visualCaseGen.visualCaseGen.OutHandler import handler as owh
from visualCaseGen.visualCaseGen.config_var import ConfigVar
from visualCaseGen.visualCaseGen.cime_interface import CIME_interface
from visualCaseGen.visualCaseGen.gui_create_custom import GUI_create_custom
from visualCaseGen.visualCaseGen.gui_create_predefined import GUI_create_predefined
from visualCaseGen.visualCaseGen.gui_preliminaries import GUI_preliminaries
from visualCaseGen.visualCaseGen.header_widget import HeaderWidget

logger = logging.getLogger(__name__)

class GUI():

    def construct_tab_observances(self):
        """ Construct links between tabs: (1) Preliminaries, (2) Create Case, ...
        """

        @owh.out.capture()
        def confirm_prelim_clicked(b):

            loadbar = widgets.FloatProgress(
                value=0.0,
                min=0,
                max=10.0,
                description='Loading',
                bar_style='info',
                style={'bar_color': '#00ff00'},
                orientation='horizontal'
            )

            self.create_tab.children = [loadbar,]
            self.main_dialog.selected_index=1
            self.prelim_tab.driver_widget.disabled = True
            self.prelim_tab.config_mode.disabled = True
            self.prelim_tab.confirm_prelim_widget.disabled = True
            self.prelim_tab.reset_prelim_widget.disabled = False
            ConfigVar.reset()

            driver = self.prelim_tab.driver_widget.value
            config_mode = self.prelim_tab.config_mode.value

            if config_mode=='predefined':
                ci = CIME_interface(driver, loadbar)
                self.create_tab.children = (GUI_create_predefined(ci).construct(),)
            elif config_mode=='custom':
                ci = CIME_interface(driver, loadbar)
                self.create_tab.children = (GUI_create_custom(ci).construct(),)
        self.prelim_tab.confirm_prelim_widget.on_click(confirm_prelim_clicked)

        def reset_prelim_clicked(b):
            self.prelim_tab.driver_widget.disabled = False
            self.prelim_tab.config_mode.disabled = False
            self.prelim_tab.confirm_prelim_widget.disabled = False
            self.prelim_tab.reset_prelim_widget.disabled = True
            self.create_tab.children = (widgets.Label("Confirm preliminaries first."),)
            ConfigVar.reset()
        self.prelim_tab.reset_prelim_widget.on_click(reset_prelim_clicked)

    def help_tab_construct(self):
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
        self.verbose_widget.observe(self.on_verbose_change)

        self.clear_log_button = widgets.Button(
            description='Clear Log',
            disabled=False,
            button_style='warning',
            icon='broom',
            layout = {'width':'100px'}
        )

        def clear_log(b):
            OutHandler.handler.out.clear_output()
        self.clear_log_button.on_click(clear_log)

        return widgets.VBox([
            widgets.Label("To report a bug or to request help:"),
            widgets.Label(" (1) Turn on verbose logging below and start over."),
            widgets.Label(" (2) Repeat the steps that led to the error."),
            widgets.Label(" (3) Send the description of the eror with the generated log below to: altuntas@ucar.edu"),
            HeaderWidget("Logs:"),
            widgets.VBox([
                widgets.HBox([self.verbose_widget, self.clear_log_button])]
                ,layout={'align_items':'flex-end'}),
            OutHandler.handler.out
        ])

    @owh.out.capture()
    def on_verbose_change(self, change):
        if change['type'] == 'change' and change['name'] == 'value':
            new_verbose = change['new']
            OutHandler.handler.out.clear_output()
            if new_verbose=='On (slow)':
                logger.info("Verbose Mode On")
                logging.getLogger().setLevel(logging.DEBUG)
            elif new_verbose=='Off':
                logger.info("Verbose Mode Off")
                logging.getLogger().setLevel(logging.INFO)


    @owh.out.capture()
    def display(self):

        logger.info("Displaying visualCaseGen GUI")

        self.prelim_tab = GUI_preliminaries()
        self.create_tab = widgets.HBox()
        self.create_tab.children = (widgets.Label("Confirm preliminaries first."),)

        self.main_dialog = widgets.Accordion(children=[
            self.prelim_tab.construct(),
            self.create_tab,
            self.help_tab_construct()]
        )
        self.main_dialog.set_title(0,'Step 1: Preliminaries')
        self.main_dialog.set_title(1,'Step 2: Create Case')
        self.main_dialog.set_title(2,'Help')

        self.construct_tab_observances()

        return self.main_dialog
