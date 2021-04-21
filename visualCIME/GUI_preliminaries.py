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

        self.config_mode = widgets.ToggleButtons(
            options=['predefined', 'custom'],
            tooltips=['Select from configurations predefined within CESM.',
                      'Allows maximum flexibility. For advanced users and breakthrough applications.'],
            value='predefined',
            #layout={'width': 'max-content'}, # If the items' names are long
            description='Config Mode:',
            disabled=False
        )
        self.config_mode.style.button_width='80px'
        self.config_mode.style.description_width = '130px'

        self.debug_widget = widgets.ToggleButtons(
            options=['On (slow)', 'Off'],
            tooltips=['Turn on the debug mode to get detailed logs. This significantly slows down the GUI.',
                      '(Default) Turn off the debug mode to get minimal logs. This improves the responsiveness of the GUI.'],
            value='Off',
            #layout={'width': 'max-content'}, # If the items' names are long
            description='Debug:',
            disabled=False
        )
        self.debug_widget.style.button_width='60px'
        self.debug_widget.style.description_width = '100px'

        self.confirm_prelim_widget = widgets.Button(
            description='Confirm',
            disabled=False,
            button_style='', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Confirm',
            icon='check',
            layout = {'width':'100px'},
        )

        self.reset_prelim_widget = widgets.Button(
            description='Reset',
            disabled=True,
            button_style='danger', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Reset',
            icon='undo',
            layout = {'width':'100px'},
        )

    def construct(self):

        hbx_basics = widgets.VBox([
            widgets.HBox([self.driver_widget, self.config_mode, self.debug_widget]),
            widgets.HBox([widgets.Label('')]), # empty
            widgets.VBox([
                widgets.HBox([self.confirm_prelim_widget, self.reset_prelim_widget])],
                layout={'align_items':'flex-end'})
        ])
        #hbx_basics.layout.border = '2px dotted lightgray'

        return hbx_basics

