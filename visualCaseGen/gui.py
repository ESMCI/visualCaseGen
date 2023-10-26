import logging
import ipywidgets as widgets

from visualCaseGen.OutHandler import handler as owh
from visualCaseGen.cime_interface import CIME_interface
from visualCaseGen.gui_create_custom import GUI_create_custom
from visualCaseGen.gui_create_predefined import GUI_create_predefined
from visualCaseGen.header_widget import HeaderWidget

logger = logging.getLogger(__name__)

class GUI(widgets.VBox):

    @owh.out.capture()
    def __init__(self):

        logger.info("Displaying visualCaseGen GUI")

        self.menubar = self.construct_menubar()
        self.welcome = self.construct_welcome_widgets()
        self.create_case = widgets.HBox(layout={'display':'none'})
        self.help = self.construct_help_widgets()

        super().__init__(children = [
            self.menubar,
            self.welcome,
            self.create_case,
            self.help
        ],   
        layout={'border':'1px solid lightgray', 'width':'830px', 'padding':'10px'})

        self.construct_observances()


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

        # hide
        self.welcome.layout.display = 'none'
        self.help.layout.display = 'none'
        # show
        self.menubar.layout.display = ''
        self.create_case.children = [loadbar,]; self.create_case.layout.display = ''

        ci = CIME_interface("nuopc", loadbar)
        if b.description == "Predefined":
            self.header.value = "<p style='font-size:120%'><b><font color='dimgrey'>{}</b></p>".format("visualCaseGen - Predefined Mode")
            self.create_case.children = [GUI_create_predefined(ci).construct(),]
        elif b.description == "Custom":
            self.header.value = "<p style='font-size:120%'><b><font color='dimgrey'>{}</b></p>".format("visualCaseGen - Custom Mode")
            self.create_case.children = [GUI_create_custom(ci).construct(),]

    def on_reset_click(self, b):
        """Called when the reset button is clicked"""
        # hide
        self.create_case.children = []; self.create_case.layout.display = 'none'
        self.help.layout.display = 'none'
        # show
        self.menubar.layout.display = ''
        self.welcome.layout.display = ''

    def on_help_click(self, b):
        # hide
        self.menubar.layout.display = 'none'
        self.welcome.layout.display = 'none'
        self.create_case.layout.display = 'none'
        # show
        self.help.layout.display = ''
    
    def on_return_click(self, b):
        if len(self.create_case.children)>0:
            # hide
            self.welcome.layout.display = 'none'
            self.help.layout.display = 'none'
            # show
            self.menubar.layout.display = ''
            self.create_case.layout.display = ''
        else:
            # hide
            self.create_case.layout.display = 'none'
            self.help.layout.display = 'none'
            # show
            self.menubar.layout.display = ''
            self.welcome.layout.display = ''

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
        self.btn_predefined.on_click(self.on_mode_selection)
        self.btn_custom.on_click(self.on_mode_selection)
        self.btn_reset.on_click(self.on_reset_click)
        self.btn_help.on_click(self.on_help_click)
        self.btn_return.on_click(self.on_return_click)
        self.verbose_widget.observe(self.on_verbose_change)
        self.btn_clear_log.on_click(self.clear_log)


    def construct_menubar(self):

        self.header = widgets.HTML(
            value = "<p style='font-size:120%'><b><font color='dimgrey'>{}</b></p>".format("visualCaseGen")
        )

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

        return widgets.HBox([
                self.header,
                widgets.HBox([self.btn_help, self.btn_reset,])
        ], layout={'display':'flex', 'justify_content':'space-between'})
    
    def construct_welcome_widgets(self):

        self.btn_predefined = widgets.Button(
            description = 'Predefined',
            tooltip = 'Select from configurations predefined within CESM.'
        )
        self.btn_custom = widgets.Button(
            description = 'Custom',
            tooltip = 'Allows maximum flexibility. For advanced users and breakthrough applications.'
        )
        welcome_text = widgets.HTML(value="""
                <p style='text-align:center;font-size:140%'><b><i>Welcome to visualCaseGen!</i></b></p>
                <p style='text-align:center'>
                Select your desired configuration mode below to start creating your CESM case. <br>
                <b>Predefined</b>: Select from predefined CESM component sets and grids. <br>
                <b>Custom</b>: Create custom component sets and grids.<br></p>
            """, layout={'left':'-10px', 'top':'20px'}) 
        
        return widgets.VBox([
            welcome_text,
            widgets.HBox([self.btn_predefined, self.btn_custom],
                layout={'display':'flex','justify_content':'center', 'margin':'30px'})
        ])
    
    def construct_help_widgets(self):

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

        help_description = widgets.HTML(value = """
        For bug reporting or assistance requests, please submit a GitHub issue with a<br>
        detailed description of the problem and include the log messages provided below.<br>
        <a href="https://github.com/ESMCI/visualCaseGen/issues/new" target="_blank" rel="noreferrer noopener"><u>Submit an issue</u></a> <br>
         """
        )

        return widgets.VBox([
                widgets.HBox([HeaderWidget(value='Help'), self.btn_return]
                    ,layout={'display':'flex', 'justify_content':'space-between'}),
                help_description,
                widgets.HBox([self.verbose_widget, self.btn_clear_log]
                    ,layout={'display':'flex', 'justify_content':'flex-end'}),
                owh.out ],
            layout={'display':'none'})


