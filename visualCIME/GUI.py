import os, sys, re
import ipywidgets as widgets

from visualCIME.visualCIME import OutHandler
from visualCIME.visualCIME.ConfigVar import ConfigVar
from visualCIME.visualCIME.CIME_interface import CIME_interface
from visualCIME.visualCIME.GUI_create_advanced import GUI_create_advanced
from visualCIME.visualCIME.GUI_create_novice import GUI_create_novice
from visualCIME.visualCIME.GUI_preliminaries import GUI_preliminaries

import logging
logger = logging.getLogger(__name__)

class GUI():

    def construct_tab_observances(self):

        def confirm_prelim_clicked(b):
            self.create_tab.children = [widgets.Label("Loading..."),]
            self.vCIME.selected_index=1
            self.prelim_tab.driver_widget.disabled = True
            self.prelim_tab.support_widget.disabled = True
            self.prelim_tab.confirm_prelim_widget.disabled = True
            self.prelim_tab.reset_prelim_widget.disabled = False
            ConfigVar.reset()

            driver = self.prelim_tab.driver_widget.value
            support = self.prelim_tab.support_widget.value

            if support=='scientific':
                ci = CIME_interface()
                w = GUI_create_novice(ci)
                self.create_tab.children = [w.construct(),]
            elif support=='unsupported':
                ci = CIME_interface()
                w = GUI_create_advanced(ci)
                self.create_tab.children = [w.construct(),]
        self.prelim_tab.confirm_prelim_widget.on_click(confirm_prelim_clicked)

        def reset_prelim_clicked(b):
            self.prelim_tab.driver_widget.disabled = False
            self.prelim_tab.support_widget.disabled = False
            self.prelim_tab.confirm_prelim_widget.disabled = False
            self.prelim_tab.reset_prelim_widget.disabled = True
            self.create_tab.children = (widgets.Label("Confirm preliminaries first."),)
            ConfigVar.reset()
        self.prelim_tab.reset_prelim_widget.on_click(reset_prelim_clicked)



    def display(self):

        self.prelim_tab = GUI_preliminaries()
        self.create_tab = widgets.HBox()
        self.create_tab.children = (widgets.Label("Confirm preliminaries first."),)

        self.vCIME = widgets.Accordion(
            children=[self.prelim_tab.construct(), self.create_tab]
        )
        self.vCIME.set_title(0,'Step 1: Preliminaries')
        self.vCIME.set_title(1,'Step 2: Create Case')

        self.construct_tab_observances()

        return self.vCIME

