import logging
import ipywidgets as widgets

from visualCaseGen.config_var import cvars
from visualCaseGen.custom_atm_grid_widget import CustomAtmGridWidget
from visualCaseGen.custom_ocn_grid_widget import CustomOcnGridWidget
from visualCaseGen.custom_lnd_grid_widget import CustomLndGridWidget
from visualCaseGen.OutHandler import handler as owh

logger = logging.getLogger(__name__)

button_width = '100px'
descr_width = '140px'

class CustomGridWidget(widgets.Tab):

    def __init__(self,session_id,ci,sdb,layout=widgets.Layout()):

        super().__init__(layout=layout)

        self.session_id = session_id
        self.ci = ci

        self.description = widgets.HTML(
            "<p style='text-align:left'>In custom grid mode, you can "
            "create new grids for the ocean and/or the land components "
            "by setting the below configuration variables. After having "
            "set all the variables, you can save grid configuration "
            "files to be read in by subsequent tools to further "
            "customize and complete the grids.</p>"
        )

        self._custom_atm_grid= CustomAtmGridWidget(self.ci)
        self._custom_ocn_grid= CustomOcnGridWidget(session_id, self.ci)
        self._custom_lnd_grid= CustomLndGridWidget(self.ci, sdb)

        self.horiz_line = widgets.HTML('<hr>')

        self.construct_observances()
        self.layout.width = '750px'

        self.turn_off() # by default, the display is off.
        self.refresh_display()

    def refresh_display(self, change=None):

        atm = cvars['COMP_ATM'].value
        ocn = cvars['COMP_OCN'].value
        lnd = cvars['COMP_LND'].value
        ice = cvars['COMP_ICE'].value

        # determine if ready to turn on custom grid dialog:
        if any([comp is None for comp in [atm, ocn, lnd, ice]]):
            self.layout.align_items = 'center'
            self.children = [widgets.Label("(All of the following components must be set before configuring the custom grid: ATM, OCN, LND, ICE)")]

        else: # atm, ocn, lnd, and ice are set by the user.
            self._custom_lnd_grid.reset_vars()
            tabs = []

            if atm in ["cam", "datm"]:
                self._custom_atm_grid.construct()
                tabs.append((self._custom_atm_grid.title, self._custom_atm_grid))
            
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

        cv_comp_atm = cvars['COMP_ATM']
        cv_comp_atm.observe(
            self.refresh_display,
            names='value',
            type='change'
        )

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

        cv_comp_ice = cvars['COMP_ICE']
        cv_comp_ice.observe(
            self.refresh_display,
            names='value',
            type='change'
        )

    def turn_off(self):
        self.layout.display = 'none'
        self._custom_atm_grid.reset_vars()
        self._custom_ocn_grid.reset_vars()
        self._custom_lnd_grid.reset_vars()

    def turn_on(self):
        self.layout.display = ''
