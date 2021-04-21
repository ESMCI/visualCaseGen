import os, sys, re
import ipywidgets as widgets

from visualCIME.visualCIME.ConfigVar import ConfigVar
from visualCIME.visualCIME.OutHandler import handler as owh

import logging
logger = logging.getLogger(__name__)

class GUI_create_novice():

    def __init__(self, ci):
        self.ci = ci

    def construct(self):

        #return vbx_create_case # TODO
        return widgets.VBox([widgets.Label(value="Not implemented yet...")])
