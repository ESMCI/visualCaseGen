import logging
import ipywidgets as widgets

from visualCaseGen.config_var import cvars
from visualCaseGen.custom_ocn_grid_widget import CustomOcnGridWidget
from visualCaseGen.custom_lnd_grid_widget import CustomLndGridWidget
from visualCaseGen.OutHandler import handler as owh

logger = logging.getLogger(__name__)

button_width = '100px'
descr_width = '140px'

class CustomGridWidget(widgets.Tab):

    def __init__(self,ci,layout=widgets.Layout()):

        super().__init__(layout=layout)

        self.ci = ci

        self.description = widgets.HTML(
            "<p style='text-align:left'>In custom grid mode, you can "
            "create new grids for the ocean and/or the land components "
            "by setting the below configuration variables. After having "
            "set all the variables, you can save grid configuration "
            "files to be read in by subsequent tools to further "
            "customize and complete the grids.</p>"
        )

        self._custom_ocn_grid= CustomOcnGridWidget(self.ci)
        self._custom_lnd_grid= CustomLndGridWidget(self.ci)

        self.horiz_line = widgets.HTML('<hr>')

        self.construct_observances()
        self.layout.width = '750px'

        self.turn_off() # by default, the display is off.
        self.refresh_display()

    def refresh_display(self, change=None):

        ocn = cvars['COMP_OCN'].value
        lnd = cvars['COMP_LND'].value

        # first determine how to align items
        if ocn is None or lnd is None:
            self.layout.align_items = 'center'
        else:
            self.layout.align_items = None

        # now, determine what items to display
        if ocn is None and lnd is None:
            self.children = [widgets.Label("(Custom grid dialogs will appear here after both the OCN and LND components are determined.)")]
        elif ocn is None:
            self.children = [widgets.Label("(Custom grid dialogs will be displayed here after the OCN component is determined.)")]
        elif lnd is None:
            self.children = [widgets.Label("(Custom grid dialogs will be displayed here after the LND component is determined.)")]
        else: # both ocean and lnd is determined.

            self._custom_ocn_grid.reset_vars()
            self._custom_lnd_grid.reset_vars()

            tabs = []

            # construct the ocean grid section layout
            if ocn == "mom":
                self._custom_ocn_grid.construct()
                tabs.append((self._custom_ocn_grid.title, self._custom_ocn_grid))
            
            if lnd == 'clm':
                self._custom_lnd_grid.construct()
                tabs.append((self._custom_lnd_grid.title, self._custom_lnd_grid))

            self.children = [tab[1] for tab in tabs]
            for i, tab in enumerate(tabs):
                self.set_title(i,tab[0])

    def construct_observances(self):

        cv_comp_ocn = cvars['COMP_OCN']
        cv_comp_ocn.observe(
            self.refresh_display,
            names='value',
            type='change'
        )

        cv_comp_lnd = cvars['COMP_LND']
        cv_comp_lnd.observe(
            self.refresh_display,
            names='value',
            type='change'
        )

    def turn_off(self):
        self.layout.display = 'none'
        self._custom_ocn_grid.reset_vars()
        self._custom_lnd_grid.reset_vars()

    def turn_on(self):
        self.layout.display = ''
