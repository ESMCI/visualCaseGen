"""CIME_interface

This module interfaces VisualCIME with the conventional CIME.
"""

import os, sys
import re

# import CIME -----------------------------------------------------------
CIMEROOT = "/glade/work/altuntas/cesm.sandboxes/cesm2.2.0_simple/cime"
sys.path.append(os.path.join(CIMEROOT, "scripts", "Tools"))

from standard_script_setup import *
from CIME.case import Case
from CIME.nmlgen import NamelistGenerator
from CIME.utils import expect
from CIME.XML.machines              import Machines
from CIME.XML.pes                   import Pes
from CIME.XML.files                 import Files
from CIME.XML.component             import Component
from CIME.XML.compsets              import Compsets
from CIME.XML.grids                 import Grids
from CIME.YML.compliances           import Compliances

import logging
logger = logging.getLogger(__name__)

class CIME_interface():
    
    def __init__(self):
        self.driver = None
        self.files = None
        self.comp_classes = None
        self.compliances = Compliances.from_cime()
        self.compliances.unfold_implications()
        self._retrieve_CIME_basics()
        self._comp_phys_opt = dict()

    def _retrieve_CIME_basics(self):
        """ Determine basic CIME variables and properties, including:
            - driver: 'nuopc' or 'mct'.
            - files: CIME.XML.files instance containing XML files of CIME.
            - comp_classes: The list of component classes, e.g., ATM, OCN, ICE, etc.,
                excluding CPL and ESP.

            Notes
            -----
                CIME basics variables (driver, files, etc.) are defined as CIME_interface module variables
        """

        self.driver = 'nuopc'
        self.files = Files(comp_interface=self.driver)
        drv_config_file = self.files.get_value("CONFIG_CPL_FILE")
        drv_comp = Component(drv_config_file, "CPL")
        self.comp_classes = drv_comp.get_valid_model_components()
        self.comp_classes = [c for c in self.comp_classes if c not in ['CPL', 'ESP']]

    def retrieve_comp_phys_opt(self, comp_class, model):
        """ Retrieves component physics (CAM60, CICE6, etc.) and options (%SCAM, %ECO, etc) from  config_component.xml file
        of a given comp_class and a given model ("cam", "cice", etc).

        Parameters
        ----------
        comp_class : str
            component class, e.g., "ATM", "ICE", etc.
        model : str
            model name excluding version number, e.g., "cam", "cice", "mom", etc.

        Returns
        -------
        comp_physics : list of strings
            List of physics for the given component model, e.g., "CAM40", "CAM50", "CAM60", etc.
        comp_options : list of strings
            List of options (modifiers) for the given components model, e.g., %SCAM, %ECO, etc.
        """

        if (comp_class, model) in self._comp_phys_opt:
            pass
        else:
            compatt = {"component": model}
            comp_config_file =  self.files.get_value('CONFIG_{}_FILE'.format(comp_class), compatt)
            compobj = Component(comp_config_file, comp_class)
            rootnode = compobj.get_child("description")
            desc_nodes = compobj.get_children("desc", root=rootnode)

            comp_physics = [] # e.g., CAM60, CICE6, etc.
            comp_options = [] # e.g., %SCAM, %ECO, etc.

            # Go through description entries in config_component.xml nd extract component physics and options:
            for node in desc_nodes:
                physics = compobj.get(node, comp_class.lower()) 
                option = compobj.get(node, 'option') 
                if physics:
                    comp_phys = physics
                    if '[%' in comp_phys:
                        comp_phys = physics.split('[%')[0]
                    if len(comp_phys)>0:
                        comp_physics.append(comp_phys)
                elif option:
                    comp_options.append(option.strip())

            self._comp_phys_opt[(comp_class,model)] = comp_physics, comp_options

        return self._comp_phys_opt[(comp_class,model)] 

    def retrieve_models(self, comp_class):

        # Find list of models for component class
        # List can be in different locations, check CONFIG_XXX_FILE
        comp_config_filename = 'CONFIG_{}_FILE'.format(comp_class)
        models = self.files.get_components(comp_config_filename)

        # Backup, check COMP_ROOT_DIR_XXX
        root_dir_node_name = 'COMP_ROOT_DIR_' + comp_class
        if (models is None) or (None in models):
            models = self.files.get_components(root_dir_node_name)

        # sanity checks
        assert (models is not None) and (None not in models),"Unable to find list of supported components"

        # sanity checks, contd.
        for model in models:
            compatt = {"component":model}
            logger.debug("Reading CIME XML for model {}...".format(model))
            comp_config_file = self.files.get_value(comp_config_filename, compatt, resolved=False)
            assert comp_config_file is not None,"No component {} found for class {}".format(model, comp_class)
            comp_config_file =  self.files.get_value(comp_config_filename, compatt)
            if not( comp_config_file is not None and os.path.isfile(comp_config_file) ):
                logger.warning("Config file {} for component {} not found.".format(comp_config_file, model))
                continue

        return models