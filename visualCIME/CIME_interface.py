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
    """CIME_interface class is an interface from VisualCIME to conventional CIME.

    CIME_interface provides several attributes (data members) as listed below. All CIME_interface methods are intended
    to be called within __init__().

    Attributes
    ----------
    driver : str
        Selected CIME driver: "noupc" or "mct"
    comp_classes : list of str
        List of available component classes, e.g., "ATM", "ICE", etc.
    models : dict of str (with str as keys)
        A mapping from component class to available models, e.g., models["ATM"] = {datm, cam, ...}
    phys_opt : dict of pairs of str (with str keys)
        A mapping from model to pair of available (physics, options), where physics are CAM50, CAM60, etc. and options
        are 4xCO2, 1PCT, etc.
    model_grids: list of tuples
        List of model grids (alias, compset, not_compset)
    compliances : CIME.YML.compliances.Compliances
        An object that encapsulates CIME config variable compliances, i.e., logical constraints regarding
        config variables.
    """

    def __init__(self, driver):
        # data members
        self.driver = driver            # nuopc or mct
        self.comp_classes = None        # ATM, ICE, etc.
        self.models = dict()            # cam, cice, etc.
        self.phys_opt = dict()          # component physics (CAM50, CAM60, etc.) and options(4xCO2, 1PCT, etc.)
        self.model_grids = dict()       # model grids (alias, compset, not_compset)
        self.compsets = dict()          # compsets defined at each component
        self._files = None
        self.cimeroot = CIMEROOT

        # Call _retrieve* methods to populate the data members defined above
        self._retrieve_CIME_basics()
        for comp_class in self.comp_classes:
            self._retrieve_models(comp_class)
            for model in self.models[comp_class]:
                self._retrieve_model_phys_opt(comp_class,model)
        self._retrieve_model_grids()

        self._retrieve_compsets()

        # Initialize the compliances instance
        self.compliances = Compliances.from_cime()
        self.compliances.unfold_compliances()

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

        self._files = Files(comp_interface=self.driver)
        drv_config_file = self._files.get_value("CONFIG_CPL_FILE")
        drv_comp = Component(drv_config_file, "CPL")
        self.comp_classes = drv_comp.get_valid_model_components()
        self.comp_classes = [c for c in self.comp_classes if c not in ['CPL', 'ESP']]

    def _retrieve_model_phys_opt(self, comp_class, model):
        """ Retrieves component physics (CAM60, CICE6, etc.) and options (%SCAM, %ECO, etc) from  config_component.xml
        file from a given comp_class and model. Retrieved physics and options pairs are stored in self.phys_opt dict.

        Parameters
        ----------
        comp_class : str
            component class, e.g., "ATM", "ICE", etc.
        model : str
            model name excluding version number, e.g., "cam", "cice", "mom", etc.
        """

        compatt = {"component": model}
        comp_config_file =  self._files.get_value('CONFIG_{}_FILE'.format(comp_class), compatt)
        if not os.path.exists(comp_config_file):
            logger.error("config file for {} doesn't exist.".format(model))
            return
        compobj = Component(comp_config_file, comp_class)
        rootnode = compobj.get_child("description")
        desc_nodes = compobj.get_children("desc", root=rootnode)

        comp_physics = [] # e.g., CAM60, CICE6, etc.
        comp_options = [] # e.g., %SCAM, %ECO, etc.
        comp_physics_desc = []
        comp_options_desc = []

        # Go through description entries in config_component.xml nd extract component physics and options:
        for node in desc_nodes:
            physics = compobj.get(node, comp_class.lower())
            option = compobj.get(node, 'option')
            description = compobj.text(node)
            if description[-1]==':':
                description = description[:-1]
            if physics:
                if '[%' in physics:
                    physics = physics.split('[%')[0]
                if len(physics)>0:
                    comp_physics.append(physics)
                comp_physics_desc.append("{}: {}".format(physics, description))
            elif option:
                option = option.strip()
                comp_options.append(option)
                comp_options_desc.append("{}: {}".format(option, description))

        self.phys_opt[model] = comp_physics, comp_options, comp_physics_desc, comp_options_desc

    def _retrieve_models(self, comp_class):
        """ Retrieves the available models of a given component class. Retrieved models
        are stored in self.models dict.

        Parameters
        ----------
        comp_class : str
            component class, e.g., "ATM", "ICE", etc.
        """

        # Find list of models for component class
        # List can be in different locations, check CONFIG_XXX_FILE
        comp_config_filename = 'CONFIG_{}_FILE'.format(comp_class)
        _models = self._files.get_components(comp_config_filename)

        # Backup, check COMP_ROOT_DIR_XXX
        root_dir_node_name = 'COMP_ROOT_DIR_' + comp_class
        if (_models is None) or (None in _models):
            _models = self._files.get_components(root_dir_node_name)

        # sanity checks
        assert (_models is not None) and (None not in _models),"Unable to find list of supported components"

        # update models for this comp_class
        self.models[comp_class] = []
        for model in _models:
            compatt = {"component":model}
            logger.debug("Reading CIME XML for model {}...".format(model))
            comp_config_file = self._files.get_value(comp_config_filename, compatt, resolved=False)
            assert comp_config_file is not None,"No component {} found for class {}".format(model, comp_class)
            comp_config_file =  self._files.get_value(comp_config_filename, compatt)
            if not( comp_config_file is not None and os.path.isfile(comp_config_file) ):
                logger.warning("Config file {} for component {} not found.".format(comp_config_file, model))
                continue
            else:
                self.models[comp_class].append(model)

    def _retrieve_model_grids(self):
        g = Grids()
        grids = g.get_child("grids")
        model_grids_xml = g.get_children("model_grid", root=grids)

        self.model_grids = []
        for model_grid in model_grids_xml:
            alias = g.get(model_grid,"alias")
            compset = g.get(model_grid,"compset")
            not_compset = g.get(model_grid,"not_compset")
            self.model_grids.append((alias, compset, not_compset))

    def _retrieve_compsets(self):
        cc = self._files.get_components("COMPSETS_SPEC_FILE")

        for component in cc:
            compsets_filename = self._files.get_value("COMPSETS_SPEC_FILE", {"component":component})

            # Check if COMPSET spec file exists
            if (os.path.isfile(compsets_filename)):
                self.compsets[component] = []
                c = Compsets(compsets_filename)
                compsets_xml = c.get_children("compset")
                for compset in compsets_xml:
                    alias  = c.text(c.get_child("alias", root=compset))
                    lname  = c.text(c.get_child("lname", root=compset))
                    self.compsets[component].append((alias,lname))
