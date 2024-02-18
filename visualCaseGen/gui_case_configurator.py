import logging
import ipywidgets as widgets

from ProConPy.out_handler import handler as owh
from ProConPy.config_var import cvars
from ProConPy.csp_solver import csp
from ProConPy.stage import Stage
from visualCaseGen.cime_interface import CIME_interface
from visualCaseGen.initialize_configvars import initialize_configvars
from visualCaseGen.initialize_widgets import initialize_widgets
from visualCaseGen.initialize_stages import initialize_stages
from visualCaseGen.specs.options import set_options
from visualCaseGen.specs.relational_constraints import get_relational_constraints

logger = logging.getLogger('\t'+__name__.split('.')[-1])

class GUI_case_configurator(widgets.VBox):
    
    @owh.out.capture()
    def __init__(self, b=None):

        welcome_text = widgets.HTML(value="""
                <p style='text-align:center;font-size:140%'><b><i>Welcome to visualCaseGen!</i></b></p>
                <p style='text-align:center'>
                visualCaseGen is a tool for generating custom CESM case configurations. <br>
            """, layout={'left':'-2px', 'top':'20px'}) 

        self.btn_start = widgets.Button(
            description="Start", layout={'width':'140px'})

        self.btn_start.on_click(self.start)

        self.progress_bar = widgets.IntProgress(
            value=0,
            min=0,
            max=10,
            step=1,
            description='',
            bar_style='info',
            orientation='horizontal',
            layout={'width':'300px', 'display':'none'}
        )

        super().__init__(
            children = [
                welcome_text,
                widgets.HBox([self.btn_start],
                    layout={'display':'flex','justify_content':'center', 'margin':'30px'}),
                widgets.HBox([self.progress_bar],
                    layout={'display':'flex','justify_content':'center', 'margin':'30px'}),
            ]
        )


    @owh.out.capture()
    def start(self, b):

        # disable btn_start:
        self.btn_start.disabled = True

        # Initialize progress bar:
        self.progress_bar.layout.display = 'flex'
        def pb(i=1): # increment progress bar
            self.progress_bar.value = min(10, self.progress_bar.value + i)
        pb()

        # Construct and display the case configurator:
        cime = CIME_interface() ; pb(2)
        initialize_configvars(cime) ; pb()
        initialize_widgets(cime) ; pb()
        initialize_stages(cime) ; pb()
        set_options(cime) ; pb(2)
        csp.initialize(cvars, get_relational_constraints(cvars)) ; pb(2)

        self.children = Stage.first().level_widgets()


