import os, sys, re
import ipywidgets as widgets

from visualCIME.visualCIME import OutHandler
from visualCIME.visualCIME.OutHandler import handler as owh
from visualCIME.visualCIME.ConfigVar import ConfigVar
from visualCIME.visualCIME.CIME_interface import CIME_interface
from visualCIME.visualCIME.GUI_create_advanced import GUI_create_advanced
from visualCIME.visualCIME.GUI_create_novice import GUI_create_novice
from visualCIME.visualCIME.GUI_preliminaries import GUI_preliminaries

import logging
logger = logging.getLogger(__name__)

class GUI():

    def construct_tab_observances(self):

        @owh.out.capture()
        def confirm_prelim_clicked(b):
            self.create_tab.children = [widgets.Label("Loading..."),]
            self.vCIME.selected_index=1
            self.prelim_tab.driver_widget.disabled = True
            self.prelim_tab.support_widget.disabled = True
            self.prelim_tab.debug_widget.disabled = True
            self.prelim_tab.confirm_prelim_widget.disabled = True
            self.prelim_tab.reset_prelim_widget.disabled = False
            ConfigVar.reset()

            driver = self.prelim_tab.driver_widget.value
            support = self.prelim_tab.support_widget.value
            debug = self.prelim_tab.debug_widget.value

            OutHandler.handler.out.clear_output()
            if debug=='On (slow)':
                logger.info("Debug Mode On")
                logging.getLogger().setLevel(logging.DEBUG)
            elif debug=='Off':
                logger.info("Debug Mode Off")
                logging.getLogger().setLevel(logging.INFO)

            if support=='scientific':
                ci = CIME_interface(driver)
                w = GUI_create_novice(ci)
                self.create_tab.children = [w.construct(),]
            elif support=='unsupported':
                ci = CIME_interface(driver)
                w = GUI_create_advanced(ci)
                self.create_tab.children = [w.construct(),]
        self.prelim_tab.confirm_prelim_widget.on_click(confirm_prelim_clicked)

        def reset_prelim_clicked(b):
            self.prelim_tab.driver_widget.disabled = False
            self.prelim_tab.support_widget.disabled = False
            self.prelim_tab.debug_widget.disabled = False
            self.prelim_tab.confirm_prelim_widget.disabled = False
            self.prelim_tab.reset_prelim_widget.disabled = True
            self.create_tab.children = (widgets.Label("Confirm preliminaries first."),)
            ConfigVar.reset()
        self.prelim_tab.reset_prelim_widget.on_click(reset_prelim_clicked)

    def help_tab_construct(self):
        return widgets.VBox([
            widgets.Label("To report a bug or to request help:"),
            widgets.Label(" (1) Start over and turn on the debug mode (slow)"),
            widgets.Label(" (2) Repeat the steps that led to the error."),
            widgets.Label(" (3) Send the description of the eror with the generated log below to: altuntas@ucar.edu"),
            widgets.Label("Logs:"),
            OutHandler.handler.out
        ])

    @owh.out.capture()
    def display(self):

        logger.info("Displaying vCIME GUI")

        self.prelim_tab = GUI_preliminaries()
        self.create_tab = widgets.HBox()
        self.create_tab.children = (widgets.Label("Confirm preliminaries first."),)

        self.vCIME = widgets.Accordion(children=[
            self.prelim_tab.construct(),
            self.create_tab,
            self.help_tab_construct()]
        )
        self.vCIME.set_title(0,'Step 1: Preliminaries')
        self.vCIME.set_title(1,'Step 2: Create Case')
        self.vCIME.set_title(2,'Help')

        self.construct_tab_observances()

        return self.vCIME

