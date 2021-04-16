import os, sys, re
import ipywidgets as widgets

import logging
logger = logging.getLogger(__name__)

class GUI_preliminaries():

    def __init__(self):

        self.driver_widget = widgets.Dropdown(
            options=['nuopc','mct'],
            value='nuopc',
            description='Driver:',
            layout={'width': '180px'}, # If the items' names are long
            disabled=False,
        )

        self.support_widget = widgets.ToggleButtons(
            options=['scientific', 'unsupported'],
            tooltips=['Select from scientifically supported configurations predefined within CESM.',
                      'Allows maximum flexibility. For advanced users and breakthrough applications.'],
            value='unsupported',
            #layout={'width': 'max-content'}, # If the items' names are long
            description='Support Level:',
            disabled=False
        )
        self.support_widget.style.button_width='80px'
        self.support_widget.style.description_width = '140px'

        self.confirm_prelim_widget = widgets.Button(
            description='Confirm',
            disabled=False,
            button_style='', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Confirm',
            layout = {'width':'90px'},
        )

        self.reset_prelim_widget = widgets.Button(
            description='Reset',
            disabled=True,
            button_style='danger', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Reset',
            layout = {'width':'90px'},
        )

    def construct(self):

        hbx_basics = widgets.VBox([
            widgets.HBox([self.driver_widget, self.support_widget]),
            widgets.VBox([
                widgets.HBox([self.confirm_prelim_widget, self.reset_prelim_widget])],
                layout={'align_items':'flex-end'})
        ])
        #hbx_basics.layout.border = '2px dotted lightgray'

        return hbx_basics

