import logging
import ipywidgets as widgets

logger = logging.getLogger('\t'+__name__.split('.')[-1])

from ProConPy.out_handler import handler as owh

class GUI_help_dialog(widgets.VBox):
    
    def __init__(self):

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
        <a href="https://github.com/ESMCI/visualCaseGen/issues/new" target="_blank" rel="noreferrer noopener"><u><b>Submit an issue</b></u></a> <br>
         """
        )

        super().__init__(
            children = [
                help_description,
                widgets.HBox([self.verbose_widget, self.btn_clear_log]
                    ,layout={'display':'flex', 'justify_content':'flex-end'}),
                owh.out ],
                layout = {'display':'none'}
        )

        self.construct_observances()

    def construct_observances(self):
        self.verbose_widget.observe(self.on_verbose_change)
        self.btn_clear_log.on_click(self.clear_log)

    @owh.out.capture()
    def on_verbose_change(self, change):
        if change['type'] == 'change' and change['name'] == 'value':
            new_verbose = change['new']
            owh.out.clear_output()
            if new_verbose=='On (slow)':
                logger.info("Verbose Mode On")
                owh.set_verbosity(verbose=True)
            elif new_verbose=='Off':
                logger.info("Verbose Mode Off")
                owh.set_verbosity(verbose=False)

    def clear_log(self, b):
        owh.out.clear_output()